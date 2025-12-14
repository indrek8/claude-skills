#!/usr/bin/env python3
"""
Unit tests for conflict_resolver.py

Run with: python -m pytest test_conflict_resolver.py -v
Or: python test_conflict_resolver.py
"""

import os
import subprocess
import tempfile
import shutil
import unittest
from pathlib import Path

# Import the module under test
from conflict_resolver import (
    detect_conflicts,
    get_conflicted_files,
    get_conflict_markers,
    resolve_file,
    resolve_all,
    abort_rebase,
    continue_rebase,
    is_rebase_in_progress,
    is_merge_in_progress,
    format_conflict_report,
)


class TestConflictDetection(unittest.TestCase):
    """Tests for conflict detection functions."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary git repo with conflicts for testing."""
        cls.test_dir = tempfile.mkdtemp(prefix="conflict_test_")
        cls.repo_path = os.path.join(cls.test_dir, "repo")
        cls.worktree_path = os.path.join(cls.test_dir, "worktree")

        # Initialize main repo
        os.makedirs(cls.repo_path)
        subprocess.run(["git", "init"], cwd=cls.repo_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=cls.repo_path, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=cls.repo_path, capture_output=True
        )

        # Create initial file
        test_file = os.path.join(cls.repo_path, "file.txt")
        with open(test_file, "w") as f:
            f.write("line 1\nline 2\nline 3\n")

        subprocess.run(["git", "add", "file.txt"], cwd=cls.repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=cls.repo_path, capture_output=True
        )

        # Create feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=cls.repo_path, capture_output=True
        )

        # Modify file on feature branch
        with open(test_file, "w") as f:
            f.write("line 1\nmodified by feature\nline 3\n")

        subprocess.run(["git", "add", "file.txt"], cwd=cls.repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Feature change"],
            cwd=cls.repo_path, capture_output=True
        )

        # Go back to main and make conflicting change
        subprocess.run(["git", "checkout", "master"], cwd=cls.repo_path, capture_output=True)
        # Try main if master doesn't exist
        subprocess.run(["git", "checkout", "main"], cwd=cls.repo_path, capture_output=True)

        with open(test_file, "w") as f:
            f.write("line 1\nmodified by main\nline 3\n")

        subprocess.run(["git", "add", "file.txt"], cwd=cls.repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Main change"],
            cwd=cls.repo_path, capture_output=True
        )

        # Create worktree on feature branch
        subprocess.run(
            ["git", "worktree", "add", cls.worktree_path, "feature"],
            cwd=cls.repo_path, capture_output=True
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up test directory."""
        try:
            # Remove worktree first
            subprocess.run(
                ["git", "worktree", "remove", cls.worktree_path, "--force"],
                cwd=cls.repo_path, capture_output=True
            )
        except Exception:
            pass

        try:
            shutil.rmtree(cls.test_dir)
        except Exception:
            pass

    def test_no_conflicts_initially(self):
        """Test that no conflicts are detected in clean state."""
        conflicts = detect_conflicts(self.worktree_path)
        self.assertFalse(conflicts["has_conflicts"])
        self.assertEqual(len(conflicts["files"]), 0)

    def test_is_rebase_not_in_progress(self):
        """Test that rebase detection works when no rebase is active."""
        self.assertFalse(is_rebase_in_progress(self.worktree_path))

    def test_is_merge_not_in_progress(self):
        """Test that merge detection works when no merge is active."""
        self.assertFalse(is_merge_in_progress(self.worktree_path))


class TestConflictMarkerParsing(unittest.TestCase):
    """Tests for parsing conflict markers from files."""

    def setUp(self):
        """Create a temporary file with conflict markers."""
        self.test_dir = tempfile.mkdtemp(prefix="marker_test_")
        self.conflict_file = os.path.join(self.test_dir, "conflict.txt")

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.test_dir)

    def test_parse_single_conflict(self):
        """Test parsing a file with single conflict."""
        content = """line 1
<<<<<<< HEAD
our change
=======
their change
>>>>>>> main
line 3
"""
        with open(self.conflict_file, "w") as f:
            f.write(content)

        result = get_conflict_markers(self.test_dir, "conflict.txt")

        self.assertEqual(result["conflict_count"], 1)
        self.assertIn("<<<<<<< HEAD", result["preview"])
        self.assertIn("=======", result["preview"])
        self.assertIn(">>>>>>> main", result["preview"])
        self.assertIn("our change", result["ours_preview"])
        self.assertIn("their change", result["theirs_preview"])

    def test_parse_multiple_conflicts(self):
        """Test parsing a file with multiple conflicts."""
        content = """<<<<<<< HEAD
change 1 ours
=======
change 1 theirs
>>>>>>> main
middle
<<<<<<< HEAD
change 2 ours
=======
change 2 theirs
>>>>>>> main
"""
        with open(self.conflict_file, "w") as f:
            f.write(content)

        result = get_conflict_markers(self.test_dir, "conflict.txt")

        self.assertEqual(result["conflict_count"], 2)
        # Preview should only show first conflict
        self.assertIn("change 1 ours", result["ours_preview"])

    def test_parse_no_conflict(self):
        """Test parsing a file without conflicts."""
        content = "just normal content\nno conflicts here\n"

        with open(self.conflict_file, "w") as f:
            f.write(content)

        result = get_conflict_markers(self.test_dir, "conflict.txt")

        self.assertEqual(result["conflict_count"], 0)
        self.assertEqual(result["preview"], "")

    def test_missing_file(self):
        """Test handling of missing file."""
        result = get_conflict_markers(self.test_dir, "nonexistent.txt")

        self.assertEqual(result["conflict_count"], 0)


class TestFormatConflictReport(unittest.TestCase):
    """Tests for conflict report formatting."""

    def test_format_no_conflicts(self):
        """Test report when no conflicts."""
        conflicts = {
            "has_conflicts": False,
            "operation": None,
            "files": []
        }

        report = format_conflict_report(conflicts)
        self.assertEqual(report, "No conflicts detected.")

    def test_format_with_conflicts(self):
        """Test report formatting with conflicts."""
        conflicts = {
            "has_conflicts": True,
            "operation": "rebase",
            "files": [
                {
                    "path": "src/file.py",
                    "conflict_count": 2,
                    "ours_preview": "our code",
                    "theirs_preview": "their code",
                    "conflict_preview": "<<<<<<< HEAD\nour code\n=======\ntheir code\n>>>>>>> main"
                }
            ]
        }

        report = format_conflict_report(conflicts, "test-task")

        self.assertIn("test-task", report)
        self.assertIn("rebase", report)
        self.assertIn("src/file.py", report)
        self.assertIn("Keep ours", report)
        self.assertIn("Keep theirs", report)
        self.assertIn("Manual", report)
        self.assertIn("Abort", report)

    def test_format_multiple_files(self):
        """Test report with multiple conflicted files."""
        conflicts = {
            "has_conflicts": True,
            "operation": "merge",
            "files": [
                {
                    "path": "file1.py",
                    "conflict_count": 1,
                    "conflict_preview": "conflict"
                },
                {
                    "path": "file2.py",
                    "conflict_count": 3,
                    "conflict_preview": "conflict"
                }
            ]
        }

        report = format_conflict_report(conflicts)

        self.assertIn("file1.py", report)
        self.assertIn("file2.py", report)
        self.assertIn("(3 conflicts in this file)", report)


class TestResolveStrategies(unittest.TestCase):
    """Tests for resolution strategy validation."""

    def test_invalid_strategy_for_resolve_file(self):
        """Test that invalid strategy is rejected for resolve_file."""
        # Use a dummy path since we're testing validation, not actual resolution
        result = resolve_file("/tmp", "file.txt", "invalid")
        self.assertFalse(result["success"])
        self.assertIn("Invalid strategy", result["message"])

    def test_invalid_strategy_for_resolve_all(self):
        """Test that invalid strategy is rejected for resolve_all."""
        result = resolve_all("/tmp", "manual")
        self.assertFalse(result["success"])
        self.assertIn("Invalid strategy", result["message"])

    def test_manual_strategy_returns_message(self):
        """Test that manual strategy returns helpful message."""
        result = resolve_file("/tmp", "file.txt", "manual")
        self.assertTrue(result["success"])
        self.assertIn("manual resolution", result["message"])
        self.assertIn("git add", result["message"])


class TestAbortFunctions(unittest.TestCase):
    """Tests for abort functionality."""

    def setUp(self):
        """Create a clean test directory."""
        self.test_dir = tempfile.mkdtemp(prefix="abort_test_")

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.test_dir)

    def test_abort_rebase_no_rebase(self):
        """Test abort when no rebase in progress."""
        # Initialize a simple git repo
        subprocess.run(["git", "init"], cwd=self.test_dir, capture_output=True)

        result = abort_rebase(self.test_dir)
        self.assertFalse(result["success"])
        self.assertIn("No rebase", result["message"])


class TestIntegration(unittest.TestCase):
    """Integration tests that create actual conflicts."""

    def setUp(self):
        """Create repos with actual conflicts."""
        self.test_dir = tempfile.mkdtemp(prefix="integration_test_")
        self.repo_path = os.path.join(self.test_dir, "repo")

        # Initialize repo
        os.makedirs(self.repo_path)
        subprocess.run(["git", "init"], cwd=self.repo_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=self.repo_path, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.repo_path, capture_output=True
        )

    def tearDown(self):
        """Clean up."""
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_detect_conflicts_full_workflow(self):
        """Test full workflow of creating and detecting conflicts."""
        # Create initial commit
        test_file = os.path.join(self.repo_path, "test.txt")
        with open(test_file, "w") as f:
            f.write("original\n")

        subprocess.run(["git", "add", "."], cwd=self.repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=self.repo_path, capture_output=True
        )

        # Create branch with change
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=self.repo_path, capture_output=True
        )
        with open(test_file, "w") as f:
            f.write("feature change\n")
        subprocess.run(["git", "add", "."], cwd=self.repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Feature"],
            cwd=self.repo_path, capture_output=True
        )

        # Make conflicting change on main
        subprocess.run(["git", "checkout", "master"], cwd=self.repo_path, capture_output=True)
        # Try main if master doesn't exist
        subprocess.run(["git", "checkout", "main"], cwd=self.repo_path, capture_output=True)

        with open(test_file, "w") as f:
            f.write("main change\n")
        subprocess.run(["git", "add", "."], cwd=self.repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Main change"],
            cwd=self.repo_path, capture_output=True
        )

        # Try to merge feature - should conflict
        result = subprocess.run(
            ["git", "merge", "feature"],
            cwd=self.repo_path, capture_output=True, text=True
        )

        if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
            # Conflicts detected - test our detection
            conflicts = detect_conflicts(self.repo_path)
            self.assertTrue(conflicts["has_conflicts"])
            self.assertEqual(len(conflicts["files"]), 1)
            self.assertEqual(conflicts["files"][0]["path"], "test.txt")
            self.assertTrue(is_merge_in_progress(self.repo_path))


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConflictDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestConflictMarkerParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatConflictReport))
    suite.addTests(loader.loadTestsFromTestCase(TestResolveStrategies))
    suite.addTests(loader.loadTestsFromTestCase(TestAbortFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_tests())
