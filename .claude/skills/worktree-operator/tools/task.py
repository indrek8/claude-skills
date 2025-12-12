#!/usr/bin/env python3
"""
Task management tools for the operator skill.

Handles creation, synchronization, acceptance, and reset of tasks and their worktrees.
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Import shared validation utilities
from validation import (
    ValidationError,
    validate_task_name,
    validate_ticket,
    validate_branch_name,
    validate_path,
)

# Import test runner
from test_runner import run_tests, verify_tests_pass


def run_command(cmd: list[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def create_task(
    ticket: str,
    task_name: str,
    main_branch: str,
    workspace_path: str = ".",
    spec_content: Optional[str] = None
) -> dict:
    """
    Create a new task with folder structure and git worktree.

    Args:
        ticket: Ticket ID (e.g., "K-123")
        task_name: Task name (e.g., "fix-logging")
        main_branch: Main feature branch to branch from
        workspace_path: Path to workspace
        spec_content: Optional content for spec.md

    Returns:
        dict with creation results
    """
    # Validate inputs
    try:
        ticket = validate_ticket(ticket)
        task_name = validate_task_name(task_name)
        main_branch = validate_branch_name(main_branch)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    repo_path = workspace / "repo"
    task_dir = workspace / f"task-{task_name}"
    worktree_path = task_dir / "worktree"
    sub_branch = f"feature/{ticket}/{task_name}"

    # Validate repo exists
    if not repo_path.exists():
        return {
            "success": False,
            "error": f"Repository not found at {repo_path}",
            "hint": "Run workspace init first"
        }

    # Check if task already exists
    if task_dir.exists():
        return {
            "success": False,
            "error": f"Task folder already exists: {task_dir}",
            "hint": "Use a different task name or remove existing folder"
        }

    # Create task folder structure
    task_dir.mkdir(parents=True)

    # Create task files
    today = datetime.now().strftime("%Y-%m-%d")

    # spec.md
    spec_path = task_dir / "spec.md"
    if spec_content:
        spec_path.write_text(spec_content)
    else:
        spec_template = f"""# Task: {task_name}

## Ticket: {ticket}
## Branch: {sub_branch}
## Created: {today}

---

## Objective

_Describe the objective here_

---

## Requirements

1. _Requirement 1_
2. _Requirement 2_

---

## Files to Modify

- `path/to/file` - _what to change_

---

## Acceptance Criteria

- [ ] _Criterion 1_
- [ ] _Criterion 2_
- [ ] All existing tests pass

---

## Hints / Guidance

