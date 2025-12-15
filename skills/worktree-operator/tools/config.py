#!/usr/bin/env python3
"""
Workspace configuration module for worktree operator.

Provides loading, validation, and management of workspace.json configuration files.
All configuration values are optional and have sensible defaults.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional, TypedDict, Union

# Import logging utilities - use lazy import to avoid circular dependencies
_logger = None


def _get_logger():
    """Get logger lazily to avoid circular imports."""
    global _logger
    if _logger is None:
        from logging_config import get_logger
        _logger = get_logger("config")
    return _logger


# Configuration file name
CONFIG_FILENAME = "workspace.json"


# Default configuration values
DEFAULT_TEST_COMMAND: Optional[str] = None  # Auto-detect
DEFAULT_TEST_TIMEOUT: int = 300  # 5 minutes
DEFAULT_MODEL: str = "opus"
DEFAULT_HEALTH_CHECK_TIMEOUT: int = 600  # 10 minutes
DEFAULT_LOCK_TIMEOUT: int = 60  # 1 minute for lock acquisition
DEFAULT_AUTO_SYNC_AFTER_ACCEPT: bool = True
DEFAULT_PUSH_AFTER_ACCEPT: bool = True
DEFAULT_DELETE_REMOTE_BRANCH: bool = True
DEFAULT_MAIN_BRANCH: str = "main"
DEFAULT_TICKET_PREFIX: Optional[str] = None


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        hint: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value
        self.hint = hint

    def to_dict(self) -> dict:
        """Convert to error dictionary."""
        result = {
            "success": False,
            "error": self.message,
            "config_error": True
        }
        if self.field:
            result["field"] = self.field
        if self.value is not None:
            result["invalid_value"] = self.value
        if self.hint:
            result["hint"] = self.hint
        return result


@dataclass
class WorkspaceConfig:
    """
    Workspace configuration with typed fields and defaults.

    All fields are optional - missing fields use sensible defaults.
    """

    # Test settings
    test_command: Optional[str] = DEFAULT_TEST_COMMAND
    test_timeout: int = DEFAULT_TEST_TIMEOUT

    # Model settings
    default_model: str = DEFAULT_MODEL

    # Health check settings
    health_check_timeout: int = DEFAULT_HEALTH_CHECK_TIMEOUT

    # Lock settings
    lock_timeout: int = DEFAULT_LOCK_TIMEOUT

    # Accept behavior settings
    auto_sync_after_accept: bool = DEFAULT_AUTO_SYNC_AFTER_ACCEPT
    push_after_accept: bool = DEFAULT_PUSH_AFTER_ACCEPT
    delete_remote_branch: bool = DEFAULT_DELETE_REMOTE_BRANCH

    # Branch settings
    main_branch: str = DEFAULT_MAIN_BRANCH
    ticket_prefix: Optional[str] = DEFAULT_TICKET_PREFIX

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceConfig":
        """
        Create from dictionary with validation.

        Args:
            data: Dictionary with configuration values

        Returns:
            WorkspaceConfig instance

        Raises:
            ConfigValidationError: If validation fails
        """
        config = cls()

        # Validate and set each field
        if "test_command" in data:
            value = data["test_command"]
            if value is not None and not isinstance(value, str):
                raise ConfigValidationError(
                    f"test_command must be a string, got {type(value).__name__}",
                    field="test_command",
                    value=value,
                    hint="Use a shell command like 'npm test' or 'pytest'"
                )
            config.test_command = value

        if "test_timeout" in data:
            value = data["test_timeout"]
            if not isinstance(value, int) or value <= 0:
                raise ConfigValidationError(
                    f"test_timeout must be a positive integer, got {value}",
                    field="test_timeout",
                    value=value,
                    hint="Timeout in seconds, e.g., 300 for 5 minutes"
                )
            config.test_timeout = value

        if "default_model" in data:
            value = data["default_model"]
            valid_models = ["opus", "sonnet", "haiku"]
            if not isinstance(value, str) or value.lower() not in valid_models:
                raise ConfigValidationError(
                    f"default_model must be one of {valid_models}, got '{value}'",
                    field="default_model",
                    value=value,
                    hint="Use 'opus', 'sonnet', or 'haiku'"
                )
            config.default_model = value.lower()

        if "health_check_timeout" in data:
            value = data["health_check_timeout"]
            if not isinstance(value, int) or value <= 0:
                raise ConfigValidationError(
                    f"health_check_timeout must be a positive integer, got {value}",
                    field="health_check_timeout",
                    value=value,
                    hint="Timeout in seconds, e.g., 600 for 10 minutes"
                )
            config.health_check_timeout = value

        if "lock_timeout" in data:
            value = data["lock_timeout"]
            if not isinstance(value, int) or value <= 0:
                raise ConfigValidationError(
                    f"lock_timeout must be a positive integer, got {value}",
                    field="lock_timeout",
                    value=value,
                    hint="Timeout in seconds, e.g., 60 for 1 minute"
                )
            config.lock_timeout = value

        if "auto_sync_after_accept" in data:
            value = data["auto_sync_after_accept"]
            if not isinstance(value, bool):
                raise ConfigValidationError(
                    f"auto_sync_after_accept must be a boolean, got {type(value).__name__}",
                    field="auto_sync_after_accept",
                    value=value,
                    hint="Use true or false"
                )
            config.auto_sync_after_accept = value

        if "push_after_accept" in data:
            value = data["push_after_accept"]
            if not isinstance(value, bool):
                raise ConfigValidationError(
                    f"push_after_accept must be a boolean, got {type(value).__name__}",
                    field="push_after_accept",
                    value=value,
                    hint="Use true or false"
                )
            config.push_after_accept = value

        if "delete_remote_branch" in data:
            value = data["delete_remote_branch"]
            if not isinstance(value, bool):
                raise ConfigValidationError(
                    f"delete_remote_branch must be a boolean, got {type(value).__name__}",
                    field="delete_remote_branch",
                    value=value,
                    hint="Use true or false"
                )
            config.delete_remote_branch = value

        if "main_branch" in data:
            value = data["main_branch"]
            if not isinstance(value, str) or not value.strip():
                raise ConfigValidationError(
                    f"main_branch must be a non-empty string, got '{value}'",
                    field="main_branch",
                    value=value,
                    hint="Use a branch name like 'main' or 'master'"
                )
            config.main_branch = value.strip()

        if "ticket_prefix" in data:
            value = data["ticket_prefix"]
            if value is not None and not isinstance(value, str):
                raise ConfigValidationError(
                    f"ticket_prefix must be a string or null, got {type(value).__name__}",
                    field="ticket_prefix",
                    value=value,
                    hint="Use a prefix like 'K-123' or 'PROJ-'"
                )
            config.ticket_prefix = value

        return config


# Cached configuration per workspace
_config_cache: dict[str, WorkspaceConfig] = {}


def get_config_path(workspace_path: str) -> Path:
    """Get the path to the workspace.json file."""
    return Path(workspace_path).resolve() / CONFIG_FILENAME


def load_config(workspace_path: str, force_reload: bool = False) -> dict:
    """
    Load workspace configuration from workspace.json.

    Args:
        workspace_path: Path to the workspace directory
        force_reload: If True, bypass cache and reload from file

    Returns:
        dict with success status and config or error
    """
    workspace = Path(workspace_path).resolve()
    cache_key = str(workspace)

    # Check cache
    if not force_reload and cache_key in _config_cache:
        return {
            "success": True,
            "config": _config_cache[cache_key],
            "cached": True
        }

    config_path = get_config_path(workspace_path)

    # If config file doesn't exist, return defaults
    if not config_path.exists():
        config = WorkspaceConfig()
        _config_cache[cache_key] = config
        _get_logger().debug(f"load_config: No config file at {config_path}, using defaults")
        return {
            "success": True,
            "config": config,
            "exists": False,
            "message": "Using default configuration (no workspace.json found)"
        }

    # Load and parse config file
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        config = WorkspaceConfig.from_dict(data)
        _config_cache[cache_key] = config
        _get_logger().info(f"load_config: Loaded configuration from {config_path}")

        return {
            "success": True,
            "config": config,
            "exists": True,
            "path": str(config_path)
        }

    except json.JSONDecodeError as e:
        _get_logger().error(f"load_config: Invalid JSON in {config_path}: {e}")
        return {
            "success": False,
            "error": f"Invalid JSON in workspace.json: {e}",
            "hint": "Check the JSON syntax in workspace.json",
            "recovery_options": [
                f"Validate JSON: cat {config_path} | python -m json.tool",
                f"Reset to defaults: python tools/config.py init --workspace {workspace_path}"
            ],
            "error_code": "CONFIG_PARSE_ERROR"
        }

    except ConfigValidationError as e:
        _get_logger().error(f"load_config: Validation error in {config_path}: {e.message}")
        return e.to_dict()

    except Exception as e:
        _get_logger().error(f"load_config: Failed to load {config_path}: {e}")
        return {
            "success": False,
            "error": f"Failed to load configuration: {e}",
            "hint": "Check file permissions and format",
            "error_code": "CONFIG_LOAD_ERROR"
        }


def get_config(workspace_path: str) -> WorkspaceConfig:
    """
    Get the workspace configuration, loading if necessary.

    This is a convenience function that always returns a WorkspaceConfig,
    using defaults if loading fails.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        WorkspaceConfig instance (defaults if loading fails)
    """
    result = load_config(workspace_path)
    if result["success"]:
        return result["config"]
    else:
        _get_logger().warning(f"get_config: Using defaults due to error: {result.get('error')}")
        return WorkspaceConfig()


def get_config_value(workspace_path: str, key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value with fallback.

    Args:
        workspace_path: Path to the workspace directory
        key: Configuration key to retrieve
        default: Default value if key not found or config fails

    Returns:
        The configuration value or default
    """
    config = get_config(workspace_path)

    if hasattr(config, key):
        value = getattr(config, key)
        return value if value is not None else default

    return default


