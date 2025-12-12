# Plan: Workflow Hardening & Improvements

## Status: IN PROGRESS
## Target: Production-Ready Multi-Agent Worktree System

---

## Overview

Following comprehensive analysis, this plan addresses all identified issues to make the multi-agent worktree system production-ready. Issues are organized by priority: Security → Reliability → Robustness → Usability.

**Analysis Summary:** 7.5/10 - Solid foundation with implementation gaps
**Estimated Total Effort:** 100-120 hours

---

## Tasks

### 1. fix-shell-injection
- Status: COMPLETED
- Priority: CRITICAL
- Dependencies: None
- Description: Fix command injection vulnerabilities in fork_terminal.py

**Problem:**
- Line 25-27: Shell command escaping only handles `\` and `"`
- Missing escapes for: `$`, backticks, `;`, newlines
- Task names and prompts can inject arbitrary commands

**Deliverables:**
- Use `shlex.quote()` for all shell arguments
- Validate task_name and ticket format (alphanumeric + hyphen only)
- Add input sanitization function
- Add unit tests for injection attempts

**Files to modify:**
- `.claude/skills/worktree-operator/tools/fork_terminal.py`

**Acceptance Criteria:**
- [ ] All shell arguments properly escaped with shlex.quote()
- [ ] Input validation rejects special characters in task names
- [ ] Unit tests cover injection attack vectors
- [ ] No subprocess calls with shell=True and user input

---

### 2. add-input-validation
- Status: COMPLETED
- Priority: CRITICAL
- Dependencies: None
- Description: Add input validation across all tools

**Problem:**
- Task names, ticket IDs, branch names not validated
- Path traversal possible in workspace paths
- No length limits on inputs

**Deliverables:**
- Create `validation.py` with validators:
  - `validate_task_name(name)` - alphanumeric, hyphens, max 50 chars
  - `validate_ticket_id(ticket)` - pattern like K-123, PROJ-456
  - `validate_branch_name(branch)` - git-safe characters
  - `validate_path(path)` - no traversal, absolute paths only
- Integrate validators into all tool functions
- Raise clear errors on validation failure

**Files to create:**
- `.claude/skills/worktree-operator/tools/validation.py`

**Files to modify:**
- `.claude/skills/worktree-operator/tools/workspace.py`
- `.claude/skills/worktree-operator/tools/task.py`
- `.claude/skills/worktree-operator/tools/git_ops.py`
- `.claude/skills/worktree-operator/tools/fork_terminal.py`

**Acceptance Criteria:**
- [ ] All public functions validate inputs before processing
- [ ] Validation errors include expected format
- [ ] Path traversal attacks blocked
- [ ] Unit tests for each validator

---

### 3. add-subagent-health-check
- Status: PENDING
- Priority: HIGH
- Dependencies: None
- Description: Implement mechanism to detect hung/crashed sub-agents

**Problem:**
- No way to know if forked sub-agent is running, stuck, or crashed
- Operator waits indefinitely for completion
- No timeout mechanism

**Deliverables:**
- Sub-agent writes `.subagent-status` file on start
- Sub-agent updates status periodically (heartbeat)
- Sub-agent writes final status on completion/error
- Operator can query status: `operator status {task_name}`
- Add timeout detection (no heartbeat in X minutes)

**Status file format:**
```json
{
  "status": "running|completed|failed",
  "started_at": "ISO timestamp",
  "last_heartbeat": "ISO timestamp",
  "progress": "Reading spec|Implementing|Testing|Writing results",
  "error": null
}
```

**Files to modify:**
- `.claude/skills/worktree-operator/tools/fork_terminal.py`
- `.claude/skills/worktree-operator/SKILL.md`
- `.claude/skills/worktree-subagent/SKILL.md`

**Files to create:**
- `.claude/skills/worktree-operator/tools/health_check.py`

**Acceptance Criteria:**
- [ ] Sub-agent creates status file on start
- [ ] Heartbeat updates every 60 seconds
- [ ] Operator can check sub-agent status
- [ ] Timeout warning after 10 minutes no heartbeat
- [ ] Status shows in `operator status` output

---

### 4. add-test-verification-post-merge
- Status: PENDING
- Priority: HIGH
- Dependencies: None
- Description: Verify tests pass after rebase and merge before completing accept

**Problem:**
- `accept_task()` merges without verifying tests pass
- Broken code can reach main branch
- No automated rollback on test failure

**Deliverables:**
- Add test runner detection (npm test, pytest, go test, cargo test)
- Run tests after rebase, abort if fail
- Run tests after merge, revert if fail
- Make test command configurable in workspace config

**Config format (workspace.json):**
```json
{
  "test_command": "npm test",
  "test_timeout": 300
}
```

