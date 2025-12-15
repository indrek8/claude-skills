#!/usr/bin/env python3
"""Unit tests for plan_parser.py."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from plan_parser import (
    parse_plan,
    get_unblocked_tasks,
    check_dependencies,
    COMPLETED_STATUSES,
    VALID_STATUSES,
)


class TestParsePlan(unittest.TestCase):
    """Tests for parse_plan function."""

    def setUp(self):
        """Create a temporary workspace for testing."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary workspace."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_parse_plan_no_file(self):
        """Test parsing when plan.md doesn't exist."""
        result = parse_plan(self.temp_dir)

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])
        self.assertEqual(result["tasks"], {})

    def test_parse_plan_simple_task(self):
        """Test parsing a simple task with status and dependencies."""
        plan_content = """# Plan: K-123 Feature

## Tasks

### 1. setup-database
- Status: COMPLETED
- Dependencies: None
- Branch: feature/K-123/setup-database
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = parse_plan(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertEqual(result["task_count"], 1)
        self.assertIn("setup-database", result["tasks"])

        task = result["tasks"]["setup-database"]
        self.assertEqual(task["status"], "COMPLETED")
        self.assertEqual(task["dependencies"], [])
        self.assertEqual(task["branch"], "feature/K-123/setup-database")

    def test_parse_plan_with_dependencies(self):
        """Test parsing task with multiple dependencies."""
        plan_content = """# Plan

## Tasks

### 1. setup-database
- Status: COMPLETED
- Dependencies: None

### 2. create-user-model
- Status: COMPLETED
- Dependencies: setup-database

