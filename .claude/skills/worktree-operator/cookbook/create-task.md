# Cookbook: Create Task

## Purpose
Create a new task with folder structure, worktree, and specification.

## When to Use
- User says "operator create task {name}"
- After planning, to set up individual tasks
- When adding new tasks mid-stream

## Prerequisites
- Workspace initialized
- Plan exists (recommended)
- Main branch known

## Required Information

1. **Ticket ID** - e.g., "K-123"
2. **Task name** - e.g., "fix-logging" (lowercase, hyphenated)
3. **Main branch** - Branch to create worktree from

## Steps

### 1. Validate Task Name

```python
# Task name should be:
# - Lowercase
# - Hyphenated (no spaces or underscores)
# - Descriptive but concise
# - Not already existing

import re
task_name = task_name.lower().replace(" ", "-").replace("_", "-")
assert re.match(r'^[a-z0-9-]+$', task_name), "Invalid task name"
```

### 2. Create Task Folder Structure

```bash
TASK="fix-logging"
WORKSPACE="."

mkdir -p "task-${TASK}"
touch "task-${TASK}/spec.md"
touch "task-${TASK}/feedback.md"
touch "task-${TASK}/results.md"
```

### 3. Create Git Worktree

```bash
TICKET="K-123"
MAIN_BRANCH="feature/K-123_user_auth"
SUB_BRANCH="feature/${TICKET}/${TASK}"

cd repo
git worktree add "../task-${TASK}/worktree" -b "${SUB_BRANCH}" "${MAIN_BRANCH}"
cd ..
```

### 4. Write spec.md

Gather information and write detailed specification:

```markdown
# Task: {task_name}

## Ticket: {ticket}
## Branch: feature/{ticket}/{task_name}
## Created: {date}

---

## Objective

{CLEAR_ONE_SENTENCE_OBJECTIVE}

---

## Background / Context

{WHY_IS_THIS_TASK_NEEDED}
{RELEVANT_CONTEXT_FROM_CODEBASE}
{ANY_PRIOR_DECISIONS_OR_CONSTRAINTS}

---

## Requirements

1. {REQUIREMENT_1}
2. {REQUIREMENT_2}
3. {REQUIREMENT_3}

---

## Files to Modify

- `{FILE_PATH}` - {WHAT_TO_CHANGE}
- `{FILE_PATH}` - {WHAT_TO_CHANGE}

## Files to Create (if any)

- `{FILE_PATH}` - {PURPOSE}

---

## Acceptance Criteria

- [ ] {CRITERION_1}
- [ ] {CRITERION_2}
- [ ] {CRITERION_3}
- [ ] All existing tests pass
- [ ] New tests added for new functionality

---

## Out of Scope

{WHAT_NOT_TO_DO}
{THINGS_TO_EXPLICITLY_AVOID}

---

## Hints / Guidance

- {HELPFUL_HINT_1}
- {REFERENCE_TO_SIMILAR_CODE}
- {PATTERNS_TO_FOLLOW}

---

## Definition of Done

1. All acceptance criteria met
2. Code committed with clear commit messages
3. Tests passing
4. results.md written with summary of changes
```

### 5. Initialize feedback.md

```markdown
# Feedback: {task_name}

_No feedback yet - this is the first iteration._
```

### 6. Initialize results.md

```markdown
# Results: {task_name}

_Results will be written by sub-agent after implementation._
```

### 7. Update plan.md

Find the task in plan.md and update:

```markdown
### X. {task_name}
- Status: PENDING → IN_PROGRESS (or keep PENDING until spawn)
- Branch: feature/{ticket}/{task_name}
- Worktree: Created
```

### 8. Report Status

```
✓ Task '{task_name}' created successfully

Task folder: task-{task_name}/
Worktree: task-{task_name}/worktree/
Branch: feature/{ticket}/{task_name}
Based on: {main_branch}

Files created:
  - spec.md (needs completion)
  - feedback.md
  - results.md

Next steps:
  1. Review and complete spec.md with detailed requirements
  2. Run "operator spawn {task_name}" to start sub-agent
```

## Using Python Tools

```python
from tools.task import create_task

result = create_task(
    ticket="K-123",
    task_name="fix-logging",
    main_branch="feature/K-123_user_auth",
    workspace_path=".",
    spec_content=None  # Or provide pre-written spec
)

if result["success"]:
    print(f"✓ {result['message']}")
    print(f"  Branch: {result['branch']}")
else:
    print(f"✗ Error: {result['error']}")
```

## Writing Good Specifications

### Be Specific
```markdown
# Bad
## Objective
Fix the logging.

# Good
## Objective
Replace console.log calls in src/services/payment.ts with structured JSON logging using the winston library.
```

### Include Context
```markdown
## Background
The payment service currently uses console.log for debugging. In production, we need structured logs for:
- Log aggregation (ELK stack)
- Debugging distributed transactions
- Compliance audit trails

See existing pattern in src/services/auth.ts which already uses structured logging.
```

### Clear Acceptance Criteria
```markdown
# Bad
- [ ] Logging works

# Good
- [ ] All console.log calls in payment.ts replaced with logger
- [ ] Each log entry includes: timestamp, level, service name, request ID
- [ ] Logs are valid JSON when parsed
- [ ] Existing tests pass
- [ ] New tests verify log format
```

### Explicit Boundaries
```markdown
## Out of Scope
- Do NOT modify other services (only payment.ts)
- Do NOT change log aggregation configuration
- Do NOT add new dependencies beyond winston (already in package.json)
```

## Error Handling

> See SKILL.md "Error Handling" section for complete error reference and recovery procedures.

| Error | Quick Fix |
|-------|-----------|
| Task folder exists | Choose different name or `rm -rf task-{name}/` |
| Branch exists | Use existing, delete with `git branch -D`, or rename |
| Main branch missing | Check spelling, `git fetch origin` |

## Checklist

- [ ] Task name validated (lowercase, hyphenated)
- [ ] Task folder created
- [ ] Worktree created with correct branch
- [ ] spec.md written with detailed requirements
- [ ] feedback.md initialized
- [ ] results.md initialized
- [ ] plan.md updated
- [ ] Status reported to user
- [ ] Spec reviewed for completeness
