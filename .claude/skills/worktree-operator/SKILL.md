# Worktree Operator Skill

A skill for orchestrating multi-agent development workflows using Git worktrees.

## Purpose

The operator manages parallel AI sub-agent development by:
- Initializing workspaces with cloned repositories
- Planning and decomposing work into tasks
- Creating isolated worktrees for each task
- Spawning sub-agents to implement tasks
- Reviewing sub-agent output
- Accepting, iterating, or resetting work
- Merging completed work back to the main branch

## Triggers

This skill activates when the user's request matches these patterns:

| Pattern | Cookbook | Description |
|---------|----------|-------------|
| "operator init workspace" | init-workspace.md | Clone repo, setup workspace |
| "operator init" | init-workspace.md | Same as above |
| "operator plan" | create-plan.md | Analyze codebase, create plan.md |
| "operator analyze" | create-plan.md | Same as above |
| "operator create task {name}" | create-task.md | Create task folder + worktree |
| "operator spawn {name}" | spawn-subagent.md | Launch sub-agent on task (inline, consumes tokens) |
| "operator run subagent {name}" | spawn-subagent.md | Same as above |
| "operator fork {name}" | spawn-subagent.md | Launch sub-agent in forked terminal (no token cost) |
| "operator spawn fork {name}" | spawn-subagent.md | Same as above |
| "operator review {name}" | review-task.md | Review sub-agent output |
| "operator accept {name}" | accept-task.md | Rebase, merge, cleanup |
| "operator iterate {name}" | reject-iterate.md | Write feedback, re-spawn |
| "operator feedback {name}" | reject-iterate.md | Same as above |
| "operator reset {name}" | reject-reset.md | Reset worktree, re-spawn |
| "operator sync" | sync-worktrees.md | Rebase all active worktrees |
| "operator sync all" | sync-worktrees.md | Same as above |
| "operator resolve {name}" | resolve-conflicts.md | Show conflicts and resolution options |
| "operator conflicts {name}" | resolve-conflicts.md | Same as above |
| "operator status" | (inline) | Show plan.md + worktree status |
| "operator status {name}" | (inline) | Check sub-agent health for specific task |
| "operator health {name}" | (inline) | Same as above |
| "operator health" | (inline) | Check health of all running sub-agents |
| "operator unblocked" | (inline) | Show tasks ready to spawn (dependencies met) |

## Variables

```yaml
# Workspace configuration
WORKSPACE_PATH: "."                    # Current directory by default
REPO_FOLDER: "repo"                    # Cloned repo folder name

# Branch patterns
MAIN_BRANCH: "feature/K-123_feature"   # Set during init
SUB_BRANCH_PATTERN: "feature/{ticket}/{task}"

# Sub-agent configuration
DEFAULT_MODEL: "opus"
FAST_MODEL: "haiku"
HEADLESS_FLAG: "--dangerously-skip-permissions"
```

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     OPERATOR WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INIT ──► PLAN ──► CREATE TASK ──► SPAWN ──► REVIEW             │
│                                                │                 │
│                        ┌───────────────────────┤                 │
│                        │           │           │                 │
│                        ▼           ▼           ▼                 │
│                    ITERATE      RESET       ACCEPT               │
│                        │           │           │                 │
│                        └─────┬─────┘           │                 │
│                              │                 │                 │
│                              ▼                 ▼                 │
│                         RE-SPAWN            SYNC ──► NEXT TASK   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Tools

Python tools available in `tools/`:

### fork_terminal.py
- `fork_terminal(command, working_dir)` - Open new terminal and run command
- `spawn_forked_subagent(task_name, ticket, workspace_path, model, iteration)` - Spawn sub-agent in forked terminal

### health_check.py
- `mark_started(task_name, workspace_path)` - Mark sub-agent as starting
- `mark_running(task_name, progress, workspace_path)` - Update heartbeat with progress
- `mark_completed(task_name, workspace_path)` - Mark sub-agent as completed
- `mark_failed(task_name, error, workspace_path)` - Mark sub-agent as failed
- `check_health(task_name, workspace_path, timeout)` - Check if sub-agent is healthy
- `read_status(task_name, workspace_path)` - Get full status of sub-agent
- `list_all_status(workspace_path)` - List status of all tasks

### test_runner.py
- `detect_test_command(repo_path)` - Auto-detect test framework (npm, pytest, go, cargo, etc.)
- `run_tests(repo_path, test_command, timeout)` - Run tests with full output
- `verify_tests_pass(repo_path, test_command, timeout)` - Simple pass/fail check
- `run_tests_with_retry(repo_path, test_command, timeout, max_retries)` - Run with retry for flaky tests

### workspace.py
- `init_workspace(repo_url, branch, workspace_path)` - Initialize workspace
- `workspace_status(workspace_path)` - Get workspace status
- `cleanup_workspace(workspace_path, remove_repo)` - Clean up

