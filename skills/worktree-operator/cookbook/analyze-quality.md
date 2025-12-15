# Cookbook: Analyze Task Quality

## Purpose
Analyze sub-agent output quality and get a recommendation for accept, iterate, or reset.

## When to Use
- User says "operator analyze {name}"
- Before deciding accept/iterate/reset
- When reviewing a task and wanting automated guidance

## Prerequisites
- Task exists with worktree
- Sub-agent has completed (or made progress)
- spec.md exists with acceptance criteria

## Steps

### 1. Run Quality Analysis

```python
from tools.quality_analyzer import analyze_task, format_analysis_report

# Analyze the task
analysis = analyze_task("fix-logging", ".")

# Print formatted report
print(format_analysis_report(analysis))
```

Or via command line:
```bash
cd .claude/skills/worktree-operator/tools
python quality_analyzer.py analyze fix-logging --workspace /path/to/workspace
```

### 2. Review the Report

The analysis provides:

```
╔══════════════════════════════════════════════════════════════╗
║            Quality Assessment: fix-logging                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Overall Score: 85/100                                       ║
║                                                              ║
║  Acceptance Criteria: 4/5 met (80%)                          ║
║    ✓ Replace console.log with logger                         ║
║    ✓ Include timestamp in logs                               ║
║    ✓ Include service name in logs                            ║
║    ✓ All existing tests pass                                 ║
║    ✗ Logs include request ID                                 ║
║                                                              ║
║  Tests: PASSING (12.3s)                                      ║
║  Diff Size: 145 lines (reasonable)                           ║
║  Scope: IN_SCOPE                                             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  RECOMMENDATION: ITERATE                                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Reasoning:                                                  ║
║  - Missing criteria: 1 items                                 ║
║  - "Logs include request ID" not met                         ║
║  - Issues are fixable - recommend iterating                  ║
║                                                              ║
║  Options:                                                    ║
║  1. ITERATE - Provide feedback, sub-agent continues          ║
║  2. ACCEPT  - Merge into main branch                         ║
║  3. RESET   - Discard work, start fresh                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

### 3. Understand the Scoring

The quality score is calculated from:

| Factor | Weight | Description |
|--------|--------|-------------|
| Acceptance Criteria | 40% | How many spec.md criteria are met |
| Tests | 30% | Test pass/fail status |
| Diff Size | 15% | Size of changes (reasonable vs excessive) |
| Scope | 15% | Whether changes are within spec scope |

### 4. Interpret Recommendations

| Recommendation | Score | Meaning |
|----------------|-------|---------|
| ACCEPT | >= 90 | Ready to merge (all critical criteria met) |
| ITERATE | 50-89 | Fixable issues, continue with feedback |
| RESET | < 50 | Fundamental problems, start over |

**Critical overrides:**
- FAILING tests always trigger ITERATE (never ACCEPT)
- More than 5 out-of-scope files triggers RESET

### 5. Follow the Recommendation

Based on the recommendation:

#### ACCEPT
```
operator accept {name}
```
See: accept-task.md

#### ITERATE
```
operator iterate {name}
```
See: reject-iterate.md

Write feedback about what's missing, then re-spawn the sub-agent.

#### RESET
```
operator reset {name}
```
See: reject-reset.md

Consider revising the spec.md before re-spawning.

## Using Python Tools

```python
from tools.quality_analyzer import (
    analyze_task,
    parse_acceptance_criteria,
    check_test_status,
    analyze_diff_size,
    check_scope,
    format_analysis_report
)

# Full analysis
analysis = analyze_task("fix-logging", ".")

# Access individual components
if analysis["success"]:
    print(f"Score: {analysis['score']}")
    print(f"Recommendation: {analysis['recommendation']}")

    # Check specific details
    criteria = analysis["details"]["acceptance_criteria"]
    print(f"Criteria met: {criteria['met']}/{criteria['total']}")

    tests = analysis["details"]["tests"]
    print(f"Tests: {tests['status']}")

    diff = analysis["details"]["diff_size"]
    print(f"Diff: {diff['total_lines']} lines ({diff['assessment']})")

    scope = analysis["details"]["scope"]
    if not scope["in_scope"]:
        print(f"Out of scope: {scope['out_of_scope_changes']}")

# Parse criteria only
criteria = parse_acceptance_criteria("task-fix-logging/spec.md")
for c in criteria.criteria:
    mark = "✓" if c.met else "✗"
    print(f"{mark} {c.criterion}")

# Skip tests for faster analysis
analysis = analyze_task("fix-logging", ".", run_tests=False)
```

## JSON Output

For scripting, get JSON output:

```bash
python quality_analyzer.py analyze fix-logging --json
```

```json
{
  "success": true,
  "task_name": "fix-logging",
  "score": 85.0,
  "recommendation": "ITERATE",
  "reasoning": [
    "Missing criteria: 1 items",
    "- Logs include request ID...",
    "Issues are fixable - recommend iterating"
  ],
  "details": {
    "acceptance_criteria": {
      "total": 5,
      "met": 4,
      "unmet": ["Logs include request ID"],
      "score": 80.0
    },
    "tests": {
      "status": "PASSING",
      "score": 100.0,
      "duration": 12.3
    },
    "diff_size": {
      "lines_added": 120,
      "lines_removed": 25,
      "total_lines": 145,
      "assessment": "reasonable",
      "score": 90.0
    },
    "scope": {
      "in_scope": true,
      "out_of_scope_changes": [],
      "score": 100.0
    }
  }
}
```

## Diff Size Assessment

| Lines Changed | Assessment | Score | Guidance |
|---------------|------------|-------|----------|
| < 100 | small | 100 | Good, focused change |
| 100-500 | reasonable | 90 | Typical task size |
| 500-1000 | large | 70 | Consider splitting |
| > 1000 | excessive | 50 | Review for scope creep |

## Common Issues

### No acceptance criteria in spec.md
```
Acceptance Criteria: 0/0 met (100%)
```
The analyzer assumes success if no criteria found. Add criteria to spec.md:
```markdown
## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [x] Criterion 3 (already done)
```

### Tests not detected
```
Tests: NOT_RUN (No test framework detected)
```
Set the test command in workspace.json:
```json
{
  "test_command": "npm test"
}
```

### Out-of-scope changes
```
Scope: OUT_OF_SCOPE
  ⚠ src/unrelated/file.ts
```
The sub-agent modified files not listed in "Files to Modify" section.
Options:
1. ITERATE with feedback to remove those changes
2. Accept if changes are justified
3. Add the files to spec.md if they should be in scope

## Integrating with Review

After analyzing, use review-task.md cookbook with the analysis results:

1. Run `operator analyze {name}` first
2. Review the automated assessment
3. Optionally do manual review for nuances
4. Make decision based on combined insight

## Checklist

- [ ] Analysis run successfully
- [ ] Score understood
- [ ] Recommendation considered
- [ ] Reasoning reviewed
- [ ] Decision made (accept/iterate/reset)
- [ ] review-notes.md updated with analysis summary
