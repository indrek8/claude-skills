#!/usr/bin/env python3
"""
File-based locking for workspace operations.

Prevents race conditions when multiple processes attempt concurrent operations
on the same workspace (e.g., creating tasks, accepting changes, syncing).
"""

import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Generator

# Import logging utilities - use lazy import to avoid circular dependencies
_logger = None

def _get_logger():
    """Get logger lazily to avoid circular imports."""
    global _logger
    if _logger is None:
        from logging_config import get_logger
        _logger = get_logger("locking")
    return _logger

# Default lock timeout (1 hour for stale lock detection)
DEFAULT_LOCK_TIMEOUT = 3600  # seconds

# Lock acquisition timeout (how long to wait for lock)
DEFAULT_ACQUIRE_TIMEOUT = 30  # seconds


def _get_lock_timeout(workspace_path: str) -> int:
    """Get lock timeout from config or use default."""
    try:
        from config import get_config_value
        return get_config_value(workspace_path, "lock_timeout", DEFAULT_ACQUIRE_TIMEOUT)
    except ImportError:
        return DEFAULT_ACQUIRE_TIMEOUT


class LockError(Exception):
    """Exception raised when lock operations fail."""

    def __init__(
        self,
        message: str,
        lock_info: Optional[dict] = None,
        hint: Optional[str] = None,
        recovery_options: Optional[list] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.lock_info = lock_info
        self.hint = hint
        self.recovery_options = recovery_options or []
        self.error_code = error_code

    def to_dict(self) -> dict:
        result = {
            "success": False,
            "error": self.message,
            "lock_error": True
        }
        if self.lock_info:
            result["lock_info"] = self.lock_info
        if self.hint:
            result["hint"] = self.hint
        if self.recovery_options:
            result["recovery_options"] = self.recovery_options
        if self.error_code:
            result["error_code"] = self.error_code
        return result


class WorkspaceLock:
    """
    File-based lock for workspace operations.

    Uses both flock (for cross-process safety) and a JSON info file
    (for debugging and stale lock detection).
    """

    def __init__(self, workspace_path: str, operation: str = "unknown"):
        """
        Initialize a workspace lock.

        Args:
            workspace_path: Path to the workspace directory
            operation: Name of the operation acquiring the lock (for debugging)
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.operation = operation
        self.lock_file = self.workspace_path / ".workspace.lock"
        self.info_file = self.workspace_path / ".workspace.lock.info"
        self._lock_fd: Optional[int] = None
        self._acquired = False

    def _get_lock_info(self) -> dict:
        """Create lock info dictionary for the current process."""
        return {
            "pid": os.getpid(),
            "operation": self.operation,
            "acquired_at": datetime.utcnow().isoformat(),
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
        }

    def _write_lock_info(self):
        """Write lock info to the info file."""
        try:
            with open(self.info_file, 'w') as f:
                json.dump(self._get_lock_info(), f, indent=2)
        except Exception:
            pass  # Best effort - info file is for debugging only

    def _read_lock_info(self) -> Optional[dict]:
        """Read lock info from the info file."""
        try:
            if self.info_file.exists():
                with open(self.info_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _remove_lock_info(self):
        """Remove the lock info file."""
        try:
            if self.info_file.exists():
                self.info_file.unlink()
        except Exception:
            pass

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with the given PID is running."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _is_lock_stale(self, timeout: int = DEFAULT_LOCK_TIMEOUT) -> bool:
        """
        Check if the current lock is stale.

        A lock is considered stale if:
        - The holding process is no longer running, OR
        - The lock was acquired more than `timeout` seconds ago
        """
        info = self._read_lock_info()
        if not info:
            return False

        # Check if process is still running
        pid = info.get("pid")
        if pid and not self._is_process_running(pid):
            return True

        # Check if lock is too old
        acquired_at = info.get("acquired_at")
        if acquired_at:
            try:
                acquired_time = datetime.fromisoformat(acquired_at)
                if datetime.utcnow() - acquired_time > timedelta(seconds=timeout):
                    return True
            except Exception:
                pass

        return False

    def _clean_stale_lock(self) -> bool:
        """
        Clean up a stale lock.

        Returns:
            True if a stale lock was cleaned, False otherwise
        """
        if self._is_lock_stale():
            info = self._read_lock_info()
            try:
                self.lock_file.unlink()
                self._remove_lock_info()
                return True
            except Exception:
                pass
        return False

    def acquire(self, timeout: int = DEFAULT_ACQUIRE_TIMEOUT, blocking: bool = True) -> bool:
        """
        Acquire the workspace lock.

        Args:
            timeout: Maximum time to wait for lock acquisition (seconds)
            blocking: If True, wait for lock; if False, fail immediately if locked

        Returns:
            True if lock was acquired

        Raises:
            LockError: If lock cannot be acquired
        """
        if self._acquired:
            return True

        # Ensure workspace directory exists
        if not self.workspace_path.exists():
            raise LockError(
                f"Workspace does not exist: {self.workspace_path}",
                hint="Initialize the workspace first with 'operator init'.",
                recovery_options=[
                    f"Create directory: mkdir -p {self.workspace_path}",
                    "Initialize workspace: operator init <repo_url> <branch>"
                ],
                error_code="WORKSPACE_NOT_FOUND"
            )

        # Try to clean stale lock first
        self._clean_stale_lock()

        start_time = time.time()
        while True:
            try:
                # Open/create lock file
                self._lock_fd = os.open(
                    str(self.lock_file),
                    os.O_RDWR | os.O_CREAT,
                    0o644
                )

                # Try to acquire exclusive lock
                if blocking:
                    flags = fcntl.LOCK_EX | fcntl.LOCK_NB
                else:
                    flags = fcntl.LOCK_EX | fcntl.LOCK_NB

                fcntl.flock(self._lock_fd, flags)

                # Lock acquired
                self._acquired = True
                self._write_lock_info()
                _get_logger().debug(f"acquire: Lock acquired for operation '{self.operation}' on {self.workspace_path}")
                return True

            except (OSError, IOError) as e:
                # Lock is held by another process
                if self._lock_fd is not None:
                    try:
                        os.close(self._lock_fd)
                    except Exception:
                        pass
                    self._lock_fd = None

                if not blocking:
                    lock_info = self._read_lock_info()
                    _get_logger().warning(f"acquire: Lock held by another operation: {lock_info}")
                    recovery = [
                        "Wait for the other operation to complete",
                        "Check lock status: python tools/locking.py status"
                    ]
                    if lock_info and lock_info.get("pid"):
                        recovery.append(f"Check if process {lock_info['pid']} is still running")
                    recovery.append("Force unlock (if stale): python tools/locking.py unlock")

                    raise LockError(
                        "Workspace is locked by another operation",
                        lock_info=lock_info,
                        hint="Another process is currently modifying the workspace.",
                        recovery_options=recovery,
                        error_code="LOCK_HELD"
                    )

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    lock_info = self._read_lock_info()
                    _get_logger().error(f"acquire: Timeout waiting for lock after {timeout}s, held by: {lock_info}")
                    raise LockError(
                        f"Timeout waiting for workspace lock after {timeout}s",
                        lock_info=lock_info,
                        hint="Another operation may be stuck or taking too long.",
                        recovery_options=[
                            "Check what operation is running",
                            "Wait and retry",
                            "Force unlock if the operation is stuck: python tools/locking.py unlock"
                        ],
                        error_code="LOCK_TIMEOUT"
                    )

                # Wait a bit and retry
                time.sleep(0.5)

    def release(self):
        """Release the workspace lock."""
        if not self._acquired:
            return

        try:
            if self._lock_fd is not None:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None
        except Exception:
            pass

        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception:
            pass

        self._remove_lock_info()
        self._acquired = False
        _get_logger().debug(f"release: Lock released for operation '{self.operation}' on {self.workspace_path}")

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False


@contextmanager
def workspace_lock(
    workspace_path: str,
    operation: str = "unknown",
    timeout: int = None,
    blocking: bool = True
) -> Generator[WorkspaceLock, None, None]:
    """
    Context manager for acquiring a workspace lock.

    Args:
        workspace_path: Path to the workspace directory
        operation: Name of the operation (for debugging)
        timeout: Maximum time to wait for lock (uses config if None)
        blocking: Whether to wait for lock or fail immediately

    Yields:
        WorkspaceLock instance

    Raises:
        LockError: If lock cannot be acquired

    Example:
        with workspace_lock("/path/to/workspace", "accept_task") as lock:
            # Perform exclusive operations
            pass
    """
    # Use config timeout if not specified
    if timeout is None:
        timeout = _get_lock_timeout(workspace_path)

    lock = WorkspaceLock(workspace_path, operation)
    try:
        lock.acquire(timeout=timeout, blocking=blocking)
        yield lock
    finally:
        lock.release()


def check_lock_status(workspace_path: str) -> dict:
    """
    Check the current lock status of a workspace.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        dict with lock status information
    """
    workspace = Path(workspace_path).resolve()
    lock_file = workspace / ".workspace.lock"
    info_file = workspace / ".workspace.lock.info"

    result = {
        "workspace": str(workspace),
        "locked": False,
        "stale": False,
        "info": None
    }

    if not lock_file.exists():
        return result

    # Lock file exists - check if actually locked
    try:
        fd = os.open(str(lock_file), os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Lock acquired - it wasn't actually held
            fcntl.flock(fd, fcntl.LOCK_UN)
            result["locked"] = False
            result["stale"] = True
        except (OSError, IOError):
            # Lock is held
            result["locked"] = True
        finally:
            os.close(fd)
    except Exception:
        result["locked"] = False

    # Read lock info
    if info_file.exists():
        try:
            with open(info_file, 'r') as f:
                result["info"] = json.load(f)
        except Exception:
            pass

    # Check if stale (process not running)
    if result["locked"] and result["info"]:
        pid = result["info"].get("pid")
        if pid:
            try:
                os.kill(pid, 0)
            except OSError:
                result["stale"] = True

    return result


def force_unlock(workspace_path: str) -> dict:
    """
    Force remove a workspace lock.

    WARNING: Only use this if you're sure no other operation is running.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        dict with unlock result
    """
    workspace = Path(workspace_path).resolve()
    lock_file = workspace / ".workspace.lock"
    info_file = workspace / ".workspace.lock.info"

    result = {
        "success": True,
        "removed_lock": False,
        "removed_info": False,
        "previous_info": None
    }

    # Read current info for reporting
    if info_file.exists():
        try:
            with open(info_file, 'r') as f:
                result["previous_info"] = json.load(f)
        except Exception:
            pass

    # Remove lock file
    if lock_file.exists():
        try:
            lock_file.unlink()
            result["removed_lock"] = True
        except Exception as e:
            result["success"] = False
            result["error"] = f"Failed to remove lock file: {e}"
            return result

    # Remove info file
    if info_file.exists():
        try:
            info_file.unlink()
            result["removed_info"] = True
        except Exception:
            pass  # Non-critical

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: locking.py <command> [workspace_path]")
        print("Commands:")
        print("  status [path]    - Check lock status")
        print("  unlock [path]    - Force unlock (WARNING: dangerous)")
        print("  test [path]      - Test lock acquisition")
        sys.exit(1)

    command = sys.argv[1]
    workspace_path = sys.argv[2] if len(sys.argv) > 2 else "."

    if command == "status":
        status = check_lock_status(workspace_path)
        print(json.dumps(status, indent=2))

    elif command == "unlock":
        print("WARNING: Force unlocking may corrupt workspace state!")
        print("Only use this if you're SURE no operation is running.")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            result = force_unlock(workspace_path)
            print(json.dumps(result, indent=2))
        else:
            print("Cancelled")
            sys.exit(1)

    elif command == "test":
        print(f"Testing lock acquisition on {workspace_path}...")
        try:
            with workspace_lock(workspace_path, "test", timeout=5) as lock:
                print("Lock acquired successfully!")
                print("Holding lock for 3 seconds...")
                time.sleep(3)
        except LockError as e:
            print(f"Lock error: {e.message}")
            if e.lock_info:
                print(f"Lock info: {json.dumps(e.lock_info, indent=2)}")
            sys.exit(1)
        print("Lock released")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
