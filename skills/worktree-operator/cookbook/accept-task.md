# Cookbook: Accept Task

## Purpose
Accept completed work: rebase, merge into main branch, and cleanup.

## When to Use
- User says "operator accept {name}"
- After positive review decision
- Work meets all acceptance criteria

## Prerequisites
- Task reviewed and approved
- Tests passing
- Code quality acceptable

## Steps

### 1. Final Verification

```bash
TASK="fix-logging"
TICKET="K-123"
MAIN_BRANCH="feature/K-123_user_auth"
SUB_BRANCH="feature/${TICKET}/${TASK}"
WORKTREE="task-${TASK}/worktree"

# Verify worktree exists
ls -la ${WORKTREE}

# Check for uncommitted changes
cd ${WORKTREE}
git status

# If uncommitted changes exist, warn user
if [ -n "$(git status --porcelain)" ]; then
    echo "WARNING: Uncommitted changes in worktree"
    echo "Sub-agent should commit all changes before acceptance"
fi
```

### 2. Rebase Sub-Branch

```bash
cd ${WORKTREE}

# Fetch latest
git fetch origin

# Rebase onto main branch
git rebase ${MAIN_BRANCH}

# If conflicts occur, resolve them
# git add <resolved files>
# git rebase --continue

# Verify tests pass after rebase
npm test  # or appropriate test command
```

### 3. Merge into Main Branch

```bash
cd repo

# Switch to main branch
git switch ${MAIN_BRANCH}

# Merge with --no-ff to preserve merge commit
git merge --no-ff ${SUB_BRANCH} -m "Merge ${TASK}: {description from spec}"

# Verify tests pass after merge
npm test
```

### 4. Push Main Branch

```bash
cd repo
git push origin ${MAIN_BRANCH}
```

### 5. Cleanup Worktree and Task Folder

```bash
cd repo

# Remove worktree
git worktree remove ../task-${TASK}/worktree

# Or force if needed
git worktree remove ../task-${TASK}/worktree --force

# Remove task folder (including spec.md, feedback.md, results.md)
# This is done automatically by accept_task() after worktree removal
rm -rf ../task-${TASK}
```

**Note:** The Python `accept_task()` function automatically removes the entire task folder after successfully removing the worktree. This cleanup happens after the point of no return (after push), so failures are non-fatal and only logged as warnings.

### 6. Delete Sub-Branch

```bash
cd repo

# Delete local branch
git branch -d ${SUB_BRANCH}

# Delete remote branch (if pushed)
git push origin --delete ${SUB_BRANCH}
```

### 7. Sync Remaining Worktrees

Other active worktrees need to be rebased onto the updated main branch:

```bash
# For each active task worktree
for task_dir in ../task-*/worktree; do
    if [ -d "$task_dir" ]; then
        echo "Syncing $task_dir..."
        cd "$task_dir"
        git fetch origin
        git rebase ${MAIN_BRANCH}
        cd -
    fi
done
```

### 8. Update plan.md

Update the task status:

```markdown
### X. {task_name}
- Status: COMPLETED
- Branch: feature/{ticket}/{task_name}
- Merged: {date}
- Summary: {brief summary of what was accomplished}
```

### 9. Log Acceptance

Add to review-notes.md:

```markdown
### {DATE} {TIME} - {task_name} ACCEPTED

**Action:** Merged into {main_branch}

**Merge commit:** {hash}

**Summary:**
{Brief description of what was merged}

**Follow-up:**
- Synced {count} remaining worktrees
- Deleted branch feature/{ticket}/{task_name}
```

### 10. Report Completion

```
✓ Task '{task_name}' accepted and merged

Actions completed:
  ✓ Rebased onto {main_branch}
  ✓ Merged with --no-ff
  ✓ Pushed to origin
  ✓ Removed worktree
  ✓ Removed task folder
  ✓ Deleted local branch
  ✓ Deleted remote branch
  ✓ Synced {count} remaining worktrees
  ✓ Updated plan.md
  ✓ Logged in review-notes.md

Next tasks in plan:
  - {next_pending_task}
  - {another_pending_task}
```

## Using Python Tools

```python
from tools.task import accept_task, list_tasks
from tools.git_ops import sync_all_worktrees

# Accept the task
result = accept_task(
    ticket="K-123",
    task_name="fix-logging",
    main_branch="feature/K-123_user_auth",
    workspace_path=".",
    push=True,
    delete_remote_branch=True
)

if result["success"]:
    print(f"✓ {result['message']}")
    for step in result["steps"]:
        print(f"  {step}")

    # Sync remaining worktrees
    sync_result = sync_all_worktrees(".", "feature/K-123_user_auth")
    print(f"\nSynced {len(sync_result['synced'])} worktrees")
else:
    print(f"✗ Acceptance failed")
    for error in result["errors"]:
        print(f"  Error: {error}")
```

## Error Handling

> See SKILL.md "Error Handling" section for complete error reference and recovery procedures.

| Error | Quick Fix |
|-------|-----------|
| Rebase conflicts | `operator resolve {name}` or manually resolve, `git add`, `git rebase --continue` |
| Tests fail after rebase | Fix in worktree and commit, or reset task |
| Push rejected | `git pull --rebase origin {main}`, resolve conflicts, retry |
| Worktree removal fails | `git worktree remove {path} --force && git worktree prune` |

## Merge Commit Message Format

Use descriptive merge commit messages:

```
Merge {task_name}: {brief description}

{Longer description if needed}

Task: {ticket}
Branch: feature/{ticket}/{task_name}
```

Example:
```
Merge fix-logging: Add structured JSON logging to payment service

Replaced console.log calls with winston-based structured logging.
All logs now include request ID, timestamp, and service context.

Task: K-123
Branch: feature/K-123/fix-logging
```

## Post-Accept Checklist

- [ ] Sub-branch rebased cleanly
- [ ] Tests pass after rebase
- [ ] Merged with --no-ff
- [ ] Tests pass after merge
- [ ] Main branch pushed
- [ ] Worktree removed
- [ ] Task folder removed (spec.md, feedback.md, results.md)
- [ ] Local branch deleted
- [ ] Remote branch deleted
- [ ] Other worktrees synced
- [ ] plan.md updated (COMPLETED)
- [ ] review-notes.md logged
