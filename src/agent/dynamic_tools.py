"""
Dynamic tool creation, validation, loading, and registration system
Enables self-extending AI agent capabilities
"""
import ast
import re
import logging
import time
from typing import Optional, Callable, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ==========================================
# Code Validation & Security
# ==========================================

class CodeValidationError(Exception):
    """Raised when generated code fails validation"""
    pass


ALLOWED_IMPORTS = {
    'json', 'datetime', 'uuid', 'typing',
    'src.db.queries', 'src.db.connection'
}

DANGEROUS_PATTERNS = [
    r'\bexec\b', r'\beval\b', r'\b__import__\b',
    r'\bopen\b', r'\bfile\b', r'\bos\.',
    r'\bsys\.', r'\bsubprocess\b', r'\bshutil\b',
    r'\brm\b', r'\bdelete\b.*file', r'\bunlink\b'
]


def validate_tool_code(function_code: str, tool_type: str) -> tuple[bool, Optional[str]]:
    """
    Validate generated tool code for security and correctness

    Args:
        function_code: Python function code as string
        tool_type: 'read' or 'write'

    Returns:
        (is_valid, error_message)
    """
    try:
        # 1. Parse AST to ensure syntactically valid Python
        tree = ast.parse(function_code)

        # 2. Check that it's a function definition
        if not tree.body or not isinstance(tree.body[0], ast.AsyncFunctionDef):
            return False, "Code must be a single async function definition"

        func_def = tree.body[0]

        # 3. Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, function_code):
                return False, f"Dangerous pattern detected: {pattern}"

        # 4. Validate imports (walk AST for import nodes)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in ALLOWED_IMPORTS:
                        return False, f"Import not allowed: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module not in ALLOWED_IMPORTS:
                    return False, f"Import not allowed: {node.module}"

        # 5. For read-only tools, verify no database writes
        if tool_type == 'read':
            code_lower = function_code.lower()
            write_keywords = ['insert', 'update', 'delete', 'drop', 'alter', 'create table']
            for keyword in write_keywords:
                if keyword in code_lower:
                    return False, f"Read-only tool cannot contain '{keyword}' operations"

        # 6. Verify function signature includes 'ctx' parameter
        if not func_def.args.args or func_def.args.args[0].arg != 'ctx':
            return False, "Function must have 'ctx' as first parameter"

        return True, None

    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def classify_tool_type(function_code: str, description: str) -> str:
    """
    Determine if tool is read-only or write operation

    Args:
        function_code: Python function code
        description: Tool description

    Returns:
        'read' or 'write'
    """
    code_lower = function_code.lower()
    desc_lower = description.lower()

    # Write indicators
    write_keywords = [
        'insert', 'update', 'delete', 'create', 'drop',
        'remove', 'save', 'edit', 'modify', 'set'
    ]

    # Check code
    for keyword in write_keywords:
        if keyword in code_lower:
            return 'write'

    # Check description
    for keyword in write_keywords:
        if keyword in desc_lower:
            return 'write'

    # Default to read-only
    return 'read'


# ==========================================
# Dynamic Tool Loading & Registration
# ==========================================

