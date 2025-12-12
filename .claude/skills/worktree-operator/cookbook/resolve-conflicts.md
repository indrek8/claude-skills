# Cookbook: Resolve Conflicts

## Purpose
Detect, display, and resolve conflicts that occur during rebase or merge operations.

## When to Use
- User says "operator resolve {name}"
- User says "operator conflicts {name}"
- After a rebase/sync fails with conflicts
- When `accept_task` fails due to conflicts

## Prerequisites
- A task with an active worktree
- A rebase or merge operation in progress with conflicts

## Understanding Conflicts

### When Conflicts Occur
1. **During sync/rebase**: The main branch has changes that conflict with sub-agent work
2. **During accept**: Rebasing onto main before merge reveals conflicts
3. **During merge**: Direct merge (less common) has conflicting changes

### Conflict Markers
```
<<<<<<< HEAD (your changes)
Your code that was changed
=======
Incoming code from the other branch
>>>>>>> main (incoming)
```

## Steps

### 1. Detect Conflicts

```python
from tools.conflict_resolver import detect_conflicts, resolve_conflicts_interactive

TASK = "fix-logging"
WORKTREE = f"task-{TASK}/worktree"

# Get detailed conflict info
conflicts = detect_conflicts(WORKTREE)

if conflicts["has_conflicts"]:
    print(f"Found {len(conflicts['files'])} conflicted files")
    for f in conflicts["files"]:
        print(f"  - {f['path']} ({f['conflict_count']} conflicts)")
```

Or use the interactive function:

```python
result = resolve_conflicts_interactive(WORKTREE, TASK)
print(result["report"])
```

### 2. Show Conflict Report to User

Present the conflict report:

```
Conflicts detected in task 'fix-logging':
  Operation: rebase

  1. src/services/payment.ts
     <<<<<<< HEAD (your changes)
     logger.info({ event: 'payment', amount });
     =======
     console.log('Payment:', amount);
     >>>>>>> main (main branch)

  2. src/utils/format.ts
     (3 conflicts in this file)

Resolution options:
  1. Keep ours   - Use your changes (HEAD) for all files
  2. Keep theirs - Use incoming changes for all files
  3. Manual      - Edit files manually to resolve
  4. Abort       - Abort operation and return to previous state
```

### 3. Resolution Options

#### Option 1: Keep Ours (Sub-agent Changes)
Use when the sub-agent's changes are correct and should override main branch.

```python
from tools.conflict_resolver import resolve_all

result = resolve_all(WORKTREE, "ours")
if result["success"]:
    print(f"✓ Resolved {len(result['resolved'])} files using your changes")
else:
    print(f"✗ Failed: {result['message']}")
```

#### Option 2: Keep Theirs (Main Branch Changes)
Use when main branch changes should be kept, discarding sub-agent work on those files.

```python
result = resolve_all(WORKTREE, "theirs")
if result["success"]:
    print(f"✓ Resolved {len(result['resolved'])} files using main branch changes")
```

#### Option 3: Resolve Individual Files
Use when different files need different strategies.

```python
from tools.conflict_resolver import resolve_file

# Keep sub-agent changes for this file
resolve_file(WORKTREE, "src/services/payment.ts", "ours")

# Keep main branch changes for this file
resolve_file(WORKTREE, "src/utils/format.ts", "theirs")

# Leave for manual editing
resolve_file(WORKTREE, "src/config/app.ts", "manual")
```

#### Option 4: Manual Resolution
For complex conflicts that need careful merging:

```bash
cd task-${TASK}/worktree

# Edit the conflicting files manually
# Remove conflict markers and keep the correct code

# Stage resolved files
git add src/services/payment.ts
git add src/utils/format.ts

# Continue the rebase
git rebase --continue
```

Using Python:

```python
from tools.conflict_resolver import continue_rebase

# After manually editing and staging files
result = continue_rebase(WORKTREE)
if result["more_conflicts"]:
    print("More conflicts need resolution in subsequent commits")
elif result["success"]:
    print("✓ Rebase completed successfully")
```

#### Option 5: Abort Operation
When conflicts are too complex or approach was wrong:

```python
from tools.conflict_resolver import abort_operation

result = abort_operation(WORKTREE)
if result["success"]:
    print(f"✓ {result['operation'].title()} aborted")
```

### 4. Continue After Resolution

After resolving conflicts:

```python
from tools.conflict_resolver import continue_rebase, continue_merge, is_rebase_in_progress

if is_rebase_in_progress(WORKTREE):
    result = continue_rebase(WORKTREE)
else:
    result = continue_merge(WORKTREE)

if result.get("more_conflicts"):
    print("More commits have conflicts - resolve and continue again")
elif result["success"]:
    print("✓ Operation completed")
```

