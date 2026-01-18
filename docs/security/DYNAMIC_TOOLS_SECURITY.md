# Dynamic Tools Security Guide

**Phase 3.5: Security Hardening for Dynamic Tool Execution**

## 🔒 Overview

The dynamic tool system has been hardened with multiple layers of security protection to prevent code injection, resource exhaustion, and unauthorized access.

## Security Architecture

### Defense in Depth

Our security approach uses multiple independent layers:

1. **AST-based Validation** - Analyzes code structure before compilation
2. **RestrictedPython Compilation** - Compiles code in restricted mode
3. **Sandboxed Execution** - Runs code with limited privileges
4. **Resource Limits** - Enforces CPU, memory, and time constraints
5. **Audit Logging** - Tracks all security events
6. **Rate Limiting** - Prevents abuse and DoS attacks

```
┌─────────────────────────────────────────────┐
│         User-Generated Tool Code            │
└──────────────────┬──────────────────────────┘
                   │
          ┌────────▼────────┐
          │ AST Validator   │ ← Blocks dangerous operations
          └────────┬────────┘
                   │
       ┌───────────▼──────────┐
       │ RestrictedPython     │ ← Safe compilation
       │ Compiler             │
       └───────────┬──────────┘
                   │
          ┌────────▼────────┐
          │   Sandbox       │ ← Resource limits
          │   Executor      │   Timeout protection
          └────────┬────────┘
                   │
            ┌──────▼──────┐
            │  Execution  │ ← Audit logging
            │   Logging   │   Security monitoring
            └─────────────┘
```

## What Code is Allowed

### ✅ Allowed Operations

**Safe Built-in Functions:**
- Basic types: `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`
- Math: `abs`, `max`, `min`, `sum`, `round`
- Iteration: `len`, `range`, `enumerate`, `zip`, `sorted`, `reversed`
- Checks: `isinstance`, `hasattr`

**Whitelisted Imports:**
- `json` - JSON parsing and serialization
- `datetime` - Date and time operations
- `uuid` - UUID generation
- `typing` - Type hints
- `src.db.queries` - Database query functions
- `src.db.connection` - Database connections

**Allowed Syntax:**
- Async functions (`async def`)
- Function calls
- Conditionals (`if`/`else`)
- Loops (`for`, `while`)
- List/dict comprehensions
- F-strings
- Basic operators (`+`, `-`, `*`, `/`, `==`, `!=`, etc.)

### ❌ Blocked Operations

**Dangerous Built-ins:**
- `eval()` - Arbitrary code execution
- `exec()` - Code execution
- `compile()` - Code compilation
- `__import__()` - Dynamic imports
- `open()` - File system access
- `input()` - User input (not applicable)
- `breakpoint()` - Debugger access

**Blocked Imports:**
- `os` - Operating system access
- `sys` - System access
- `subprocess` - Shell commands
- `socket` - Network access
- `requests` - HTTP requests
- `urllib` - URL access
- `shutil` - File operations
- Any module not explicitly whitelisted

**Blocked Attributes:**
- `__globals__` - Global namespace access
- `__dict__` - Object internals
- `__class__` - Class manipulation
- `__code__` - Code object access
- `__import__` - Import bypass
- `__builtins__` - Builtins access

## Resource Limits

All dynamic tools are subject to strict resource limits:

| Resource | Limit | Reason |
|----------|-------|--------|
| **Execution Time** | 5 seconds | Prevents infinite loops |
| **Memory** | 50 MB | Prevents memory exhaustion |
| **CPU** | 25% | Prevents CPU hogging |

If a tool exceeds these limits, it will be automatically terminated and a security event will be logged.

## Rate Limits

To prevent abuse, the system enforces rate limits:

| Action | Limit | Window |
|--------|-------|--------|
| **Tool Creation** | 5 tools | Per user per day |
| **Tool Execution** | 100 executions | Per user per day |

## Code Examples

### ✅ SAFE: Database Query Tool

```python
async def get_recent_food_entries(ctx, days: int = 7):
    """
    Get user's food entries from the last N days
    """
    from src.db.queries import get_food_entries_by_date
    import datetime

    deps = ctx.deps
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=days)

    entries = await get_food_entries_by_date(
        user_id=deps.user_id,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "entries": entries,
        "count": len(entries),
        "period_days": days
    }
```

**Why it's safe:**
- Uses whitelisted imports (`datetime`, `src.db.queries`)
- Calls approved database functions
- No file system or network access
- Returns safe data structures

### ✅ SAFE: Data Processing Tool

```python
async def calculate_weekly_average(ctx, category: str):
    """
    Calculate average for a tracking category over 7 days
    """
    from src.db.queries import get_tracking_entries
    import datetime

    deps = ctx.deps
    entries = await get_tracking_entries(
        user_id=deps.user_id,
        category=category,
        days=7
    )

    if not entries:
        return {"average": 0, "count": 0}

    values = [entry['value'] for entry in entries]
    average = sum(values) / len(values)

    return {
        "category": category,
        "average": round(average, 2),
        "count": len(values),
        "min": min(values),
        "max": max(values)
    }
```

**Why it's safe:**
- Only uses safe built-ins (`sum`, `len`, `min`, `max`)
- No dangerous operations
- Resource usage is minimal

### ❌ UNSAFE: File System Access

