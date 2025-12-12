#!/usr/bin/env python3
"""
Conflict detection and resolution utilities for the operator skill.

Provides tools to detect, display, and resolve git conflicts during rebase
or merge operations, with guided resolution options.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, List


def run_command(cmd: list[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def is_rebase_in_progress(worktree_path: str) -> bool:
    """Check if a rebase operation is currently in progress."""
    worktree = Path(worktree_path)
    git_dir = worktree / ".git"

    # .git might be a file pointing to the actual git dir for worktrees
    if git_dir.is_file():
        content = git_dir.read_text().strip()
        if content.startswith("gitdir:"):
            git_dir = Path(content[7:].strip())

    # Check for rebase-merge or rebase-apply directories
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def is_merge_in_progress(worktree_path: str) -> bool:
    """Check if a merge operation is currently in progress."""
    worktree = Path(worktree_path)
    git_dir = worktree / ".git"

    if git_dir.is_file():
        content = git_dir.read_text().strip()
        if content.startswith("gitdir:"):
            git_dir = Path(content[7:].strip())

    return (git_dir / "MERGE_HEAD").exists()


def get_conflicted_files(worktree_path: str) -> List[str]:
    """Get list of files with conflicts."""
    returncode, stdout, stderr = run_command(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=worktree_path
    )

    if returncode != 0 or not stdout.strip():
        return []

    return [f.strip() for f in stdout.strip().split("\n") if f.strip()]


def get_conflict_markers(worktree_path: str, file_path: str, max_lines: int = 20) -> dict:
    """
    Extract conflict markers and content from a file.

    Returns:
        {
            "conflict_count": int,
            "preview": str,  # First conflict preview
            "ours_preview": str,
            "theirs_preview": str
        }
    """
    full_path = Path(worktree_path) / file_path

    if not full_path.exists():
        return {
            "conflict_count": 0,
            "preview": "",
            "ours_preview": "",
            "theirs_preview": ""
        }

    try:
        content = full_path.read_text()
    except Exception:
        return {
            "conflict_count": 0,
            "preview": "(Could not read file)",
            "ours_preview": "",
            "theirs_preview": ""
        }

    lines = content.split("\n")
    conflict_count = 0
    preview_lines = []
    ours_lines = []
    theirs_lines = []

    in_conflict = False
    in_ours = False
    in_theirs = False
    first_conflict_captured = False

    for line in lines:
        if line.startswith("<<<<<<<"):
            conflict_count += 1
            in_conflict = True
            in_ours = True
            in_theirs = False
            if not first_conflict_captured:
                preview_lines.append(line)
        elif line.startswith("=======") and in_conflict:
            in_ours = False
            in_theirs = True
            if not first_conflict_captured:
                preview_lines.append(line)
        elif line.startswith(">>>>>>>") and in_conflict:
            in_conflict = False
            in_ours = False
            in_theirs = False
            if not first_conflict_captured:
                preview_lines.append(line)
                first_conflict_captured = True
        elif in_conflict and not first_conflict_captured:
            preview_lines.append(line)
            if in_ours:
                ours_lines.append(line)
            elif in_theirs:
                theirs_lines.append(line)

    # Truncate preview if too long
    if len(preview_lines) > max_lines:
        preview_lines = preview_lines[:max_lines]
        preview_lines.append("... (truncated)")

    return {
        "conflict_count": conflict_count,
        "preview": "\n".join(preview_lines),
        "ours_preview": "\n".join(ours_lines[:10]),
        "theirs_preview": "\n".join(theirs_lines[:10])
    }


def detect_conflicts(worktree_path: str) -> dict:
    """
    Detect conflicts in a worktree.

    Returns:
        {
            "has_conflicts": True/False,
            "operation": "rebase" | "merge" | None,
            "files": [
                {
                    "path": "src/file.py",
                    "conflict_count": 3,
                    "ours_preview": "...",
                    "theirs_preview": "...",
                    "conflict_preview": "first conflict block"
                }
            ]
        }
    """
    result = {
        "has_conflicts": False,
        "operation": None,
        "files": []
    }

    # Determine what operation is in progress
    if is_rebase_in_progress(worktree_path):
        result["operation"] = "rebase"
    elif is_merge_in_progress(worktree_path):
        result["operation"] = "merge"

    # Get conflicted files
    conflicted_files = get_conflicted_files(worktree_path)

    if not conflicted_files:
        return result

    result["has_conflicts"] = True

    for file_path in conflicted_files:
        markers = get_conflict_markers(worktree_path, file_path)
        result["files"].append({
            "path": file_path,
            "conflict_count": markers["conflict_count"],
            "ours_preview": markers["ours_preview"],
            "theirs_preview": markers["theirs_preview"],
            "conflict_preview": markers["preview"]
        })

    return result


def resolve_file(worktree_path: str, file_path: str, strategy: str) -> dict:
    """
    Resolve a single file conflict.

    Args:
        worktree_path: Path to the worktree
        file_path: Relative path to the conflicted file
        strategy: "ours" | "theirs" | "manual"

    Returns:
        {"success": True/False, "message": "..."}
    """
    if strategy not in ("ours", "theirs", "manual"):
        return {
            "success": False,
            "message": f"Invalid strategy: {strategy}. Must be 'ours', 'theirs', or 'manual'"
        }

    if strategy == "manual":
        return {
            "success": True,
            "message": f"File '{file_path}' left for manual resolution. Edit the file, then run: git add {file_path}"
        }

    # Use git checkout with --ours or --theirs
    returncode, stdout, stderr = run_command(
        ["git", "checkout", f"--{strategy}", file_path],
        cwd=worktree_path
    )

    if returncode != 0:
        return {
            "success": False,
            "message": f"Failed to resolve {file_path} with '{strategy}': {stderr}"
        }

    # Stage the resolved file
    returncode, stdout, stderr = run_command(
        ["git", "add", file_path],
        cwd=worktree_path
    )

    if returncode != 0:
        return {
            "success": False,
            "message": f"Failed to stage {file_path}: {stderr}"
        }

    strategy_desc = "your changes (HEAD)" if strategy == "ours" else "incoming changes"
    return {
        "success": True,
        "message": f"Resolved '{file_path}' using {strategy_desc}"
    }


def resolve_all(worktree_path: str, strategy: str) -> dict:
    """
    Resolve all conflicts with the same strategy.

    Args:
        worktree_path: Path to the worktree
        strategy: "ours" | "theirs"

    Returns:
        {"success": True/False, "resolved": [], "failed": [], "message": "..."}
    """
    if strategy not in ("ours", "theirs"):
        return {
            "success": False,
            "resolved": [],
            "failed": [],
            "message": f"Invalid strategy for resolve_all: {strategy}. Must be 'ours' or 'theirs'"
        }

    conflicted_files = get_conflicted_files(worktree_path)

    if not conflicted_files:
        return {
            "success": True,
            "resolved": [],
            "failed": [],
            "message": "No conflicts to resolve"
        }

    resolved = []
    failed = []

    for file_path in conflicted_files:
        result = resolve_file(worktree_path, file_path, strategy)
        if result["success"]:
            resolved.append(file_path)
        else:
            failed.append({"path": file_path, "error": result["message"]})

    success = len(failed) == 0
    strategy_desc = "your changes (ours)" if strategy == "ours" else "incoming changes (theirs)"

    return {
        "success": success,
        "resolved": resolved,
        "failed": failed,
        "message": f"Resolved {len(resolved)} files using {strategy_desc}" +
                   (f", {len(failed)} failed" if failed else "")
    }


def abort_rebase(worktree_path: str) -> dict:
    """
    Abort the current rebase operation.

    Returns:
        {"success": True/False, "message": "..."}
    """
    if not is_rebase_in_progress(worktree_path):
        return {
            "success": False,
            "message": "No rebase in progress to abort"
        }

    returncode, stdout, stderr = run_command(
        ["git", "rebase", "--abort"],
        cwd=worktree_path
    )

    if returncode != 0:
        return {
            "success": False,
            "message": f"Failed to abort rebase: {stderr}"
        }

    return {
        "success": True,
        "message": "Rebase aborted. Working directory returned to previous state."
    }


def abort_merge(worktree_path: str) -> dict:
    """
    Abort the current merge operation.

    Returns:
        {"success": True/False, "message": "..."}
    """
    if not is_merge_in_progress(worktree_path):
        return {
            "success": False,
            "message": "No merge in progress to abort"
        }

    returncode, stdout, stderr = run_command(
        ["git", "merge", "--abort"],
        cwd=worktree_path
    )

    if returncode != 0:
        return {
            "success": False,
            "message": f"Failed to abort merge: {stderr}"
        }

    return {
        "success": True,
        "message": "Merge aborted. Working directory returned to previous state."
    }


def abort_operation(worktree_path: str) -> dict:
    """
    Abort the current rebase or merge operation.

    Returns:
        {"success": True/False, "operation": str, "message": "..."}
    """
    if is_rebase_in_progress(worktree_path):
        result = abort_rebase(worktree_path)
        result["operation"] = "rebase"
        return result
    elif is_merge_in_progress(worktree_path):
        result = abort_merge(worktree_path)
        result["operation"] = "merge"
        return result
    else:
        return {
            "success": False,
            "operation": None,
            "message": "No rebase or merge in progress to abort"
        }


def continue_rebase(worktree_path: str) -> dict:
    """
    Continue rebase after manual resolution.

    Returns:
        {"success": True/False, "message": "...", "more_conflicts": bool}
    """
    if not is_rebase_in_progress(worktree_path):
        return {
            "success": False,
            "message": "No rebase in progress",
            "more_conflicts": False
        }

    # Check if there are still unresolved conflicts
    conflicted = get_conflicted_files(worktree_path)
    if conflicted:
        return {
            "success": False,
            "message": f"Cannot continue: {len(conflicted)} files still have conflicts",
            "more_conflicts": True,
            "conflicted_files": conflicted
        }

    returncode, stdout, stderr = run_command(
        ["git", "rebase", "--continue"],
        cwd=worktree_path
    )

    # Check if continue created more conflicts
    if returncode != 0:
        new_conflicts = get_conflicted_files(worktree_path)
        if new_conflicts:
            return {
                "success": False,
                "message": "Rebase continued but hit more conflicts",
                "more_conflicts": True,
                "conflicted_files": new_conflicts
            }
        return {
            "success": False,
            "message": f"Rebase continue failed: {stderr}",
            "more_conflicts": False
        }

    # Check if rebase is complete
    if is_rebase_in_progress(worktree_path):
        new_conflicts = get_conflicted_files(worktree_path)
        if new_conflicts:
            return {
                "success": False,
                "message": "Rebase continued but more commits have conflicts",
                "more_conflicts": True,
                "conflicted_files": new_conflicts
            }

    return {
        "success": True,
        "message": "Rebase completed successfully",
        "more_conflicts": False
    }


def continue_merge(worktree_path: str, message: Optional[str] = None) -> dict:
    """
    Continue/complete merge after manual resolution.

    Returns:
        {"success": True/False, "message": "..."}
    """
    if not is_merge_in_progress(worktree_path):
        return {
            "success": False,
            "message": "No merge in progress"
        }

    # Check if there are still unresolved conflicts
    conflicted = get_conflicted_files(worktree_path)
    if conflicted:
        return {
            "success": False,
            "message": f"Cannot continue: {len(conflicted)} files still have conflicts",
            "conflicted_files": conflicted
        }

    # Complete the merge with a commit
    cmd = ["git", "commit"]
    if message:
        cmd.extend(["-m", message])
    else:
        cmd.append("--no-edit")  # Use default merge message

    returncode, stdout, stderr = run_command(cmd, cwd=worktree_path)

    if returncode != 0:
        return {
            "success": False,
            "message": f"Merge commit failed: {stderr}"
        }

    return {
        "success": True,
        "message": "Merge completed successfully"
    }


def format_conflict_report(conflicts: dict, task_name: Optional[str] = None) -> str:
    """
    Format a human-readable conflict report.

    Args:
        conflicts: Result from detect_conflicts()
        task_name: Optional task name for context

    Returns:
        Formatted string report
    """
    if not conflicts["has_conflicts"]:
        return "No conflicts detected."

    lines = []

    # Header
    if task_name:
        lines.append(f"Conflicts detected in task '{task_name}':")
    else:
        lines.append("Conflicts detected:")

    if conflicts["operation"]:
        lines.append(f"  Operation: {conflicts['operation']}")

    lines.append("")

    # List each conflicted file
    for i, file_info in enumerate(conflicts["files"], 1):
        lines.append(f"  {i}. {file_info['path']}")

        if file_info["conflict_count"] > 1:
            lines.append(f"     ({file_info['conflict_count']} conflicts in this file)")

        # Show preview
        if file_info["conflict_preview"]:
            lines.append("")
            for preview_line in file_info["conflict_preview"].split("\n")[:15]:
                lines.append(f"     {preview_line}")

        lines.append("")

    # Resolution options
    lines.append("Resolution options:")
    lines.append("  1. Keep ours   - Use your changes (HEAD) for all files")
    lines.append("  2. Keep theirs - Use incoming changes for all files")
    lines.append("  3. Manual      - Edit files manually to resolve")
    lines.append("  4. Abort       - Abort operation and return to previous state")
    lines.append("")

    return "\n".join(lines)


def resolve_conflicts_interactive(worktree_path: str, task_name: Optional[str] = None) -> dict:
    """
    Detect and display conflicts with resolution options.

    This is the main entry point for the 'operator resolve' command.

    Returns:
        {
            "has_conflicts": bool,
            "operation": str,
            "files": [...],
            "report": str  # Human-readable report
        }
    """
    conflicts = detect_conflicts(worktree_path)
    conflicts["report"] = format_conflict_report(conflicts, task_name)
    return conflicts


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Conflict resolution tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # detect command
    detect_parser = subparsers.add_parser("detect", help="Detect conflicts")
    detect_parser.add_argument("worktree_path", help="Path to worktree")
    detect_parser.add_argument("--task", help="Task name for context")
    detect_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # resolve-file command
    resolve_file_parser = subparsers.add_parser("resolve-file", help="Resolve single file")
    resolve_file_parser.add_argument("worktree_path", help="Path to worktree")
    resolve_file_parser.add_argument("file_path", help="File to resolve")
    resolve_file_parser.add_argument("strategy", choices=["ours", "theirs", "manual"])

    # resolve-all command
    resolve_all_parser = subparsers.add_parser("resolve-all", help="Resolve all files")
    resolve_all_parser.add_argument("worktree_path", help="Path to worktree")
    resolve_all_parser.add_argument("strategy", choices=["ours", "theirs"])

    # abort command
    abort_parser = subparsers.add_parser("abort", help="Abort rebase/merge")
    abort_parser.add_argument("worktree_path", help="Path to worktree")

    # continue command
    continue_parser = subparsers.add_parser("continue", help="Continue rebase/merge")
    continue_parser.add_argument("worktree_path", help="Path to worktree")
    continue_parser.add_argument("--message", "-m", help="Commit message (for merge)")

    args = parser.parse_args()

    if args.command == "detect":
        result = resolve_conflicts_interactive(args.worktree_path, args.task)
        if args.json:
            # Remove the report for JSON output
            output = {k: v for k, v in result.items() if k != "report"}
            print(json.dumps(output, indent=2))
        else:
            print(result["report"])
        if result["has_conflicts"]:
            sys.exit(1)

    elif args.command == "resolve-file":
        result = resolve_file(args.worktree_path, args.file_path, args.strategy)
        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}")
            sys.exit(1)

    elif args.command == "resolve-all":
        result = resolve_all(args.worktree_path, args.strategy)
        if result["success"]:
            print(f"✓ {result['message']}")
            for f in result["resolved"]:
                print(f"  ✓ {f}")
        else:
            print(f"✗ {result['message']}")
            for f in result["resolved"]:
                print(f"  ✓ {f}")
            for err in result["failed"]:
                print(f"  ✗ {err['path']}: {err['error']}")
            sys.exit(1)

    elif args.command == "abort":
        result = abort_operation(args.worktree_path)
        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}")
            sys.exit(1)

    elif args.command == "continue":
        if is_rebase_in_progress(args.worktree_path):
            result = continue_rebase(args.worktree_path)
        elif is_merge_in_progress(args.worktree_path):
            result = continue_merge(args.worktree_path, args.message)
        else:
            result = {"success": False, "message": "No operation in progress"}

        if result["success"]:
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}")
            if result.get("more_conflicts"):
                print("  More conflicts need resolution")
            sys.exit(1)

    else:
        parser.print_help()
