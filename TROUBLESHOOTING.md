# Troubleshooting Guide

This guide covers common issues, error recovery, and debugging procedures for the multi-agent worktree system.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Error Code Reference](#error-code-reference)
3. [Common Issues and Solutions](#common-issues-and-solutions)
4. [Recovery Procedures](#recovery-procedures)
5. [Debugging Tips](#debugging-tips)

---

## Quick Reference

### Diagnostic Commands

```bash
# Check all task statuses in workspace
python3 tools/health_check.py list [workspace]

# Check specific task health
python3 tools/health_check.py health <task_name> [workspace]

# List all known error codes
python3 tools/errors.py list

# Get diagnostic info for specific error
python3 tools/errors.py diagnose <error_code>

# Check workspace lock status
python3 tools/locking.py status [workspace]

# Detect git conflicts in worktree
python3 tools/conflict_resolver.py detect <worktree_path>

# View all worktrees
cd repo && git worktree list

# Check repository status
cd repo && git status
```

### Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Workspace locked | `python3 tools/locking.py status` then `unlock` if stale |
| Rebase conflicts | `python3 tools/conflict_resolver.py detect <worktree>` |
| Sub-agent stuck | Check terminal, or `operator reset <task>` |
| Worktree missing | `git worktree list` then recreate task |
| Tests failing | Run tests manually in worktree to see output |

---

## Error Code Reference

All error codes from the operator tools with descriptions and recovery hints.

### Repository/Workspace Errors

#### REPO_EXISTS

**Symptom:** Cannot initialize workspace - repo folder exists

**Causes:**
- Previous initialization was interrupted
- Workspace already set up

**Diagnosis:** Check if the repo folder contains a valid git repository

**Recovery Options:**
```bash
# Remove existing and reinitialize
rm -rf repo/

# Or continue with existing
operator status
```

---

#### REPO_NOT_FOUND

**Symptom:** Repository not found at specified path

**Causes:**
- Workspace not initialized
- Wrong directory

**Recovery Options:**
```bash
# Initialize workspace
operator init <repo_url> <branch>

# Check current directory
pwd
ls -la
```

---

#### WORKSPACE_NOT_FOUND

**Symptom:** Workspace directory does not exist

**Causes:**
- Wrong path specified
- Directory was deleted

**Recovery Options:**
```bash
# Create directory
mkdir -p <workspace_path>

# Use a different workspace path
```

---

### Task Errors

#### TASK_EXISTS

**Symptom:** Task folder already exists

**Causes:**
- Task with this name already created
- Previous task creation interrupted

**Recovery Options:**
```bash
# Use a different task name
operator create task <new-name>

# Remove existing task folder
rm -rf task-<name>/

# Check existing task status
operator status <task_name>
```

---

#### TASK_NOT_FOUND

**Symptom:** Task folder not found

**Causes:**
- Task doesn't exist
- Task was already removed

**Recovery Options:**
```bash
# Create the task
operator create task <task_name>

# List existing tasks
operator status
```

---

#### WORKTREE_NOT_FOUND

**Symptom:** Task exists but worktree is missing

**Causes:**
- Worktree was manually deleted
- Git prune removed it
- Creation was interrupted

**Diagnosis:** Run `git worktree list` to see all worktrees

**Recovery Options:**
```bash
# Recreate task
operator reset <task_name>

# Check worktrees
cd repo && git worktree list

# Manual recreation
cd repo
git worktree add "../task-<name>/worktree" -b "feature/TICKET/<task>" <main_branch>
```

---

#### SPEC_NOT_FOUND

**Symptom:** spec.md file missing in task folder

**Causes:**
- Task folder created but spec not written
- File was deleted

**Recovery Options:**
```bash
# Create spec file manually
touch task-<name>/spec.md

# Recreate the task
operator create task <task_name>
```

---

### Git Errors

#### BRANCH_EXISTS

**Symptom:** Branch already exists

**Causes:**
- Previous task with same name
- Branch created manually

**Recovery Options:**
```bash
# Use different task name

# Delete existing branch
git branch -D <branch_name>

# Switch to existing branch
git switch <branch_name>
```

---

#### CLONE_FAILED

**Symptom:** Git clone failed

**Causes:**
- Invalid repository URL
- Network issues
- No access to repository

**Recovery Options:**
```bash
# Verify repository URL
git ls-remote <repo_url>

# Check network connection
ping github.com

# Try manual clone
git clone <repo_url>
```

---

#### CHECKOUT_FAILED

**Symptom:** Git checkout/switch failed

**Causes:**
- Branch doesn't exist
- Uncommitted changes blocking checkout

**Recovery Options:**
```bash
# Create the branch
git switch -c <branch_name>

# Check available branches
git branch -a

# Fetch latest
git fetch origin

# Stash changes if needed
git stash
```

---

#### REBASE_CONFLICT

**Symptom:** Sync or accept fails with conflicts

**Causes:**
- Main branch changed files that sub-agent also modified

**Diagnosis:** Check `git status` in the worktree for conflict markers

**Recovery Options:**
```bash
# Resolve conflicts manually in worktree
cd task-<name>/worktree

# View conflicted files
git status
git diff

# After resolving conflicts
git add .
git rebase --continue

# Or abort and try again
git rebase --abort

# Or reset the task completely
operator reset <task_name>
```

See [How to Manually Resolve Conflicts](#how-to-manually-resolve-conflicts) for detailed steps.

---

#### MERGE_CONFLICT

**Symptom:** Merge conflict during accept

**Causes:**
- Changes in main branch conflict with task changes

**Recovery Options:**
```bash
# Resolve conflicts in files
git status

# After resolving
git add .
git commit

# Or abort
git merge --abort
```

---

#### PUSH_FAILED

**Symptom:** Git push failed

**Causes:**
- Remote branch has new commits
- No access to remote
- Branch protection rules

**Recovery Options:**
```bash
# Fetch and rebase first
git fetch && git rebase origin/main

# Check remote configuration
git remote -v

# Force push (use with caution)
git push --force-with-lease origin <branch>
```

---

#### WORKTREE_CREATE_FAILED

**Symptom:** Failed to create git worktree

**Causes:**
- Branch already exists and checked out elsewhere
- Invalid path

**Recovery Options:**
```bash
# Check if branch already exists
git branch -a

# Remove existing worktree using that branch
git worktree remove <path>

# Manual creation
git worktree add <path> -b <branch>
```

---

### Test Errors

#### TESTS_FAILED

**Symptom:** Accept fails at test verification

**Causes:**
- Code changes broke existing tests
- Test environment issues

**Diagnosis:** Run tests manually in the worktree to see full output

**Recovery Options:**
```bash
# Run tests manually
cd task-<name>/worktree
npm test  # or pytest, etc.

# Check test output for specific failures
# Review recent changes for potential issues
```

---

#### TEST_TIMEOUT

**Symptom:** Tests timed out

**Causes:**
- Tests take too long
- Infinite loop in tests
- Hanging test

**Recovery Options:**
```bash
# Increase timeout in workspace.json

# Run tests manually to investigate
cd task-<name>/worktree
npm test

# Check for infinite loops or hanging tests
```

---

#### TEST_DETECTION_FAILED

**Symptom:** Could not auto-detect test command

**Causes:**
- No recognized test framework files found

**Recovery Options:**
```bash
# Set test_command in workspace.json
# Pass test_command parameter explicitly

# Supported frameworks: npm, pytest, go test, cargo test, etc.
```

---

### Lock Errors

#### LOCK_HELD

**Symptom:** Operations fail with 'workspace locked'

**Causes:**
- Another operation is running
- Previous operation crashed

**Diagnosis:** Check `.workspace.lock.info` for holder details

**Recovery Options:**
```bash
# Check lock status
python3 tools/locking.py status

# Wait for other operation to complete

# Check if process is still running
ps aux | grep <pid>

# Force unlock if stale
python3 tools/locking.py unlock
```

---

#### LOCK_TIMEOUT

**Symptom:** Timeout waiting for workspace lock

**Causes:**
- Another operation taking too long
- Stuck operation

**Recovery Options:**
```bash
# Check what operation is running
python3 tools/locking.py status

# Wait and retry

# Force unlock if stuck
python3 tools/locking.py unlock
```

---

### Sub-agent Errors

#### SUBAGENT_TIMEOUT

**Symptom:** Sub-agent appears stuck or unresponsive

**Causes:**
- Long-running operation
- Waiting for user input
- Crashed

**Diagnosis:** Check the sub-agent terminal window for errors

**Recovery Options:**
```bash
# Check sub-agent status
operator health <task_name>
python3 tools/health_check.py health <task_name>

# Check the terminal window running the sub-agent

# Reset and re-spawn
operator reset <task_name>
```

---

#### SUBAGENT_SPAWN_FAILED

**Symptom:** Failed to spawn sub-agent

**Causes:**
- Claude not installed
- Task folder missing spec.md
- Permission issues

**Recovery Options:**
```bash
# Check if Claude is installed
claude --version

# Verify task folder exists and has spec.md
ls task-<name>/
cat task-<name>/spec.md

# Try spawning manually
cd task-<name>/worktree
claude -p "Read ../spec.md and implement the task"
```

---

#### TERMINAL_NOT_SUPPORTED

**Symptom:** Platform not supported for terminal forking

**Causes:**
- Unsupported operating system

**Recovery Options:**
```bash
# Use inline mode instead
operator spawn <task>

# Open a terminal manually and run sub-agent command
```

---

#### NO_TERMINAL_FOUND

**Symptom:** No supported terminal emulator found (Linux)

**Causes:**
- Missing terminal emulator

**Recovery Options:**
```bash
# Install a supported terminal
sudo apt install gnome-terminal  # or konsole, xterm

# Use inline mode
operator spawn <task>
```

---

### Validation Errors

#### INVALID_INPUT

**Symptom:** Invalid input for a field

**Causes:**
- Incorrect format
- Invalid characters

**Recovery Options:**
- Check the field format requirements
- Use valid examples provided in the error message

---

## Common Issues and Solutions

### Sub-agent Appears Stuck/Hung

**Symptoms:**
- No progress updates for extended period
- Terminal appears frozen
- No new commits in worktree

**Solution:**

1. Check sub-agent health:
   ```bash
   python3 tools/health_check.py health <task_name>
   ```

2. Look at the sub-agent terminal window for:
   - Error messages
   - Prompts waiting for input
   - Stack traces

3. Check if process is running:
   ```bash
   # Get PID from health check
   ps aux | grep claude
   ```

4. If stuck, reset and re-spawn:
   ```bash
   operator reset <task_name>
   operator spawn <task_name>
   ```

---

### Rebase Conflicts During Accept

**Symptoms:**
- Accept operation fails
- Git reports conflict markers
- Files contain `<<<<<<<` markers

**Solution:**

1. Detect conflicts:
   ```bash
   python3 tools/conflict_resolver.py detect task-<name>/worktree
   ```

2. View conflicted files:
   ```bash
   cd task-<name>/worktree
   git status
   ```

3. Resolve conflicts (see [How to Manually Resolve Conflicts](#how-to-manually-resolve-conflicts))

4. Continue the rebase:
   ```bash
   git add .
   git rebase --continue
   ```

5. Retry accept:
   ```bash
   operator accept <task_name>
   ```

---

### Merge Conflicts During Sync

**Symptoms:**
- Sync operation fails
- Worktree has conflict markers

**Solution:**

1. Check conflict status:
   ```bash
   cd task-<name>/worktree
   git status
   ```

2. Choose resolution strategy:
   ```bash
   # Keep your changes
   python3 tools/conflict_resolver.py resolve-all <worktree_path> ours

   # Keep incoming changes
   python3 tools/conflict_resolver.py resolve-all <worktree_path> theirs

   # Or resolve manually
   ```

3. Continue operation:
   ```bash
   python3 tools/conflict_resolver.py continue <worktree_path>
   ```

---

### Tests Failing After Rebase

**Symptoms:**
- Tests pass before rebase
- Tests fail after rebase
- Accept operation fails at test stage

**Solution:**

1. Run tests manually to see output:
   ```bash
   cd task-<name>/worktree
   npm test  # or pytest, etc.
   ```

2. Check what changed in main branch:
   ```bash
   git log --oneline HEAD~5..HEAD
   git diff HEAD~1
   ```

3. Fix test failures in worktree

4. Commit fixes:
   ```bash
   git add .
   git commit -m "Fix tests after rebase"
   ```

5. Retry accept

---

### Worktree in Dirty State

**Symptoms:**
- Uncommitted changes in worktree
- Operations refuse to proceed
- Git status shows modified files

**Solution:**

1. Check status:
   ```bash
   cd task-<name>/worktree
   git status
   ```

2. Decide what to do with changes:
   ```bash
   # Commit changes
   git add .
   git commit -m "WIP: uncommitted work"

   # Or stash changes
   git stash

   # Or discard changes
   git checkout -- .
   git clean -fd
   ```

---

### Lock File Stuck

**Symptoms:**
- Operations fail with "workspace locked"
- No other operations running
- Previous operation may have crashed

**Solution:**

1. Check lock status:
   ```bash
   python3 tools/locking.py status
   ```

2. Check if holding process is running:
   ```bash
   # Look at PID in status output
   ps aux | grep <pid>
   ```

3. If process not running, force unlock:
   ```bash
   python3 tools/locking.py unlock
   # Type 'yes' to confirm
   ```

4. If process IS running, wait for it to complete or terminate it

---

### Task Folder Cleanup Issues

**Symptoms:**
- Worktree can't be removed
- Branch deletion fails
- Orphaned task folders

**Solution:**

1. List all worktrees:
   ```bash
   cd repo
   git worktree list
   ```

2. Force remove problematic worktree:
   ```bash
   git worktree remove task-<name>/worktree --force
   ```

3. Prune stale worktree references:
   ```bash
   git worktree prune
   ```

4. Delete branch:
   ```bash
   git branch -D feature/TICKET/<task_name>
   ```

5. Clean up task folder:
   ```bash
   rm -rf task-<name>/
   ```

---

### Dependency Blocking Spawn

**Symptoms:**
- Task depends on another task
- Cannot spawn sub-agent
- Operator reports dependency issue

**Solution:**

1. Check plan.md for dependencies

2. Complete dependent tasks first:
   ```bash
   operator accept <dependency_task>
   ```

3. Sync remaining worktrees:
   ```bash
   operator sync all
   ```

4. Then spawn the blocked task:
   ```bash
   operator spawn <task_name>
   ```

---

## Recovery Procedures

### How to Manually Resolve Conflicts

1. **Identify conflicted files:**
   ```bash
   cd task-<name>/worktree
   git status
   # Files marked as "both modified" have conflicts
   ```

2. **View conflict details:**
   ```bash
   python3 tools/conflict_resolver.py detect .
   ```

3. **Open conflicted files and look for markers:**
   ```
   <<<<<<< HEAD
   Your changes (current branch)
   =======
   Incoming changes (from rebase/merge)
   >>>>>>> commit-sha
   ```

4. **Edit files to resolve:**
   - Keep the code you want
   - Remove conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
   - Ensure code is syntactically correct

5. **Stage resolved files:**
   ```bash
   git add <file>
   ```

6. **Continue the operation:**
   ```bash
   # For rebase
   git rebase --continue

   # For merge
   git commit
   ```

---

### How to Recover from Failed Accept

1. **Check current state:**
   ```bash
   cd task-<name>/worktree
   git status
   ```

2. **If rebase in progress:**
   ```bash
   # Abort and start fresh
   git rebase --abort

   # Or continue after fixing issues
   git rebase --continue
   ```

3. **If merge in progress:**
   ```bash
   # Abort
   git merge --abort
   ```

4. **Verify worktree is clean:**
   ```bash
   git status
   # Should show "nothing to commit"
   ```

5. **Retry accept:**
   ```bash
   operator accept <task_name>
   ```

---

### How to Force Unlock Workspace

**Warning:** Only do this if you're certain no operation is running.

1. **Check lock status:**
   ```bash
   python3 tools/locking.py status
   ```

2. **Verify holding process:**
   ```bash
   # Check if PID is running
   ps aux | grep <pid>
   ```

3. **Force unlock:**
   ```bash
   python3 tools/locking.py unlock
   # Type 'yes' to confirm
   ```

4. **Verify unlocked:**
   ```bash
   python3 tools/locking.py status
   # Should show "locked": false
   ```

---

### How to Reset a Stuck Task

1. **Check task status:**
   ```bash
   python3 tools/health_check.py status <task_name>
   ```

2. **Reset the task:**
   ```bash
   operator reset <task_name>
   ```

3. **If reset fails, manual cleanup:**
   ```bash
   cd repo
   git worktree remove ../task-<name>/worktree --force
   git worktree prune
   ```

4. **Recreate the task:**
   ```bash
   operator create task <task_name>
   ```

---

### How to Check Sub-agent Health

1. **Get status:**
   ```bash
   python3 tools/health_check.py health <task_name>
   ```

2. **Check output for:**
   - `status`: "running", "completed", "failed", or "starting"
   - `healthy`: true/false
   - `time_since_heartbeat`: seconds since last update
   - `progress`: current activity

3. **If unhealthy:**
   - Check sub-agent terminal for errors
   - Look at recent commits in worktree
   - Check `task-<name>/results.md` for output

---

### How to Abort and Restart Operations

#### Abort a Rebase:
```bash
cd task-<name>/worktree
git rebase --abort
```

#### Abort a Merge:
```bash
cd task-<name>/worktree
git merge --abort
```

#### Abort Any Git Operation:
```bash
python3 tools/conflict_resolver.py abort <worktree_path>
```

#### Restart a Task from Scratch:
```bash
# Reset worktree to main branch state
cd task-<name>/worktree
git fetch origin
git reset --hard <main_branch>
git clean -fd

# Or use operator reset
operator reset <task_name>
```

---

## Debugging Tips

### Check Skill Loading

```
> What worktree skills do you have?
```

Claude should recognize operator and sub-agent skills.

### View Workspace State

```bash
# See all worktrees
cd repo && git worktree list

# Check task folder contents
ls -la task-*/

# View git branch structure
git log --oneline --graph --all | head -30
```

### View Detailed Logs

The tools use Python logging. Check stderr output for detailed logs:

```bash
python3 tools/health_check.py status <task> 2>&1 | less
```

### Manual Recovery

```bash
# If worktree is corrupted, remove and recreate
cd repo
git worktree remove ../task-broken/worktree --force
git worktree add ../task-broken/worktree -b feature/TICKET/task-name feature/TICKET_main

# If sub-branch is ahead of main but not merged
cd task-name/worktree
git log feature/TICKET_main..HEAD  # see commits
git diff feature/TICKET_main..HEAD  # see changes
```

### Inspect Lock Info

```bash
cat .workspace.lock.info
```

Shows:
- `pid`: Process holding the lock
- `operation`: What operation is running
- `acquired_at`: When lock was acquired
- `hostname`: Which machine holds the lock

### Check Git State

```bash
cd task-<name>/worktree

# Check current branch
git branch --show-current

# Check if rebase in progress
ls .git/rebase-merge 2>/dev/null && echo "Rebase in progress"

# Check if merge in progress
ls .git/MERGE_HEAD 2>/dev/null && echo "Merge in progress"

# Check for uncommitted changes
git status --porcelain
```

### Test Commands Before Documenting

When troubleshooting, always verify commands work:

```bash
# Test error diagnosis
python3 tools/errors.py diagnose REBASE_CONFLICT

# Test health check
python3 tools/health_check.py list

# Test conflict detection
python3 tools/conflict_resolver.py detect <worktree_path>
```

---

## Getting Help

- **Documentation:** See [README.md](README.md) for workflow documentation
- **Issue Tracker:** Report issues at the project repository
- **Error Codes:** Run `python3 tools/errors.py list` for all error codes
- **Diagnostics:** Run `python3 tools/errors.py diagnose <code>` for specific errors
