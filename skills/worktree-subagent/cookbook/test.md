# Cookbook: Test Mode

## Purpose
Focus on writing, fixing, or improving tests for the codebase.

## When to Use
- Task spec focuses on testing
- Adding test coverage
- Fixing flaky tests
- Writing integration tests
- Improving test quality

## Steps

### 1. Understand Testing Requirements

```
# Read spec.md for testing requirements
cat ../spec.md

# Look for:
# - What needs to be tested
# - Coverage targets
# - Test types needed (unit, integration, e2e)
# - Specific scenarios to cover
```

### 2. Assess Current Test State

```bash
# Find existing tests
find . -name "*.test.*" -o -name "*.spec.*" -o -name "*_test.*"

# Run existing tests
npm test
# or
pytest
# or
go test ./...

# Check coverage
npm test -- --coverage
```

### 3. Identify Test Gaps

Compare code to tests:

```bash
# List source files
find src -name "*.ts" | grep -v test

# List test files
find . -name "*.test.ts"

# Find untested code
# Coverage report shows this
```

### 4. Plan Test Strategy

Determine what tests to write:

| Code Area | Unit Tests | Integration Tests | E2E Tests |
|-----------|------------|-------------------|-----------|
| Utilities | Yes | No | No |
| Services | Yes | Maybe | No |
| API endpoints | Yes | Yes | Maybe |
| UI components | Yes | Yes | Maybe |

### 5. Write Unit Tests

```typescript
// Test file mirrors source structure
// src/utils/calculator.ts -> tests/utils/calculator.test.ts

import { calculate } from '../src/utils/calculator';

describe('calculate', () => {
  describe('addition', () => {
    it('should add positive numbers', () => {
      expect(calculate(2, 3, 'add')).toBe(5);
    });

    it('should add negative numbers', () => {
      expect(calculate(-2, -3, 'add')).toBe(-5);
    });

    it('should handle zero', () => {
      expect(calculate(5, 0, 'add')).toBe(5);
    });
  });

  describe('edge cases', () => {
    it('should throw on invalid operation', () => {
      expect(() => calculate(1, 2, 'invalid'))
        .toThrow('Invalid operation');
    });

    it('should handle very large numbers', () => {
      expect(calculate(Number.MAX_SAFE_INTEGER, 1, 'add'))
        .toBe(Number.MAX_SAFE_INTEGER + 1);
    });
  });
});
```

### 6. Write Integration Tests

```typescript
// tests/integration/payment-flow.test.ts

describe('Payment Flow', () => {
  let db: TestDatabase;
  let api: TestApi;

  beforeAll(async () => {
    db = await TestDatabase.create();
    api = await TestApi.create(db);
  });

  afterAll(async () => {
    await db.cleanup();
    await api.close();
  });

  beforeEach(async () => {
    await db.reset();
  });

  it('should process payment end-to-end', async () => {
    // Setup
    const user = await db.createUser({ balance: 100 });
    const order = await db.createOrder({ userId: user.id, amount: 50 });

    // Execute
    const response = await api.post('/payments', {
      orderId: order.id,
      amount: 50
    });

    // Verify
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);

    const updatedUser = await db.getUser(user.id);
    expect(updatedUser.balance).toBe(50);
  });
});
```

### 7. Test Edge Cases

Always test:

```typescript
describe('Edge Cases', () => {
  // Null/undefined
  it('should handle null input', () => { });
  it('should handle undefined input', () => { });

  // Empty values
  it('should handle empty string', () => { });
  it('should handle empty array', () => { });
  it('should handle empty object', () => { });

  // Boundaries
  it('should handle minimum value', () => { });
  it('should handle maximum value', () => { });
  it('should handle zero', () => { });

  // Invalid input
  it('should reject invalid type', () => { });
  it('should reject out of range', () => { });

  // Async edge cases
  it('should handle timeout', () => { });
  it('should handle network error', () => { });
});
```

### 8. Test Error Handling

```typescript
describe('Error Handling', () => {
  it('should throw descriptive error for invalid input', () => {
    expect(() => processPayment(-1))
      .toThrow('Amount must be positive');
  });

  it('should return error object on API failure', async () => {
    mockApi.mockReject(new Error('Network error'));

    const result = await processPayment(100);

    expect(result.success).toBe(false);
    expect(result.error).toBe('Network error');
  });

  it('should log error and continue on non-critical failure', () => {
    const logSpy = jest.spyOn(logger, 'error');

    processWithLogging(invalidData);

    expect(logSpy).toHaveBeenCalledWith(
      expect.stringContaining('Non-critical error')
    );
  });
});
```

