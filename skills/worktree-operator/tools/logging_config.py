#!/usr/bin/env python3
"""
Logging configuration for worktree operator tools.

Provides structured logging with file rotation, timestamps, and operation context.
Supports multi-process safety with separate log files for operator and sub-agents.
"""

import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# Default configuration
DEFAULT_LOG_FILE = "workspace.log"
DEFAULT_SUBAGENT_LOG_FILE = "subagent.log"
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5

# Log format: timestamp [level] operation: message
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Module-level logger cache
_loggers: dict = {}
_log_file_handler: Optional[logging.Handler] = None
_initialized = False


def find_workspace_root(start_path: Optional[Path] = None, max_levels: int = 10) -> Optional[Path]:
    """
    Find the workspace root by looking for plan.md.

    Traverses up from start_path (or cwd) looking for a directory containing plan.md.

    Args:
        start_path: Starting path for search (default: current working directory)
        max_levels: Maximum number of parent directories to check (default: 10)

    Returns:
        Path to workspace root directory, or None if not found
    """
    current = start_path or Path.cwd()

    # Check current directory and parents
    for _ in range(max_levels):
        if (current / "plan.md").exists():
            return current

        # Move to parent
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def find_task_folder(start_path: Optional[Path] = None, max_levels: int = 5) -> Optional[Path]:
    """
    Find the task folder from a worktree path.

    Looks for a parent directory that contains spec.md, which indicates a task folder.
    Typically matches pattern: task-{name}/worktree/...

    Args:
        start_path: Starting path for search (default: current working directory)
        max_levels: Maximum number of parent directories to check (default: 5)

    Returns:
        Path to task folder, or None if not in a task context
    """
    current = start_path or Path.cwd()

    # Check if we're inside a worktree by looking for parent with spec.md
    for _ in range(max_levels):
        # Check if current directory is 'worktree' and parent has spec.md
        if current.name == "worktree" and (current.parent / "spec.md").exists():
            return current.parent

        # Also check if parent has spec.md (we might be deeper in worktree)
        if (current / "spec.md").exists():
            return current

        # Move to parent
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def detect_log_context(start_path: Optional[Path] = None) -> Tuple[str, Optional[Path]]:
    """
    Detect whether we're running as operator or sub-agent.

    Args:
        start_path: Starting path for detection (default: current working directory)

    Returns:
        Tuple of (context_type, log_directory) where:
        - context_type is "operator" or "subagent"
        - log_directory is the directory where logs should be written
    """
    # First check if we're in a task worktree
    task_folder = find_task_folder(start_path)
    if task_folder:
        return "subagent", task_folder

    # Not in worktree, find workspace root for operator logs
    workspace = find_workspace_root(start_path)
    if workspace:
        return "operator", workspace

    # Fallback to current directory if no workspace found
    return "operator", start_path or Path.cwd()