### 3. implement-auth
- Status: PENDING
- Dependencies: setup-database, create-user-model
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = parse_plan(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertEqual(result["task_count"], 3)

        # Check dependencies are parsed correctly
        auth_task = result["tasks"]["implement-auth"]
        self.assertEqual(auth_task["status"], "PENDING")
        self.assertEqual(
            sorted(auth_task["dependencies"]),
            ["create-user-model", "setup-database"]
        )

    def test_parse_plan_case_insensitive_status(self):
        """Test that status is case-insensitive."""
        plan_content = """# Plan

### 1. task-lower
- Status: completed

### 2. task-upper
- Status: COMPLETED

### 3. task-mixed
- Status: Completed
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = parse_plan(self.temp_dir)

        self.assertTrue(result["success"])
        # All should be normalized to COMPLETED
        self.assertEqual(result["tasks"]["task-lower"]["status"], "COMPLETED")
        self.assertEqual(result["tasks"]["task-upper"]["status"], "COMPLETED")
        self.assertEqual(result["tasks"]["task-mixed"]["status"], "COMPLETED")

    def test_parse_plan_with_priority_and_description(self):
        """Test parsing optional fields like priority and description."""
        plan_content = """# Plan

### 1. critical-task
- Status: PENDING
- Dependencies: None
- Priority: HIGH
- Description: This is a critical task
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = parse_plan(self.temp_dir)

        self.assertTrue(result["success"])
        task = result["tasks"]["critical-task"]
        self.assertEqual(task["priority"], "HIGH")
        self.assertEqual(task["description"], "This is a critical task")

    def test_parse_plan_no_number_prefix(self):
        """Test parsing task without number prefix."""
        plan_content = """# Plan

### task-without-number
- Status: PENDING
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = parse_plan(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertIn("task-without-number", result["tasks"])

    def test_parse_plan_backtick_task_name(self):
        """Test parsing task name with backticks."""
        plan_content = """# Plan

### 1. `task-with-backticks`
- Status: PENDING
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = parse_plan(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertIn("task-with-backticks", result["tasks"])

    def test_parse_plan_none_dependencies(self):
        """Test various formats for no dependencies."""
        plan_content = """# Plan

### 1. task-none
- Status: PENDING
- Dependencies: None

### 2. task-na
- Status: PENDING
- Dependencies: n/a

### 3. task-dash
- Status: PENDING
- Dependencies: -
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = parse_plan(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertEqual(result["tasks"]["task-none"]["dependencies"], [])
        self.assertEqual(result["tasks"]["task-na"]["dependencies"], [])
        self.assertEqual(result["tasks"]["task-dash"]["dependencies"], [])


class TestGetUnblockedTasks(unittest.TestCase):
    """Tests for get_unblocked_tasks function."""

    def setUp(self):
        """Create a temporary workspace for testing."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary workspace."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_unblocked_no_dependencies(self):
        """Test that tasks with no dependencies are unblocked."""
        plan_content = """# Plan

### 1. task1
- Status: PENDING
- Dependencies: None

### 2. task2
- Status: PENDING
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = get_unblocked_tasks(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertIn("task1", result["unblocked"])
        self.assertIn("task2", result["unblocked"])
        self.assertEqual(result["blocked"], {})

    def test_blocked_dependencies_not_met(self):
        """Test that tasks with unmet dependencies are blocked."""
        plan_content = """# Plan

### 1. task1
- Status: PENDING
- Dependencies: None

### 2. task2
- Status: PENDING
- Dependencies: task1
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = get_unblocked_tasks(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertIn("task1", result["unblocked"])
        self.assertIn("task2", result["blocked"])
        self.assertEqual(result["blocked"]["task2"]["missing"], ["task1"])

    def test_unblocked_after_dependency_completed(self):
        """Test that tasks become unblocked when dependencies complete."""
        plan_content = """# Plan

### 1. task1
- Status: COMPLETED
- Dependencies: None

### 2. task2
- Status: PENDING
- Dependencies: task1
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = get_unblocked_tasks(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertIn("task2", result["unblocked"])
        self.assertIn("task1", result["completed"])
        self.assertEqual(result["blocked"], {})

    def test_in_progress_categorization(self):
        """Test that in-progress tasks are categorized correctly."""
        plan_content = """# Plan

### 1. task1
- Status: IN_PROGRESS
- Dependencies: None

### 2. task2
- Status: IN_REVIEW
- Dependencies: None

### 3. task3
- Status: ITERATING
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = get_unblocked_tasks(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertIn("task1", result["in_progress"])
        self.assertIn("task2", result["in_progress"])
        self.assertIn("task3", result["in_progress"])
        self.assertEqual(result["unblocked"], [])

    def test_multiple_dependencies_partial_met(self):
        """Test task with some dependencies met."""
        plan_content = """# Plan

### 1. dep1
- Status: COMPLETED
- Dependencies: None

### 2. dep2
- Status: PENDING
- Dependencies: None

### 3. task1
- Status: PENDING
- Dependencies: dep1, dep2
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = get_unblocked_tasks(self.temp_dir)

        self.assertTrue(result["success"])
        self.assertIn("task1", result["blocked"])
        self.assertEqual(result["blocked"]["task1"]["missing"], ["dep2"])


class TestCheckDependencies(unittest.TestCase):
    """Tests for check_dependencies function."""

    def setUp(self):
        """Create a temporary workspace for testing."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary workspace."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_check_task_not_in_plan(self):
        """Test checking a task that doesn't exist in plan."""
        plan_content = """# Plan

### 1. existing-task
- Status: PENDING
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = check_dependencies("nonexistent-task", self.temp_dir)

        self.assertTrue(result["success"])
        self.assertTrue(result["can_spawn"])  # Allow ad-hoc tasks
        self.assertFalse(result["task_exists"])
        self.assertIn("warning", result)

    def test_check_task_no_dependencies(self):
        """Test checking a task with no dependencies."""
        plan_content = """# Plan

### 1. simple-task
- Status: PENDING
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = check_dependencies("simple-task", self.temp_dir)

        self.assertTrue(result["success"])
        self.assertTrue(result["can_spawn"])
        self.assertTrue(result["task_exists"])
        self.assertEqual(result["missing"], [])

    def test_check_task_dependencies_not_met(self):
        """Test checking a task with unmet dependencies."""
        plan_content = """# Plan

### 1. dep-task
- Status: PENDING
- Dependencies: None

### 2. main-task
- Status: PENDING
- Dependencies: dep-task
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = check_dependencies("main-task", self.temp_dir)

        self.assertTrue(result["success"])
        self.assertFalse(result["can_spawn"])
        self.assertEqual(result["missing"], ["dep-task"])
        self.assertIn("error", result)
        self.assertIn("hint", result)

    def test_check_task_dependencies_met(self):
        """Test checking a task with all dependencies met."""
        plan_content = """# Plan

### 1. dep-task
- Status: COMPLETED
- Dependencies: None

### 2. main-task
- Status: PENDING
- Dependencies: dep-task
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = check_dependencies("main-task", self.temp_dir)

        self.assertTrue(result["success"])
        self.assertTrue(result["can_spawn"])
        self.assertEqual(result["completed"], ["dep-task"])
        self.assertEqual(result["missing"], [])

    def test_check_completed_task(self):
        """Test checking a task that is already completed."""
        plan_content = """# Plan

### 1. done-task
- Status: COMPLETED
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = check_dependencies("done-task", self.temp_dir)

        self.assertTrue(result["success"])
        self.assertFalse(result["can_spawn"])  # Can't spawn completed task
        self.assertIn("warning", result)

    def test_check_in_progress_task(self):
        """Test checking a task that is in progress."""
        plan_content = """# Plan

### 1. active-task
- Status: IN_PROGRESS
- Dependencies: None
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = check_dependencies("active-task", self.temp_dir)

        self.assertTrue(result["success"])
        self.assertTrue(result["can_spawn"])  # Allow re-spawning
        self.assertIn("info", result)

    def test_check_missing_dependency_not_in_plan(self):
        """Test when a dependency doesn't exist in the plan."""
        plan_content = """# Plan

### 1. task1
- Status: PENDING
- Dependencies: nonexistent-dep
"""
        plan_path = Path(self.temp_dir) / "plan.md"
        plan_path.write_text(plan_content)

        result = check_dependencies("task1", self.temp_dir)

        self.assertTrue(result["success"])
        self.assertFalse(result["can_spawn"])
        self.assertEqual(result["missing"], ["nonexistent-dep"])


class TestCompletedStatuses(unittest.TestCase):
    """Tests for status constants."""

    def test_completed_statuses(self):
        """Test that expected statuses are considered complete."""
        self.assertIn("COMPLETED", COMPLETED_STATUSES)
        self.assertIn("DONE", COMPLETED_STATUSES)
        self.assertIn("MERGED", COMPLETED_STATUSES)

    def test_valid_statuses(self):
        """Test that all expected statuses are valid."""
        expected = {
            'PENDING', 'IN_PROGRESS', 'IN_REVIEW', 'ITERATING',
            'COMPLETED', 'DONE', 'MERGED', 'BLOCKED', 'ABANDONED'
        }
        self.assertEqual(VALID_STATUSES, expected)


if __name__ == "__main__":
    unittest.main()
