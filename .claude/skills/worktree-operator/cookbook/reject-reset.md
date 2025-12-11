# Cookbook: Reject - Reset

## Purpose
Discard current work and start fresh with a clean worktree.

## When to Use
- User says "operator reset {name}"
- After review finds fundamental issues
- Approach is wrong, not just implementation
- Multiple iterations haven't resolved issues
- Scope creep has made changes unmanageable

## When NOT to Use
- Issues are fixable with iteration
- Only minor problems exist
- Sub-agent just needs more guidance

## Prerequisites
- Task reviewed
- Decision made that reset is better than iterate
- Understanding of why current approach failed

## Steps

### 1. Document Reset Reason

Before resetting, document why:

```markdown
## Reset Reason

### What went wrong:
{Description of fundamental issue}

### Why reset instead of iterate:
{Justification for starting over}

### Lessons for next attempt:
{What to do differently}
```

### 2. Preserve Current State (Optional)

If there's anything salvageable:

```bash
TASK="fix-logging"
cd task-${TASK}/worktree

# Save current diff for reference
git diff HEAD > ../failed-attempt-{N}.diff

# Or create a backup branch
git branch backup/failed-attempt-{N}
```

### 3. Reset Worktree

```bash
TASK="fix-logging"
MAIN_BRANCH="feature/K-123_user_auth"

cd task-${TASK}/worktree

# Fetch latest main branch
git fetch origin

# Hard reset to main branch
git reset --hard ${MAIN_BRANCH}

# Clean untracked files
git clean -fd

# Verify clean state
git status
```

### 4. Clear/Update Task Files

```bash
TASK="fix-logging"

# Clear results.md
cat > task-${TASK}/results.md << 'EOF'
# Results: {task_name}

_Previous attempt was reset. Results will be written by sub-agent after new implementation._

## Previous Attempt Summary
{Brief note about what was tried and why it was reset}
EOF

# Update feedback.md with reset context
cat > task-${TASK}/feedback.md << 'EOF'
# Feedback: {task_name} (After Reset)

## Reset Date: {date}
## Reason: {brief reason}

---

## What Went Wrong Previously

{Description of issues with previous attempt}

---

## Approach for New Attempt

{Guidance for the new approach}

---

## Lessons Learned

1. {Lesson 1}
2. {Lesson 2}

---

## Spec Clarifications

{Any clarifications to the original spec based on learnings}
EOF
```

### 5. Optionally Revise spec.md

If the spec was unclear or contributed to the failure:

```bash
# Review and update spec.md
# Add clarifications, remove ambiguity, adjust scope
```

### 6. Update plan.md

```markdown
### X. {task_name}
- Status: PENDING (reset from ITERATING)
- Branch: feature/{ticket}/{task_name}
- Resets: {count}
- Last reset: {date}
- Reset reason: {brief reason}
```

### 7. Log in review-notes.md

```markdown
### {DATE} {TIME} - {task_name} RESET

**Previous state:** Iteration {N}

**Decision:** RESET

**Reason:**
{Detailed explanation of why reset was chosen}

**What was tried:**
{Summary of previous approach}

**Why it failed:**
{Root cause analysis}

**New approach:**
{What will be different in the next attempt}

**Spec changes:**
{Any changes made to spec.md}
```

### 8. Re-spawn Sub-Agent

```
You are a sub-agent starting fresh on task '{task_name}'.

IMPORTANT: A previous attempt on this task was reset.
Read feedback.md to understand what went wrong and the new approach.

WORKSPACE CONTEXT:
- Task folder: {workspace}/task-{task_name}
- Your worktree: {workspace}/task-{task_name}/worktree
- Your branch: feature/{ticket}/{task_name}

The worktree has been reset to a clean state matching {main_branch}.

INSTRUCTIONS:
1. Read feedback.md FIRST - it explains what went wrong before
2. Read spec.md for the task requirements
3. Follow the "Approach for New Attempt" guidance
4. Implement the task with the lessons learned in mind
5. Run tests frequently
6. Commit with clear messages
7. Write comprehensive results.md
8. Exit when complete

AVOID THE PREVIOUS MISTAKES:
{List key mistakes to avoid}

START FRESH WITH A BETTER APPROACH.
```

### 9. Report Reset

```
✓ Task '{task_name}' has been reset

Actions completed:
  ✓ Worktree reset to {main_branch}
  ✓ Untracked files cleaned
  ✓ feedback.md updated with reset context
  ✓ results.md cleared
  ✓ plan.md updated
  ✓ review-notes.md logged

Previous attempt:
  - Iterations: {N}
  - Reason for reset: {brief reason}

Next steps:
  The spec has been {updated/kept as-is}.
  Sub-agent will start fresh with guidance from feedback.md.

Re-spawning sub-agent...

Run "operator review {task_name}" when complete.
```

## Using Python Tools

```python
from tools.task import reset_task

result = reset_task(
    task_name="fix-logging",
    main_branch="feature/K-123_user_auth",
    workspace_path="."
)

if result["success"]:
    print(f"✓ {result['message']}")
else:
    print(f"✗ Error: {result['error']}")
```

## Reset vs Iterate Decision Guide

| Situation | Decision | Reason |
|-----------|----------|--------|
| Missing a requirement | Iterate | Fixable with guidance |
| Wrong approach to problem | Reset | Need different solution |
| Code quality issues | Iterate | Refactorable |
| Wrong architecture | Reset | Fundamental rethink needed |
| 3+ iterations, same issues | Reset | Not learning from feedback |
| Scope creep | Reset | Need clean boundaries |
| Test failures | Iterate | Usually fixable |
| Completely wrong understanding | Reset | Need better spec |

## Common Reset Reasons

### Wrong Approach
```markdown
## Reason
Sub-agent implemented feature X using approach A, but the codebase
uses approach B consistently. Rather than refactor, better to
re-implement following established patterns.
```

### Scope Creep
```markdown
## Reason
Task was to "fix logging" but sub-agent refactored the entire
service architecture. Resetting to focus on the original scope.
```

### Spec Misunderstanding
```markdown
## Reason
Sub-agent interpreted "structured logging" as adding log levels,
but spec meant JSON-formatted logs with specific fields.
Clarifying spec and resetting for clean implementation.
```

### Multiple Failed Iterations
```markdown
## Reason
After 3 iterations, same test failures persist. Sub-agent seems
to be making changes without understanding the root cause.
Resetting with more detailed guidance.
```

## Error Handling

### Uncommitted changes
```
Worktree has uncommitted changes.

Options:
1. Force reset (discard changes): git reset --hard && git clean -fd
2. Commit first, then reset
3. Stash changes for review: git stash

Proceed with force reset? [y/N]:
```

### Backup branch exists
```
Backup branch 'backup/failed-attempt-{N}' already exists.

Options:
1. Delete and recreate
2. Use different backup name
3. Skip backup

Choose option [1/2/3]:
```

## Checklist

- [ ] Reset reason documented
- [ ] Previous state preserved (if valuable)
- [ ] Worktree hard reset
- [ ] Untracked files cleaned
- [ ] feedback.md updated with reset context
- [ ] results.md cleared/updated
- [ ] spec.md revised (if needed)
- [ ] plan.md updated
- [ ] review-notes.md logged with analysis
- [ ] Sub-agent re-spawned with fresh context
