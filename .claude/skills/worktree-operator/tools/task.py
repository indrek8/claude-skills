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
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass, field

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

# Import locking utilities
from locking import workspace_lock, LockError

# Import logging utilities
from logging_config import get_logger

# Import plan parser for dependency checking
from plan_parser import check_dependencies

# Import error utilities
from errors import (
    make_error,
    repo_not_found_error,
    task_exists_error,
    task_not_found_error,
    worktree_not_found_error,
    worktree_create_failed_error,
    rebase_conflict_error,
    tests_failed_error,
    push_failed_error,
)

# Module logger
logger = get_logger("task")


def run_command(cmd: list[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


@dataclass
class TransactionStep:
    """Represents a step in a transaction with its rollback action."""
    name: str
    rollback_fn: Optional[Callable[[], bool]] = None
    completed: bool = False
    error: Optional[str] = None


class AcceptTransaction:
    """
    Manages transactional accept with full rollback capability.

    Tracks all operations and can roll back on any failure to restore
    the workspace to its original state.
    """

    def __init__(
        self,
        repo_path: Path,
        worktree_path: Path,
        task_dir: Path,
        main_branch: str,
        sub_branch: str
    ):
        self.repo_path = repo_path
        self.worktree_path = worktree_path
        self.task_dir = task_dir
        self.main_branch = main_branch
        self.sub_branch = sub_branch

        self.steps: List[TransactionStep] = []
        self.original_main_sha: Optional[str] = None
        self.original_worktree_sha: Optional[str] = None
        self.original_branch_in_repo: Optional[str] = None
        self.rolled_back: bool = False
        self.log: List[str] = []

    def checkpoint(self) -> bool:
        """
        Save the current state for potential rollback.

        Returns:
            True if checkpoint was successful
        """
        # Get current commit SHA on main branch
        returncode, stdout, _ = run_command(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.repo_path)
        )
        if returncode == 0:
            self.original_main_sha = stdout.strip()

        # Get current commit SHA on worktree
        if self.worktree_path.exists():
            returncode, stdout, _ = run_command(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.worktree_path)
            )
            if returncode == 0:
                self.original_worktree_sha = stdout.strip()

        # Get current branch in repo
        returncode, stdout, _ = run_command(
            ["git", "branch", "--show-current"],
            cwd=str(self.repo_path)
        )
        if returncode == 0:
            self.original_branch_in_repo = stdout.strip()

        self._log(f"Checkpoint: main@{self.original_main_sha[:8] if self.original_main_sha else 'unknown'}, "
                  f"worktree@{self.original_worktree_sha[:8] if self.original_worktree_sha else 'unknown'}")

        return self.original_main_sha is not None

    def add_step(self, name: str, rollback_fn: Optional[Callable[[], bool]] = None) -> TransactionStep:
        """Add a step to the transaction."""
        step = TransactionStep(name=name, rollback_fn=rollback_fn)
        self.steps.append(step)
        self._log(f"Step: {name}")
        return step

    def complete_step(self, step: TransactionStep):
        """Mark a step as completed."""
        step.completed = True
        self._log(f"✓ Completed: {step.name}")

    def fail_step(self, step: TransactionStep, error: str):
        """Mark a step as failed."""
        step.error = error
        self._log(f"✗ Failed: {step.name} - {error}")

    def rollback(self) -> dict:
        """
        Roll back all completed steps in reverse order.

        Returns:
            dict with rollback results
        """
        if self.rolled_back:
            return {"success": True, "message": "Already rolled back"}

        self._log("Starting rollback...")
        rollback_errors = []

        # Rollback steps in reverse order
        for step in reversed(self.steps):
            if step.completed and step.rollback_fn:
                self._log(f"Rolling back: {step.name}")
                try:
                    success = step.rollback_fn()
                    if not success:
                        rollback_errors.append(f"Failed to rollback: {step.name}")
                except Exception as e:
                    rollback_errors.append(f"Error rolling back {step.name}: {str(e)}")

        # Always try to restore repo to original branch
        if self.original_branch_in_repo:
            returncode, _, stderr = run_command(
                ["git", "switch", self.original_branch_in_repo],
                cwd=str(self.repo_path)
            )
            if returncode != 0:
                self._log(f"Warning: Could not restore original branch: {stderr}")

        # If main branch was modified, try to restore it
        if self.original_main_sha:
            # Check current state
            returncode, stdout, _ = run_command(
                ["git", "rev-parse", self.main_branch],
                cwd=str(self.repo_path)
            )
            current_sha = stdout.strip() if returncode == 0 else None

            if current_sha and current_sha != self.original_main_sha:
                self._log(f"Restoring main branch to {self.original_main_sha[:8]}")
                run_command(
                    ["git", "update-ref", f"refs/heads/{self.main_branch}", self.original_main_sha],
                    cwd=str(self.repo_path)
                )

        self.rolled_back = True
        self._log("Rollback complete")

        return {
            "success": len(rollback_errors) == 0,
            "errors": rollback_errors,
            "log": self.log
        }

    def _log(self, message: str):
        """Add a message to the transaction log."""
        self.log.append(message)


