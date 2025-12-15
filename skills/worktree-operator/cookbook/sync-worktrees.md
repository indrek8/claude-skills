# Cookbook: Sync Worktrees

## Purpose
Rebase all active worktrees onto the latest main branch after changes.

## When to Use
- User says "operator sync" or "operator sync all"
- After accepting a task (other worktrees need updating)
- After pulling changes to main branch
- Before spawning sub-agents to ensure they have latest code

## Prerequisites
- At least one task with active worktree
- Main branch known

## Steps

### 1. Get Current State

```bash
MAIN_BRANCH="feature/K-123_user_auth"

# List all worktrees
cd repo
git worktree list

# Find active task worktrees
ls -la ../task-*/worktree 2>/dev/null
```

### 2. Update Main Branch (Optional)

If main branch might have remote changes:

```bash
cd repo
git fetch origin
git switch ${MAIN_BRANCH}
git pull --ff-only origin ${MAIN_BRANCH}
```

### 3. Sync Each Worktree

```bash
MAIN_BRANCH="feature/K-123_user_auth"

# For each task with a worktree
for task_dir in ../task-*/; do
    worktree="${task_dir}worktree"

    if [ -d "$worktree" ]; then
        task_name=$(basename "$task_dir" | sed 's/^task-//')
        echo "Syncing: ${task_name}..."

        cd "$worktree"

        # Fetch latest
        git fetch origin

        # Attempt rebase
        if git rebase ${MAIN_BRANCH}; then
            echo "  ✓ ${task_name} synced successfully"
        else
            echo "  ✗ ${task_name} has conflicts"
            # Abort the failed rebase
            git rebase --abort
        fi

        cd - > /dev/null
    fi
done
```

### 4. Handle Conflicts

If any worktree has conflicts:

```
Sync completed with conflicts in:
  - task-{name1}: {conflict details}
  - task-{name2}: {conflict details}

For each conflicted task:
1. cd task-{name}/worktree
2. git rebase {main_branch}
3. Resolve conflicts in affected files
4. git add <resolved files>
5. git rebase --continue
6. Run tests to verify

Or abort and handle later:
  git rebase --abort
```

### 5. Run Tests (Optional)

After syncing, optionally verify tests pass:

```bash
for task_dir in ../task-*/; do
    worktree="${task_dir}worktree"

    if [ -d "$worktree" ]; then
        task_name=$(basename "$task_dir" | sed 's/^task-//')
        echo "Testing: ${task_name}..."

        cd "$worktree"
        npm test || echo "  ⚠ Tests failed for ${task_name}"
        cd - > /dev/null
    fi
done
```

### 6. Report Status

```
╔══════════════════════════════════════════════════════════════╗
║                     SYNC COMPLETE                             ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Main branch: {main_branch}                                   ║
║  Worktrees synced: {count}                                    ║
║                                                               ║
║  RESULTS:                                                     ║
║  ───────────────────────────────────────────────────────────  ║
║  ✓ task-{name1} - synced successfully                         ║
║  ✓ task-{name2} - synced successfully                         ║
║  ✗ task-{name3} - conflicts (needs manual resolution)         ║
║  - task-{name4} - skipped (no worktree)                       ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝

{If conflicts}
Action required for conflicted worktrees.
Run "operator status" to see current state.
```

## Using Python Tools

```python
from tools.git_ops import sync_all_worktrees

result = sync_all_worktrees(
    workspace_path=".",
    main_branch="feature/K-123_user_auth"
)

print(f"\n{'='*60}")
print("SYNC RESULTS")
print(f"{'='*60}")

print(f"\nSynced successfully: {len(result['synced'])}")
for item in result['synced']:
    print(f"  ✓ {item['task']}")

print(f"\nFailed (conflicts): {len(result['failed'])}")
for item in result['failed']:
    print(f"  ✗ {item['task']}: {item['error']}")

print(f"\nSkipped: {len(result['skipped'])}")
for item in result['skipped']:
    print(f"  - {item['task']}: {item['reason']}")

if not result['success']:
    print("\n⚠ Some worktrees need manual conflict resolution")
```

## Resolving Conflicts

When a rebase has conflicts:

### 1. Enter the conflicted worktree
```bash
cd task-{name}/worktree
```

### 2. See what's conflicted
```bash
git status
# Shows files with conflicts
```

### 3. For each conflicted file
```bash
# Open file, look for conflict markers:
# <<<<<<< HEAD
# ... your changes ...
# =======
# ... main branch changes ...
# >>>>>>> main_branch

# Edit to resolve, then:
git add <file>
```

### 4. Continue rebase
```bash
git rebase --continue
```

### 5. If too messy, abort and try merge instead
```bash
git rebase --abort
git merge ${MAIN_BRANCH}
# Resolve conflicts
git commit
```

### 6. Verify
```bash
npm test  # Run tests
git status  # Should be clean
```

## Sync Strategies

### Aggressive (Abort on Conflict)
- Quickly identifies problems
- Leaves conflicts for manual resolution
- Good for: routine syncs, many worktrees

### Careful (Stop on First Conflict)
- Handles one conflict at a time
- More operator attention
- Good for: complex codebases, related tasks

### Test-Verified
- Runs tests after each sync
- Catches integration issues early
- Good for: critical features, complex dependencies

## Common Issues

### All worktrees conflict
```
All worktrees have conflicts after sync.

This usually means the main branch had significant changes
that affect all tasks.

Options:
1. Resolve conflicts one by one
2. Consider if tasks need to be re-planned
3. Check if main branch changes should have been coordinated
```

### Worktree diverged significantly
```
Worktree 'task-{name}' is {N} commits behind and has {M} local commits.

This may cause complex conflicts.

Options:
1. Try rebase anyway
2. Merge instead of rebase
3. Reset task and re-implement
```

### Test failures after sync
```
Task '{name}' synced but tests now fail.

The main branch introduced changes that conflict with this task's work.

Options:
1. Fix tests in the worktree
2. This is expected - task may need iteration after review
3. Reset if changes are too significant
```

## When to Sync

| Event | Should Sync? | Reason |
|-------|--------------|--------|
| After accepting a task | Yes | Other tasks need the changes |
| Before spawning sub-agent | Recommended | Ensures latest code |
| After pulling main branch | Yes | Keep all worktrees current |
| Routinely (daily) | Optional | Prevents drift |
| Before review | Optional | Ensures comparison is fair |

## Checklist

- [ ] Main branch identified
- [ ] Main branch updated (if needed)
- [ ] Each worktree rebased
- [ ] Conflicts identified
- [ ] Conflict resolution guidance provided
- [ ] Tests run (optional)
- [ ] Status reported
