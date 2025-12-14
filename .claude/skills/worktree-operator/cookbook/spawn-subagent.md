# Cookbook: Spawn Sub-Agent

## Purpose
Launch a sub-agent to work on a task in its dedicated worktree.

## When to Use
- User says "operator spawn {name}" or "operator spawn inline {name}"
- User says "operator spawn forked {name}"
- User says "operator spawn interactive {name}"
- After task is created and spec.md is complete
- When re-running after iteration feedback

## Prerequisites
- Task folder exists with spec.md
- Worktree exists and is on correct branch
- spec.md has sufficient detail for sub-agent

## Execution Modes

### Inline Mode (Default)
**Command:** `operator spawn {name}` or `operator spawn inline {name}`

- Sub-agent runs autonomously **in current session**
- Consumes tokens in operator's context
- No interactive questions
- Reads spec.md → works → writes results.md → exits
- Best for: small tasks, quick fixes

### Forked Mode
**Command:** `operator spawn forked {name}`

- Sub-agent runs autonomously **in new terminal window**
- Does NOT consume tokens in operator's session
- Uses `--dangerously-skip-permissions` flag
- Operator can continue working or monitor progress
- Best for: larger tasks, parallel work, token-heavy implementations

### Interactive Mode
**Command:** `operator spawn interactive {name}`

- Sub-agent runs **in new terminal window**
- Can ask clarifying questions and interact with user
- Does NOT use `--dangerously-skip-permissions` flag
- Best for: complex tasks, unclear requirements

## Steps

### 1. Verify Task Readiness

```python
from pathlib import Path

task_dir = Path(f"task-{task_name}")
worktree = task_dir / "worktree"
spec = task_dir / "spec.md"

# Check existence
assert task_dir.exists(), f"Task folder not found: {task_dir}"
assert worktree.exists(), f"Worktree not found: {worktree}"
assert spec.exists(), f"Spec not found: {spec}"

# Check spec has content (not just template)
spec_content = spec.read_text()
assert "REQUIREMENT" not in spec_content, "Spec still has template placeholders"
assert len(spec_content) > 200, "Spec seems too short"
```

### 2. Determine Mode

Ask user or infer from context:

```
Task '{task_name}' is ready to spawn.

Execution mode:
1. Inline (default - small tasks, consumes session tokens)
2. Forked (larger tasks, runs in new terminal, headless)
3. Interactive (complex tasks, runs in new terminal, allows questions)

Which mode? [1/2/3]:
```

**Default recommendations:**
- Small fixes, quick changes → Inline (1)
- Feature implementation, refactoring, tests → Forked (2)
- Unclear specs, needs discussion → Interactive (3)

### 3. Build Sub-Agent Prompt

```python
workspace = Path(".").resolve()
task_folder = workspace / f"task-{task_name}"
worktree_path = task_folder / "worktree"

# Check if this is an iteration (feedback exists)
feedback_path = task_folder / "feedback.md"
is_iteration = feedback_path.exists() and "No feedback yet" not in feedback_path.read_text()

if is_iteration:
    iteration_instruction = """
IMPORTANT: This is an iteration. Previous work was reviewed and feedback was provided.
Read feedback.md FIRST to understand what needs to be fixed or improved.
Build upon your previous commits, don't start over unless feedback says to."""
else:
    iteration_instruction = ""

prompt = f'''You are a sub-agent working on task '{task_name}'.

WORKSPACE CONTEXT:
- Task folder: {task_folder}
- Your worktree: {worktree_path}
- You ONLY work in the worktree directory

{iteration_instruction}

INSTRUCTIONS:
1. Read {task_folder}/spec.md to understand your task
2. {"Read " + str(task_folder) + "/feedback.md for iteration feedback" if is_iteration else "Check if feedback.md has any notes"}
3. Work ONLY in {worktree_path}
4. Make changes, run tests, commit with clear messages
5. Write {task_folder}/results.md summarizing your work
6. Exit when complete

COMMIT MESSAGE FORMAT:
{ticket}: Brief description of change

RESULTS.MD MUST INCLUDE:
- Summary of what was done
- Files modified/created
- Test results
- Any risks or concerns
- List of commits made

RESTRICTIONS:
- Do NOT modify files outside {worktree_path}
- Do NOT merge branches
- Do NOT push to remote (operator will do this)
- Do NOT modify plan.md or review-notes.md

BEGIN WORK NOW.'''
```

### 4. Execute Spawn

#### Inline Mode (Default)

Runs in current session (consumes tokens):

```bash
# Using Claude CLI in current session
claude --dangerously-skip-permissions -p "{prompt}"
```

#### Forked Mode (Recommended for larger tasks)

Runs in new terminal window (does NOT consume session tokens):

