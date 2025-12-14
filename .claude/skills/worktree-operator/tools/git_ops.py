#!/usr/bin/env python3
"""
Git operations tools for the operator skill.

Low-level git operations: rebase, merge, branch management, worktree sync.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, List

# Import shared validation utilities
from validation import (
    ValidationError,
    validate_branch_name,
    validate_path,
)

# Import locking utilities
from locking import workspace_lock, LockError

# Import logging utilities
from logging_config import get_logger

# Import conflict resolution utilities
from conflict_resolver import (
    detect_conflicts,
    resolve_all,
    resolve_file,
    abort_rebase,
    continue_rebase,
    format_conflict_report,
    is_rebase_in_progress,
)

# Import error utilities
from errors import (
    make_error,
    rebase_conflict_error,
    merge_conflict_error,
    checkout_failed_error,
    push_failed_error,
)

# Module logger
logger = get_logger("git_ops")


def run_command(cmd: list[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def get_current_branch(repo_path: str) -> Optional[str]:
    """Get the current branch name."""
    returncode, stdout, stderr = run_command(
        ["git", "branch", "--show-current"],
        cwd=repo_path
    )
    return stdout.strip() if returncode == 0 else None


def get_commits_between(repo_path: str, base: str, head: str) -> List[dict]:
    """Get list of commits between base and head."""
    returncode, stdout, stderr = run_command(
        ["git", "log", f"{base}..{head}", "--format=%H|%h|%s|%an|%ar"],
        cwd=repo_path
    )

    if returncode != 0 or not stdout.strip():
        return []

    commits = []
    for line in stdout.strip().split("\n"):
        parts = line.split("|")
        if len(parts) >= 5:
            commits.append({
                "hash": parts[0],
                "short_hash": parts[1],
                "subject": parts[2],
                "author": parts[3],
                "relative_time": parts[4]
            })
    return commits


def get_diff_stats(repo_path: str, base: str, head: str) -> dict:
    """Get diff statistics between base and head."""
    returncode, stdout, stderr = run_command(
        ["git", "diff", "--stat", f"{base}..{head}"],
        cwd=repo_path
    )

    stats = {
        "raw": stdout.strip() if returncode == 0 else "",
        "files_changed": 0,
        "insertions": 0,
        "deletions": 0
    }

    if returncode == 0 and stdout.strip():
        # Parse the summary line (last line)
        lines = stdout.strip().split("\n")
        if lines:
            summary = lines[-1]
            # Parse "X files changed, Y insertions(+), Z deletions(-)"
            import re
            files_match = re.search(r"(\d+) files? changed", summary)
            ins_match = re.search(r"(\d+) insertions?", summary)
            del_match = re.search(r"(\d+) deletions?", summary)

            if files_match:
                stats["files_changed"] = int(files_match.group(1))
            if ins_match:
                stats["insertions"] = int(ins_match.group(1))
            if del_match:
                stats["deletions"] = int(del_match.group(1))

    return stats


def rebase_branch(
    worktree_path: str,
    target_branch: str,
    abort_on_conflict: bool = False
) -> dict:
    """
    Rebase the current branch onto target_branch.

    Args:
        worktree_path: Path to the worktree
        target_branch: Branch to rebase onto
        abort_on_conflict: If True, abort rebase on conflict

    Returns:
        dict with rebase results
    """
    # Fetch first
    run_command(["git", "fetch", "origin"], cwd=worktree_path)

    # Get current branch
    current = get_current_branch(worktree_path)

    # Perform rebase
    returncode, stdout, stderr = run_command(
        ["git", "rebase", target_branch],
        cwd=worktree_path
    )

    if returncode != 0:
        has_conflicts = "CONFLICT" in stderr or "conflict" in stdout.lower()

        if has_conflicts and abort_on_conflict:
            run_command(["git", "rebase", "--abort"], cwd=worktree_path)
            result = make_error(
                "Rebase had conflicts and was aborted",
                hint="The rebase was automatically aborted due to conflicts.",
                recovery_options=[
                    "Review the conflicting files manually",
                    "Rebase again without abort_on_conflict to resolve interactively",
                    "Check which commits have conflicts: git log --oneline"
                ],
                error_code="REBASE_CONFLICT_ABORTED"
            )
            result["conflicts"] = True
            result["aborted"] = True
            return result

        result = make_error(
            f"Rebase failed: {stderr}",
            hint="Resolve conflicts manually or abort the rebase.",
            recovery_options=[
                "Resolve conflicts, then run: git rebase --continue",
                "To abort rebase: git rebase --abort",
                "Check status: git status"
            ],
            error_code="REBASE_FAILED",
            target_branch=target_branch
        )
        result["conflicts"] = has_conflicts
        return result

    return {
        "success": True,
        "branch": current,
        "rebased_onto": target_branch,
        "message": f"Successfully rebased {current} onto {target_branch}"
    }


def merge_branch(
    repo_path: str,
    source_branch: str,
    target_branch: str,
    message: Optional[str] = None,
    no_ff: bool = True
) -> dict:
    """
    Merge source_branch into target_branch.

    Args:
        repo_path: Path to the repository
        source_branch: Branch to merge from
        target_branch: Branch to merge into
        message: Merge commit message
        no_ff: If True, always create a merge commit (--no-ff)

    Returns:
        dict with merge results
    """
    # Switch to target branch
    returncode, stdout, stderr = run_command(
        ["git", "switch", target_branch],
        cwd=repo_path
    )

    if returncode != 0:
        return checkout_failed_error(target_branch, stderr)

    # Build merge command
    merge_cmd = ["git", "merge"]
    if no_ff:
        merge_cmd.append("--no-ff")
    merge_cmd.append(source_branch)
    if message:
        merge_cmd.extend(["-m", message])

    returncode, stdout, stderr = run_command(merge_cmd, cwd=repo_path)

    if returncode != 0:
        has_conflicts = "CONFLICT" in stderr or "conflict" in stdout.lower()
        if has_conflicts:
            result = merge_conflict_error(source_branch, target_branch)
            result["conflicts"] = True
            return result
        return make_error(
            f"Merge failed: {stderr}",
            hint="Check the git error message for details.",
            recovery_options=[
                "Check status: git status",
                "Abort merge: git merge --abort",
                "Check if branches exist: git branch -a"
            ],
            error_code="MERGE_FAILED",
            source_branch=source_branch,
            target_branch=target_branch
        )

    return {
        "success": True,
        "source": source_branch,
        "target": target_branch,
        "message": f"Successfully merged {source_branch} into {target_branch}"
    }


def delete_branch(
    repo_path: str,
    branch_name: str,
    force: bool = False,
    delete_remote: bool = False
) -> dict:
    """
    Delete a git branch (local and optionally remote).

    Args:
        repo_path: Path to the repository
        branch_name: Branch to delete
        force: If True, force delete even if not merged
        delete_remote: If True, also delete from remote

    Returns:
        dict with deletion results
    """
    results = {
        "success": True,
        "local_deleted": False,
        "remote_deleted": False,
        "errors": []
    }

    # Delete local branch
    flag = "-D" if force else "-d"
    returncode, stdout, stderr = run_command(
        ["git", "branch", flag, branch_name],
        cwd=repo_path
    )

    if returncode == 0:
        results["local_deleted"] = True
    else:
        results["errors"].append(f"Local delete failed: {stderr}")

    # Delete remote branch
    if delete_remote:
        returncode, stdout, stderr = run_command(
            ["git", "push", "origin", "--delete", branch_name],
            cwd=repo_path
        )

        if returncode == 0:
            results["remote_deleted"] = True
        else:
            # Not a critical error - branch may not exist on remote
            results["errors"].append(f"Remote delete: {stderr.strip()}")

    results["success"] = results["local_deleted"]
    return results


def sync_all_worktrees(
    workspace_path: str,
    main_branch: str
) -> dict:
    """
    Rebase all active worktrees onto the main branch.

    This operation acquires a workspace lock to prevent race conditions
    with other operations (create, accept, etc.).

    Args:
        workspace_path: Path to workspace
        main_branch: Branch to rebase onto

    Returns:
        dict with sync results for each worktree
    """
    workspace = Path(workspace_path).resolve()

    # Acquire workspace lock for the entire sync operation
    try:
        with workspace_lock(str(workspace), "sync_all_worktrees"):
            return _sync_all_worktrees_locked(workspace, main_branch)
    except LockError as e:
        return e.to_dict()


def _sync_all_worktrees_locked(workspace: Path, main_branch: str) -> dict:
    """
    Internal implementation of sync_all_worktrees, called with lock held.
    """
    results = {
        "success": True,
        "synced": [],
        "failed": [],
        "skipped": []
    }

    # Find all task folders with worktrees
    for item in sorted(workspace.iterdir()):
        if item.is_dir() and item.name.startswith("task-"):
            task_name = item.name[5:]
            worktree_path = item / "worktree"

            if not worktree_path.exists():
                results["skipped"].append({
                    "task": task_name,
                    "reason": "No worktree"
                })
                continue

            # Rebase this worktree
            rebase_result = rebase_branch(
                str(worktree_path),
                main_branch,
                abort_on_conflict=True
            )

            if rebase_result["success"]:
                results["synced"].append({
                    "task": task_name,
                    "branch": rebase_result.get("branch")
                })
            else:
                results["failed"].append({
                    "task": task_name,
                    "error": rebase_result.get("error"),
                    "conflicts": rebase_result.get("conflicts", False)
                })
                results["success"] = False

    return results


def get_worktree_list(repo_path: str) -> List[dict]:
    """
    Get list of all worktrees.

    Args:
        repo_path: Path to repository

    Returns:
        List of worktree info dicts
    """
    returncode, stdout, stderr = run_command(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_path
    )

    if returncode != 0:
        return []

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
            current_wt["branch"] = line[7:].replace("refs/heads/", "")
        elif line == "bare":
            current_wt["bare"] = True
        elif line == "detached":
            current_wt["detached"] = True

    if current_wt:
        worktrees.append(current_wt)

    return worktrees


def remove_worktree(repo_path: str, worktree_path: str, force: bool = False) -> dict:
    """
    Remove a worktree.

    Args:
        repo_path: Path to main repository
        worktree_path: Path to worktree to remove
        force: If True, force remove even with uncommitted changes

    Returns:
        dict with removal result
    """
    cmd = ["git", "worktree", "remove", worktree_path]
    if force:
        cmd.append("--force")

    returncode, stdout, stderr = run_command(cmd, cwd=repo_path)

    if returncode != 0:
        return make_error(
            f"Failed to remove worktree: {stderr.strip()}",
            hint="The worktree may have uncommitted changes or be in use.",
            recovery_options=[
                f"Force remove: git worktree remove {worktree_path} --force",
                "Check for uncommitted changes in the worktree",
                "Ensure no processes are using the worktree"
            ],
            error_code="WORKTREE_REMOVE_FAILED",
            worktree_path=worktree_path
        )

    return {
        "success": True,
        "removed": worktree_path
    }


def push_branch(repo_path: str, branch: str, remote: str = "origin") -> dict:
    """
    Push a branch to remote.

    Args:
        repo_path: Path to repository
        branch: Branch to push
        remote: Remote name

    Returns:
        dict with push result
    """
    returncode, stdout, stderr = run_command(
        ["git", "push", remote, branch],
        cwd=repo_path
    )

    if returncode != 0:
        return push_failed_error(branch, stderr.strip())

    return {
        "success": True,
        "branch": branch,
        "remote": remote
    }


def print_diff_summary(repo_path: str, base: str, head: str):
    """Print a summary of changes between base and head."""
    commits = get_commits_between(repo_path, base, head)
    stats = get_diff_stats(repo_path, base, head)

    print(f"\n{'='*60}")
    print(f"DIFF: {base}..{head}")
    print(f"{'='*60}")

    print(f"\nStats:")
    print(f"  Files changed: {stats['files_changed']}")
    print(f"  Insertions: +{stats['insertions']}")
    print(f"  Deletions: -{stats['deletions']}")

    print(f"\nCommits ({len(commits)}):")
    for commit in commits[:10]:  # Show first 10
        print(f"  {commit['short_hash']} {commit['subject'][:50]}")

    if len(commits) > 10:
        print(f"  ... and {len(commits) - 10} more")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Git operations tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # rebase command
    rebase_parser = subparsers.add_parser("rebase", help="Rebase branch")
    rebase_parser.add_argument("worktree_path", help="Path to worktree")
    rebase_parser.add_argument("target_branch", help="Branch to rebase onto")
    rebase_parser.add_argument("--abort-on-conflict", action="store_true")

    # merge command
    merge_parser = subparsers.add_parser("merge", help="Merge branches")
    merge_parser.add_argument("repo_path", help="Path to repo")
    merge_parser.add_argument("source", help="Source branch")
    merge_parser.add_argument("target", help="Target branch")
    merge_parser.add_argument("--message", "-m", help="Merge message")
    merge_parser.add_argument("--ff", action="store_true", help="Allow fast-forward")

    # delete-branch command
    delete_parser = subparsers.add_parser("delete-branch", help="Delete branch")
    delete_parser.add_argument("repo_path", help="Path to repo")
    delete_parser.add_argument("branch", help="Branch to delete")
    delete_parser.add_argument("--force", "-f", action="store_true")
    delete_parser.add_argument("--remote", "-r", action="store_true")

    # sync-all command
    sync_parser = subparsers.add_parser("sync-all", help="Sync all worktrees")
    sync_parser.add_argument("workspace_path", help="Path to workspace")
    sync_parser.add_argument("main_branch", help="Branch to sync with")

    # worktrees command
    wt_parser = subparsers.add_parser("worktrees", help="List worktrees")
    wt_parser.add_argument("repo_path", help="Path to repo")

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Show diff summary")
    diff_parser.add_argument("repo_path", help="Path to repo")
    diff_parser.add_argument("base", help="Base ref")
    diff_parser.add_argument("head", help="Head ref")

    args = parser.parse_args()

    if args.command == "rebase":
        result = rebase_branch(
            args.worktree_path,
            args.target_branch,
            args.abort_on_conflict
        )
        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['error']}")
            sys.exit(1)

    elif args.command == "merge":
        result = merge_branch(
            args.repo_path,
            args.source,
            args.target,
            args.message,
            no_ff=not args.ff
        )
        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['error']}")
            sys.exit(1)

    elif args.command == "delete-branch":
        result = delete_branch(
            args.repo_path,
            args.branch,
            args.force,
            args.remote
        )
        if result["success"]:
            print(f"✓ Branch '{args.branch}' deleted")
        else:
            print(f"✗ Errors: {result['errors']}")
            sys.exit(1)

    elif args.command == "sync-all":
        result = sync_all_worktrees(args.workspace_path, args.main_branch)
        print(f"\n{'='*60}")
        print("SYNC ALL WORKTREES")
        print(f"{'='*60}")
        print(f"Synced: {len(result['synced'])}")
        for item in result['synced']:
            print(f"  ✓ {item['task']}")
        print(f"Failed: {len(result['failed'])}")
        for item in result['failed']:
            print(f"  ✗ {item['task']}: {item['error']}")
        print(f"Skipped: {len(result['skipped'])}")
        for item in result['skipped']:
            print(f"  - {item['task']}: {item['reason']}")
        if not result["success"]:
            sys.exit(1)

    elif args.command == "worktrees":
        worktrees = get_worktree_list(args.repo_path)
        print(f"\n{'='*60}")
        print("WORKTREES")
        print(f"{'='*60}")
        for wt in worktrees:
            branch = wt.get('branch', 'detached' if wt.get('detached') else 'unknown')
            print(f"  {wt['path']}")
            print(f"    Branch: {branch}")
        print(f"{'='*60}\n")

    elif args.command == "diff":
        print_diff_summary(args.repo_path, args.base, args.head)

    else:
        parser.print_help()
