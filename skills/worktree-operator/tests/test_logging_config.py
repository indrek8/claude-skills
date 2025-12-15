#!/usr/bin/env python3
"""
Unit tests for logging_config module.
"""

import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add tools directory to path
tools_dir = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_dir))

from logging_config import (
    setup_logging,
    get_logger,
    log_operation_start,
    log_operation_success,
    log_operation_failure,
    log_exception,
    log_warning,
    log_debug,
    OperationLogger,
    get_log_file_path,
    read_recent_logs,
    clear_log_file,
    find_workspace_root,
    find_task_folder,
    detect_log_context,
    setup_subagent_logging,
    LOG_FORMAT,
    DATE_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_BYTES,
    DEFAULT_BACKUP_COUNT,
)


class TestSetupLogging(unittest.TestCase):
    """Tests for setup_logging function."""

    def setUp(self):
        """Create a temporary directory for test logs."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_setup_logging_creates_log_file(self):
        """Test that setup_logging creates the log file."""
        logger = setup_logging(log_file=str(self.log_file))
        logger.info("Test message")

        # File should exist after logging
        self.assertTrue(self.log_file.exists())

    def test_setup_logging_with_workspace_path(self):
        """Test setup_logging with workspace_path parameter."""
        logger = setup_logging(workspace_path=self.temp_dir)

        # Log file should be created in workspace
        expected_log = Path(self.temp_dir) / "workspace.log"
        logger.info("Test message")
        self.assertTrue(expected_log.exists())

    def test_setup_logging_with_custom_level(self):
        """Test setup_logging with custom log level."""
        logger = setup_logging(
            log_file=str(self.log_file),
            log_level=logging.DEBUG
        )

        self.assertEqual(logger.level, logging.DEBUG)

    def test_setup_logging_returns_operator_logger(self):
        """Test that setup_logging returns operator logger."""
        logger = setup_logging(log_file=str(self.log_file))

        self.assertEqual(logger.name, "operator")


class TestGetLogger(unittest.TestCase):
    """Tests for get_logger function."""

    def setUp(self):
        """Set up test logging."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"
        setup_logging(log_file=str(self.log_file))

    def tearDown(self):
        """Clean up."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_get_logger_returns_named_logger(self):
        """Test that get_logger returns a properly named logger."""
        logger = get_logger("test_module")

        self.assertEqual(logger.name, "operator.test_module")

    def test_get_logger_with_task_name(self):
        """Test get_logger with task_name parameter."""
        logger = get_logger("task", task_name="fix-bug")

        self.assertEqual(logger.name, "operator.task.fix-bug")

    def test_get_logger_caches_loggers(self):
        """Test that get_logger caches and returns same logger."""
        logger1 = get_logger("cached_module")
        logger2 = get_logger("cached_module")

        self.assertIs(logger1, logger2)


class TestLoggingHelpers(unittest.TestCase):
    """Tests for logging helper functions."""

    def setUp(self):
        """Set up test logging."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"
        setup_logging(log_file=str(self.log_file))
        self.logger = get_logger("test_helpers")

    def tearDown(self):
        """Clean up."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_log_operation_start(self):
        """Test log_operation_start logs correctly."""
        log_operation_start(self.logger, "test_op", param1="value1")

        content = self.log_file.read_text()
        self.assertIn("Starting test_op", content)
        self.assertIn("param1=value1", content)

    def test_log_operation_success(self):
        """Test log_operation_success logs correctly."""
        log_operation_success(self.logger, "test_op", "completed")

        content = self.log_file.read_text()
        self.assertIn("test_op succeeded", content)
        self.assertIn("completed", content)

    def test_log_operation_failure(self):
        """Test log_operation_failure logs correctly."""
        log_operation_failure(self.logger, "test_op", "error message")

        content = self.log_file.read_text()
        self.assertIn("test_op failed", content)
        self.assertIn("error message", content)

    def test_log_warning(self):
        """Test log_warning logs correctly."""
        log_warning(self.logger, "test_op", "warning message")

        content = self.log_file.read_text()
        self.assertIn("WARNING", content)
        self.assertIn("warning message", content)

    def test_log_debug(self):
        """Test log_debug logs at debug level."""
        # Re-setup with DEBUG level
        setup_logging(log_file=str(self.log_file), log_level=logging.DEBUG)
        logger = get_logger("debug_test")

        log_debug(logger, "test_op", "debug message")

        content = self.log_file.read_text()
        self.assertIn("debug message", content)


class TestOperationLogger(unittest.TestCase):
    """Tests for OperationLogger context manager."""

    def setUp(self):
        """Set up test logging."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"
        setup_logging(log_file=str(self.log_file))
        self.logger = get_logger("test_op_logger")

    def tearDown(self):
        """Clean up."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_operation_logger_logs_start_and_success(self):
        """Test OperationLogger logs start and success."""
        with OperationLogger(self.logger, "test_operation", key="value"):
            pass  # Do nothing

        content = self.log_file.read_text()
        self.assertIn("Starting test_operation", content)
        self.assertIn("test_operation succeeded", content)
        self.assertIn("key=value", content)

    def test_operation_logger_logs_exception(self):
        """Test OperationLogger logs exception on failure."""
        try:
            with OperationLogger(self.logger, "failing_operation"):
                raise ValueError("test error")
        except ValueError:
            pass

        content = self.log_file.read_text()
        self.assertIn("Starting failing_operation", content)
        self.assertIn("raised exception", content)
        self.assertIn("ValueError", content)

    def test_operation_logger_info_method(self):
        """Test OperationLogger.info method."""
        with OperationLogger(self.logger, "test_op") as op:
            op.info("progress message")

        content = self.log_file.read_text()
        self.assertIn("progress message", content)


class TestLogFileUtilities(unittest.TestCase):
    """Tests for log file utility functions."""

    def setUp(self):
        """Set up test logging."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"
        setup_logging(log_file=str(self.log_file))
        self.logger = get_logger("test_utils")

    def tearDown(self):
        """Clean up."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_get_log_file_path(self):
        """Test get_log_file_path returns correct path."""
        path = get_log_file_path()

        self.assertEqual(path, str(self.log_file))

    def test_read_recent_logs(self):
        """Test read_recent_logs returns log lines."""
        self.logger.info("Log line 1")
        self.logger.info("Log line 2")
        self.logger.info("Log line 3")

        lines = read_recent_logs(num_lines=10)

        self.assertGreater(len(lines), 0)
        # Check that our log messages are present
        content = "".join(lines)
        self.assertIn("Log line 1", content)
        self.assertIn("Log line 3", content)

    def test_clear_log_file(self):
        """Test clear_log_file clears the log."""
        self.logger.info("Old log message")
        self.assertTrue(self.log_file.exists())

        result = clear_log_file()
        self.assertTrue(result)

        # File should still exist but be nearly empty (only the "cleared" message)
        lines = read_recent_logs()
        content = "".join(lines)
        self.assertNotIn("Old log message", content)


class TestLogFormat(unittest.TestCase):
    """Tests for log format and structure."""

    def setUp(self):
        """Set up test logging."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"
        setup_logging(log_file=str(self.log_file))
        self.logger = get_logger("format_test")

    def tearDown(self):
        """Clean up."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_log_contains_timestamp(self):
        """Test that logs contain timestamps."""
        self.logger.info("Test message")

        content = self.log_file.read_text()
        # Should have ISO-like timestamp
        import re
        timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        self.assertTrue(re.search(timestamp_pattern, content))

    def test_log_contains_level(self):
        """Test that logs contain level."""
        self.logger.warning("Warning message")

        content = self.log_file.read_text()
        self.assertIn("[WARNING]", content)

    def test_log_contains_logger_name(self):
        """Test that logs contain logger name."""
        self.logger.info("Test message")

        content = self.log_file.read_text()
        self.assertIn("operator.format_test", content)


class TestWorkspaceDetection(unittest.TestCase):
    """Tests for workspace and task folder detection."""

    def setUp(self):
        """Create a temporary workspace structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir) / "myworkspace"
        self.workspace.mkdir()

        # Create plan.md to mark workspace root
        (self.workspace / "plan.md").write_text("# Workspace Plan")

        # Create a task folder structure
        self.task_folder = self.workspace / "task-fix-bug"
        self.task_folder.mkdir()
        (self.task_folder / "spec.md").write_text("# Task Spec")

        # Create worktree inside task folder
        self.worktree = self.task_folder / "worktree"
        self.worktree.mkdir()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_find_workspace_root_from_workspace(self):
        """Test finding workspace root from workspace directory."""
        result = find_workspace_root(self.workspace)
        self.assertEqual(result, self.workspace)

    def test_find_workspace_root_from_subdirectory(self):
        """Test finding workspace root from subdirectory."""
        result = find_workspace_root(self.task_folder)
        self.assertEqual(result, self.workspace)

    def test_find_workspace_root_from_worktree(self):
        """Test finding workspace root from worktree."""
        result = find_workspace_root(self.worktree)
        self.assertEqual(result, self.workspace)

    def test_find_workspace_root_not_found(self):
        """Test that None is returned when no workspace found."""
        non_workspace = Path(self.temp_dir) / "not-a-workspace"
        non_workspace.mkdir()
        result = find_workspace_root(non_workspace)
        self.assertIsNone(result)

    def test_find_task_folder_from_worktree(self):
        """Test finding task folder from worktree."""
        result = find_task_folder(self.worktree)
        self.assertEqual(result, self.task_folder)

    def test_find_task_folder_from_nested_path(self):
        """Test finding task folder from nested path in worktree."""
        nested = self.worktree / "src" / "deep"
        nested.mkdir(parents=True)
        result = find_task_folder(nested)
        self.assertEqual(result, self.task_folder)

    def test_find_task_folder_not_in_task(self):
        """Test that None is returned when not in task context."""
        result = find_task_folder(self.workspace)
        self.assertIsNone(result)

    def test_detect_log_context_subagent(self):
        """Test detecting sub-agent context from worktree."""
        context_type, log_dir = detect_log_context(self.worktree)
        self.assertEqual(context_type, "subagent")
        self.assertEqual(log_dir, self.task_folder)

    def test_detect_log_context_operator(self):
        """Test detecting operator context from workspace."""
        context_type, log_dir = detect_log_context(self.workspace)
        self.assertEqual(context_type, "operator")
        self.assertEqual(log_dir, self.workspace)

    def test_detect_log_context_fallback(self):
        """Test fallback when no workspace found."""
        non_workspace = Path(self.temp_dir) / "standalone"
        non_workspace.mkdir()
        context_type, log_dir = detect_log_context(non_workspace)
        self.assertEqual(context_type, "operator")
        self.assertEqual(log_dir, non_workspace)


