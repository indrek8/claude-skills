# Cookbook: Initialize Workspace

## Purpose
Set up a new workspace for multi-agent development with Git worktrees.

## When to Use
- User says "operator init workspace"
- User wants to start a new multi-agent development session
- Starting work on a new feature/ticket

## Required Information

Gather from user:
1. **Repository URL** - Git clone URL
2. **Branch** - Feature branch to work on (or develop)
3. **Workspace path** - Where to create workspace (default: current directory)

## Steps

### 1. Validate Prerequisites

```python
# Check we're in a suitable location
import os
workspace_path = os.getcwd()  # or user-specified path

# Ensure no existing repo/ folder
repo_path = os.path.join(workspace_path, "repo")
if os.path.exists(repo_path):
    # Warn user and ask to confirm or choose different location
    pass
```

### 2. Create Workspace Structure

```bash
# Create workspace directory if needed
mkdir -p {workspace_path}
cd {workspace_path}

# Clone repository
git clone {repo_url} repo

# Checkout branch
cd repo
git switch {branch}
# Or create if new: git switch -c {branch}

# Pull latest
git pull --ff-only origin {branch}
cd ..
```

### 3. Create Workspace Files

```bash
# Create operator files
touch plan.md
touch review-notes.md
```

### 4. Initialize plan.md

Write initial plan.md content:

```markdown
# Plan: {ticket_or_feature_name}

## Status: PENDING
## Branch: {branch}
## Repository: {repo_url}

---

## Objective

_To be defined during planning phase_

---

## Tasks

_Tasks will be added after analysis_

---

## Notes

- Created: {today}
- Last Updated: {today}
```

### 5. Initialize review-notes.md

```markdown
# Review Notes

## Project: {ticket_or_feature_name}
## Branch: {branch}

---

## Log

### {today} - Workspace initialized

Created workspace for {branch}.
Repository: {repo_url}

---
```

### 6. Report Status

After successful init, report:

```
✓ Workspace initialized successfully

Workspace: {workspace_path}
Repository: {repo_path}
Branch: {branch}

Files created:
  - plan.md
  - review-notes.md

Next steps:
  1. Run "operator plan" to analyze codebase and create task breakdown
  2. Or "operator create task {name}" to create specific tasks
```

## Using Python Tools

```python
from tools.workspace import init_workspace, print_status

# Initialize
result = init_workspace(
    repo_url="git@github.com:org/repo.git",
    branch="feature/K-123_feature_name",
    workspace_path="."
)

if result["success"]:
    print(f"✓ {result['message']}")
    print_status(".")
else:
    print(f"✗ Error: {result['error']}")
```

## Error Handling

> See SKILL.md "Error Handling" section for complete error reference and recovery procedures.

| Error | Quick Fix |
|-------|-----------|
| Clone fails | Check URL, SSH keys, network |
| Branch not found | Verify spelling, `git fetch origin`, or create new |
| Repo exists | Remove `rm -rf repo/` or continue with existing |

## Checklist

- [ ] Repository URL obtained
- [ ] Branch name obtained
- [ ] Workspace path confirmed
- [ ] Repository cloned successfully
- [ ] Correct branch checked out
- [ ] plan.md created
- [ ] review-notes.md created
- [ ] Status reported to user