**Files to modify:**
- `.claude/skills/worktree-operator/tools/task.py` (accept_task function)
- `.claude/skills/worktree-operator/cookbook/accept-task.md`

**Files to create:**
- `.claude/skills/worktree-operator/tools/test_runner.py`

**Acceptance Criteria:**
- [ ] Tests run after rebase, blocks merge if fail
- [ ] Tests run after merge, reverts if fail
- [ ] Test command auto-detected or configurable
- [ ] Clear error message on test failure with logs
- [ ] Cookbook documents test verification step

---

### 5. add-transactional-accept
- Status: PENDING
- Priority: HIGH
- Dependencies: add-test-verification-post-merge
- Description: Make accept_task() atomic with rollback on failure

**Problem:**
- Multi-step accept can leave inconsistent state
- If step 5 fails, steps 1-4 already completed
- No way to undo partial accept

**Deliverables:**
- Record initial state (branch HEADs, worktree list) before accept
- Wrap all steps in try/except
- On any failure, rollback to initial state
- Add `--dry-run` option to preview changes

**Rollback actions:**
- Reset main branch to initial HEAD
- Restore worktree if removed
- Restore sub-branch if deleted

**Files to modify:**
- `.claude/skills/worktree-operator/tools/task.py`
- `.claude/skills/worktree-operator/tools/git_ops.py`

**Acceptance Criteria:**
- [ ] Initial state recorded before any changes
- [ ] All failures trigger automatic rollback
- [ ] Rollback restores exact initial state
- [ ] `--dry-run` shows what would happen
- [ ] Transaction log written for debugging

---

### 6. fix-race-conditions
- Status: PENDING
- Priority: HIGH
- Dependencies: add-input-validation
- Description: Prevent race conditions in concurrent operations

**Problem:**
- Simultaneous task creation can create same branch twice
- Accept during sync causes inconsistent state
- No locking mechanism

**Deliverables:**
- Add file-based locking for workspace operations
- Lock acquired before: create_task, accept_task, sync_all
- Lock file: `.workspace.lock` with PID and timestamp
- Stale lock detection (process not running)

**Files to create:**
- `.claude/skills/worktree-operator/tools/locking.py`

**Files to modify:**
- `.claude/skills/worktree-operator/tools/task.py`
- `.claude/skills/worktree-operator/tools/workspace.py`

**Acceptance Criteria:**
- [ ] Concurrent create_task fails gracefully
- [ ] Lock prevents concurrent accept operations
- [ ] Stale locks auto-cleaned after 1 hour
- [ ] Lock holder info in error message
- [ ] Tests for concurrent access scenarios

---

### 7. add-comprehensive-logging
- Status: PENDING
- Priority: MEDIUM
- Dependencies: None
- Description: Replace print statements with structured logging

**Problem:**
- Only print() statements, no persistent logs
- No timestamps or operation context
- Can't audit what happened

**Deliverables:**
- Create logging configuration module
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log to file: `workspace.log` (rotating, 10MB max, 5 files)
- Structured format with: timestamp, level, operation, task, details
- Add log viewing: `operator logs [--tail N] [--level LEVEL]`

**Log format:**
```
2024-01-15T10:30:45 [INFO] accept_task: Starting acceptance for task fix-logging
2024-01-15T10:30:46 [INFO] accept_task: Rebase successful, 3 commits
2024-01-15T10:30:47 [ERROR] accept_task: Tests failed - see test.log
```

**Files to create:**
- `.claude/skills/worktree-operator/tools/logging_config.py`

