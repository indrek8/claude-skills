# Cookbook: Reject - Iterate

## Purpose
Provide feedback on incomplete/incorrect work and re-spawn sub-agent to continue.

## When to Use
- User says "operator iterate {name}" or "operator feedback {name}"
- After review finds issues that can be fixed
- Work is close but needs improvement

## Prerequisites
- Task reviewed
- Issues identified that can be addressed
- Approach is fundamentally sound (if not, use reset instead)

## Steps

### 1. Identify Issues

Document specific issues found during review:

```markdown
## Issues Found

### Issue 1: {title}
- Severity: HIGH/MEDIUM/LOW
- Location: {file:line or general area}
- Problem: {what's wrong}
- Expected: {what should be done}

### Issue 2: {title}
- Severity: HIGH/MEDIUM/LOW
- Location: {file:line}
- Problem: {what's wrong}
- Expected: {what should be done}
```

### 2. Write feedback.md

```bash
TASK="fix-logging"
cat > task-${TASK}/feedback.md << 'EOF'
# Feedback: {task_name} (Iteration {N})

## Reviewed: {date}
## Reviewer: Operator

---

## Overall Assessment

{1-2 sentence summary: "Good progress but missing X" or "Core implementation solid, needs Y"}

---

## Issues Found

### Issue 1: {Issue Title}
- **Severity:** {HIGH|MEDIUM|LOW}
- **Location:** `{file_path}:{line_number}`
- **Problem:** {Clear description of what's wrong}
- **Expected:** {What the correct behavior/code should be}

### Issue 2: {Issue Title}
- **Severity:** {HIGH|MEDIUM|LOW}
- **Location:** `{file_path}`
- **Problem:** {Description}
- **Expected:** {Expected behavior}

---

## Required Changes

1. {Specific action item 1}
2. {Specific action item 2}
3. {Specific action item 3}

---

## What Worked Well

- {Positive feedback 1}
- {Positive feedback 2}

---

## Hints for This Iteration

- {Helpful hint or reference}
- {Pattern to follow}

---

## Clarifications

{Any spec clarifications based on questions or misunderstandings}

---

## Next Steps

1. Address all issues listed above
2. Re-run tests to ensure nothing broke
3. Update results.md with iteration summary
4. Commit changes with clear message referencing this feedback
EOF
```

### 3. Update plan.md

```markdown
### X. {task_name}
- Status: ITERATING
- Branch: feature/{ticket}/{task_name}
- Iteration: {N}
- Issues: {count} ({high} high, {medium} medium, {low} low)
```

### 4. Log in review-notes.md

```markdown
### {DATE} {TIME} - {task_name} review (Iteration {N-1})

**Diff Stats:** {lines} lines across {files} files

**Quality Assessment:**
- Correctness: NEEDS_WORK
- Completeness: {assessment}
- Code Quality: {assessment}
- Tests: {PASS|FAIL}

**Issues Found:**
1. {Issue 1 summary}
2. {Issue 2 summary}

**Decision:** ITERATE

**Reasoning:**
{Why iteration rather than accept or reset}

**Feedback written to:** task-{task_name}/feedback.md
```

### 5. Re-spawn Sub-Agent

The sub-agent prompt for iteration:

```
You are a sub-agent continuing work on task '{task_name}'.

IMPORTANT: This is iteration {N}. Your previous work was reviewed and needs improvements.

WORKSPACE CONTEXT:
- Task folder: {workspace}/task-{task_name}
- Your worktree: {workspace}/task-{task_name}/worktree
- Your branch: feature/{ticket}/{task_name}

CRITICAL FIRST STEP:
Read {workspace}/task-{task_name}/feedback.md IMMEDIATELY.
This contains the issues you need to fix.

INSTRUCTIONS:
1. Read feedback.md to understand what needs to be fixed
2. Review the issues and required changes
3. Make the necessary fixes in your worktree
4. Run tests to verify fixes
5. Commit with message: "{ticket}: Address iteration {N} feedback"
6. Update results.md with iteration summary
7. Exit when complete

DO NOT:
- Start over unless feedback explicitly says to
- Ignore any issues marked HIGH severity
- Make unrelated changes

BUILD ON YOUR PREVIOUS WORK. Fix the specific issues identified.
```

### 6. Report Iteration

```
✓ Iteration feedback written for '{task_name}'

Iteration: {N}
Issues identified: {count}
  - {high} HIGH severity
  - {medium} MEDIUM severity
  - {low} LOW severity

Feedback written to: task-{task_name}/feedback.md

Re-spawning sub-agent...

The sub-agent will:
1. Read feedback.md
2. Address identified issues
3. Update results.md
4. Commit fixes

Run "operator review {task_name}" when complete.
```

## Writing Good Feedback

### Be Specific

```markdown
# Bad
The logging is wrong.

# Good
### Issue: Log format doesn't match specification
- **Location:** `src/services/payment.ts:45`
- **Problem:** Using `logger.info(message)` but spec requires structured format
- **Expected:** `logger.info({ event: 'payment_processed', orderId, amount })`
```

### Be Actionable

```markdown
# Bad
Fix the tests.

# Good
## Required Changes
1. Fix test in `tests/payment.test.ts:23` - mock should return `{ success: true }` not `true`
2. Add missing test for error case when payment fails
3. Remove console.log statements from test file
```

### Acknowledge Good Work

```markdown
## What Worked Well
- Clean separation of logging utility from business logic
- Good error handling pattern in the catch blocks
- Commit messages were clear and well-formatted
```

### Provide Hints

```markdown
## Hints for This Iteration
- Look at `src/services/auth.ts:78-95` for the correct logging pattern
- Use `requestId` from the async context, not a new UUID each time
- The test helper in `tests/utils/mockLogger.ts` can simplify your test setup
```

## Iteration Limits

Consider reset instead of iterate if:
- More than 3 iterations on same task
- Sub-agent keeps making same mistakes
- Fundamental approach seems wrong
- Scope creep is occurring

```
This is iteration {N} for task '{task_name}'.

Consider:
- Is the approach fundamentally correct?
- Is the spec clear enough?
- Should we reset and try a different approach?

Options:
1. Continue with iteration
2. Reset and revise spec
3. Reset and try different approach
```

## Error Handling

> See SKILL.md "Error Handling" section for complete error reference and recovery procedures.

| Error | Quick Fix |
|-------|-----------|
| Previous feedback exists | Append new feedback or replace if superseded |
| No changes since feedback | Re-spawn sub-agent or check if still running |

## Checklist

- [ ] Issues clearly identified
- [ ] Severity assigned to each issue
- [ ] Specific locations noted
- [ ] Expected behavior described
- [ ] Required changes listed
- [ ] Positive feedback included
- [ ] Hints provided
- [ ] feedback.md written
- [ ] plan.md updated (ITERATING)
- [ ] review-notes.md logged
- [ ] Sub-agent re-spawned
