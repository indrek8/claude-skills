# Cookbook: Review Mode

## Purpose
Analyze code and write findings without making code changes.

## When to Use
- Task spec asks for code review
- Security audit
- Performance analysis
- Architecture review
- Code quality assessment

## Golden Rule

> **No code changes.**
> This mode is for analysis and documentation only.

## Steps

### 1. Understand Review Scope

```
# Read spec.md for review requirements
cat ../spec.md

# Look for:
# - What to review (files, modules, patterns)
# - What to look for (security, performance, quality)
# - Review criteria
# - Output format expected
```

### 2. Identify Files to Review

```bash
# Find relevant files based on spec
find . -name "*.ts" -path "*/src/*"

# Or specific patterns
grep -rl "pattern_to_find" --include="*.ts"

# Get file statistics
wc -l $(find . -name "*.ts" -path "*/target_path/*")
```

### 3. Systematic Code Review

Work through code systematically:

```bash
# Read each file thoroughly
cat src/services/target-service.ts

# Check dependencies
grep -n "import" src/services/target-service.ts

# Check exports
grep -n "export" src/services/target-service.ts

# Look for patterns
grep -n "TODO\|FIXME\|HACK" src/
```

### 4. Security Review Checklist

```typescript
// Check for common vulnerabilities

// 1. SQL Injection
// BAD:
const query = `SELECT * FROM users WHERE id = ${userId}`;
// GOOD:
const query = 'SELECT * FROM users WHERE id = ?';

// 2. XSS
// BAD:
element.innerHTML = userInput;
// GOOD:
element.textContent = userInput;

// 3. Command Injection
// BAD:
exec(`ls ${userPath}`);
// GOOD:
execFile('ls', [sanitizedPath]);

// 4. Path Traversal
// BAD:
readFile(`./uploads/${filename}`);
// GOOD:
readFile(path.join(uploadsDir, path.basename(filename)));

// 5. Hardcoded Secrets
// BAD:
const apiKey = 'sk-1234567890';
// GOOD:
const apiKey = process.env.API_KEY;
```

### 5. Performance Review Checklist

```typescript
// Check for common performance issues

// 1. N+1 Queries
// BAD:
for (const user of users) {
  const orders = await getOrders(user.id); // N queries
}
// GOOD:
const orders = await getOrdersForUsers(users.map(u => u.id)); // 1 query

// 2. Missing Indexes (note for database files)
// Check if queries have appropriate indexes

// 3. Unbounded Operations
// BAD:
const all = await db.findAll(); // Could be millions
// GOOD:
const page = await db.findPaginated({ limit: 100 });

// 4. Blocking Operations
// BAD:
const data = fs.readFileSync(path); // Blocks event loop
// GOOD:
const data = await fs.promises.readFile(path);

// 5. Memory Leaks
// Check for:
// - Event listeners not removed
// - Timers not cleared
// - Large objects held in closures
```

### 6. Code Quality Review

```typescript
// Check for code quality issues

// 1. Complexity
// Functions > 50 lines
// Cyclomatic complexity > 10
// Deep nesting > 4 levels

// 2. Duplication
// Repeated code blocks
// Copy-paste patterns
// Similar functions that could be unified

// 3. Naming
// Unclear variable names (x, temp, data)
// Misleading names
// Inconsistent conventions

// 4. Error Handling
// Missing try-catch
// Swallowed errors
// Generic error messages

// 5. Documentation
// Missing JSDoc on public APIs
// Outdated comments
// No README for modules
```

### 7. Architecture Review

```
Questions to consider:

1. Separation of Concerns
   - Are responsibilities clearly divided?
   - Is business logic mixed with infrastructure?

2. Dependencies
   - Are there circular dependencies?
   - Is coupling too tight?
   - Are abstractions appropriate?

3. Testability
   - Is the code easy to test?
   - Are dependencies injectable?
   - Are there side effects in constructors?

4. Scalability
   - Will this work under load?
   - Are there bottlenecks?
   - Is state managed appropriately?

5. Maintainability
   - Is the code easy to understand?
   - Can it be modified safely?
   - Are there clear boundaries?
```

### 8. Document Findings

Create structured findings:

```markdown
## Finding: [Title]

**Severity:** HIGH | MEDIUM | LOW
**Category:** Security | Performance | Quality | Architecture
**Location:** `path/to/file.ts:123`

**Description:**
What the issue is and why it matters.

**Current Code:**
```typescript
// problematic code
```

**Recommendation:**
What should be done to fix it.

**Recommended Code:**
```typescript
// suggested fix
```
```

### 9. Categorize and Prioritize

Organize findings by severity:

```markdown
## Critical (Must Fix)
- Security vulnerabilities
- Data loss risks
- Breaking bugs

## High (Should Fix Soon)
- Performance issues affecting users
- Code that will cause future problems
- Missing error handling

## Medium (Plan to Fix)
- Code quality issues
- Maintainability concerns
- Technical debt

## Low (Nice to Have)
- Style inconsistencies
- Minor optimizations
- Documentation gaps
```