class TestSubagentLogging(unittest.TestCase):
    """Tests for sub-agent logging setup."""

    def setUp(self):
        """Create a temporary workspace."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir) / "workspace"
        self.workspace.mkdir()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_setup_subagent_logging_creates_log_file(self):
        """Test that setup_subagent_logging creates log in task folder."""
        logger = setup_subagent_logging("test-task", str(self.workspace))
        logger.info("Test message")

        # Check log file is in task folder
        expected_log = self.workspace / "task-test-task" / "subagent.log"
        self.assertTrue(expected_log.exists())

    def test_setup_subagent_logging_file_path(self):
        """Test that subagent log file path is correct."""
        setup_subagent_logging("fix-bug", str(self.workspace))

        log_path = get_log_file_path()
        expected_path = str(self.workspace / "task-fix-bug" / "subagent.log")
        self.assertEqual(log_path, expected_path)


class TestLoggingContext(unittest.TestCase):
    """Tests for logging context detection in setup_logging."""

    def setUp(self):
        """Create a temporary workspace structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir) / "workspace"
        self.workspace.mkdir()
        (self.workspace / "plan.md").write_text("# Plan")

        self.task_folder = self.workspace / "task-test"
        self.task_folder.mkdir()
        (self.task_folder / "spec.md").write_text("# Spec")

        self.worktree = self.task_folder / "worktree"
        self.worktree.mkdir()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_setup_logging_operator_mode(self):
        """Test that operator logs go to workspace.log."""
        # Change to workspace directory
        original_cwd = os.getcwd()
        try:
            os.chdir(self.workspace)

            # Reset initialized flag to force re-initialization
            import logging_config
            logging_config._initialized = False

            logger = setup_logging()
            logger.info("Operator message")

            expected_log = self.workspace / "workspace.log"
            self.assertTrue(expected_log.exists())

            content = expected_log.read_text()
            self.assertIn("Operator message", content)
            self.assertIn("context: operator", content)
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_subagent_mode(self):
        """Test that sub-agent logs go to subagent.log."""
        # Change to worktree directory
        original_cwd = os.getcwd()
        try:
            os.chdir(self.worktree)

            # Reset initialized flag to force re-initialization
            import logging_config
            logging_config._initialized = False

            logger = setup_logging()
            logger.info("Subagent message")

            expected_log = self.task_folder / "subagent.log"
            self.assertTrue(expected_log.exists())

            content = expected_log.read_text()
            self.assertIn("Subagent message", content)
            self.assertIn("context: subagent", content)
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
