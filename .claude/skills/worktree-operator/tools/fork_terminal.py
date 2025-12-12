#!/usr/bin/env python3
"""Fork a new terminal window to run a headless Claude sub-agent."""

import os
import platform
import shlex
import subprocess
from pathlib import Path

# Import shared validation utilities
from validation import (
    ValidationError,
    validate_task_name,
    validate_ticket,
    validate_model,
    validate_path,
    validate_positive_int,
)

# Import health check utilities
from health_check import mark_started, mark_running

# Import logging utilities
from logging_config import get_logger

# Import plan parser for dependency checking
from plan_parser import check_dependencies

# Import error utilities
from errors import (
    make_error,
    task_not_found_error,
    worktree_not_found_error,
    spec_not_found_error,
    terminal_not_supported_error,
    no_terminal_found_error,
    subagent_spawn_failed_error,
)

# Module logger
logger = get_logger("fork_terminal")


def escape_for_applescript(s: str) -> str:
    """
    Properly escape a string for use in AppleScript.

    Escapes: backslash, double quote, and converts the string
    to be safe for embedding in AppleScript double-quoted strings.

    Args:
        s: String to escape

    Returns:
        Escaped string safe for AppleScript
    """
    # AppleScript uses backslash escaping within double quotes
    # We need to escape: \ and "
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    return s


def fork_terminal(command: str, working_dir: str = None) -> dict:
    """
    Open a new Terminal window and run the specified command.

    Args:
        command: The command to run in the new terminal
        working_dir: Working directory for the command (defaults to cwd)

    Returns:
        dict with success status and details
    """
    system = platform.system()

    try:
        cwd = validate_path(working_dir) if working_dir else Path.cwd()
    except ValidationError as e:
        return {
            "success": False,
            "error": str(e),
            "platform": system
        }

    cwd_str = str(cwd)

    if system == "Darwin":  # macOS
        # Use shlex.quote for the working directory in shell command
        # The command itself is passed as-is (caller is responsible for it)
        shell_command = f"cd {shlex.quote(cwd_str)} && {command}"

        # Escape the entire shell command for AppleScript embedding
        escaped_for_applescript = escape_for_applescript(shell_command)

        applescript = f'tell application "Terminal" to do script "{escaped_for_applescript}"'

        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "return_code": result.returncode,
                "platform": "macOS",
                "working_dir": cwd_str
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "platform": "macOS"
            }

    elif system == "Windows":
        # Build command without shell=True
        # Use proper quoting for the path
        quoted_cwd = f'"{cwd_str}"'
        full_command = f'cd /d {quoted_cwd} && {command}'

        try:
            # Don't use shell=True - pass arguments as list
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", full_command]
            )
            return {
                "success": True,
                "platform": "Windows",
                "working_dir": cwd_str
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "platform": "Windows"
            }

    elif system == "Linux":
        # Use shlex.quote for the working directory
        quoted_cwd = shlex.quote(cwd_str)

        # Build shell command with proper quoting
        shell_cmd = f"cd {quoted_cwd} && {command}; exec bash"

        # Try common terminal emulators
        terminals = [
            ("gnome-terminal", ["gnome-terminal", "--", "bash", "-c", shell_cmd]),
            ("konsole", ["konsole", "-e", "bash", "-c", shell_cmd]),
            ("xterm", ["xterm", "-e", "bash", "-c", shell_cmd]),
        ]

        for term_name, term_cmd in terminals:
            try:
                # Check if terminal exists using shutil.which (safer than subprocess)
                import shutil
                if shutil.which(term_name):
                    subprocess.Popen(term_cmd)
                    return {
                        "success": True,
                        "platform": "Linux",
                        "terminal": term_name,
                        "working_dir": cwd_str
                    }
            except Exception:
                continue

        result = no_terminal_found_error()
        result["platform"] = "Linux"
        return result

    else:
        result = terminal_not_supported_error(system)
        result["platform"] = system
        return result


