# Plan: Build Multi-Agent Worktree Skills

## Status: IN PROGRESS
## Target: Claude Code Skills for Operator/Sub-Agent Workflow

---

## Overview

Build a set of Claude Code skills that implement the operator/sub-agent workflow documented in README.md. The skills will enable:

1. **Operator skill** - Orchestrates work: init workspace, plan, create tasks, spawn sub-agents, review, accept/reject, merge
2. **Sub-agent skill** - Implements work: read spec, work in worktree, commit, write results
3. **Common templates** - Shared templates for spec.md, feedback.md, results.md

---

## Tasks

### 1. setup-skill-structure
- Status: COMPLETED
- Dependencies: None
- Description: Create the `.claude/skills/` directory structure

**Deliverables:**
```
.claude/skills/
├── worktree-operator/
│   ├── SKILL.md
│   ├── cookbook/
│   ├── prompts/
│   └── tools/
├── worktree-subagent/
│   ├── SKILL.md
│   ├── cookbook/
│   └── prompts/
└── worktree-common/
    └── templates/
```

---

### 2. create-common-templates
- Status: COMPLETED
- Dependencies: setup-skill-structure
- Description: Create shared templates used by operator and sub-agent

**Deliverables:**
- `worktree-common/templates/spec.md` - Task specification template
- `worktree-common/templates/feedback.md` - Iteration feedback template
- `worktree-common/templates/results.md` - Sub-agent results template
- `worktree-common/templates/plan.md` - Plan.md template

---

### 3. create-operator-tools
- Status: COMPLETED
- Dependencies: setup-skill-structure
- Description: Create Python tools for operator workspace/task management

**Deliverables:**
- `worktree-operator/tools/workspace.py`
  - `init_workspace(repo_url, branch, workspace_path)` - Clone and setup
  - `workspace_status()` - Show current state
  - `cleanup_workspace()` - Remove all worktrees, cleanup

- `worktree-operator/tools/task.py`
  - `create_task(ticket, task_name, main_branch)` - Create folder + worktree
  - `sync_task(task_name, main_branch)` - Rebase worktree
  - `reset_task(task_name, main_branch)` - Hard reset worktree
  - `accept_task(ticket, task_name, main_branch)` - Rebase + merge + cleanup
  - `task_status(task_name)` - Show task state

- `worktree-operator/tools/git_ops.py`
  - `rebase_branch(worktree_path, target_branch)` - Rebase operation
  - `merge_branch(repo_path, source_branch, target_branch)` - Merge with --no-ff
  - `cleanup_branch(repo_path, branch_name)` - Delete local + remote branch
  - `sync_all_worktrees(workspace_path, main_branch)` - Rebase all active

---

### 4. create-operator-skill-definition
- Status: COMPLETED
- Dependencies: create-operator-tools
- Description: Create SKILL.md that defines operator triggers and behavior

**Deliverables:**
- `worktree-operator/SKILL.md`

**Triggers to implement:**
| Trigger | Action |
|---------|--------|
| "operator init workspace" | init-workspace.md cookbook |
| "operator plan" / "operator analyze" | create-plan.md cookbook |
| "operator create task X" | create-task.md cookbook |
| "operator spawn/run subagent X" | spawn-subagent.md cookbook |
| "operator review X" | review-task.md cookbook |
| "operator accept X" | accept-task.md cookbook |
| "operator iterate X" / "operator feedback X" | reject-iterate.md cookbook |
| "operator reset X" | reject-reset.md cookbook |
| "operator sync" / "operator sync all" | sync-worktrees.md cookbook |
| "operator status" | Show plan.md + worktree status |

---

### 5. create-operator-cookbooks
- Status: COMPLETED
- Dependencies: create-operator-skill-definition
- Description: Create cookbook files for each operator action

**Deliverables:**
- `worktree-operator/cookbook/init-workspace.md`
  - Steps to clone repo, setup workspace structure
  - Create plan.md, review-notes.md

- `worktree-operator/cookbook/create-plan.md`
  - Analyze codebase
  - Identify tasks
  - Write plan.md using template

- `worktree-operator/cookbook/create-task.md`
  - Create task folder
  - Create worktree with sub-branch
  - Write spec.md using template

- `worktree-operator/cookbook/spawn-subagent.md`
  - Determine headless vs interactive
  - Build claude command with context
  - Execute spawn

- `worktree-operator/cookbook/review-task.md`
  - Read results.md
  - View git diff
  - Analyze quality
  - Present decision options

- `worktree-operator/cookbook/accept-task.md`
  - Rebase sub-branch
  - Run tests
  - Merge --no-ff
  - Cleanup worktree + branch
  - Update plan.md
  - Sync remaining worktrees

- `worktree-operator/cookbook/reject-iterate.md`
  - Write feedback.md
  - Log in review-notes.md
  - Re-spawn sub-agent

- `worktree-operator/cookbook/reject-reset.md`
  - Reset worktree
  - Optionally revise spec.md
  - Re-spawn sub-agent

- `worktree-operator/cookbook/sync-worktrees.md`
  - Find all active worktrees
  - Rebase each onto main feature

---

### 6. create-operator-prompts
- Status: COMPLETED
- Dependencies: create-common-templates
- Description: Create prompt templates for operator

