# Prime Session

Prime Claude with the multi-agent Git worktree skills system.

## Context Files

@README.md
@PLAN.md

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

@.claude/skills/worktree-operator/cookbook/create-plan.md
@.claude/skills/worktree-operator/cookbook/create-task.md
@.claude/skills/worktree-operator/cookbook/spawn-subagent.md
@.claude/skills/worktree-operator/cookbook/review-task.md
@.claude/skills/worktree-operator/cookbook/accept-task.md
@.claude/skills/worktree-operator/cookbook/reject-iterate.md
@.claude/skills/worktree-operator/cookbook/reject-reset.md
@.claude/skills/worktree-operator/cookbook/sync-worktrees.md

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
- `operator init workspace` - Clone repo, setup workspace
- `operator plan` - Analyze codebase, create plan.md
- `operator create task {name}` - Create task folder + worktree
- `operator spawn {name}` - Launch sub-agent on task
- `operator review {name}` - Review sub-agent output
- `operator accept {name}` - Rebase, merge, cleanup
- `operator iterate {name}` - Write feedback, re-spawn
- `operator reset {name}` - Reset worktree, re-spawn
- `operator sync` - Rebase all active worktrees
- `operator status` - Show plan.md + worktree status

**Workspace Structure:**
```
myworkspace/
├── plan.md           # Task board
├── review-notes.md   # Decision log
├── repo/             # Main clone
└── task-{name}/      # Task folders
    ├── spec.md       # Task specification
    ├── feedback.md   # Iteration feedback
    ├── results.md    # Sub-agent output
    └── worktree/     # Git worktree
```

Ready to assist with multi-agent Git worktree workflows.
