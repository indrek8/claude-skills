# Context Handoff Template

Template for passing context from operator to sub-agent.

## Basic Handoff

```
You are a sub-agent working on task '{TASK_NAME}'.

WORKSPACE:
- Task folder: {WORKSPACE}/task-{TASK_NAME}
- Worktree: {WORKSPACE}/task-{TASK_NAME}/worktree
- Branch: feature/{TICKET}/{TASK_NAME}

INSTRUCTIONS:
1. Read spec.md for task requirements
2. Check feedback.md for any iteration feedback
3. Work only in the worktree directory
4. Commit changes with clear messages
5. Write results.md when complete
6. Exit

COMMIT FORMAT: "{TICKET}: Description"

RESTRICTIONS:
- Only modify files in worktree
- Do not merge branches
- Do not push to remote
- Do not modify plan.md or review-notes.md
```

## Iteration Handoff

```
You are a sub-agent CONTINUING work on task '{TASK_NAME}'.

*** THIS IS ITERATION {N} - READ FEEDBACK FIRST ***

WORKSPACE:
- Task folder: {WORKSPACE}/task-{TASK_NAME}
- Worktree: {WORKSPACE}/task-{TASK_NAME}/worktree
- Branch: feature/{TICKET}/{TASK_NAME}

CRITICAL: Read feedback.md IMMEDIATELY.
It contains issues you must fix from the previous review.

INSTRUCTIONS:
1. READ feedback.md - understand what needs fixing
2. Address each issue listed
3. Build on previous work - don't start over
4. Run tests after fixes
5. Commit: "{TICKET}: Address iteration {N} feedback"
6. Update results.md with iteration summary
7. Exit

PREVIOUS ISSUES TO FIX:
{LIST_OF_ISSUES_FROM_FEEDBACK}
```

## Reset Handoff

```
You are a sub-agent starting FRESH on task '{TASK_NAME}'.

*** PREVIOUS ATTEMPT WAS RESET - READ FEEDBACK FOR CONTEXT ***

WORKSPACE:
- Task folder: {WORKSPACE}/task-{TASK_NAME}
- Worktree: {WORKSPACE}/task-{TASK_NAME}/worktree (clean state)
- Branch: feature/{TICKET}/{TASK_NAME}

The worktree has been reset to {MAIN_BRANCH}.

IMPORTANT: Read feedback.md first.
It explains what went wrong before and how to approach this differently.

INSTRUCTIONS:
1. READ feedback.md - understand previous failure
2. READ spec.md - task requirements
3. Follow the new approach guidance
4. Implement carefully, avoiding previous mistakes
5. Run tests frequently
6. Commit with clear messages
7. Write comprehensive results.md
8. Exit

AVOID THESE MISTAKES:
{LIST_OF_PREVIOUS_MISTAKES}
```

## Rich Context Handoff

For complex tasks, include more context:

```
You are a sub-agent working on task '{TASK_NAME}'.

═══════════════════════════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════════════════════════

PROJECT: {PROJECT_NAME}
TICKET: {TICKET}
FEATURE: {FEATURE_DESCRIPTION}

This task is part of a larger feature. Other tasks include:
- {TASK_1}: {STATUS}
- {TASK_2}: {STATUS}
- {TASK_3}: {STATUS} (this task)

═══════════════════════════════════════════════════════════════
WORKSPACE
═══════════════════════════════════════════════════════════════

Task folder: {WORKSPACE}/task-{TASK_NAME}
Worktree: {WORKSPACE}/task-{TASK_NAME}/worktree
Branch: feature/{TICKET}/{TASK_NAME}
Based on: {MAIN_BRANCH}

═══════════════════════════════════════════════════════════════
CODEBASE CONTEXT
═══════════════════════════════════════════════════════════════

Key files you'll work with:
- {FILE_1}: {DESCRIPTION}
- {FILE_2}: {DESCRIPTION}

Related code to reference:
- {FILE_3}: {WHY_RELEVANT}

Patterns to follow:
- {PATTERN_DESCRIPTION}

═══════════════════════════════════════════════════════════════
INSTRUCTIONS
═══════════════════════════════════════════════════════════════

1. Read spec.md for detailed requirements
2. Check feedback.md for any iteration notes
3. Review the related code mentioned above
4. Implement following established patterns
5. Add tests for new functionality
6. Commit with clear, atomic commits
7. Write results.md summarizing your work
8. Exit when complete

═══════════════════════════════════════════════════════════════
COMMIT FORMAT
═══════════════════════════════════════════════════════════════

{TICKET}: Brief description

Example:
K-123: Add structured logging to payment service

═══════════════════════════════════════════════════════════════
RESTRICTIONS
═══════════════════════════════════════════════════════════════

DO:
- Work only in your worktree
- Follow existing code patterns
- Write tests for new code
- Commit frequently

DO NOT:
- Modify files outside worktree
- Merge or rebase branches
- Push to remote
- Modify plan.md or review-notes.md
- Add unrelated changes

═══════════════════════════════════════════════════════════════

BEGIN WORK NOW.
```

## Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `{TASK_NAME}` | Task identifier | `fix-logging` |
| `{TICKET}` | Ticket/issue ID | `K-123` |
| `{WORKSPACE}` | Absolute workspace path | `/Users/dev/myworkspace` |
| `{MAIN_BRANCH}` | Main feature branch | `feature/K-123_user_auth` |
| `{N}` | Iteration number | `2` |
| `{PROJECT_NAME}` | Project name | `Payment Service` |
| `{FEATURE_DESCRIPTION}` | Feature being built | `User Authentication` |

## Usage in Spawn

The operator fills in this template when spawning a sub-agent:

```python
template = """
You are a sub-agent working on task '{task_name}'.
...
"""

prompt = template.format(
    task_name=task_name,
    ticket=ticket,
    workspace=str(workspace_path),
    main_branch=main_branch,
    # ... other variables
)

# Then spawn with this prompt
```
