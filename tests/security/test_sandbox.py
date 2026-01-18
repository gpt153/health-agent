"""
Tests for sandboxed code execution

Validates that the sandbox:
- Executes safe code correctly
- Blocks dangerous operations
- Enforces resource limits
- Handles timeouts properly
"""

import pytest
import asyncio
from src.agent.security.sandbox import (
    SandboxExecutor,
    SandboxViolation,
    TimeoutException,
    ResourceLimitExceeded
)


class TestSandboxExecutor:
    """Test sandboxed execution"""

    @pytest.fixture
    def executor(self):
        """Create sandbox executor for tests"""
        return SandboxExecutor(
            max_execution_time=2,
            max_memory_mb=50,
            max_cpu_percent=25
        )

    def test_executes_simple_function(self, executor):
        """Test that simple functions execute correctly"""
        code = """
async def test_func(ctx):
    return {"result": "success", "value": 42}
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)

        assert func is not None
        assert callable(func)
        assert hasattr(func, '__name__')

    @pytest.mark.asyncio
    async def test_async_execution(self, executor):
        """Test that async functions execute correctly"""
        code = """
async def test_func(ctx):
    await asyncio.sleep(0.1)
    return {"status": "completed"}
"""
        namespace = {'asyncio': asyncio}
        func = executor.execute_sandboxed(code, namespace)

        # Create mock context
        class MockCtx:
            pass

        result = await executor.execute_async_sandboxed(func, MockCtx())
        assert result == {"status": "completed"}

    def test_blocks_import_bypass(self, executor):
        """Test that __import__ is blocked"""
        code = """
async def malicious(ctx):
    os = __import__('os')
    return os.listdir('/')
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    def test_blocks_eval_in_code(self, executor):
        """Test that eval() is blocked"""
        code = """
async def malicious(ctx):
    result = eval("1 + 1")
    return result
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    def test_blocks_exec_in_code(self, executor):
        """Test that exec() is blocked"""
        code = """
async def malicious(ctx):
    exec("print('hacked')")
    return "done"
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    def test_allows_safe_builtins(self, executor):
        """Test that safe builtins are available"""
        code = """
async def use_builtins(ctx):
    numbers = [1, 2, 3, 4, 5]
    return {
        "sum": sum(numbers),
        "max": max(numbers),
        "len": len(numbers),
        "sorted": sorted(numbers, reverse=True)
    }
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)
        assert func is not None

    @pytest.mark.asyncio
    async def test_timeout_protection(self, executor):
        """Test that infinite loops are terminated"""
        code = """
async def infinite_loop(ctx):
    while True:
        pass
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)

        class MockCtx:
            pass

        with pytest.raises(TimeoutException):
            await executor.execute_async_sandboxed(func, MockCtx(), timeout=1)

    @pytest.mark.asyncio
    async def test_timeout_with_sleep(self, executor):
        """Test timeout with slow async operations"""
        code = """
async def slow_function(ctx):
    await asyncio.sleep(10)
    return "done"
"""
        namespace = {'asyncio': asyncio}
        func = executor.execute_sandboxed(code, namespace)

        class MockCtx:
            pass

        with pytest.raises(TimeoutException):
            await executor.execute_async_sandboxed(func, MockCtx(), timeout=1)

    def test_safe_namespace_isolation(self, executor):
        """Test that namespace is isolated"""
        code = """
async def test_func(ctx):
    return {"value": test_var}
"""
        namespace = {'test_var': 'secret_value'}
        func = executor.execute_sandboxed(code, namespace)

        # Function should only see what's in namespace
        assert func is not None

    def test_blocks_file_operations(self, executor):
        """Test that file operations are blocked"""
        code = """
async def read_file(ctx):
    with open('/etc/passwd', 'r') as f:
        return f.read()
"""
        namespace = {}

        # This should fail during compilation
        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    def test_blocks_network_access(self, executor):
        """Test that network operations are blocked"""
        code = """
async def make_request(ctx):
    import requests
    return requests.get('https://evil.com').text
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    def test_allows_datetime_module(self, executor):
        """Test that datetime module is allowed"""
        code = """