**Files to modify:**
- All tools/*.py files

**Acceptance Criteria:**
- [ ] All operations logged with context
- [ ] Log file rotates at 10MB
- [ ] Error logs include stack traces
- [ ] `operator logs` command works
- [ ] No more bare print() statements

---

### 8. add-dependency-enforcement
- Status: PENDING
- Priority: MEDIUM
- Dependencies: None
- Description: Enforce task dependencies from plan.md

**Problem:**
- plan.md documents dependencies but not enforced
- Can spawn tasks in wrong order
- Manual tracking required

**Deliverables:**
- Parse dependencies from plan.md task entries
- `create_task()` warns if dependencies not COMPLETED
- `spawn_subagent()` blocks if dependencies not met
- Add `operator unblocked` to show spawnable tasks
- Add `--force` flag to override dependency check

**plan.md dependency format:**
```markdown
### 3. implement-auth
- Status: PENDING
- Dependencies: setup-database, create-user-model
```

**Files to create:**
- `.claude/skills/worktree-operator/tools/plan_parser.py`

**Files to modify:**
- `.claude/skills/worktree-operator/tools/task.py`
- `.claude/skills/worktree-operator/SKILL.md`

**Acceptance Criteria:**
- [ ] Dependencies parsed from plan.md
- [ ] Spawn blocked for tasks with unmet dependencies
- [ ] `operator unblocked` lists ready tasks
- [ ] `--force` overrides dependency check
- [ ] Clear error shows which dependencies missing

---

### 9. add-conflict-resolution-guide
- Status: PENDING
- Priority: MEDIUM
- Dependencies: None
- Description: Improve guidance when rebase conflicts occur

**Problem:**
- Conflicts detected but no resolution help
- Operator must manually resolve
- No context about conflict files

**Deliverables:**
- Show conflicted file list with conflict markers preview
- Provide resolution options:
  1. Keep ours (sub-agent changes)
  2. Keep theirs (main branch changes)
  3. Manual merge (open in editor)
  4. Abort and reset
- Add `operator resolve {task_name}` command
- Document common conflict patterns

**Files to create:**
- `.claude/skills/worktree-operator/cookbook/resolve-conflicts.md`
- `.claude/skills/worktree-operator/tools/conflict_resolver.py`

**Files to modify:**
- `.claude/skills/worktree-operator/tools/git_ops.py`
- `.claude/skills/worktree-operator/SKILL.md`

**Acceptance Criteria:**
- [ ] Conflict files listed with preview
- [ ] Resolution options presented
- [ ] Each option has clear outcome description
- [ ] `operator resolve` command works
- [ ] Cookbook documents resolution strategies

---

### 10. improve-error-messages
- Status: PENDING
- Priority: MEDIUM
- Dependencies: None
- Description: Add recovery hints to all error messages

**Problem:**
- Errors say what failed but not how to fix
- User must guess recovery steps
- No consistent error format

**Deliverables:**
- Create error class with: message, hint, recovery_options
- Update all tool functions to use new error format
- Each error includes actionable next steps
- Add `operator diagnose` for common issues

**Error format:**
```python
{
  "success": False,
  "error": "Repository folder already exists: /path/repo",
  "hint": "The workspace already has a repo. Choose an action below.",
  "recovery_options": [
    "Remove existing: rm -rf repo/",
    "Use different workspace",
    "Continue with existing: operator status"
  ]
}
```

**Files to create:**
- `.claude/skills/worktree-operator/tools/errors.py`

**Files to modify:**
- All tools/*.py files

**Acceptance Criteria:**
- [ ] All errors include hint and recovery_options
- [ ] Hints are actionable (not just "try again")
- [ ] Consistent error format across all tools
- [ ] `operator diagnose` checks common issues

---

### 11. add-decision-support
- Status: PENDING
- Priority: MEDIUM
- Dependencies: None
- Description: Help operator decide accept/iterate/reset

**Problem:**
- Operator must manually decide with no guidance
- No quality metrics to inform decision
- Inconsistent decision criteria

**Deliverables:**
- Calculate quality score based on:
  - All acceptance criteria met (from spec.md)
  - Tests passing
  - Code diff size reasonable
  - No out-of-scope changes
- Provide recommendation: ACCEPT / ITERATE / RESET
- Show reasoning for recommendation
- Add `operator analyze {task_name}` command

**Output format:**
```
Quality Assessment for 'fix-logging':

  Acceptance Criteria: 4/5 met (80%)
  Tests: PASSING
  Diff Size: 145 lines (reasonable)
  Scope: IN_SCOPE

  RECOMMENDATION: ITERATE

  Reasoning:
  - Missing acceptance criterion: "Logs include request ID"
  - Otherwise good quality, suggest adding the missing feature

  Options:
  1. ITERATE - Ask sub-agent to add request ID to logs
  2. ACCEPT - Good enough, can add request ID later
  3. RESET - Start over (not recommended)
```

**Files to create:**
- `.claude/skills/worktree-operator/tools/quality_analyzer.py`
- `.claude/skills/worktree-operator/cookbook/analyze-quality.md`

**Files to modify:**
- `.claude/skills/worktree-operator/SKILL.md`
- `.claude/skills/worktree-operator/cookbook/review-task.md`

**Acceptance Criteria:**
- [ ] Quality score calculated from multiple factors
- [ ] Recommendation given with reasoning
- [ ] `operator analyze` command works
- [ ] Integrates with review workflow

---

### 12. add-batch-operations
- Status: PENDING
- Priority: LOW
- Dependencies: add-dependency-enforcement
- Description: Support batch task creation and spawning

**Problem:**
- Must create/spawn tasks one at a time
- Slow for large feature decompositions
- No parallel spawn capability

**Deliverables:**
- `operator create-all` - Create all PENDING tasks from plan
- `operator spawn-unblocked` - Spawn all tasks with met dependencies
- `operator spawn-parallel N` - Spawn up to N tasks in parallel
- Progress reporting for batch operations

**Files to create:**
- `.claude/skills/worktree-operator/cookbook/batch-operations.md`

**Files to modify:**
- `.claude/skills/worktree-operator/tools/task.py`
- `.claude/skills/worktree-operator/SKILL.md`

**Acceptance Criteria:**
- [ ] `create-all` creates multiple tasks
- [ ] `spawn-unblocked` respects dependencies
- [ ] `spawn-parallel` limits concurrent sub-agents
- [ ] Progress shown for batch operations
- [ ] Errors don't stop entire batch

---

### 13. add-troubleshooting-docs
- Status: PENDING
- Priority: LOW
- Dependencies: All above
- Description: Document common issues and recovery procedures

**Problem:**
- No troubleshooting guide
- Users must debug manually
- Common issues not documented

**Deliverables:**
- Troubleshooting section in README.md
- Common issues:
  - Worktree in bad state (how to reset)
  - Sub-agent hung (how to kill and restart)
  - Rebase conflicts (how to resolve)
  - Tests failing after merge (how to revert)
  - Lock file stuck (how to clean)
- Decision matrix: when to accept/iterate/reset
- Recovery procedures for each error type

**Files to modify:**
- `README.md`

**Files to create:**
- `.claude/skills/worktree-operator/TROUBLESHOOTING.md`

**Acceptance Criteria:**
- [ ] All common issues documented
- [ ] Each issue has step-by-step recovery
- [ ] Decision matrix included
- [ ] Examples for each scenario

---

### 14. add-workspace-config
- Status: PENDING
- Priority: LOW
- Dependencies: None
- Description: Add workspace configuration file

**Problem:**
- Settings hardcoded (test command, timeouts, etc.)
- No way to customize per-project
- Main branch name assumed

**Deliverables:**
- Create `workspace.json` on init
- Configurable settings:
  - `test_command`: Command to run tests
  - `test_timeout`: Max test runtime (seconds)
  - `main_branch`: Default main branch name
  - `commit_prefix`: Ticket format for commits
  - `auto_push`: Whether to push after accept
  - `heartbeat_interval`: Sub-agent heartbeat (seconds)
  - `heartbeat_timeout`: When to warn about hung agent

**Default workspace.json:**
```json
{
  "test_command": "npm test",
  "test_timeout": 300,
  "main_branch": "main",
  "commit_prefix": "{ticket}:",
  "auto_push": false,
  "heartbeat_interval": 60,
  "heartbeat_timeout": 600
}
```

**Files to create:**
- `.claude/skills/worktree-common/templates/workspace.json`

**Files to modify:**
- `.claude/skills/worktree-operator/tools/workspace.py`
- `.claude/skills/worktree-operator/cookbook/init-workspace.md`

**Acceptance Criteria:**
- [ ] workspace.json created on init
- [ ] All tools read from config
- [ ] Missing config uses defaults
- [ ] `operator config` shows current settings
- [ ] `operator config set KEY VALUE` updates settings

---

## Execution Order

```
CRITICAL (Security) - Do First
├── 1. fix-shell-injection
└── 2. add-input-validation

HIGH (Reliability) - Do Second
├── 3. add-subagent-health-check
├── 4. add-test-verification-post-merge
│   └── 5. add-transactional-accept
└── 6. fix-race-conditions

MEDIUM (Robustness) - Do Third
├── 7. add-comprehensive-logging
├── 8. add-dependency-enforcement
├── 9. add-conflict-resolution-guide
├── 10. improve-error-messages
└── 11. add-decision-support

LOW (Usability) - Do Last
├── 12. add-batch-operations (depends on 8)
├── 13. add-troubleshooting-docs (depends on all)
└── 14. add-workspace-config
```

---

## Success Criteria

### Security
- [ ] No shell injection vulnerabilities
- [ ] All inputs validated
- [ ] Path traversal blocked

### Reliability
- [ ] Sub-agent health monitoring works
- [ ] Tests verified before merge
- [ ] Failed operations rollback cleanly
- [ ] No race conditions

### Robustness
- [ ] All operations logged
- [ ] Dependencies enforced
- [ ] Conflicts have resolution guidance
- [ ] Error messages are actionable

### Usability
- [ ] Batch operations available
- [ ] Troubleshooting documented
- [ ] Workspace configurable
- [ ] Decision support helps reviews

---

## Notes

### Effort Estimates

| Priority | Tasks | Estimated Hours |
|----------|-------|-----------------|
| CRITICAL | 1-2 | 8-10 |
| HIGH | 3-6 | 30-35 |
| MEDIUM | 7-11 | 35-40 |
| LOW | 12-14 | 20-25 |
| **Total** | **14** | **~100 hours** |

### Risk Mitigation

1. **Security tasks first** - Block exploitation before adding features
2. **Test each task** - Don't skip testing even for "simple" fixes
3. **Backward compatible** - Existing workflows should still work
4. **Incremental rollout** - Each task is independently deployable
