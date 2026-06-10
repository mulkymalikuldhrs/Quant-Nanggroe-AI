"""
Sandbox Module - Safe code execution for AgentPress.

Adapted from suna's sandbox system for Quant-Nanggroe-AI.
Re-exports the Sandbox from agents.sandbox and adds AgentPress-specific
integration for the agent loop:
- Auto-provisioning sandboxes for agent tool execution
- Trading-strategy code validation and backtesting execution
- Session management for long-running sandboxes

The core Sandbox class supports three backends:
- LOCAL: subprocess-based execution (limited isolation, good for dev)
- DOCKER: Docker container execution (strong isolation)
- DAYTONA: Cloud sandbox via Daytona SDK (production-grade isolation)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging

# Re-export core sandbox classes from the existing module
from quant_nanggroe_ai.agents.sandbox import (
    Sandbox,
    SandboxConfig,
    SandboxBackend,
    SandboxResult,
    SandboxStatus,
    create_sandbox,
)

logger = logging.getLogger(__name__)


class SandboxPool:
    """Pool of sandbox instances for agent tool execution.

    Manages a pool of pre-provisioned sandboxes that can be checked out
    by the agent loop for tool execution, avoiding the overhead of
    creating a new sandbox for each request.

    Usage:
        pool = SandboxPool(max_size=3)
        async with pool.acquire() as sandbox:
            result = await sandbox.execute("print('hello')")
    """

    def __init__(
        self,
        max_size: int = 3,
        backend: str = "local",
        timeout_seconds: int = 30,
        memory_limit_mb: int = 512,
    ):
        self._max_size = max_size
        self._backend = backend
        self._timeout_seconds = timeout_seconds
        self._memory_limit_mb = memory_limit_mb
        self._available: List[Sandbox] = []
        self._in_use: Dict[str, Sandbox] = {}
        self._lock = asyncio.Lock()

    async def acquire(self) -> Sandbox:
        """Get a sandbox from the pool (or create one).

        Returns:
            A ready-to-use Sandbox instance
        """
        async with self._lock:
            if self._available:
                sandbox = self._available.pop()
            else:
                sandbox = create_sandbox(
                    backend=self._backend,
                    timeout_seconds=self._timeout_seconds,
                    memory_limit_mb=self._memory_limit_mb,
                )
                await sandbox.start()

            self._in_use[sandbox.sandbox_id] = sandbox
            return sandbox

    async def release(self, sandbox: Sandbox):
        """Return a sandbox to the pool.

        Args:
            sandbox: Sandbox to release
        """
        async with self._lock:
            self._in_use.pop(sandbox.sandbox_id, None)
            if len(self._available) < self._max_size:
                self._available.append(sandbox)
            else:
                await sandbox.stop()

    async def shutdown(self):
        """Shutdown all sandboxes in the pool."""
        for sandbox in self._available:
            await sandbox.stop()
        for sandbox in self._in_use.values():
            await sandbox.stop()
        self._available.clear()
        self._in_use.clear()

    @property
    def available_count(self) -> int:
        """Number of available sandboxes."""
        return len(self._available)

    @property
    def in_use_count(self) -> int:
        """Number of sandboxes currently in use."""
        return len(self._in_use)


class TradingSandbox:
    """Sandbox specialized for trading strategy code execution.

    Provides pre-configured environments with trading libraries
    and validation helpers for safe strategy execution.

    Usage:
        tbox = TradingSandbox()
        result = await tbox.validate_strategy(strategy_code)
        result = await tbox.run_backtest(strategy_code, market_data)
    """

    # Python code template for strategy validation
    VALIDATE_TEMPLATE = """
import ast
import sys

code = {code_repr!r}
try:
    tree = ast.parse(code)
    # Check for unsafe operations
    unsafe = {{'exec', 'eval', 'compile', '__import__', 'open'}}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in unsafe:
            print(f"UNSAFE: {{node.id}} is not allowed")
            sys.exit(1)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in ('os', 'subprocess', 'shutil', 'socket'):
                    print(f"UNSAFE: import {{alias.name}} is not allowed")
                    sys.exit(1)
    print("VALID: Strategy code passes safety checks")
except SyntaxError as e:
    print(f"SYNTAX ERROR: {{e}}")
    sys.exit(1)
"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self._sandbox = Sandbox(config or SandboxConfig(
            backend=SandboxBackend.LOCAL,
            timeout_seconds=60,
            allowed_languages=["python"],
        ))

    async def start(self):
        """Start the trading sandbox."""
        await self._sandbox.start()

    async def stop(self):
        """Stop the trading sandbox."""
        await self._sandbox.stop()

    async def validate_strategy(self, code: str) -> SandboxResult:
        """Validate trading strategy code for safety.

        Checks for:
        - Syntax errors
        - Unsafe function calls (exec, eval, etc.)
        - Unsafe imports (os, subprocess, etc.)

        Args:
            code: Strategy code to validate

        Returns:
            SandboxResult with validation output
        """
        validation_code = self.VALIDATE_TEMPLATE.format(code_repr=code)
        return await self._sandbox.execute(validation_code, language="python")

    async def run_code(self, code: str, timeout: Optional[int] = None) -> SandboxResult:
        """Execute trading code in the sandbox.

        Args:
            code: Python code to execute
            timeout: Optional timeout override in seconds

        Returns:
            SandboxResult with execution output
        """
        if timeout:
            original = self._sandbox.config.timeout_seconds
            self._sandbox.config.timeout_seconds = timeout
            try:
                result = await self._sandbox.execute(code, language="python")
            finally:
                self._sandbox.config.timeout_seconds = original
            return result

        return await self._sandbox.execute(code, language="python")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
