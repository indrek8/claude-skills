#!/usr/bin/env python3
"""
Workspace management tools for the operator skill.

Handles initialization, status, and cleanup of the multi-agent workspace.
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
    validate_branch_name,
    validate_path,
    validate_url,
)

# Import logging utilities
from logging_config import get_logger, log_operation_start, log_operation_success, log_operation_failure

# Module logger
logger = get_logger("workspace")


def run_command(cmd: list[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def init_workspace(
    repo_url: str,
    branch: str,
    workspace_path: str = ".",
    repo_folder: str = "repo"
) -> dict:
    """
    Initialize a new workspace for multi-agent development.

    Args:
        repo_url: Git repository URL to clone
        branch: Branch to checkout (feature branch or develop)
        workspace_path: Path to create workspace (default: current directory)
        repo_folder: Name of the repo folder (default: "repo")

    Returns:
        dict with status and details
    """
    # Validate inputs
    try:
        repo_url = validate_url(repo_url)
        branch = validate_branch_name(branch)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    # Validate repo_folder name (simple alphanumeric check)
    if not repo_folder or not repo_folder.replace('-', '').replace('_', '').isalnum():
        return {
            "success": False,
            "error": f"Invalid repo folder name: '{repo_folder}'",
            "hint": "Use alphanumeric characters, hyphens, or underscores"
        }

    repo_path = workspace / repo_folder

    # Validate workspace doesn't already have a repo
    if repo_path.exists():
        return {
            "success": False,
            "error": f"Repository folder already exists: {repo_path}",
            "hint": "Use a different workspace or remove existing repo folder"
        }

    # Create workspace directory if needed
    workspace.mkdir(parents=True, exist_ok=True)

    # Clone repository
    logger.info(f"init_workspace: Cloning {repo_url} into {repo_path}")
    returncode, stdout, stderr = run_command(
        ["git", "clone", repo_url, repo_folder],
        cwd=str(workspace)
    )

    if returncode != 0:
        logger.error(f"init_workspace: Failed to clone repository: {stderr}")
        return {
            "success": False,
            "error": f"Failed to clone repository: {stderr}",
            "command": f"git clone {repo_url} {repo_folder}"
        }

    # Checkout the specified branch
    logger.info(f"init_workspace: Checking out branch {branch}")
    returncode, stdout, stderr = run_command(
        ["git", "switch", branch],
        cwd=str(repo_path)
    )

    # If branch doesn't exist, try to create it
    if returncode != 0:
        logger.info(f"init_workspace: Branch {branch} not found, creating")
        returncode, stdout, stderr = run_command(
            ["git", "switch", "-c", branch],
            cwd=str(repo_path)
        )

        if returncode != 0:
            logger.error(f"init_workspace: Failed to checkout/create branch: {stderr}")
            return {
                "success": False,
                "error": f"Failed to checkout/create branch: {stderr}",
                "command": f"git switch -c {branch}"
            }

    # Pull latest (if branch exists on remote)
    run_command(["git", "pull", "--ff-only", "origin", branch], cwd=str(repo_path))

    # Create workspace files
    plan_path = workspace / "plan.md"
    review_notes_path = workspace / "review-notes.md"

    # Get current date for templates
    today = datetime.now().strftime("%Y-%m-%d")

    # Create plan.md with basic structure
    if not plan_path.exists():
        plan_content = f"""# Plan

## Status: PENDING
## Branch: {branch}
## Repository: {repo_url}

---

## Objective

_Describe the objective here_

---

## Tasks

_Tasks will be added here_

---

## Notes

- Created: {today}
- Last Updated: {today}
"""
        plan_path.write_text(plan_content)
        logger.debug(f"init_workspace: Created {plan_path}")

    # Create review-notes.md
    if not review_notes_path.exists():
        review_notes_content = f"""# Review Notes

## Branch: {branch}

---

## Log

_Review entries will be added here_

---

