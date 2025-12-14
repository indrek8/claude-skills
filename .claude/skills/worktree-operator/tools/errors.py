#!/usr/bin/env python3
"""
Standardized error classes and utilities for the operator skill.

Provides structured errors with recovery hints and actionable options.
"""

from typing import List, Optional


class OperatorError(Exception):
    """
    Structured error with recovery hints.

    Provides consistent error formatting across all operator tools with
    actionable hints and recovery options.
    """

    def __init__(
        self,
        message: str,
        hint: Optional[str] = None,
        recovery_options: Optional[List[str]] = None,
        error_code: Optional[str] = None,
        context: Optional[dict] = None
    ):
        """
        Initialize an OperatorError.

        Args:
            message: The error message describing what went wrong
            hint: A brief actionable hint for how to fix the issue
            recovery_options: List of specific commands or actions to recover
            error_code: Optional error code for programmatic handling
            context: Optional additional context (paths, values, etc.)
        """
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.recovery_options = recovery_options or []
        self.error_code = error_code
        self.context = context or {}

    def to_dict(self) -> dict:
        """Convert to error dictionary format used by tools."""
        result = {
            "success": False,
            "error": self.message
        }
        if self.hint:
            result["hint"] = self.hint
        if self.recovery_options:
            result["recovery_options"] = self.recovery_options
        if self.error_code:
            result["error_code"] = self.error_code
        if self.context:
            result["context"] = self.context
        return result

    def __str__(self) -> str:
        """Format error for display."""
        parts = [f"Error: {self.message}"]
        if self.hint:
            parts.append(f"Hint: {self.hint}")
        if self.recovery_options:
            parts.append("Recovery options:")
            for opt in self.recovery_options:
                parts.append(f"  - {opt}")
        return "\n".join(parts)


def make_error(
    message: str,
    hint: Optional[str] = None,
    recovery_options: Optional[List[str]] = None,
    error_code: Optional[str] = None,
    **context
) -> dict:
    """
    Create an error dictionary without raising an exception.

    This is a convenience function for returning error dicts from tools.

    Args:
        message: The error message
        hint: Actionable hint
        recovery_options: List of recovery actions
        error_code: Optional error code
        **context: Additional context to include

    Returns:
        Error dictionary suitable for returning from a tool function
    """
    return OperatorError(
        message=message,
        hint=hint,
        recovery_options=recovery_options,
        error_code=error_code,
        context=context if context else None
    ).to_dict()


# =============================================================================
# Pre-defined errors for common scenarios
# =============================================================================

# --- Repository/Workspace Errors ---

def repo_exists_error(path: str) -> dict:
    """Error when repository folder already exists."""
    return make_error(
        f"Repository folder already exists: {path}",
        hint="The workspace already has a repo. Choose an action below.",
        recovery_options=[
            f"Remove existing: rm -rf {path}",
            "Use a different workspace path",
            "Continue with existing: operator status"
        ],
        error_code="REPO_EXISTS",
        path=path
    )


def repo_not_found_error(path: str) -> dict:
    """Error when repository is not found."""
    return make_error(
        f"Repository not found at: {path}",
        hint="The workspace needs to be initialized first.",
        recovery_options=[
            "Initialize workspace: operator init <repo_url> <branch>",
            "Check if you're in the correct directory"
        ],
        error_code="REPO_NOT_FOUND",
        path=path
    )


def workspace_not_found_error(path: str) -> dict:
    """Error when workspace doesn't exist."""
    return make_error(
        f"Workspace does not exist: {path}",
        hint="Create the workspace directory first.",
        recovery_options=[
            f"Create directory: mkdir -p {path}",
            "Use a different workspace path"
        ],
        error_code="WORKSPACE_NOT_FOUND",
        path=path
    )


# --- Task Errors ---

def task_exists_error(task_name: str, task_dir: str) -> dict:
    """Error when task folder already exists."""
    return make_error(
        f"Task folder already exists: {task_dir}",
        hint="A task with this name already exists in the workspace.",
        recovery_options=[
            f"Use different name: operator create task <new-name>",
            f"Remove existing: rm -rf {task_dir}",
            f"Check task status: operator status {task_name}"
        ],
        error_code="TASK_EXISTS",
        task_name=task_name,
        task_dir=task_dir
    )


def task_not_found_error(task_name: str, task_dir: str) -> dict:
    """Error when task folder is not found."""
    return make_error(
        f"Task folder not found: {task_dir}",
        hint="The task doesn't exist or was already removed.",
        recovery_options=[
            f"Create the task: operator create task {task_name}",
            "List existing tasks: operator status"
        ],
        error_code="TASK_NOT_FOUND",
        task_name=task_name,
        task_dir=task_dir
    )


