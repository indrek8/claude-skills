#!/usr/bin/env python3
"""
Quality analyzer for task reviews.

Provides automated quality assessment to help operators decide
between accept, iterate, or reset for sub-agent work.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, List

from validation import ValidationError, validate_task_name, validate_path


# Scoring weights
WEIGHTS = {
    "acceptance_criteria": 0.40,
    "tests": 0.30,
    "diff_size": 0.15,
    "scope": 0.15,
}

# Diff size thresholds (lines changed = added + removed)
DIFF_SIZE_THRESHOLDS = {
    "small": 100,      # < 100 lines is small
    "reasonable": 500, # 100-500 is reasonable
    "large": 1000,     # 500-1000 is large
    # > 1000 is excessive
}

# Recommendation thresholds
ACCEPT_THRESHOLD = 90
ITERATE_THRESHOLD = 50


@dataclass
class CriterionResult:
    """Result of checking a single acceptance criterion."""
    criterion: str
    met: bool
    checked: bool = True  # False if we couldn't determine status


@dataclass
class AcceptanceCriteriaResult:
    """Result of parsing and checking acceptance criteria."""
    total: int = 0
    met: int = 0
    unmet: List[str] = field(default_factory=list)
    criteria: List[CriterionResult] = field(default_factory=list)
    score: float = 0.0


@dataclass
class TestResult:
    """Result of test status check."""
    status: str = "UNKNOWN"  # PASSING, FAILING, NOT_RUN, ERROR
    score: float = 0.0
    message: str = ""
    duration: Optional[float] = None


@dataclass
class DiffSizeResult:
    """Result of diff size analysis."""
    lines_added: int = 0
    lines_removed: int = 0
    files_changed: int = 0
    total_lines: int = 0
    assessment: str = "unknown"  # small, reasonable, large, excessive
    score: float = 0.0


@dataclass
class ScopeResult:
    """Result of scope analysis."""
    in_scope: bool = True
    out_of_scope_changes: List[str] = field(default_factory=list)
    score: float = 100.0
    warnings: List[str] = field(default_factory=list)


def run_command(cmd: list[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def parse_acceptance_criteria(spec_path: str) -> AcceptanceCriteriaResult:
    """
    Extract acceptance criteria from spec.md.

    Looks for a section titled "Acceptance Criteria" and extracts
    all checkbox items (- [ ] or - [x]).

    Args:
        spec_path: Path to spec.md file

    Returns:
        AcceptanceCriteriaResult with parsed criteria
    """
    result = AcceptanceCriteriaResult()
    spec_file = Path(spec_path)

    if not spec_file.exists():
        return result

    content = spec_file.read_text()
    lines = content.split("\n")

    # Find the Acceptance Criteria section
    in_criteria_section = False

    for line in lines:
        # Check for Acceptance Criteria header
        if re.match(r'^##\s*Acceptance\s+Criteria', line, re.IGNORECASE):
            in_criteria_section = True
            continue

        # Exit section on next header
        if in_criteria_section and line.startswith("##"):
            break

        if not in_criteria_section:
            continue

        # Parse checkbox items
        # Matches: - [ ] text, - [x] text, - [X] text, * [ ] text
        checkbox_match = re.match(r'^[-*]\s*\[([xX ])\]\s*(.+)$', line.strip())
        if checkbox_match:
            is_checked = checkbox_match.group(1).lower() == 'x'
            criterion_text = checkbox_match.group(2).strip()

            criterion = CriterionResult(
                criterion=criterion_text,
                met=is_checked
            )
            result.criteria.append(criterion)
            result.total += 1

            if is_checked:
                result.met += 1
            else:
                result.unmet.append(criterion_text)

    # Calculate score
    if result.total > 0:
        result.score = (result.met / result.total) * 100
    else:
        result.score = 100  # No criteria = assume met

    return result


def check_test_status(
    worktree_path: str,
    workspace_path: Optional[str] = None
) -> TestResult:
    """
    Check the test status of the task's worktree.

    Uses the test_runner module to run tests.

    Args:
        worktree_path: Path to the task's worktree
        workspace_path: Optional workspace path for config

    Returns:
        TestResult with test status
    """
    result = TestResult()

    # Import here to avoid circular import
    try:
        from test_runner import verify_tests_pass
    except ImportError:
        result.status = "ERROR"
        result.message = "Could not import test_runner"
        result.score = 0
        return result

    test_result = verify_tests_pass(
        worktree_path,
        workspace_path=workspace_path
    )

    if test_result.get("passed"):
        result.status = "PASSING"
        result.score = 100
        result.message = test_result.get("message", "Tests passed")
        result.duration = test_result.get("duration")
    elif test_result.get("error") and "Could not auto-detect" in test_result.get("error", ""):
        result.status = "NOT_RUN"
        result.score = 50  # Partial credit if no test framework found
        result.message = "No test framework detected"
    else:
        result.status = "FAILING"
        result.score = 0
        result.message = test_result.get("error", "Tests failed")
        result.duration = test_result.get("duration")

    return result


def analyze_diff_size(
    repo_path: str,
    main_branch: str,
    sub_branch: str
) -> DiffSizeResult:
    """
    Analyze the diff size between main and sub-branch.

    Args:
        repo_path: Path to the repository
        main_branch: Main branch name
        sub_branch: Sub-branch name

    Returns:
        DiffSizeResult with diff analysis
    """
    result = DiffSizeResult()

    # Get diff stats
    returncode, stdout, stderr = run_command(
        ["git", "diff", "--stat", f"{main_branch}..{sub_branch}"],
        cwd=repo_path
    )

    if returncode != 0:
        result.assessment = "error"
        result.score = 50  # Neutral score on error
        return result

    if not stdout.strip():
        result.assessment = "no_changes"
        result.score = 100
        return result

    # Parse the stats
    lines = stdout.strip().split("\n")

    # Count file changes from individual lines
    for line in lines[:-1]:  # Skip last summary line
        if "|" in line:
            result.files_changed += 1

    # Parse the summary line
    if lines:
        summary = lines[-1]
        import re
        ins_match = re.search(r"(\d+) insertions?", summary)
        del_match = re.search(r"(\d+) deletions?", summary)

        if ins_match:
            result.lines_added = int(ins_match.group(1))
        if del_match:
            result.lines_removed = int(del_match.group(1))

    result.total_lines = result.lines_added + result.lines_removed

    # Assess size
    if result.total_lines < DIFF_SIZE_THRESHOLDS["small"]:
        result.assessment = "small"
        result.score = 100
    elif result.total_lines < DIFF_SIZE_THRESHOLDS["reasonable"]:
        result.assessment = "reasonable"
        result.score = 90
    elif result.total_lines < DIFF_SIZE_THRESHOLDS["large"]:
        result.assessment = "large"
        result.score = 70
    else:
        result.assessment = "excessive"
        result.score = 50

    return result


def check_scope(
    task_name: str,
    workspace_path: str,
    main_branch: str,
    ticket: str
) -> ScopeResult:
    """
    Check if changes are within scope defined in spec.md.

    Analyzes which files were modified and compares against
    the "Files to Modify" section in spec.md.

    Args:
        task_name: Task name
        workspace_path: Path to workspace
        main_branch: Main branch name
        ticket: Ticket ID (for branch construction)

    Returns:
        ScopeResult with scope analysis
    """
    result = ScopeResult()
    workspace = Path(workspace_path)
    task_dir = workspace / f"task-{task_name}"
    worktree_path = task_dir / "worktree"
    repo_path = workspace / "repo"
    sub_branch = f"feature/{ticket}/{task_name}"

    # Get the spec.md content
    spec_path = task_dir / "spec.md"
    if not spec_path.exists():
        result.warnings.append("No spec.md found - cannot verify scope")
        return result

    spec_content = spec_path.read_text()

    # Extract "Files to Modify" section
    expected_files = set()
    in_files_section = False

    for line in spec_content.split("\n"):
        if re.match(r'^##\s*Files\s+to\s+(Modify|Create)', line, re.IGNORECASE):
            in_files_section = True
            continue
        if in_files_section and line.startswith("##"):
            break
        if in_files_section:
            # Extract file paths from lines like "- `path/to/file` - description"
            file_match = re.search(r'`([^`]+)`', line)
            if file_match:
                expected_files.add(file_match.group(1))

    # Get actual changed files
    returncode, stdout, stderr = run_command(
        ["git", "diff", "--name-only", f"{main_branch}..{sub_branch}"],
        cwd=str(repo_path)
    )

    if returncode != 0:
        result.warnings.append(f"Could not get changed files: {stderr}")
        return result

    actual_files = set(stdout.strip().split("\n")) if stdout.strip() else set()

    # If no expected files specified, assume in scope
    if not expected_files:
        result.warnings.append("No 'Files to Modify' section found in spec.md")
        return result

    # Check for out-of-scope changes
    for actual in actual_files:
        is_in_scope = False

        for expected in expected_files:
            # Check if actual file matches expected (with wildcards support)
            if expected.endswith("*"):
                if actual.startswith(expected[:-1]):
                    is_in_scope = True
                    break
            elif actual == expected or actual.startswith(expected + "/"):
                is_in_scope = True
                break

        if not is_in_scope:
            result.out_of_scope_changes.append(actual)

    # Calculate score based on out-of-scope changes
    if result.out_of_scope_changes:
        result.in_scope = False
        # Penalize based on number of out-of-scope files
        penalty = min(len(result.out_of_scope_changes) * 20, 80)
        result.score = 100 - penalty

    return result


def calculate_quality_score(
    acceptance_result: AcceptanceCriteriaResult,
    test_result: TestResult,
    diff_result: DiffSizeResult,
    scope_result: ScopeResult
) -> float:
    """
    Calculate weighted quality score.

    Args:
        acceptance_result: Result from acceptance criteria check
        test_result: Result from test check
        diff_result: Result from diff size analysis
        scope_result: Result from scope check

    Returns:
        Quality score (0-100)
    """
    weighted_score = (
        acceptance_result.score * WEIGHTS["acceptance_criteria"] +
        test_result.score * WEIGHTS["tests"] +
        diff_result.score * WEIGHTS["diff_size"] +
        scope_result.score * WEIGHTS["scope"]
    )

    return round(weighted_score, 1)


def get_recommendation(
    score: float,
    acceptance_result: AcceptanceCriteriaResult,
    test_result: TestResult,
    scope_result: ScopeResult
) -> Tuple[str, List[str]]:
    """
    Determine recommendation based on analysis results.

    Args:
        score: Overall quality score
        acceptance_result: Result from acceptance criteria check
        test_result: Result from test check
        scope_result: Result from scope check

    Returns:
        Tuple of (recommendation, list of reasoning points)
    """
    reasoning = []

    # Critical failures that override score
    if test_result.status == "FAILING":
        reasoning.append("Tests are failing - must fix before accepting")
        return "ITERATE", reasoning

    # Check for major scope issues
    if len(scope_result.out_of_scope_changes) > 5:
        reasoning.append(f"Too many out-of-scope changes ({len(scope_result.out_of_scope_changes)} files)")
        reasoning.append("Consider resetting and clarifying task scope")
        return "RESET", reasoning

    # Score-based recommendation
    if score >= ACCEPT_THRESHOLD:
        if acceptance_result.score == 100:
            reasoning.append("All acceptance criteria met")
        else:
            reasoning.append(f"{acceptance_result.met}/{acceptance_result.total} acceptance criteria met")

        if test_result.status == "PASSING":
            reasoning.append("Tests passing")
        elif test_result.status == "NOT_RUN":
            reasoning.append("No test framework detected (verify manually)")

        if scope_result.in_scope:
            reasoning.append("Changes are in scope")

        return "ACCEPT", reasoning

    elif score >= ITERATE_THRESHOLD:
        # Identify what needs improvement
        if acceptance_result.unmet:
            reasoning.append(f"Missing criteria: {len(acceptance_result.unmet)} items")
            for item in acceptance_result.unmet[:3]:
                reasoning.append(f"  - {item[:60]}...")

        if scope_result.out_of_scope_changes:
            reasoning.append(f"Out-of-scope changes: {len(scope_result.out_of_scope_changes)} files")

        reasoning.append("Issues are fixable - recommend iterating")
        return "ITERATE", reasoning

    else:
        reasoning.append(f"Quality score too low ({score})")

        if acceptance_result.score < 50:
            reasoning.append("Most acceptance criteria not met")

        if scope_result.out_of_scope_changes:
            reasoning.append(f"Significant out-of-scope changes")

        reasoning.append("Consider resetting and clarifying requirements")
        return "RESET", reasoning


def analyze_task(
    task_name: str,
    workspace_path: str,
    main_branch: Optional[str] = None,
    ticket: Optional[str] = None,
    run_tests: bool = True
) -> dict:
    """
    Analyze task quality and provide recommendation.

    Args:
        task_name: Name of the task to analyze
        workspace_path: Path to the workspace
        main_branch: Main branch name (auto-detected if not provided)
        ticket: Ticket ID (auto-detected from spec.md if not provided)
        run_tests: Whether to run tests (True by default)

    Returns:
        dict with complete analysis results
    """
    # Validate inputs
    try:
        task_name = validate_task_name(task_name)
        workspace = validate_path(workspace_path)
    except ValidationError as e:
        return e.to_dict() if hasattr(e, 'to_dict') else {
            "success": False,
            "error": str(e),
            "validation_error": True
        }

    task_dir = workspace / f"task-{task_name}"
    worktree_path = task_dir / "worktree"
    repo_path = workspace / "repo"
    spec_path = task_dir / "spec.md"

    # Verify task exists
    if not task_dir.exists():
        return {
            "success": False,
            "error": f"Task folder not found: {task_dir}",
            "hint": "Create the task first with 'operator create task'"
        }

    if not worktree_path.exists():
        return {
            "success": False,
            "error": f"Worktree not found: {worktree_path}",
            "hint": "Task may have been reset or not properly created"
        }

    # Auto-detect ticket and branch from spec.md if not provided
    if spec_path.exists():
        spec_content = spec_path.read_text()

        if not ticket:
            ticket_match = re.search(r'^##\s*Ticket:\s*(.+)$', spec_content, re.MULTILINE)
            if ticket_match:
                ticket = ticket_match.group(1).strip()

        if not main_branch:
            # Try to detect from worktree
            returncode, stdout, stderr = run_command(
                ["git", "log", "--oneline", "-1", "--format=%D"],
                cwd=str(worktree_path)
            )
            # Fall back to looking in repo
            if not main_branch:
                returncode, stdout, stderr = run_command(
                    ["git", "branch", "--show-current"],
                    cwd=str(repo_path)
                )
                if returncode == 0:
                    main_branch = stdout.strip()

    if not ticket:
        ticket = "WH-0"  # Default ticket

    if not main_branch:
        main_branch = "main"  # Default branch

    sub_branch = f"feature/{ticket}/{task_name}"

    # Run all analyses
    acceptance_result = parse_acceptance_criteria(str(spec_path))

    if run_tests:
        test_result = check_test_status(str(worktree_path), str(workspace))
    else:
        test_result = TestResult(
            status="NOT_RUN",
            score=50,
            message="Tests skipped by request"
        )

    diff_result = analyze_diff_size(str(repo_path), main_branch, sub_branch)

    scope_result = check_scope(task_name, str(workspace), main_branch, ticket)

    # Calculate overall score
    score = calculate_quality_score(
        acceptance_result, test_result, diff_result, scope_result
    )

    # Get recommendation
    recommendation, reasoning = get_recommendation(
        score, acceptance_result, test_result, scope_result
    )

    return {
        "success": True,
        "task_name": task_name,
        "score": score,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "details": {
            "acceptance_criteria": {
                "total": acceptance_result.total,
                "met": acceptance_result.met,
                "unmet": acceptance_result.unmet,
                "criteria": [
                    {"criterion": c.criterion, "met": c.met}
                    for c in acceptance_result.criteria
                ],
                "score": acceptance_result.score
            },
            "tests": {
                "status": test_result.status,
                "message": test_result.message,
                "duration": test_result.duration,
                "score": test_result.score
            },
            "diff_size": {
                "lines_added": diff_result.lines_added,
                "lines_removed": diff_result.lines_removed,
                "files_changed": diff_result.files_changed,
                "total_lines": diff_result.total_lines,
                "assessment": diff_result.assessment,
                "score": diff_result.score
            },
            "scope": {
                "in_scope": scope_result.in_scope,
                "out_of_scope_changes": scope_result.out_of_scope_changes,
                "warnings": scope_result.warnings,
                "score": scope_result.score
            }
        }
    }


def format_analysis_report(analysis: dict, width: int = 64) -> str:
    """
    Format analysis results as a readable report.

    Args:
        analysis: Result from analyze_task()
        width: Width of the report box

    Returns:
        Formatted string report
    """
    if not analysis.get("success"):
        return f"Error: {analysis.get('error', 'Unknown error')}"

    task_name = analysis["task_name"]
    score = analysis["score"]
    recommendation = analysis["recommendation"]
    reasoning = analysis["reasoning"]
    details = analysis["details"]

    lines = []

    # Header
    lines.append("╔" + "═" * (width - 2) + "╗")
    header = f"Quality Assessment: {task_name}"
    lines.append("║" + header.center(width - 2) + "║")
    lines.append("╠" + "═" * (width - 2) + "╣")

    # Overall Score
    lines.append("║" + " " * (width - 2) + "║")
    score_line = f"Overall Score: {score}/100"
    lines.append("║  " + score_line.ljust(width - 4) + "║")
    lines.append("║" + " " * (width - 2) + "║")

    # Acceptance Criteria
    ac = details["acceptance_criteria"]
    ac_line = f"Acceptance Criteria: {ac['met']}/{ac['total']} met ({ac['score']:.0f}%)"
    lines.append("║  " + ac_line.ljust(width - 4) + "║")

    for criterion in ac.get("criteria", [])[:8]:  # Show first 8
        mark = "✓" if criterion["met"] else "✗"
        text = criterion["criterion"][:width - 10]
        lines.append("║    " + f"{mark} {text}".ljust(width - 6) + "║")

    if len(ac.get("criteria", [])) > 8:
        more = len(ac["criteria"]) - 8
        lines.append("║    " + f"... and {more} more".ljust(width - 6) + "║")

    lines.append("║" + " " * (width - 2) + "║")

    # Tests
    tests = details["tests"]
    test_line = f"Tests: {tests['status']}"
    if tests.get("duration"):
        test_line += f" ({tests['duration']:.1f}s)"
    lines.append("║  " + test_line.ljust(width - 4) + "║")

    # Diff Size
    diff = details["diff_size"]
    diff_line = f"Diff Size: {diff['total_lines']} lines ({diff['assessment']})"
    lines.append("║  " + diff_line.ljust(width - 4) + "║")

    # Scope
    scope = details["scope"]
    scope_status = "IN_SCOPE" if scope["in_scope"] else "OUT_OF_SCOPE"
    scope_line = f"Scope: {scope_status}"
    lines.append("║  " + scope_line.ljust(width - 4) + "║")

    if scope["out_of_scope_changes"]:
        for oos_file in scope["out_of_scope_changes"][:3]:
            lines.append("║    " + f"⚠ {oos_file[:width - 10]}".ljust(width - 6) + "║")
        if len(scope["out_of_scope_changes"]) > 3:
            more = len(scope["out_of_scope_changes"]) - 3
            lines.append("║    " + f"... and {more} more".ljust(width - 6) + "║")

    lines.append("║" + " " * (width - 2) + "║")

    # Recommendation
    lines.append("╠" + "═" * (width - 2) + "╣")
    rec_line = f"RECOMMENDATION: {recommendation}"
    lines.append("║  " + rec_line.ljust(width - 4) + "║")
    lines.append("╠" + "═" * (width - 2) + "╣")

    # Reasoning
    lines.append("║" + " " * (width - 2) + "║")
    lines.append("║  " + "Reasoning:".ljust(width - 4) + "║")
    for reason in reasoning:
        wrapped = reason[:width - 6]
        lines.append("║  " + f"- {wrapped}".ljust(width - 4) + "║")

    lines.append("║" + " " * (width - 2) + "║")

    # Options
    lines.append("║  " + "Options:".ljust(width - 4) + "║")
    lines.append("║  " + "1. ITERATE - Provide feedback, sub-agent continues".ljust(width - 4) + "║")
    lines.append("║  " + "2. ACCEPT  - Merge into main branch".ljust(width - 4) + "║")
    lines.append("║  " + "3. RESET   - Discard work, start fresh".ljust(width - 4) + "║")
    lines.append("║" + " " * (width - 2) + "║")

    # Footer
    lines.append("╚" + "═" * (width - 2) + "╝")

    return "\n".join(lines)


def print_analysis(task_name: str, workspace_path: str = ".", **kwargs):
    """
    Analyze task and print formatted report.

    Args:
        task_name: Name of the task to analyze
        workspace_path: Path to the workspace
        **kwargs: Additional arguments passed to analyze_task()
    """
    analysis = analyze_task(task_name, workspace_path, **kwargs)
    report = format_analysis_report(analysis)
    print(report)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Task quality analyzer")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze task quality")
    analyze_parser.add_argument("task_name", help="Task name to analyze")
    analyze_parser.add_argument("--workspace", "-w", default=".", help="Workspace path")
    analyze_parser.add_argument("--main-branch", "-m", help="Main branch name")
    analyze_parser.add_argument("--ticket", "-t", help="Ticket ID")
    analyze_parser.add_argument("--no-tests", action="store_true", help="Skip running tests")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # parse-criteria command
    criteria_parser = subparsers.add_parser("parse-criteria", help="Parse acceptance criteria from spec.md")
    criteria_parser.add_argument("spec_path", help="Path to spec.md")

    args = parser.parse_args()

    if args.command == "analyze":
        analysis = analyze_task(
            args.task_name,
            args.workspace,
            main_branch=args.main_branch,
            ticket=args.ticket,
            run_tests=not args.no_tests
        )

        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            print(format_analysis_report(analysis))

        # Exit with appropriate code
        if not analysis.get("success"):
            exit(1)
        elif analysis.get("recommendation") == "RESET":
            exit(2)
        elif analysis.get("recommendation") == "ITERATE":
            exit(0)  # ITERATE is expected, not an error
        else:
            exit(0)

    elif args.command == "parse-criteria":
        result = parse_acceptance_criteria(args.spec_path)
        print(f"Total criteria: {result.total}")
        print(f"Met: {result.met}")
        print(f"Score: {result.score}%")
        print("\nCriteria:")
        for c in result.criteria:
            mark = "✓" if c.met else "✗"
            print(f"  {mark} {c.criterion}")

    else:
        parser.print_help()