async def get_timestamp(ctx):
    import datetime
    return {"timestamp": datetime.datetime.now().isoformat()}
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)
        assert func is not None

    def test_allows_json_module(self, executor):
        """Test that json module is allowed"""
        code = """
async def parse_json(ctx):
    import json
    data = '{"key": "value"}'
    return json.loads(data)
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)
        assert func is not None

    @pytest.mark.asyncio
    async def test_execution_with_parameters(self, executor):
        """Test execution with function parameters"""
        code = """
async def add_numbers(ctx, a: int, b: int):
    return {"result": a + b}
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)

        class MockCtx:
            pass

        result = await executor.execute_async_sandboxed(func, MockCtx(), 10, 20)
        assert result == {"result": 30}

    def test_handles_syntax_errors(self, executor):
        """Test that syntax errors are caught"""
        code = """
async def broken(ctx):
    return "unclosed string
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    def test_blocks_attribute_access_to_globals(self, executor):
        """Test that access to __globals__ is blocked"""
        code = """
async def access_globals(ctx):
    func = lambda: None
    return func.__globals__
"""
        namespace = {}

        # Should be blocked by RestrictedPython
        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    @pytest.mark.asyncio
    async def test_list_comprehension_works(self, executor):
        """Test that list comprehensions work"""
        code = """
async def filter_numbers(ctx, numbers: list):
    evens = [x for x in numbers if x % 2 == 0]
    return {"evens": evens, "count": len(evens)}
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)

        class MockCtx:
            pass

        result = await executor.execute_async_sandboxed(
            func,
            MockCtx(),
            [1, 2, 3, 4, 5, 6]
        )
        assert result == {"evens": [2, 4, 6], "count": 3}

    @pytest.mark.asyncio
    async def test_dict_operations_work(self, executor):
        """Test that dictionary operations work"""
        code = """
async def process_dict(ctx, data: dict):
    result = {k.upper(): v * 2 for k, v in data.items()}
    return result
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)

        class MockCtx:
            pass

        result = await executor.execute_async_sandboxed(
            func,
            MockCtx(),
            {"a": 1, "b": 2}
        )
        assert result == {"A": 2, "B": 4}


class TestPenetrationScenarios:
    """Penetration testing scenarios"""

    @pytest.fixture
    def executor(self):
        return SandboxExecutor()

    def test_bypass_via_encoding(self, executor):
        """Test that encoding-based bypasses are blocked"""
        code = """
async def bypass_attempt(ctx):
    # Try to use base64 to hide malicious code
    import base64
    evil_code = base64.b64decode(b'X19pbXBvcnRfXygnb3MnKS5zeXN0ZW0oJ2xzJyk=')
    exec(evil_code)
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    def test_bypass_via_getattr(self, executor):
        """Test that getattr-based bypasses are blocked"""
        code = """
async def bypass_attempt(ctx):
    # Try to access __import__ via getattr
    import_func = getattr(__builtins__, '__import__')
    os = import_func('os')
    return os.listdir('/')
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)

    @pytest.mark.asyncio
    async def test_resource_exhaustion_memory(self, executor):
        """Test that memory bombs are caught"""
        code = """
async def memory_bomb(ctx):
    # Try to allocate huge list
    big_list = [1] * (10**9)
    return len(big_list)
"""
        namespace = {}
        func = executor.execute_sandboxed(code, namespace)

        class MockCtx:
            pass

        # This should either fail during execution or be caught by memory limits
        # Depending on system, might raise MemoryError or ResourceLimitExceeded
        with pytest.raises((MemoryError, ResourceLimitExceeded, TimeoutException)):
            result = await executor.execute_async_sandboxed(func, MockCtx())

    def test_nested_import_bypass(self, executor):
        """Test that nested import attempts are blocked"""
        code = """
async def nested_bypass(ctx):
    # Try to import via importlib
    import importlib
    os = importlib.import_module('os')
    return os.getcwd()
"""
        namespace = {}

        with pytest.raises(SandboxViolation):
            executor.execute_sandboxed(code, namespace)
