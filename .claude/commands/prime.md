# Prime Session

Prime Claude with the multi-agent Git worktree skills system.

## Skills

@.claude/skills/worktree-operator/SKILL.md
@.claude/skills/worktree-subagent/SKILL.md

## Templates

@.claude/skills/worktree-common/templates/plan.md
@.claude/skills/worktree-common/templates/spec.md
@.claude/skills/worktree-common/templates/feedback.md
@.claude/skills/worktree-common/templates/results.md
@.claude/skills/worktree-common/templates/review-notes.md

## Operator Cookbooks

@.claude/skills/worktree-operator/cookbook/init-workspace.md
@.claude/skills/worktree-operator/cookbook/create-plan.md
@.claude/skills/worktree-operator/cookbook/create-task.md
@.claude/skills/worktree-operator/cookbook/spawn-subagent.md
@.claude/skills/worktree-operator/cookbook/review-task.md
@.claude/skills/worktree-operator/cookbook/analyze-quality.md
@.claude/skills/worktree-operator/cookbook/accept-task.md
@.claude/skills/worktree-operator/cookbook/reject-iterate.md
@.claude/skills/worktree-operator/cookbook/reject-reset.md
@.claude/skills/worktree-operator/cookbook/sync-worktrees.md
@.claude/skills/worktree-operator/cookbook/resolve-conflicts.md
@.claude/skills/worktree-operator/cookbook/batch-operations.md

## Operator Prompts

@.claude/skills/worktree-operator/prompts/context_handoff.md
@.claude/skills/worktree-operator/prompts/review_checklist.md

## Sub-Agent Cookbooks

@.claude/skills/worktree-subagent/cookbook/implement.md
@.claude/skills/worktree-subagent/cookbook/test.md
@.claude/skills/worktree-subagent/cookbook/refactor.md
@.claude/skills/worktree-subagent/cookbook/review.md

## Sub-Agent Prompts

@.claude/skills/worktree-subagent/prompts/spec_reader.md
@.claude/skills/worktree-subagent/prompts/results_writer.md

## Instructions

You are now primed with the multi-agent Git worktree workflow skills.

**Available Roles:**
- **Operator**: Orchestrates parallel AI sub-agent development using Git worktrees
- **Sub-Agent**: Implements specific tasks in isolated worktrees

**Operator Commands:**

| Command | Description |
|---------|-------------|
| `operator init workspace` | Clone repo, setup workspace |
| `operator init` | Same as above |
| `operator plan` | Analyze codebase, create plan.md |
| `operator analyze` | Same as above |
| `operator create task {name}` | Create task folder + worktree |
| `operator spawn {name}` | Launch sub-agent inline (default, consumes tokens) |
| `operator spawn inline {name}` | Same as above |
| `operator spawn forked {name}` | Launch sub-agent in forked terminal (no token cost) |
| `operator spawn interactive {name}` | Launch sub-agent in forked terminal (allows interaction) |
| `operator review {name}` | Review sub-agent output |
| `operator analyze {name}` | Get quality score + recommendation |
| `operator accept {name}` | Rebase, merge, cleanup |
| `operator iterate {name}` | Write feedback, re-spawn |
| `operator feedback {name}` | Same as above |
| `operator reset {name}` | Reset worktree, re-spawn |
| `operator sync` | Rebase all active worktrees |
| `operator sync all` | Same as above |
| `operator resolve {name}` | Show conflicts with resolution options |
| `operator conflicts {name}` | Same as above |
| `operator status` | Show plan.md + worktree status |
| `operator status {name}` | Check sub-agent health for specific task |
| `operator health {name}` | Same as above |
| `operator health` | Check health of all running sub-agents |
| `operator unblocked` | Show tasks ready to spawn (dependencies met) |

**Batch Operations:**

| Command | Description |
|---------|-------------|
| `operator create-all` | Create folders/worktrees for all pending tasks |
| `operator spawn-unblocked` | Spawn all tasks with met dependencies |
| `operator spawn-parallel N` | Spawn up to N tasks concurrently |

**Workspace Structure:**
```
myworkspace/
├── plan.md                # Task board
├── review-notes.md        # Decision log
├── workspace.json         # Configuration (optional)
├── .workspace.lock        # Lock file (when operation in progress)
├── repo/                  # Main clone
└── task-{name}/           # Task folders
    ├── spec.md            # Task specification
    ├── feedback.md        # Iteration feedback
    ├── results.md         # Sub-agent output
    ├── .subagent-status.json  # Sub-agent health status
    └── worktree/          # Git worktree
```

**Key Features:**
- Dependency enforcement between tasks
- Conflict resolution guidance
- Quality analysis with accept/iterate/reset recommendations
- Sub-agent health monitoring
- Structured error messages with recovery hints
- Workspace configuration via workspace.json
- Batch operations for parallel development

Ready to assist with multi-agent Git worktree workflows.