def worktree_not_found_error(task_name: str, worktree_path: str) -> dict:
    """Error when worktree is missing for a task."""
    return make_error(
        f"Worktree not found: {worktree_path}",
        hint="The task exists but its worktree is missing.",
        recovery_options=[
            f"Recreate task: operator reset {task_name}",
            "Check git worktree list for issues: git worktree list"
        ],
        error_code="WORKTREE_NOT_FOUND",
        task_name=task_name,
        worktree_path=worktree_path
    )


def spec_not_found_error(task_name: str, spec_path: str) -> dict:
    """Error when spec.md is missing for a task."""
    return make_error(
        f"Spec not found: {spec_path}",
        hint="The task needs a spec.md file to define the work.",
        recovery_options=[
            f"Create spec file in the task folder",
            f"Recreate the task: operator create task {task_name}"
        ],
        error_code="SPEC_NOT_FOUND",
        task_name=task_name,
        spec_path=spec_path
    )


# --- Git Errors ---

def branch_exists_error(branch: str) -> dict:
    """Error when branch already exists."""
    return make_error(
        f"Branch already exists: {branch}",
        hint="A branch with this name already exists.",
        recovery_options=[
            "Use a different task name",
            f"Delete existing branch: git branch -D {branch}",
            f"Switch to existing: git switch {branch}"
        ],
        error_code="BRANCH_EXISTS",
        branch=branch
    )


def clone_failed_error(repo_url: str, stderr: str) -> dict:
    """Error when git clone fails."""
    return make_error(
        f"Failed to clone repository: {stderr}",
        hint="Git clone failed. Check the URL and your network connection.",
        recovery_options=[
            "Verify the repository URL is correct",
            "Check your network connection",
            "Ensure you have access to the repository",
            f"Try manually: git clone {repo_url}"
        ],
        error_code="CLONE_FAILED",
        repo_url=repo_url,
        git_error=stderr
    )


def checkout_failed_error(branch: str, stderr: str) -> dict:
    """Error when git checkout/switch fails."""
    return make_error(
        f"Failed to checkout branch '{branch}': {stderr}",
        hint="Git checkout failed. The branch may not exist or have issues.",
        recovery_options=[
            f"Create the branch: git switch -c {branch}",
            "Check available branches: git branch -a",
            "Fetch latest: git fetch origin"
        ],
        error_code="CHECKOUT_FAILED",
        branch=branch,
        git_error=stderr
    )


def rebase_conflict_error(task_name: str, main_branch: str) -> dict:
    """Error when rebase has conflicts."""
    return make_error(
        f"Rebase has conflicts while syncing task '{task_name}'",
        hint="The rebase encountered merge conflicts that need manual resolution.",
        recovery_options=[
            "Resolve conflicts in the worktree manually",
            "After resolving: git rebase --continue",
            "To abort rebase: git rebase --abort",
            f"Reset to start over: operator reset {task_name}"
        ],
        error_code="REBASE_CONFLICT",
        task_name=task_name,
        main_branch=main_branch
    )


def merge_conflict_error(source: str, target: str) -> dict:
    """Error when merge has conflicts."""
    return make_error(
        f"Merge conflict while merging '{source}' into '{target}'",
        hint="The merge encountered conflicts that need manual resolution.",
        recovery_options=[
            "Resolve conflicts in the files",
            "After resolving: git add . && git commit",
            "To abort: git merge --abort"
        ],
        error_code="MERGE_CONFLICT",
        source_branch=source,
        target_branch=target
    )


def push_failed_error(branch: str, stderr: str) -> dict:
    """Error when git push fails."""
    return make_error(
        f"Failed to push branch '{branch}': {stderr}",
        hint="Git push failed. Check remote access and branch protection rules.",
        recovery_options=[
            "Fetch and rebase first: git fetch && git rebase origin/main",
            "Check remote configuration: git remote -v",
            f"Force push (use with caution): git push --force-with-lease origin {branch}"
        ],
        error_code="PUSH_FAILED",
        branch=branch,
        git_error=stderr
    )


def worktree_create_failed_error(
    worktree_path: str,
    branch: str,
    stderr: str
) -> dict:
    """Error when creating git worktree fails."""
    return make_error(
        f"Failed to create worktree: {stderr}",
        hint="Git worktree creation failed.",
        recovery_options=[
            "Check if the branch already exists: git branch -a",
            "Remove existing worktree: git worktree remove <path>",
            f"Try manually: git worktree add {worktree_path} -b {branch}"
        ],
        error_code="WORKTREE_CREATE_FAILED",
        worktree_path=worktree_path,
        branch=branch,
        git_error=stderr
    )


# --- Test Errors ---

