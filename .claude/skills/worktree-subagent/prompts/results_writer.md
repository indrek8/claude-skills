# Results Writer Prompt

Guidance for writing comprehensive results.md files.

## Template

> Use the template in `templates/results.md` for structure.

```markdown
# Results: {task_name}

## Summary
{2-3 sentences: what was accomplished, key technical decisions}

## Changes Made
- {High-level change 1}
- {High-level change 2}

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `path/to/file.ts` | Modified | {what changed} |

## Tests
- All existing tests: {PASS | FAIL (details)}
- New tests added: {count}
- Coverage: {before}% → {after}%

## Commits
| Hash | Message |
|------|---------|
| `abc1234` | {ticket}: {message} |

## Risks / Concerns
- {Risks for reviewer, or "None identified"}

## Notes for Reviewer
- {Decisions made, assumptions, questions}
```

## Writing Guidelines

| Section | Good | Bad |
|---------|------|-----|
| Summary | "Implemented structured logging with transaction IDs for traceability" | "Did the task" |
| Changes | "Added error logging to processPayment() for failures" | "Changed payment.ts" |
| Tests | "FAIL - 2 tests in order.test.ts (unrelated, existed before)" | "Some tests fail" |
| Risks | "Log volume may increase significantly in high-traffic" | (empty) |

## Mode-Specific Additions

**Implement mode:** Standard template

**Test mode:** Add "Coverage by Module" table

**Refactor mode:** Add "Before/After Metrics" table (LOC, complexity, duplication)

**Review mode:** Replace Changes with "Findings" sections by severity (Critical/High/Medium/Low)

## Iteration Results

When addressing feedback, add a "Feedback Addressed" section:

```markdown
## Feedback Addressed
| Issue | Resolution |
|-------|------------|
| {Issue from feedback} | {How resolved} |
```

## Quality Checklist

- [ ] Summary is clear and specific
- [ ] All changes documented
- [ ] All modified files listed
- [ ] Test status accurate
- [ ] All commits listed with hashes
- [ ] Risks honestly reported
- [ ] No placeholder text remaining