```python
async def read_config_file(ctx):
    """
    BLOCKED: This will fail validation
    """
    with open('/etc/passwd', 'r') as f:  # ❌ File access blocked
        return f.read()
```

**Why it's blocked:**
- `open()` is not in the safe builtins list
- File system access is prohibited
- This would fail during AST validation

### ❌ UNSAFE: Code Execution

```python
async def execute_user_code(ctx, user_code: str):
    """
    BLOCKED: This will fail validation
    """
    result = eval(user_code)  # ❌ eval() blocked
    return {"result": result}
```

**Why it's blocked:**
- `eval()` is explicitly blocked
- Arbitrary code execution is prohibited
- This would fail during AST validation

### ❌ UNSAFE: Import Bypass

```python
async def import_dangerous_module(ctx):
    """
    BLOCKED: This will fail validation
    """
    os = __import__('os')  # ❌ __import__ blocked
    return os.listdir('/')
```

**Why it's blocked:**
- `__import__` is blocked
- `os` module is not whitelisted
- This would fail during AST and RestrictedPython validation

### ❌ UNSAFE: Attribute Access

```python
async def access_internals(ctx):
    """
    BLOCKED: This will fail validation
    """
    secrets = ctx.__dict__  # ❌ __dict__ access blocked
    return secrets
```

**Why it's blocked:**
- `__dict__` attribute access is prohibited
- Prevents access to internal object state
- This would fail during AST validation

## Security Event Monitoring

All security violations are logged to the `tool_security_events` table:

```sql
SELECT
    event_type,
    severity,
    user_id,
    error_details,
    created_at
FROM tool_security_events
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

### Event Types

- `validation_failure` - Code failed AST validation
- `sandbox_violation` - Code violated sandbox restrictions
- `rate_limit_exceeded` - User exceeded rate limits
- `timeout_exceeded` - Execution exceeded 5 seconds
- `resource_limit_exceeded` - Memory or CPU limit exceeded
- `suspicious_pattern` - Anomaly detection triggered
- `compilation_error` - Code failed to compile

### Severity Levels

- **Critical** - Attempted code injection, privilege escalation
- **High** - Dangerous patterns, repeated violations
- **Medium** - Rate limit violations, unusual patterns
- **Low** - Syntax errors, minor validation failures

## Admin Tools

### Check User Risk Score

```sql
SELECT * FROM user_security_risk_scores
WHERE risk_score > 10
ORDER BY risk_score DESC;
```

### View Recent Security Events

```sql
SELECT * FROM security_events_summary
WHERE hour > NOW() - INTERVAL '24 hours';
```

### Disable Suspicious Tool

```sql
UPDATE dynamic_tools
SET
    is_enabled = FALSE,
    auto_disabled_reason = 'Multiple security violations'
WHERE id = 'tool-uuid';
```

## Best Practices

### For Users Creating Tools

1. **Start Simple** - Test with minimal functionality first
2. **Use Whitelisted Imports** - Stick to allowed modules
3. **Handle Errors Gracefully** - Check for None/empty results
4. **Avoid Complexity** - Complex logic may hit timeout limits
5. **Test Locally** - Validate logic before creating tool

### For Administrators

1. **Monitor Security Events** - Review daily
2. **Investigate High-Risk Users** - Check risk scores weekly
3. **Review New Tools** - Audit new tool creations
4. **Update Whitelist Carefully** - Only add trusted modules
5. **Run Security Scans** - Periodic penetration testing

## Incident Response

If a security breach is detected:

1. **Immediate Actions:**
   - Disable affected tool(s)
   - Block affected user(s)
   - Review security event logs

2. **Investigation:**
   - Analyze attack vector
   - Check for similar patterns
   - Assess damage/exposure

3. **Remediation:**
   - Patch vulnerability
   - Update validation rules
   - Notify affected users (if needed)

4. **Prevention:**
   - Update documentation
   - Enhance monitoring
   - Conduct security training

## Frequently Asked Questions

### Q: Why can't I import `requests` to fetch data?

**A:** Network access is prohibited to prevent:
- Data exfiltration to external servers
- SSRF attacks
- DoS attacks via network flooding

Use approved database functions or API integrations instead.

### Q: My tool times out after 5 seconds. Can I increase the limit?

**A:** No, the 5-second limit is fixed for security. Optimize your code:
- Use database indexes
- Limit result set sizes
- Avoid nested loops
- Use list comprehensions

### Q: Why can't I use try/except for error handling?

**A:** Try/except is currently blocked to prevent:
- Suppressing security errors
- Hiding malicious behavior
- Bypassing validation checks

Use defensive programming instead (check for None, validate inputs).

### Q: Can I create a tool that modifies other tools?

**A:** No, tools cannot modify other tools or access tool metadata. Each tool operates in isolation.

## Security Audit History

- **2026-01-18** - Phase 3.5 implemented (RestrictedPython, sandboxing)
- **2025-XX-XX** - Phase 3.0 implemented (basic AST validation)
- **2025-XX-XX** - Initial dynamic tool system deployed

## Contact

For security concerns or vulnerability reports:
- Email: security@healthagent.example.com (if applicable)
- Create a private security issue in GitHub
- Contact system administrators directly

---

**Last Updated:** 2026-01-18
**Security Version:** Phase 3.5
**Compliance:** Internal Security Standards
