#!/usr/bin/env python3
"""
Unit tests for the errors module.

Tests the OperatorError class and pre-defined error functions.
"""

import unittest
import sys
import os

# Add the tools directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from errors import (
    OperatorError,
    make_error,
    repo_exists_error,
    repo_not_found_error,
    task_exists_error,
    task_not_found_error,
    worktree_not_found_error,
    rebase_conflict_error,
    tests_failed_error,
    test_timeout_error,
    test_detection_failed_error,
    lock_held_error,
    subagent_timeout_error,
    diagnose,
    list_known_errors,
)


class TestOperatorError(unittest.TestCase):
    """Tests for the OperatorError class."""

    def test_basic_error(self):
        """Test basic error creation."""
        err = OperatorError("Test error")
        self.assertEqual(err.message, "Test error")
        self.assertIsNone(err.hint)
        self.assertEqual(err.recovery_options, [])
        self.assertIsNone(err.error_code)

    def test_error_with_hint(self):
        """Test error with hint."""
        err = OperatorError("Test error", hint="Try this")
        self.assertEqual(err.hint, "Try this")

    def test_error_with_recovery_options(self):
        """Test error with recovery options."""
        options = ["Option 1", "Option 2"]
        err = OperatorError("Test error", recovery_options=options)
        self.assertEqual(err.recovery_options, options)

    def test_error_with_code(self):
        """Test error with error code."""
        err = OperatorError("Test error", error_code="TEST_ERROR")
        self.assertEqual(err.error_code, "TEST_ERROR")

    def test_error_with_context(self):
        """Test error with context."""
        err = OperatorError("Test error", context={"path": "/test"})
        self.assertEqual(err.context, {"path": "/test"})

    def test_to_dict(self):
        """Test conversion to dictionary."""
        err = OperatorError(
            "Test error",
            hint="Try this",
            recovery_options=["Option 1"],
            error_code="TEST_ERROR",
            context={"key": "value"}
        )
        d = err.to_dict()

        self.assertFalse(d["success"])
        self.assertEqual(d["error"], "Test error")
        self.assertEqual(d["hint"], "Try this")
        self.assertEqual(d["recovery_options"], ["Option 1"])
        self.assertEqual(d["error_code"], "TEST_ERROR")
        self.assertEqual(d["context"], {"key": "value"})

    def test_str_representation(self):
        """Test string representation."""
        err = OperatorError(
            "Test error",
            hint="Try this",
            recovery_options=["Option 1", "Option 2"]
        )
        s = str(err)

        self.assertIn("Test error", s)
        self.assertIn("Try this", s)
        self.assertIn("Option 1", s)
        self.assertIn("Option 2", s)


class TestMakeError(unittest.TestCase):
    """Tests for the make_error convenience function."""

    def test_basic_make_error(self):
        """Test basic error creation."""
        result = make_error("Test error")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Test error")

    def test_make_error_with_all_fields(self):
        """Test error with all fields."""
        result = make_error(
            "Test error",
            hint="Try this",
            recovery_options=["Option 1"],
            error_code="TEST_ERROR",
            path="/test/path"
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Test error")
        self.assertEqual(result["hint"], "Try this")
        self.assertEqual(result["recovery_options"], ["Option 1"])
        self.assertEqual(result["error_code"], "TEST_ERROR")
        self.assertEqual(result["context"]["path"], "/test/path")


class TestPreDefinedErrors(unittest.TestCase):
    """Tests for pre-defined error functions."""

    def test_repo_exists_error(self):
        """Test repo_exists_error."""
        result = repo_exists_error("/test/repo")
        self.assertFalse(result["success"])
        self.assertIn("already exists", result["error"])
        self.assertIn("recovery_options", result)
        self.assertEqual(result["error_code"], "REPO_EXISTS")

    def test_repo_not_found_error(self):
        """Test repo_not_found_error."""
        result = repo_not_found_error("/test/repo")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])
        self.assertEqual(result["error_code"], "REPO_NOT_FOUND")

    def test_task_exists_error(self):
        """Test task_exists_error."""
        result = task_exists_error("fix-bug", "/workspace/task-fix-bug")
        self.assertFalse(result["success"])
        self.assertIn("already exists", result["error"])
        self.assertEqual(result["error_code"], "TASK_EXISTS")
        self.assertIn("fix-bug", result["context"]["task_name"])

    def test_task_not_found_error(self):
        """Test task_not_found_error."""
        result = task_not_found_error("fix-bug", "/workspace/task-fix-bug")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])
        self.assertEqual(result["error_code"], "TASK_NOT_FOUND")

    def test_worktree_not_found_error(self):
        """Test worktree_not_found_error."""
        result = worktree_not_found_error("fix-bug", "/workspace/task-fix-bug/worktree")
        self.assertFalse(result["success"])
        self.assertIn("Worktree", result["error"])
        self.assertEqual(result["error_code"], "WORKTREE_NOT_FOUND")

    def test_rebase_conflict_error(self):
        """Test rebase_conflict_error."""
        result = rebase_conflict_error("fix-bug", "main")
        self.assertFalse(result["success"])
        self.assertIn("conflict", result["error"].lower())
        self.assertEqual(result["error_code"], "REBASE_CONFLICT")
        self.assertIn("recovery_options", result)

    def test_tests_failed_error(self):
        """Test tests_failed_error."""
        result = tests_failed_error("npm test", 1, 5.2, "execution")
        self.assertFalse(result["success"])
        self.assertIn("failed", result["error"].lower())
        self.assertEqual(result["error_code"], "TESTS_FAILED")

    def test_test_timeout_error(self):
        """Test test_timeout_error."""
        result = test_timeout_error("npm test", 300)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"].lower())
        self.assertEqual(result["error_code"], "TEST_TIMEOUT")

    def test_test_detection_failed_error(self):
        """Test test_detection_failed_error."""
        result = test_detection_failed_error("/test/repo")
        self.assertFalse(result["success"])
        self.assertIn("detect", result["error"].lower())
        self.assertEqual(result["error_code"], "TEST_DETECTION_FAILED")

    def test_lock_held_error(self):
        """Test lock_held_error."""
        result = lock_held_error("/workspace")
        self.assertFalse(result["success"])
        self.assertIn("locked", result["error"].lower())
        self.assertEqual(result["error_code"], "LOCK_HELD")

    def test_lock_held_error_with_info(self):
        """Test lock_held_error with lock info."""
        lock_info = {"pid": 12345, "operation": "test"}
        result = lock_held_error("/workspace", lock_info)
        self.assertFalse(result["success"])
        # Should include PID in recovery options
        recovery_text = " ".join(result["recovery_options"])
        self.assertIn("12345", recovery_text)

    def test_subagent_timeout_error(self):
        """Test subagent_timeout_error."""
        result = subagent_timeout_error("fix-bug", 600)
        self.assertFalse(result["success"])
        self.assertIn("unresponsive", result["error"].lower())
        self.assertEqual(result["error_code"], "SUBAGENT_TIMEOUT")


