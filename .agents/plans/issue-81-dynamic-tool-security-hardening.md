# Phase 3.5: Security Hardening for Dynamic Tool Execution

**Epic Reference**: [Epic 008: Phase 3 Long-Term Architecture](https://github.com/gpt153/health-agent-planning/blob/main/.bmad/epic-008-phase3-architecture.md)

**Issue**: #81

**Priority**: CRITICAL

**Estimated Time**: 12-16 hours

---

## Executive Summary

Current `dynamic_tools.py` uses Python's `exec()` to run user-generated code, creating a **CRITICAL SECURITY VULNERABILITY**. This plan provides a comprehensive approach to harden the system using sandboxed execution with RestrictedPython.

---

## Current State Analysis

### Security Audit Findings

**Critical Vulnerability Location**: `src/agent/dynamic_tools.py:240`
```python
exec(compile(function_code, f"<dynamic_tool_{tool_name}>", "exec"), namespace)
```

**Current Protection Mechanisms** (INSUFFICIENT):
1. ✅ AST parsing for syntax validation
2. ✅ Regex-based pattern blocking for dangerous keywords
3. ✅ Import whitelist (limited to: json, datetime, uuid, typing, src.db.queries, src.db.connection)
4. ✅ Read/write tool classification
5. ❌ **NO runtime sandbox** - exec runs with full interpreter privileges
6. ❌ **NO resource limits** - can consume unlimited CPU/memory
7. ❌ **NO timeout protection** - can run indefinitely
8. ❌ **NO process isolation** - runs in main process
9. ❌ **NO comprehensive audit logging** - only basic tool execution logs

### Attack Surface

**What an attacker could do**:
1. **Arbitrary Code Execution**: Bypass regex filters using encoding tricks
2. **Data Exfiltration**: Access database connection pool, read all user data
3. **Denial of Service**: Infinite loops, memory exhaustion
4. **Privilege Escalation**: Import restricted modules via `__import__`
5. **Persistence**: Modify global state, inject code into other tools

**Example Attack Vectors**:
```python
# Bypass import filter
__import__('os').system('rm -rf /')

# Access private attributes
ctx.deps.__dict__['database'].execute('DROP TABLE users')

# Infinite loop DoS
while True: pass

# Memory exhaustion
x = [1] * 10**10
```

### Current Usage Statistics

**Dynamic Tools in Database**: Unknown (requires query)
**Tool Execution Logs**: Present in `tool_executions` table
**Rate Limiting**: ❌ Not implemented
**Admin Approval Workflow**: ✅ Partially implemented (see `src/bot.py:589`)

---

## Recommended Approach: Option A+

**Hybrid approach combining the best of all options**:
- **RestrictedPython** for AST-based sandboxing
- **Process isolation** for defense in depth
- **Resource limits** (CPU, memory, timeout)
- **Enhanced validation** with comprehensive AST analysis
- **Rate limiting** to prevent abuse
- **Comprehensive audit logging** with anomaly detection

### Why Not Option B or C?

- **Option B (Remove Dynamic Tools)**: Loses core self-extending capability
- **Option C (Safe Expressions Only)**: Too limiting for database queries and complex logic
- **Option A+**: Maintains functionality while achieving security

---

## Implementation Plan

### Phase 1: Foundation (4 hours)

#### 1.1: Install Dependencies
- Add `RestrictedPython>=7.0` to `requirements.txt`
- Add `psutil>=5.9.0` for resource monitoring
- Add `resource` module usage (built-in on Unix)

#### 1.2: Create Security Module
**File**: `src/agent/security/sandbox.py`

```python
"""
Sandboxed execution environment for dynamic tools
"""
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import guarded_iter_unpack_sequence
import multiprocessing
import signal
import resource
import psutil
from typing import Any, Dict, Callable
import logging

class SandboxViolation(Exception):
    """Raised when sandbox restrictions are violated"""
    pass

class SandboxExecutor:
    """Execute code in restricted environment"""

    MAX_EXECUTION_TIME = 5  # seconds
    MAX_MEMORY_MB = 50
    MAX_CPU_PERCENT = 25

    def execute_sandboxed(
        self,
        code: str,
        namespace: Dict[str, Any],
        timeout: int = MAX_EXECUTION_TIME
    ) -> Any:
        """Execute code in sandbox with resource limits"""
        # Implementation details below
```

**Key Features**:
- Compile with `RestrictedPython.compile_restricted()`
- Use safe_globals with whitelisted builtins
- Execute in subprocess with resource limits
- Timeout protection with signal.alarm() or multiprocessing.Process
- Memory monitoring with psutil

#### 1.3: Enhanced AST Analyzer
**File**: `src/agent/security/ast_analyzer.py`

```python
"""
Advanced AST analysis for code validation
"""
import ast
from typing import List, Tuple, Optional

class ASTSecurityAnalyzer:
    """Analyze AST for security violations"""

    ALLOWED_NODES = {
        ast.AsyncFunctionDef, ast.FunctionDef, ast.Assign,
        ast.AugAssign, ast.Return, ast.Await, ast.Call,
        ast.Attribute, ast.Name, ast.Constant, ast.List,
        ast.Dict, ast.Tuple, ast.Compare, ast.BinOp,
        ast.UnaryOp, ast.BoolOp, ast.If, ast.For,
        ast.AsyncFor, ast.ListComp, ast.DictComp,
        ast.JoinedStr, ast.FormattedValue,  # f-strings
    }

    BLOCKED_ATTRIBUTES = {
        '__globals__', '__code__', '__dict__',
        '__class__', '__bases__', '__subclasses__',
        '__import__', 'eval', 'exec', 'compile'
    }

    def validate_ast(self, tree: ast.AST) -> Tuple[bool, Optional[str]]:
        """Deep AST validation"""
        # Check all nodes
        # Verify attribute access
        # Ensure no dangerous operations
```

### Phase 2: Core Security (4 hours)

#### 2.1: Refactor DynamicToolManager
**File**: `src/agent/dynamic_tools.py`

**Changes**:
1. Replace `exec()` with `SandboxExecutor.execute_sandboxed()`
2. Add comprehensive AST validation before compilation
3. Integrate resource limits
4. Add per-tool execution metadata

**Before**:
```python
exec(compile(function_code, f"<dynamic_tool_{tool_name}>", "exec"), namespace)
```

**After**:
```python
from src.agent.security.sandbox import SandboxExecutor, SandboxViolation
from src.agent.security.ast_analyzer import ASTSecurityAnalyzer

sandbox = SandboxExecutor()
ast_analyzer = ASTSecurityAnalyzer()

# Validate AST
is_valid, error = ast_analyzer.validate_ast(ast.parse(function_code))
if not is_valid:
    raise CodeValidationError(f"AST validation failed: {error}")

# Compile in restricted mode
func = sandbox.execute_sandboxed(function_code, namespace, timeout=5)
```

#### 2.2: Tool Execution Wrapper
**File**: `src/agent/dynamic_tools.py`

Update `execute_tool_with_logging()`:
- Wrap execution in try/except for SandboxViolation
- Log all security violations to separate table
- Automatically disable tools that violate sandbox
- Alert admins on suspicious activity

#### 2.3: Safe Globals Configuration
Define minimal safe environment:
```python
safe_namespace = {
    '__builtins__': {
        'None': None,
        'False': False,
        'True': True,
        'abs': abs,
        'bool': bool,
        'dict': dict,
        'float': float,
        'int': int,
        'len': len,
        'list': list,
        'max': max,
        'min': min,
        'range': range,
        'round': round,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'zip': zip,
    },
    # Allowed imports (controlled)
    'json': json,
    'datetime': datetime,
    'uuid4': uuid4,
    # Result models
    # DB query functions (wrapped with safety checks)
}
```

### Phase 3: Rate Limiting & Monitoring (2 hours)

#### 3.1: Rate Limiter
**File**: `src/agent/security/rate_limiter.py`

```python
"""
Rate limiting for tool creation and execution
"""
from datetime import datetime, timedelta
from typing import Dict
import asyncio

class RateLimiter:
    """Token bucket rate limiter"""

    # Limits
    TOOL_CREATION_LIMIT = 5  # per user per day
    TOOL_EXECUTION_LIMIT = 100  # per user per day

    async def check_tool_creation_limit(self, user_id: str) -> bool:
        """Check if user can create another tool"""
        # Query database for today's creation count
        # Return True if under limit

    async def check_execution_limit(self, user_id: str) -> bool:
        """Check if user can execute another tool"""
        # Query database for today's execution count
        # Return True if under limit
```

**Integration Points**:
- `create_dynamic_tool()` in `src/agent/__init__.py:2156`
- `execute_tool_with_logging()` in `src/agent/dynamic_tools.py:277`

#### 3.2: Enhanced Audit Logging
**File**: `src/db/queries.py`

New table: `tool_security_events`
```sql
CREATE TABLE tool_security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,  -- 'validation_failure', 'sandbox_violation', 'rate_limit_exceeded'
    tool_id UUID REFERENCES dynamic_tools(id),
    user_id TEXT NOT NULL,
    code_snippet TEXT,
    error_details JSONB,
    severity TEXT,  -- 'low', 'medium', 'high', 'critical'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_security_events_user ON tool_security_events(user_id, created_at);
CREATE INDEX idx_security_events_severity ON tool_security_events(severity, created_at);
```

New functions:
```python
async def log_security_event(
    event_type: str,
    tool_id: Optional[str],
    user_id: str,
    code_snippet: str,
    error_details: dict,
    severity: str
) -> str:
    """Log security event for monitoring"""

async def get_user_security_events(
    user_id: str,
    hours: int = 24
) -> List[dict]:
    """Get recent security events for user"""

async def get_high_severity_events(
    hours: int = 1
) -> List[dict]:
    """Get recent high-severity events for admin alerts"""
```

#### 3.3: Anomaly Detection
**File**: `src/agent/security/anomaly_detector.py`

```python
"""
Detect suspicious patterns in tool usage
"""

class AnomalyDetector:
    """Detect anomalous tool behavior"""

    async def analyze_tool_execution(
        self,
        user_id: str,
        tool_id: str,
        code: str,
        result: Any
    ) -> List[str]:
        """
        Returns list of anomaly flags:
        - 'rapid_execution': Too many executions in short time
        - 'unusual_patterns': Code patterns not seen before
        - 'error_spike': High error rate
        - 'resource_abuse': Consistently hitting resource limits
        """
```

### Phase 4: Testing & Validation (3 hours)

#### 4.1: Security Test Suite
**File**: `tests/security/test_sandbox.py`

```python
"""
Comprehensive security tests for sandboxed execution
"""
import pytest
from src.agent.security.sandbox import SandboxExecutor, SandboxViolation

class TestSandbox:
    """Test sandbox security"""

    async def test_blocks_import_bypass(self):
        """Test that import bypasses are blocked"""
        malicious_code = "__import__('os').system('ls')"
        with pytest.raises(SandboxViolation):
            await executor.execute_sandboxed(malicious_code, {})

    async def test_blocks_attribute_access(self):
        """Test that private attribute access is blocked"""
        malicious_code = "ctx.__dict__['secret']"
        with pytest.raises(SandboxViolation):
            await executor.execute_sandboxed(malicious_code, namespace)

    async def test_timeout_protection(self):
        """Test that infinite loops are terminated"""
        infinite_loop = "while True: pass"
        with pytest.raises(TimeoutError):
            await executor.execute_sandboxed(infinite_loop, {}, timeout=1)

    async def test_memory_limits(self):
        """Test that memory exhaustion is prevented"""
        memory_bomb = "x = [1] * 10**10"
        with pytest.raises(MemoryError):
            await executor.execute_sandboxed(memory_bomb, {})

    async def test_benign_code_works(self):
        """Test that legitimate code still executes"""
        benign_code = """
async def get_user_info(ctx):
    return {"name": "test"}
"""
        result = await executor.execute_sandboxed(benign_code, namespace)
        assert result is not None
```

#### 4.2: Penetration Testing Scenarios
**File**: `tests/security/test_pentest.py`

Test cases for:
1. ✅ Import statement bypasses
2. ✅ Attribute access escalation
3. ✅ Code injection via parameters
4. ✅ Resource exhaustion attacks
5. ✅ SQL injection via generated queries
6. ✅ Unicode/encoding-based bypasses
7. ✅ Timing attacks
8. ✅ Serialization exploits

#### 4.3: Integration Tests
**File**: `tests/integration/test_dynamic_tools_security.py`

End-to-end tests:
- Create tool with malicious code → should be rejected
- Execute legitimate tool → should work normally
- Exceed rate limits → should be blocked
- Trigger anomaly detection → should log alert
- Test tool versioning with security changes

### Phase 5: Documentation & Deployment (2 hours)

#### 5.1: User Documentation
**File**: `docs/DYNAMIC_TOOLS_SECURITY.md`

```markdown
# Dynamic Tools Security Guide

## What Code is Allowed

### ✅ Allowed Operations
- Basic Python operators (+, -, *, /, ==, !=, etc.)
- Built-in functions: len(), str(), int(), list(), dict()
- Whitelisted imports: json, datetime, uuid
- Database queries via src.db.queries.*
- Async/await syntax

### ❌ Blocked Operations
- Import statements (except whitelisted)
- File system access (open, read, write)
- Network access (socket, requests, urllib)
- System commands (os.system, subprocess)
- Code execution (eval, exec, compile)
- Private attribute access (__dict__, __globals__)

## Resource Limits
- **Execution time**: 5 seconds maximum
- **Memory**: 50 MB maximum
- **CPU**: 25% maximum

## Rate Limits
- **Tool creation**: 5 per day per user
- **Tool execution**: 100 per day per user

## Examples

### ✅ Safe Tool Example
```python
async def get_recent_entries(ctx, category: str, days: int):
    from src.db.queries import get_tracking_entries
    entries = await get_tracking_entries(
        user_id=ctx.deps.user_id,
        category=category,
        days=days
    )
    return {"entries": entries, "count": len(entries)}
```

### ❌ Unsafe Tool Example (Rejected)
```python
async def dangerous_tool(ctx):
    import os  # ❌ Blocked import
    os.system('rm -rf /')  # ❌ System command
    return "Done"
```
```

#### 5.2: Admin Documentation
**File**: `docs/DYNAMIC_TOOLS_MONITORING.md`

- How to monitor security events dashboard
- Anomaly detection alerts
- How to investigate suspicious tools
- Emergency response procedures

#### 5.3: Migration Guide
**File**: `docs/DYNAMIC_TOOLS_MIGRATION.md`

- Backward compatibility considerations
- How existing tools are affected
- Revalidation process for existing tools
- Timeline for deprecating old execution method

#### 5.4: Deployment Checklist
```markdown
## Pre-Deployment
- [ ] All tests passing (unit, integration, security)
- [ ] Code review by 2+ developers
- [ ] External security review completed
- [ ] Database migrations tested on staging
- [ ] Rate limiter tested under load
- [ ] Documentation reviewed and published

## Deployment
- [ ] Deploy to staging environment
- [ ] Run security test suite on staging
- [ ] Monitor for 24 hours on staging
- [ ] Deploy to production (gradual rollout)
- [ ] Enable security event monitoring
- [ ] Set up alerting for high-severity events

## Post-Deployment
- [ ] Monitor security events dashboard for 7 days
- [ ] Review anomaly detection patterns
- [ ] Tune rate limits based on usage
- [ ] Gather user feedback
- [ ] Document lessons learned
```

---

## Database Schema Changes

### New Table: `tool_security_events`
```sql
CREATE TABLE tool_security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    tool_id UUID REFERENCES dynamic_tools(id),
    user_id TEXT NOT NULL,
    code_snippet TEXT,
    error_details JSONB,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_security_events_user ON tool_security_events(user_id, created_at DESC);
CREATE INDEX idx_security_events_severity ON tool_security_events(severity, created_at DESC);
CREATE INDEX idx_security_events_type ON tool_security_events(event_type, created_at DESC);
```

### New Table: `rate_limit_tracking`
```sql
CREATE TABLE rate_limit_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    action_type TEXT NOT NULL,  -- 'tool_creation', 'tool_execution'
    action_count INT DEFAULT 1,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rate_limit_user_action ON rate_limit_tracking(user_id, action_type, window_end DESC);
```

---

## Success Metrics

### Security Metrics
- ✅ **Zero successful sandbox escapes** in penetration testing
- ✅ **Zero arbitrary code execution vulnerabilities**
- ✅ **100% of dangerous operations blocked**
- ✅ **Resource limits enforced** (no OOM crashes)
- ✅ **Timeout protection working** (no infinite loops)

### Performance Metrics
- ✅ **Tool execution latency** < 100ms overhead
- ✅ **Tool creation validation** < 500ms
- ✅ **Rate limiter overhead** < 10ms per check
- ✅ **No impact on non-dynamic tool performance**

### Operational Metrics
- ✅ **Security events dashboard** operational
- ✅ **Admin alerts** for high-severity events
- ✅ **Anomaly detection** catching suspicious patterns
- ✅ **Zero false positives** blocking legitimate tools

---

## Risk Assessment

### Residual Risks (Post-Implementation)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| RestrictedPython bypass | Low | High | Regular updates, external security audits |
| Resource limit bypass | Very Low | Medium | Process isolation, OS-level limits |
| Timing-based side channel | Low | Low | Rate limiting, execution time jitter |
| Admin account compromise | Low | Critical | MFA required, audit logging |

### Risk Acceptance
- **Dynamic tool functionality maintained**: Accept minimal residual risk for core capability
- **Defense in depth**: Multiple layers (AST, RestrictedPython, resource limits, monitoring)
- **Rapid response**: Security event monitoring enables quick incident response

---

## Timeline

### Week 1: Foundation & Core Security (Days 1-5)
- Day 1: Install dependencies, create security module structure
- Day 2: Implement SandboxExecutor with RestrictedPython
- Day 3: Build AST analyzer and enhanced validation
- Day 4: Refactor DynamicToolManager to use sandbox
- Day 5: Testing and debugging

### Week 2: Monitoring & Hardening (Days 6-10)
- Day 6: Implement rate limiter
- Day 7: Create audit logging infrastructure
- Day 8: Build anomaly detector
- Day 9: Security test suite (penetration tests)
- Day 10: Integration tests

### Week 3: Documentation & Deployment (Days 11-12)
- Day 11: Write documentation (user + admin)
- Day 12: External security review, staging deployment

### Week 4: Production Rollout (Days 13-14)
- Day 13: Production deployment (gradual)
- Day 14: Monitoring and tuning

---

## Definition of Done

- [x] Audit of current implementation completed
- [ ] RestrictedPython integration complete
- [ ] AST security analyzer implemented
- [ ] Sandbox executor with resource limits working
- [ ] Rate limiting functional
- [ ] Comprehensive audit logging in place
- [ ] Security event monitoring dashboard operational
- [ ] Anomaly detection system deployed
- [ ] All security tests passing (100% coverage of attack vectors)
- [ ] Penetration testing completed with zero critical findings
- [ ] User documentation published
- [ ] Admin monitoring guide published
- [ ] External security review passed
- [ ] Production deployment successful
- [ ] 7-day monitoring period completed with no incidents

---

## Open Questions

1. **Should we revalidate all existing dynamic tools in database?**
   - Recommendation: Yes, run migration script to revalidate with new security rules
   - Some tools may fail validation and require user update

2. **What should be the escalation path for security events?**
   - Recommendation:
     - Low/Medium: Log only
     - High: Email admin
     - Critical: Disable tool + immediate Telegram alert

3. **Should rate limits be configurable per user or global?**
   - Recommendation: Per-user with admin override capability

4. **How to handle legitimate edge cases that trigger sandbox violations?**
   - Recommendation: Admin approval workflow for exceptions (already partially exists)

---

## References

- [RestrictedPython Documentation](https://restrictedpython.readthedocs.io/)
- [OWASP Code Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)
- [Python Sandboxing Best Practices](https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html)
- [Epic 008: Phase 3 Architecture](https://github.com/gpt153/health-agent-planning/blob/main/.bmad/epic-008-phase3-architecture.md)

---

**Author**: SCAR Agent
**Date**: 2026-01-15
**Status**: Approved (Pending Implementation)
**Priority**: CRITICAL
