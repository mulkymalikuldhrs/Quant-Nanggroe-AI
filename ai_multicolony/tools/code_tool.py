"""Code execution tool with sandboxing support.

Provides safe Python code execution with output capture, timeout
enforcement, resource limits, and return value capture.
"""

from __future__ import annotations

import asyncio
import resource
import sys
import traceback
from io import StringIO
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError, ToolTimeoutError
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)

# Safe builtins whitelist for sandbox mode
_SAFE_BUILTINS: dict[str, Any] = {
    # Types
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "bytes": bytes, "bytearray": bytearray, "frozenset": frozenset,
    "complex": complex,
    # Functions
    "print": print, "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "sorted": sorted,
    "reversed": reversed, "sum": sum, "min": min, "max": max,
    "abs": abs, "round": round, "pow": pow, "divmod": divmod,
    "all": all, "any": any, "chr": chr, "ord": ord, "hex": hex, "oct": oct,
    "bin": bin, "format": format, "repr": repr, "hash": hash,
    "id": id, "type": type, "isinstance": isinstance, "issubclass": issubclass,
    "hasattr": hasattr, "getattr": getattr, "setattr": setattr, "delattr": delattr,
    "dir": dir, "vars": vars, "callable": callable,
    "iter": iter, "next": next, "super": super,
    "staticmethod": staticmethod, "classmethod": classmethod,
    "property": property,
    # Exceptions
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    "KeyError": KeyError, "IndexError": IndexError, "AttributeError": AttributeError,
    "RuntimeError": RuntimeError, "StopIteration": StopIteration,
    "NotImplementedError": NotImplementedError, "ZeroDivisionError": ZeroDivisionError,
    "OverflowError": OverflowError, "FileNotFoundError": FileNotFoundError,
    # Constants
    "True": True, "False": False, "None": None,
    # Special
    "help": help,
}

# Optional safe imports
_SAFE_IMPORTS: dict[str, Any] = {
    "math": __import__("math"),
    "json": __import__("json"),
    "re": __import__("re"),
    "collections": __import__("collections"),
    "itertools": __import__("itertools"),
    "functools": __import__("functools"),
    "datetime": __import__("datetime"),
    "decimal": __import__("decimal"),
    "fractions": __import__("fractions"),
    "statistics": __import__("statistics"),
    "random": __import__("random"),
    "string": __import__("string"),
    "hashlib": __import__("hashlib"),
    "base64": __import__("base64"),
    "textwrap": __import__("textwrap"),
    "pprint": __import__("pprint"),
    "copy": __import__("copy"),
    "operator": __import__("operator"),
    "pathlib": __import__("pathlib"),
    "typing": __import__("typing"),
}


def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
    """Restricted import function that only allows safe modules.

    Args:
        name: Module name to import.

    Returns:
        The imported module.

    Raises:
        ImportError: If the module is not in the safe list.
    """
    if name in _SAFE_IMPORTS:
        return _SAFE_IMPORTS[name]
    # Allow sub-modules of safe packages
    top_level = name.split(".")[0]
    if top_level in _SAFE_IMPORTS:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"Import of '{name}' is not allowed in sandbox mode")