### 10. Write results.md

```markdown
# Results: {task_name}

## Summary
Completed code review of the payment service module. Found 3 critical issues,
5 high-priority issues, and 12 medium/low issues requiring attention.

## Review Scope
- Files reviewed: 15
- Lines of code: 2,450
- Focus areas: Security, Performance, Code Quality

## Critical Findings

### 1. SQL Injection Vulnerability
**Severity:** CRITICAL
**Location:** `src/services/payment.ts:89`
**Description:** User input directly interpolated into SQL query.
**Recommendation:** Use parameterized queries.

### 2. Hardcoded API Key
**Severity:** CRITICAL
**Location:** `src/config/stripe.ts:12`
**Description:** Stripe API key hardcoded in source.
**Recommendation:** Move to environment variable.

### 3. Missing Authentication Check
**Severity:** CRITICAL
**Location:** `src/routes/admin.ts:45`
**Description:** Admin endpoint accessible without auth.
**Recommendation:** Add authentication middleware.

## High Priority Findings

### 4. N+1 Query Pattern
**Severity:** HIGH
**Location:** `src/services/order.ts:156`
**Description:** Database query inside loop causing performance degradation.
**Recommendation:** Batch queries using IN clause.

[... more findings ...]

## Medium Priority Findings

### 8. Complex Function
**Severity:** MEDIUM
**Location:** `src/services/payment.ts:200`
**Description:** Function has cyclomatic complexity of 15.
**Recommendation:** Extract sub-functions for each payment type.

[... more findings ...]

## Low Priority Findings

### 15. Inconsistent Naming
**Severity:** LOW
**Location:** Multiple files
**Description:** Mix of camelCase and snake_case in variable names.
**Recommendation:** Standardize on camelCase per project conventions.

## Summary Statistics

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Security | 2 | 1 | 0 | 0 |
| Performance | 1 | 2 | 3 | 1 |
| Quality | 0 | 2 | 5 | 4 |
| Architecture | 0 | 0 | 2 | 2 |

## Recommendations

### Immediate Actions
1. Fix SQL injection vulnerability
2. Remove hardcoded API key
3. Add authentication to admin routes

### Short-term (Next Sprint)
1. Optimize N+1 queries
2. Add input validation
3. Improve error handling

### Long-term (Tech Debt)
1. Refactor complex functions
2. Standardize naming conventions
3. Add comprehensive documentation

## Files Reviewed
| File | Lines | Findings |
|------|-------|----------|
| `src/services/payment.ts` | 450 | 4 |
| `src/services/order.ts` | 320 | 3 |
| `src/routes/admin.ts` | 180 | 2 |
| ... | ... | ... |

## Notes for Team
- Consider security training for team
- Recommend adding linter rules for common issues
- Suggest code review checklist adoption
```

## Review Templates

### Security Review Template

```markdown
## Security Review: {module_name}

### Authentication
- [ ] All endpoints require authentication
- [ ] Token validation is correct
- [ ] Session management is secure

### Authorization
- [ ] Role checks are present
- [ ] Resource ownership verified
- [ ] Privilege escalation prevented

### Input Validation
- [ ] All inputs validated
- [ ] Types are checked
- [ ] Bounds are enforced

### Data Protection
- [ ] Sensitive data encrypted
- [ ] PII handled correctly
- [ ] Logs don't contain secrets

### Common Vulnerabilities
- [ ] No SQL injection
- [ ] No XSS vectors
- [ ] No CSRF vulnerabilities
- [ ] No path traversal
- [ ] No command injection
```

### Performance Review Template

```markdown
## Performance Review: {module_name}

### Database
- [ ] Queries are optimized
- [ ] Indexes are appropriate
- [ ] N+1 patterns avoided
- [ ] Connection pooling used

### Memory
- [ ] No memory leaks
- [ ] Large objects handled properly
- [ ] Caching is appropriate

### I/O
- [ ] Async operations used
- [ ] Streaming for large data
- [ ] Proper timeout handling

### Scalability
- [ ] Stateless where possible
- [ ] Horizontal scaling supported
- [ ] Bottlenecks identified
```

## Quality Checklist

Before completing review:
- [ ] All specified areas reviewed
- [ ] Findings are actionable
- [ ] Severity is appropriate
- [ ] Recommendations are practical
- [ ] results.md is comprehensive
- [ ] No code changes made (review only)

## Anti-Patterns to Avoid

### Vague Findings
```
DON'T: "Code could be better"
DO: "Function processPayment (line 89) has cyclomatic complexity of 15.
     Extract validation logic to separate function."
```

### Missing Context
```
DON'T: "SQL injection here"
DO: "SQL injection vulnerability at payment.ts:89. User-supplied orderId
     is interpolated directly into query string. Use parameterized query."
```

### No Recommendations
```
DON'T: "This is a problem"
DO: "This is a problem. Recommend: [specific fix with code example]"
```

### Scope Creep
```
DON'T: Review everything you see
DO: Focus on scope defined in spec.md
```
