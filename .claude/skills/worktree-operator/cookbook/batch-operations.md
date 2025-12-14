# Cookbook: Batch Operations

## Purpose
Create and spawn multiple tasks at once, improving operator efficiency for larger plans.

## When to Use
- User says "operator create-all" - Create all pending task folders
- User says "operator spawn-unblocked" - Spawn all tasks with met dependencies
- User says "operator spawn-parallel N" - Spawn up to N tasks concurrently
- When working with plans that have many tasks (5+)
- When you want to parallelize work across multiple sub-agents

## Prerequisites
- Workspace initialized with `operator init`
- plan.md exists with task definitions
- For spawn commands: task folders with worktrees must exist

## Commands

### Create All Tasks

Creates task folders and git worktrees for all PENDING tasks in plan.md.
Tasks that already have folders are skipped.

```bash
# CLI usage
python tools/batch_operations.py create-all --workspace . --ticket WH --main-branch main

# With JSON output
python tools/batch_operations.py create-all --workspace . --json
```

```python
# Python usage
from tools.batch_operations import create_all_tasks

result = create_all_tasks(
    workspace_path=".",
    ticket="WH",
    main_branch="main"
)

if result["success"]:
    print(f"Created: {result['created']}")
    print(f"Skipped: {result['skipped']}")
else:
    print(f"Errors: {result['errors']}")
```

### Spawn Unblocked Tasks

Spawns sub-agents for all tasks that:
1. Have PENDING status
2. Have all dependencies completed (or no dependencies)
3. Have existing task folders with worktrees

```bash
# CLI usage
python tools/batch_operations.py spawn-unblocked --workspace . --model opus

# Skip dependency checking
python tools/batch_operations.py spawn-unblocked --workspace . --force

# With JSON output
python tools/batch_operations.py spawn-unblocked --workspace . --json
```

```python
# Python usage
from tools.batch_operations import spawn_unblocked_tasks

result = spawn_unblocked_tasks(
    workspace_path=".",
    ticket="WH",
    model="opus",
    force=False
)

if result["success"]:
    print(f"Spawned: {result['spawned']}")
    print(f"Skipped (no folder): {result['skipped']}")
else:
    for failure in result["failed"]:
        print(f"Failed: {failure['task']} - {failure['error']}")
```

### Spawn Parallel

Spawns up to N tasks concurrently, respecting dependency order.
Useful for controlling resource usage on limited systems.

```bash
# Spawn up to 3 tasks (default)
python tools/batch_operations.py spawn-parallel 3 --workspace .

# Spawn up to 5 tasks with specific model
python tools/batch_operations.py spawn-parallel 5 --workspace . --model sonnet

# Skip dependency checking
python tools/batch_operations.py spawn-parallel 3 --workspace . --force
```

```python
# Python usage
from tools.batch_operations import spawn_parallel

result = spawn_parallel(
    max_parallel=3,
    workspace_path=".",
    ticket="WH",
    model="opus",
    force=False
)

print(f"Spawned: {result['spawned']}")
print(f"Remaining (hit limit): {result['remaining']}")
print(f"Skipped (no folder): {result['skipped']}")
```

## Workflow Example

### Complete Batch Workflow

1. Initialize workspace and create plan:
```
operator init https://github.com/user/repo.git feature/big-feature
operator plan
```

2. Create all task folders at once:
```python
from tools.batch_operations import create_all_tasks

result = create_all_tasks(workspace_path=".", ticket="K-123", main_branch="feature/big-feature")
print(f"Created {len(result['created'])} task folders")
```

3. Spawn tasks in parallel (up to 3):
```python
from tools.batch_operations import spawn_parallel

result = spawn_parallel(max_parallel=3, workspace_path=".", ticket="K-123", model="opus")
print(f"Spawned {len(result['spawned'])} sub-agents")
```

4. As tasks complete, spawn remaining:
```python
# After reviewing and accepting completed tasks, spawn more
result = spawn_parallel(max_parallel=3, workspace_path=".", ticket="K-123", model="opus")
```

### Dependency-Aware Spawning

Given a plan like:
```markdown
### 1. setup-database
- Status: PENDING
- Dependencies: None

### 2. create-models
- Status: PENDING
- Dependencies: setup-database

### 3. implement-api
- Status: PENDING
- Dependencies: create-models

### 4. write-tests
- Status: PENDING
- Dependencies: implement-api
```

Initial spawn will only launch `setup-database` (the only unblocked task).

After `setup-database` is marked COMPLETED, `create-models` becomes unblocked.

## Result Format

All batch operations return a consistent result format:

```json
{
  "success": true,
  "created": ["task1", "task2"],
  "skipped": ["task3"],
  "spawned": ["task1", "task2"],
  "remaining": ["task4", "task5"],
  "failed": [
    {"task": "task6", "error": "reason"}
  ],
  "errors": ["task6: reason"],
  "message": "Batch complete: 2 created, 1 skipped",
  "summary": {
    "created_count": 2,
    "skipped_count": 1,
    "spawned_count": 2,
    "failed_count": 1
  }
}
```

## Error Handling

### Plan Parse Errors
```
Error: Failed to parse plan.md
Hint: Ensure plan.md exists and is properly formatted
```
Solution: Check that plan.md follows the expected format with ### task headers and - Status: lines.

### No Pending Tasks
```
Message: No pending tasks found in plan.md
```
This is not an error - all tasks may already be completed or in progress.

### Tasks Without Folders
Tasks in plan.md without corresponding task folders are skipped with a message.
Create them first with `create-all` or `operator create task {name}`.

### Spawn Failures
Individual spawn failures don't stop the batch. The operation continues and reports failures at the end.

## Best Practices

1. **Create before spawn**: Always run `create-all` before `spawn-unblocked` or `spawn-parallel`

2. **Start conservative**: Begin with `spawn-parallel 2` to avoid overwhelming your system

3. **Check dependencies**: Use `operator unblocked` to see what tasks are ready

4. **Monitor progress**: Use `operator health` to check on running sub-agents

5. **Accept incrementally**: Accept completed tasks to unblock dependent ones

## Checklist

- [ ] plan.md exists with task definitions
- [ ] Tasks have proper status (PENDING for new tasks)
- [ ] Dependencies are correctly specified
- [ ] Task folders created (via `create-all` or `create task`)
- [ ] Worktrees exist in task folders
- [ ] spec.md files are complete in each task folder
