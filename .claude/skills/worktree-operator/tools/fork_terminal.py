#!/usr/bin/env python3
"""Fork a new terminal window to run a headless Claude sub-agent."""

import os
import platform
import subprocess
from pathlib import Path


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
    cwd = working_dir or os.getcwd()

    if system == "Darwin":  # macOS
        shell_command = f"cd '{cwd}' && {command}"
        # Escape for AppleScript
        escaped_shell_command = shell_command.replace("\\", "\\\\").replace('"', '\\"')

        try:
            result = subprocess.run(
                [
                    "osascript", "-e",
                    f'tell application "Terminal" to do script "{escaped_shell_command}"'
                ],
                capture_output=True,
                text=True,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "return_code": result.returncode,
                "platform": "macOS",
                "working_dir": cwd
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "platform": "macOS"
            }

    elif system == "Windows":
        full_command = f'cd /d "{cwd}" && {command}'
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", full_command],
                shell=True
            )
            return {
                "success": True,
                "platform": "Windows",
                "working_dir": cwd
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "platform": "Windows"
            }

    elif system == "Linux":
        # Try common terminal emulators
        terminals = [
            ("gnome-terminal", ["gnome-terminal", "--", "bash", "-c", f"cd '{cwd}' && {command}; exec bash"]),
            ("konsole", ["konsole", "-e", "bash", "-c", f"cd '{cwd}' && {command}; exec bash"]),
            ("xterm", ["xterm", "-e", f"cd '{cwd}' && {command}; exec bash"]),
        ]

        for term_name, term_cmd in terminals:
            try:
                # Check if terminal exists
                which_result = subprocess.run(["which", term_name], capture_output=True)
                if which_result.returncode == 0:
                    subprocess.Popen(term_cmd)
                    return {
                        "success": True,
                        "platform": "Linux",
                        "terminal": term_name,
                        "working_dir": cwd
                    }
            except Exception:
                continue

        return {
            "success": False,
            "error": "No supported terminal emulator found (tried gnome-terminal, konsole, xterm)",
            "platform": "Linux"
        }

    else:
        return {
            "success": False,
            "error": f"Platform {system} not supported",
            "platform": system
        }


def spawn_forked_subagent(
    task_name: str,
    ticket: str,
    workspace_path: str = ".",
    model: str = "opus",
    iteration: int = 1
) -> dict:
    """
    Spawn a sub-agent in a forked terminal to work on a task.

    Args:
        task_name: Name of the task (e.g., "fix-logging")
        ticket: Ticket ID (e.g., "K-123")
        workspace_path: Path to workspace root
        model: Model to use (opus, sonnet, haiku)
        iteration: Current iteration number

    Returns:
        dict with spawn result
    """
    workspace = Path(workspace_path).resolve()
    task_folder = workspace / f"task-{task_name}"
    worktree_path = task_folder / "worktree"

    # Validate task exists
    if not task_folder.exists():
        return {
            "success": False,
            "error": f"Task folder not found: {task_folder}"
        }

    if not worktree_path.exists():
        return {
            "success": False,
            "error": f"Worktree not found: {worktree_path}"
        }

    spec_path = task_folder / "spec.md"
    if not spec_path.exists():
        return {
            "success": False,
            "error": f"Spec not found: {spec_path}"
        }

    # Check if this is an iteration
    feedback_path = task_folder / "feedback.md"
    is_iteration = False
    if feedback_path.exists():
        content = feedback_path.read_text()
        is_iteration = "No feedback yet" not in content and len(content.strip()) > 50

    # Build the prompt
    if is_iteration:
        iteration_context = f"""
IMPORTANT: This is iteration {iteration}. Previous work was reviewed and feedback was provided.
Read feedback.md FIRST to understand what needs to be fixed or improved.
Build upon your previous commits, don't start over unless feedback says to."""
    else:
        iteration_context = ""

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

    # Escape single quotes for shell
    escaped_prompt = prompt.replace("'", "'\"'\"'")

    # Build claude command
    model_flag = ""
    if model == "haiku":
        model_flag = "--model haiku"
    elif model == "sonnet":
        model_flag = "--model sonnet"
    # opus is default, no flag needed

    claude_command = f"claude --dangerously-skip-permissions {model_flag} -p '{escaped_prompt}'"

    # Fork the terminal
    result = fork_terminal(claude_command, str(worktree_path))

    if result["success"]:
        result["task_name"] = task_name
        result["ticket"] = ticket
        result["model"] = model
        result["iteration"] = iteration
        result["worktree"] = str(worktree_path)
        result["message"] = f"Sub-agent forked for task '{task_name}' in new terminal"

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: fork_terminal.py <command>")
        print("   or: fork_terminal.py --spawn <task_name> <ticket> [workspace] [model]")
        sys.exit(1)

    if sys.argv[1] == "--spawn":
        if len(sys.argv) < 4:
            print("Usage: fork_terminal.py --spawn <task_name> <ticket> [workspace] [model]")
            sys.exit(1)

        task_name = sys.argv[2]
        ticket = sys.argv[3]
        workspace = sys.argv[4] if len(sys.argv) > 4 else "."
        model = sys.argv[5] if len(sys.argv) > 5 else "opus"

        result = spawn_forked_subagent(task_name, ticket, workspace, model)
        print(result)
    else:
        # Raw command mode
        command = " ".join(sys.argv[1:])
        result = fork_terminal(command)
        print(result)