def tests_failed_error(
    command: str,
    returncode: int,
    duration: float,
    stage: str = "execution"
) -> dict:
    """Error when tests fail."""
    return make_error(
        f"Tests failed with exit code {returncode}",
        hint=f"Tests failed during {stage}. Review the output and fix the issues.",
        recovery_options=[
            f"Run tests manually: {command}",
            "Check test output for specific failures",
            "Review recent changes for potential issues"
        ],
        error_code="TESTS_FAILED",
        command=command,
        returncode=returncode,
        duration=duration,
        stage=stage
    )


def test_timeout_error(command: str, timeout: int) -> dict:
    """Error when tests timeout."""
    return make_error(
        f"Tests timed out after {timeout} seconds",
        hint="Tests took too long to complete and were terminated.",
        recovery_options=[
            "Increase timeout in workspace.json",
            "Check for infinite loops or hanging tests",
            f"Run tests manually to investigate: {command}"
        ],
        error_code="TEST_TIMEOUT",
        command=command,
        timeout=timeout
    )


def test_detection_failed_error(repo_path: str) -> dict:
    """Error when test command cannot be auto-detected."""
    return make_error(
        f"Could not auto-detect test command for: {repo_path}",
        hint="No known test framework files found (package.json, pytest.ini, etc.).",
        recovery_options=[
            "Set test_command in workspace.json",
            "Pass test_command parameter explicitly",
            "Supported frameworks: npm, pytest, go test, cargo test, etc."
        ],
        error_code="TEST_DETECTION_FAILED",
        repo_path=repo_path
    )


# --- Lock Errors ---

def lock_held_error(workspace: str, lock_info: Optional[dict] = None) -> dict:
    """Error when workspace is locked by another operation."""
    options = [
        "Wait for the other operation to complete",
        "Check lock status: python tools/locking.py status",
    ]

    if lock_info and lock_info.get("pid"):
        options.append(f"Check if process {lock_info['pid']} is still running")

    options.append("Force unlock (if stale): python tools/locking.py unlock")

    return make_error(
        "Workspace is locked by another operation",
        hint="Another process is currently modifying the workspace.",
        recovery_options=options,
        error_code="LOCK_HELD",
        workspace=workspace,
        lock_info=lock_info
    )


def lock_timeout_error(
    workspace: str,
    timeout: int,
    lock_info: Optional[dict] = None
) -> dict:
    """Error when waiting for lock times out."""
    return make_error(
        f"Timeout waiting for workspace lock after {timeout}s",
        hint="Another operation may be stuck or taking too long.",
        recovery_options=[
            "Check what operation is running",
            "Wait and retry",
            "Force unlock if the operation is stuck: python tools/locking.py unlock"
        ],
        error_code="LOCK_TIMEOUT",
        workspace=workspace,
        timeout=timeout,
        lock_info=lock_info
    )


# --- Sub-agent Errors ---

def subagent_timeout_error(task_name: str, timeout: int) -> dict:
    """Error when sub-agent heartbeat times out."""
    return make_error(
        f"Sub-agent for task '{task_name}' appears unresponsive",
        hint=f"No heartbeat received in {timeout} seconds.",
        recovery_options=[
            "Check the sub-agent terminal for errors",
            f"View sub-agent status: operator health {task_name}",
            f"Reset and re-spawn: operator reset {task_name}"
        ],
        error_code="SUBAGENT_TIMEOUT",
        task_name=task_name,
        timeout=timeout
    )


def subagent_spawn_failed_error(task_name: str, error: str) -> dict:
    """Error when sub-agent fails to spawn."""
    return make_error(
        f"Failed to spawn sub-agent for task '{task_name}': {error}",
        hint="The sub-agent could not be started.",
        recovery_options=[
            "Check if Claude is installed and accessible",
            "Verify the task folder exists and has spec.md",
            f"Try spawning manually in the task worktree"
        ],
        error_code="SUBAGENT_SPAWN_FAILED",
        task_name=task_name,
        spawn_error=error
    )


def terminal_not_supported_error(platform: str) -> dict:
    """Error when platform doesn't support terminal forking."""
    return make_error(
        f"Platform '{platform}' not supported for terminal forking",
        hint="Terminal forking is only supported on macOS, Windows, and Linux with common terminal emulators.",
        recovery_options=[
            "Use inline mode instead: operator spawn {task}",
            "Open a terminal manually and run the sub-agent command"
        ],
        error_code="TERMINAL_NOT_SUPPORTED",
        platform=platform
    )


def no_terminal_found_error() -> dict:
    """Error when no terminal emulator is found on Linux."""
    return make_error(
        "No supported terminal emulator found",
        hint="Tried gnome-terminal, konsole, and xterm.",
        recovery_options=[
            "Install a supported terminal: gnome-terminal, konsole, or xterm",
            "Use inline mode instead: operator spawn {task}"
        ],
        error_code="NO_TERMINAL_FOUND"
    )