- _Helpful hints_
"""
        spec_path.write_text(spec_template)

    # feedback.md (empty initially)
    feedback_path = task_dir / "feedback.md"
    feedback_path.write_text(f"# Feedback: {task_name}\n\n_No feedback yet_\n")

    # results.md (empty initially)
    results_path = task_dir / "results.md"
    results_path.write_text(f"# Results: {task_name}\n\n_Results will be written by sub-agent_\n")

    # Create git worktree with sub-branch
    returncode, stdout, stderr = run_command(
        ["git", "worktree", "add", str(worktree_path), "-b", sub_branch, main_branch],
        cwd=str(repo_path)
    )

    if returncode != 0:
        # Clean up on failure
        import shutil
        shutil.rmtree(task_dir)
        return {
            "success": False,
            "error": f"Failed to create worktree: {stderr}",
            "command": f"git worktree add {worktree_path} -b {sub_branch} {main_branch}"
        }

    return {
        "success": True,
        "task_dir": str(task_dir),
        "worktree_path": str(worktree_path),
        "branch": sub_branch,
        "based_on": main_branch,
        "files_created": ["spec.md", "feedback.md", "results.md"],
        "message": f"Task '{task_name}' created successfully"
    }


def sync_task(
    task_name: str,
    main_branch: str,
    workspace_path: str = "."
) -> dict:
    """
    Sync (rebase) a task's worktree onto the latest main branch.

    Args:
        task_name: Task name
        main_branch: Main feature branch to rebase onto
        workspace_path: Path to workspace

    Returns:
        dict with sync results
    """
    # Validate inputs
    try:
        task_name = validate_task_name(task_name)
        main_branch = validate_branch_name(main_branch)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    task_dir = workspace / f"task-{task_name}"
    worktree_path = task_dir / "worktree"

    if not worktree_path.exists():
        return {
            "success": False,
            "error": f"Worktree not found at {worktree_path}",
            "hint": "Task may not exist or worktree was removed"
        }

    # Fetch latest
    returncode, stdout, stderr = run_command(
        ["git", "fetch", "origin"],
        cwd=str(worktree_path)
    )

    # Rebase onto main branch
    returncode, stdout, stderr = run_command(
        ["git", "rebase", main_branch],
        cwd=str(worktree_path)
    )

    if returncode != 0:
        # Check if it's a conflict
        if "CONFLICT" in stderr or "conflict" in stdout.lower():
            return {
                "success": False,
                "error": "Rebase has conflicts",
                "conflicts": True,
                "stderr": stderr,
                "hint": "Resolve conflicts manually, then run: git rebase --continue"
            }
        return {
            "success": False,
            "error": f"Rebase failed: {stderr}",
            "command": f"git rebase {main_branch}"
        }

    return {
        "success": True,
        "task_name": task_name,
        "rebased_onto": main_branch,
        "message": f"Task '{task_name}' synced with {main_branch}"
    }


def reset_task(
    task_name: str,
    main_branch: str,
    workspace_path: str = "."
) -> dict:
    """
    Reset a task's worktree to the main branch state (hard reset).

    Args:
        task_name: Task name
        main_branch: Main feature branch to reset to
        workspace_path: Path to workspace

    Returns:
        dict with reset results
    """
    # Validate inputs
    try:
        task_name = validate_task_name(task_name)
        main_branch = validate_branch_name(main_branch)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    task_dir = workspace / f"task-{task_name}"
    worktree_path = task_dir / "worktree"

    if not worktree_path.exists():
        return {
            "success": False,
            "error": f"Worktree not found at {worktree_path}"
        }

    # Fetch latest
    run_command(["git", "fetch", "origin"], cwd=str(worktree_path))

    # Hard reset to main branch
    returncode, stdout, stderr = run_command(
        ["git", "reset", "--hard", main_branch],
        cwd=str(worktree_path)
    )

    if returncode != 0:
        return {
            "success": False,
            "error": f"Reset failed: {stderr}"
        }

    # Clean untracked files
    run_command(["git", "clean", "-fd"], cwd=str(worktree_path))

    return {
        "success": True,
        "task_name": task_name,
        "reset_to": main_branch,
        "message": f"Task '{task_name}' reset to {main_branch}"
    }


def accept_task(
    ticket: str,
    task_name: str,
    main_branch: str,
    workspace_path: str = ".",
    push: bool = True,
    delete_remote_branch: bool = True
) -> dict:
    """
    Accept a task: rebase, merge into main branch, cleanup.

    Args:
        ticket: Ticket ID
        task_name: Task name
        main_branch: Main feature branch
        workspace_path: Path to workspace
        push: Whether to push the main branch after merge
        delete_remote_branch: Whether to delete the remote sub-branch

    Returns:
        dict with acceptance results
    """
    # Validate inputs
    try:
        ticket = validate_ticket(ticket)
        task_name = validate_task_name(task_name)
        main_branch = validate_branch_name(main_branch)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    repo_path = workspace / "repo"
    task_dir = workspace / f"task-{task_name}"
    worktree_path = task_dir / "worktree"
    sub_branch = f"feature/{ticket}/{task_name}"

    results = {
        "success": True,
        "steps": [],
        "errors": []
    }

    if not worktree_path.exists():
        return {
            "success": False,
            "error": f"Worktree not found at {worktree_path}"
        }

    # Step 1: Rebase sub-branch onto main
    results["steps"].append("Rebasing sub-branch...")
    sync_result = sync_task(task_name, main_branch, str(workspace))
    if not sync_result["success"]:
        results["success"] = False
        results["errors"].append(f"Rebase failed: {sync_result.get('error')}")
        return results
    results["steps"].append("✓ Rebase complete")

    # Step 1.5: Verify tests pass after rebase
    results["steps"].append("Running tests after rebase...")
    test_result = verify_tests_pass(str(worktree_path), workspace_path=str(workspace))
    if not test_result["passed"]:
        results["success"] = False
        results["errors"].append(f"Tests failed after rebase: {test_result.get('error', 'Unknown error')}")
        results["test_output"] = test_result
        results["hint"] = "Fix test failures in the worktree before accepting"
        return results
    results["steps"].append(f"✓ Tests passed ({test_result.get('duration', '?')}s)")
    results["test_after_rebase"] = test_result

    # Step 2: Switch to main branch in repo
    results["steps"].append("Switching to main branch...")
    returncode, stdout, stderr = run_command(
        ["git", "switch", main_branch],
        cwd=str(repo_path)
    )
    if returncode != 0:
        results["success"] = False
        results["errors"].append(f"Failed to switch branch: {stderr}")
        return results
    results["steps"].append("✓ Switched to main branch")

    # Step 3: Merge with --no-ff
    results["steps"].append("Merging sub-branch...")

    # Try to get first line of spec for commit message
    spec_path = task_dir / "spec.md"
    merge_msg = f"Merge {task_name}"
    if spec_path.exists():
        lines = spec_path.read_text().split("\n")
        for line in lines:
            if line.startswith("## Objective"):
                # Get next non-empty line
                idx = lines.index(line)
                for next_line in lines[idx+1:]:
                    if next_line.strip() and not next_line.startswith("#"):
                        merge_msg = f"Merge {task_name}: {next_line.strip()[:50]}"
                        break
                break

    returncode, stdout, stderr = run_command(
        ["git", "merge", "--no-ff", sub_branch, "-m", merge_msg],
        cwd=str(repo_path)
    )
    if returncode != 0:
        results["success"] = False
        results["errors"].append(f"Merge failed: {stderr}")
        return results
    results["steps"].append("✓ Merge complete")
    results["merge_commit"] = merge_msg

    # Step 3.5: Verify tests pass after merge
    results["steps"].append("Running tests after merge...")
    test_result = verify_tests_pass(str(repo_path), workspace_path=str(workspace))
    if not test_result["passed"]:
        # Tests failed after merge - revert the merge!
        results["steps"].append("✗ Tests failed after merge, reverting...")
        revert_returncode, _, revert_stderr = run_command(
            ["git", "reset", "--hard", "HEAD~1"],
            cwd=str(repo_path)
        )
        if revert_returncode == 0:
            results["steps"].append("✓ Merge reverted")
            results["reverted"] = True
        else:
            results["errors"].append(f"Failed to revert merge: {revert_stderr}")

        results["success"] = False
        results["errors"].append(f"Tests failed after merge: {test_result.get('error', 'Unknown error')}")
        results["test_output"] = test_result
        results["hint"] = "The merge was reverted. Fix test failures and try again."
        return results
    results["steps"].append(f"✓ Tests passed after merge ({test_result.get('duration', '?')}s)")
    results["test_after_merge"] = test_result

    # Step 4: Push (optional)
    if push:
        results["steps"].append("Pushing main branch...")
        returncode, stdout, stderr = run_command(
            ["git", "push", "origin", main_branch],
            cwd=str(repo_path)
        )
        if returncode != 0:
            results["errors"].append(f"Push failed (non-fatal): {stderr}")
        else:
            results["steps"].append("✓ Pushed to origin")

    # Step 5: Remove worktree
    results["steps"].append("Removing worktree...")
    returncode, stdout, stderr = run_command(
        ["git", "worktree", "remove", str(worktree_path)],
        cwd=str(repo_path)
    )
    if returncode != 0:
        # Try force remove
        run_command(
            ["git", "worktree", "remove", str(worktree_path), "--force"],
            cwd=str(repo_path)
        )
    results["steps"].append("✓ Worktree removed")

    # Step 6: Delete local branch
    results["steps"].append("Deleting local branch...")
    returncode, stdout, stderr = run_command(
        ["git", "branch", "-d", sub_branch],
        cwd=str(repo_path)
    )
    if returncode != 0:
        # Force delete if needed
        run_command(["git", "branch", "-D", sub_branch], cwd=str(repo_path))
    results["steps"].append("✓ Local branch deleted")

    # Step 7: Delete remote branch (optional)
    if delete_remote_branch:
        results["steps"].append("Deleting remote branch...")
        returncode, stdout, stderr = run_command(
            ["git", "push", "origin", "--delete", sub_branch],
            cwd=str(repo_path)
        )
        if returncode == 0:
            results["steps"].append("✓ Remote branch deleted")
        else:
            results["steps"].append("- Remote branch not found or already deleted")

    results["message"] = f"Task '{task_name}' accepted and merged into {main_branch}"
    return results


def task_status(task_name: str, workspace_path: str = ".") -> dict:
    """
    Get detailed status of a specific task.

    Args:
        task_name: Task name
        workspace_path: Path to workspace

    Returns:
        dict with task status details
    """
    # Validate inputs
    try:
        task_name = validate_task_name(task_name)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    task_dir = workspace / f"task-{task_name}"
    worktree_path = task_dir / "worktree"

    status = {
        "task_name": task_name,
        "task_dir": str(task_dir),
        "exists": task_dir.exists()
    }

    if not task_dir.exists():
        status["error"] = "Task folder not found"
        return status

    # Check files
    status["files"] = {
        "spec.md": (task_dir / "spec.md").exists(),
        "feedback.md": (task_dir / "feedback.md").exists(),
        "results.md": (task_dir / "results.md").exists()
    }

    # Check worktree
    status["has_worktree"] = worktree_path.exists()

    if worktree_path.exists():
        # Get branch
        returncode, stdout, stderr = run_command(
            ["git", "branch", "--show-current"],
            cwd=str(worktree_path)
        )
        status["branch"] = stdout.strip() if returncode == 0 else "unknown"

        # Get commit count
        returncode, stdout, stderr = run_command(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=str(worktree_path)
        )
        status["total_commits"] = int(stdout.strip()) if returncode == 0 else 0

        # Get uncommitted changes
        returncode, stdout, stderr = run_command(
            ["git", "status", "--porcelain"],
            cwd=str(worktree_path)
        )
        changes = stdout.strip().split("\n") if stdout.strip() else []
        status["uncommitted_changes"] = len(changes)
        status["uncommitted_files"] = changes[:10]  # First 10 files

        # Get last commit
        returncode, stdout, stderr = run_command(
            ["git", "log", "-1", "--format=%h %s"],
            cwd=str(worktree_path)
        )
        status["last_commit"] = stdout.strip() if returncode == 0 else "none"

    # Read results.md summary if exists
    results_path = task_dir / "results.md"
    if results_path.exists():
        content = results_path.read_text()
        # Get first non-empty, non-header line as summary
        for line in content.split("\n"):
            if line.strip() and not line.startswith("#") and not line.startswith("_"):
                status["results_summary"] = line.strip()[:100]
                break

    return status


def list_tasks(workspace_path: str = ".") -> list:
    """
    List all tasks in the workspace.

    Args:
        workspace_path: Path to workspace

    Returns:
        list of task status dicts
    """
    # Validate inputs
    try:
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return [{
            "success": False,
            "error": str(e),
            "validation_error": True
        }]

    tasks = []

    if not workspace.exists():
        return tasks

    for item in sorted(workspace.iterdir()):
        if item.is_dir() and item.name.startswith("task-"):
            task_name = item.name[5:]  # Remove "task-" prefix
            tasks.append(task_status(task_name, workspace_path))

    return tasks


def print_task_status(task_name: str, workspace_path: str = "."):
    """Print task status in human-readable format."""
    status = task_status(task_name, workspace_path)

    print(f"\n{'='*60}")
    print(f"TASK: {status['task_name']}")
    print(f"{'='*60}")

    if not status.get('exists'):
        print("Task not found!")
        return

    print(f"Directory: {status['task_dir']}")
    print(f"Has worktree: {'Yes' if status.get('has_worktree') else 'No'}")

    if status.get('has_worktree'):
        print(f"Branch: {status.get('branch', 'unknown')}")
        print(f"Last commit: {status.get('last_commit', 'none')}")
        print(f"Uncommitted changes: {status.get('uncommitted_changes', 0)}")

    print(f"\nFiles:")
    for filename, exists in status.get('files', {}).items():
        mark = "✓" if exists else "✗"
        print(f"  {mark} {filename}")

    if status.get('results_summary'):
        print(f"\nResults summary: {status['results_summary']}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task management tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("ticket", help="Ticket ID (e.g., K-123)")
    create_parser.add_argument("task_name", help="Task name (e.g., fix-logging)")
    create_parser.add_argument("main_branch", help="Main branch to branch from")
    create_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync task with main branch")
    sync_parser.add_argument("task_name", help="Task name")
    sync_parser.add_argument("main_branch", help="Main branch to sync with")
    sync_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    # reset command
    reset_parser = subparsers.add_parser("reset", help="Reset task to main branch")
    reset_parser.add_argument("task_name", help="Task name")
    reset_parser.add_argument("main_branch", help="Main branch to reset to")
    reset_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    # accept command
    accept_parser = subparsers.add_parser("accept", help="Accept and merge task")
    accept_parser.add_argument("ticket", help="Ticket ID")
    accept_parser.add_argument("task_name", help="Task name")
    accept_parser.add_argument("main_branch", help="Main branch to merge into")
    accept_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    accept_parser.add_argument("--no-push", action="store_true", help="Don't push after merge")

    # status command
    status_parser = subparsers.add_parser("status", help="Show task status")
    status_parser.add_argument("task_name", help="Task name")
    status_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    # list command
    list_parser = subparsers.add_parser("list", help="List all tasks")
    list_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    args = parser.parse_args()

    if args.command == "create":
        result = create_task(args.ticket, args.task_name, args.main_branch, args.workspace)
        if result["success"]:
            print(f"✓ {result['message']}")
            print(f"  Task dir: {result['task_dir']}")
            print(f"  Branch: {result['branch']}")
        else:
            print(f"✗ Error: {result['error']}")
            sys.exit(1)

    elif args.command == "sync":
        result = sync_task(args.task_name, args.main_branch, args.workspace)
        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ Error: {result['error']}")
            if result.get('conflicts'):
                print("  Conflicts detected. Resolve manually.")
            sys.exit(1)

    elif args.command == "reset":
        result = reset_task(args.task_name, args.main_branch, args.workspace)
        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ Error: {result['error']}")
            sys.exit(1)

    elif args.command == "accept":
        result = accept_task(
            args.ticket, args.task_name, args.main_branch,
            args.workspace, push=not args.no_push
        )
        if result["success"]:
            print(f"✓ {result['message']}")
            for step in result["steps"]:
                print(f"  {step}")
        else:
            print(f"✗ Acceptance failed")
            for error in result["errors"]:
                print(f"  Error: {error}")
            sys.exit(1)

    elif args.command == "status":
        print_task_status(args.task_name, args.workspace)

    elif args.command == "list":
        tasks = list_tasks(args.workspace)
        if not tasks:
            print("No tasks found")
        else:
            print(f"\n{'='*60}")
            print("TASKS")
            print(f"{'='*60}")
            for task in tasks:
                wt = "✓" if task.get('has_worktree') else "✗"
                branch = task.get('branch', 'no worktree')
                print(f"  [{wt}] {task['task_name']}: {branch}")
            print(f"{'='*60}\n")

    else:
        parser.print_help()
