#!/usr/bin/env python3
"""
Plan parser for extracting task dependencies from plan.md.

Parses the plan.md file to extract task information including status,
dependencies, and branch names. Used for dependency enforcement.
"""

import re
from pathlib import Path
from typing import Optional


# Status values that are considered "complete" for dependency checking
COMPLETED_STATUSES = {'COMPLETED', 'DONE', 'MERGED'}

# Status values that are considered valid
VALID_STATUSES = {
    'PENDING', 'IN_PROGRESS', 'IN_REVIEW', 'ITERATING',
    'COMPLETED', 'DONE', 'MERGED', 'BLOCKED', 'ABANDONED'
}


def parse_plan(workspace_path: str) -> dict:
    """
    Parse plan.md and return task information.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        {
            "success": True/False,
            "tasks": {
                "task-name": {
                    "status": "PENDING",
                    "dependencies": ["dep1", "dep2"],
                    "branch": "feature/...",
                    "priority": "HIGH",  # if specified
                    "description": "..."  # if specified
                }
            },
            "error": "..." # if success is False
        }
    """
    workspace = Path(workspace_path)
    plan_path = workspace / "plan.md"

    if not plan_path.exists():
        return {
            "success": False,
            "error": f"plan.md not found at {plan_path}",
            "hint": "Create a plan.md file or run 'operator plan' first",
            "tasks": {}
        }

    try:
        content = plan_path.read_text()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read plan.md: {e}",
            "tasks": {}
        }

    tasks = {}

    # Pattern to match task headers like "### 1. task-name" or "### task-name"
    # Supports formats:
    #   ### 1. task-name
    #   ### task-name
    #   ### 1. `task-name`
    task_header_pattern = re.compile(
        r'^###\s+(?:\d+\.\s+)?`?([a-zA-Z0-9_-]+)`?\s*$',
        re.MULTILINE
    )

    # Pattern to extract status
    status_pattern = re.compile(
        r'^-\s*Status:\s*(\w+)',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern to extract dependencies
    deps_pattern = re.compile(
        r'^-\s*Dependencies:\s*(.+)$',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern to extract branch
    branch_pattern = re.compile(
        r'^-\s*Branch:\s*(.+)$',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern to extract priority
    priority_pattern = re.compile(
        r'^-\s*Priority:\s*(\w+)',
        re.MULTILINE | re.IGNORECASE
    )

    # Pattern to extract description
    desc_pattern = re.compile(
        r'^-\s*Description:\s*(.+)$',
        re.MULTILINE | re.IGNORECASE
    )

    # Find all task sections
    matches = list(task_header_pattern.finditer(content))

    for i, match in enumerate(matches):
        task_name = match.group(1)

        # Get section content (from this header to next header or end)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section = content[start:end]

        task_info = {
            "status": "PENDING",
            "dependencies": [],
            "branch": None,
            "priority": None,
            "description": None
        }

        # Extract status
        status_match = status_pattern.search(section)
        if status_match:
            status = status_match.group(1).upper()
            if status in VALID_STATUSES:
                task_info["status"] = status

        # Extract dependencies
        deps_match = deps_pattern.search(section)
        if deps_match:
            deps_str = deps_match.group(1).strip()
            if deps_str.lower() not in ('none', 'n/a', '-', ''):
                # Split by comma and clean up
                deps = [
                    dep.strip().strip('`')
                    for dep in deps_str.split(',')
                    if dep.strip() and dep.strip().lower() not in ('none', 'n/a')
                ]
                task_info["dependencies"] = deps

        # Extract branch
        branch_match = branch_pattern.search(section)
        if branch_match:
            task_info["branch"] = branch_match.group(1).strip()

        # Extract priority
        priority_match = priority_pattern.search(section)
        if priority_match:
            task_info["priority"] = priority_match.group(1).upper()

        # Extract description
        desc_match = desc_pattern.search(section)
        if desc_match:
            task_info["description"] = desc_match.group(1).strip()

        tasks[task_name] = task_info

    return {
        "success": True,
        "tasks": tasks,
        "task_count": len(tasks)
    }


def get_unblocked_tasks(workspace_path: str) -> dict:
    """
    Return list of tasks ready to spawn (all dependencies met).

    A task is "unblocked" if:
    1. Its status is PENDING (not started yet)
    2. All its dependencies have status COMPLETED/DONE/MERGED

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        {
            "success": True/False,
            "unblocked": ["task1", "task2"],  # Tasks ready to spawn
            "blocked": {  # Tasks not ready
                "task3": {
                    "missing": ["dep1", "dep2"],
                    "status": "PENDING"
                }
            },
            "in_progress": ["task4"],  # Already started
            "completed": ["task5"]  # Already done
        }
    """
    plan_result = parse_plan(workspace_path)

    if not plan_result["success"]:
        return {
            "success": False,
            "error": plan_result.get("error", "Failed to parse plan"),
            "unblocked": [],
            "blocked": {},
            "in_progress": [],
            "completed": []
        }

    tasks = plan_result["tasks"]

    unblocked = []
    blocked = {}
    in_progress = []
    completed = []

    for task_name, task_info in tasks.items():
        status = task_info["status"]

        # Categorize by current status
        if status in COMPLETED_STATUSES:
            completed.append(task_name)
            continue

        if status in ('IN_PROGRESS', 'IN_REVIEW', 'ITERATING'):
            in_progress.append(task_name)
            continue

        if status == 'ABANDONED':
            continue

        # For PENDING/BLOCKED tasks, check dependencies
        deps = task_info.get("dependencies", [])

        if not deps:
            # No dependencies - ready to spawn
            unblocked.append(task_name)
        else:
            # Check if all dependencies are completed
            missing = []
            for dep in deps:
                dep_info = tasks.get(dep)
                if dep_info is None:
                    # Dependency not found in plan - consider it missing
                    missing.append(dep)
                elif dep_info["status"] not in COMPLETED_STATUSES:
                    missing.append(dep)

            if missing:
                blocked[task_name] = {
                    "missing": missing,
                    "status": status
                }
            else:
                unblocked.append(task_name)

    return {
        "success": True,
        "unblocked": unblocked,
        "blocked": blocked,
        "in_progress": in_progress,
        "completed": completed
    }


def check_dependencies(task_name: str, workspace_path: str) -> dict:
    """
    Check if task dependencies are met.

    Args:
        task_name: Name of the task to check
        workspace_path: Path to the workspace directory

    Returns:
        {
            "success": True/False,
            "can_spawn": True/False,
            "task_exists": True/False,
            "missing": ["dep1", "dep2"],  # Dependencies not yet completed
            "completed": ["dep3"],  # Dependencies that are completed
            "status": "PENDING",  # Current task status
            "error": "..."  # If success is False
        }
    """
    plan_result = parse_plan(workspace_path)

    if not plan_result["success"]:
        return {
            "success": False,
            "can_spawn": False,
            "task_exists": False,
            "error": plan_result.get("error", "Failed to parse plan"),
            "missing": [],
            "completed": []
        }

    tasks = plan_result["tasks"]

    # Check if task exists in plan
    if task_name not in tasks:
        return {
            "success": True,
            "can_spawn": True,  # Unknown task - allow spawning (might be ad-hoc)
            "task_exists": False,
            "warning": f"Task '{task_name}' not found in plan.md - spawning anyway",
            "missing": [],
            "completed": []
        }

    task_info = tasks[task_name]
    status = task_info["status"]
    deps = task_info.get("dependencies", [])

    # If task is already completed or in progress, warn but allow
    if status in COMPLETED_STATUSES:
        return {
            "success": True,
            "can_spawn": False,
            "task_exists": True,
            "status": status,
            "warning": f"Task '{task_name}' is already {status}",
            "missing": [],
            "completed": deps
        }

    if status in ('IN_PROGRESS', 'IN_REVIEW', 'ITERATING'):
        return {
            "success": True,
            "can_spawn": True,  # Allow re-spawning in-progress tasks
            "task_exists": True,
            "status": status,
            "info": f"Task '{task_name}' is {status} - re-spawning",
            "missing": [],
            "completed": []
        }

    # Check dependencies
    if not deps:
        return {
            "success": True,
            "can_spawn": True,
            "task_exists": True,
            "status": status,
            "missing": [],
            "completed": []
        }

    missing = []
    completed = []

    for dep in deps:
        dep_info = tasks.get(dep)
        if dep_info is None:
            # Dependency not in plan - consider it missing
            missing.append(dep)
        elif dep_info["status"] in COMPLETED_STATUSES:
            completed.append(dep)
        else:
            missing.append(dep)

    can_spawn = len(missing) == 0

    result = {
        "success": True,
        "can_spawn": can_spawn,
        "task_exists": True,
        "status": status,
        "missing": missing,
        "completed": completed
    }

    if not can_spawn:
        result["error"] = f"Dependencies not met: {', '.join(missing)}"
        result["hint"] = "Complete dependencies first or use --force to override"

    return result


def format_unblocked_report(workspace_path: str) -> str:
    """
    Format a human-readable report of unblocked tasks.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        Formatted string report
    """
    result = get_unblocked_tasks(workspace_path)

    if not result["success"]:
        return f"Error: {result.get('error', 'Unknown error')}"

    lines = []
    lines.append("=" * 60)
    lines.append("TASK DEPENDENCY STATUS")
    lines.append("=" * 60)

    # Unblocked (ready to spawn)
    lines.append("\n✓ READY TO SPAWN:")
    if result["unblocked"]:
        for task in result["unblocked"]:
            lines.append(f"  - {task}")
    else:
        lines.append("  (none)")

    # In progress
    if result["in_progress"]:
        lines.append("\n⟳ IN PROGRESS:")
        for task in result["in_progress"]:
            lines.append(f"  - {task}")

    # Blocked
    if result["blocked"]:
        lines.append("\n✗ BLOCKED (dependencies not met):")
        for task, info in result["blocked"].items():
            missing = ", ".join(info["missing"])
            lines.append(f"  - {task}")
            lines.append(f"    Waiting on: {missing}")

    # Completed
    if result["completed"]:
        lines.append("\n✓ COMPLETED:")
        for task in result["completed"]:
            lines.append(f"  - {task}")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Plan parser and dependency checker")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # parse command
    parse_parser = subparsers.add_parser("parse", help="Parse plan.md")
    parse_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    parse_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # unblocked command
    unblocked_parser = subparsers.add_parser("unblocked", help="Show unblocked tasks")
    unblocked_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    unblocked_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # check command
    check_parser = subparsers.add_parser("check", help="Check task dependencies")
    check_parser.add_argument("task_name", help="Task name to check")
    check_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    check_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "parse":
        result = parse_plan(args.workspace)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Found {result['task_count']} tasks:")
                for name, info in result["tasks"].items():
                    deps = ", ".join(info["dependencies"]) if info["dependencies"] else "none"
                    print(f"  - {name}: {info['status']} (deps: {deps})")
            else:
                print(f"Error: {result['error']}")

    elif args.command == "unblocked":
        if args.json:
            result = get_unblocked_tasks(args.workspace)
            print(json.dumps(result, indent=2))
        else:
            print(format_unblocked_report(args.workspace))

    elif args.command == "check":
        result = check_dependencies(args.task_name, args.workspace)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["can_spawn"]:
                print(f"✓ Task '{args.task_name}' can be spawned")
                if result.get("completed"):
                    print(f"  Dependencies met: {', '.join(result['completed'])}")
            else:
                print(f"✗ Task '{args.task_name}' cannot be spawned")
                if result.get("missing"):
                    print(f"  Missing dependencies: {', '.join(result['missing'])}")
                if result.get("error"):
                    print(f"  {result['error']}")

    else:
        parser.print_help()