def spawn_forked_subagent(
    task_name: str,
    ticket: str,
    workspace_path: str = ".",
    model: str = "opus",
    iteration: int = 1,
    force: bool = False
) -> dict:
    """
    Spawn a sub-agent in a forked terminal to work on a task.

    Args:
        task_name: Name of the task (e.g., "fix-logging")
        ticket: Ticket ID (e.g., "K-123")
        workspace_path: Path to workspace root
        model: Model to use (opus, sonnet, haiku)
        iteration: Current iteration number
        force: If True, skip dependency checking and spawn anyway

    Returns:
        dict with spawn result
    """
    # Validate all inputs first
    try:
        task_name = validate_task_name(task_name)
        ticket = validate_ticket(ticket)
        model = validate_model(model)
        workspace = validate_path(workspace_path)
        iteration = validate_positive_int(iteration, "iteration")
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "hint": getattr(e, 'hint', "Check input format and try again"),
            "validation_error": True
        }

    # Check dependencies before spawning (unless force is True)
    if not force:
        dep_check = check_dependencies(task_name, str(workspace))
        if dep_check["success"] and not dep_check["can_spawn"]:
            return {
                "success": False,
                "error": dep_check.get("error", "Dependencies not met"),
                "hint": dep_check.get("hint", "Use --force to override dependency check"),
                "missing_dependencies": dep_check.get("missing", []),
                "completed_dependencies": dep_check.get("completed", []),
                "dependency_check": True
            }
        # Include warning if task doesn't exist in plan
        if dep_check.get("warning"):
            # Store warning to include in result later
            dep_warning = dep_check["warning"]
        else:
            dep_warning = None
    else:
        dep_warning = "Dependency check skipped (--force)"

    task_folder = workspace / f"task-{task_name}"
    worktree_path = task_folder / "worktree"

    # Validate task exists
    if not task_folder.exists():
        return task_not_found_error(task_name, str(task_folder))

    if not worktree_path.exists():
        return worktree_not_found_error(task_name, str(worktree_path))

    spec_path = task_folder / "spec.md"
    if not spec_path.exists():
        return spec_not_found_error(task_name, str(spec_path))

    # Check if this is an iteration
    feedback_path = task_folder / "feedback.md"
    is_iteration = False
    if feedback_path.exists():
        content = feedback_path.read_text()
        is_iteration = "No feedback yet" not in content and len(content.strip()) > 50

    # Build the prompt - use only validated/safe values
    # task_name, ticket are validated to be safe alphanumeric strings
    # Paths are resolved absolute paths
    if is_iteration:
        iteration_context = f"""
IMPORTANT: This is iteration {iteration}. Previous work was reviewed and feedback was provided.
Read feedback.md FIRST to understand what needs to be fixed or improved.
Build upon your previous commits, don't start over unless feedback says to."""
    else:
        iteration_context = ""

    # Build prompt with validated values only
    prompt = f'''You are a sub-agent working on task '{task_name}'.

WORKSPACE CONTEXT:
- Task folder: {task_folder}
- Your worktree: {worktree_path}
- You ONLY work in the worktree directory
{iteration_context}

INSTRUCTIONS:
1. Read {task_folder}/spec.md to understand your task
2. {"Read " + str(task_folder) + "/feedback.md for iteration feedback" if is_iteration else "Check if feedback.md has any notes"}
3. Work ONLY in {worktree_path}
4. Make changes, run tests, commit with clear messages
5. Write {task_folder}/results.md summarizing your work
6. Exit when complete

COMMIT MESSAGE FORMAT:
{ticket}: Brief description of change

RESULTS.MD MUST INCLUDE:
- Summary of what was done
- Files modified/created
- Test results
- Any risks or concerns
- List of commits made

RESTRICTIONS:
- Do NOT modify files outside {worktree_path}
- Do NOT merge branches
- Do NOT push to remote (operator will do this)
- Do NOT modify plan.md or review-notes.md

BEGIN WORK NOW.'''

    # Use shlex.quote for the prompt to safely embed in shell command
    quoted_prompt = shlex.quote(prompt)

    # Build claude command with proper quoting
    model_flag = ""
    if model == "haiku":
        model_flag = "--model haiku "
    elif model == "sonnet":
        model_flag = "--model sonnet "
    # opus is default, no flag needed

    claude_command = f"claude --dangerously-skip-permissions {model_flag}-p {quoted_prompt}"

    logger.info(f"spawn_forked_subagent: Spawning sub-agent for task '{task_name}', ticket {ticket}, model {model}, iteration {iteration}")

    # Mark sub-agent as starting
    mark_started(task_name, str(workspace))

    # Fork the terminal
    result = fork_terminal(claude_command, str(worktree_path))

    if result["success"]:
        # Update status to running
        mark_running(task_name, "Sub-agent starting in new terminal", str(workspace))
        logger.info(f"spawn_forked_subagent: Sub-agent forked successfully for task '{task_name}'")

        result["task_name"] = task_name
        result["ticket"] = ticket
        result["model"] = model
        result["iteration"] = iteration
        result["worktree"] = str(worktree_path)
        result["message"] = f"Sub-agent forked for task '{task_name}' in new terminal"
        result["health_check"] = "Status file created. Use 'operator status {task_name}' to check progress."
    else:
        logger.error(f"spawn_forked_subagent: Failed to fork terminal for task '{task_name}': {result.get('error')}")

        # Include dependency warning if any
        if dep_warning:
            result["warning"] = dep_warning

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: fork_terminal.py <command>")
        print("   or: fork_terminal.py --spawn <task_name> <ticket> [workspace] [model] [--force]")
        sys.exit(1)

    if sys.argv[1] == "--spawn":
        if len(sys.argv) < 4:
            print("Usage: fork_terminal.py --spawn <task_name> <ticket> [workspace] [model] [--force]")
            sys.exit(1)

        # Parse arguments, handling --force flag
        args = sys.argv[2:]
        force = "--force" in args
        if force:
            args.remove("--force")

        task_name = args[0]
        ticket = args[1]
        workspace = args[2] if len(args) > 2 else "."
        model = args[3] if len(args) > 3 else "opus"

        result = spawn_forked_subagent(task_name, ticket, workspace, model, force=force)

        if result["success"]:
            print(f"Success: {result.get('message', 'Sub-agent spawned')}")
            if result.get("warning"):
                print(f"Warning: {result['warning']}")
        else:
            print(f"Error: {result['error']}")
            if "hint" in result:
                print(f"Hint: {result['hint']}")
            if result.get("missing_dependencies"):
                print(f"Missing dependencies: {', '.join(result['missing_dependencies'])}")
            sys.exit(1)
    else:
        # Raw command mode
        command = " ".join(sys.argv[1:])
        result = fork_terminal(command)

        if result["success"]:
            print(f"Terminal forked successfully ({result['platform']})")
        else:
            print(f"Error: {result['error']}")
            sys.exit(1)