class TestDiagnose(unittest.TestCase):
    """Tests for the diagnose function."""

    def test_diagnose_known_error(self):
        """Test diagnosing a known error code."""
        result = diagnose("REBASE_CONFLICT")
        self.assertTrue(result["success"])
        self.assertEqual(result["error_code"], "REBASE_CONFLICT")
        self.assertIn("symptom", result)
        self.assertIn("possible_causes", result)
        self.assertIn("diagnosis_steps", result)

    def test_diagnose_unknown_error(self):
        """Test diagnosing an unknown error code."""
        result = diagnose("UNKNOWN_ERROR_CODE")
        self.assertFalse(result["success"])
        self.assertIn("known_codes", result)


class TestListKnownErrors(unittest.TestCase):
    """Tests for the list_known_errors function."""

    def test_list_known_errors(self):
        """Test listing known errors."""
        result = list_known_errors()
        self.assertTrue(result["success"])
        self.assertIn("errors", result)
        self.assertIsInstance(result["errors"], list)
        self.assertGreater(len(result["errors"]), 0)

        # Check structure of each error
        for error in result["errors"]:
            self.assertIn("code", error)
            self.assertIn("symptom", error)


class TestErrorConsistency(unittest.TestCase):
    """Tests to ensure error format consistency."""

    def test_all_errors_have_success_false(self):
        """All errors should have success=False."""
        error_funcs = [
            lambda: repo_exists_error("/test"),
            lambda: repo_not_found_error("/test"),
            lambda: task_exists_error("test", "/test"),
            lambda: task_not_found_error("test", "/test"),
            lambda: worktree_not_found_error("test", "/test"),
            lambda: rebase_conflict_error("test", "main"),
            lambda: tests_failed_error("test", 1, 1.0, "test"),
            lambda: test_timeout_error("test", 300),
            lambda: test_detection_failed_error("/test"),
            lambda: lock_held_error("/test"),
            lambda: subagent_timeout_error("test", 600),
        ]

        for func in error_funcs:
            result = func()
            self.assertFalse(result["success"], f"Error {func} should have success=False")
            self.assertIn("error", result, f"Error {func} should have 'error' key")

    def test_all_errors_have_error_code(self):
        """All pre-defined errors should have an error_code."""
        error_funcs = [
            lambda: repo_exists_error("/test"),
            lambda: repo_not_found_error("/test"),
            lambda: task_exists_error("test", "/test"),
            lambda: task_not_found_error("test", "/test"),
            lambda: worktree_not_found_error("test", "/test"),
            lambda: rebase_conflict_error("test", "main"),
            lambda: tests_failed_error("test", 1, 1.0, "test"),
            lambda: test_timeout_error("test", 300),
            lambda: test_detection_failed_error("/test"),
            lambda: lock_held_error("/test"),
            lambda: subagent_timeout_error("test", 600),
        ]

        for func in error_funcs:
            result = func()
            self.assertIn("error_code", result, f"Error {func} should have 'error_code'")


if __name__ == "__main__":
    unittest.main()
