# Cookbook: Refactor Mode

## Purpose
Restructure code to improve quality without changing external behavior.

## When to Use
- Task spec focuses on refactoring
- Improving code structure
- Reducing duplication
- Improving readability
- Preparing code for new features

## Golden Rule

> **The behavior must not change.**
> After refactoring, the code should do exactly what it did before.

## Steps

### 1. Understand Refactoring Goals

```
# Read spec.md for refactoring requirements
cat ../spec.md

# Look for:
# - What needs to be refactored
# - Why (readability, performance, maintainability)
# - Constraints (don't break X, keep API stable)
# - Expected outcome
```

### 2. Verify Tests Exist

**CRITICAL:** Before refactoring, ensure tests cover the code:

```bash
# Run existing tests
npm test

# Check coverage for code being refactored
npm test -- --coverage --collectCoverageFrom='src/target/**'

# If coverage is low, ADD TESTS FIRST
```

### 3. Establish Baseline

```bash
# Run tests - they must pass before refactoring
npm test

# Document current behavior
# Note any edge cases the tests reveal
```

### 4. Make Small, Incremental Changes

```
WRONG:
1. Make all changes
2. Hope it works
3. Debug for hours

RIGHT:
1. Make one small change
2. Run tests
3. Commit if green
4. Repeat
```

### 5. Common Refactoring Patterns

#### Extract Function

```typescript
// Before
function processOrder(order) {
  // validate
  if (!order.items || order.items.length === 0) {
    throw new Error('Empty order');
  }
  if (!order.customer) {
    throw new Error('No customer');
  }
  // ... lots more code
}

// After
function validateOrder(order) {
  if (!order.items || order.items.length === 0) {
    throw new Error('Empty order');
  }
  if (!order.customer) {
    throw new Error('No customer');
  }
}

function processOrder(order) {
  validateOrder(order);
  // ... rest of code
}
```

#### Extract Variable

```typescript
// Before
if (user.age >= 18 && user.country === 'US' && user.verified) {
  // ...
}

// After
const isEligible = user.age >= 18 && user.country === 'US' && user.verified;
if (isEligible) {
  // ...
}
```

#### Replace Conditional with Polymorphism

```typescript
// Before
function calculateDiscount(customer) {
  switch (customer.type) {
    case 'regular': return 0;
    case 'premium': return 0.1;
    case 'vip': return 0.2;
  }
}

// After
interface Customer {
  getDiscount(): number;
}

class RegularCustomer implements Customer {
  getDiscount() { return 0; }
}

class PremiumCustomer implements Customer {
  getDiscount() { return 0.1; }
}

class VIPCustomer implements Customer {
  getDiscount() { return 0.2; }
}
```

#### Remove Duplication

```typescript
// Before
function createUser(name, email) {
  const timestamp = new Date().toISOString();
  const id = generateId();
  return { id, name, email, createdAt: timestamp, updatedAt: timestamp };
}

function createProduct(name, price) {
  const timestamp = new Date().toISOString();
  const id = generateId();
  return { id, name, price, createdAt: timestamp, updatedAt: timestamp };
}

// After
function withTimestamps<T>(data: T): T & { createdAt: string; updatedAt: string } {
  const timestamp = new Date().toISOString();
  return { ...data, createdAt: timestamp, updatedAt: timestamp };
}

function withId<T>(data: T): T & { id: string } {
  return { ...data, id: generateId() };
}

function createUser(name, email) {
  return withId(withTimestamps({ name, email }));
}

function createProduct(name, price) {
  return withId(withTimestamps({ name, price }));
}
```

#### Simplify Conditionals

```typescript
// Before
function getStatus(user) {
  if (user.isActive) {
    if (user.isPremium) {
      return 'active-premium';
    } else {
      return 'active';
    }
  } else {
    if (user.isPremium) {
      return 'inactive-premium';
    } else {
      return 'inactive';
    }
  }
}

// After
function getStatus(user) {
  const activeStatus = user.isActive ? 'active' : 'inactive';
  const premiumSuffix = user.isPremium ? '-premium' : '';
  return activeStatus + premiumSuffix;
}
```

