# Cookbook: Review Task

## Purpose
Review sub-agent output and decide: accept, iterate, or reset.

## When to Use
- User says "operator review {name}"
- After sub-agent completes work
- When checking on task progress

## Prerequisites
- Task exists with worktree
- Sub-agent has completed (or made progress)
- results.md written (ideally)

## Steps

### 1. Run Automated Quality Analysis (Recommended)

Start with automated analysis to get a recommendation:

```python
from tools.quality_analyzer import analyze_task, format_analysis_report

# Get automated quality assessment
analysis = analyze_task("fix-logging", ".")
print(format_analysis_report(analysis))
```

Or via command line:
```bash
cd .claude/skills/worktree-operator/tools
python quality_analyzer.py analyze fix-logging --workspace /path/to/workspace
```

This provides:
- Quality score (0-100)
- Acceptance criteria check
- Test status
- Diff size assessment
- Scope verification
- Recommendation (ACCEPT/ITERATE/RESET)

See analyze-quality.md for detailed guidance on interpreting results.

### 2. Gather Additional Review Information

```bash
TASK="fix-logging"
TICKET="K-123"
MAIN_BRANCH="feature/K-123_user_auth"
SUB_BRANCH="feature/${TICKET}/${TASK}"

# Read results summary
cat task-${TASK}/results.md

# View commits
cd repo
git log --oneline ${MAIN_BRANCH}..${SUB_BRANCH}

# View diff statistics
git diff --stat ${MAIN_BRANCH}..${SUB_BRANCH}

# View full diff
git diff ${MAIN_BRANCH}..${SUB_BRANCH}
```

### 3. Manual Quality Assessment (Optional)

If the automated analysis needs human judgment, review against these criteria:

#### Correctness
- Does the code do what the spec asked?
- Are there any obvious bugs?
- Does it handle edge cases?

#### Completeness
- Are all requirements addressed?
- Are all acceptance criteria met?
- Are tests included?

#### Code Quality
- Does it follow existing patterns?
- Is it readable and maintainable?
- Are there any code smells?

#### Tests
- Do existing tests pass?
- Are new tests adequate?
- Is coverage acceptable?

### 4. Check Test Results

```bash
cd task-${TASK}/worktree

# Run tests (adjust for your project)
npm test
# or
pytest
# or
go test ./...
# or
cargo test
```

### 5. Present Review Summary

```
╔══════════════════════════════════════════════════════════════╗
║                    REVIEW: {task_name}                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Branch: feature/{ticket}/{task_name}                         ║
║  Commits: {count}                                             ║
║  Files changed: {count}                                       ║
║  Lines: +{insertions} / -{deletions}                          ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║  RESULTS SUMMARY                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  {First paragraph from results.md}                            ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║  COMMITS                                                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  {hash1} {message1}                                           ║
║  {hash2} {message2}                                           ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║  ASSESSMENT                                                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Correctness:  {GOOD / NEEDS_WORK / POOR}                     ║
║  Completeness: {GOOD / NEEDS_WORK / POOR}                     ║
║  Code Quality: {GOOD / NEEDS_WORK / POOR}                     ║
║  Tests:        {PASS / FAIL / MISSING}                        ║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║  DECISION OPTIONS                                             ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  1. ACCEPT  - Merge into main branch                          ║
║  2. ITERATE - Provide feedback, sub-agent continues           ║
║  3. RESET   - Discard work, start fresh                       ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝

What would you like to do? [1/2/3]:
```

### 6. Process Decision

Based on user decision:

#### Accept
→ Run accept-task.md cookbook

#### Iterate
→ Run reject-iterate.md cookbook

#### Reset
→ Run reject-reset.md cookbook

### 7. Log Review Decision

Add to review-notes.md:

```markdown
### {DATE} {TIME} - {task_name} review

**Diff Stats:** {lines} lines across {files} files

**Quality Assessment:**
- Correctness: {GOOD|NEEDS_WORK|POOR}
- Completeness: {GOOD|NEEDS_WORK|POOR}
- Code Quality: {GOOD|NEEDS_WORK|POOR}
- Tests: {PASS|FAIL|MISSING}

**Observations:**
{SPECIFIC_OBSERVATIONS_ABOUT_THE_CODE}

**Decision:** {ACCEPT|ITERATE|RESET}

**Reasoning:**
{WHY_THIS_DECISION}

**Next Action:**
{WHAT_HAPPENS_NEXT}
```

## Using Python Tools

```python
from tools.task import task_status
from tools.git_ops import get_diff_stats, get_commits_between
from tools.quality_analyzer import analyze_task, format_analysis_report

# Run full quality analysis (recommended)
analysis = analyze_task("fix-logging", ".")
if analysis["success"]:
    print(format_analysis_report(analysis))
    print(f"\nRecommendation: {analysis['recommendation']}")

# Get task info
status = task_status("fix-logging", ".")

# Get diff stats
stats = get_diff_stats(
    "repo",
    "feature/K-123_user_auth",
    "feature/K-123/fix-logging"
)

# Get commits
commits = get_commits_between(
    "repo",
    "feature/K-123_user_auth",
    "feature/K-123/fix-logging"
)

print(f"Files changed: {stats['files_changed']}")
print(f"Insertions: +{stats['insertions']}")
print(f"Deletions: -{stats['deletions']}")
print(f"Commits: {len(commits)}")
```

## Review Checklist

### Spec Compliance
- [ ] All requirements addressed
- [ ] All acceptance criteria met
- [ ] Nothing out of scope included

### Code Quality
- [ ] Follows existing patterns
- [ ] No obvious bugs
- [ ] Handles edge cases
- [ ] No security vulnerabilities
- [ ] No hardcoded values that should be config

### Tests
- [ ] Existing tests pass
- [ ] New tests added
- [ ] Tests are meaningful (not just for coverage)

### Documentation
- [ ] results.md is comprehensive
- [ ] Code comments where needed
- [ ] No TODO/FIXME left unaddressed

### Git Hygiene
- [ ] Commits are atomic and well-described
- [ ] No merge commits in sub-branch
- [ ] No unrelated changes

## Common Issues

### Missing results.md
```
results.md not found or empty.

The sub-agent should have written results.md.
You can still review via git diff, but consider:
1. Ask sub-agent to write results.md
2. Review based on diff only
3. Reset and re-spawn with clearer instructions
```

### Tests failing
```
Tests are failing:
{test output}

Options:
1. ITERATE - ask sub-agent to fix tests
2. ACCEPT anyway - if failures are unrelated
3. RESET - if approach is fundamentally wrong
```

### Too many changes
```
This task modified {count} files, which seems excessive.

The sub-agent may have:
- Gone beyond scope
- Made unnecessary refactoring
- Included unrelated changes

Consider:
1. Review carefully for out-of-scope changes
2. ITERATE with feedback to reduce scope
3. Accept if all changes are justified
```

## Decision Guidelines

### Accept when:
- All acceptance criteria met
- Tests pass
- Code quality is acceptable
- No security concerns

### Iterate when:
- Close but missing something
- Minor issues to fix
- Tests failing but fixable
- Needs more tests

### Reset when:
- Fundamental approach is wrong
- Too much out-of-scope work
- Code quality is unacceptable
- Better to start fresh than fix

## Checklist

- [ ] Quality analysis run (`operator analyze {name}`)
- [ ] results.md read
- [ ] Diff reviewed
- [ ] Commits examined
- [ ] Tests run
- [ ] Quality assessed
- [ ] Decision made
- [ ] review-notes.md updated
- [ ] Next action initiated
