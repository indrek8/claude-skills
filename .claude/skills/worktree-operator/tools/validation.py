#!/usr/bin/env python3
"""Input validation utilities for worktree operator tools."""

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


# Validation patterns
TASK_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,49}$')
TICKET_PATTERN = re.compile(r'^[A-Z]{1,10}-[0-9]{1,10}$')
BRANCH_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9/_.-]{0,199}$')
MODEL_CHOICES = {'opus', 'sonnet', 'haiku'}

# Characters that are forbidden in git branch names
GIT_FORBIDDEN_CHARS = set('~^:?*[\\')
GIT_FORBIDDEN_SEQUENCES = ['..', '@{', '//']


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.hint = hint

    def to_dict(self) -> dict:
        """Convert to error dict format used by tools."""
        result = {
            "success": False,
            "error": self.message,
            "validation_error": True
        }
        if self.hint:
            result["hint"] = self.hint
        return result


def validate_task_name(task_name: str) -> str:
    """
    Validate task name format.

    Rules:
    - 1-50 characters
    - Must start with alphanumeric
    - Can contain: letters, numbers, hyphens, underscores
    - Cannot be empty

    Args:
        task_name: Task name to validate

    Returns:
        Validated task name (stripped of whitespace)

    Raises:
        ValidationError: If task name is invalid
    """
    if task_name is None:
        raise ValidationError(
            "Task name cannot be None",
            hint="Provide a task name like 'fix-logging' or 'add-auth'"
        )

    task_name = str(task_name).strip()

    if not task_name:
        raise ValidationError(
            "Task name cannot be empty",
            hint="Provide a task name like 'fix-logging' or 'add-auth'"
        )

    if not TASK_NAME_PATTERN.match(task_name):
        raise ValidationError(
            f"Invalid task name: '{task_name}'. "
            "Must be 1-50 characters, start with alphanumeric, "
            "and contain only letters, numbers, hyphens, and underscores.",
            hint="Examples: 'fix-logging', 'add_auth', 'refactor-api-v2'"
        )

    return task_name


def validate_ticket(ticket: str) -> str:
    """
    Validate ticket ID format.

    Rules:
    - Format: PREFIX-NUMBER
    - PREFIX: 1-10 uppercase letters
    - NUMBER: 1-10 digits

    Args:
        ticket: Ticket ID to validate (e.g., "K-123", "PROJ-456")

    Returns:
        Validated ticket ID (uppercase)

    Raises:
        ValidationError: If ticket ID is invalid
    """
    if ticket is None:
        raise ValidationError(
            "Ticket ID cannot be None",
            hint="Provide a ticket ID like 'K-123' or 'PROJ-456'"
        )

    ticket = str(ticket).strip().upper()

    if not ticket:
        raise ValidationError(
            "Ticket ID cannot be empty",
            hint="Provide a ticket ID like 'K-123' or 'PROJ-456'"
        )

    if not TICKET_PATTERN.match(ticket):
        raise ValidationError(
            f"Invalid ticket ID: '{ticket}'. "
            "Must be in format: PREFIX-NUMBER (e.g., K-123, PROJ-456)",
            hint="Use uppercase letters for prefix, numbers for ID"
        )

    return ticket


def validate_branch_name(branch: str) -> str:
    """
    Validate git branch name.

    Rules:
    - 1-200 characters
    - Must start with alphanumeric
    - Can contain: letters, numbers, forward slash, dot, hyphen, underscore
    - Cannot contain: ~, ^, :, ?, *, [, \\, .., @{

    Args:
        branch: Branch name to validate

    Returns:
        Validated branch name

    Raises:
        ValidationError: If branch name is invalid
    """
    if branch is None:
        raise ValidationError(
            "Branch name cannot be None",
            hint="Provide a branch name like 'main' or 'feature/K-123/fix-bug'"
        )

    branch = str(branch).strip()

    if not branch:
        raise ValidationError(
            "Branch name cannot be empty",
            hint="Provide a branch name like 'main' or 'feature/K-123/fix-bug'"
        )

    # Check for forbidden characters
    for char in GIT_FORBIDDEN_CHARS:
        if char in branch:
            raise ValidationError(
                f"Invalid branch name: '{branch}'. "
                f"Contains forbidden character: '{char}'",
                hint="Git branch names cannot contain: ~ ^ : ? * [ \\"
            )

    # Check for forbidden sequences
    for seq in GIT_FORBIDDEN_SEQUENCES:
        if seq in branch:
            raise ValidationError(
                f"Invalid branch name: '{branch}'. "
                f"Contains forbidden sequence: '{seq}'",
                hint="Git branch names cannot contain: .. @{ //"
            )

    # Check pattern
    if not BRANCH_NAME_PATTERN.match(branch):
        raise ValidationError(
            f"Invalid branch name: '{branch}'. "
            "Must be 1-200 characters, start with alphanumeric.",
            hint="Examples: 'main', 'feature/K-123/fix-bug', 'release-1.0'"
        )

    # Cannot end with .lock
    if branch.endswith('.lock'):
        raise ValidationError(
            f"Invalid branch name: '{branch}'. "
            "Cannot end with '.lock'",
            hint="Remove the .lock suffix"
        )

    # Cannot end with /
    if branch.endswith('/'):
        raise ValidationError(
            f"Invalid branch name: '{branch}'. "
            "Cannot end with '/'",
            hint="Remove the trailing slash"
        )

    return branch