def create_default_config(workspace_path: str, overwrite: bool = False) -> dict:
    """
    Create a default workspace.json configuration file.

    Args:
        workspace_path: Path to the workspace directory
        overwrite: If True, overwrite existing config

    Returns:
        dict with creation result
    """
    workspace = Path(workspace_path).resolve()
    config_path = get_config_path(workspace_path)

    # Check if workspace exists
    if not workspace.exists():
        return {
            "success": False,
            "error": f"Workspace directory does not exist: {workspace}",
            "hint": "Initialize the workspace first with 'operator init'",
            "error_code": "WORKSPACE_NOT_FOUND"
        }

    # Check if config already exists
    if config_path.exists() and not overwrite:
        return {
            "success": False,
            "error": f"Configuration file already exists: {config_path}",
            "hint": "Use --overwrite to replace existing configuration",
            "recovery_options": [
                f"View current config: python tools/config.py show --workspace {workspace_path}",
                f"Overwrite: python tools/config.py init --workspace {workspace_path} --overwrite"
            ],
            "error_code": "CONFIG_EXISTS"
        }

    # Create default config
    config = WorkspaceConfig()
    config_dict = config.to_dict()

    # Add comments as a header (will be stripped by JSON, but visible in file)
    config_with_comments = {
        "_comment": "Workspace configuration for worktree operator. All fields are optional.",
        **config_dict
    }

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_with_comments, f, indent=2)
            f.write("\n")

        _get_logger().info(f"create_default_config: Created config at {config_path}")

        # Clear cache for this workspace
        cache_key = str(workspace)
        if cache_key in _config_cache:
            del _config_cache[cache_key]

        return {
            "success": True,
            "path": str(config_path),
            "config": config_dict,
            "message": f"Created workspace.json at {config_path}"
        }

    except Exception as e:
        _get_logger().error(f"create_default_config: Failed to write {config_path}: {e}")
        return {
            "success": False,
            "error": f"Failed to create configuration file: {e}",
            "hint": "Check directory permissions",
            "error_code": "CONFIG_WRITE_ERROR"
        }


