# Cookbook: Create Plan

## Purpose
Analyze the codebase and create a task breakdown in plan.md.

## When to Use
- User says "operator plan" or "operator analyze"
- After workspace init, before creating tasks
- When re-planning after scope change

## Prerequisites
- Workspace initialized (repo/ exists)
- On correct branch

## Steps

### 1. Understand the Objective

Ask user if not clear:
- What feature/fix are we implementing?
- What's the ticket/issue number?
- Any specific requirements or constraints?

### 2. Analyze the Codebase

Explore the repository to understand:

```bash
cd repo/

# Project structure
ls -la
find . -type f -name "*.md" | head -20

# Package configuration
cat package.json 2>/dev/null || cat Cargo.toml 2>/dev/null || cat go.mod 2>/dev/null

# Source structure
find src -type f | head -30
find lib -type f | head -30

# Test structure
find test* -type f 2>/dev/null | head -20
find *test* -type f 2>/dev/null | head -20

# Recent changes
git log --oneline -20
```

### 3. Identify Task Breakdown

Decompose the work into discrete tasks. Each task should be:

**Good task characteristics:**
- Single-purpose (one clear objective)
- Independently testable
- Completable in one sub-agent session
- Clear acceptance criteria
- Minimal overlap with other tasks

**Common task patterns:**
- Add new module/component
- Modify existing functionality
- Write/fix tests
- Refactor code
- Update configuration
- Add documentation

### 4. Determine Task Order

Consider dependencies:
- Which tasks can run in parallel?
- Which tasks depend on others?
- What's the critical path?

### 5. Write plan.md

```markdown
# Plan: {TICKET} {FEATURE_NAME}

## Status: IN_PROGRESS
## Branch: {MAIN_BRANCH}
## Repository: {REPO_URL}

---

## Objective

{CLEAR_DESCRIPTION_OF_WHAT_WE'RE_BUILDING}

---

## Tasks

### 1. {task-name-1}
- Status: PENDING
- Branch: feature/{TICKET}/{task-name-1}
- Dependencies: None
- Description: {WHAT_THIS_TASK_ACCOMPLISHES}
- Files: {KEY_FILES_TO_MODIFY}

### 2. {task-name-2}
- Status: PENDING
- Branch: feature/{TICKET}/{task-name-2}
- Dependencies: {task-name-1} (if any)
- Description: {WHAT_THIS_TASK_ACCOMPLISHES}
- Files: {KEY_FILES_TO_MODIFY}

### 3. {task-name-3}
- Status: PENDING
- Branch: feature/{TICKET}/{task-name-3}
- Dependencies: None
- Description: {WHAT_THIS_TASK_ACCOMPLISHES}
- Files: {KEY_FILES_TO_MODIFY}

---

## Parallel Execution

Tasks that can run in parallel:
- {task-name-1} and {task-name-3} (no overlap)

Sequential requirements:
- {task-name-2} must wait for {task-name-1}

---

## Risks / Notes

- {ANY_RISKS_OR_CONCERNS}
- {AREAS_NEEDING_EXTRA_ATTENTION}

---

## Notes

- Created: {DATE}
- Last Updated: {DATE}
```

### 6. Log Planning Decision

Add entry to review-notes.md:

```markdown
### {DATE} {TIME} - Plan created

Analyzed codebase for {TICKET}.

Tasks identified:
1. {task-1}: {brief description}
2. {task-2}: {brief description}
3. {task-3}: {brief description}

Reasoning:
- {WHY_THIS_BREAKDOWN}
- {KEY_CONSIDERATIONS}

Parallel opportunities: {tasks that can run together}
Critical path: {sequential dependencies}
```

### 7. Report Plan

Present the plan to user:

```
✓ Plan created

Objective: {objective}
Tasks identified: {count}

Tasks:
  1. {task-1} - {brief description}
  2. {task-2} - {brief description}
  3. {task-3} - {brief description}

Parallel opportunities:
  - {task-1} and {task-3} can run simultaneously

Next steps:
  - "operator create task {task-1}" to start first task
  - Or create multiple tasks for parallel execution
```

## Task Sizing Guidelines

**Too small:**
- "Add import statement"
- "Fix typo"
- Single line changes

**Good size:**
- "Implement user authentication endpoint"
- "Add unit tests for payment service"
- "Refactor database connection pooling"

**Too large:**
- "Build entire feature"
- "Rewrite the codebase"
- Multiple unrelated changes

## Example Plan

```markdown
# Plan: K-123 User Authentication

## Status: IN_PROGRESS
## Branch: feature/K-123_user_auth

---

## Objective

Add JWT-based authentication to the API, including login, logout, and token refresh endpoints.

---

## Tasks

### 1. setup-jwt-utils
- Status: PENDING
- Branch: feature/K-123/setup-jwt-utils
- Dependencies: None
- Description: Create JWT utility functions for token generation and validation
- Files: src/utils/jwt.ts, src/types/auth.ts

### 2. implement-auth-endpoints
- Status: PENDING
- Branch: feature/K-123/implement-auth-endpoints
- Dependencies: setup-jwt-utils
- Description: Add /login, /logout, /refresh API endpoints
- Files: src/routes/auth.ts, src/controllers/auth.ts

### 3. add-auth-middleware
- Status: PENDING
- Branch: feature/K-123/add-auth-middleware
- Dependencies: setup-jwt-utils
- Description: Create middleware to protect routes requiring authentication
- Files: src/middleware/auth.ts

### 4. write-auth-tests
- Status: PENDING
- Branch: feature/K-123/write-auth-tests
- Dependencies: implement-auth-endpoints, add-auth-middleware
- Description: Add unit and integration tests for auth system
- Files: tests/auth/*.test.ts

---

## Parallel Execution

- setup-jwt-utils runs first (no dependencies)
- implement-auth-endpoints and add-auth-middleware can run in parallel after jwt-utils
- write-auth-tests runs last after all implementation

---

## Notes

- Created: 2024-01-15
```

## Checklist

- [ ] Objective clearly understood
- [ ] Codebase analyzed
- [ ] Tasks identified (3-7 typically)
- [ ] Each task is single-purpose
- [ ] Dependencies mapped
- [ ] plan.md written
- [ ] review-notes.md updated
- [ ] Plan presented to user