class DynamicToolManager:
    """Manages dynamic tool lifecycle"""

    def __init__(self):
        self.loaded_tools: dict[str, Callable] = {}
        self.tool_metadata: dict[str, dict] = {}

    async def load_all_tools(self) -> list[str]:
        """
        Load all enabled tools from database

        Returns:
            List of loaded tool names
        """
        from src.db.queries import get_all_enabled_tools

        tools = await get_all_enabled_tools()
        loaded_names = []

        for tool in tools:
            try:
                func = self._create_function_from_code(
                    tool["function_code"],
                    tool["tool_name"]
                )

                self.loaded_tools[tool["tool_name"]] = func
                self.tool_metadata[tool["tool_name"]] = tool
                loaded_names.append(tool["tool_name"])

                logger.info(f"Loaded dynamic tool: {tool['tool_name']}")

            except Exception as e:
                logger.error(f"Failed to load tool {tool['tool_name']}: {e}")

        return loaded_names

    def _create_function_from_code(
        self,
        function_code: str,
        tool_name: str
    ) -> Callable:
        """
        Compile and create function object from code string

        Args:
            function_code: Python function code
            tool_name: Tool name for error messages

        Returns:
            Compiled function object
        """
        # Import result models from agent module
        from src.agent import (
            ProfileUpdateResult,
            PreferenceSaveResult,
            TrackingCategoryResult,
            TrackingEntryResult,
            ReminderScheduleResult,
            FoodSummaryResult,
            DynamicToolCreationResult,
        )

        # Create namespace for execution
        namespace = {
            'BaseModel': BaseModel,
            'Optional': Optional,
            'Any': Any,
            'logger': logger,
            # Result models
            'ProfileUpdateResult': ProfileUpdateResult,
            'PreferenceSaveResult': PreferenceSaveResult,
            'TrackingCategoryResult': TrackingCategoryResult,
            'TrackingEntryResult': TrackingEntryResult,
            'ReminderScheduleResult': ReminderScheduleResult,
            'FoodSummaryResult': FoodSummaryResult,
            'DynamicToolCreationResult': DynamicToolCreationResult,
        }

        # Import commonly needed modules
        import json
        import datetime
        from uuid import uuid4

        namespace['json'] = json
        namespace['datetime'] = datetime
        namespace['uuid4'] = uuid4

        # Import db connection if needed
        if 'db.connection()' in function_code:
            from src.db.connection import db
            namespace['db'] = db

        # Import all query functions that might be referenced
        from src.db import queries
        for attr_name in dir(queries):
            if not attr_name.startswith('_'):
                namespace[attr_name] = getattr(queries, attr_name)

        # Import AgentDeps for type hints
        from src.agent import AgentDeps
        namespace['AgentDeps'] = AgentDeps

        # Execute code to define function
        try:
            exec(compile(function_code, f"<dynamic_tool_{tool_name}>", "exec"), namespace)
        except Exception as e:
            logger.error(f"Failed to compile tool {tool_name}: {e}")
            raise

        # Extract the function (should be the only async function defined)
        func = None
        for name, obj in namespace.items():
            if callable(obj) and hasattr(obj, '__name__') and not name.startswith('_'):
                # Check if it's the function we just defined
                if hasattr(obj, '__code__'):
                    func = obj
                    break

        if not func:
            raise ValueError(f"No function found in code for {tool_name}")

        return func

    def register_tools_on_agent(self, agent) -> int:
        """
        Register all loaded tools on a PydanticAI agent

        Args:
            agent: PydanticAI Agent instance

        Returns:
            Number of tools registered
        """
        count = 0
        for tool_name, func in self.loaded_tools.items():
            agent.tool(func)
            count += 1
            logger.info(f"Registered dynamic tool on agent: {tool_name}")

        return count

    async def execute_tool_with_logging(
        self,
        tool_name: str,
        user_id: str,
        **kwargs
    ) -> Any:
        """
        Execute a tool with audit logging

        Args:
            tool_name: Name of tool to execute
            user_id: User ID for logging
            **kwargs: Tool parameters

        Returns:
            Tool result
        """
        from src.db.queries import log_tool_execution

        if tool_name not in self.loaded_tools:
            raise ValueError(f"Tool not found: {tool_name}")

        metadata = self.tool_metadata[tool_name]
        tool_id = metadata["id"]

        start_time = time.time()
        success = False
        result = None
        error_message = None

        try:
            # Execute tool
            result = await self.loaded_tools[tool_name](**kwargs)
            success = True
            return result

        except Exception as e:
            error_message = str(e)
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            raise

        finally:
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Log execution
            await log_tool_execution(
                tool_id=tool_id,
                user_id=user_id,
                parameters=kwargs,
                result=result,
                success=success,
                error_message=error_message,
                execution_time_ms=execution_time_ms
            )


# Global tool manager instance
tool_manager = DynamicToolManager()
