"""
Standalone tests for AST analyzer (without full app imports)
"""

import ast
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


def test_ast_parsing():
    """Test that we can parse simple AST"""
    code = """
async def test_func(ctx):
    return {"result": "success"}
"""
    tree = ast.parse(code)
    assert tree is not None
    assert len(tree.body) == 1
    assert isinstance(tree.body[0], ast.AsyncFunctionDef)


def test_ast_import_detection():
    """Test that we can detect imports in AST"""
    code = """
async def test_func(ctx):
    import os
    return os.getcwd()
"""
    tree = ast.parse(code)

    imports_found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports_found.append(alias.name)

    assert 'os' in imports_found


def test_ast_attribute_access():
    """Test that we can detect attribute access"""
    code = """
async def test_func(ctx):
    return ctx.__dict__
"""
    tree = ast.parse(code)

    attributes_found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            attributes_found.append(node.attr)

    assert '__dict__' in attributes_found


if __name__ == '__main__':
    test_ast_parsing()
    test_ast_import_detection()
    test_ast_attribute_access()
    print("✅ All standalone AST tests passed!")