### task.py
- `create_task(ticket, task_name, main_branch, workspace_path)` - Create task
- `sync_task(task_name, main_branch, workspace_path)` - Rebase task
- `reset_task(task_name, main_branch, workspace_path)` - Reset task
- `accept_task(ticket, task_name, main_branch, workspace_path)` - Accept task
- `task_status(task_name, workspace_path)` - Get task status
- `list_tasks(workspace_path)` - List all tasks

### git_ops.py
- `rebase_branch(worktree_path, target_branch)` - Rebase operation (now includes conflict info)
- `merge_branch(repo_path, source, target, message)` - Merge branches
- `delete_branch(repo_path, branch, force, delete_remote)` - Delete branch
- `sync_all_worktrees(workspace_path, main_branch)` - Sync all worktrees (locked)
- `get_diff_stats(repo_path, base, head)` - Get diff statistics
- `get_commits_between(repo_path, base, head)` - Get commit list

### conflict_resolver.py
- `detect_conflicts(worktree_path)` - Detect and list all conflicts in a worktree
- `resolve_file(worktree_path, file_path, strategy)` - Resolve single file ("ours"/"theirs"/"manual")
- `resolve_all(worktree_path, strategy)` - Resolve all conflicts with same strategy
- `abort_rebase(worktree_path)` - Abort current rebase operation
- `abort_merge(worktree_path)` - Abort current merge operation
- `abort_operation(worktree_path)` - Abort either rebase or merge
- `continue_rebase(worktree_path)` - Continue rebase after resolution
- `continue_merge(worktree_path, message)` - Complete merge after resolution
- `format_conflict_report(conflicts, task_name)` - Format human-readable report

### locking.py
- `workspace_lock(workspace_path, operation)` - Context manager for workspace lock
- `check_lock_status(workspace_path)` - Check current lock status
- `force_unlock(workspace_path)` - Force remove a stale lock (use with caution)

### plan_parser.py
- `parse_plan(workspace_path)` - Parse plan.md and extract task info, dependencies, and status
- `get_unblocked_tasks(workspace_path)` - Return tasks ready to spawn (all dependencies met)
- `check_dependencies(task_name, workspace_path)` - Check if task dependencies are met
- `format_unblocked_report(workspace_path)` - Format human-readable dependency status report

## File Structure

The operator maintains this workspace structure:

```
myworkspace/                     # Operator root (NOT a git repo)
├── plan.md                      # Task board
├── review-notes.md              # Decision log
├── workspace.json               # Configuration (optional)
├── .workspace.lock              # Lock file (when operation in progress)
├── .workspace.lock.info         # Lock holder info (for debugging)
├── repo/                        # Main clone
└── task-{name}/                 # Task folders
    ├── spec.md                  # Task specification
    ├── feedback.md              # Iteration feedback
    ├── results.md               # Sub-agent output
    ├── .subagent-status.json    # Sub-agent health status
    └── worktree/                # Git worktree
```

## Key Files

| File | Purpose | Who Writes |
|------|---------|------------|
| plan.md | Task status tracking | Operator |
| review-notes.md | Decision reasoning | Operator |
| spec.md | Task specification | Operator |
| feedback.md | Iteration feedback | Operator |
| results.md | Work summary | Sub-agent |

## Instructions

### General Behavior

1. **Always know the current state** - Before any action, check workspace status
2. **Update plan.md** - After every status change (task created, accepted, etc.)
3. **Log decisions** - Write reasoning to review-notes.md when accepting/rejecting
4. **Don't implement** - Operator orchestrates, sub-agents implement

### On Init

1. Clone repository to `repo/` folder
2. Checkout the specified branch
3. Create `plan.md` and `review-notes.md`
4. Report workspace setup complete

### On Plan

1. Analyze the codebase in `repo/`
2. Identify discrete tasks needed
3. Write plan.md with task breakdown
4. Each task should be:
   - Single-purpose
   - Independently testable
   - Clear acceptance criteria

### On Create Task

1. Create task folder `task-{name}/`
2. Create worktree with sub-branch
3. Write detailed spec.md
4. Update plan.md with new task

### On Spawn Sub-Agent

1. **Check dependencies** (from plan.md)
   - If dependencies not met, spawn is blocked
   - Use `--force` flag to override dependency check
2. Determine headless vs interactive mode
3. Build sub-agent prompt with:
   - Task folder path
   - Instructions to read spec.md
   - Instructions to write results.md
4. Execute spawn command

### On Review

1. Read results.md from sub-agent
2. View git diff between main and sub-branch
3. Assess:
   - Does it meet acceptance criteria?
   - Are tests passing?
   - Is code quality acceptable?
4. Present decision options: Accept, Iterate, Reset

### On Accept

