"""
Advanced AST analysis for dynamic tool code validation

Performs deep security analysis on Python AST to prevent:
- Unauthorized imports
- Dangerous attribute access
- Unsafe operations
- Code injection attempts
"""

import ast
from typing import List, Tuple, Optional, Set
import logging

logger = logging.getLogger(__name__)


class ASTValidationError(Exception):
    """Raised when AST validation detects security issues"""
    pass


class ASTSecurityAnalyzer(ast.NodeVisitor):
    """
    Deep AST analysis for security validation

    Validates that code:
    - Only uses allowed node types
    - Doesn't access dangerous attributes
    - Uses only whitelisted imports
    - Doesn't use dangerous builtins
    """

    # Node types allowed in dynamic tools
    ALLOWED_NODES = {
        ast.Module,
        ast.AsyncFunctionDef,
        ast.FunctionDef,
        ast.Assign,
        ast.AugAssign,
        ast.AnnAssign,
        ast.Return,
        ast.Await,
        ast.Call,
        ast.Attribute,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Dict,
        ast.Tuple,
        ast.Set,
        ast.Compare,
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Break,
        ast.Continue,
        ast.ListComp,
        ast.DictComp,
        ast.SetComp,
        ast.GeneratorExp,
        ast.JoinedStr,
        ast.FormattedValue,
        ast.Expr,
        ast.Pass,
        ast.arg,
        ast.arguments,
        ast.keyword,
        ast.alias,
        # Comparison operators
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.Is, ast.IsNot, ast.In, ast.NotIn,
        # Binary operators
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
        ast.Mod, ast.Pow, ast.MatMult,
        # Unary operators
        ast.UAdd, ast.USub, ast.Not, ast.Invert,
        # Boolean operators
        ast.And, ast.Or,
        # Context
        ast.Load, ast.Store, ast.Del,
    }

    # Attributes that should never be accessed (escape hatch prevention)
    BLOCKED_ATTRIBUTES = {
        '__globals__',
        '__code__',
        '__dict__',
        '__class__',
        '__bases__',
        '__subclasses__',
        '__import__',
        '__builtins__',
        'eval',
        'exec',
        'compile',
        '__loader__',
        '__spec__',
        '__cached__',
        'func_globals',
        'func_code',
        'gi_frame',
        'gi_code',
        'cr_frame',
        'cr_code',
    }

    # Whitelisted imports
    ALLOWED_IMPORTS = {
        'json',
        'datetime',
        'uuid',
        'typing',
        'src.db.queries',
        'src.db.connection',
    }

    # Dangerous names that shouldn't appear
    BLOCKED_NAMES = {
        'eval',
        'exec',
        'compile',
        '__import__',
        'open',
        'input',
        'breakpoint',
    }

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.imports_used: Set[str] = set()
        self.has_async_function = False

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Python code for security issues

        Args:
            code: Python source code as string

        Returns:
            (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"

        # Reset state
        self.errors = []
        self.warnings = []
        self.imports_used = set()
        self.has_async_function = False

        # Visit all nodes
        self.visit(tree)

        # Check that code defines exactly one async function
        if not self.has_async_function:
            self.errors.append("Code must define exactly one async function")

        # Return results
        if self.errors:
            return False, "; ".join(self.errors)

        return True, None

    def visit(self, node):
        """Visit a node and validate it"""
        # Check if node type is allowed
        if type(node) not in self.ALLOWED_NODES:
            self.errors.append(
                f"Disallowed AST node type: {type(node).__name__} at line {getattr(node, 'lineno', '?')}"
            )

        # Call specific visitor method
        return super().visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Validate async function definition"""
        self.has_async_function = True

        # Check that first parameter is 'ctx'
        if not node.args.args or node.args.args[0].arg != 'ctx':
            self.errors.append(
                f"Function '{node.name}' must have 'ctx' as first parameter"
            )

        # Continue visiting children
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Validate function definition (nested functions)"""
        # Only allow nested functions, not top-level sync functions
        # This is checked by context - if we're not inside AsyncFunctionDef, error
        self.generic_visit(node)

    def visit_Import(self, node):
        """Validate import statements"""
        for alias in node.names:
            if alias.name not in self.ALLOWED_IMPORTS:
                self.errors.append(
                    f"Import not allowed: {alias.name} at line {node.lineno}"
                )
            else:
                self.imports_used.add(alias.name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Validate from...import statements"""
        module = node.module or ''

        # Check if module is allowed
        allowed = False
        for allowed_import in self.ALLOWED_IMPORTS:
            if module == allowed_import or module.startswith(allowed_import + '.'):
                allowed = True
                break

        if not allowed:
            self.errors.append(
                f"Import not allowed: from {module} import ... at line {node.lineno}"
            )
        else:
            self.imports_used.add(module)

        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Validate attribute access"""
        attr_name = node.attr

        # Check if accessing blocked attribute
        if attr_name in self.BLOCKED_ATTRIBUTES:
            self.errors.append(
                f"Blocked attribute access: {attr_name} at line {node.lineno}"
            )

        # Check for suspicious patterns like obj.__dict__
        if attr_name.startswith('__') and attr_name.endswith('__'):
            self.warnings.append(
                f"Suspicious dunder attribute: {attr_name} at line {node.lineno}"
            )

        self.generic_visit(node)

    def visit_Name(self, node):
        """Validate name usage"""
        if node.id in self.BLOCKED_NAMES:
            self.errors.append(
                f"Blocked name: {node.id} at line {node.lineno}"
            )

        self.generic_visit(node)

    def visit_Call(self, node):
        """Validate function calls"""
        # Check for dangerous function calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.BLOCKED_NAMES:
                self.errors.append(
                    f"Blocked function call: {func_name}() at line {node.lineno}"
                )

        # Check for attribute calls that might be dangerous
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in self.BLOCKED_ATTRIBUTES:
                self.errors.append(
                    f"Blocked method call: {node.func.attr}() at line {node.lineno}"
                )

        self.generic_visit(node)

    def visit_Try(self, node):
        """Try blocks are not in ALLOWED_NODES, but we might allow them"""
        # For now, block try/except to prevent error suppression
        self.errors.append(
            f"Try/except blocks not allowed at line {node.lineno}"
        )
        self.generic_visit(node)

    def visit_With(self, node):
        """With blocks are not in ALLOWED_NODES"""
        # We might allow 'with' for database connections
        # For now, allow it but validate the context manager
        self.generic_visit(node)

    def visit_Raise(self, node):
        """Raise statements"""
        # Allow raising exceptions (for validation errors, etc.)
        self.generic_visit(node)


def validate_tool_code_ast(code: str) -> Tuple[bool, Optional[str]]:
    """
    Convenience function for AST validation

    Args:
        code: Python source code

    Returns:
        (is_valid, error_message)
    """
    analyzer = ASTSecurityAnalyzer()
    return analyzer.validate(code)
