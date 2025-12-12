#!/usr/bin/env python3
"""
Unit tests for quality_analyzer.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from quality_analyzer import (
    parse_acceptance_criteria,
    check_test_status,
    analyze_diff_size,
    check_scope,
    calculate_quality_score,
    get_recommendation,
    analyze_task,
    format_analysis_report,
    AcceptanceCriteriaResult,
    TestResult,
    DiffSizeResult,
    ScopeResult,
    CriterionResult,
    WEIGHTS,
)


class TestParseAcceptanceCriteria(unittest.TestCase):
    """Tests for parse_acceptance_criteria function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_all_checked_criteria(self):
        """Test parsing spec with all criteria checked."""
        spec_content = """# Task: test-task

## Acceptance Criteria

- [x] First criterion
- [x] Second criterion
- [x] Third criterion

## Other Section
"""
        spec_path = Path(self.temp_dir) / "spec.md"
        spec_path.write_text(spec_content)

        result = parse_acceptance_criteria(str(spec_path))

        self.assertEqual(result.total, 3)
        self.assertEqual(result.met, 3)
        self.assertEqual(len(result.unmet), 0)
        self.assertEqual(result.score, 100.0)

    def test_parse_mixed_criteria(self):
        """Test parsing spec with some criteria unchecked."""
        spec_content = """# Task: test-task

## Acceptance Criteria

- [x] First criterion is done
- [ ] Second criterion not done
- [x] Third criterion is done
- [ ] Fourth criterion not done

## Other Section
"""
        spec_path = Path(self.temp_dir) / "spec.md"
        spec_path.write_text(spec_content)

        result = parse_acceptance_criteria(str(spec_path))

        self.assertEqual(result.total, 4)
        self.assertEqual(result.met, 2)
        self.assertEqual(len(result.unmet), 2)
        self.assertEqual(result.score, 50.0)
        self.assertIn("Second criterion not done", result.unmet)
        self.assertIn("Fourth criterion not done", result.unmet)

    def test_parse_no_criteria_section(self):
        """Test parsing spec without acceptance criteria section."""
        spec_content = """# Task: test-task

## Requirements

Some requirements here.

## Other Section
"""
        spec_path = Path(self.temp_dir) / "spec.md"
        spec_path.write_text(spec_content)

        result = parse_acceptance_criteria(str(spec_path))

        self.assertEqual(result.total, 0)
        self.assertEqual(result.met, 0)
        self.assertEqual(result.score, 100.0)  # No criteria = assume met

    def test_parse_uppercase_x(self):
        """Test parsing criteria with uppercase X."""
        spec_content = """# Task: test-task

## Acceptance Criteria

- [X] Criterion with uppercase X
- [x] Criterion with lowercase x
"""
        spec_path = Path(self.temp_dir) / "spec.md"
        spec_path.write_text(spec_content)

        result = parse_acceptance_criteria(str(spec_path))

        self.assertEqual(result.total, 2)
        self.assertEqual(result.met, 2)

    def test_parse_asterisk_bullets(self):
        """Test parsing criteria with asterisk bullets."""
        spec_content = """# Task: test-task

## Acceptance Criteria

* [x] First criterion
* [ ] Second criterion
"""
        spec_path = Path(self.temp_dir) / "spec.md"
        spec_path.write_text(spec_content)

        result = parse_acceptance_criteria(str(spec_path))

        self.assertEqual(result.total, 2)
        self.assertEqual(result.met, 1)

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file."""
        result = parse_acceptance_criteria("/nonexistent/path/spec.md")

        self.assertEqual(result.total, 0)
        self.assertEqual(result.met, 0)


class TestAnalyzeDiffSize(unittest.TestCase):
    """Tests for analyze_diff_size function."""

    @patch('quality_analyzer.run_command')
    def test_small_diff(self, mock_run_command):
        """Test small diff assessment."""
        mock_run_command.return_value = (
            0,
            " file1.py | 20 ++++\n file2.py | 30 +++--\n 2 files changed, 40 insertions(+), 10 deletions(-)",
            ""
        )

        result = analyze_diff_size("/repo", "main", "feature/test")

        self.assertEqual(result.lines_added, 40)
        self.assertEqual(result.lines_removed, 10)
        self.assertEqual(result.total_lines, 50)
        self.assertEqual(result.assessment, "small")
        self.assertEqual(result.score, 100)

    @patch('quality_analyzer.run_command')
    def test_reasonable_diff(self, mock_run_command):
        """Test reasonable diff assessment."""
        mock_run_command.return_value = (
            0,
            " file1.py | 200 ++++\n 1 files changed, 200 insertions(+), 50 deletions(-)",
            ""
        )

        result = analyze_diff_size("/repo", "main", "feature/test")

        self.assertEqual(result.total_lines, 250)
        self.assertEqual(result.assessment, "reasonable")
        self.assertEqual(result.score, 90)

    @patch('quality_analyzer.run_command')
    def test_large_diff(self, mock_run_command):
        """Test large diff assessment."""
        mock_run_command.return_value = (
            0,
            " file1.py | 600 ++++\n 1 files changed, 600 insertions(+), 100 deletions(-)",
            ""
        )

        result = analyze_diff_size("/repo", "main", "feature/test")

        self.assertEqual(result.total_lines, 700)
        self.assertEqual(result.assessment, "large")
        self.assertEqual(result.score, 70)

    @patch('quality_analyzer.run_command')
    def test_excessive_diff(self, mock_run_command):
        """Test excessive diff assessment."""
        mock_run_command.return_value = (
            0,
            " file1.py | 1500 ++++\n 1 files changed, 1500 insertions(+), 200 deletions(-)",
            ""
        )

        result = analyze_diff_size("/repo", "main", "feature/test")

        self.assertEqual(result.total_lines, 1700)
        self.assertEqual(result.assessment, "excessive")
        self.assertEqual(result.score, 50)

    @patch('quality_analyzer.run_command')
    def test_no_changes(self, mock_run_command):
        """Test no changes diff."""
        mock_run_command.return_value = (0, "", "")

        result = analyze_diff_size("/repo", "main", "feature/test")

        self.assertEqual(result.assessment, "no_changes")
        self.assertEqual(result.score, 100)


class TestCalculateQualityScore(unittest.TestCase):
    """Tests for calculate_quality_score function."""

    def test_perfect_score(self):
        """Test perfect score calculation."""
        acceptance = AcceptanceCriteriaResult(total=5, met=5, score=100)
        tests = TestResult(status="PASSING", score=100)
        diff = DiffSizeResult(assessment="small", score=100)
        scope = ScopeResult(in_scope=True, score=100)

        score = calculate_quality_score(acceptance, tests, diff, scope)

        self.assertEqual(score, 100.0)

    def test_weighted_score(self):
        """Test weighted score calculation."""
        acceptance = AcceptanceCriteriaResult(total=5, met=5, score=100)
        tests = TestResult(status="FAILING", score=0)
        diff = DiffSizeResult(assessment="small", score=100)
        scope = ScopeResult(in_scope=True, score=100)

        score = calculate_quality_score(acceptance, tests, diff, scope)

        # Expected: 100 * 0.4 + 0 * 0.3 + 100 * 0.15 + 100 * 0.15 = 70
        self.assertEqual(score, 70.0)

    def test_mixed_scores(self):
        """Test mixed score calculation."""
        acceptance = AcceptanceCriteriaResult(total=4, met=2, score=50)
        tests = TestResult(status="PASSING", score=100)
        diff = DiffSizeResult(assessment="large", score=70)
        scope = ScopeResult(in_scope=False, score=60)

        score = calculate_quality_score(acceptance, tests, diff, scope)

        # Expected: 50 * 0.4 + 100 * 0.3 + 70 * 0.15 + 60 * 0.15 = 69.5
        self.assertEqual(score, 69.5)


class TestGetRecommendation(unittest.TestCase):
    """Tests for get_recommendation function."""

    def test_recommend_accept_high_score(self):
        """Test ACCEPT recommendation for high score."""
        acceptance = AcceptanceCriteriaResult(total=5, met=5, score=100)
        tests = TestResult(status="PASSING", score=100)
        scope = ScopeResult(in_scope=True, score=100)

        recommendation, reasoning = get_recommendation(
            95, acceptance, tests, scope
        )

        self.assertEqual(recommendation, "ACCEPT")
        self.assertTrue(any("criteria met" in r.lower() for r in reasoning))

    def test_recommend_iterate_failing_tests(self):
        """Test ITERATE recommendation for failing tests."""
        acceptance = AcceptanceCriteriaResult(total=5, met=5, score=100)
        tests = TestResult(status="FAILING", score=0)
        scope = ScopeResult(in_scope=True, score=100)

        recommendation, reasoning = get_recommendation(
            70, acceptance, tests, scope
        )

        self.assertEqual(recommendation, "ITERATE")
        self.assertTrue(any("failing" in r.lower() for r in reasoning))

    def test_recommend_iterate_medium_score(self):
        """Test ITERATE recommendation for medium score."""
        acceptance = AcceptanceCriteriaResult(
            total=5, met=3, unmet=["criterion 1", "criterion 2"], score=60
        )
        tests = TestResult(status="PASSING", score=100)
        scope = ScopeResult(in_scope=True, score=100)

        recommendation, reasoning = get_recommendation(
            75, acceptance, tests, scope
        )

        self.assertEqual(recommendation, "ITERATE")

    def test_recommend_reset_low_score(self):
        """Test RESET recommendation for low score."""
        # Note: FAILING tests trigger ITERATE override, so use PASSING tests
        # to test pure score-based RESET recommendation
        acceptance = AcceptanceCriteriaResult(total=5, met=1, score=20)
        tests = TestResult(status="PASSING", score=100)
        scope = ScopeResult(in_scope=True, score=100)

        recommendation, reasoning = get_recommendation(
            30, acceptance, tests, scope
        )

        self.assertEqual(recommendation, "RESET")

    def test_recommend_reset_many_out_of_scope(self):
        """Test RESET recommendation for many out-of-scope changes."""
        acceptance = AcceptanceCriteriaResult(total=5, met=5, score=100)
        tests = TestResult(status="PASSING", score=100)
        scope = ScopeResult(
            in_scope=False,
            out_of_scope_changes=["file1", "file2", "file3", "file4", "file5", "file6"],
            score=20
        )

        recommendation, reasoning = get_recommendation(
            85, acceptance, tests, scope
        )

        self.assertEqual(recommendation, "RESET")
        self.assertTrue(any("out-of-scope" in r.lower() for r in reasoning))


class TestFormatAnalysisReport(unittest.TestCase):
    """Tests for format_analysis_report function."""

    def test_format_successful_analysis(self):
        """Test formatting successful analysis."""
        analysis = {
            "success": True,
            "task_name": "test-task",
            "score": 85.0,
            "recommendation": "ITERATE",
            "reasoning": ["Missing one criterion", "Tests passing"],
            "details": {
                "acceptance_criteria": {
                    "total": 5,
                    "met": 4,
                    "unmet": ["One criterion"],
                    "criteria": [
                        {"criterion": "Criterion 1", "met": True},
                        {"criterion": "Criterion 2", "met": True},
                        {"criterion": "One criterion", "met": False},
                    ],
                    "score": 80.0
                },
                "tests": {
                    "status": "PASSING",
                    "message": "All tests passed",
                    "duration": 5.2,
                    "score": 100.0
                },
                "diff_size": {
                    "lines_added": 100,
                    "lines_removed": 20,
                    "files_changed": 3,
                    "total_lines": 120,
                    "assessment": "reasonable",
                    "score": 90.0
                },
                "scope": {
                    "in_scope": True,
                    "out_of_scope_changes": [],
                    "warnings": [],
                    "score": 100.0
                }
            }
        }

        report = format_analysis_report(analysis)

        self.assertIn("test-task", report)
        self.assertIn("85.0/100", report)
        self.assertIn("ITERATE", report)
        self.assertIn("PASSING", report)
        self.assertIn("reasonable", report)

    def test_format_failed_analysis(self):
        """Test formatting failed analysis."""
        analysis = {
            "success": False,
            "error": "Task not found"
        }

        report = format_analysis_report(analysis)

        self.assertIn("Error", report)
        self.assertIn("Task not found", report)


class TestAnalyzeTaskIntegration(unittest.TestCase):
    """Integration tests for analyze_task function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

        # Create task directory structure
        self.task_dir = self.workspace / "task-test-task"
        self.task_dir.mkdir(parents=True)

        self.worktree_path = self.task_dir / "worktree"
        self.worktree_path.mkdir()

        self.repo_path = self.workspace / "repo"
        self.repo_path.mkdir()

        # Create spec.md
        spec_content = """# Task: test-task

## Ticket: WH-123

## Acceptance Criteria

- [x] First criterion
- [x] Second criterion
- [ ] Third criterion

## Files to Modify

- `src/file.py` - main file
"""
        (self.task_dir / "spec.md").write_text(spec_content)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('quality_analyzer.check_test_status')
    @patch('quality_analyzer.run_command')
    def test_analyze_task_basic(self, mock_run_command, mock_test_status):
        """Test basic task analysis."""
        # Mock git commands
        def run_command_side_effect(cmd, cwd=None):
            if "diff" in cmd and "--stat" in cmd:
                return (0, " file.py | 50 ++++\n 1 file changed, 50 insertions(+)", "")
            if "diff" in cmd and "--name-only" in cmd:
                return (0, "src/file.py", "")
            if "branch" in cmd:
                return (0, "main", "")
            return (0, "", "")

        mock_run_command.side_effect = run_command_side_effect
        mock_test_status.return_value = TestResult(
            status="PASSING",
            score=100,
            message="Tests passed"
        )

        result = analyze_task(
            "test-task",
            str(self.workspace),
            main_branch="main",
            ticket="WH-123",
            run_tests=False
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["task_name"], "test-task")
        self.assertIn("score", result)
        self.assertIn("recommendation", result)
        self.assertIn(result["recommendation"], ["ACCEPT", "ITERATE", "RESET"])

    def test_analyze_task_not_found(self):
        """Test analysis of nonexistent task."""
        result = analyze_task("nonexistent-task", str(self.workspace))

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])