def setup_logging(
    log_file: Optional[str] = None,
    log_level: int = DEFAULT_LOG_LEVEL,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    workspace_path: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging with rotating file handler.

    Uses auto-detection to determine if running as operator or sub-agent,
    and sets up logging in the appropriate location.

    Args:
        log_file: Path to log file (explicit override)
        log_level: Logging level (default: INFO)
        max_bytes: Maximum log file size before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        workspace_path: Workspace directory for log file (explicit override)

    Returns:
        Root logger for the operator tools
    """
    global _log_file_handler, _initialized

    # Determine log file path
    context_type = "unknown"  # Default value for explicit log_file case

    if log_file:
        log_path = Path(log_file)
        # Try to detect context even when explicit log file provided
        detected_type, _ = detect_log_context()
        context_type = detected_type
    elif workspace_path:
        # Explicit workspace path provided - always use workspace.log
        # (caller is explicitly providing workspace, not auto-detecting)
        context_type = "operator"
        log_path = Path(workspace_path) / DEFAULT_LOG_FILE
    else:
        # Auto-detect context and location
        context_type, log_dir = detect_log_context()
        if context_type == "subagent":
            log_path = log_dir / DEFAULT_SUBAGENT_LOG_FILE
        else:
            log_path = log_dir / DEFAULT_LOG_FILE

    # Ensure parent directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create or get the root logger for operator tools
    root_logger = logging.getLogger("operator")
    root_logger.setLevel(log_level)

    # Remove existing handlers if reinitializing
    if _initialized:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    _log_file_handler = file_handler

    _initialized = True

    # Log initialization
    root_logger.info(f"Logging initialized: {log_path} (context: {context_type})")

    return root_logger


def setup_subagent_logging(
    task_name: str,
    workspace_path: str,
    log_level: int = DEFAULT_LOG_LEVEL,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT
) -> logging.Logger:
    """
    Explicitly set up logging for a sub-agent.

    This function should be called by sub-agents at startup to ensure logs
    go to the task-specific log file instead of the main workspace log.

    Args:
        task_name: Name of the task (e.g., "fix-bug")
        workspace_path: Path to the workspace root
        log_level: Logging level (default: INFO)
        max_bytes: Maximum log file size before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)

    Returns:
        Root logger configured for the sub-agent
    """
    # Build path to task folder
    task_folder = Path(workspace_path) / f"task-{task_name}"
    log_path = task_folder / DEFAULT_SUBAGENT_LOG_FILE

    # Ensure task folder exists
    task_folder.mkdir(parents=True, exist_ok=True)

    # Use setup_logging with explicit log file
    return setup_logging(
        log_file=str(log_path),
        log_level=log_level,
        max_bytes=max_bytes,
        backup_count=backup_count
    )


def get_logger(name: str, task_name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger for a specific operation/module.

    Args:
        name: Name of the operation or module (e.g., "workspace", "task", "git_ops")
        task_name: Optional task name to include in log context

    Returns:
        Logger instance configured for the operation
    """
    global _initialized

    # Ensure logging is initialized
    if not _initialized:
        setup_logging()

    # Build logger name
    logger_name = f"operator.{name}"
    if task_name:
        logger_name = f"operator.{name}.{task_name}"

    # Check cache
    if logger_name in _loggers:
        return _loggers[logger_name]

    # Create new logger
    logger = logging.getLogger(logger_name)
    _loggers[logger_name] = logger

    return logger


def log_operation_start(logger: logging.Logger, operation: str, **context):
    """
    Log the start of an operation with context.

    Args:
        logger: Logger instance
        operation: Name of the operation
        **context: Additional context to log
    """
    ctx_str = ", ".join(f"{k}={v}" for k, v in context.items()) if context else ""
    if ctx_str:
        logger.info(f"Starting {operation}: {ctx_str}")
    else:
        logger.info(f"Starting {operation}")


def log_operation_success(logger: logging.Logger, operation: str, message: str = ""):
    """
    Log successful completion of an operation.

    Args:
        logger: Logger instance
        operation: Name of the operation
        message: Optional success message
    """
    if message:
        logger.info(f"{operation} succeeded: {message}")
    else:
        logger.info(f"{operation} succeeded")


def log_operation_failure(
    logger: logging.Logger,
    operation: str,
    error: str,
    exc_info: bool = False
):
    """
    Log operation failure with optional stack trace.

    Args:
        logger: Logger instance
        operation: Name of the operation
        error: Error message
        exc_info: If True, include stack trace
    """
    if exc_info:
        logger.error(f"{operation} failed: {error}", exc_info=True)
    else:
        logger.error(f"{operation} failed: {error}")


def log_exception(logger: logging.Logger, operation: str, exc: Exception):
    """
    Log an exception with full stack trace.

    Args:
        logger: Logger instance
        operation: Name of the operation
        exc: Exception that was raised
    """
    logger.error(
        f"{operation} raised exception: {type(exc).__name__}: {exc}",
        exc_info=True
    )


def log_warning(logger: logging.Logger, operation: str, message: str):
    """
    Log a warning message.

    Args:
        logger: Logger instance
        operation: Name of the operation
        message: Warning message
    """
    logger.warning(f"{operation}: {message}")


