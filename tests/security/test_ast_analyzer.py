"""
Tests for AST security analyzer

Validates that the AST analyzer correctly:
- Allows safe code patterns
- Blocks dangerous operations
- Detects security violations
"""

import pytest
from src.agent.security.ast_analyzer import (
    ASTSecurityAnalyzer,
    ASTValidationError,
    validate_tool_code_ast
)


class TestASTSecurityAnalyzer:
    """Test AST-based security validation"""

    def test_allows_simple_async_function(self):
        """Test that simple async functions pass validation"""
        code = """
async def get_user_data(ctx, user_id: str):
    return {"user_id": user_id, "status": "active"}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid code rejected: {error}"

    def test_allows_database_query(self):
        """Test that database queries are allowed"""
        code = """
async def get_entries(ctx, category: str):
    from src.db.queries import get_tracking_entries
    entries = await get_tracking_entries(ctx.deps.user_id, category)
    return {"entries": entries, "count": len(entries)}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid code rejected: {error}"

    def test_allows_json_module(self):
        """Test that json module is allowed"""
        code = """
async def parse_json(ctx, data: str):
    import json
    return json.loads(data)
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid code rejected: {error}"

    def test_blocks_os_import(self):
        """Test that os module import is blocked"""
        code = """
async def dangerous(ctx):
    import os
    return os.listdir('/')
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "Dangerous os import should be blocked"
        assert "os" in error.lower()

    def test_blocks_subprocess_import(self):
        """Test that subprocess import is blocked"""
        code = """
async def dangerous(ctx):
    import subprocess
    subprocess.run(['ls', '-la'])
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "Dangerous subprocess import should be blocked"
        assert "subprocess" in error.lower()

    def test_blocks_eval_usage(self):
        """Test that eval() is blocked"""
        code = """
async def dangerous(ctx, code: str):
    result = eval(code)
    return result
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "eval() should be blocked"
        assert "eval" in error.lower()

    def test_blocks_exec_usage(self):
        """Test that exec() is blocked"""
        code = """
async def dangerous(ctx, code: str):
    exec(code)
    return "done"
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "exec() should be blocked"
        assert "exec" in error.lower()

    def test_blocks_import_bypass(self):
        """Test that __import__ bypass is blocked"""
        code = """
async def dangerous(ctx):
    os = __import__('os')
    return os.system('ls')
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "__import__ should be blocked"
        assert "__import__" in error.lower() or "import" in error.lower()

    def test_blocks_globals_access(self):
        """Test that __globals__ access is blocked"""
        code = """
async def dangerous(ctx):
    secrets = ctx.__globals__
    return secrets
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "__globals__ access should be blocked"
        assert "__globals__" in error.lower() or "attribute" in error.lower()

    def test_blocks_dict_access(self):
        """Test that __dict__ access is blocked"""
        code = """
async def dangerous(ctx):
    internal = ctx.__dict__
    return internal
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "__dict__ access should be blocked"
        assert "__dict__" in error.lower() or "attribute" in error.lower()

    def test_blocks_class_access(self):
        """Test that __class__ manipulation is blocked"""
        code = """
async def dangerous(ctx):
    cls = ctx.__class__
    return cls.__bases__
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "__class__ access should be blocked"

    def test_requires_ctx_parameter(self):
        """Test that ctx parameter is required"""
        code = """
async def missing_ctx(user_id: str):
    return {"user_id": user_id}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "Function without ctx should be rejected"
        assert "ctx" in error.lower()

    def test_blocks_open_function(self):
        """Test that open() is blocked"""
        code = """
async def dangerous(ctx):
    with open('/etc/passwd', 'r') as f:
        return f.read()
"""
        is_valid, error = validate_tool_code_ast(code)
        # Note: 'with' might be allowed, but 'open' should be blocked
        # This test might need adjustment based on ALLOWED_NODES
        assert not is_valid or "open" in error.lower()

    def test_allows_string_operations(self):
        """Test that string operations are allowed"""
        code = """
async def process_string(ctx, text: str):
    result = text.upper().strip()
    return {"processed": result, "length": len(result)}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid string operations rejected: {error}"

    def test_allows_list_comprehension(self):
        """Test that list comprehensions are allowed"""
        code = """
async def filter_data(ctx, items: list):
    filtered = [x for x in items if x > 0]
    return {"filtered": filtered, "count": len(filtered)}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid list comprehension rejected: {error}"

    def test_allows_dict_comprehension(self):
        """Test that dict comprehensions are allowed"""
        code = """
async def transform_data(ctx, items: dict):
    transformed = {k.upper(): v * 2 for k, v in items.items()}
    return transformed
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid dict comprehension rejected: {error}"

    def test_allows_f_strings(self):
        """Test that f-strings are allowed"""
        code = """
async def format_message(ctx, name: str, count: int):
    message = f"Hello {name}, you have {count} items"
    return {"message": message}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Valid f-string rejected: {error}"

    def test_blocks_try_except(self):
        """Test that try/except is blocked (prevents error suppression)"""
        code = """
async def with_error_handling(ctx):
    try:
        result = some_function()
        return result
    except:
        return None
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "Try/except should be blocked to prevent error suppression"

    def test_detects_syntax_error(self):
        """Test that syntax errors are detected"""
        code = """
async def broken(ctx):
    return "missing quote
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "Syntax errors should be caught"
        assert "syntax" in error.lower()

    def test_blocks_compile_function(self):
        """Test that compile() is blocked"""
        code = """
async def dangerous(ctx, code: str):
    compiled = compile(code, '<string>', 'exec')
    return compiled
"""
        is_valid, error = validate_tool_code_ast(code)
        assert not is_valid, "compile() should be blocked"
        assert "compile" in error.lower()


class TestASTAnalyzerEdgeCases:
    """Test edge cases and complex scenarios"""

    def test_nested_function_allowed(self):
        """Test that nested helper functions are allowed"""
        code = """
async def main_tool(ctx, data: list):
    def helper(x):
        return x * 2

    results = [helper(item) for item in data]
    return {"results": results}
"""
        is_valid, error = validate_tool_code_ast(code)
        # Nested functions should be allowed for helper logic
        assert is_valid, f"Nested functions should be allowed: {error}"

    def test_multiple_imports_validated(self):
        """Test that multiple imports are all validated"""
        code = """
async def multi_import(ctx):
    import json
    import datetime
    from uuid import uuid4

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "id": str(uuid4())
    }
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Multiple allowed imports rejected: {error}"

    def test_chained_attribute_access(self):
        """Test that chained attribute access is validated"""
        code = """
async def chain_access(ctx):
    value = ctx.deps.user_id
    return {"user": value}
"""
        is_valid, error = validate_tool_code_ast(code)
        assert is_valid, f"Safe attribute chain rejected: {error}"