class TestCheckScope(unittest.TestCase):
    """Tests for check_scope function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

        # Create task directory structure
        self.task_dir = self.workspace / "task-test-task"
        self.task_dir.mkdir(parents=True)

        self.repo_path = self.workspace / "repo"
        self.repo_path.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('quality_analyzer.run_command')
    def test_in_scope_changes(self, mock_run_command):
        """Test detection of in-scope changes."""
        spec_content = """# Task: test-task

## Files to Modify

- `src/main.py` - main file
- `src/utils.py` - utilities
"""
        (self.task_dir / "spec.md").write_text(spec_content)

        mock_run_command.return_value = (0, "src/main.py\nsrc/utils.py", "")

        result = check_scope("test-task", str(self.workspace), "main", "WH-123")

        self.assertTrue(result.in_scope)
        self.assertEqual(len(result.out_of_scope_changes), 0)
        self.assertEqual(result.score, 100.0)

    @patch('quality_analyzer.run_command')
    def test_out_of_scope_changes(self, mock_run_command):
        """Test detection of out-of-scope changes."""
        spec_content = """# Task: test-task

## Files to Modify

- `src/main.py` - main file
"""
        (self.task_dir / "spec.md").write_text(spec_content)

        mock_run_command.return_value = (0, "src/main.py\nsrc/unrelated.py\ntests/other.py", "")

        result = check_scope("test-task", str(self.workspace), "main", "WH-123")

        self.assertFalse(result.in_scope)
        self.assertEqual(len(result.out_of_scope_changes), 2)
        self.assertIn("src/unrelated.py", result.out_of_scope_changes)
        self.assertIn("tests/other.py", result.out_of_scope_changes)
        self.assertLess(result.score, 100.0)


if __name__ == "__main__":
    unittest.main()
