# Cookbook: Implement Mode

## Purpose
Standard implementation mode for building features, fixing bugs, or adding functionality.

## When to Use
- Default mode for most tasks
- Building new features
- Fixing bugs
- Adding functionality
- General code changes

## Steps

### 1. Understand the Task

```
# Read spec.md thoroughly
cat ../spec.md

# Note:
# - Objective (what to accomplish)
# - Requirements (what must be done)
# - Files to modify
# - Acceptance criteria
# - Out of scope items
# - Hints/guidance
```

### 2. Check for Iteration Feedback

```
# Check if this is an iteration
cat ../feedback.md

# If feedback exists:
# - Address issues FIRST
# - Don't repeat mistakes
# - Build on previous work
```

### 3. Explore the Codebase

Before coding, understand the context:

```bash
# Project structure
ls -la
find . -type f -name "*.ts" | head -20  # adjust for your language

# Related files mentioned in spec
cat {file_mentioned_in_spec}

# Existing patterns
grep -r "similar_pattern" --include="*.ts"

# Tests structure
ls -la tests/ test/ __tests__/ 2>/dev/null
```

### 4. Plan Your Approach

Before writing code, plan:

1. What files need to change?
2. What order should changes happen?
3. Are there dependencies between changes?
4. What tests need to be added?
5. What could go wrong?

### 5. Implement Incrementally

```
For each logical change:
1. Make the change
2. Run related tests
3. Commit if tests pass

Don't make all changes then test at the end.
```

### 6. Follow Existing Patterns

```typescript
// Look for similar code in the codebase
// Match the style, naming, structure

// BAD: Inventing new patterns
export function myNewUtility() { ... }

// GOOD: Following existing patterns
export const myNewUtility = createUtility({
  // ... matches existing utility pattern
});
```

### 7. Handle Edge Cases

```typescript
// Don't just handle happy path
function processPayment(amount: number) {
  // Check edge cases
  if (amount <= 0) {
    throw new Error('Amount must be positive');
  }
  if (amount > MAX_AMOUNT) {
    throw new Error('Amount exceeds maximum');
  }
  // ... proceed with normal flow
}
```

### 8. Add Tests

```typescript
// Test file should mirror source structure
// src/services/payment.ts -> tests/services/payment.test.ts

describe('processPayment', () => {
  it('should process valid payment', () => {
    // Happy path
  });

  it('should reject negative amount', () => {
    // Edge case
  });

  it('should reject amount over maximum', () => {
    // Edge case
  });
});
```

### 9. Run Full Test Suite

```bash
# Run all tests before committing final changes
npm test
# or
pytest
# or
go test ./...
```

### 10. Commit with Clear Messages

```bash
# Format: {TICKET}: Brief description
git add .
git commit -m "K-123: Add payment processing service

- Implement processPayment function
- Add validation for amount
- Include error handling for edge cases"
```

### 11. Write results.md

```markdown
# Results: {task_name}

## Summary
Implemented the payment processing service with validation and error handling.

## Changes Made
- Created payment service with processPayment function
- Added input validation for amount
- Implemented error handling for edge cases
- Added comprehensive unit tests

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `src/services/payment.ts` | Created | Main payment service |
| `src/types/payment.ts` | Created | Type definitions |
| `tests/services/payment.test.ts` | Created | Unit tests |

## Tests
- All existing tests: PASS
- New tests added: 5
- Coverage: 78% → 82%

## Commits
| Hash | Message |
|------|---------|
| `abc1234` | K-123: Add payment processing service |
| `def5678` | K-123: Add unit tests for payment service |

## Risks / Concerns
- None identified

## Notes for Reviewer
- Followed existing service pattern from auth.ts
- Amount validation uses same limits as order service
```

## Common Patterns

### Adding a New Service

```typescript
// 1. Create types
// src/types/myservice.ts
export interface MyServiceConfig { ... }
export interface MyServiceResult { ... }

// 2. Create service
// src/services/myservice.ts
import { MyServiceConfig, MyServiceResult } from '../types/myservice';

export class MyService {
  constructor(private config: MyServiceConfig) {}

  async process(): Promise<MyServiceResult> {
    // Implementation
  }
}

// 3. Add tests
// tests/services/myservice.test.ts
describe('MyService', () => {
  // Tests
});

// 4. Export from index if needed
// src/services/index.ts
export { MyService } from './myservice';
```

### Modifying Existing Code

```typescript
// 1. Read existing code thoroughly
// 2. Understand why it's structured this way
// 3. Make minimal changes to achieve goal
// 4. Ensure tests still pass
// 5. Add tests for new behavior
```

### Fixing a Bug

```typescript
// 1. Write a failing test that reproduces the bug
it('should handle the edge case that caused bug', () => {
  expect(buggyFunction(edgeCase)).toBe(expectedResult);
});

// 2. Fix the code
// 3. Verify test passes
// 4. Ensure no regressions
```

## Quality Checklist

Before completing:

- [ ] All requirements from spec addressed
- [ ] Each acceptance criterion met
- [ ] No debug code or console.logs left
- [ ] No commented-out code
- [ ] Error handling in place
- [ ] Tests added for new code
- [ ] All tests passing
- [ ] Commits are atomic and well-described
- [ ] results.md written

## Troubleshooting

### Tests fail after changes
1. Read error message carefully
2. Check if you broke existing functionality
3. Fix the issue
4. If unsure, document in results.md

### Unsure about spec interpretation
1. Make your best interpretation
2. Document assumption in results.md
3. Proceed with implementation
4. Operator will clarify if needed

### Dependencies missing
1. Check if dependency is already in project
2. If truly needed, add to package.json
3. Document in results.md
4. Minimize new dependencies

### Code doesn't compile
1. Read error messages
2. Check imports
3. Check types
4. Don't commit broken code
