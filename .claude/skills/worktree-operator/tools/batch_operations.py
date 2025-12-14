#!/usr/bin/env python3
"""
Batch operations for creating and spawning multiple tasks at once.

Provides efficient operations for larger plans with many tasks:
- create_all_tasks(): Create folders/worktrees for all pending plan tasks
- spawn_unblocked_tasks(): Spawn all tasks with met dependencies
- spawn_parallel(N): Spawn up to N tasks concurrently
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

# Import shared utilities
from logging_config import get_logger, OperationLogger
from locking import workspace_lock, LockError
from plan_parser import parse_plan, get_unblocked_tasks, COMPLETED_STATUSES
from task import create_task
from fork_terminal import spawn_forked_subagent
from errors import make_error

# Module logger
logger = get_logger("batch_operations")


@dataclass
class BatchResult:
    """Result of a batch operation."""
    success: bool
    created: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    spawned: List[str] = field(default_factory=list)
    failed: List[dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "created": self.created,
            "skipped": self.skipped,
            "spawned": self.spawned,
            "failed": self.failed,
            "errors": self.errors,
            "message": self.message,
            "summary": {
                "created_count": len(self.created),
                "skipped_count": len(self.skipped),
                "spawned_count": len(self.spawned),
                "failed_count": len(self.failed)
            }
        }


def create_all_tasks(
    workspace_path: str = ".",
    ticket: str = "WH",
    main_branch: str = "main"
) -> dict:
    """
    Create task folders and worktrees for all PENDING tasks in plan.md.

    This function parses plan.md to find all tasks with PENDING status
    and creates the task folder structure and git worktrees for each.
    Tasks that already have folders are skipped.

    Args:
        workspace_path: Path to the workspace directory
        ticket: Ticket ID prefix for branch names (default: "WH")
        main_branch: Main branch to create worktrees from

    Returns:
        dict with:
            - success: Overall success status
            - created: List of task names successfully created
            - skipped: List of task names that already existed
            - failed: List of dicts with task name and error for failed creations
            - errors: List of error messages
            - message: Summary message
    """
    workspace = Path(workspace_path).resolve()
    result = BatchResult(success=True)

    with OperationLogger(logger, "create_all_tasks", workspace=str(workspace)):
        # Parse plan.md to get all tasks
        plan_result = parse_plan(str(workspace))

        if not plan_result["success"]:
            return make_error(
                f"Failed to parse plan.md: {plan_result.get('error', 'Unknown error')}",
                hint=plan_result.get("hint", "Ensure plan.md exists and is properly formatted"),
                error_code="PLAN_PARSE_FAILED"
            )

        tasks = plan_result.get("tasks", {})

        if not tasks:
            return make_error(
                "No tasks found in plan.md",
                hint="Create a plan with tasks first: operator plan",
                error_code="NO_TASKS_FOUND"
            )

        # Filter to only PENDING tasks
        pending_tasks = [
            name for name, info in tasks.items()
            if info.get("status", "PENDING") == "PENDING"
        ]

        if not pending_tasks:
            result.message = "No pending tasks found in plan.md"
            logger.info("create_all_tasks: No pending tasks to create")
            return result.to_dict()

        logger.info(f"create_all_tasks: Found {len(pending_tasks)} pending tasks to create")

        # Acquire workspace lock for batch creation
        try:
            with workspace_lock(str(workspace), "create_all_tasks"):
                for task_name in pending_tasks:
                    task_dir = workspace / f"task-{task_name}"

                    # Skip if task folder already exists
                    if task_dir.exists():
                        result.skipped.append(task_name)
                        logger.info(f"create_all_tasks: Skipping {task_name} (folder exists)")
                        continue

                    # Create the task
                    create_result = create_task(
                        ticket=ticket,
                        task_name=task_name,
                        main_branch=main_branch,
                        workspace_path=str(workspace)
                    )

                    if create_result.get("success"):
                        result.created.append(task_name)
                        logger.info(f"create_all_tasks: Created {task_name}")
                    else:
                        result.failed.append({
                            "task": task_name,
                            "error": create_result.get("error", "Unknown error")
                        })
                        result.errors.append(f"{task_name}: {create_result.get('error')}")
                        logger.error(f"create_all_tasks: Failed to create {task_name}: {create_result.get('error')}")

        except LockError as e:
            return e.to_dict()

        # Build summary
        result.success = len(result.failed) == 0
        parts = []
        if result.created:
            parts.append(f"{len(result.created)} created")
        if result.skipped:
            parts.append(f"{len(result.skipped)} skipped (already exist)")
        if result.failed:
            parts.append(f"{len(result.failed)} failed")

        result.message = f"Batch create complete: {', '.join(parts)}"

        return result.to_dict()


def spawn_unblocked_tasks(
    workspace_path: str = ".",
    ticket: str = "WH",
    model: str = "opus",
    force: bool = False
) -> dict:
    """
    Spawn sub-agents for all unblocked tasks (dependencies met, status PENDING).

    Uses get_unblocked_tasks() from plan_parser.py to identify tasks ready
    to spawn, then uses fork_terminal.spawn_forked_subagent() to launch
    each sub-agent in a new terminal window.

    Args:
        workspace_path: Path to the workspace directory
        ticket: Ticket ID for commit messages
        model: Model to use for sub-agents (opus, sonnet, haiku)
        force: If True, skip dependency checking

    Returns:
        dict with:
            - success: Overall success status
            - spawned: List of task names successfully spawned
            - skipped: List of task names skipped (no folder/worktree)
            - failed: List of dicts with task name and error
            - errors: List of error messages
            - message: Summary message
    """
    workspace = Path(workspace_path).resolve()
    result = BatchResult(success=True)

    with OperationLogger(logger, "spawn_unblocked_tasks", workspace=str(workspace)):
        # Get unblocked tasks
        unblocked_result = get_unblocked_tasks(str(workspace))

        if not unblocked_result["success"]:
            return make_error(
                f"Failed to get unblocked tasks: {unblocked_result.get('error', 'Unknown error')}",
                hint="Ensure plan.md exists and is properly formatted",
                error_code="UNBLOCKED_CHECK_FAILED"
            )

        unblocked_tasks = unblocked_result.get("unblocked", [])

        if not unblocked_tasks:
            blocked_info = unblocked_result.get("blocked", {})
            in_progress = unblocked_result.get("in_progress", [])

            message_parts = ["No unblocked tasks to spawn"]
            if in_progress:
                message_parts.append(f"{len(in_progress)} task(s) already in progress")
            if blocked_info:
                message_parts.append(f"{len(blocked_info)} task(s) blocked by dependencies")

            result.message = ". ".join(message_parts)
            logger.info(f"spawn_unblocked_tasks: {result.message}")
            return result.to_dict()

        logger.info(f"spawn_unblocked_tasks: Found {len(unblocked_tasks)} unblocked tasks to spawn")

        # Spawn each unblocked task
        for task_name in unblocked_tasks:
            task_dir = workspace / f"task-{task_name}"
            worktree_path = task_dir / "worktree"

            # Check if task folder exists
            if not task_dir.exists() or not worktree_path.exists():
                result.skipped.append(task_name)
                logger.info(f"spawn_unblocked_tasks: Skipping {task_name} (no folder/worktree)")
                continue

            # Spawn the sub-agent
            spawn_result = spawn_forked_subagent(
                task_name=task_name,
                ticket=ticket,
                workspace_path=str(workspace),
                model=model,
                iteration=1,
                force=force
            )

            if spawn_result.get("success"):
                result.spawned.append(task_name)
                logger.info(f"spawn_unblocked_tasks: Spawned {task_name}")
            else:
                result.failed.append({
                    "task": task_name,
                    "error": spawn_result.get("error", "Unknown error")
                })
                result.errors.append(f"{task_name}: {spawn_result.get('error')}")
                logger.error(f"spawn_unblocked_tasks: Failed to spawn {task_name}: {spawn_result.get('error')}")

        # Build summary
        result.success = len(result.failed) == 0
        parts = []
        if result.spawned:
            parts.append(f"{len(result.spawned)} spawned")
        if result.skipped:
            parts.append(f"{len(result.skipped)} skipped (no folder/worktree)")
        if result.failed:
            parts.append(f"{len(result.failed)} failed")

        result.message = f"Spawn unblocked complete: {', '.join(parts)}"

        return result.to_dict()


def spawn_parallel(
    max_parallel: int = 3,
    workspace_path: str = ".",
    ticket: str = "WH",
    model: str = "opus",
    force: bool = False
) -> dict:
    """
    Spawn up to N tasks concurrently, respecting dependency order.

    This function gets unblocked tasks from plan_parser and spawns
    up to max_parallel of them. It respects task dependencies,
    only spawning tasks whose dependencies are completed.

    Args:
        max_parallel: Maximum number of tasks to spawn (default: 3)
        workspace_path: Path to the workspace directory
        ticket: Ticket ID for commit messages
        model: Model to use for sub-agents (opus, sonnet, haiku)
        force: If True, skip dependency checking

    Returns:
        dict with:
            - success: Overall success status
            - spawned: List of task names successfully spawned
            - skipped: List of task names skipped (no folder/worktree)
            - remaining: List of unblocked tasks not spawned (hit limit)
            - failed: List of dicts with task name and error
            - errors: List of error messages
            - message: Summary message
    """
    workspace = Path(workspace_path).resolve()
    result = BatchResult(success=True)
    remaining = []

    with OperationLogger(logger, "spawn_parallel", workspace=str(workspace), max_parallel=max_parallel):
        # Validate max_parallel
        if max_parallel < 1:
            return make_error(
                f"Invalid max_parallel value: {max_parallel}",
                hint="max_parallel must be at least 1",
                error_code="INVALID_PARAM"
            )

        if max_parallel > 10:
            logger.warning(f"spawn_parallel: max_parallel={max_parallel} is very high, may cause resource issues")

        # Get unblocked tasks
        unblocked_result = get_unblocked_tasks(str(workspace))

        if not unblocked_result["success"]:
            return make_error(
                f"Failed to get unblocked tasks: {unblocked_result.get('error', 'Unknown error')}",
                hint="Ensure plan.md exists and is properly formatted",
                error_code="UNBLOCKED_CHECK_FAILED"
            )

        unblocked_tasks = unblocked_result.get("unblocked", [])

        if not unblocked_tasks:
            blocked_info = unblocked_result.get("blocked", {})
            in_progress = unblocked_result.get("in_progress", [])

            message_parts = ["No unblocked tasks to spawn"]
            if in_progress:
                message_parts.append(f"{len(in_progress)} task(s) already in progress")
            if blocked_info:
                message_parts.append(f"{len(blocked_info)} task(s) blocked by dependencies")

            result.message = ". ".join(message_parts)
            logger.info(f"spawn_parallel: {result.message}")
            return result.to_dict()

        logger.info(f"spawn_parallel: Found {len(unblocked_tasks)} unblocked tasks, spawning up to {max_parallel}")

        # Spawn up to max_parallel tasks
        spawned_count = 0
        for task_name in unblocked_tasks:
            # Check if we've hit the limit
            if spawned_count >= max_parallel:
                remaining.append(task_name)
                continue

            task_dir = workspace / f"task-{task_name}"
            worktree_path = task_dir / "worktree"

            # Check if task folder exists
            if not task_dir.exists() or not worktree_path.exists():
                result.skipped.append(task_name)
                logger.info(f"spawn_parallel: Skipping {task_name} (no folder/worktree)")
                continue

            # Spawn the sub-agent
            spawn_result = spawn_forked_subagent(
                task_name=task_name,
                ticket=ticket,
                workspace_path=str(workspace),
                model=model,
                iteration=1,
                force=force
            )

            if spawn_result.get("success"):
                result.spawned.append(task_name)
                spawned_count += 1
                logger.info(f"spawn_parallel: Spawned {task_name} ({spawned_count}/{max_parallel})")
            else:
                result.failed.append({
                    "task": task_name,
                    "error": spawn_result.get("error", "Unknown error")
                })
                result.errors.append(f"{task_name}: {spawn_result.get('error')}")
                logger.error(f"spawn_parallel: Failed to spawn {task_name}: {spawn_result.get('error')}")

        # Build summary
        result.success = len(result.failed) == 0

        result_dict = result.to_dict()
        result_dict["remaining"] = remaining
        result_dict["max_parallel"] = max_parallel

        parts = []
        if result.spawned:
            parts.append(f"{len(result.spawned)} spawned")
        if result.skipped:
            parts.append(f"{len(result.skipped)} skipped (no folder/worktree)")
        if remaining:
            parts.append(f"{len(remaining)} remaining (hit limit)")
        if result.failed:
            parts.append(f"{len(result.failed)} failed")

        result_dict["message"] = f"Spawn parallel complete: {', '.join(parts)}"

        return result_dict


def format_batch_report(result: dict) -> str:
    """
    Format a batch operation result as a human-readable report.

    Args:
        result: Result dictionary from a batch operation

    Returns:
        Formatted string report
    """
    lines = []
    lines.append("=" * 60)
    lines.append("BATCH OPERATION RESULT")
    lines.append("=" * 60)

    # Status
    status = "SUCCESS" if result.get("success") else "PARTIAL FAILURE"
    lines.append(f"\nStatus: {status}")

    if result.get("message"):
        lines.append(f"Summary: {result['message']}")

    # Created tasks
    if result.get("created"):
        lines.append(f"\n CREATED ({len(result['created'])}):")
        for task in result["created"]:
            lines.append(f"  - {task}")

    # Spawned tasks
    if result.get("spawned"):
        lines.append(f"\n SPAWNED ({len(result['spawned'])}):")
        for task in result["spawned"]:
            lines.append(f"  - {task}")

    # Skipped tasks
    if result.get("skipped"):
        lines.append(f"\n- SKIPPED ({len(result['skipped'])}):")
        for task in result["skipped"]:
            lines.append(f"  - {task}")

    # Remaining tasks
    if result.get("remaining"):
        lines.append(f"\n... REMAINING ({len(result['remaining'])}):")
        for task in result["remaining"]:
            lines.append(f"  - {task}")

    # Failed tasks
    if result.get("failed"):
        lines.append(f"\n FAILED ({len(result['failed'])}):")
        for item in result["failed"]:
            lines.append(f"  - {item['task']}: {item['error']}")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch operations for tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_operations.py create-all --workspace .
  python batch_operations.py spawn-unblocked --workspace . --model opus
  python batch_operations.py spawn-parallel 3 --workspace . --model opus
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create-all command
    create_all_parser = subparsers.add_parser(
        "create-all",
        help="Create task folders/worktrees for all pending tasks"
    )
    create_all_parser.add_argument(
        "--workspace", "-w",
        default=".",
        help="Workspace path (default: current directory)"
    )
    create_all_parser.add_argument(
        "--ticket", "-t",
        default="WH",
        help="Ticket ID prefix (default: WH)"
    )
    create_all_parser.add_argument(
        "--main-branch", "-b",
        default="main",
        help="Main branch to branch from (default: main)"
    )
    create_all_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    # spawn-unblocked command
    spawn_unblocked_parser = subparsers.add_parser(
        "spawn-unblocked",
        help="Spawn all tasks with met dependencies"
    )
    spawn_unblocked_parser.add_argument(
        "--workspace", "-w",
        default=".",
        help="Workspace path (default: current directory)"
    )
    spawn_unblocked_parser.add_argument(
        "--ticket", "-t",
        default="WH",
        help="Ticket ID for commits (default: WH)"
    )
    spawn_unblocked_parser.add_argument(
        "--model", "-m",
        default="opus",
        choices=["opus", "sonnet", "haiku"],
        help="Model to use (default: opus)"
    )
    spawn_unblocked_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip dependency checking"
    )
    spawn_unblocked_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    # spawn-parallel command
    spawn_parallel_parser = subparsers.add_parser(
        "spawn-parallel",
        help="Spawn up to N tasks concurrently"
    )
    spawn_parallel_parser.add_argument(
        "max_parallel",
        type=int,
        nargs="?",
        default=3,
        help="Maximum tasks to spawn (default: 3)"
    )
    spawn_parallel_parser.add_argument(
        "--workspace", "-w",
        default=".",
        help="Workspace path (default: current directory)"
    )
    spawn_parallel_parser.add_argument(
        "--ticket", "-t",
        default="WH",
        help="Ticket ID for commits (default: WH)"
    )
    spawn_parallel_parser.add_argument(
        "--model", "-m",
        default="opus",
        choices=["opus", "sonnet", "haiku"],
        help="Model to use (default: opus)"
    )
    spawn_parallel_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip dependency checking"
    )
    spawn_parallel_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    if args.command == "create-all":
        result = create_all_tasks(
            workspace_path=args.workspace,
            ticket=args.ticket,
            main_branch=args.main_branch
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_batch_report(result))
            if result["success"]:
                sys.exit(0)
            else:
                sys.exit(1)

    elif args.command == "spawn-unblocked":
        result = spawn_unblocked_tasks(
            workspace_path=args.workspace,
            ticket=args.ticket,
            model=args.model,
            force=args.force
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_batch_report(result))
            if result["success"]:
                sys.exit(0)
            else:
                sys.exit(1)

    elif args.command == "spawn-parallel":
        result = spawn_parallel(
            max_parallel=args.max_parallel,
            workspace_path=args.workspace,
            ticket=args.ticket,
            model=args.model,
            force=args.force
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_batch_report(result))
            if result["success"]:
                sys.exit(0)
            else:
                sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)
