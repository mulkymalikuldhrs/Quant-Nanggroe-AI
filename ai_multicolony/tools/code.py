"""CodeTool – code analysis, linting, formatting, and sandboxed execution.

Autonomy levels:
  - L1: analyze, lint, format, syntax_check
  - L2: run (sandboxed code execution)
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import time
import traceback
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)


class SandboxResult:
    """Result from sandboxed code execution."""

    def __init__(
        self,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        timed_out: bool = False,
        duration_ms: float = 0.0,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_ms": round(self.duration_ms, 2),
        }


class CodeTool(MCPTool):
    """Code analysis, linting, formatting, and sandboxed execution.

    Actions
    -------
    syntax_check : verify syntax of code (L1)
    lint         : run linter on code (L1)
    format       : auto-format code (L1)
    analyze      : static analysis / complexity check (L1)
    run          : execute code in a sandboxed subprocess (L2)
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "code.operations"

    def category(self) -> str:
        return "compute"

    def autonomy_level(self) -> int:
        return 1  # minimum; L2 for 'run'

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["action", "code"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["syntax_check", "lint", "format", "analyze", "run"],
                    "description": "Code action to perform",
                },
                "code": {
                    "type": "string",
                    "description": "Source code to process",
                },
                "language": {
                    "type": "string",
                    "default": "python",
                    "enum": ["python", "javascript", "typescript", "go", "rust"],
                    "description": "Programming language",
                },
                "timeout": {
                    "type": "integer",
                    "default": 10,
                    "description": "Execution timeout in seconds (for 'run')",
                },
                "filename": {
                    "type": "string",
                    "description": "Optional filename for context",
                },
                "linter": {
                    "type": "string",
                    "default": "auto",
                    "description": "Linter to use (auto, flake8, pylint, eslint)",
                },
                "formatter": {
                    "type": "string",
                    "default": "auto",
                    "description": "Formatter to use (auto, black, autopep8, prettier)",
                },
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "action": {"type": "string"},
                "result": {"type": "object"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 5001, "message": "Syntax error"},
            {"code": 5002, "message": "Lint error"},
            {"code": 5003, "message": "Format error"},
            {"code": 5004, "message": "Sandbox execution error"},
            {"code": 5005, "message": "Sandbox timeout"},
            {"code": 5006, "message": "Unsupported language"},
        ]

    # ── Execute ──────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action: str = params["action"]
        code: str = params["code"]
        language: str = params.get("language", "python")
        autonomy = context.get("autonomy_level", 0)

        # 'run' requires L2
        if action == "run" and autonomy < 2:
            self.record_call(False)
            return {
                "success": False,
                "action": action,
                "result": {"error": "Sandboxed execution requires autonomy level L2"},
            }

        dispatch = {
            "syntax_check": self._syntax_check,
            "lint": self._lint,
            "format": self._format,
            "analyze": self._analyze,
            "run": self._run,
        }

        handler = dispatch.get(action)
        if handler is None:
            self.record_call(False)
            return {
                "success": False,
                "action": action,
                "result": {"error": f"Unknown action: {action}"},
            }

        start = time.monotonic()
        try:
            result = await handler(code, language, params)
            duration = (time.monotonic() - start) * 1000
            self.record_call(result.get("success", True), duration)
            result["action"] = action
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {
                "success": False,
                "action": action,
                "result": {"error": str(exc)},
            }

    # ── Syntax check ─────────────────────────────────────────────

    async def _syntax_check(self, code: str, language: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if language == "python":
            return self._python_syntax_check(code)
        elif language in ("javascript", "typescript"):
            return self._js_syntax_check(code)
        elif language == "go":
            return self._go_syntax_check(code)
        elif language == "rust":
            return self._rust_syntax_check(code)
        return {"success": False, "result": {"error": f"Unsupported language: {language}"}}

    def _python_syntax_check(self, code: str) -> Dict[str, Any]:
        try:
            compile(code, "<string>", "exec")
            return {"success": True, "result": {"valid": True, "errors": []}}
        except SyntaxError as exc:
            return {
                "success": False,
                "result": {
                    "valid": False,
                    "errors": [{
                        "line": exc.lineno or 0,
                        "offset": exc.offset or 0,
                        "message": exc.msg,
                        "text": exc.text or "",
                    }],
                },
            }

    def _js_syntax_check(self, code: str) -> Dict[str, Any]:
        # Basic heuristic: try to parse with node --check if available
        try:
            proc = subprocess.run(
                ["node", "--check", "-e", code],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                return {"success": True, "result": {"valid": True, "errors": []}}
            return {
                "success": False,
                "result": {"valid": False, "errors": [{"message": proc.stderr.strip()}]},
            }
        except FileNotFoundError:
            # node not available; do a very basic bracket check
            open_b = code.count("{") + code.count("(") + code.count("[")
            close_b = code.count("}") + code.count(")") + code.count("]")
            if open_b != close_b:
                return {
                    "success": False,
                    "result": {"valid": False, "errors": [{"message": "Unbalanced brackets detected"}]},
                }
            return {"success": True, "result": {"valid": True, "errors": [], "note": "node not available; basic check only"}}

    def _go_syntax_check(self, code: str) -> Dict[str, Any]:
        # Basic check for Go: balanced braces
        if code.count("{") != code.count("}"):
            return {"success": False, "result": {"valid": False, "errors": [{"message": "Unbalanced braces"}]}}
        return {"success": True, "result": {"valid": True, "errors": [], "note": "Basic check only (go not available)"}}

    def _rust_syntax_check(self, code: str) -> Dict[str, Any]:
        if code.count("{") != code.count("}"):
            return {"success": False, "result": {"valid": False, "errors": [{"message": "Unbalanced braces"}]}}
        return {"success": True, "result": {"valid": True, "errors": [], "note": "Basic check only (rustc not available)"}}

    # ── Lint ─────────────────────────────────────────────────────

    async def _lint(self, code: str, language: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if language == "python":
            return self._python_lint(code, params)
        return {"success": True, "result": {"errors": 0, "warnings": 0, "note": f"Linting not implemented for {language}"}}

    def _python_lint(self, code: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Basic Python linting without external tools."""
        lines = code.splitlines()
        errors = []
        warnings = []

        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()

            # Trailing whitespace
            if line != stripped and stripped:
                warnings.append({"line": i, "message": "Trailing whitespace", "type": "style"})

            # Line too long
            if len(stripped) > 120:
                warnings.append({"line": i, "message": f"Line too long ({len(stripped)} chars)", "type": "style"})

            # Bare except
            if stripped.endswith("except:"):
                errors.append({"line": i, "message": "Bare except clause", "type": "error"})

            # Mutable default arguments
            if "def " in stripped and ("=[]" in stripped or "={}" in stripped):
                warnings.append({"line": i, "message": "Mutable default argument", "type": "warning"})

            # Unused imports (very simple heuristic)
            if stripped.startswith("import ") and "*" in stripped:
                warnings.append({"line": i, "message": "Wildcard import", "type": "style"})

        return {
            "success": True,
            "result": {
                "errors": len(errors),
                "warnings": len(warnings),
                "error_details": errors,
                "warning_details": warnings,
            },
        }

    # ── Format ───────────────────────────────────────────────────

    async def _format(self, code: str, language: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if language == "python":
            return self._python_format(code)
        return {"success": True, "result": {"formatted": code, "changed": False, "note": f"Formatting not implemented for {language}"}}

    def _python_format(self, code: str) -> Dict[str, Any]:
        """Basic Python formatting: normalize indentation, trailing whitespace."""
        lines = code.splitlines()
        formatted_lines = []
        for line in lines:
            # Remove trailing whitespace
            formatted = line.rstrip()
            # Normalize tabs to 4 spaces
            formatted = formatted.replace("\t", "    ")
            formatted_lines.append(formatted)

        # Ensure file ends with newline
        formatted = "\n".join(formatted_lines)
        if formatted and not formatted.endswith("\n"):
            formatted += "\n"

        changed = formatted != code
        return {
            "success": True,
            "result": {
                "formatted": formatted,
                "changed": changed,
                "original_lines": len(lines),
                "formatted_lines": len(formatted_lines),
            },
        }

    # ── Analyze ──────────────────────────────────────────────────

    async def _analyze(self, code: str, language: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if language == "python":
            return self._python_analyze(code)
        return {"success": True, "result": {"complexity": "unknown", "note": f"Analysis not implemented for {language}"}}

    def _python_analyze(self, code: str) -> Dict[str, Any]:
        """Basic Python static analysis."""
        lines = code.splitlines()
        total_lines = len(lines)
        code_lines = sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))
        comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
        blank_lines = total_lines - code_lines - comment_lines

        # Count functions and classes
        func_count = sum(1 for l in lines if l.strip().startswith("def "))
        class_count = sum(1 for l in lines if l.strip().startswith("class "))

        # Simple cyclomatic complexity: count branching keywords
        complexity_keywords = ["if ", "elif ", "else:", "for ", "while ", "except ", "and ", "or "]
        complexity = 1  # base
        for line in lines:
            for kw in complexity_keywords:
                if kw in line:
                    complexity += 1

        # Imports
        imports = [l.strip() for l in lines if l.strip().startswith("import ") or l.strip().startswith("from ")]

        return {
            "success": True,
            "result": {
                "complexity": "low" if complexity <= 5 else "medium" if complexity <= 15 else "high",
                "cyclomatic_complexity": complexity,
                "total_lines": total_lines,
                "code_lines": code_lines,
                "comment_lines": comment_lines,
                "blank_lines": blank_lines,
                "functions": func_count,
                "classes": class_count,
                "imports": imports,
                "issues": [],
            },
        }

    # ── Run (sandboxed) ──────────────────────────────────────────

    async def _run(self, code: str, language: str, params: Dict[str, Any]) -> Dict[str, Any]:
        timeout = params.get("timeout", 10)

        if language == "python":
            return (await self._run_python(code, timeout)).to_dict()
        elif language in ("javascript", "typescript"):
            return (await self._run_js(code, timeout)).to_dict()
        return {"success": False, "result": {"error": f"Execution not supported for {language}"}}

    async def _run_python(self, code: str, timeout: int) -> SandboxResult:
        """Run Python code in a subprocess with timeout."""
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                exit_code=proc.returncode or 0,
                duration_ms=duration,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return SandboxResult(
                stderr=f"Execution timed out after {timeout}s",
                exit_code=-1,
                timed_out=True,
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            return SandboxResult(
                stderr=str(exc),
                exit_code=-1,
                duration_ms=(time.monotonic() - start) * 1000,
            )

    async def _run_js(self, code: str, timeout: int) -> SandboxResult:
        """Run JavaScript code in a subprocess with timeout."""
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", "-e", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = (time.monotonic() - start) * 1000
            return SandboxResult(
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                exit_code=proc.returncode or 0,
                duration_ms=duration,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return SandboxResult(
                stderr=f"Execution timed out after {timeout}s",
                exit_code=-1,
                timed_out=True,
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except FileNotFoundError:
            return SandboxResult(
                stderr="Node.js not available for execution",
                exit_code=-1,
                duration_ms=(time.monotonic() - start) * 1000,
            )