def show_config(workspace_path: str) -> dict:
    """
    Show the current workspace configuration.

    Args:
        workspace_path: Path to the workspace directory

    Returns:
        dict with configuration details
    """
    result = load_config(workspace_path, force_reload=True)

    if not result["success"]:
        return result

    config = result["config"]
    config_path = get_config_path(workspace_path)

    return {
        "success": True,
        "path": str(config_path),
        "exists": result.get("exists", False),
        "config": config.to_dict(),
        "cached": False
    }


def clear_config_cache(workspace_path: Optional[str] = None):
    """
    Clear the configuration cache.

    Args:
        workspace_path: If provided, only clear cache for this workspace.
                       If None, clear all cached configurations.
    """
    global _config_cache

    if workspace_path:
        cache_key = str(Path(workspace_path).resolve())
        if cache_key in _config_cache:
            del _config_cache[cache_key]
    else:
        _config_cache = {}


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Workspace configuration management")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init command
    init_parser = subparsers.add_parser("init", help="Create default workspace.json")
    init_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    init_parser.add_argument("--overwrite", "-f", action="store_true",
                            help="Overwrite existing configuration")

    # show command
    show_parser = subparsers.add_parser("show", help="Show current configuration")
    show_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    show_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration file")
    validate_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")

    args = parser.parse_args()

    if args.command == "init":
        result = create_default_config(args.workspace, overwrite=args.overwrite)
        if result["success"]:
            print(f"✓ {result['message']}")
            print(f"\nConfiguration values:")
            for key, value in result["config"].items():
                print(f"  {key}: {value}")
        else:
            print(f"✗ Error: {result['error']}")
            if result.get("hint"):
                print(f"  Hint: {result['hint']}")
            sys.exit(1)

    elif args.command == "show":
        result = show_config(args.workspace)
        if result["success"]:
            if args.json:
                print(json.dumps(result["config"], indent=2))
            else:
                print(f"\nWorkspace Configuration")
                print(f"{'=' * 50}")
                print(f"Path: {result['path']}")
                print(f"Exists: {'Yes' if result['exists'] else 'No (using defaults)'}")
                print(f"\nValues:")
                for key, value in result["config"].items():
                    print(f"  {key}: {value}")
                print(f"{'=' * 50}")
        else:
            print(f"✗ Error: {result['error']}")
            if result.get("hint"):
                print(f"  Hint: {result['hint']}")
            sys.exit(1)

    elif args.command == "validate":
        result = load_config(args.workspace, force_reload=True)
        if result["success"]:
            if result.get("exists"):
                print(f"✓ Configuration is valid: {get_config_path(args.workspace)}")
            else:
                print(f"ℹ No configuration file found (using defaults)")
        else:
            print(f"✗ Configuration error: {result['error']}")
            if result.get("field"):
                print(f"  Field: {result['field']}")
            if result.get("hint"):
                print(f"  Hint: {result['hint']}")
            sys.exit(1)

    else:
        parser.print_help()
