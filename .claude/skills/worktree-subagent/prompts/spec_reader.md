# Spec Reader Prompt

Templates for parsing and understanding spec.md content.

## Reading Spec.md

When you receive a task, start by thoroughly reading the spec:

```
Read the spec.md file in your task folder.
Extract and understand each section before proceeding.
```

## Extracting Key Information

### Task Identification

```markdown
From spec.md, identify:

**Task ID:** {ticket number or identifier}
**Task Name:** {descriptive name}
**Mode:** {implement | test | refactor | review}
**Priority:** {if specified}
```

### Objective Extraction

```markdown
OBJECTIVE: What is the primary goal?

Read the objective section and summarize in one sentence:
- What needs to be accomplished?
- What is the expected end state?
```

### Requirements Checklist

```markdown
REQUIREMENTS: What must be done?

Create a checklist from the requirements section:
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

Each item should be verifiable.
```

### Files to Modify

```markdown
FILES: Where will you work?

List files mentioned in the spec:
| File | Action | Notes |
|------|--------|-------|
| path/to/file.ts | Modify | Main changes here |
| path/to/new.ts | Create | New file needed |
| path/to/test.ts | Modify | Add tests |
```

### Acceptance Criteria

```markdown
ACCEPTANCE CRITERIA: How do we know it's done?

Extract testable criteria:
1. [ ] Criterion 1 (how to verify)
2. [ ] Criterion 2 (how to verify)
3. [ ] Criterion 3 (how to verify)
```

### Out of Scope

```markdown
OUT OF SCOPE: What should NOT be done?

List items explicitly excluded:
- Do NOT change X
- Do NOT refactor Y
- Do NOT add feature Z

These are boundaries. Respect them.
```

### Hints and Guidance

```markdown
HINTS: What help is provided?

Note any guidance from the spec:
- Look at similar implementation in X
- Use pattern from Y
- Be careful about Z
```

## Spec Validation Checklist

Before starting work, verify you understand:

```markdown
## Spec Understanding Checklist

- [ ] I understand the objective
- [ ] I can list all requirements
- [ ] I know which files to modify
- [ ] I understand the acceptance criteria
- [ ] I know what's out of scope
- [ ] I've noted all hints/guidance

If any item is unclear:
- Document the ambiguity
- Make reasonable assumption
- Note in results.md for operator review
```

## Handling Ambiguous Specs

When spec is unclear:

```markdown
## Ambiguity Resolution

**Unclear Item:** {what's unclear}

**Options:**
1. Interpretation A: {description}
2. Interpretation B: {description}

**Decision:** Going with option {N} because {reasoning}

**Note:** Will document in results.md for operator review.
```

## Spec Summary Template

After reading, create a mental summary:

```markdown
## Task Summary

**I need to:** {one sentence objective}

**By:**
1. {main action 1}
2. {main action 2}
3. {main action 3}

**Touching files:**
- {file 1}
- {file 2}

**Success looks like:**
- {criterion 1}
- {criterion 2}

**I must NOT:**
- {out of scope item}
```

## Cross-Reference with Feedback

If feedback.md exists:

```markdown
## Iteration Context

This is iteration {N}.

**Previous Issues:**
1. {issue from feedback}
2. {issue from feedback}

**My Plan:**
1. Address {issue 1} by {action}
2. Address {issue 2} by {action}
3. Continue with remaining spec work

**Priority:** Fix feedback issues FIRST, then complete spec.
```

## Questions to Ask Yourself

Before starting implementation:

1. **Do I understand the WHY?**
   - Why is this change needed?
   - What problem does it solve?

2. **Do I know the WHAT?**
   - What exactly needs to change?
   - What files are involved?

3. **Do I understand the HOW?**
   - How should I approach this?
   - What patterns should I follow?

4. **Do I know the BOUNDARIES?**
   - What's in scope?
   - What's explicitly out of scope?

5. **Can I verify SUCCESS?**
   - How will I know I'm done?
   - What tests prove completion?

## Red Flags in Specs

Watch for these issues:

```markdown
## Spec Red Flags

1. **Vague Requirements**
   "Make it better" - Better how? Need specifics.

2. **Missing Acceptance Criteria**
   No way to verify done. Ask or define your own.

3. **Conflicting Requirements**
   Requirement A contradicts B. Document and choose.

4. **Scope Creep Hints**
   "While you're there, also..." - Check if in scope.

5. **Missing Context**
   Need to understand existing code first.
```

## Example Spec Parsing

Given this spec.md:

```markdown
# Task: Add Logging to Payment Service

## Objective
Add structured logging to the payment service for debugging and audit purposes.

## Requirements
- Add info logs for successful payments
- Add error logs for failed payments
- Include transaction ID in all logs
- Use existing logger utility

## Files to Modify
- src/services/payment.ts

## Acceptance Criteria
- All payment operations logged
- Logs include transaction ID
- Tests pass
- No console.log statements

## Out of Scope
- Changing log storage/transport
- Adding metrics
- Modifying other services
```

Parsed summary:

```markdown
## My Understanding

**Task:** K-XXX - Add logging to payment service
**Mode:** Implement

**Objective:** Add structured logging for debugging and audit.

**I need to:**
1. Add info logs for successful payments
2. Add error logs for failed payments
3. Include transaction ID in all log entries
4. Use existing logger (not console.log)

**File:** src/services/payment.ts

**Success when:**
- [ ] All payment ops have logs
- [ ] Transaction ID in every log
- [ ] Using logger utility (not console.log)
- [ ] Tests pass

**NOT doing:**
- Log storage changes
- Metrics
- Other services

**Approach:**
1. Find existing logger utility
2. Identify all payment operations
3. Add appropriate log calls
4. Run tests
```