# --- Validation Errors ---

def invalid_input_error(
    field: str,
    value: str,
    reason: str,
    examples: Optional[List[str]] = None
) -> dict:
    """Error for invalid input validation."""
    options = []
    if examples:
        options.append(f"Valid examples: {', '.join(examples)}")

    return make_error(
        f"Invalid {field}: '{value}'. {reason}",
        hint=f"Check the {field} format and try again.",
        recovery_options=options,
        error_code="INVALID_INPUT",
        field=field,
        value=value
    )


# =============================================================================
# Diagnose command support
# =============================================================================

COMMON_ISSUES = {
    "REPO_EXISTS": {
        "symptom": "Cannot initialize workspace - repo folder exists",
        "causes": ["Previous initialization was interrupted", "Workspace already set up"],
        "diagnosis": "Check if the repo folder contains a valid git repository"
    },
    "WORKTREE_NOT_FOUND": {
        "symptom": "Task exists but worktree is missing",
        "causes": ["Worktree was manually deleted", "Git prune removed it", "Creation was interrupted"],
        "diagnosis": "Run 'git worktree list' to see all worktrees"
    },
    "REBASE_CONFLICT": {
        "symptom": "Sync or accept fails with conflicts",
        "causes": ["Main branch changed files that sub-agent also modified"],
        "diagnosis": "Check 'git status' in the worktree for conflict markers"
    },
    "LOCK_HELD": {
        "symptom": "Operations fail with 'workspace locked'",
        "causes": ["Another operation is running", "Previous operation crashed"],
        "diagnosis": "Check .workspace.lock.info for holder details"
    },
    "TESTS_FAILED": {
        "symptom": "Accept fails at test verification",
        "causes": ["Code changes broke existing tests", "Test environment issues"],
        "diagnosis": "Run tests manually in the worktree to see full output"
    },
    "SUBAGENT_TIMEOUT": {
        "symptom": "Sub-agent appears stuck or unresponsive",
        "causes": ["Long-running operation", "Waiting for user input", "Crashed"],
        "diagnosis": "Check the sub-agent terminal window for errors"
    }
}


def diagnose(error_code: str) -> dict:
    """
    Get diagnostic information for a common error.

    Args:
        error_code: The error code to diagnose

    Returns:
        dict with diagnostic information
    """
    if error_code not in COMMON_ISSUES:
        return {
            "success": False,
            "error": f"Unknown error code: {error_code}",
            "known_codes": list(COMMON_ISSUES.keys())
        }

    info = COMMON_ISSUES[error_code]
    return {
        "success": True,
        "error_code": error_code,
        "symptom": info["symptom"],
        "possible_causes": info["causes"],
        "diagnosis_steps": info["diagnosis"]
    }


def list_known_errors() -> dict:
    """
    List all known error codes with brief descriptions.

    Returns:
        dict with list of error codes and symptoms
    """
    return {
        "success": True,
        "errors": [
            {"code": code, "symptom": info["symptom"]}
            for code, info in COMMON_ISSUES.items()
        ]
    }


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: errors.py <command> [args]")
        print("Commands:")
        print("  diagnose <error_code>  - Get diagnostic info for an error")
        print("  list                   - List all known error codes")
        print("  test                   - Run self-test")
        sys.exit(1)

    command = sys.argv[1]

    if command == "diagnose":
        if len(sys.argv) < 3:
            print("Error: error_code required")
            print("Use 'errors.py list' to see known error codes")
            sys.exit(1)
        result = diagnose(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif command == "list":
        result = list_known_errors()
        print(json.dumps(result, indent=2))

    elif command == "test":
        # Self-test: create some errors and display them
        print("Testing OperatorError class:\n")

        err = OperatorError(
            "Test error message",
            hint="This is a test hint",
            recovery_options=["Option 1", "Option 2"],
            error_code="TEST_ERROR"
        )
        print("String representation:")
        print(str(err))
        print("\nDict representation:")
        print(json.dumps(err.to_dict(), indent=2))

        print("\n\nTesting pre-defined errors:\n")

        # Test a few pre-defined errors
        errors = [
            ("repo_exists_error", repo_exists_error("/workspace/repo")),
            ("task_not_found_error", task_not_found_error("fix-bug", "/workspace/task-fix-bug")),
            ("rebase_conflict_error", rebase_conflict_error("fix-bug", "main")),
            ("tests_failed_error", tests_failed_error("npm test", 1, 5.2, "acceptance")),
        ]

        for name, err_dict in errors:
            print(f"--- {name} ---")
            print(json.dumps(err_dict, indent=2))
            print()

        print("All tests passed!")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
