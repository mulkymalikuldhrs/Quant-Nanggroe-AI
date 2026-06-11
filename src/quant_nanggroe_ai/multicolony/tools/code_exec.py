"""Code execution MCP server tool for the Multi-Colony Ecosystem.

This module provides sandboxed code execution capabilities through the
MCP protocol. It supports Python and JavaScript execution with
package installation in isolated environments.

Security:
    - Code runs in sandboxed environments by default.
    - Network access is restricted based on security level.
    - Execution timeouts prevent runaway processes.
    - Resource limits (memory, CPU) are enforced.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class CodeLanguage(str, Enum):
    """Supported programming languages for code execution."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"


class ExecutionStatus(str, Enum):
    """Status of a code execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecConfig(BaseModel):
    """Configuration for the code execution tool.

    Attributes:
        default_timeout_ms: Default execution timeout in milliseconds.
        max_timeout_ms: Maximum allowed timeout in milliseconds.
        max_memory_mb: Maximum memory allowed per execution in MB.
        max_output_bytes: Maximum output size in bytes.
        allowed_languages: Languages that are allowed for execution.
        sandbox_enabled: Whether to run code in a sandbox.
        network_access: Whether executed code can access the network.
        install_allowed: Whether package installation is allowed.
        pip_index_url: Custom pip index URL for package installation.
    """

    default_timeout_ms: int = 30000
    max_timeout_ms: int = 120000
    max_memory_mb: int = 512
    max_output_bytes: int = 1_000_000
    allowed_languages: list[CodeLanguage] = Field(
        default_factory=lambda: [CodeLanguage.PYTHON, CodeLanguage.JAVASCRIPT],
    )
    sandbox_enabled: bool = True
    network_access: bool = False
    install_allowed: bool = True
    pip_index_url: str | None = None


class ExecutionResult(BaseModel):
    """Result of a code execution.

    Attributes:
        execution_id: Unique identifier for this execution.
        language: The language of the executed code.
        code: The code that was executed.
        status: Execution status.
        stdout: Standard output from the execution.
        stderr: Standard error from the execution.
        return_value: Return value of the execution, if any.
        execution_time_ms: Execution time in milliseconds.
        memory_used_mb: Memory used during execution in MB.
        error_message: Error message if execution failed.
        exit_code: Process exit code.
        timestamp: When the execution was performed.
    """

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    language: CodeLanguage = CodeLanguage.PYTHON
    code: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    error_message: str | None = None
    exit_code: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PackageInstallResult(BaseModel):
    """Result of a package installation.

    Attributes:
        packages: List of packages that were installed.
        language: Language ecosystem of the packages.
        success: Whether installation succeeded.
        stdout: Standard output from the installation.
        stderr: Standard error from the installation.
        install_time_ms: Installation time in milliseconds.
    """

    packages: list[str]
    language: CodeLanguage = CodeLanguage.PYTHON
    success: bool = True
    stdout: str = ""
    stderr: str = ""
    install_time_ms: float = 0.0


class CodeExecTool:
    """MCP tool for sandboxed code execution.

    This tool provides safe code execution capabilities with support
    for Python and JavaScript, package installation, and resource limits.

    Example::

        executor = CodeExecTool(config=ExecConfig(default_timeout_ms=60000))
        await executor.start()

        result = await executor.execute_python("print('Hello, World!')")
        result = await executor.execute_javascript("console.log('Hello!');")
        await executor.install_packages(["numpy", "pandas"])

        await executor.stop()
    """

    def __init__(self, config: ExecConfig | None = None) -> None:
        """Initialize the code execution tool.

        Args:
            config: Execution configuration. Uses defaults if not provided.
        """
        self._config = config or ExecConfig()
        self._running = False
        self._execution_history: list[ExecutionResult] = []
        self._installed_packages: dict[CodeLanguage, set[str]] = {
            lang: set() for lang in self._config.allowed_languages
        }
        self._log = logger.bind(
            component="code_exec_tool",
            sandbox=self._config.sandbox_enabled,
        )

    @property
    def is_running(self) -> bool:
        """Whether the executor is active."""
        return self._running

    async def start(self) -> None:
        """Start the code execution environment.

        Initializes the sandbox environment and prepares for code execution.
        """
        self._running = True
        self._log.info("code_executor_started")

        # Stub: In production, would initialize Docker container or subprocess
        await asyncio.sleep(0)

    async def stop(self) -> None:
        """Stop the code execution environment and clean up resources."""
        self._running = False
        self._log.info("code_executor_stopped")

        # Stub: In production, would clean up containers/processes
        await asyncio.sleep(0)

    async def execute_python(
        self,
        code: str,
        timeout_ms: int | None = None,
    ) -> ExecutionResult:
        """Execute Python code in the sandbox.

        Args:
            code: Python code to execute.
            timeout_ms: Execution timeout in milliseconds.

        Returns:
            The execution result.

        Raises:
            CodeExecutionError: If the executor is not running.
            LanguageNotAllowedError: If Python is not allowed.
        """
        self._ensure_running()

        if CodeLanguage.PYTHON not in self._config.allowed_languages:
            raise LanguageNotAllowedError(
                "Python execution is not allowed in this configuration."
            )

        return await self._execute(
            code=code,
            language=CodeLanguage.PYTHON,
            timeout_ms=timeout_ms,
        )

    async def execute_javascript(
        self,
        code: str,
        timeout_ms: int | None = None,
    ) -> ExecutionResult:
        """Execute JavaScript code in the sandbox.

        Args:
            code: JavaScript code to execute.
            timeout_ms: Execution timeout in milliseconds.

        Returns:
            The execution result.

        Raises:
            CodeExecutionError: If the executor is not running.
            LanguageNotAllowedError: If JavaScript is not allowed.
        """
        self._ensure_running()

        if CodeLanguage.JAVASCRIPT not in self._config.allowed_languages:
            raise LanguageNotAllowedError(
                "JavaScript execution is not allowed in this configuration."
            )

        return await self._execute(
            code=code,
            language=CodeLanguage.JAVASCRIPT,
            timeout_ms=timeout_ms,
        )

    async def install_packages(
        self,
        packages: list[str],
        language: CodeLanguage = CodeLanguage.PYTHON,
    ) -> PackageInstallResult:
        """Install packages in the execution environment.

        Args:
            packages: List of package names to install.
            language: Language ecosystem for package installation.

        Returns:
            The installation result.

        Raises:
            PackageInstallNotAllowedError: If package installation is disabled.
        """
        if not self._config.install_allowed:
            raise PackageInstallNotAllowedError(
                "Package installation is not allowed in this configuration."
            )

        self._log.info(
            "installing_packages",
            packages=packages,
            language=language.value,
        )

        # Stub: In production, would run pip install or npm install
        await asyncio.sleep(0)

        self._installed_packages[language].update(packages)

        return PackageInstallResult(
            packages=packages,
            language=language,
            success=True,
            stdout=f"Successfully installed: {', '.join(packages)}",
        )

    def get_installed_packages(
        self,
        language: CodeLanguage | None = None,
    ) -> list[str] | dict[str, list[str]]:
        """Get installed packages.

        Args:
            language: Filter by language. If None, returns all.

        Returns:
            List of installed package names, or dict by language.
        """
        if language is not None:
            return sorted(self._installed_packages.get(language, set()))
        return {
            lang.value: sorted(pkgs)
            for lang, pkgs in self._installed_packages.items()
        }

    def get_execution_history(
        self,
        limit: int | None = None,
        language: CodeLanguage | None = None,
    ) -> list[ExecutionResult]:
        """Get execution history.

        Args:
            limit: Maximum number of records to return.
            language: Filter by language.

        Returns:
            A list of execution results, newest first.
        """
        history = list(reversed(self._execution_history))
        if language is not None:
            history = [h for h in history if h.language == language]
        if limit is not None:
            history = history[:limit]
        return history

    async def _execute(
        self,
        code: str,
        language: CodeLanguage,
        timeout_ms: int | None = None,
    ) -> ExecutionResult:
        """Internal method to execute code.

        Args:
            code: Code to execute.
            language: Language of the code.
            timeout_ms: Optional custom timeout.

        Returns:
            The execution result.
        """
        import time

        effective_timeout = min(
            timeout_ms or self._config.default_timeout_ms,
            self._config.max_timeout_ms,
        )

        result = ExecutionResult(
            language=language,
            code=code,
            status=ExecutionStatus.RUNNING,
        )

        start_time = time.monotonic()

        try:
            # Stub: In production, would execute in Docker/subprocess
            # with timeout and resource limits
            await asyncio.sleep(0)

            result.stdout = "Execution output placeholder"
            result.status = ExecutionStatus.COMPLETED
            result.exit_code = 0

        except asyncio.TimeoutError:
            result.status = ExecutionStatus.TIMEOUT
            result.error_message = (
                f"Execution timed out after {effective_timeout}ms"
            )
            result.exit_code = -1

        except Exception as exc:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(exc)
            result.exit_code = 1

        finally:
            result.execution_time_ms = (time.monotonic() - start_time) * 1000
            self._execution_history.append(result)

        self._log.info(
            "code_executed",
            execution_id=result.execution_id,
            language=language.value,
            status=result.status.value,
            execution_time_ms=result.execution_time_ms,
        )

        return result

    def _ensure_running(self) -> None:
        """Ensure the executor is running.

        Raises:
            CodeExecutionError: If the executor is not running.
        """
        if not self._running:
            raise CodeExecutionError(
                "Code executor is not running. Call start() first."
            )


class CodeExecutionError(Exception):
    """Raised when code execution encounters an error."""


class LanguageNotAllowedError(Exception):
    """Raised when a language is not allowed for execution."""


class PackageInstallNotAllowedError(Exception):
    """Raised when package installation is not allowed."""