def create_task(
    ticket: str,
    task_name: str,
    main_branch: str,
    workspace_path: str = ".",
    spec_content: Optional[str] = None
) -> dict:
    """
    Create a new task with folder structure and git worktree.

    This operation acquires a workspace lock to prevent race conditions
    when creating multiple tasks concurrently.

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
        return repo_not_found_error(str(repo_path))

    # Acquire workspace lock to prevent race conditions
    try:
        with workspace_lock(str(workspace), f"create_task:{task_name}"):
            # Check if task already exists (inside lock to prevent race)
            if task_dir.exists():
                return task_exists_error(task_name, str(task_dir))

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
                return worktree_create_failed_error(str(worktree_path), sub_branch, stderr)

            return {
                "success": True,
                "task_dir": str(task_dir),
                "worktree_path": str(worktree_path),
                "branch": sub_branch,
                "based_on": main_branch,
                "files_created": ["spec.md", "feedback.md", "results.md"],
                "message": f"Task '{task_name}' created successfully"
            }

    except LockError as e:
        return e.to_dict()


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
        return worktree_not_found_error(task_name, str(worktree_path))

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
            result = rebase_conflict_error(task_name, main_branch)
            result["conflicts"] = True
            result["stderr"] = stderr
            return result
        return make_error(
            f"Rebase failed: {stderr}",
            hint="Check the git error message and resolve any issues.",
            recovery_options=[
                f"Check worktree status: cd {worktree_path} && git status",
                "Abort any in-progress rebase: git rebase --abort",
                f"Reset to start over: operator reset {task_name}"
            ],
            error_code="REBASE_FAILED",
            task_name=task_name,
            main_branch=main_branch
        )

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
        return worktree_not_found_error(task_name, str(worktree_path))

    # Fetch latest
    run_command(["git", "fetch", "origin"], cwd=str(worktree_path))

    # Hard reset to main branch
    returncode, stdout, stderr = run_command(
        ["git", "reset", "--hard", main_branch],
        cwd=str(worktree_path)
    )

    if returncode != 0:
        return make_error(
            f"Reset failed: {stderr}",
            hint="Git reset encountered an issue.",
            recovery_options=[
                f"Check the branch exists: git branch -a | grep {main_branch}",
                "Try manual reset: git reset --hard HEAD",
                "Check for uncommitted changes: git status"
            ],
            error_code="RESET_FAILED",
            task_name=task_name,
            main_branch=main_branch
        )

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

    This function is fully transactional - on any failure, all changes
    are rolled back to restore the workspace to its original state.

    This operation acquires a workspace lock to prevent race conditions
    with other operations (create, sync, etc.).

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

    if not worktree_path.exists():
        return worktree_not_found_error(task_name, str(worktree_path))

    # Acquire workspace lock for the entire accept operation
    try:
        with workspace_lock(str(workspace), f"accept_task:{task_name}"):
            return _accept_task_locked(
                ticket, task_name, main_branch, workspace, repo_path,
                task_dir, worktree_path, sub_branch, push, delete_remote_branch
            )
    except LockError as e:
        return e.to_dict()


def _accept_task_locked(
    ticket: str,
    task_name: str,
    main_branch: str,
    workspace: Path,
    repo_path: Path,
    task_dir: Path,
    worktree_path: Path,
    sub_branch: str,
    push: bool,
    delete_remote_branch: bool
) -> dict:
    """
    Internal implementation of accept_task, called with lock held.
    """
    results = {
        "success": True,
        "steps": [],
        "errors": [],
        "transactional": True
    }

    # Initialize transaction
    txn = AcceptTransaction(
        repo_path=repo_path,
        worktree_path=worktree_path,
        task_dir=task_dir,
        main_branch=main_branch,
        sub_branch=sub_branch
    )

    # Checkpoint current state
    if not txn.checkpoint():
        return make_error(
            "Failed to checkpoint current state",
            hint="Ensure the repo is in a valid git state.",
            recovery_options=[
                "Check git status in the repo: git status",
                "Ensure you're on a valid branch: git branch --show-current",
                "Try running: git fsck"
            ],
            error_code="CHECKPOINT_FAILED"
        )

    # Helper to handle failure with rollback
    def fail_with_rollback(error_msg: str, step: TransactionStep = None, hint: str = None):
        if step:
            txn.fail_step(step, error_msg)
        results["success"] = False
        results["errors"].append(error_msg)

        # Rollback all completed steps
        rollback_result = txn.rollback()
        results["rolled_back"] = True
        results["rollback_success"] = rollback_result["success"]
        if not rollback_result["success"]:
            results["rollback_errors"] = rollback_result["errors"]

        results["transaction_log"] = txn.log
        if hint:
            results["hint"] = hint
        return results

    # Step 1: Rebase sub-branch onto main
    step1 = txn.add_step("Rebase sub-branch")
    results["steps"].append("Rebasing sub-branch...")

    # Create rollback function for rebase (abort if in progress, or reset to original)
    def rollback_rebase() -> bool:
        # Check if rebase is in progress
        rebase_dir = worktree_path / ".git" / "rebase-merge"
        if rebase_dir.exists() or (worktree_path / ".git" / "rebase-apply").exists():
            run_command(["git", "rebase", "--abort"], cwd=str(worktree_path))
        # Reset to original state
        if txn.original_worktree_sha:
            run_command(["git", "reset", "--hard", txn.original_worktree_sha], cwd=str(worktree_path))
        return True

    step1.rollback_fn = rollback_rebase

    sync_result = sync_task(task_name, main_branch, str(workspace))
    if not sync_result["success"]:
        return fail_with_rollback(
            f"Rebase failed: {sync_result.get('error')}",
            step1,
            sync_result.get('hint')
        )
    txn.complete_step(step1)
    results["steps"].append("✓ Rebase complete")

    # Step 1.5: Verify tests pass after rebase
    step1_5 = txn.add_step("Test after rebase")
    step1_5.rollback_fn = rollback_rebase  # Same rollback as rebase
    results["steps"].append("Running tests after rebase...")

    test_result = verify_tests_pass(str(worktree_path), workspace_path=str(workspace))
    if not test_result["passed"]:
        results["test_output"] = test_result
        return fail_with_rollback(
            f"Tests failed after rebase: {test_result.get('error', 'Unknown error')}",
            step1_5,
            "Fix test failures in the worktree before accepting"
        )
    txn.complete_step(step1_5)
    results["steps"].append(f"✓ Tests passed ({test_result.get('duration', '?')}s)")
    results["test_after_rebase"] = test_result

    # Step 2: Switch to main branch in repo
    step2 = txn.add_step("Switch to main branch")

    def rollback_switch() -> bool:
        if txn.original_branch_in_repo:
            returncode, _, _ = run_command(
                ["git", "switch", txn.original_branch_in_repo],
                cwd=str(repo_path)
            )
            return returncode == 0
        return True

    step2.rollback_fn = rollback_switch
    results["steps"].append("Switching to main branch...")

    returncode, stdout, stderr = run_command(
        ["git", "switch", main_branch],
        cwd=str(repo_path)
    )
    if returncode != 0:
        return fail_with_rollback(f"Failed to switch branch: {stderr}", step2)
    txn.complete_step(step2)
    results["steps"].append("✓ Switched to main branch")

    # Step 3: Merge with --no-ff
    step3 = txn.add_step("Merge sub-branch")

    def rollback_merge() -> bool:
        # Reset main branch to original SHA
        if txn.original_main_sha:
            returncode, _, _ = run_command(
                ["git", "reset", "--hard", txn.original_main_sha],
                cwd=str(repo_path)
            )
            return returncode == 0
        return True

    step3.rollback_fn = rollback_merge
    results["steps"].append("Merging sub-branch...")

    # Try to get first line of spec for commit message
    spec_path = task_dir / "spec.md"
    merge_msg = f"Merge {task_name}"
    if spec_path.exists():
        lines = spec_path.read_text().split("\n")
        for line in lines:
            if line.startswith("## Objective"):
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
        return fail_with_rollback(f"Merge failed: {stderr}", step3)
    txn.complete_step(step3)
    results["steps"].append("✓ Merge complete")
    results["merge_commit"] = merge_msg

    # Step 3.5: Verify tests pass after merge
    step3_5 = txn.add_step("Test after merge")
    step3_5.rollback_fn = rollback_merge  # Same rollback as merge
    results["steps"].append("Running tests after merge...")

    test_result = verify_tests_pass(str(repo_path), workspace_path=str(workspace))
    if not test_result["passed"]:
        results["test_output"] = test_result
        return fail_with_rollback(
            f"Tests failed after merge: {test_result.get('error', 'Unknown error')}",
            step3_5,
            "Tests failed after merge. Fix and try again."
        )
    txn.complete_step(step3_5)
    results["steps"].append(f"✓ Tests passed after merge ({test_result.get('duration', '?')}s)")
    results["test_after_merge"] = test_result

    # Step 4: Push (optional)
    # Note: Push is a point of no return - we don't rollback after push succeeds
    if push:
        step4 = txn.add_step("Push to origin")
        # No rollback for push - it's a point of no return
        # But we can still fail before completing the step
        results["steps"].append("Pushing main branch...")

        returncode, stdout, stderr = run_command(
            ["git", "push", "origin", main_branch],
            cwd=str(repo_path)
        )
        if returncode != 0:
            # Push failed - rollback everything
            return fail_with_rollback(
                f"Push failed: {stderr}",
                step4,
                "Push to origin failed. Local changes have been rolled back."
            )
        txn.complete_step(step4)
        results["steps"].append("✓ Pushed to origin")

    # === POINT OF NO RETURN ===
    # After push, we commit to cleanup. Cleanup failures are non-fatal.
    results["point_of_no_return"] = True

    # Step 5: Remove worktree
    results["steps"].append("Removing worktree...")
    returncode, stdout, stderr = run_command(
        ["git", "worktree", "remove", str(worktree_path)],
        cwd=str(repo_path)
    )
    if returncode != 0:
        # Try force remove
        returncode, _, _ = run_command(
            ["git", "worktree", "remove", str(worktree_path), "--force"],
            cwd=str(repo_path)
        )
        if returncode != 0:
            results["errors"].append(f"Warning: Could not remove worktree (non-fatal)")
        else:
            results["steps"].append("✓ Worktree removed (forced)")
    else:
        results["steps"].append("✓ Worktree removed")

    # Step 6: Delete local branch
    results["steps"].append("Deleting local branch...")
    returncode, stdout, stderr = run_command(
        ["git", "branch", "-d", sub_branch],
        cwd=str(repo_path)
    )
    if returncode != 0:
        # Force delete if needed
        returncode, _, _ = run_command(
            ["git", "branch", "-D", sub_branch],
            cwd=str(repo_path)
        )
        if returncode != 0:
            results["errors"].append(f"Warning: Could not delete local branch (non-fatal)")
        else:
            results["steps"].append("✓ Local branch deleted (forced)")
    else:
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
    results["transaction_log"] = txn.log
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
        return task_not_found_error(task_name, str(task_dir))

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
