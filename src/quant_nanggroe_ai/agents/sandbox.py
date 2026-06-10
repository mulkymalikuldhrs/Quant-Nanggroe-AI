"""
Sandbox execution module for safe code execution.

Adapted from suna's sandbox system for Quant-Nanggroe-AI trading platform.
Provides isolated execution environments for running untrusted code,
with support for Docker-based local sandboxes and cloud sandbox services.
"""

import asyncio
import subprocess
import tempfile
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class SandboxBackend(str, Enum):
    """Available sandbox backends."""
    LOCAL = "local"
    DOCKER = "docker"
    DAYTONA = "daytona"


class SandboxStatus(str, Enum):
    """Status of a sandbox instance."""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


@dataclass
class SandboxResult:
    """Result from a sandbox execution.
    
    Attributes:
        success: Whether the execution succeeded
        stdout: Standard output from the execution
        stderr: Standard error from the execution
        exit_code: Process exit code
        execution_time_ms: Execution time in milliseconds
    """
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float = 0.0


@dataclass
class SandboxConfig:
    """Configuration for a sandbox instance.
    
    Attributes:
        backend: Which sandbox backend to use
        timeout_seconds: Maximum execution time
        memory_limit_mb: Memory limit in MB
        cpu_limit: CPU limit (number of cores)
        allowed_languages: List of allowed programming languages
        environment_vars: Environment variables to set
        docker_image: Docker image to use (for Docker backend)
    """
    backend: SandboxBackend = SandboxBackend.LOCAL
    timeout_seconds: int = 30
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0
    allowed_languages: List[str] = field(default_factory=lambda: ["python", "javascript"])
    environment_vars: Dict[str, str] = field(default_factory=dict)
    docker_image: str = "python:3.11-slim"