## Created: {today}
"""
        review_notes_path.write_text(review_notes_content)
        logger.debug(f"init_workspace: Created {review_notes_path}")

    logger.info(f"init_workspace: Workspace initialized successfully at {workspace}")
    return {
        "success": True,
        "workspace": str(workspace),
        "repo_path": str(repo_path),
        "branch": branch,
        "files_created": ["plan.md", "review-notes.md"],
        "message": f"Workspace initialized successfully at {workspace}"
    }


def workspace_status(workspace_path: str = ".") -> dict:
    """
    Get the current status of the workspace.

    Args:
        workspace_path: Path to the workspace

    Returns:
        dict with workspace status details
    """
    # Validate inputs
    try:
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    repo_path = workspace / "repo"

    status = {
        "workspace": str(workspace),
        "exists": workspace.exists(),
        "repo_exists": repo_path.exists(),
        "tasks": [],
        "files": {}
    }

    if not workspace.exists():
        status["error"] = "Workspace does not exist"
        return status

    # Check workspace files
    for filename in ["plan.md", "review-notes.md"]:
        filepath = workspace / filename
        status["files"][filename] = {
            "exists": filepath.exists(),
            "size": filepath.stat().st_size if filepath.exists() else 0
        }

    # Get repo status
    if repo_path.exists():
        returncode, stdout, stderr = run_command(
            ["git", "branch", "--show-current"],
            cwd=str(repo_path)
        )
        status["current_branch"] = stdout.strip() if returncode == 0 else "unknown"

        # Get worktree list
        returncode, stdout, stderr = run_command(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(repo_path)
        )

        if returncode == 0:
            worktrees = []
            current_wt = {}
            for line in stdout.strip().split("\n"):
                if line.startswith("worktree "):
                    if current_wt:
                        worktrees.append(current_wt)
                    current_wt = {"path": line[9:]}
                elif line.startswith("HEAD "):
                    current_wt["head"] = line[5:]
                elif line.startswith("branch "):
                    current_wt["branch"] = line[7:]
            if current_wt:
                worktrees.append(current_wt)
            status["worktrees"] = worktrees

    # Find task folders
    for item in workspace.iterdir():
        if item.is_dir() and item.name.startswith("task-"):
            task_name = item.name[5:]  # Remove "task-" prefix
            task_info = {
                "name": task_name,
                "folder": str(item),
                "has_worktree": (item / "worktree").exists(),
                "has_spec": (item / "spec.md").exists(),
                "has_feedback": (item / "feedback.md").exists(),
                "has_results": (item / "results.md").exists()
            }

            # Get worktree status if exists
            worktree_path = item / "worktree"
            if worktree_path.exists():
                returncode, stdout, stderr = run_command(
                    ["git", "branch", "--show-current"],
                    cwd=str(worktree_path)
                )
                task_info["branch"] = stdout.strip() if returncode == 0 else "unknown"

                # Get commit count ahead of main
                returncode, stdout, stderr = run_command(
                    ["git", "status", "--porcelain"],
                    cwd=str(worktree_path)
                )
                task_info["uncommitted_changes"] = len(stdout.strip().split("\n")) if stdout.strip() else 0

            status["tasks"].append(task_info)

    return status


def cleanup_workspace(workspace_path: str = ".", remove_repo: bool = False) -> dict:
    """
    Clean up workspace: remove all worktrees and optionally the repo.

    Args:
        workspace_path: Path to the workspace
        remove_repo: If True, also remove the cloned repo

    Returns:
        dict with cleanup results
    """
    # Validate inputs
    try:
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    repo_path = workspace / "repo"

    results = {
        "success": True,
        "worktrees_removed": [],
        "branches_deleted": [],
        "errors": []
    }

    if not repo_path.exists():
        logger.warning(f"cleanup_workspace: Repository not found at {repo_path}")
        results["error"] = "Repository not found"
        results["success"] = False
        return results

    logger.info(f"cleanup_workspace: Starting cleanup of {workspace}")

    # Find and remove all task worktrees
    for item in workspace.iterdir():
        if item.is_dir() and item.name.startswith("task-"):
            worktree_path = item / "worktree"
            if worktree_path.exists():
                # Get branch name before removing
                returncode, stdout, stderr = run_command(
                    ["git", "branch", "--show-current"],
                    cwd=str(worktree_path)
                )
                branch_name = stdout.strip() if returncode == 0 else None

                # Remove worktree
                logger.debug(f"cleanup_workspace: Removing worktree {worktree_path}")
                returncode, stdout, stderr = run_command(
                    ["git", "worktree", "remove", str(worktree_path), "--force"],
                    cwd=str(repo_path)
                )

                if returncode == 0:
                    results["worktrees_removed"].append(str(worktree_path))
                    logger.info(f"cleanup_workspace: Removed worktree {worktree_path}")

                    # Delete the branch
                    if branch_name:
                        returncode, stdout, stderr = run_command(
                            ["git", "branch", "-D", branch_name],
                            cwd=str(repo_path)
                        )
                        if returncode == 0:
                            results["branches_deleted"].append(branch_name)
                            logger.info(f"cleanup_workspace: Deleted branch {branch_name}")
                else:
                    logger.error(f"cleanup_workspace: Failed to remove {worktree_path}: {stderr}")
                    results["errors"].append(f"Failed to remove {worktree_path}: {stderr}")

    # Optionally remove the repo
    if remove_repo:
        import shutil
        try:
            shutil.rmtree(repo_path)
            results["repo_removed"] = True
            logger.info(f"cleanup_workspace: Removed repository at {repo_path}")
        except Exception as e:
            logger.error(f"cleanup_workspace: Failed to remove repo: {e}")
            results["errors"].append(f"Failed to remove repo: {e}")
            results["success"] = False

    if results["errors"]:
        results["success"] = False
        logger.warning(f"cleanup_workspace: Completed with {len(results['errors'])} errors")
    else:
        logger.info(f"cleanup_workspace: Completed successfully, removed {len(results['worktrees_removed'])} worktrees")

    return results


def print_status(workspace_path: str = "."):
    """Print workspace status in a human-readable format."""
    status = workspace_status(workspace_path)

    print(f"\n{'='*60}")
    print(f"WORKSPACE STATUS")
    print(f"{'='*60}")
    print(f"Path: {status['workspace']}")
    print(f"Repo exists: {status['repo_exists']}")

    if status.get('current_branch'):
        print(f"Current branch: {status['current_branch']}")

    print(f"\n{'─'*60}")
    print("FILES:")
    for filename, info in status.get('files', {}).items():
        exists = "✓" if info['exists'] else "✗"
        print(f"  {exists} {filename}")

    print(f"\n{'─'*60}")
    print("TASKS:")
    if status.get('tasks'):
        for task in status['tasks']:
            wt = "✓" if task['has_worktree'] else "✗"
            print(f"  [{wt}] {task['name']}")
            if task['has_worktree']:
                print(f"      Branch: {task.get('branch', 'unknown')}")
                print(f"      Uncommitted: {task.get('uncommitted_changes', 0)}")
    else:
        print("  No tasks created yet")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Workspace management tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize workspace")
    init_parser.add_argument("repo_url", help="Git repository URL")
    init_parser.add_argument("branch", help="Branch to checkout")
    init_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    # status command
    status_parser = subparsers.add_parser("status", help="Show workspace status")
    status_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up workspace")
    cleanup_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    cleanup_parser.add_argument("--remove-repo", action="store_true", help="Also remove the repo")

    args = parser.parse_args()

    if args.command == "init":
        result = init_workspace(args.repo_url, args.branch, args.workspace)
        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ Error: {result['error']}")
            sys.exit(1)

    elif args.command == "status":
        print_status(args.workspace)

    elif args.command == "cleanup":
        result = cleanup_workspace(args.workspace, args.remove_repo)
        if result["success"]:
            print(f"✓ Cleanup complete")
            print(f"  Worktrees removed: {len(result['worktrees_removed'])}")
            print(f"  Branches deleted: {len(result['branches_deleted'])}")
        else:
            print(f"✗ Cleanup had errors:")
            for error in result["errors"]:
                print(f"  - {error}")
            sys.exit(1)

    else:
        parser.print_help()
