# Review Checklist

Structured checklist for reviewing sub-agent work.

## Quick Assessment

### Correctness
- [ ] Code does what the spec asked
- [ ] No obvious bugs or logic errors
- [ ] Edge cases handled appropriately
- [ ] Error handling is adequate

### Completeness
- [ ] All requirements from spec addressed
- [ ] All acceptance criteria met
- [ ] No missing functionality
- [ ] results.md is comprehensive

### Code Quality
- [ ] Follows existing codebase patterns
- [ ] Readable and maintainable
- [ ] No code smells (duplication, complexity)
- [ ] Appropriate naming conventions

### Tests
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Tests are meaningful (not just for coverage)
- [ ] Edge cases tested

### Git Hygiene
- [ ] Commits are atomic and well-described
- [ ] No merge commits in sub-branch
- [ ] No unrelated changes included
- [ ] Commit messages follow format

## Detailed Review

### 1. Read results.md

Check for:
- Clear summary of work done
- List of files modified/created
- Test results mentioned
- Risks/concerns documented
- Commits listed

**Questions:**
- Does the summary match what you see in the diff?
- Are there any risks the sub-agent identified?
- Any questions for operator?

### 2. Review Diff

```bash
git diff {main_branch}..{sub_branch}
```

Check for:
- Changes match spec requirements
- No unexpected file modifications
- Code style matches existing code
- No debug code left in
- No hardcoded values that should be config
- No sensitive data exposed

### 3. Review Commits

```bash
git log --oneline {main_branch}..{sub_branch}
```

Check for:
- Each commit is atomic (one logical change)
- Messages are clear and descriptive
- Format follows convention
- No "WIP" or "fix" only commits

### 4. Run Tests

```bash
cd task-{name}/worktree
npm test  # or appropriate command
```

Check for:
- All tests pass
- No new test failures
- Coverage maintained/improved

### 5. Security Review

- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] No hardcoded secrets/credentials
- [ ] Input validation adequate
- [ ] Authentication/authorization correct
- [ ] No sensitive data logged

### 6. Performance Review (if applicable)

- [ ] No obvious performance issues
- [ ] No N+1 queries
- [ ] Appropriate caching
- [ ] No blocking operations in hot paths

## Decision Matrix

### Accept if:
- All checklist items pass
- Tests pass
- No security concerns
- Code quality acceptable
- Meets acceptance criteria

### Iterate if:
- Most items pass but some issues
- Issues are clearly fixable
- Sub-agent can improve with feedback
- Approach is fundamentally sound

### Reset if:
- Fundamental approach is wrong
- Too many issues to iterate
- 3+ iterations without progress
- Significant scope creep
- Major security issues

## Review Notes Template

```markdown
### {DATE} {TIME} - {task_name} review

**Stats:**
- Commits: {count}
- Files: {count}
- Lines: +{ins} / -{del}

**Checklist:**
- Correctness: {PASS|ISSUES|FAIL}
- Completeness: {PASS|ISSUES|FAIL}
- Code Quality: {PASS|ISSUES|FAIL}
- Tests: {PASS|FAIL}

**Observations:**
{What you noticed}

**Issues Found:**
1. {Issue 1}
2. {Issue 2}

**Decision:** {ACCEPT|ITERATE|RESET}

**Reasoning:**
{Why this decision}
```

## Common Issues to Watch For

### Code Issues
- Copied code that should be abstracted
- Inconsistent error handling
- Missing null checks
- Hardcoded strings/numbers
- Unused imports/variables

### Test Issues
- Tests that don't actually test anything
- Missing edge case tests
- Flaky tests
- Tests that depend on external state

### Git Issues
- Giant commits with many changes
- Commits that don't compile/pass tests
- Merge commits in feature branch
- Unrelated changes bundled together

### Spec Compliance Issues
- Missing requirements
- Extra features not requested
- Different approach than specified
- Out of scope changes