def validate_model(model: str) -> str:
    """
    Validate model choice.

    Args:
        model: Model name to validate

    Returns:
        Validated model name (lowercase)

    Raises:
        ValidationError: If model is invalid
    """
    if model is None:
        raise ValidationError(
            "Model cannot be None",
            hint=f"Choose one of: {', '.join(MODEL_CHOICES)}"
        )

    model = str(model).strip().lower()

    if model not in MODEL_CHOICES:
        raise ValidationError(
            f"Invalid model: '{model}'. Must be one of: {', '.join(sorted(MODEL_CHOICES))}",
            hint="Use 'opus' for best quality, 'sonnet' for balanced, 'haiku' for fast"
        )

    return model


def validate_path(path: str, must_exist: bool = False, must_be_dir: bool = False) -> Path:
    """
    Validate and resolve a filesystem path.

    Rules:
    - Cannot be empty
    - Cannot contain path traversal (..)
    - Resolves to absolute path

    Args:
        path: Path to validate
        must_exist: If True, path must exist on filesystem
        must_be_dir: If True, path must be a directory

    Returns:
        Resolved Path object

    Raises:
        ValidationError: If path is invalid
    """
    if path is None:
        raise ValidationError(
            "Path cannot be None",
            hint="Provide a valid filesystem path"
        )

    path_str = str(path).strip()

    if not path_str:
        raise ValidationError(
            "Path cannot be empty",
            hint="Provide a valid filesystem path"
        )

    # Check for path traversal attempts in the input
    if '..' in path_str:
        raise ValidationError(
            f"Invalid path (contains '..'): '{path_str}'",
            hint="Use absolute paths without '..' components"
        )

    # Resolve to absolute path
    try:
        resolved = Path(path_str).resolve()
    except Exception as e:
        raise ValidationError(
            f"Invalid path: '{path_str}'. Error: {e}",
            hint="Check the path syntax and permissions"
        )

    # Verify path normalization (no remaining ..)
    resolved_str = str(resolved)
    if resolved_str != os.path.normpath(resolved_str):
        raise ValidationError(
            f"Invalid path after resolution: '{path_str}'",
            hint="Use a clean absolute path"
        )

    # Check existence if required
    if must_exist and not resolved.exists():
        raise ValidationError(
            f"Path does not exist: '{resolved}'",
            hint="Check the path or create it first"
        )

    # Check if directory if required
    if must_be_dir and resolved.exists() and not resolved.is_dir():
        raise ValidationError(
            f"Path is not a directory: '{resolved}'",
            hint="Provide a directory path, not a file"
        )

    return resolved


def validate_url(url: str, allowed_schemes: Optional[list] = None) -> str:
    """
    Validate a URL.

    Args:
        url: URL to validate
        allowed_schemes: List of allowed schemes (default: ['http', 'https', 'git', 'ssh'])

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid
    """
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https', 'git', 'ssh']

    if url is None:
        raise ValidationError(
            "URL cannot be None",
            hint="Provide a valid URL"
        )

    url = str(url).strip()

    if not url:
        raise ValidationError(
            "URL cannot be empty",
            hint="Provide a valid URL"
        )

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(
            f"Invalid URL: '{url}'. Error: {e}",
            hint="Check the URL format"
        )

    # Check scheme
    if parsed.scheme and parsed.scheme not in allowed_schemes:
        raise ValidationError(
            f"Invalid URL scheme: '{parsed.scheme}'. "
            f"Allowed: {', '.join(allowed_schemes)}",
            hint=f"Use one of: {', '.join(allowed_schemes)}"
        )

    # Must have a netloc (host) or path for git URLs
    if not parsed.netloc and not parsed.path:
        raise ValidationError(
            f"Invalid URL: '{url}'. Missing host or path.",
            hint="Provide a complete URL like 'https://github.com/user/repo.git'"
        )

    return url


def validate_positive_int(value: any, name: str = "value") -> int:
    """
    Validate a positive integer.

    Args:
        value: Value to validate
        name: Name of the parameter (for error messages)

    Returns:
        Validated integer

    Raises:
        ValidationError: If value is not a positive integer
    """
    if value is None:
        raise ValidationError(
            f"{name} cannot be None",
            hint=f"Provide a positive integer for {name}"
        )

    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Invalid {name}: '{value}'. Must be an integer.",
            hint=f"Provide a positive integer for {name}"
        )

    if int_value < 1:
        raise ValidationError(
            f"Invalid {name}: {int_value}. Must be a positive integer (>= 1).",
            hint=f"{name} must be at least 1"
        )

    return int_value


def validate_all(**kwargs) -> dict:
    """
    Validate multiple values at once.

    Usage:
        validated = validate_all(
            task_name=("fix-bug", validate_task_name),
            ticket=("K-123", validate_ticket),
            path=("/some/path", lambda p: validate_path(p, must_exist=True))
        )

    Args:
        **kwargs: Mapping of name -> (value, validator_func)

    Returns:
        Dict of validated values

    Raises:
        ValidationError: If any validation fails (with all errors combined)
    """
    results = {}
    errors = []

    for name, (value, validator) in kwargs.items():
        try:
            results[name] = validator(value)
        except ValidationError as e:
            errors.append(f"{name}: {e.message}")

    if errors:
        raise ValidationError(
            "Validation failed:\n" + "\n".join(f"  - {e}" for e in errors),
            hint="Fix the listed validation errors and try again"
        )

    return results


# Convenience function for tools to use
def safe_validate(validator_func, value, default_error: str = "Validation failed"):
    """
    Safely validate a value, returning a result dict instead of raising.

    Args:
        validator_func: Validation function to call
        value: Value to validate
        default_error: Error message if validation fails unexpectedly

    Returns:
        Tuple of (success: bool, result_or_error: any)
    """
    try:
        result = validator_func(value)
        return True, result
    except ValidationError as e:
        return False, e.to_dict()
    except Exception as e:
        return False, {
            "success": False,
            "error": f"{default_error}: {e}",
            "validation_error": True
        }