1. Rebase sub-branch onto main
2. Merge with --no-ff
3. Run tests
4. Push main branch
5. Remove worktree
6. Delete sub-branch
7. Sync remaining worktrees
8. Update plan.md

### On Iterate

1. Write feedback to feedback.md
2. Log decision in review-notes.md
3. Re-spawn sub-agent on same worktree

### On Reset

1. Hard reset worktree to main branch
2. Optionally revise spec.md
3. Re-spawn sub-agent

### On Sync

1. Find all active worktrees
2. Rebase each onto main branch
3. Report any conflicts

## Sub-Agent Spawn Command

### Headless Inline Mode (consumes session tokens)
```bash
claude --dangerously-skip-permissions -p "You are a sub-agent working on task '{task_name}'.

Your task folder is: {workspace}/task-{task_name}/
Your worktree is: {workspace}/task-{task_name}/worktree/

Instructions:
1. Read spec.md to understand your task
2. Read feedback.md if it exists (previous iteration feedback)
3. Work in worktree/ - edit files, run tests
4. Commit your changes with clear messages
5. Write results.md summarizing your work
6. Exit when done

IMPORTANT: Only modify files in your worktree. Do not touch other folders."
```

### Headless Forked Mode (runs in new terminal, no token cost)
```python
from tools.fork_terminal import spawn_forked_subagent

result = spawn_forked_subagent(
    task_name="{task_name}",
    ticket="{ticket}",
    workspace_path=".",
    model="opus",  # or "sonnet", "haiku"
    iteration=1,
    force=False  # Set to True to skip dependency checking
)
```

Or via command line:
```bash
python tools/fork_terminal.py --spawn {task_name} {ticket} . opus

# To skip dependency checking:
python tools/fork_terminal.py --spawn {task_name} {ticket} . opus --force
```

### Interactive Mode
Spawn in new terminal without -p flag, then provide instructions.

## Error Handling

All errors now include structured recovery hints with actionable options.

### Error Format

Errors return a standardized format:
```json
{
  "success": false,
  "error": "Human-readable error message",
  "hint": "Brief actionable hint",
  "recovery_options": [
    "First recovery option with command",
    "Second recovery option"
  ],
  "error_code": "ERROR_CODE"
}
```

### Common Error Patterns

- **Rebase conflicts**: Use `operator resolve {name}` to view and resolve conflicts
  - Shows conflicted files with preview of conflict markers
  - Offers resolution strategies: ours, theirs, manual, abort
  - See `cookbook/resolve-conflicts.md` for detailed guidance
- **Worktree exists**: Suggest reset or different task name
- **Branch exists**: Suggest force create or different name
- **Tests fail**: Include in review, decide whether to accept anyway
- **Dependencies not met**: Spawn blocked, show missing dependencies, suggest `--force` or complete dependencies first

### Diagnose Command

Use the `errors.py diagnose` command to get detailed information about common errors:

```bash
# Get diagnostic info for a specific error code
python tools/errors.py diagnose REBASE_CONFLICT

# List all known error codes
python tools/errors.py list
```

### Known Error Codes

| Code | Description |
|------|-------------|
| REPO_EXISTS | Repository folder already exists |
| REPO_NOT_FOUND | Repository not found |
| TASK_EXISTS | Task folder already exists |
| TASK_NOT_FOUND | Task folder not found |
| WORKTREE_NOT_FOUND | Worktree missing for task |
| REBASE_CONFLICT | Rebase has conflicts |
| MERGE_CONFLICT | Merge has conflicts |
| TESTS_FAILED | Tests failed during execution |
| TEST_TIMEOUT | Tests timed out |
| LOCK_HELD | Workspace locked by another operation |
| SUBAGENT_TIMEOUT | Sub-agent unresponsive |

### errors.py Module

The `tools/errors.py` module provides:

- `OperatorError`: Exception class with structured error info
- `make_error()`: Convenience function to create error dicts
- Pre-defined error functions for common scenarios
- `diagnose(error_code)`: Get diagnostic info for an error
- `list_known_errors()`: List all known error codes

## Dependency Enforcement

Tasks in plan.md can specify dependencies:

```markdown
### 3. implement-auth
- Status: PENDING
- Dependencies: setup-database, create-user-model
```

**Behavior:**
- `create_task()` - Warns if dependencies not met (does not block)
- `spawn_subagent()` - Blocks if dependencies not met
- Use `--force` flag to override dependency check
- `operator unblocked` - Shows tasks ready to spawn

**To check dependencies:**
```python
from tools.plan_parser import check_dependencies, get_unblocked_tasks

# Check specific task
result = check_dependencies("implement-auth", workspace_path)
if not result["can_spawn"]:
    print(f"Missing: {result['missing']}")

# Get all spawnable tasks
unblocked = get_unblocked_tasks(workspace_path)
print(f"Ready to spawn: {unblocked['unblocked']}")
```
