# Spec Reader Prompt

How to read and understand spec.md before starting work.

## Reading Process

1. **Read spec.md completely** before starting any work
2. **Extract key sections** (see below)
3. **Verify understanding** with checklist
4. **Document ambiguities** in results.md

## Key Sections to Extract

| Section | What to Find |
|---------|--------------|
| **Objective** | Primary goal in one sentence |
| **Requirements** | Checklist of what must be done |
| **Files to Modify** | Which files, what action (create/modify) |
| **Acceptance Criteria** | Testable conditions for "done" |
| **Out of Scope** | What NOT to do (respect boundaries) |
| **Hints** | Guidance, patterns to follow |

## Understanding Checklist

Before starting work:
- [ ] I understand the objective
- [ ] I can list all requirements
- [ ] I know which files to modify
- [ ] I understand acceptance criteria
- [ ] I know what's out of scope
- [ ] I've noted all hints/guidance

**If unclear:** Document assumption, proceed, note in results.md

## Handling Feedback (Iteration)

If `feedback.md` exists:
1. Read feedback issues **first**
2. Address feedback **before** continuing spec work
3. Document resolutions in results.md

## Red Flags

| Red Flag | Action |
|----------|--------|
| "Make it better" | Ask: better how? Need specifics |
| No acceptance criteria | Define your own, note in results |
| Conflicting requirements | Document choice and reasoning |
| "While you're there..." | Check if actually in scope |

## Quick Summary Template

After reading spec, mentally summarize:

```
I need to: {objective}
By: {main actions}
Touching: {files}
Success: {criteria}
NOT doing: {out of scope}
```
