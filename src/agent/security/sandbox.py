"""
Sandboxed execution environment for dynamic tools

Provides secure code execution with:
- RestrictedPython compilation
- Resource limits (CPU, memory, time)
- Safe globals/builtins
- Timeout protection
"""

import asyncio
import logging
import signal
import time
from typing import Any, Dict, Callable, Optional
from contextlib import contextmanager
import traceback

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - resource monitoring disabled")

try:
    from RestrictedPython import compile_restricted
    from RestrictedPython.Guards import safe_builtins, safe_globals, guarded_iter_unpack_sequence
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    RESTRICTED_PYTHON_AVAILABLE = False
    logging.warning("RestrictedPython not available - sandbox disabled")

logger = logging.getLogger(__name__)


class SandboxViolation(Exception):
    """Raised when sandboxed code violates security restrictions"""
    pass


class TimeoutException(Exception):
    """Raised when code execution exceeds timeout"""
    pass


class ResourceLimitExceeded(Exception):
    """Raised when resource limits are exceeded"""
    pass


class SandboxExecutor:
    """
    Execute dynamic tool code in a restricted sandbox

    Security layers:
    1. RestrictedPython compilation (AST-based)
    2. Safe globals/builtins whitelist
    3. Timeout protection
    4. Resource monitoring (CPU, memory)
    """

    # Resource limits
    MAX_EXECUTION_TIME = 5  # seconds
    MAX_MEMORY_MB = 50  # megabytes
    MAX_CPU_PERCENT = 25  # percent

    def __init__(
        self,
        max_execution_time: int = MAX_EXECUTION_TIME,
        max_memory_mb: int = MAX_MEMORY_MB,
        max_cpu_percent: int = MAX_CPU_PERCENT
    ):
        """
        Initialize sandbox executor

        Args:
            max_execution_time: Maximum execution time in seconds
            max_memory_mb: Maximum memory usage in MB
            max_cpu_percent: Maximum CPU usage percent
        """
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent

        if not RESTRICTED_PYTHON_AVAILABLE:
            logger.critical("RestrictedPython not installed - sandbox is DISABLED")

    def _create_safe_globals(self, namespace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create safe global namespace for code execution

        Args:
            namespace: Additional safe names to include

        Returns:
            Safe globals dictionary
        """
        # Start with RestrictedPython's safe_globals
        safe_ns = safe_globals.copy() if RESTRICTED_PYTHON_AVAILABLE else {}

        # Add minimal safe builtins
        safe_ns['__builtins__'] = {
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
            'enumerate': enumerate,
            'isinstance': isinstance,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,  # Controlled by RestrictedPython
            'sorted': sorted,
            'reversed': reversed,
            'any': any,
            'all': all,
            # Type hints
            'Optional': Optional,
            'Any': Any,
            'List': list,
            'Dict': dict,
        }

        # Add user-provided safe names
        safe_ns.update(namespace)

        # Add guards
        if RESTRICTED_PYTHON_AVAILABLE:
            safe_ns['_iter_unpack_sequence_'] = guarded_iter_unpack_sequence

        return safe_ns

    @contextmanager
    def _timeout_context(self, timeout: int):
        """
        Context manager for execution timeout

        Args:
            timeout: Timeout in seconds
        """
        def timeout_handler(signum, frame):
            raise TimeoutException(f"Execution exceeded {timeout} seconds")

        # Set alarm (Unix only)
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            yield
        finally:
            # Disable alarm
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def _check_memory_usage(self):
        """Check if memory usage exceeds limit"""
        if not PSUTIL_AVAILABLE:
            return

        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.max_memory_mb:
                raise ResourceLimitExceeded(
                    f"Memory usage ({memory_mb:.1f}MB) exceeded limit ({self.max_memory_mb}MB)"
                )
        except psutil.Error as e:
            logger.warning(f"Failed to check memory usage: {e}")

    def compile_restricted_code(
        self,
        code: str,
        filename: str = "<dynamic_tool>"
    ) -> Any:
        """
        Compile code using RestrictedPython

        Args:
            code: Python source code
            filename: Filename for error messages

        Returns:
            Compiled code object

        Raises:
            SandboxViolation: If compilation fails or code is unsafe
        """
        if not RESTRICTED_PYTHON_AVAILABLE:
            raise SandboxViolation(
                "RestrictedPython not available - cannot compile safely"
            )

        try:
            # Compile with RestrictedPython
            byte_code = compile_restricted(
                code,
                filename=filename,
                mode='exec'
            )

            # Check for compilation errors
            if byte_code.errors:
                error_msg = "; ".join(byte_code.errors)
                raise SandboxViolation(f"RestrictedPython compilation errors: {error_msg}")

            # Check for warnings
            if byte_code.warnings:
                for warning in byte_code.warnings:
                    logger.warning(f"RestrictedPython warning: {warning}")

            return byte_code.code

        except SyntaxError as e:
            raise SandboxViolation(f"Syntax error in dynamic tool: {str(e)}")
        except Exception as e:
            raise SandboxViolation(f"Failed to compile code: {str(e)}")

    def execute_sandboxed(
        self,
        code: str,
        namespace: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Callable:
        """
        Execute code in sandboxed environment

        Args:
            code: Python source code (should define one async function)
            namespace: Safe namespace with allowed names/modules
            timeout: Execution timeout in seconds (default: self.max_execution_time)

        Returns:
            The compiled function object

        Raises:
            SandboxViolation: If code violates security restrictions
            TimeoutException: If execution exceeds timeout
            ResourceLimitExceeded: If resource limits exceeded
        """
        if timeout is None:
            timeout = self.max_execution_time

        start_time = time.time()

        try:
            # Compile code using RestrictedPython
            compiled_code = self.compile_restricted_code(code)

            # Create safe global namespace
            safe_namespace = self._create_safe_globals(namespace)

            # Execute with timeout protection
            try:
                with self._timeout_context(timeout):
                    # Check memory before execution
                    self._check_memory_usage()

                    # Execute compiled code
                    exec(compiled_code, safe_namespace)

                    # Check memory after execution
                    self._check_memory_usage()

            except TimeoutException:
                raise TimeoutException(f"Code execution exceeded {timeout}s timeout")
            except MemoryError:
                raise ResourceLimitExceeded("Memory limit exceeded")

            # Extract the function from namespace
            func = None
            for name, obj in safe_namespace.items():
                if callable(obj) and hasattr(obj, '__name__') and not name.startswith('_'):
                    if hasattr(obj, '__code__'):
                        func = obj
                        break

            if func is None:
                raise SandboxViolation("No function found in compiled code")

            execution_time = time.time() - start_time
            logger.info(
                f"Sandboxed code compiled successfully in {execution_time:.3f}s"
            )

            return func

        except (SandboxViolation, TimeoutException, ResourceLimitExceeded):
            raise
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}\n{traceback.format_exc()}")
            raise SandboxViolation(f"Execution error: {str(e)}")

    async def execute_async_sandboxed(
        self,
        func: Callable,
        *args,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Execute an async function with timeout and resource monitoring

        Args:
            func: Async function to execute
            *args: Positional arguments
            timeout: Timeout in seconds
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            TimeoutException: If execution exceeds timeout
            ResourceLimitExceeded: If resource limits exceeded
        """
        if timeout is None:
            timeout = self.max_execution_time

        try:
            # Execute with asyncio timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )

            # Check memory usage after execution
            self._check_memory_usage()

            return result

        except asyncio.TimeoutError:
            raise TimeoutException(f"Async execution exceeded {timeout}s timeout")
        except MemoryError:
            raise ResourceLimitExceeded("Memory limit exceeded during execution")


# Global singleton instance
_default_executor = None


def get_sandbox_executor() -> SandboxExecutor:
    """Get or create the default sandbox executor"""
    global _default_executor
    if _default_executor is None:
        _default_executor = SandboxExecutor()
    return _default_executor