### 9. Fix Flaky Tests

If fixing flaky tests:

```typescript
// BAD: Timing-dependent
it('should complete within 100ms', async () => {
  const start = Date.now();
  await slowOperation();
  expect(Date.now() - start).toBeLessThan(100);
});

// GOOD: Use proper async handling
it('should complete the operation', async () => {
  const result = await slowOperation();
  expect(result).toBeDefined();
});

// BAD: Order-dependent
it('test 2', () => {
  expect(sharedState.value).toBe('from test 1'); // depends on test 1
});

// GOOD: Isolated
it('test 2', () => {
  const state = createFreshState();
  state.value = 'expected';
  expect(state.value).toBe('expected');
});

// BAD: Time-dependent
it('should format today', () => {
  expect(formatDate()).toBe('2024-01-15'); // fails tomorrow
});

// GOOD: Controlled time
it('should format date', () => {
  jest.setSystemTime(new Date('2024-01-15'));
  expect(formatDate()).toBe('2024-01-15');
});
```

### 10. Verify Coverage

```bash
# Generate coverage report
npm test -- --coverage

# Check against targets
# Look for uncovered lines
# Add tests for red lines
```

### 11. Commit Tests

```bash
# Commit message format
git add .
git commit -m "K-123: Add unit tests for payment service

- Add happy path tests
- Add edge case tests
- Add error handling tests
- Coverage: 65% → 85%"
```

### 12. Write results.md

```markdown
# Results: {task_name}

## Summary
Added comprehensive test coverage for the payment service.

## Changes Made
- Added unit tests for all payment functions
- Added integration tests for payment flow
- Fixed 2 flaky tests in order service
- Improved error handling test coverage

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `tests/services/payment.test.ts` | Created | Unit tests |
| `tests/integration/payment.test.ts` | Created | Integration tests |
| `tests/services/order.test.ts` | Modified | Fixed flaky tests |

## Tests
- Previous test count: 45
- New test count: 72
- All tests passing
- Coverage: 65% → 85%

## Coverage by Area
| Module | Before | After |
|--------|--------|-------|
| payment | 40% | 92% |
| order | 70% | 85% |
| utils | 90% | 95% |

## Commits
| Hash | Message |
|------|---------|
| `abc1234` | K-123: Add unit tests for payment service |
| `def5678` | K-123: Add integration tests for payment flow |
| `ghi9012` | K-123: Fix flaky tests in order service |

## Notes for Reviewer
- Followed existing test patterns from auth.test.ts
- Used testcontainers for database integration tests
- Mocked external payment API in unit tests
```

## Test Patterns

### Arrange-Act-Assert

```typescript
it('should process payment', () => {
  // Arrange
  const payment = { amount: 100, currency: 'USD' };

  // Act
  const result = processPayment(payment);

  // Assert
  expect(result.success).toBe(true);
});
```

### Given-When-Then (BDD style)

```typescript
describe('Payment Processing', () => {
  describe('given a valid payment', () => {
    describe('when processing', () => {
      it('then should return success', () => { });
    });
  });
});
```

### Test Doubles

```typescript
// Mock - verify interactions
const mockLogger = jest.fn();
processPayment(100, mockLogger);
expect(mockLogger).toHaveBeenCalledWith('Processing: 100');

// Stub - provide canned responses
const stubApi = { getRate: () => 1.5 };
const result = convertCurrency(100, stubApi);
expect(result).toBe(150);

// Fake - simplified implementation
class FakeDatabase implements Database {
  private data = new Map();
  async get(id) { return this.data.get(id); }
  async set(id, value) { this.data.set(id, value); }
}
```

## Quality Checklist

- [ ] All specified scenarios tested
- [ ] Edge cases covered
- [ ] Error handling tested
- [ ] Tests are deterministic (not flaky)
- [ ] Tests are isolated (no shared state)
- [ ] Tests are readable (clear intent)
- [ ] Coverage targets met
- [ ] All tests passing
- [ ] No skipped tests without reason