def log_debug(logger: logging.Logger, operation: str, message: str):
    """
    Log a debug message.

    Args:
        logger: Logger instance
        operation: Name of the operation
        message: Debug message
    """
    logger.debug(f"{operation}: {message}")


class OperationLogger:
    """
    Context manager for logging operation lifecycle.

    Usage:
        with OperationLogger(logger, "accept_task", task="fix-bug") as op:
            # Do work
            op.info("Rebasing...")
            # If exception occurs, it's logged automatically
    """

    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        log_operation_start(self.logger, self.operation, **self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        duration_str = f"{duration:.2f}s"

        if exc_type is None:
            log_operation_success(self.logger, self.operation, f"completed in {duration_str}")
        else:
            log_exception(self.logger, self.operation, exc_val)
        return False  # Don't suppress exceptions

    def info(self, message: str):
        """Log an info message within the operation."""
        self.logger.info(f"{self.operation}: {message}")

    def debug(self, message: str):
        """Log a debug message within the operation."""
        self.logger.debug(f"{self.operation}: {message}")

    def warning(self, message: str):
        """Log a warning message within the operation."""
        self.logger.warning(f"{self.operation}: {message}")

    def error(self, message: str, exc_info: bool = False):
        """Log an error message within the operation."""
        self.logger.error(f"{self.operation}: {message}", exc_info=exc_info)


def get_log_file_path() -> Optional[str]:
    """
    Get the current log file path.

    Returns:
        Path to the current log file, or None if not initialized
    """
    global _log_file_handler
    if _log_file_handler and hasattr(_log_file_handler, 'baseFilename'):
        return _log_file_handler.baseFilename
    return None


def read_recent_logs(num_lines: int = 100) -> list:
    """
    Read the most recent log entries.

    Args:
        num_lines: Number of recent lines to read

    Returns:
        List of recent log lines
    """
    log_file = get_log_file_path()
    if not log_file or not Path(log_file).exists():
        return []

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-num_lines:]
    except Exception:
        return []


def clear_log_file() -> bool:
    """
    Clear the current log file.

    Returns:
        True if successful, False otherwise
    """
    log_file = get_log_file_path()
    if not log_file:
        return False

    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")

        # Log that we cleared the file
        logger = get_logger("logging_config")
        logger.info("Log file cleared")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Demo usage
    import argparse

    parser = argparse.ArgumentParser(description="Logging configuration utilities")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # setup command
    setup_parser = subparsers.add_parser("setup", help="Initialize logging")
    setup_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    setup_parser.add_argument("--level", default="INFO", help="Log level")

    # read command
    read_parser = subparsers.add_parser("read", help="Read recent logs")
    read_parser.add_argument("--lines", "-n", type=int, default=50, help="Number of lines")

    # path command
    path_parser = subparsers.add_parser("path", help="Show log file path")

    # test command
    test_parser = subparsers.add_parser("test", help="Test logging")
    test_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    args = parser.parse_args()

    if args.command == "setup":
        level = getattr(logging, args.level.upper(), logging.INFO)
        setup_logging(workspace_path=args.workspace, log_level=level)
        print(f"Logging initialized at {get_log_file_path()}")

    elif args.command == "read":
        lines = read_recent_logs(args.lines)
        for line in lines:
            print(line.rstrip())

    elif args.command == "path":
        path = get_log_file_path()
        if path:
            print(path)
        else:
            print("Logging not initialized")
            sys.exit(1)

    elif args.command == "test":
        setup_logging(workspace_path=args.workspace)
        logger = get_logger("test")

        print("Testing logging...")
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")

        with OperationLogger(logger, "test_operation", param="value") as op:
            op.info("Doing some work...")
            op.debug("Debug details...")

        print(f"Log file: {get_log_file_path()}")
        print("\nRecent logs:")
        for line in read_recent_logs(10):
            print(f"  {line.rstrip()}")

    else:
        parser.print_help()