**Deliverables:**
- `worktree-operator/prompts/context_handoff.md`
  - Template for context passed to sub-agents
  - Includes: task spec, relevant codebase context, iteration feedback

- `worktree-operator/prompts/review_analysis.md`
  - Template for analyzing sub-agent output
  - Checklist: correctness, completeness, tests, style

---

### 7. create-subagent-skill-definition
- Status: COMPLETED
- Dependencies: setup-skill-structure
- Description: Create SKILL.md for sub-agent behavior

**Deliverables:**
- `worktree-subagent/SKILL.md`

**Behavior:**
- Activates when Claude spawned with task context
- Reads spec.md to understand task
- Reads feedback.md if exists (iteration)
- Works in worktree/
- Commits changes
- Writes results.md
- Exits (headless) or signals done (interactive)

**Modes:**
| Mode | When |
|------|------|
| implement | Default - implement features |
| test | Spec focuses on testing |
| refactor | Spec focuses on refactoring |
| review | Spec asks for code review |

---

### 8. create-subagent-cookbooks
- Status: COMPLETED
- Dependencies: create-subagent-skill-definition
- Description: Create cookbook files for sub-agent modes

**Deliverables:**
- `worktree-subagent/cookbook/implement.md`
  - Read and understand spec
  - Plan implementation
  - Make changes
  - Run tests
  - Commit with good messages
  - Write results.md

- `worktree-subagent/cookbook/test.md`
  - Understand what needs testing
  - Write unit tests
  - Write integration tests (if specified)
  - Ensure coverage targets met
  - Commit and document

- `worktree-subagent/cookbook/refactor.md`
  - Understand refactoring goals
  - Ensure tests exist first
  - Make incremental changes
  - Verify tests still pass
  - Commit and document

- `worktree-subagent/cookbook/review.md`
  - Analyze code for issues
  - Check patterns and style
  - Identify potential bugs
  - Write review findings to results.md

---

### 9. create-subagent-prompts
- Status: COMPLETED
- Dependencies: create-common-templates
- Description: Create prompt templates for sub-agent

**Deliverables:**
- `worktree-subagent/prompts/spec_reader.md`
  - How to parse and understand spec.md
  - Extracting requirements, acceptance criteria

- `worktree-subagent/prompts/results_writer.md`
  - How to write comprehensive results.md
  - Sections: summary, changes, files, tests, risks, commits

---

### 10. integration-testing
- Status: COMPLETED
- Dependencies: All above
- Description: Test end-to-end workflow

**Test scenarios:**
1. Init workspace with real repo
2. Create plan with 2-3 tasks
3. Create task, spawn sub-agent, review
4. Accept one task, verify merge
5. Iterate on another task
6. Reset a task
7. Sync worktrees after merge
8. Complete all tasks

---

### 11. documentation-and-examples
- Status: COMPLETED
- Dependencies: integration-testing
- Description: Add usage examples and troubleshooting

**Deliverables:**
- Update README.md with skill installation instructions
- Add example session transcript
- Document common issues specific to skills

---

## Execution Order

```
1. setup-skill-structure
   │
   ├─► 2. create-common-templates
   │       │
   │       ├─► 6. create-operator-prompts
   │       │
   │       └─► 9. create-subagent-prompts
   │
   ├─► 3. create-operator-tools
   │       │
   │       └─► 4. create-operator-skill-definition
   │               │
   │               └─► 5. create-operator-cookbooks
   │
   └─► 7. create-subagent-skill-definition
           │
           └─► 8. create-subagent-cookbooks

All above ─► 10. integration-testing
                    │
                    └─► 11. documentation-and-examples
```

---

## Notes

### Design Decisions

1. **Python tools vs bash scripts**
   - Using Python for tools (workspace.py, task.py, git_ops.py)
   - More robust error handling
   - Easier to test
   - Consistent with fork-repository-skill pattern

2. **Skill activation**
   - Operator: explicit triggers ("operator X")
   - Sub-agent: context-based (spawned in task folder)

3. **Sub-agent spawn method**
   - Use `claude --dangerously-skip-permissions -p "..."` for headless
   - Use forked terminal for interactive
   - Pass context via prompt, not files (except spec.md/feedback.md)

4. **State management**
   - All state in filesystem (plan.md, review-notes.md, task folders)
   - No database or external state
   - Easy to inspect, debug, recover

### Open Questions

1. **How to handle sub-agent failures?**
   - Sub-agent crashes mid-work
   - Incomplete commits
   - Proposed: Operator can always reset

2. **Parallel sub-agents?**
   - Can spawn multiple sub-agents on different tasks
   - Each has own worktree - no conflicts
   - Operator reviews sequentially or in parallel?

3. **CI integration?**
   - Push sub-branches for CI?
   - Wait for CI before merge?
   - Proposed: Optional, operator decides

---

## Success Criteria

- [ ] Can init workspace from any git repo
- [ ] Can create plan with task breakdown
- [ ] Can create tasks with worktrees
- [ ] Can spawn sub-agents (headless and interactive)
- [ ] Sub-agents can implement, test, refactor, review
- [ ] Can review sub-agent output
- [ ] Can accept (rebase + merge + cleanup)
- [ ] Can iterate (feedback + re-spawn)
- [ ] Can reset (hard reset + re-spawn)
- [ ] Remaining worktrees sync after merge
- [ ] All state tracked in markdown files
- [ ] Works with real-world repositories