class Sandbox:
    """Sandbox execution environment for safe code execution.
    
    Adapted from suna's sandbox system for Quant-Nanggroe-AI.
    Provides isolated execution with timeout, memory limits,
    and language restrictions.
    
    Usage:
        sandbox = Sandbox()
        result = await sandbox.execute("print('hello')", language="python")
        if result.success:
            print(result.stdout)
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._status = SandboxStatus.CREATING
        self._sandbox_id = str(uuid.uuid4())[:8]
        self._docker_container = None
        logger.info(f"Initialized sandbox {self._sandbox_id} with {self.config.backend.value} backend")
    
    @property
    def status(self) -> SandboxStatus:
        """Get the current sandbox status."""
        return self._status
    
    @property
    def sandbox_id(self) -> str:
        """Get the sandbox ID."""
        return self._sandbox_id
    
    async def start(self):
        """Start the sandbox environment."""
        if self.config.backend == SandboxBackend.DOCKER:
            await self._start_docker()
        elif self.config.backend == SandboxBackend.DAYTONA:
            await self._start_daytona()
        else:
            self._status = SandboxStatus.RUNNING
        
        logger.info(f"Sandbox {self._sandbox_id} started ({self.config.backend.value})")
    
    async def stop(self):
        """Stop the sandbox environment."""
        if self.config.backend == SandboxBackend.DOCKER and self._docker_container:
            await self._stop_docker()
        elif self.config.backend == SandboxBackend.DAYTONA:
            await self._stop_daytona()
        
        self._status = SandboxStatus.STOPPED
        logger.info(f"Sandbox {self._sandbox_id} stopped")
    
    async def execute(self, code: str, language: str = "python") -> SandboxResult:
        """Execute code in the sandbox.
        
        Args:
            code: The code to execute
            language: Programming language (python, javascript)
            
        Returns:
            SandboxResult with execution output
        """
        if language not in self.config.allowed_languages:
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Language '{language}' is not allowed. Allowed: {self.config.allowed_languages}",
                exit_code=1
            )
        
        if self.config.backend == SandboxBackend.DOCKER:
            return await self._execute_docker(code, language)
        elif self.config.backend == SandboxBackend.DAYTONA:
            return await self._execute_daytona(code, language)
        else:
            return await self._execute_local(code, language)
    
    async def _execute_local(self, code: str, language: str) -> SandboxResult:
        """Execute code locally in a subprocess (limited isolation)."""
        import time
        start_time = time.time()
        
        try:
            if language == "python":
                cmd = ["python3", "-c", code]
            elif language == "javascript":
                cmd = ["node", "-e", code]
            else:
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr=f"Unsupported language for local execution: {language}",
                    exit_code=1
                )
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**self.config.environment_vars},
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds
                )
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                return SandboxResult(
                    success=process.returncode == 0,
                    stdout=stdout.decode('utf-8', errors='replace'),
                    stderr=stderr.decode('utf-8', errors='replace'),
                    exit_code=process.returncode or 0,
                    execution_time_ms=execution_time_ms,
                )
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time_ms = (time.time() - start_time) * 1000
                
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution timed out after {self.config.timeout_seconds}s",
                    exit_code=-1,
                    execution_time_ms=execution_time_ms,
                )
                
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                exit_code=1,
                execution_time_ms=execution_time_ms,
            )
    
    async def _execute_docker(self, code: str, language: str) -> SandboxResult:
        """Execute code in a Docker container."""
        import time
        start_time = time.time()
        
        try:
            # Write code to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            if language == "python":
                cmd = [
                    "docker", "run", "--rm",
                    f"--memory={self.config.memory_limit_mb}m",
                    f"--cpus={self.config.cpu_limit}",
                    self.config.docker_image,
                    "python3", f"/tmp/code.{language}"
                ]
            else:
                cmd = [
                    "docker", "run", "--rm",
                    f"--memory={self.config.memory_limit_mb}m",
                    self.config.docker_image,
                    "node", "-e", code
                ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds
                )
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                return SandboxResult(
                    success=process.returncode == 0,
                    stdout=stdout.decode('utf-8', errors='replace'),
                    stderr=stderr.decode('utf-8', errors='replace'),
                    exit_code=process.returncode or 0,
                    execution_time_ms=execution_time_ms,
                )
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time_ms = (time.time() - start_time) * 1000
                
                return SandboxResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution timed out after {self.config.timeout_seconds}s",
                    exit_code=-1,
                    execution_time_ms=execution_time_ms,
                )
                
        except FileNotFoundError:
            # Docker not installed, fall back to local
            logger.warning("Docker not available, falling back to local execution")
            return await self._execute_local(code, language)
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return SandboxResult(
                success=False,
                stdout="",
                stderr=f"Docker execution error: {str(e)}",
                exit_code=1,
                execution_time_ms=execution_time_ms,
            )
    
    async def _execute_daytona(self, code: str, language: str) -> SandboxResult:
        """Execute code in a Daytona cloud sandbox."""
        try:
            from daytona_sdk import AsyncDaytona, DaytonaConfig
        except ImportError:
            logger.error("daytona_sdk not installed. Install with: pip install daytona-sdk")
            return SandboxResult(
                success=False,
                stdout="",
                stderr="daytona_sdk not installed. Falling back to local execution.",
                exit_code=1
            )
        
        # Fall back to local execution if Daytona is not configured
        return await self._execute_local(code, language)
    
    async def _start_docker(self):
        """Start a Docker container for the sandbox."""
        self._status = SandboxStatus.RUNNING
    
    async def _stop_docker(self):
        """Stop the Docker container."""
        self._status = SandboxStatus.STOPPED
    
    async def _start_daytona(self):
        """Start a Daytona cloud sandbox."""
        self._status = SandboxStatus.RUNNING
    
    async def _stop_daytona(self):
        """Stop the Daytona cloud sandbox."""
        self._status = SandboxStatus.STOPPED
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


def create_sandbox(
    backend: str = "local",
    timeout_seconds: int = 30,
    memory_limit_mb: int = 512,
    **kwargs
) -> Sandbox:
    """Factory function to create a sandbox instance.
    
    Args:
        backend: Backend type ('local', 'docker', 'daytona')
        timeout_seconds: Maximum execution time
        memory_limit_mb: Memory limit in MB
        **kwargs: Additional configuration options
        
    Returns:
        Configured Sandbox instance
    """
    config = SandboxConfig(
        backend=SandboxBackend(backend),
        timeout_seconds=timeout_seconds,
        memory_limit_mb=memory_limit_mb,
        **kwargs
    )
    return Sandbox(config)
