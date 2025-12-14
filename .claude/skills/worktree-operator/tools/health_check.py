#!/usr/bin/env python3
"""
Health check utilities for monitoring sub-agent status.

Provides mechanism to track sub-agent lifecycle: start, heartbeat, completion.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from validation import ValidationError, validate_task_name, validate_path

# Import logging utilities
from logging_config import get_logger

# Import error utilities
from errors import make_error, task_not_found_error, subagent_timeout_error

# Module logger
logger = get_logger("health_check")


# Status constants
STATUS_STARTING = "starting"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Default timeouts (in seconds)
DEFAULT_HEARTBEAT_INTERVAL = 60
DEFAULT_HEARTBEAT_TIMEOUT = 600  # 10 minutes


def _get_health_check_timeout(workspace_path: str) -> int:
    """Get health check timeout from config or use default."""
    try:
        from config import get_config_value
        return get_config_value(workspace_path, "health_check_timeout", DEFAULT_HEARTBEAT_TIMEOUT)
    except ImportError:
        return DEFAULT_HEARTBEAT_TIMEOUT


class SubagentStatus:
    """Represents the status of a sub-agent."""

    def __init__(
        self,
        task_name: str,
        status: str = STATUS_STARTING,
        progress: str = "Initializing",
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        last_heartbeat: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        self.task_name = task_name
        self.status = status
        self.progress = progress
        self.error = error
        self.started_at = started_at or datetime.now()
        self.last_heartbeat = last_heartbeat or datetime.now()
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_name": self.task_name,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SubagentStatus":
        """Create from dictionary."""
        return cls(
            task_name=data.get("task_name", "unknown"),
            status=data.get("status", STATUS_STARTING),
            progress=data.get("progress", "Unknown"),
            error=data.get("error"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]) if data.get("last_heartbeat") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )

    def is_healthy(self, timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT) -> bool:
        """Check if sub-agent is healthy (recent heartbeat)."""
        if self.status in (STATUS_COMPLETED, STATUS_FAILED):
            return True  # Terminal states are "healthy" in the sense of not hung

        if not self.last_heartbeat:
            return False

        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < timeout_seconds

    def time_since_heartbeat(self) -> Optional[float]:
        """Get seconds since last heartbeat."""
        if not self.last_heartbeat:
            return None
        return (datetime.now() - self.last_heartbeat).total_seconds()

    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()


def get_status_file_path(task_name: str, workspace_path: str = ".") -> Path:
    """Get path to the status file for a task."""
    workspace = Path(workspace_path).resolve()
    task_folder = workspace / f"task-{task_name}"
    return task_folder / ".subagent-status.json"


def write_status(
    task_name: str,
    status: str,
    progress: str = "Working",
    error: Optional[str] = None,
    workspace_path: str = "."
) -> dict:
    """
    Write or update sub-agent status file.

    Args:
        task_name: Name of the task
        status: Current status (starting, running, completed, failed)
        progress: Description of current activity
        error: Error message if failed
        workspace_path: Path to workspace

    Returns:
        dict with result
    """
    try:
        task_name = validate_task_name(task_name)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e)
        }

    status_file = get_status_file_path(task_name, str(workspace))
    task_folder = status_file.parent

    if not task_folder.exists():
        return task_not_found_error(task_name, str(task_folder))

    # Read existing status or create new
    if status_file.exists():
        try:
            with open(status_file, 'r') as f:
                data = json.load(f)
            subagent_status = SubagentStatus.from_dict(data)
        except Exception:
            subagent_status = SubagentStatus(task_name)
    else:
        subagent_status = SubagentStatus(task_name)

    # Update status
    subagent_status.status = status
    subagent_status.progress = progress
    subagent_status.last_heartbeat = datetime.now()

    if error:
        subagent_status.error = error

    if status in (STATUS_COMPLETED, STATUS_FAILED):
        subagent_status.completed_at = datetime.now()

    # Write status file
    try:
        with open(status_file, 'w') as f:
            json.dump(subagent_status.to_dict(), f, indent=2)

        return {
            "success": True,
            "status_file": str(status_file),
            "status": subagent_status.to_dict()
        }
    except Exception as e:
        return make_error(
            f"Failed to write status file: {e}",
            hint="Check file permissions in the task folder.",
            recovery_options=[
                f"Check permissions: ls -la {status_file.parent}",
                "Ensure the task folder is writable"
            ],
            error_code="STATUS_WRITE_FAILED",
            status_file=str(status_file)
        )


def read_status(task_name: str, workspace_path: str = ".") -> dict:
    """
    Read sub-agent status for a task.

    Args:
        task_name: Name of the task
        workspace_path: Path to workspace

    Returns:
        dict with status information
    """
    try:
        task_name = validate_task_name(task_name)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e)
        }

    status_file = get_status_file_path(task_name, str(workspace))

    if not status_file.exists():
        return {
            "success": True,
            "exists": False,
            "status": None,
            "message": "No sub-agent has been started for this task"
        }

    try:
        with open(status_file, 'r') as f:
            data = json.load(f)

        subagent_status = SubagentStatus.from_dict(data)

        return {
            "success": True,
            "exists": True,
            "status": subagent_status.to_dict(),
            "is_healthy": subagent_status.is_healthy(),
            "time_since_heartbeat": subagent_status.time_since_heartbeat(),
            "duration": subagent_status.duration()
        }
    except Exception as e:
        return make_error(
            f"Failed to read status file: {e}",
            hint="The status file may be corrupted or inaccessible.",
            recovery_options=[
                f"Check file: cat {status_file}",
                "Remove corrupted status file and restart sub-agent"
            ],
            error_code="STATUS_READ_FAILED",
            status_file=str(status_file)
        )


def check_health(
    task_name: str,
    workspace_path: str = ".",
    timeout_seconds: int = None
) -> dict:
    """
    Check health of a sub-agent.

    Args:
        task_name: Name of the task
        workspace_path: Path to workspace
        timeout_seconds: Heartbeat timeout in seconds (uses config if None)

    Returns:
        dict with health status
    """
    # Use config timeout if not specified
    if timeout_seconds is None:
        timeout_seconds = _get_health_check_timeout(workspace_path)

    status_result = read_status(task_name, workspace_path)

    if not status_result["success"]:
        return status_result

    if not status_result["exists"]:
        return {
            "success": True,
            "healthy": None,
            "status": "not_started",
            "message": "No sub-agent has been started"
        }

    status_data = status_result["status"]
    subagent_status = SubagentStatus.from_dict(status_data)

    is_healthy = subagent_status.is_healthy(timeout_seconds)
    time_since = subagent_status.time_since_heartbeat()

    result = {
        "success": True,
        "healthy": is_healthy,
        "status": subagent_status.status,
        "progress": subagent_status.progress,
        "time_since_heartbeat": time_since,
        "duration": subagent_status.duration()
    }

    # Add warnings/messages based on status
    if subagent_status.status == STATUS_COMPLETED:
        result["message"] = "Sub-agent completed successfully"
    elif subagent_status.status == STATUS_FAILED:
        result["message"] = f"Sub-agent failed: {subagent_status.error}"
        result["error"] = subagent_status.error
    elif not is_healthy:
        timeout_result = subagent_timeout_error(task_name, timeout_seconds)
        result["message"] = f"Sub-agent may be hung (no heartbeat in {int(time_since)}s)"
        result["warning"] = timeout_result.get("hint")
        result["recovery_options"] = timeout_result.get("recovery_options", [])
    else:
        result["message"] = f"Sub-agent running: {subagent_status.progress}"

    return result


def heartbeat(
    task_name: str,
    progress: str = "Working",
    workspace_path: str = "."
) -> dict:
    """
    Send heartbeat for a running sub-agent.

    Args:
        task_name: Name of the task
        progress: Current progress description
        workspace_path: Path to workspace

    Returns:
        dict with result
    """
    return write_status(
        task_name=task_name,
        status=STATUS_RUNNING,
        progress=progress,
        workspace_path=workspace_path
    )


def mark_started(task_name: str, workspace_path: str = ".") -> dict:
    """Mark sub-agent as started."""
    return write_status(
        task_name=task_name,
        status=STATUS_STARTING,
        progress="Initializing",
        workspace_path=workspace_path
    )


def mark_running(task_name: str, progress: str = "Working", workspace_path: str = ".") -> dict:
    """Mark sub-agent as running with progress."""
    return write_status(
        task_name=task_name,
        status=STATUS_RUNNING,
        progress=progress,
        workspace_path=workspace_path
    )


def mark_completed(task_name: str, workspace_path: str = ".") -> dict:
    """Mark sub-agent as completed."""
    return write_status(
        task_name=task_name,
        status=STATUS_COMPLETED,
        progress="Completed",
        workspace_path=workspace_path
    )


def mark_failed(task_name: str, error: str, workspace_path: str = ".") -> dict:
    """Mark sub-agent as failed."""
    return write_status(
        task_name=task_name,
        status=STATUS_FAILED,
        progress="Failed",
        error=error,
        workspace_path=workspace_path
    )


def list_all_status(workspace_path: str = ".") -> dict:
    """
    List status of all tasks in workspace.

    Args:
        workspace_path: Path to workspace

    Returns:
        dict with list of task statuses
    """
    try:
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e)
        }

    if not workspace.exists():
        return {
            "success": True,
            "tasks": []
        }

    tasks = []
    for item in sorted(workspace.iterdir()):
        if item.is_dir() and item.name.startswith("task-"):
            task_name = item.name[5:]  # Remove "task-" prefix
            status_result = read_status(task_name, str(workspace))

            task_info = {
                "task_name": task_name,
                "has_status": status_result.get("exists", False)
            }

            if status_result.get("exists"):
                task_info.update({
                    "status": status_result["status"]["status"],
                    "progress": status_result["status"]["progress"],
                    "is_healthy": status_result.get("is_healthy"),
                    "time_since_heartbeat": status_result.get("time_since_heartbeat")
                })
            else:
                task_info["status"] = "not_started"

            tasks.append(task_info)

    return {
        "success": True,
        "tasks": tasks,
        "total": len(tasks),
        "running": sum(1 for t in tasks if t.get("status") == STATUS_RUNNING),
        "completed": sum(1 for t in tasks if t.get("status") == STATUS_COMPLETED),
        "failed": sum(1 for t in tasks if t.get("status") == STATUS_FAILED)
    }


def cleanup_status(task_name: str, workspace_path: str = ".") -> dict:
    """
    Remove status file for a task.

    Args:
        task_name: Name of the task
        workspace_path: Path to workspace

    Returns:
        dict with result
    """
    try:
        task_name = validate_task_name(task_name)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e)
        }

    status_file = get_status_file_path(task_name, str(workspace))

    if not status_file.exists():
        return {
            "success": True,
            "message": "Status file does not exist"
        }

    try:
        status_file.unlink()
        return {
            "success": True,
            "message": f"Status file removed: {status_file}"
        }
    except Exception as e:
        return make_error(
            f"Failed to remove status file: {e}",
            hint="Check file permissions.",
            recovery_options=[
                f"Remove manually: rm {status_file}",
                f"Check permissions: ls -la {status_file}"
            ],
            error_code="STATUS_CLEANUP_FAILED",
            status_file=str(status_file)
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: health_check.py <command> [args]")
        print("Commands:")
        print("  status <task_name> [workspace]  - Get status of a task")
        print("  health <task_name> [workspace]  - Check health of a task")
        print("  list [workspace]                - List all task statuses")
        print("  heartbeat <task_name> <progress> [workspace] - Send heartbeat")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        task_name = sys.argv[2] if len(sys.argv) > 2 else None
        workspace = sys.argv[3] if len(sys.argv) > 3 else "."
        if not task_name:
            print("Error: task_name required")
            sys.exit(1)
        result = read_status(task_name, workspace)
        print(json.dumps(result, indent=2))

    elif command == "health":
        task_name = sys.argv[2] if len(sys.argv) > 2 else None
        workspace = sys.argv[3] if len(sys.argv) > 3 else "."
        if not task_name:
            print("Error: task_name required")
            sys.exit(1)
        result = check_health(task_name, workspace)
        print(json.dumps(result, indent=2))

    elif command == "list":
        workspace = sys.argv[2] if len(sys.argv) > 2 else "."
        result = list_all_status(workspace)
        print(json.dumps(result, indent=2))

    elif command == "heartbeat":
        task_name = sys.argv[2] if len(sys.argv) > 2 else None
        progress = sys.argv[3] if len(sys.argv) > 3 else "Working"
        workspace = sys.argv[4] if len(sys.argv) > 4 else "."
        if not task_name:
            print("Error: task_name required")
            sys.exit(1)
        result = heartbeat(task_name, progress, workspace)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
