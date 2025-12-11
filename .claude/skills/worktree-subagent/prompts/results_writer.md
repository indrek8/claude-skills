# Results Writer Prompt

Templates and guidance for writing comprehensive results.md files.

## Purpose of results.md

The results.md file is your primary communication with the operator. It should:
- Summarize what you accomplished
- Document all changes made
- Report test status
- Highlight any risks or concerns
- Provide context for code review

## When to Write

Write results.md:
- After completing all work
- Before exiting the task
- After all commits are made

## Required Sections

Every results.md must include:

1. **Summary** - What was accomplished
2. **Changes Made** - High-level changes
3. **Files Modified** - Detailed file list
4. **Tests** - Test status and coverage
5. **Commits** - List of commits made
6. **Risks/Concerns** - Any issues to flag
7. **Notes for Reviewer** - Important context

## Template

```markdown
# Results: {task_name}

## Summary
{2-3 sentences describing what was accomplished. Be specific about the outcome.}

## Changes Made
- {High-level change 1}
- {High-level change 2}
- {High-level change 3}

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `path/to/file.ts` | Modified | {what changed} |
| `path/to/new.ts` | Created | {purpose} |
| `path/to/deleted.ts` | Deleted | {why} |

## Tests
- All existing tests: {PASS | FAIL (details)}
- New tests added: {count}
- Coverage: {before}% → {after}%

## Commits
| Hash | Message |
|------|---------|
| `abc1234` | {ticket}: {message} |
| `def5678` | {ticket}: {message} |

## Risks / Concerns
- {Any risks the reviewer should know about}
- {Or "None identified" if none}

## Notes for Reviewer
- {Important decisions made}
- {Assumptions taken}
- {Questions for operator}
```

## Section Guidelines

### Summary

Good summary:
```markdown
## Summary
Implemented structured logging for the payment service. Added info-level logs
for successful transactions and error-level logs for failures. All logs include
the transaction ID for traceability. Used the existing Winston logger utility.
```

Bad summary:
```markdown
## Summary
Did the task. Added logging.
```

### Changes Made

Good changes:
```markdown
## Changes Made
- Added info logging to processPayment() for successful transactions
- Added error logging to processPayment() for failed transactions
- Added transaction ID to all log contexts
- Added 3 new unit tests for logging behavior
```

Bad changes:
```markdown
## Changes Made
- Changed payment.ts
- Added tests
```

### Files Modified

Be comprehensive:
```markdown
## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `src/services/payment.ts` | Modified | Added logging calls |
| `src/types/payment.ts` | Modified | Added LogContext interface |
| `tests/services/payment.test.ts` | Modified | Added logging tests |
```

### Tests

Include specifics:
```markdown
## Tests
- All existing tests: PASS (45/45)
- New tests added: 3
  - should log successful payment
  - should log failed payment with error
  - should include transaction ID in logs
- Coverage: 78% → 82%
```

If tests fail:
```markdown
## Tests
- All existing tests: FAIL
  - 2 tests failing in order.test.ts (unrelated to changes)
  - Failures existed before my changes (verified with git stash)
- New tests added: 3 (all passing)
- Coverage: 78% → 82%
```

### Commits

List all commits:
```markdown
## Commits
| Hash | Message |
|------|---------|
| `a1b2c3d` | K-123: Add structured logging to payment service |
| `e4f5g6h` | K-123: Add unit tests for payment logging |
| `i7j8k9l` | K-123: Add LogContext type definition |
```

### Risks / Concerns

Be honest about issues:
```markdown
## Risks / Concerns
- Log volume may increase significantly in high-traffic scenarios
- Consider adding log sampling for production
- Transaction ID format assumption may need validation
```

Or if none:
```markdown
## Risks / Concerns
None identified.
```

### Notes for Reviewer

Provide context:
```markdown
## Notes for Reviewer
- Followed logging pattern from auth.service.ts
- Used structured logging format for consistency with existing logs
- Assumption: transaction ID is always available when processPayment is called
- Question: Should we also log partial refunds? (not in spec, didn't implement)
```

## Mode-Specific Templates

### Implement Mode Results

