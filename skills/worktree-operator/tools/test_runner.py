#!/usr/bin/env python3
"""
Test runner utilities for verifying code before merge.

Provides auto-detection and execution of tests across different project types.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple, List

from validation import ValidationError, validate_path

# Import logging utilities - use lazy import to avoid circular dependencies
_logger = None

def _get_logger():
    """Get logger lazily to avoid circular imports."""
    global _logger
    if _logger is None:
        from logging_config import get_logger
        _logger = get_logger("test_runner")
    return _logger

# Import error utilities
from errors import (
    make_error,
    tests_failed_error,
    test_timeout_error,
    test_detection_failed_error,
)


# Default test timeout (5 minutes)
DEFAULT_TEST_TIMEOUT = 300

# Test command patterns by project type
TEST_PATTERNS = {
    # Node.js / JavaScript
    "package.json": {
        "detect_file": "package.json",
        "commands": ["npm test", "npm run test", "yarn test"],
        "type": "nodejs"
    },
    # Python
    "pytest.ini": {
        "detect_file": "pytest.ini",
        "commands": ["pytest", "python -m pytest"],
        "type": "python"
    },
    "setup.py": {
        "detect_file": "setup.py",
        "commands": ["pytest", "python -m pytest", "python setup.py test"],
        "type": "python"
    },
    "pyproject.toml": {
        "detect_file": "pyproject.toml",
        "commands": ["pytest", "python -m pytest"],
        "type": "python"
    },
    # Go
    "go.mod": {
        "detect_file": "go.mod",
        "commands": ["go test ./..."],
        "type": "go"
    },
    # Rust
    "Cargo.toml": {
        "detect_file": "Cargo.toml",
        "commands": ["cargo test"],
        "type": "rust"
    },
    # Ruby
    "Gemfile": {
        "detect_file": "Gemfile",
        "commands": ["bundle exec rspec", "rake test"],
        "type": "ruby"
    },
    # Java / Maven
    "pom.xml": {
        "detect_file": "pom.xml",
        "commands": ["mvn test"],
        "type": "java-maven"
    },
    # Java / Gradle
    "build.gradle": {
        "detect_file": "build.gradle",
        "commands": ["./gradlew test", "gradle test"],
        "type": "java-gradle"
    },
    # .NET
    "*.csproj": {
        "detect_pattern": "*.csproj",
        "commands": ["dotnet test"],
        "type": "dotnet"
    },
}


def run_command(
    cmd: str,
    cwd: str,
    timeout: int = DEFAULT_TEST_TIMEOUT
) -> Tuple[int, str, str, float]:
    """
    Run a shell command with timeout.

    Returns:
        Tuple of (returncode, stdout, stderr, duration_seconds)
    """
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        return result.returncode, result.stdout, result.stderr, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return -1, "", f"Test timed out after {timeout} seconds", duration

    except Exception as e:
        duration = time.time() - start_time
        return -1, "", str(e), duration


def detect_test_command(repo_path: str) -> Optional[dict]:
    """
    Auto-detect the appropriate test command for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        dict with detected test info or None if not detected
    """
    repo = Path(repo_path)

    if not repo.exists():
        return None

    # Check each pattern
    for pattern_name, pattern_info in TEST_PATTERNS.items():
        detect_file = pattern_info.get("detect_file")
        detect_pattern = pattern_info.get("detect_pattern")

        if detect_file:
            if (repo / detect_file).exists():
                return {
                    "type": pattern_info["type"],
                    "commands": pattern_info["commands"],
                    "detected_by": detect_file
                }
        elif detect_pattern:
            if list(repo.glob(detect_pattern)):
                return {
                    "type": pattern_info["type"],
                    "commands": pattern_info["commands"],
                    "detected_by": detect_pattern
                }

    return None


def find_working_test_command(
    repo_path: str,
    commands: List[str],
    timeout: int = 30
) -> Optional[str]:
    """
    Find the first working test command from a list.

    Args:
        repo_path: Path to the repository
        commands: List of commands to try
        timeout: Timeout for each command check

    Returns:
        First working command or None
    """
    for cmd in commands:
        # Quick check - just see if the command starts without error
        # Use a very short timeout for detection
        returncode, stdout, stderr, _ = run_command(
            f"{cmd} --help 2>/dev/null || {cmd} -h 2>/dev/null || echo 'ok'",
            repo_path,
            timeout=10
        )
        if returncode == 0:
            return cmd

    # If none work with --help, just return the first one
    return commands[0] if commands else None


def load_workspace_config(workspace_path: str) -> dict:
    """
    Load workspace configuration if it exists.

    Args:
        workspace_path: Path to workspace

    Returns:
        Config dict (empty if no config file)
    """
    try:
        from config import get_config
        config = get_config(workspace_path)
        return config.to_dict()
    except ImportError:
        # Fallback for when config module is not available
        config_path = Path(workspace_path) / "workspace.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


def run_tests(
    repo_path: str,
    test_command: Optional[str] = None,
    timeout: int = DEFAULT_TEST_TIMEOUT,
    workspace_path: Optional[str] = None
) -> dict:
    """
    Run tests for a repository.

    Args:
        repo_path: Path to the repository or worktree
        test_command: Specific test command to run (auto-detect if None)
        timeout: Test timeout in seconds
        workspace_path: Optional workspace path for config

    Returns:
        dict with test results
    """
    try:
        repo = validate_path(repo_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e)
        }

    if not repo.exists():
        return make_error(
            f"Repository path does not exist: {repo}",
            hint="Check if the path is correct.",
            recovery_options=[
                "Verify the repository path exists",
                "Initialize workspace if needed: operator init"
            ],
            error_code="REPO_NOT_FOUND",
            repo_path=str(repo)
        )

    # Load config for custom test command
    config = {}
    if workspace_path:
        config = load_workspace_config(workspace_path)

    # Determine test command
    if test_command:
        cmd = test_command
        detected = None
    elif config.get("test_command"):
        cmd = config["test_command"]
        detected = {"type": "config", "detected_by": "workspace.json"}
    else:
        detected = detect_test_command(str(repo))
        if detected:
            cmd = find_working_test_command(str(repo), detected["commands"])
        else:
            return test_detection_failed_error(str(repo))

    # Use config timeout if available
    if config.get("test_timeout"):
        timeout = config["test_timeout"]

    # Run the tests
    result = {
        "success": False,
        "command": cmd,
        "detected": detected,
        "repo_path": str(repo)
    }

    returncode, stdout, stderr, duration = run_command(cmd, str(repo), timeout)

    result["returncode"] = returncode
    result["duration"] = round(duration, 2)
    result["stdout"] = stdout[-5000:] if len(stdout) > 5000 else stdout  # Limit output
    result["stderr"] = stderr[-2000:] if len(stderr) > 2000 else stderr

    if returncode == 0:
        result["success"] = True
        result["message"] = f"Tests passed in {result['duration']}s"
    elif returncode == -1:
        # Test execution failed or timed out
        timeout_result = test_timeout_error(cmd, timeout)
        result["success"] = False
        result["error"] = timeout_result["error"]
        result["hint"] = timeout_result.get("hint")
        result["recovery_options"] = timeout_result.get("recovery_options", [])
        result["message"] = stderr
    else:
        # Tests failed
        failed_result = tests_failed_error(cmd, returncode, duration, "execution")
        result["success"] = False
        result["error"] = failed_result["error"]
        result["hint"] = failed_result.get("hint")
        result["recovery_options"] = failed_result.get("recovery_options", [])
        result["message"] = "Tests failed. Check stdout/stderr for details."

    return result


def verify_tests_pass(
    repo_path: str,
    test_command: Optional[str] = None,
    timeout: int = DEFAULT_TEST_TIMEOUT,
    workspace_path: Optional[str] = None
) -> dict:
    """
    Verify that tests pass. Returns a simple pass/fail result.

    Args:
        repo_path: Path to the repository or worktree
        test_command: Specific test command to run (auto-detect if None)
        timeout: Test timeout in seconds
        workspace_path: Optional workspace path for config

    Returns:
        dict with pass/fail status
    """
    result = run_tests(repo_path, test_command, timeout, workspace_path)

    return {
        "passed": result["success"],
        "command": result.get("command"),
        "duration": result.get("duration"),
        "error": result.get("error"),
        "message": result.get("message")
    }


def run_tests_with_retry(
    repo_path: str,
    test_command: Optional[str] = None,
    timeout: int = DEFAULT_TEST_TIMEOUT,
    max_retries: int = 2,
    workspace_path: Optional[str] = None
) -> dict:
    """
    Run tests with retry for flaky tests.

    Args:
        repo_path: Path to the repository or worktree
        test_command: Specific test command to run
        timeout: Test timeout in seconds
        max_retries: Maximum number of retries
        workspace_path: Optional workspace path for config

    Returns:
        dict with test results
    """
    attempts = []

    for attempt in range(max_retries + 1):
        result = run_tests(repo_path, test_command, timeout, workspace_path)
        attempts.append({
            "attempt": attempt + 1,
            "success": result["success"],
            "duration": result.get("duration"),
            "error": result.get("error")
        })

        if result["success"]:
            result["attempts"] = attempts
            result["message"] = f"Tests passed on attempt {attempt + 1}"
            return result

    # All attempts failed
    result["attempts"] = attempts
    result["message"] = f"Tests failed after {max_retries + 1} attempts"
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: test_runner.py <command> [args]")
        print("Commands:")
        print("  detect <repo_path>         - Detect test command for repo")
        print("  run <repo_path> [command]  - Run tests")
        print("  verify <repo_path>         - Verify tests pass (simple pass/fail)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "detect":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
        result = detect_test_command(repo_path)
        if result:
            print(f"Detected: {result['type']}")
            print(f"Commands: {', '.join(result['commands'])}")
            print(f"Detected by: {result['detected_by']}")
        else:
            print("Could not detect test framework")
            sys.exit(1)

    elif command == "run":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
        test_cmd = sys.argv[3] if len(sys.argv) > 3 else None
        result = run_tests(repo_path, test_cmd)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)

    elif command == "verify":
        repo_path = sys.argv[2] if len(sys.argv) > 2 else "."
        result = verify_tests_pass(repo_path)
        if result["passed"]:
            print(f"✓ Tests passed in {result['duration']}s")
        else:
            print(f"✗ Tests failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
