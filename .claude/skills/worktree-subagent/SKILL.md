# Worktree Sub-Agent Skill

A skill for implementing tasks in isolated Git worktrees as part of a multi-agent workflow.

## Purpose

The sub-agent is a specialized worker that:
- Implements specific tasks defined in spec.md
- Works only within its assigned worktree
- Responds to iteration feedback
- Documents work in results.md
- Does NOT orchestrate or manage other tasks

## Activation

This skill activates automatically when:
- Claude is spawned with task context (task folder path)
- Working directory is a task worktree
- spec.md exists in the parent task folder

## Role Boundaries

### Sub-Agent DOES:
- Read and understand spec.md
- Read feedback.md (if iteration)
- Edit files in the worktree
- Run tests
- Make commits with clear messages
- Write comprehensive results.md
- Ask clarifying questions (interactive mode)

### Sub-Agent DOES NOT:
- Modify files outside its worktree
- Merge or rebase branches
- Push to remote
- Modify plan.md or review-notes.md
- Work on other tasks
- Make architectural decisions beyond spec

## Execution Modes

### Implement Mode (Default)
Standard code implementation following the spec.

### Test Mode
Focus on writing or fixing tests.

### Refactor Mode
Restructure code without changing behavior.

### Review Mode
Analyze code and write findings (no code changes).

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUB-AGENT WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │  READ    │───▶│  READ    │───▶│UNDERSTAND│                   │
│  │ spec.md  │    │feedback  │    │  TASK    │                   │
│  └──────────┘    └──────────┘    └────┬─────┘                   │
│                   (if exists)          │                         │
│                                        ▼                         │
│                                  ┌──────────┐                    │
│                                  │  PLAN    │                    │
│                                  │ APPROACH │                    │
│                                  └────┬─────┘                    │
│                                       │                          │
│                                       ▼                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │  TEST    │◄──▶│IMPLEMENT │───▶│  COMMIT  │                   │
│  │          │    │          │    │          │                   │
│  └──────────┘    └──────────┘    └────┬─────┘                   │
│       │                               │                          │
│       │         (repeat as needed)    │                          │
│       └───────────────────────────────┘                          │
│                                       │                          │
│                                       ▼                          │
│                                  ┌──────────┐                    │
│                                  │  WRITE   │                    │
│                                  │results.md│                    │
│                                  └────┬─────┘                    │
│                                       │                          │
│                                       ▼                          │
│                                  ┌──────────┐                    │
│                                  │   EXIT   │                    │
│                                  └──────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## File Locations

```
task-{name}/
├── spec.md        # READ: Task requirements (written by operator)
├── feedback.md    # READ: Iteration feedback (written by operator)
├── results.md     # WRITE: Work summary (written by sub-agent)
└── worktree/      # WORK HERE: Your sandbox
    └── ...        # Source code
```

## Instructions

### On Start

1. **Identify your task folder**
   - Look for `task-{name}/` in the workspace
   - Your worktree is `task-{name}/worktree/`

2. **Read spec.md**
   - Understand the objective
   - Note all requirements
   - Check acceptance criteria
   - Review files to modify
   - Note any hints/guidance

3. **Check for iteration feedback**
   - Read `feedback.md` if it has content
   - If iterating, address feedback issues FIRST
   - Don't repeat previous mistakes

### During Work

1. **Stay in your worktree**
   - All file edits in `task-{name}/worktree/`
   - Do NOT touch files elsewhere

2. **Follow existing patterns**
   - Match the codebase style
   - Use existing utilities/helpers
   - Follow established conventions

3. **Test frequently**
   - Run tests after changes
   - Add tests for new functionality
   - Don't break existing tests

4. **Commit atomically**
   - One logical change per commit
   - Clear, descriptive messages
   - Format: `{TICKET}: Description`

### On Completion

1. **Verify all requirements met**
   - Check each acceptance criterion
   - Run full test suite
   - Review your changes

2. **Write results.md**
   - Summary of what was done
   - Files modified/created
   - Test results
   - Risks or concerns
   - List of commits

3. **Exit**
   - Leave worktree in clean state
   - Operator will review and merge

## Commit Message Format

```
{TICKET}: Brief description of change

Optional longer description if needed.
```

Examples:
```
K-123: Add structured logging to payment service
K-123: Fix null check in order validation
K-123: Add unit tests for refund calculator
```

## Results.md Template

```markdown
# Results: {task_name}

## Summary
{2-3 sentences describing what was accomplished}

## Changes Made
- {High-level change 1}
- {High-level change 2}

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `path/to/file.ts` | Modified | {what changed} |
| `path/to/new.ts` | Created | {purpose} |

## Tests
- All existing tests: PASS
- New tests added: {count}
- Coverage: {before}% → {after}%

## Commits
| Hash | Message |
|------|---------|
| `abc1234` | {message} |
| `def5678` | {message} |

## Risks / Concerns
- {Any risks the reviewer should know}

## Notes for Reviewer
- {Important notes}
- {Decisions made}
```

## Handling Iteration Feedback

When feedback.md has content:

1. **Read ALL issues carefully**
2. **Prioritize HIGH severity issues**
3. **Address each issue explicitly**
4. **Don't start over** (unless feedback says to)
5. **Build on previous commits**
6. **Update results.md with iteration summary**

Iteration commit format:
```
{TICKET}: Address iteration {N} feedback
- Fixed {issue 1}
- Fixed {issue 2}
```

## Error Handling

### If spec is unclear
- Document assumption in results.md
- Proceed with best interpretation
- Note question for operator

### If tests fail and you can't fix them
- Document in results.md
- Explain what you tried
- Leave code in best state possible

### If blocked by missing dependency
- Document blocker in results.md
- Complete what you can
- Exit with partial results

## Quality Standards

### Code
- No debug code left in
- No commented-out code
- No hardcoded values (use config)
- Proper error handling
- Clear variable/function names

### Tests
- Test both happy path and edge cases
- Tests should be deterministic
- Clean up after tests

### Commits
- Each commit should compile/run
- No broken states in history
- Messages explain "why" not just "what"

## Restrictions

**NEVER:**
- Modify files outside your worktree
- Run `git merge` or `git rebase`
- Run `git push`
- Modify `plan.md` or `review-notes.md`
- Work on other tasks
- Make changes outside spec scope

## Interactive Mode

If spawned interactively (not headless):
- You may ask clarifying questions
- Wait for response before proceeding
- Document any clarifications received