class CodeTool(BaseTool):
    """Code execution tool with sandboxing.

    Features:
    - Execute Python code with output capture
    - Timeout enforcement
    - Restricted builtins for safety
    - Safe import whitelist
    - Variable persistence across executions (optional)
    - Return value capture (last expression)
    - Resource limits (memory, file descriptors)
    - Namespace reset option
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._default_timeout = self._config.get("timeout", 30)
        self._sandbox_mode = self._config.get("sandbox_mode", True)
        self._max_output_bytes = self._config.get("max_output_bytes", 50000)
        self._max_memory_mb = self._config.get("max_memory_mb", 256)
        self._namespace: dict[str, Any] = {}

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code",
            description="Execute Python code with output capture, timeout, and sandbox",
            tool_type=ToolType.CODE,
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute",
                    required=True,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Programming language (currently only python supported)",
                    required=False,
                    default="python",
                    enum=["python"],
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Execution timeout in seconds",
                    required=False,
                    default=self._default_timeout,
                ),
                ToolParameter(
                    name="reset_namespace",
                    type="boolean",
                    description="Reset the execution namespace before running",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="sandbox",
                    type="boolean",
                    description="Enable sandbox mode (restricted builtins/imports)",
                    required=False,
                    default=True,
                ),
            ],
            tags=["code", "execution", "python"],
            requires_permission="code.execute",
            timeout=self._default_timeout,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute code.

        Args:
            tool_call: The tool call with code arguments.

        Returns:
            ToolResult with execution output.
        """
        code = tool_call.arguments.get("code", "")
        timeout = tool_call.arguments.get("timeout", self._default_timeout)
        reset_namespace = tool_call.arguments.get("reset_namespace", False)
        use_sandbox = tool_call.arguments.get("sandbox", self._sandbox_mode)

        if not code:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="code",
                success=False, error="No code specified",
            )

        if reset_namespace:
            self._namespace = {}

        namespace = self._build_namespace(sandbox=use_sandbox)

        # Capture output
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        return_value: Any = None

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Set resource limits
            self._set_resource_limits()

            # Execute with timeout
            return_value = await asyncio.wait_for(
                self._run_code(code, namespace),
                timeout=timeout,
            )

        except asyncio.TimeoutError:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            raise ToolTimeoutError(
                f"Code execution timed out after {timeout}s",
                tool_name="code",
                timeout=float(timeout),
            )

        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            tb = traceback.format_exc()
            stdout_val = stdout_capture.getvalue()
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="code",
                success=False,
                output=stdout_val[:self._max_output_bytes],
                error=f"{type(e).__name__}: {e}\n{tb}"[:5000],
            )

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # Persist namespace state
            self._namespace.update(namespace)

        # Build output
        output = stdout_capture.getvalue()
        stderr_val = stderr_capture.getvalue()

        if return_value is not None:
            output += f"\n>>> Return value: {repr(return_value)}"

        if stderr_val:
            output += f"\n[stderr]\n{stderr_val}"

        # Truncate
        output = output[:self._max_output_bytes]

        metadata: dict[str, Any] = {}
        if return_value is not None:
            metadata["return_type"] = type(return_value).__name__
            metadata["return_value_repr"] = repr(return_value)[:500]

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="code",
            success=True, output=output,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _run_code(self, code: str, namespace: dict[str, Any]) -> Any:
        """Run code in the given namespace.

        Attempts to compile as an expression first to capture the return
        value.  Falls back to exec for statement blocks.

        Args:
            code: The code to execute.
            namespace: The execution namespace.

        Returns:
            The result of the last expression, if any.
        """
        # Try expression first
        try:
            compiled_expr = compile(code, "<code_tool>", "eval")
            result = eval(compiled_expr, namespace)
            return result
        except SyntaxError:
            pass

        # Split code: try to capture the last expression as return value
        lines = code.rstrip().split("\n")
        return_val: Any = None

        # Check if the last line could be an expression
        if lines:
            last_line = lines[-1].strip()
            # Don't treat statements as return values
            if last_line and not last_line.startswith((
                "import ", "from ", "def ", "class ", "if ", "for ",
                "while ", "try:", "with ", "@", "return ", "raise ",
                "break", "continue", "pass", "#", '"""', "'''",
            )):
                # Try compiling without the last line as statements,
                # and the last line as an expression
                try:
                    main_code = "\n".join(lines[:-1])
                    last_expr = lines[-1]
                    if main_code.strip():
                        compiled_main = compile(main_code, "<code_tool>", "exec")
                        exec(compiled_main, namespace)
                    compiled_last = compile(last_expr, "<code_tool>", "eval")
                    return_val = eval(compiled_last, namespace)
                except (SyntaxError, Exception):
                    # Fall back to full exec
                    compiled = compile(code, "<code_tool>", "exec")
                    exec(compiled, namespace)
            else:
                compiled = compile(code, "<code_tool>", "exec")
                exec(compiled, namespace)
        else:
            compiled = compile(code, "<code_tool>", "exec")
            exec(compiled, namespace)

        return return_val

    def _build_namespace(self, sandbox: bool = True) -> dict[str, Any]:
        """Build the execution namespace.

        Args:
            sandbox: Whether to apply sandbox restrictions.

        Returns:
            The namespace dict for code execution.
        """
        if sandbox:
            namespace: dict[str, Any] = {"__builtins__": dict(_SAFE_BUILTINS)}
            # Add safe import function
            namespace["__builtins__"]["__import__"] = _safe_import
            namespace["__builtins__"]["__name__"] = "__code_tool__"
        else:
            namespace = {"__builtins__": __builtins__}

        # Carry over persisted variables
        namespace.update(self._namespace)

        return namespace

    def _set_resource_limits(self) -> None:
        """Set resource limits for the execution context.

        Limits memory usage and number of open file descriptors.
        """
        try:
            # Limit memory (only works on Unix)
            max_bytes = self._max_memory_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (max_bytes, max_bytes),
            )
            # Limit file descriptors
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (64, 64),
            )
        except (ValueError, AttributeError, OSError):
            # resource module may not be available on all platforms
            pass

    def reset(self) -> None:
        """Reset the execution namespace."""
        self._namespace = {}

    def get_namespace_vars(self) -> dict[str, str]:
        """Get a summary of variables in the namespace.

        Returns:
            Dict mapping variable names to their type names.
        """
        return {
            k: type(v).__name__
            for k, v in self._namespace.items()
            if not k.startswith("__")
        }
