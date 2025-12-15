# Multi-Agent Git Workflow with Worktrees

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/indrek8/claude-skills)](https://github.com/indrek8/claude-skills/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/indrek8/claude-skills)](https://github.com/indrek8/claude-skills/issues)

A complete workflow and Claude Code skill system for parallel AI agent development using Git worktrees, designed for operator/sub-agent orchestration patterns.

---

## Table of Contents

1. [Overview](#overview)
2. [Skill Installation](#skill-installation)
3. [Quick Start Guide](#quick-start-guide)
4. [Workspace Structure](#workspace-structure)
5. [File Purposes](#file-purposes)
6. [Git Branch Structure](#git-branch-structure)
7. [Roles: Operator vs Sub-Agent](#roles-operator-vs-sub-agent)
8. [Complete Workflow](#complete-workflow)
9. [Rebase vs Merge Strategy](#rebase-vs-merge-strategy)
10. [Claude Code Skills Architecture](#claude-code-skills-architecture)
11. [Forked Terminals vs Sub-Agents](#forked-terminals-vs-sub-agents)
12. [Example Session Transcript](#example-session-transcript)
13. [Helper Scripts](#helper-scripts)
14. [Common Issues and Solutions](#common-issues-and-solutions)
15. [Quick Reference](#quick-reference)
16. [Troubleshooting](#troubleshooting)

---

## Overview

This system enables an **operator** (orchestrating AI agent) to manage multiple **sub-agents** working in parallel on isolated Git worktrees. The operator:
- Plans and decomposes work
- Creates sandboxed environments (worktrees) for sub-agents
- Reviews sub-agent output
- Decides to iterate, reset, or accept work
- Merges accepted work back to the main feature branch

**Key benefits:**
- Parallel development without branch conflicts
- Clean separation of concerns (operator orchestrates, sub-agents implement)
- Safe experimentation (worktrees are isolated)
- Full audit trail (plan.md, review-notes.md, task docs preserved)

[Back to Top](#table-of-contents)

---

## Skill Installation

### Prerequisites

- [Claude Code CLI](https://github.com/anthropics/claude-code) installed
- Git 2.15+ (for worktree support)
- Bash shell

### Installing the Skills

Copy the `skills/` and `commands/` directories to your project or home `.claude` directory:

```bash
# Option 1: Project-level installation (recommended)
# Skills will be available when running Claude Code in this project

# 1a) Copy from local clone
cp -r skills/* /path/to/your/project/.claude/skills/
cp -r commands/* /path/to/your/project/.claude/commands/

# 1b) Install from GitHub
TMP_DIR=$(mktemp -d) \
  && git clone --depth 1 git@github.com:indrek8/claude-skills.git "$TMP_DIR" \
  && cp -r "$TMP_DIR/skills/"* /path/to/your/project/.claude/skills/ \
  && cp -r "$TMP_DIR/commands/"* /path/to/your/project/.claude/commands/ \
  && rm -rf "$TMP_DIR"

# Option 2: User-level installation
# Skills will be available in all Claude Code sessions

# 2a) Copy from local clone
cp -r skills/* ~/.claude/skills/
cp -r commands/* ~/.claude/commands/

# 2b) Install from GitHub
TMP_DIR=$(mktemp -d) \
  && git clone --depth 1 git@github.com:indrek8/claude-skills.git "$TMP_DIR" \
  && cp -r "$TMP_DIR/skills/"* ~/.claude/skills/ \
  && cp -r "$TMP_DIR/commands/"* ~/.claude/commands/ \
  && rm -rf "$TMP_DIR"
```

### Skill Structure

After installation, you should have:

```
.claude/
├── commands/
│   └── prime_worktree_operator.md   # Slash command to prime Claude
│
└── skills/
    ├── worktree-common/
    │   └── templates/           # Shared templates
    │       ├── plan.md
    │       ├── spec.md
    │       ├── feedback.md
    │       ├── results.md
    │       └── review-notes.md
    │
    ├── worktree-operator/
    │   ├── SKILL.md            # Operator skill definition
    │   ├── cookbook/           # 9 workflow cookbooks
    │   ├── prompts/            # Context handoff templates
    │   └── tools/              # Python utilities
    │
    └── worktree-subagent/
        ├── SKILL.md            # Sub-agent skill definition
        ├── cookbook/           # 4 mode cookbooks
        └── prompts/            # Spec reading/results writing
```

### Verifying Installation

Start Claude Code and ask:

```
What skills do you have for worktree management?
```

Claude should recognize the operator and sub-agent skills.

### Using the Slash Command

The quickest way to prime Claude with the full worktree operator system is to use the included slash command:

```
/prime_worktree_operator
```

This command loads all skills, templates, cookbooks, and prompts into context, giving Claude complete knowledge of the multi-agent workflow system. Use this at the start of any session where you want to use the operator/sub-agent workflow.

**What the command loads:**
- Operator and sub-agent skill definitions
- All workflow templates (plan.md, spec.md, feedback.md, results.md, review-notes.md)
- Operator cookbooks (init, plan, create task, spawn, review, accept, iterate, reset, sync, resolve conflicts, batch operations)
- Sub-agent cookbooks (implement, test, refactor, review modes)
- Context handoff and review prompts

[Back to Top](#table-of-contents)

---

## Quick Start Guide

**Get started in 5 commands:**

```bash
mkdir myworkspace && cd myworkspace    # 1. Create workspace
claude                                  # 2. Start Claude Code
```

Then tell Claude:
```
operator init <repo-url> <branch>       # 3. Initialize
operator plan                           # 4. Create plan
operator create <task-name>             # 5. Create task
operator spawn <task-name>              # 6. Run sub-agent
operator accept <task-name>             # 7. Merge when done
```

**Detailed steps below** | [Skip to Workspace Structure](#workspace-structure)

---

### Step 1: Create an Empty Workspace

```bash
mkdir myworkspace
cd myworkspace
```

### Step 2: Start Claude Code

```bash
claude
```

### Step 3: Initialize the Workspace

Tell Claude:

```
operator init workspace for K-123
Repository: git@github.com:myorg/myrepo.git
Branch: feature/K-123_user_auth
```

Claude will clone the repo, create `plan.md` and `review-notes.md`, and set up the workspace structure.

### Step 4: Create a Plan

```
operator analyze and create plan
```

Claude will analyze the codebase, identify tasks, and write a structured `plan.md`.

### Step 5: Create and Execute Tasks

```
operator create task fix-logging
operator run subagent on fix-logging
```

Claude will create the task folder with worktree and spec, then spawn a sub-agent to implement.

### Step 6: Review and Accept

```
operator review fix-logging
operator accept fix-logging
```

Claude will show the diff and results, then rebase, merge, and cleanup.

### Step 7: Continue with Next Task

Repeat steps 5-6 for each task in your plan.

[Back to Top](#table-of-contents)

---

## Workspace Structure

```
myworkspace/                              # operator root (NOT a git repo)
│
├── plan.md                               # task board: what's done, what's next
├── review-notes.md                       # decision log: why we accepted/rejected
│
├── repo/                                 # main clone (feature branch or develop)
│   └── <source code>
│
├── task-fix-logging/                     # task folder
│   ├── spec.md                           # task specification for sub-agent
│   ├── feedback.md                       # operator feedback (for iterations)
│   ├── results.md                        # sub-agent output summary
│   └── worktree/                         # git worktree (feature/K-123/fix-logging)
│       └── <source code>
│
├── task-fix-tests/
│   ├── spec.md
│   ├── feedback.md
│   ├── results.md
│   └── worktree/
│
└── task-refactor-config/
    ├── spec.md
    ├── feedback.md
    ├── results.md
    └── worktree/
```

**Key principles:**
- `myworkspace/` is the operator root - **never** a git repo
- All `.md` files live outside git repos - safe from commits/merges
- Each task gets its own folder containing docs + worktree
- `repo/` and `task-*/` folders are siblings under workspace

[Back to Top](#table-of-contents)

---

## File Purposes

### Workspace-Level Files

| File | Purpose | Who Writes | When Updated |
|------|---------|------------|--------------|
| **plan.md** | Task board - tracks what's done, in progress, pending | Operator | After each task status change |
| **review-notes.md** | Decision log - reasoning behind accept/reject decisions | Operator | During reviews, when making decisions |

#### plan.md - The Task Board

Semi-structured progress tracker. Shows current state of all tasks.

```markdown
# Plan: K-123 User Authentication

## Status: IN_PROGRESS
## Branch: feature/K-123_user_auth

## Tasks

### 1. fix-logging
- Status: COMPLETED
- Branch: feature/K-123/fix-logging
- Merged: 2024-01-15
- Summary: Improved service logging with structured output

### 2. fix-tests
- Status: IN_PROGRESS
- Branch: feature/K-123/fix-tests
- Iteration: 2
- Blocker: None

### 3. refactor-config
- Status: PENDING
- Dependencies: fix-logging
- Notes: Wait until logging merged to avoid conflicts
```

**Key question answered:** "What's the current state of work?"

#### review-notes.md - The Decision Log

Free-form log of operator decisions and reasoning.

```markdown
# Review Notes

## 2024-01-15 14:30 - fix-logging review

Reviewed diff: 47 lines changed across 3 files.
Quality: Good overall. Structured logging format matches existing patterns.
Tests: All passing.
Decision: ACCEPT

## 2024-01-15 16:00 - fix-tests review (iteration 1)

Reviewed diff: 120 lines, mostly test files.
Issue: Sub-agent only wrote unit tests, missing integration tests per spec.
Decision: REJECT - ITERATE
Feedback written to task-fix-tests/feedback.md

## 2024-01-15 17:00 - Architecture decision

Question: Should refactor-config happen before or after fix-tests?
Consideration: Config changes might affect test mocks.
Decision: After. Tests need stable config interface.
```

**Key question answered:** "Why did we make this decision?"

### Task-Level Files

| File | Purpose | Who Writes | When Read |
|------|---------|------------|-----------|
| **spec.md** | Task specification - what sub-agent should do | Operator | Sub-agent reads at start |
| **feedback.md** | Iteration feedback - what to fix/improve | Operator | Sub-agent reads on iteration |
| **results.md** | Work summary - what was done, changes, risks | Sub-agent | Operator reads during review |

#### spec.md - Task Specification

```markdown
# Task: fix-logging

## Objective
Improve logging in the foo service to use structured JSON format.

## Requirements
1. Replace console.log with structured logger
2. Include request ID in all log entries
3. Add log levels (debug, info, warn, error)

## Files to Modify
- src/services/foo.ts
- src/utils/logger.ts (create if needed)

## Acceptance Criteria
- All tests pass
- No console.log remaining in foo service
- Logs parseable as JSON

## Context
We're preparing for production monitoring. Need structured logs for log aggregation.
```

#### feedback.md - Iteration Feedback

```markdown
# Feedback: fix-tests (Iteration 1)

## Issues Found
1. Missing integration tests - spec required both unit AND integration
2. Test coverage only 60%, need 80%+

## Required Changes
1. Add integration tests in tests/integration/
2. Test the full request flow, not just individual functions
3. Mock external services properly

## Hints
- Look at tests/integration/auth.test.ts for pattern
- Use testcontainers for database tests
```

#### results.md - Sub-Agent Output

```markdown
# Results: fix-logging

## Summary
Implemented structured JSON logging for foo service.

## Changes Made
- Created src/utils/logger.ts with winston-based structured logger
- Replaced 12 console.log calls with structured logging
- Added request ID propagation via async context

## Files Modified
- src/services/foo.ts (modified)
- src/utils/logger.ts (created)
- src/middleware/requestId.ts (created)
- package.json (added winston dependency)

## Tests
- All existing tests pass
- Added 5 new tests for logger utility

## Risks / Notes
- Winston adds ~50KB to bundle size
- Request ID middleware must be registered before foo service routes

## Commits
- abc1234: feat: add structured logger utility
- def5678: refactor: replace console.log in foo service
- ghi9012: feat: add request ID propagation
```

[Back to Top](#table-of-contents)

---

## Git Branch Structure

```
develop                                   # shared long-lived branch (NEVER rebase)
│
└── feature/K-123_user_auth               # main feature (in repo/)
    │
    ├── feature/K-123/fix-logging         # sub-branch (in task-fix-logging/worktree/)
    ├── feature/K-123/fix-tests           # sub-branch (in task-fix-tests/worktree/)
    └── feature/K-123/refactor-config     # sub-branch (in task-refactor-config/worktree/)
```

**Naming conventions:**

| Type | Branch Pattern | Folder |
|------|----------------|--------|
| Main feature | `feature/K-123_feature_name` | `repo/` |
| Sub-task | `feature/K-123/<task-name>` | `task-<task-name>/worktree/` |

[Back to Top](#table-of-contents)

---

## Roles: Operator vs Sub-Agent

### Operator

The **orchestrator**. Does not write implementation code directly.

**Responsibilities:**
1. Initialize workspace (clone repo, setup structure)
2. Analyze codebase and create plan
3. Create task folders and worktrees
4. Write task specifications (spec.md)
5. Spawn sub-agents
6. Review sub-agent output
7. Decide: iterate (write feedback), reset, or accept
8. Merge accepted work (rebase + merge --no-ff)
9. Sync remaining worktrees after merge
10. Update plan.md status
11. Log decisions in review-notes.md

**Does NOT:**
- Write implementation code
- Work directly in worktrees
- Make commits in sub-branches

### Sub-Agent

The **worker**. Implements specific tasks in isolated worktrees.

**Responsibilities:**
1. Read spec.md (understand task)
2. Read feedback.md (if iteration - understand what to fix)
3. Work in worktree/ (edit files, run tests)
4. Make commits
5. Write results.md (summary of work done)
6. Exit (headless) or signal completion (interactive)

**Does NOT:**
- Modify files outside its worktree
- Merge branches
- Update plan.md or review-notes.md
- Work on other tasks

### Execution Modes

| Mode | Command | When to Use | Sub-Agent Behavior |
|------|---------|-------------|-------------------|
| **Inline** | `operator spawn {name}` | Small tasks, quick fixes | Runs in current session (consumes tokens) |
| **Forked** | `operator spawn forked {name}` | Larger tasks, parallel work | Runs in new terminal (headless, no token cost) |
| **Interactive** | `operator spawn interactive {name}` | Complex/unclear tasks | Runs in new terminal (can ask questions) |

[Back to Top](#table-of-contents)

---

## Complete Workflow

### Phase 0: Initialize Workspace

Human starts Claude in an empty folder:

```bash
# Create workspace structure
mkdir -p myworkspace
cd myworkspace

# Clone repository and checkout feature branch
git clone git@github.com:org/myrepo.git repo
cd repo
git switch feature/K-123_user_auth      # or create: git switch -c feature/K-123_user_auth
git pull --ff-only origin feature/K-123_user_auth
cd ..

# Create operator planning docs
touch plan.md review-notes.md
```

**Workspace state:**
```
myworkspace/
├── plan.md
├── review-notes.md
└── repo/                    [feature/K-123_user_auth]
```

---

### Phase 1: Operator Plans

Operator analyzes codebase and creates plan:

1. Read and understand the codebase in `repo/`
2. Identify tasks needed to complete the feature
3. Write plan.md with task breakdown
4. Log initial reasoning in review-notes.md

---

### Phase 2: Create Task

Operator creates task folder and worktree:

```bash
cd myworkspace

# Create task folder structure
TASK="fix-logging"
mkdir -p "task-${TASK}"
touch "task-${TASK}/spec.md"
touch "task-${TASK}/feedback.md"
touch "task-${TASK}/results.md"

# Create worktree with sub-branch
cd repo
git worktree add "../task-${TASK}/worktree" \
    -b "feature/K-123/${TASK}" \
    feature/K-123_user_auth
cd ..
```

Operator then writes detailed spec in `task-fix-logging/spec.md`.

**Verify worktrees:**
```bash
cd repo && git worktree list
```

---

### Phase 3: Spawn Sub-Agent

Operator spawns sub-agent to work on task:

**Inline mode (default - small tasks):**
```bash
claude --dangerously-skip-permissions \
    -p "You are a sub-agent. Your task folder is task-fix-logging/.
        Read spec.md, implement the task in worktree/,
        commit your changes, write results.md, then exit."
```

**Forked mode (larger tasks - runs in new terminal):**
```bash
# Opens new terminal window with headless sub-agent
python3 tools/fork_terminal.py --spawn fix-logging K-123 . opus
```

**Interactive mode (complex tasks - allows questions):**
```bash
# Opens new terminal, sub-agent can ask questions
osascript -e 'tell app "Terminal" to do script "cd task-fix-logging/worktree && claude"'
# Then instruct: "Read ../spec.md and implement the task"
```

---

### Phase 4: Sub-Agent Works

Sub-agent in its worktree:

```bash
cd myworkspace/task-fix-logging/worktree

# Read spec
cat ../spec.md

# Read feedback (if iteration)
cat ../feedback.md

# Make changes
# ... edit files ...

# Stage and commit
git add .
git commit -m "K-123: Fix logging in foo service"

# Run tests
npm test

# Write results
# ... write ../results.md ...

# Optional: push for CI/backup
git push -u origin feature/K-123/fix-logging
```

---

### Phase 5: Operator Reviews

Operator reviews sub-agent work:

```bash
cd myworkspace/repo

# View commits made by sub-agent
git log --oneline feature/K-123_user_auth..feature/K-123/fix-logging

# View diff
git diff feature/K-123_user_auth..feature/K-123/fix-logging

# Read results
cat ../task-fix-logging/results.md
```

Three possible outcomes:

#### Outcome A: Reject → Iterate

Work needs improvement. Operator:
1. Writes feedback to `task-fix-logging/feedback.md`
2. Logs decision in `review-notes.md`
3. Re-spawns sub-agent on same worktree

```bash
# Sub-agent reads feedback, continues in same worktree
cd myworkspace/task-fix-logging/worktree
cat ../feedback.md
# ... more edits ...
git add .
git commit -m "K-123: Address review feedback"
```

#### Outcome B: Reject → Reset

Work is fundamentally wrong. Reset worktree:

```bash
cd myworkspace/task-fix-logging/worktree
git fetch origin
git reset --hard feature/K-123_user_auth
git clean -fd
```

Worktree now matches main feature branch. Spawn new sub-agent with revised spec.

#### Outcome C: Accept → Rebase → Merge

Work is good. Integrate into main feature branch:

**Step 1: Rebase sub-branch onto latest main feature**

```bash
cd myworkspace/task-fix-logging/worktree

git fetch origin
git rebase feature/K-123_user_auth

# If conflicts: resolve, git add, git rebase --continue

npm test  # verify tests pass after rebase
```

**Step 2: Merge into main feature branch**

```bash
cd myworkspace/repo

git switch feature/K-123_user_auth
git merge --no-ff feature/K-123/fix-logging -m "Merge fix-logging: improved service logging"

npm test  # run full test suite

git push origin feature/K-123_user_auth
```

**Step 3: Cleanup**

```bash
cd myworkspace/repo

# Remove worktree (keeps task folder and .md files)
git worktree remove ../task-fix-logging/worktree

# Delete sub-branch locally
git branch -d feature/K-123/fix-logging

# Delete sub-branch from remote (if pushed)
git push origin --delete feature/K-123/fix-logging
```

**Step 4: Update plan.md**

Mark task as COMPLETED, update any dependencies.

---

### Phase 6: Sync Remaining Worktrees

After merging, remaining worktrees are behind. Rebase them:

```bash
# Sync fix-tests worktree
cd myworkspace/task-fix-tests/worktree
git fetch origin
git rebase feature/K-123_user_auth
npm test
```

**Why rebase?**
- Keeps sub-branch based on latest feature state
- Surfaces conflicts early
- Clean history

---

### Phase 7: Final Integration to Develop

After all sub-tasks merged into main feature branch:

```bash
cd myworkspace/repo

git switch feature/K-123_user_auth
git pull --ff-only origin feature/K-123_user_auth

# Rebase onto latest develop
git fetch origin
git rebase origin/develop

npm test

# Merge into develop
git switch develop
git pull --ff-only origin develop
git merge --no-ff feature/K-123_user_auth -m "Merge K-123: User authentication feature"

npm test
git push origin develop
```

[Back to Top](#table-of-contents)

---

## Rebase vs Merge Strategy

### Policy Rules

| Branch Type | Rebase Allowed? | Merge Strategy |
|-------------|-----------------|----------------|
| `develop` / `main` | **NEVER** | N/A (target only) |
| Main feature branch | Before sub-tasks branch off | `--no-ff` into develop |
| Sub-task branches | **ALWAYS** before merge | `--no-ff` into feature |

### Why Rebase for Sub-Tasks?

```
Before rebase:
feature/K-123_user_auth:  A - B - C - D        (D = merged fix-logging)
feature/K-123/fix-tests:      B - X - Y        (branched from B)

After rebase:
feature/K-123_user_auth:  A - B - C - D
feature/K-123/fix-tests:              D - X' - Y'   (rebased onto D)
```

**Benefits:**
- Sub-branch always based on latest feature state
- Conflicts resolved incrementally
- Clean commit history

### Why `--no-ff` Merge?

```
With --no-ff:
A - B - C - D --------- M   [feature/K-123_user_auth]
              \       /
               X' - Y'      [feature/K-123/fix-tests]

Without (fast-forward):
A - B - C - D - X' - Y'     [feature/K-123_user_auth]
```

**Benefits:**
- Clear audit trail: "this work came from fix-tests task"
- Easy to revert entire sub-task: `git revert -m 1 <merge-commit>`
- Visual history shows parallel work streams
- Matches operator/sub-agent mental model

[Back to Top](#table-of-contents)

---

## Claude Code Skills Architecture

Skills are modular capabilities that extend Claude Code. See [Skill Installation](#skill-installation) for the directory structure.

### Operator Skill Triggers

| Trigger Phrase | Action |
|----------------|--------|
| "operator init workspace for K-123" | Clone repo, setup workspace structure |
| "operator analyze and create plan" | Analyze codebase, write plan.md |
| "operator create task fix-logging" | Create task folder, worktree, write spec |
| "operator run subagent on fix-logging" | Spawn sub-agent (headless or interactive) |
| "operator review fix-logging" | Review diff, results, decide outcome |
| "operator accept fix-logging" | Rebase, merge, cleanup |
| "operator iterate fix-logging" | Write feedback, re-spawn sub-agent |
| "operator reset fix-logging" | Reset worktree, re-spawn |
| "operator sync all" | Rebase all active worktrees |
| "operator status" | Show plan.md, worktree status |

### Sub-Agent Skill Triggers

Sub-agent skill activates automatically when Claude is spawned in a task worktree context.

| Mode | When Used |
|------|-----------|
| implement | Default - implement features per spec |
| test | Spec focuses on testing |
| refactor | Spec focuses on refactoring |
| review | Spec asks for code review |

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OPERATOR WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  INIT    │───▶│  PLAN    │───▶│  CREATE  │───▶│  SPAWN   │              │
│  │workspace │    │ tasks    │    │  task    │    │sub-agent │              │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘              │
│                                                        │                    │
│                                                        ▼                    │
│                                                  ┌──────────┐               │
│                                                  │  REVIEW  │               │
│                                                  │  output  │               │
│                                                  └────┬─────┘               │
│                        ┌───────────────────────────────┼───────────────┐    │
│                        │                               │               │    │
│                        ▼                               ▼               ▼    │
│                   ┌─────────┐                    ┌──────────┐    ┌─────────┐│
│                   │ ITERATE │                    │  RESET   │    │ ACCEPT  ││
│                   │feedback │                    │ restart  │    │ merge   ││
│                   └────┬────┘                    └────┬─────┘    └────┬────┘│
│                        │                              │               │     │
│                        └──────────────┬───────────────┘               │     │
│                                       │                               │     │
│                                       ▼                               ▼     │
│                              ┌──────────────┐                 ┌───────────┐ │
│                              │   RE-SPAWN   │                 │   SYNC    │ │
│                              │  sub-agent   │                 │ worktrees │ │
│                              └──────────────┘                 └─────┬─────┘ │
│                                                                     │       │
│                                                                     ▼       │
│                                                              ┌───────────┐  │
│                                                              │UPDATE PLAN│  │
│                                                              │ next task │  │
│                                                              └───────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          SUB-AGENT WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  READ    │───▶│  READ    │───▶│   WORK   │───▶│  COMMIT  │              │
│  │ spec.md  │    │feedback  │    │in worktree│   │ changes  │              │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘              │
│                   (if exists)                          │                    │
│                                                        ▼                    │
│                                                  ┌──────────┐               │
│                                                  │  WRITE   │               │
│                                                  │results.md│               │
│                                                  └────┬─────┘               │
│                                                       │                     │
│                                                       ▼                     │
│                                                  ┌──────────┐               │
│                                                  │   EXIT   │               │
│                                                  │(operator │               │
│                                                  │ reviews) │               │
│                                                  └──────────┘               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

[Back to Top](#table-of-contents)

---

## Forked Terminals vs Sub-Agents

### When to Use Each

| Scenario | Use | Reason |
|----------|-----|--------|
| Plan → assign → review → iterate loop | **Sub-agents** | Need conversational feedback |
| Long-running test suites | **Forked terminal** | Don't block main loop |
| Heavy analysis/indexing | **Forked terminal** | Background processing |
| Code review and refinement | **Sub-agents** | Interactive iteration |
| Parallel independent tasks | **Both** | Sub-agents in worktrees, fork for CLI |

### Key Distinction

**Forked terminals:**
- Fire-and-forget / background jobs
- Communication via filesystem (temp files)
- No direct feedback to operator
- Good for: tests, builds, heavy CLI work

**Sub-agents:**
- Operator sees output directly
- Can iterate with feedback
- Conversational loop
- Good for: implementation, review, complex tasks

### Hybrid Pattern

```
Operator (main conversation)
│
├── Sub-agent: Planner
│   └── Output: plan.md, task specs
│
├── Sub-agent: Implementer (in task-X/worktree)
│   ├── Interactive code changes
│   └── Forked terminal: npm test (background)
│
├── Sub-agent: Reviewer
│   └── Reviews diffs, writes feedback.md
│
└── Forked terminal: Full integration test suite
```

**Key insight:** Sub-agents handle the conversational loop (plan-review-iterate). Forked terminals handle heavy CLI work that sub-agents trigger but don't need to watch.

[Back to Top](#table-of-contents)

---

## Example Session Transcript

This is a complete example of using the operator skill to manage a feature implementation.

### Session Start

```
$ mkdir payment-feature && cd payment-feature
$ claude

╭─────────────────────────────────────────────────────────────╮
│ Claude Code                                                  │
╰─────────────────────────────────────────────────────────────╯

> operator init workspace for PAYMENT-42
  Repository: git@github.com:acme/billing-service.git
  Branch: feature/PAYMENT-42_stripe_integration
```

**Claude responds:**

```
I'll initialize the workspace for PAYMENT-42.

Setting up workspace structure...
✓ Created workspace directories
✓ Cloned repository to repo/
✓ Checked out feature/PAYMENT-42_stripe_integration
✓ Created plan.md
✓ Created review-notes.md

Workspace ready:
  payment-feature/
  ├── plan.md
  ├── review-notes.md
  └── repo/  [feature/PAYMENT-42_stripe_integration]

What would you like to do next? I can analyze the codebase and create a plan.
```

### Creating the Plan

```
> operator analyze and create plan
```

**Claude responds:**

```
Analyzing the billing-service codebase...

Found:
- Express.js API with TypeScript
- Existing PayPal integration in src/services/
- PostgreSQL database with Prisma ORM
- Jest test suite with 78% coverage

Based on the feature requirements (Stripe integration), I recommend these tasks:

1. add-stripe-config - Add Stripe SDK and configuration
2. create-stripe-service - Implement StripePaymentService
3. add-payment-routes - Add API endpoints for Stripe payments
4. add-stripe-webhooks - Handle Stripe webhook events
5. add-stripe-tests - Write tests for Stripe integration

Writing plan.md...
✓ Plan created with 5 tasks

View the plan with: cat plan.md
```

### Creating and Running a Task

```
> operator create task add-stripe-config
```

**Claude responds:**

```
Creating task: add-stripe-config

✓ Created task-add-stripe-config/
✓ Created worktree on branch feature/PAYMENT-42/add-stripe-config
✓ Written spec.md with requirements:
  - Add @stripe/stripe-node dependency
  - Create src/config/stripe.ts with environment-based configuration
  - Add STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET to .env.example

Acceptance criteria:
  - Stripe SDK importable throughout codebase
  - Configuration validates required env vars on startup
  - All existing tests pass

Ready to spawn sub-agent?
```

```
> operator run subagent on add-stripe-config
```

**Claude responds:**

```
Spawning sub-agent for task: add-stripe-config
Mode: headless (spec is clear and well-defined)

Sub-agent working...

[Sub-agent output]
Reading spec.md...
- Objective: Add Stripe SDK and configuration
- Requirements: 3 items
- Files to modify: package.json, src/config/stripe.ts (create), .env.example

Installing dependency...
$ npm install @stripe/stripe-node

Creating src/config/stripe.ts...
✓ Created with StripeConfig interface
✓ Added environment validation
✓ Exported initialized Stripe client

Updating .env.example...
✓ Added STRIPE_SECRET_KEY
✓ Added STRIPE_WEBHOOK_SECRET

Running tests...
✓ All 45 tests passing

Committing changes...
✓ PAYMENT-42: Add Stripe SDK and configuration

Writing results.md...
✓ Results documented

Sub-agent completed. Ready for review.
```

### Reviewing the Task

```
> operator review add-stripe-config
```

**Claude responds:**

```
Reviewing task: add-stripe-config

=== Results Summary ===
The sub-agent added Stripe SDK configuration with:
- @stripe/stripe-node@14.5.0 dependency
- src/config/stripe.ts with typed configuration
- Environment variable validation
- Updated .env.example

=== Diff Statistics ===
3 files changed, 47 insertions(+), 2 deletions(-)

=== Key Changes ===

package.json:
  + "@stripe/stripe-node": "^14.5.0"

src/config/stripe.ts (new file):
  + StripeConfig interface with typed keys
  + validateStripeConfig() function
  + Initialized Stripe client export

.env.example:
  + STRIPE_SECRET_KEY=sk_test_xxx
  + STRIPE_WEBHOOK_SECRET=whsec_xxx

=== Tests ===
All 45 existing tests pass
No new tests added (none required for config)

=== Commits ===
abc1234 PAYMENT-42: Add Stripe SDK and configuration

=== Assessment ===
✓ Correctness: Configuration follows best practices
✓ Completeness: All spec requirements met
✓ Code Quality: Matches existing patterns in src/config/
✓ Tests: All passing

Recommendation: ACCEPT

Options:
1. Accept - Merge this task
2. Iterate - Request changes
3. Reset - Start over
```

### Accepting the Task

```
> operator accept add-stripe-config
```

**Claude responds:**

```
Accepting task: add-stripe-config

Step 1: Rebasing sub-branch...
✓ feature/PAYMENT-42/add-stripe-config rebased onto feature/PAYMENT-42_stripe_integration

Step 2: Running tests...
✓ All 45 tests passing

Step 3: Merging...
✓ Merged with --no-ff: "Merge add-stripe-config: Add Stripe SDK and configuration"

Step 4: Pushing...
✓ Pushed to origin/feature/PAYMENT-42_stripe_integration

Step 5: Cleanup...
✓ Removed worktree
✓ Deleted local branch feature/PAYMENT-42/add-stripe-config
✓ Deleted remote branch

Step 6: Updating plan.md...
✓ Task add-stripe-config marked COMPLETED

=== Summary ===
Task add-stripe-config successfully merged.
Remaining tasks: 4

Next task: create-stripe-service
Would you like to create this task?
```

### Handling an Iteration

Later, after running `create-stripe-service`:

```
> operator review create-stripe-service
```

**Claude responds:**

```
Reviewing task: create-stripe-service

=== Assessment ===
✓ Correctness: Service implementation is correct
✗ Completeness: Missing error handling for declined cards
✓ Code Quality: Good structure
✗ Tests: Only 2 tests, spec required comprehensive coverage

Issues found:
1. No handling for Stripe card_declined errors
2. Missing tests for refund functionality
3. Test coverage for new code is only 45%

Recommendation: ITERATE

Options:
1. Accept - Merge anyway
2. Iterate - Request changes (recommended)
3. Reset - Start over
```

```
> operator iterate create-stripe-service
```

**Claude responds:**

```
Writing feedback for iteration...

feedback.md:
# Feedback: create-stripe-service (Iteration 1)

## Issues Found

### HIGH: Missing Error Handling
The StripePaymentService doesn't handle card_declined errors.
When Stripe returns a card_declined error, the service throws a generic error.
This should be caught and converted to a user-friendly PaymentDeclinedError.

### MEDIUM: Incomplete Test Coverage
Spec required comprehensive test coverage. Current coverage is 45%.
Missing tests:
- processRefund() happy path
- processRefund() partial refund
- Error scenarios (network timeout, invalid amount)

## Required Changes

1. Add try/catch in processPayment() for StripeCardError
2. Add PaymentDeclinedError class to src/errors/
3. Add tests for all refund scenarios
4. Add tests for error handling

## Hints
- See src/services/paypal.ts:89 for similar error handling pattern
- Use jest.spyOn to mock Stripe responses

✓ Logged decision in review-notes.md
✓ Feedback written to task-create-stripe-service/feedback.md

Spawning sub-agent for iteration 2...
```

### Session End - Final Status

```
> operator status
```

**Claude responds:**

```
=== Workspace Status ===
Ticket: PAYMENT-42
Branch: feature/PAYMENT-42_stripe_integration

=== Plan Progress ===
| # | Task                | Status      | Branch                              |
|---|---------------------|-------------|-------------------------------------|
| 1 | add-stripe-config   | COMPLETED   | (merged)                            |
| 2 | create-stripe-service| COMPLETED   | (merged, 2 iterations)              |
| 3 | add-payment-routes  | IN_PROGRESS | feature/PAYMENT-42/add-payment-routes|
| 4 | add-stripe-webhooks | PENDING     | -                                   |
| 5 | add-stripe-tests    | PENDING     | -                                   |

=== Active Worktrees ===
repo/                    feature/PAYMENT-42_stripe_integration  (main)
task-add-payment-routes/ feature/PAYMENT-42/add-payment-routes  (3 commits ahead)

=== Statistics ===
- Total commits merged: 5
- Total iterations: 3
- Tests: 67 (was 45)
- Coverage: 82% (was 78%)
```

[Back to Top](#table-of-contents)

---

## Helper Scripts

### task-create.sh

Creates task folder and worktree:

```bash
#!/bin/bash
set -e

WORKSPACE="${1:-.}"
TICKET="$2"
TASK="$3"
MAIN_BRANCH="${4:-feature/${TICKET}_feature_name}"

if [[ -z "$TICKET" || -z "$TASK" ]]; then
    echo "Usage: task-create.sh <workspace> <ticket> <task-name> [main-branch]"
    echo "Example: task-create.sh ./myworkspace K-123 fix-logging"
    exit 1
fi

TASK_DIR="${WORKSPACE}/task-${TASK}"
SUB_BRANCH="feature/${TICKET}/${TASK}"

# Create task folder structure
mkdir -p "${TASK_DIR}"
touch "${TASK_DIR}/spec.md"
touch "${TASK_DIR}/feedback.md"
touch "${TASK_DIR}/results.md"

# Create worktree
cd "${WORKSPACE}/repo"
git worktree add "${TASK_DIR}/worktree" -b "${SUB_BRANCH}" "${MAIN_BRANCH}"

echo "Created task: ${TASK_DIR}"
echo "Worktree branch: ${SUB_BRANCH}"
echo "Based on: ${MAIN_BRANCH}"
```

### task-sync.sh

Rebases worktree onto main feature branch:

```bash
#!/bin/bash
set -e

WORKSPACE="${1:-.}"
TASK="$2"
MAIN_BRANCH="${3:-feature/K-123_feature_name}"

if [[ -z "$TASK" ]]; then
    echo "Usage: task-sync.sh <workspace> <task-name> [main-branch]"
    exit 1
fi

WORKTREE="${WORKSPACE}/task-${TASK}/worktree"

cd "${WORKTREE}"
git fetch origin
git rebase "${MAIN_BRANCH}"

echo "Rebased task-${TASK} onto ${MAIN_BRANCH}"
echo "Run tests to verify: cd ${WORKTREE} && npm test"
```

### task-accept.sh

Accepts task: rebase, merge, cleanup:

```bash
#!/bin/bash
set -e

WORKSPACE="${1:-.}"
TICKET="$2"
TASK="$3"
MAIN_BRANCH="${4:-feature/${TICKET}_feature_name}"

if [[ -z "$TICKET" || -z "$TASK" ]]; then
    echo "Usage: task-accept.sh <workspace> <ticket> <task-name> [main-branch]"
    exit 1
fi

TASK_DIR="${WORKSPACE}/task-${TASK}"
WORKTREE="${TASK_DIR}/worktree"
SUB_BRANCH="feature/${TICKET}/${TASK}"
REPO="${WORKSPACE}/repo"

echo "=== Step 1: Rebase sub-branch ==="
cd "${WORKTREE}"
git fetch origin
git rebase "${MAIN_BRANCH}"
echo "Rebase complete. Run tests manually, then press Enter to continue..."
read

echo "=== Step 2: Merge into main feature ==="
cd "${REPO}"
git switch "${MAIN_BRANCH}"
git merge --no-ff "${SUB_BRANCH}" -m "Merge ${TASK}: $(head -1 ${TASK_DIR}/spec.md 2>/dev/null || echo 'task completed')"
echo "Merge complete. Run tests manually, then press Enter to continue..."
read

echo "=== Step 3: Push ==="
git push origin "${MAIN_BRANCH}"

echo "=== Step 4: Cleanup ==="
git worktree remove "${WORKTREE}"
git branch -d "${SUB_BRANCH}"
git push origin --delete "${SUB_BRANCH}" 2>/dev/null || echo "Remote branch already deleted or never pushed"

echo "=== Done ==="
echo "Task ${TASK} merged into ${MAIN_BRANCH}"
echo "Task docs preserved at: ${TASK_DIR}/"
```

### task-reset.sh

Resets worktree to main feature branch state:

```bash
#!/bin/bash
set -e

WORKSPACE="${1:-.}"
TASK="$2"
MAIN_BRANCH="${3:-feature/K-123_feature_name}"

if [[ -z "$TASK" ]]; then
    echo "Usage: task-reset.sh <workspace> <task-name> [main-branch]"
    exit 1
fi

WORKTREE="${WORKSPACE}/task-${TASK}/worktree"

cd "${WORKTREE}"
git fetch origin
git reset --hard "${MAIN_BRANCH}"
git clean -fd

echo "Reset task-${TASK} to ${MAIN_BRANCH}"
echo "Worktree is now clean for new sub-agent"
```

### task-status.sh

Shows status of all tasks:

```bash
#!/bin/bash

WORKSPACE="${1:-.}"
MAIN_BRANCH="${2:-feature/K-123_feature_name}"

echo "=== Workspace: ${WORKSPACE} ==="
echo ""

# List worktrees
echo "=== Git Worktrees ==="
cd "${WORKSPACE}/repo"
git worktree list
echo ""

# Show each task status
echo "=== Task Status ==="
for TASK_DIR in "${WORKSPACE}"/task-*/; do
    if [[ -d "$TASK_DIR" ]]; then
        TASK=$(basename "$TASK_DIR" | sed 's/^task-//')
        WORKTREE="${TASK_DIR}worktree"

        if [[ -d "$WORKTREE" ]]; then
            cd "$WORKTREE"
            BRANCH=$(git branch --show-current)
            COMMITS=$(git rev-list --count "${MAIN_BRANCH}..HEAD" 2>/dev/null || echo "?")
            STATUS=$(git status --porcelain | wc -l | tr -d ' ')
            echo "  ${TASK}: ${COMMITS} commits ahead, ${STATUS} uncommitted changes [${BRANCH}]"
        else
            echo "  ${TASK}: (worktree removed - task completed or abandoned)"
        fi
    fi
done
```

[Back to Top](#table-of-contents)

---

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| "Branch already checked out" | Each branch can only be in one worktree. Use unique sub-branch names per task. |
| Conflicts during rebase | Resolve in worktree, `git add`, `git rebase --continue`. If too messy, `git rebase --abort` and try merge instead. |
| Worktree out of sync | Run `task-sync.sh` to rebase onto latest main feature. |
| Forgot to rebase before merge | Merge still works, just noisier history. Next time rebase first. |
| Want to abandon task | `git worktree remove <path>`, `git branch -D <branch>`. Keep task folder for reference. |
| Main feature moved while working | Normal. Rebase sub-branch: `git rebase feature/K-123_user_auth`. |
| Sub-agent modified wrong files | Review caught it. Either iterate with feedback or reset. |
| Sub-agent didn't write results.md | Operator can still review via git diff. Add to feedback for next iteration. |

### Skill-Specific Issues

| Issue | Solution |
|-------|----------|
| "Skill not recognized" | Verify `.claude/skills/` exists and contains SKILL.md files. Check file permissions. |
| Sub-agent doesn't read spec.md | Ensure spec.md exists in task folder (not worktree). Check path in spawn command. |
| Sub-agent modifies files outside worktree | This is a sub-agent error. Reset the task and add explicit boundaries to spec.md. |
| Operator can't find worktrees | Run `git worktree list` from repo/ to see all worktrees. Check task folder structure. |
| "Branch already exists" error | The sub-branch name is taken. Either delete the old branch or use a different task name. |
| Merge conflicts during accept | Resolve in worktree first: `git rebase feature/K-123_main`, then retry accept. |
| Sub-agent exits without results.md | Check if sub-agent crashed. Look at last commits. May need to manually write results or reset. |
| Plan.md out of sync | Run `operator status` to get current state. Manually update plan.md if needed. |
| Sub-agent hangs (inline/forked mode) | Check for interactive prompts (npm install confirmations, etc.). Use `--yes` flags. |
| Python tools not found | Ensure Python 3 is installed. Tools are in `.claude/skills/worktree-operator/tools/`. |

### Debugging Tips

**Check skill loading:**
```
> What worktree skills do you have?
```

**View workspace state:**
```bash
# See all worktrees
cd repo && git worktree list

# Check task folder contents
ls -la task-*/

# View git branch structure
git log --oneline --graph --all | head -30
```

**Manual recovery:**
```bash
# If worktree is corrupted, remove and recreate
cd repo
git worktree remove ../task-broken/worktree --force
git worktree add ../task-broken/worktree -b feature/K-123/task-name feature/K-123_main

# If sub-branch is ahead of main but not merged
cd task-name/worktree
git log feature/K-123_main..HEAD  # see commits
git diff feature/K-123_main..HEAD  # see changes
```

[Back to Top](#table-of-contents)

---

## Quick Reference

### Initialize Workspace
```bash
mkdir myworkspace && cd myworkspace
git clone <repo-url> repo
cd repo && git switch feature/K-123_feature_name && cd ..
touch plan.md review-notes.md
```

### Create Task
```bash
./task-create.sh ./myworkspace K-123 fix-logging feature/K-123_feature_name
```

### Spawn Sub-Agent (Inline Mode)
```bash
claude --dangerously-skip-permissions \
    -p "You are a sub-agent. Task folder: task-fix-logging/.
        Read spec.md, implement in worktree/, commit, write results.md, exit."
```

### Review Task
```bash
cd myworkspace/repo
git diff feature/K-123_feature_name..feature/K-123/fix-logging
cat ../task-fix-logging/results.md
```

### Accept Task
```bash
./task-accept.sh ./myworkspace K-123 fix-logging feature/K-123_feature_name
```

### Iterate Task
```bash
# Write feedback
echo "Fix X, Y, Z" >> myworkspace/task-fix-logging/feedback.md
# Re-spawn sub-agent on same worktree
```

### Reset Task
```bash
./task-reset.sh ./myworkspace fix-logging feature/K-123_feature_name
```

### Sync All Worktrees
```bash
for dir in myworkspace/task-*/worktree; do
    cd "$dir" && git fetch origin && git rebase feature/K-123_feature_name && cd -
done
```

### Check Status
```bash
./task-status.sh ./myworkspace feature/K-123_feature_name
```

[Back to Top](#table-of-contents)

---

## Troubleshooting

For comprehensive troubleshooting guidance, including:

- **Error Code Reference** - All error codes with symptoms, causes, and recovery options
- **Common Issues and Solutions** - Step-by-step solutions for frequent problems
- **Recovery Procedures** - How to recover from conflicts, failed accepts, stuck locks, etc.
- **Debugging Tips** - Commands and techniques for diagnosing issues

See the dedicated **[Troubleshooting Guide](skills/worktree-operator/reference/troubleshooting.md)**.

### Quick Diagnostic Commands

```bash
# List all error codes
python3 tools/errors.py list

# Diagnose specific error
python3 tools/errors.py diagnose <error_code>

# Check sub-agent health
python3 tools/health_check.py health <task_name>

# Check workspace lock status
python3 tools/locking.py status

# Detect conflicts
python3 tools/conflict_resolver.py detect <worktree_path>
```

[Back to Top](#table-of-contents)