### 6. Run Tests After Each Change

```bash
# After every refactoring step
npm test

# If tests fail:
# 1. Undo the change
# 2. Figure out why
# 3. Try a smaller step
```

### 7. Commit Frequently

```bash
# Commit each successful refactoring step
git add .
git commit -m "K-123: Extract validateOrder function"

git add .
git commit -m "K-123: Replace customer discount switch with polymorphism"

git add .
git commit -m "K-123: Remove duplication in entity creation"
```

### 8. Update Related Code

If refactoring changes internal APIs:

```typescript
// Update all callers
// Before
processOrder(order);

// After (if signature changed)
const validated = validateOrder(order);
processOrder(validated);
```

### 9. Final Verification

```bash
# Run full test suite
npm test

# Check for regressions
# Compare behavior to baseline

# Verify code quality improved
# - Less duplication
# - Better structure
# - More readable
```

### 10. Write results.md

```markdown
# Results: {task_name}

## Summary
Refactored the order processing module to improve maintainability and reduce duplication.

## Changes Made

### Extract Functions
- Extracted `validateOrder` from `processOrder`
- Extracted `calculateTotals` from `processOrder`

### Remove Duplication
- Created `withTimestamps` utility for consistent timestamps
- Created `withId` utility for consistent ID generation

### Improve Structure
- Replaced discount switch with polymorphic Customer classes
- Simplified nested conditionals in status calculation

## Files Modified
| File | Action | Description |
|------|--------|-------------|
| `src/services/order.ts` | Modified | Extracted functions |
| `src/utils/entity.ts` | Created | Shared entity utilities |
| `src/models/customer.ts` | Modified | Added Customer classes |

## Tests
- All 45 tests passing (no changes to tests needed)
- Behavior unchanged

## Before/After Comparison

### Cyclomatic Complexity
- processOrder: 15 → 5
- calculateDiscount: 4 → 1 (per class)

### Lines of Code
- order.ts: 250 → 180 (28% reduction)
- Total duplication: 45 lines → 12 lines

## Commits
| Hash | Message |
|------|---------|
| `abc1234` | K-123: Extract validateOrder function |
| `def5678` | K-123: Extract calculateTotals function |
| `ghi9012` | K-123: Add entity timestamp utilities |
| `jkl3456` | K-123: Replace discount switch with polymorphism |

## Notes for Reviewer
- All refactoring preserves existing behavior
- No new tests needed as existing coverage was adequate
- Recommend follow-up task to add tests for edge cases
```

## Refactoring Safety Checklist

Before starting:
- [ ] Tests exist for code being refactored
- [ ] All tests pass
- [ ] Understand current behavior

During refactoring:
- [ ] Making small changes
- [ ] Running tests after each change
- [ ] Committing frequently
- [ ] Not changing behavior

After refactoring:
- [ ] All tests still pass
- [ ] Behavior unchanged
- [ ] Code quality improved
- [ ] No dead code left behind

## Anti-Patterns to Avoid

### Big Bang Refactoring
```
DON'T: Rewrite everything at once
DO: Small, incremental changes
```

### Refactoring Without Tests
```
DON'T: "Tests slow me down"
DO: Add tests first if they don't exist
```

### Changing Behavior
```
DON'T: "While I'm here, let me also fix this bug"
DO: Refactor only, log bugs for separate tasks
```

### Gold Plating
```
DON'T: "Let me also add this cool feature"
DO: Stick to the refactoring scope
```

## When to Stop

Stop refactoring when:
- Goals from spec are met
- Tests pass
- Code is measurably better
- Further changes would be diminishing returns

Don't chase perfection - good enough is good enough.