```python
from tools.fork_terminal import spawn_forked_subagent

result = spawn_forked_subagent(
    task_name="fix-logging",
    ticket="K-123",
    workspace_path=".",
    model="opus",  # or "sonnet", "haiku"
    iteration=1
)

if result["success"]:
    print(f"✓ Sub-agent spawned in forked terminal")
    print(f"  Worktree: {result['worktree']}")
else:
    print(f"✗ Spawn failed: {result['error']}")
```

Or via command line:

```bash
# macOS - opens new Terminal window
python3 tools/fork_terminal.py --spawn {task_name} {ticket} {workspace} {model}

# Example
python3 tools/fork_terminal.py --spawn fix-logging K-123 . opus
```

#### Interactive Mode

Opens new terminal for interactive session (user can interact):

```bash
# Open new terminal and run claude interactively (no -p flag)
# On macOS:
osascript -e 'tell app "Terminal" to do script "cd {worktree_path} && claude"'

# Then manually provide the task context in the new terminal
```

### 5. Update Status

Update plan.md task status:
```markdown
### X. {task_name}
- Status: IN_PROGRESS
- Branch: feature/{ticket}/{task_name}
- Spawned: {timestamp}
- Mode: {inline|forked|interactive}
```

### 6. Report Spawn

```
✓ Sub-agent spawned for '{task_name}'

Mode: {inline|forked|interactive}
Worktree: {worktree_path}
Branch: {branch}

{if inline}
Sub-agent is running in this session.
Wait for completion, then review output.
{/if}

{if forked}
Sub-agent is running in a NEW TERMINAL WINDOW.
Uses --dangerously-skip-permissions (headless mode).
You can continue working here or switch to monitor.
Run "operator review {task_name}" when complete.
{/if}

{if interactive}
Sub-agent terminal opened for interactive session.
You can interact with the sub-agent in the new terminal.
Provide task context and guidance as needed.
{/if}
```

## Sub-Agent Prompt Template

Full template for copy/paste:

```
You are a sub-agent working on task '{TASK_NAME}'.

WORKSPACE CONTEXT:
- Task folder: {WORKSPACE}/task-{TASK_NAME}
- Your worktree: {WORKSPACE}/task-{TASK_NAME}/worktree
- Main branch: {MAIN_BRANCH}
- Your branch: feature/{TICKET}/{TASK_NAME}

INSTRUCTIONS:
1. Read spec.md to understand your task requirements
2. Check feedback.md for any iteration feedback
3. Work in the worktree directory ONLY
4. Edit files, run tests, verify your changes
5. Commit changes with clear, descriptive messages
6. Write results.md summarizing everything you did
7. Exit when the task is complete

COMMIT MESSAGE FORMAT:
Use format: "{TICKET}: Brief description"
Example: "K-123: Add structured logging to payment service"

RESULTS.MD REQUIREMENTS:
Your results.md must include:
- Summary (2-3 sentences of what was accomplished)
- Changes Made (detailed list)
- Files Modified (with brief description of each)
- Tests (what tests exist, pass/fail status)
- Risks/Concerns (anything the reviewer should know)
- Commits (list of commit hashes and messages)

RESTRICTIONS:
- Only modify files in your worktree
- Do not merge or rebase branches
- Do not push to remote
- Do not touch plan.md or review-notes.md
- Do not work on other tasks

If you encounter blockers or need clarification, document them in results.md under a "Blockers/Questions" section.

START WORKING NOW.
```

## Monitoring Progress

For inline and forked modes, check progress by:

```bash
# Check for commits
cd task-{name}/worktree
git log --oneline -5

# Check for results
cat ../results.md

# Check uncommitted changes
git status
```

## Error Handling

### Spec incomplete
```
Spec.md appears incomplete (found template placeholders).

Please complete the specification before spawning:
  - Fill in all {PLACEHOLDER} values
  - Remove template instructions
  - Ensure acceptance criteria are specific
```

### Worktree missing
```
Worktree not found for task '{name}'.

The task folder exists but worktree is missing.
Options:
1. Recreate task: operator create task {name}
2. Check git worktree list for issues
```

### Previous sub-agent still running
```
A sub-agent may still be running on this task.

Check:
- Is there an active Claude session for this task?
- Are there uncommitted changes in the worktree?

Options:
1. Wait for current sub-agent to complete
2. Kill existing session and spawn new one
```

## Mode Summary

| Mode | Command | Terminal | Tokens | Headless | Best For |
|------|---------|----------|--------|----------|----------|
| Inline | `spawn {name}` | Current | Yes | Yes | Small tasks |
| Forked | `spawn forked {name}` | New | No | Yes | Large tasks |
| Interactive | `spawn interactive {name}` | New | No | No | Complex tasks |

## Checklist

- [ ] Task folder exists
- [ ] Worktree exists and is clean
- [ ] spec.md is complete (no placeholders)
- [ ] Execution mode determined
- [ ] Prompt built with correct paths
- [ ] Sub-agent spawned
- [ ] plan.md status updated
- [ ] Spawn reported to user
