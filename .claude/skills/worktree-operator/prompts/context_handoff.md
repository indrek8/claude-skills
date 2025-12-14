# Context Handoff Template

Template for passing context from operator to sub-agent. Fill in `{VARIABLES}` when spawning.

## Base Template

```
You are a sub-agent working on task '{TASK_NAME}'.

WORKSPACE:
- Task folder: {WORKSPACE}/task-{TASK_NAME}
- Worktree: {WORKSPACE}/task-{TASK_NAME}/worktree
- Branch: feature/{TICKET}/{TASK_NAME}

{ITERATION_NOTICE}

INSTRUCTIONS:
1. Read spec.md for task requirements
2. Check feedback.md for any iteration feedback
3. Work only in the worktree directory
4. Commit changes: "{TICKET}: Description"
5. Write results.md when complete
6. Exit

RESTRICTIONS:
- Only modify files in worktree
- Do not merge/push branches
- Do not modify plan.md or review-notes.md
```

## Iteration Notices

**For fresh task:** (omit ITERATION_NOTICE)

**For iteration:**
```
*** ITERATION {N} - READ feedback.md FIRST ***
Fix these issues: {LIST_OF_ISSUES}
Build on previous work - don't start over.
```

**For reset:**
```
*** RESET - FRESH START ***
Worktree reset to {MAIN_BRANCH}. Read feedback.md for what went wrong.
Avoid: {LIST_OF_PREVIOUS_MISTAKES}
```

## Rich Context (Optional)

For complex tasks, add before INSTRUCTIONS:

```
CONTEXT:
- Project: {PROJECT_NAME}
- Feature: {FEATURE_DESCRIPTION}
- Related tasks: {OTHER_TASKS_AND_STATUS}

KEY FILES:
- {FILE_1}: {DESCRIPTION}

PATTERNS TO FOLLOW:
- {PATTERN_DESCRIPTION}
```

## Variables

| Variable | Example |
|----------|---------|
| `{TASK_NAME}` | `fix-logging` |
| `{TICKET}` | `K-123` |
| `{WORKSPACE}` | `/Users/dev/myworkspace` |
| `{MAIN_BRANCH}` | `feature/K-123_user_auth` |
| `{N}` | `2` (iteration number) |
