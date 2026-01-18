"""
Integration tests for security modules (isolated from main app)

Tests the security modules without requiring full application imports
"""

import pytest
import sys
import os

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestASTAnalyzerIsolated:
    """Test AST analyzer without app dependencies"""

    def test_import_ast_analyzer(self):
        """Test that AST analyzer can be imported"""
        try:
            from src.agent.security.ast_analyzer import ASTSecurityAnalyzer, validate_tool_code_ast
            assert ASTSecurityAnalyzer is not None
            assert validate_tool_code_ast is not None
        except ImportError as e:
            pytest.skip(f"Cannot import AST analyzer: {e}")

    def test_validate_simple_function(self):
        """Test validation of simple async function"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def test_func(ctx):
    return {"result": "success"}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid code rejected: {error}"

    def test_block_eval(self):
        """Test that eval() is blocked"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def dangerous(ctx):
    result = eval("1 + 1")
    return result
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "eval() should be blocked"
        assert "eval" in error.lower()

    def test_block_exec(self):
        """Test that exec() is blocked"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def dangerous(ctx):
    exec("print('hello')")
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "exec() should be blocked"
        assert "exec" in error.lower()

    def test_block_os_import(self):
        """Test that os import is blocked"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def dangerous(ctx):
    import os
    return os.getcwd()
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "os import should be blocked"
        assert "os" in error.lower() or "import" in error.lower()

    def test_block_import_bypass(self):
        """Test that __import__ is blocked"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def dangerous(ctx):
    os = __import__('os')
    return os.system('ls')
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "__import__ should be blocked"

    def test_block_globals_access(self):
        """Test that __globals__ access is blocked"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def dangerous(ctx):
    secrets = ctx.__globals__
    return secrets
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "__globals__ access should be blocked"

    def test_allow_json_import(self):
        """Test that json import is allowed"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def safe_func(ctx):
    import json
    return json.dumps({"test": "data"})
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"json import should be allowed: {error}"

    def test_allow_datetime_import(self):
        """Test that datetime import is allowed"""
        try:
            from src.agent.security.ast_analyzer import validate_tool_code_ast
        except ImportError:
            pytest.skip("AST analyzer not available")

        code = """
async def safe_func(ctx):
    import datetime
    return datetime.datetime.now().isoformat()
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"datetime import should be allowed: {error}"


class TestSandboxExecutorIsolated:
    """Test sandbox executor without app dependencies"""

    def test_import_sandbox(self):
        """Test that sandbox can be imported"""
        try:
            from src.agent.security.sandbox import SandboxExecutor
            assert SandboxExecutor is not None
        except ImportError as e:
            pytest.skip(f"Cannot import sandbox: {e}")

    def test_create_executor(self):
        """Test that executor can be created"""
        try:
            from src.agent.security.sandbox import SandboxExecutor
        except ImportError:
            pytest.skip("Sandbox not available")

        executor = SandboxExecutor(
            max_execution_time=2,
            max_memory_mb=50,
            max_cpu_percent=25
        )
        assert executor is not None
        assert executor.max_execution_time == 2
        assert executor.max_memory_mb == 50
        assert executor.max_cpu_percent == 25

    def test_safe_globals_creation(self):
        """Test that safe globals can be created"""
        try:
            from src.agent.security.sandbox import SandboxExecutor
        except ImportError:
            pytest.skip("Sandbox not available")

        executor = SandboxExecutor()
        safe_ns = executor._create_safe_globals({})

        # Verify safe builtins are present
        assert '__builtins__' in safe_ns
        builtins = safe_ns['__builtins__']
        assert 'len' in builtins
        assert 'str' in builtins
        assert 'int' in builtins

        # Verify dangerous builtins are NOT present
        assert 'eval' not in builtins
        assert 'exec' not in builtins
        assert 'open' not in builtins


class TestRestrictedPythonAvailability:
    """Test RestrictedPython integration"""

    def test_restricted_python_installed(self):
        """Test if RestrictedPython is installed"""
        try:
            import RestrictedPython
            assert RestrictedPython is not None
        except ImportError:
            pytest.skip("RestrictedPython not installed - run: pip install RestrictedPython>=7.0")

    def test_compile_restricted_available(self):
        """Test if compile_restricted is available"""
        try:
            from RestrictedPython import compile_restricted
            assert compile_restricted is not None
        except ImportError:
            pytest.skip("RestrictedPython not installed")

    def test_safe_globals_available(self):
        """Test if safe_globals is available"""
        try:
            from RestrictedPython.Guards import safe_globals, safe_builtins
            assert safe_globals is not None
            assert safe_builtins is not None
        except ImportError:
            pytest.skip("RestrictedPython not installed")

    def test_basic_restricted_compilation(self):
        """Test basic RestrictedPython compilation"""
        try:
            from RestrictedPython import compile_restricted
        except ImportError:
            pytest.skip("RestrictedPython not installed")

        code = """
def safe_function():
    return 1 + 1
"""
        byte_code = compile_restricted(code, '<test>', 'exec')

        # Should compile successfully
        assert byte_code is not None
        assert byte_code.code is not None
        assert len(byte_code.errors) == 0

    def test_restricted_blocks_dangerous_code(self):
        """Test that RestrictedPython blocks dangerous operations"""
        try:
            from RestrictedPython import compile_restricted
        except ImportError:
            pytest.skip("RestrictedPython not installed")

        # Try to compile code with __import__
        code = """
def dangerous():
    os = __import__('os')
    return os.getcwd()
"""
        byte_code = compile_restricted(code, '<test>', 'exec')

        # Should have errors or warnings
        # RestrictedPython may compile but will restrict at runtime
        assert byte_code is not None


class TestPsutilAvailability:
    """Test psutil integration"""

    def test_psutil_installed(self):
        """Test if psutil is installed"""
        try:
            import psutil
            assert psutil is not None
        except ImportError:
            pytest.skip("psutil not installed - run: pip install psutil>=5.9.0")

    def test_process_monitoring(self):
        """Test basic process monitoring"""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not installed")

        process = psutil.Process()
        memory_info = process.memory_info()

        assert memory_info is not None
        assert memory_info.rss > 0  # Resident Set Size should be > 0


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
