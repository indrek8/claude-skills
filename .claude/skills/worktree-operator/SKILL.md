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
| "operator spawn {name}" | spawn-subagent.md | Launch sub-agent on task |
| "operator run subagent {name}" | spawn-subagent.md | Same as above |
| "operator review {name}" | review-task.md | Review sub-agent output |
| "operator accept {name}" | accept-task.md | Rebase, merge, cleanup |
| "operator iterate {name}" | reject-iterate.md | Write feedback, re-spawn |
| "operator feedback {name}" | reject-iterate.md | Same as above |
| "operator reset {name}" | reject-reset.md | Reset worktree, re-spawn |
| "operator sync" | sync-worktrees.md | Rebase all active worktrees |
| "operator sync all" | sync-worktrees.md | Same as above |
| "operator status" | (inline) | Show plan.md + worktree status |

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
- `rebase_branch(worktree_path, target_branch)` - Rebase operation
- `merge_branch(repo_path, source, target, message)` - Merge branches
- `delete_branch(repo_path, branch, force, delete_remote)` - Delete branch
- `sync_all_worktrees(workspace_path, main_branch)` - Sync all worktrees
- `get_diff_stats(repo_path, base, head)` - Get diff statistics
- `get_commits_between(repo_path, base, head)` - Get commit list

## File Structure

The operator maintains this workspace structure:

```
myworkspace/                     # Operator root (NOT a git repo)
├── plan.md                      # Task board
├── review-notes.md              # Decision log
├── repo/                        # Main clone
└── task-{name}/                 # Task folders
    ├── spec.md                  # Task specification
    ├── feedback.md              # Iteration feedback
    ├── results.md               # Sub-agent output
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

1. Determine headless vs interactive mode
2. Build sub-agent prompt with:
   - Task folder path
   - Instructions to read spec.md
   - Instructions to write results.md
3. Execute spawn command

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

### Headless Mode
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

### Interactive Mode
Spawn in new terminal without -p flag, then provide instructions.

## Error Handling

- **Rebase conflicts**: Report to user, provide conflict files
- **Worktree exists**: Suggest reset or different task name
- **Branch exists**: Suggest force create or different name
- **Tests fail**: Include in review, decide whether to accept anyway