### 5. Verify Resolution

```bash
cd task-${TASK}/worktree

# Check no conflicts remain
git status

# Run tests
npm test  # or appropriate test command
```

## CLI Usage

The conflict_resolver.py can be run directly:

```bash
cd .claude/skills/worktree-operator/tools

# Detect conflicts
python conflict_resolver.py detect ../../../task-fix-logging/worktree --task fix-logging

# Resolve all with one strategy
python conflict_resolver.py resolve-all ../../../task-fix-logging/worktree ours

# Resolve single file
python conflict_resolver.py resolve-file ../../../task-fix-logging/worktree src/file.ts theirs

# Abort operation
python conflict_resolver.py abort ../../../task-fix-logging/worktree

# Continue after manual resolution
python conflict_resolver.py continue ../../../task-fix-logging/worktree
```

## Common Patterns

### Pattern 1: Simple Override
When sub-agent's work is correct and main branch changes don't matter for these files:

```python
result = resolve_all(worktree_path, "ours")
if result["success"]:
    continue_rebase(worktree_path)
```

### Pattern 2: Accept Main Branch Updates
When main branch has newer/better implementations:

```python
result = resolve_all(worktree_path, "theirs")
if result["success"]:
    # Re-run sub-agent to redo work on top of new main
    continue_rebase(worktree_path)
```

### Pattern 3: Mixed Resolution
Different strategies for different files:

```python
# Core logic - keep sub-agent work
resolve_file(worktree_path, "src/feature.ts", "ours")

# Config updates - keep main branch
resolve_file(worktree_path, "package.json", "theirs")

# Complex merge - do manually
resolve_file(worktree_path, "src/shared.ts", "manual")
print("Please edit src/shared.ts manually, then run: git add src/shared.ts")
```

### Pattern 4: Abort and Reset
When conflicts indicate fundamentally incompatible changes:

```python
abort_operation(worktree_path)
# Then use: operator reset {task}
```

## Decision Guide

Use this guide to choose a resolution strategy:

| Scenario | Strategy |
|----------|----------|
| Sub-agent rewrote a feature, main has minor changes | ours |
| Main branch has critical fixes sub-agent should use | theirs |
| Both changes are important, need manual merge | manual |
| Changes are fundamentally incompatible | abort + reset |
| Config/dependency updates from main are needed | theirs for those files |
| Sub-agent added new code, main modified existing | ours (usually) |

## Error Handling

### "No rebase in progress"
The rebase may have already completed or been aborted.
```bash
git status  # Check current state
```

### "Cannot continue: files still have conflicts"
Not all files were resolved. Check remaining conflicts:
```python
conflicts = detect_conflicts(worktree_path)
for f in conflicts["files"]:
    print(f"  Still conflicted: {f['path']}")
```

### "More conflicts in subsequent commits"
Rebase processes commits one by one. After resolving one commit's conflicts,
there may be more in later commits. Continue the cycle:
```python
while True:
    result = continue_rebase(worktree_path)
    if not result.get("more_conflicts"):
        break
    # Resolve new conflicts
    resolve_all(worktree_path, "ours")
```

## Best Practices

1. **Preview before resolving**: Always show the conflict report before choosing a strategy
2. **Test after resolution**: Run tests after completing resolution
3. **Document decisions**: Note in review-notes.md why a particular strategy was chosen
4. **Prefer manual for complex cases**: When in doubt, manual resolution is safest
5. **Consider re-implementing**: If conflicts are extensive, resetting and re-implementing may be faster

## Integration with Other Commands

### With accept_task
If accept fails due to conflicts:
```python
result = accept_task(...)
if not result["success"] and result.get("conflicts"):
    print(result["conflict_report"])
    # Resolve, then retry accept
```

### With sync_all_worktrees
If sync fails for a task:
```python
result = sync_all_worktrees(workspace, main_branch)
for failed in result["failed"]:
    if failed.get("conflicts"):
        print(f"Resolve conflicts in: task-{failed['task']}/worktree")
```

## Report Template

After resolving conflicts, log in review-notes.md:

```markdown
### {DATE} {TIME} - {task_name} CONFLICT RESOLUTION

**Conflict during:** {rebase|merge|sync}

**Files affected:**
- {file1}: resolved using {strategy}
- {file2}: resolved using {strategy}

**Resolution approach:** {Brief explanation of why this approach was chosen}

**Tests after resolution:** {PASS|FAIL}
```