```markdown
# Results: {feature_name}

## Summary
Implemented {feature} that {what it does}. {Key technical decision if any}.

## Changes Made
- Created {new components/services}
- Modified {existing code} to {support feature}
- Added {tests/types/utilities}

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| ... | ... | ... |

## Tests
- All existing tests: PASS
- New tests added: {N}
- Coverage: X% → Y%

## Commits
| Hash | Message |
|------|---------|
| ... | ... |

## Risks / Concerns
- {Any risks}

## Notes for Reviewer
- {Important notes}
```

### Test Mode Results

```markdown
# Results: {test_task_name}

## Summary
Added {N} tests for {target}. Coverage increased from X% to Y%.
{Notable findings during testing if any}.

## Changes Made
- Added unit tests for {components}
- Added integration tests for {flows}
- Fixed {flaky tests if applicable}

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `tests/...` | Created/Modified | ... |

## Tests
- Previous test count: {N}
- New test count: {M}
- All tests passing
- Coverage: X% → Y%

## Coverage by Module
| Module | Before | After |
|--------|--------|-------|
| {module} | X% | Y% |

## Commits
| Hash | Message |
|------|---------|
| ... | ... |

## Risks / Concerns
- {Any gaps still remaining}

## Notes for Reviewer
- {Testing approach taken}
- {Edge cases covered}
```

### Refactor Mode Results

```markdown
# Results: {refactor_task_name}

## Summary
Refactored {target} to {improvement}. No behavior changes.
{Key structural changes}.

## Changes Made
- Extracted {functions/classes}
- Consolidated {duplicated code}
- Simplified {complex logic}

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| ... | ... | ... |

## Tests
- All tests: PASS (behavior unchanged)
- No new tests needed

## Before/After Metrics
| Metric | Before | After |
|--------|--------|-------|
| Lines of code | X | Y |
| Cyclomatic complexity | X | Y |
| Duplication | X | Y |

## Commits
| Hash | Message |
|------|---------|
| ... | ... |

## Risks / Concerns
- {None - behavior unchanged}

## Notes for Reviewer
- {Refactoring decisions}
- {Patterns applied}
```

### Review Mode Results

```markdown
# Results: {review_task_name}

## Summary
Completed {type} review of {target}. Found {N} critical, {M} high,
{O} medium/low issues.

## Review Scope
- Files reviewed: {N}
- Lines of code: {N}
- Focus areas: {areas}

## Critical Findings
### 1. {Finding Title}
**Severity:** CRITICAL
**Location:** `file:line`
**Description:** {what and why}
**Recommendation:** {how to fix}

## High Priority Findings
### 2. {Finding Title}
...

## Summary Statistics
| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Security | N | N | N | N |
| Performance | N | N | N | N |
| Quality | N | N | N | N |

## Recommendations
1. {Immediate action}
2. {Short-term action}
3. {Long-term action}

## Notes for Reviewer
- {Review methodology}
- {Limitations}
```

## Iteration Results

When addressing feedback:

```markdown
# Results: {task_name} (Iteration {N})

## Summary
Addressed all {N} issues from iteration feedback. {Brief description of fixes}.

## Feedback Addressed
| Issue | Resolution |
|-------|------------|
| {Issue 1 from feedback} | {How resolved} |
| {Issue 2 from feedback} | {How resolved} |

## Additional Changes
- {Any additional improvements made}

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| ... | ... | ... |

## Tests
- All tests: PASS
- New tests added: {N} (for issue fixes)

## Commits
| Hash | Message |
|------|---------|
| `xyz789` | K-123: Address iteration {N} feedback |

## Risks / Concerns
- {Any remaining concerns}

## Notes for Reviewer
- {Explanation of fix approaches}
- {Any clarifications needed}
```

## Quality Checklist

Before finalizing results.md:

- [ ] Summary is clear and specific
- [ ] All changes are documented
- [ ] All modified files are listed
- [ ] Test status is accurate
- [ ] All commits are listed with correct hashes
- [ ] Risks are honestly reported
- [ ] Reviewer notes provide useful context
- [ ] No placeholder text remaining
- [ ] Formatting is correct
