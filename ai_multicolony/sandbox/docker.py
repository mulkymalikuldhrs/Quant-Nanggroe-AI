"""Docker-based sandbox for isolated code execution.

Provides containerized execution environment with resource limits,
file transfer, and lifecycle management.
"""

from __future__ import annotations

import asyncio
import io
import tarfile
import time
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.exceptions import SandboxError

logger = get_logger(__name__)


class DockerSandbox:
    """Docker-based sandbox for isolated code execution.

    Features:
    - Create isolated execution environments
    - Run code with resource limits (CPU, memory, network)
    - File system isolation with file transfer
    - Network control (disabled by default)
    - Automatic cleanup
    - Working directory management
    - Environment variable injection
    """

    def __init__(
        self,
        image: str = "python:3.12-slim",
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
        timeout: int = 300,
        network_disabled: bool = True,
        work_dir: str = "/workspace",
        env_vars: Optional[dict[str, str]] = None,
    ) -> None:
        self._image = image
        self._memory_limit = memory_limit
        self._cpu_limit = cpu_limit
        self._timeout = timeout
        self._network_disabled = network_disabled
        self._work_dir = work_dir
        self._env_vars = env_vars or {}
        self._container_id: Optional[str] = None
        self._created_at: Optional[float] = None

    async def create(self) -> str:
        """Create a new sandbox container.

        Returns:
            The container ID.
        """
        try:
            import docker
            client = docker.from_env()

            container = client.containers.run(
                self._image,
                command=f"bash -c 'mkdir -p {self._work_dir} && tail -f /dev/null'",
                detach=True,
                mem_limit=self._memory_limit,
                nano_cpus=int(self._cpu_limit * 1e9),
                network_mode="none" if self._network_disabled else "bridge",
                working_dir=self._work_dir,
                environment=self._env_vars,
                labels={
                    "ai_multicolony_sandbox": "true",
                    "ai_multicolony_created": str(time.time()),
                },
                volumes={
                    self._work_dir: {"bind": self._work_dir, "mode": "rw"},
                } if False else None,  # Don't mount by default
            )

            self._container_id = container.id[:12]
            self._created_at = time.time()
            logger.info("sandbox_created", container_id=self._container_id)
            return self._container_id

        except ImportError:
            raise SandboxError("Docker SDK not installed. Install with: pip install docker", sandbox_type="docker")
        except Exception as e:
            raise SandboxError(f"Failed to create sandbox: {e}", sandbox_type="docker")

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        work_dir: Optional[str] = None,
        env_vars: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Execute a command in the sandbox.

        Args:
            command: Command to execute.
            timeout: Override timeout in seconds.
            work_dir: Override working directory.
            env_vars: Additional environment variables for this command.

        Returns:
            Dictionary with stdout, stderr, exit_code, and duration.
        """
        if not self._container_id:
            raise SandboxError("Sandbox not created", sandbox_type="docker")

        start_time = time.time()

        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(self._container_id)

            # Build exec command
            exec_kwargs: dict[str, Any] = {
                "demux": True,
                "workdir": work_dir or self._work_dir,
            }
            if env_vars:
                exec_kwargs["environment"] = env_vars

            exec_result = container.exec_run(command, **exec_kwargs)
            stdout = exec_result.output[0] or b""
            stderr = exec_result.output[1] or b""

            duration = time.time() - start_time

            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": exec_result.exit_code,
                "duration": duration,
                "command": command,
            }
        except Exception as e:
            raise SandboxError(f"Execution failed: {e}", sandbox_type="docker")

    async def execute_python(self, code: str, timeout: Optional[int] = None) -> dict[str, Any]:
        """Execute Python code in the sandbox.

        Args:
            code: Python code to execute.
            timeout: Execution timeout.

        Returns:
            Execution result.
        """
        # Write code to a temp file and execute it
        await self.write_file("/tmp/_exec.py", code)
        return await self.execute("python /tmp/_exec.py", timeout=timeout)

    async def copy_file(self, host_path: str, container_path: str) -> None:
        """Copy a file from the host into the sandbox.

        Args:
            host_path: Path on the host.
            container_path: Path in the container.
        """
        if not self._container_id:
            raise SandboxError("Sandbox not created", sandbox_type="docker")

        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(self._container_id)

            with open(host_path, "rb") as f:
                content = f.read()
                tar_stream = io.BytesIO()
                filename = container_path.rsplit("/", 1)[-1]
                tar_info = tarfile.TarInfo(name=filename)
                tar_info.size = len(content)
                with tarfile.open(fileobj=tar_stream, mode="w") as tar_file:
                    tar_file.addfile(tar_info, io.BytesIO(content))
                tar_stream.seek(0)
                container.put_archive(
                    container_path.rsplit("/", 1)[0] or "/",
                    tar_stream,
                )
        except Exception as e:
            raise SandboxError(f"Copy failed: {e}", sandbox_type="docker")

    async def write_file(self, container_path: str, content: str) -> None:
        """Write a string as a file in the sandbox.

        Args:
            container_path: Path in the container.
            content: File content.
        """
        if not self._container_id:
            raise SandboxError("Sandbox not created", sandbox_type="docker")

        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(self._container_id)

            content_bytes = content.encode("utf-8")
            tar_stream = io.BytesIO()
            filename = container_path.rsplit("/", 1)[-1]
            tar_info = tarfile.TarInfo(name=filename)
            tar_info.size = len(content_bytes)
            with tarfile.open(fileobj=tar_stream, mode="w") as tar_file:
                tar_file.addfile(tar_info, io.BytesIO(content_bytes))
            tar_stream.seek(0)
            container.put_archive(
                container_path.rsplit("/", 1)[0] or "/",
                tar_stream,
            )
        except Exception as e:
            raise SandboxError(f"Write failed: {e}", sandbox_type="docker")

    async def read_file(self, container_path: str) -> str:
        """Read a file from the sandbox.

        Args:
            container_path: Path in the container.

        Returns:
            File content as string.
        """
        if not self._container_id:
            raise SandboxError("Sandbox not created", sandbox_type="docker")

        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(self._container_id)

            bits, stat = container.get_archive(container_path)
            tar_stream = io.BytesIO()
            for chunk in bits:
                tar_stream.write(chunk)
            tar_stream.seek(0)

            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                members = tar.getmembers()
                if members:
                    f = tar.extractfile(members[0])
                    if f:
                        return f.read().decode("utf-8", errors="replace")

            return ""
        except Exception as e:
            raise SandboxError(f"Read failed: {e}", sandbox_type="docker")

    async def get_stats(self) -> dict[str, Any]:
        """Get container resource usage statistics.

        Returns:
            Container stats.
        """
        if not self._container_id:
            return {"status": "not_created"}

        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(self._container_id)
            stats = container.stats(stream=False)

            return {
                "container_id": self._container_id,
                "status": container.status,
                "cpu_percent": self._calculate_cpu_percent(stats),
                "memory_usage": stats.get("memory_stats", {}).get("usage", 0),
                "memory_limit": stats.get("memory_stats", {}).get("limit", 0),
                "network_rx": sum(
                    v.get("rx_bytes", 0) for v in stats.get("networks", {}).values()
                ),
                "network_tx": sum(
                    v.get("tx_bytes", 0) for v in stats.get("networks", {}).values()
                ),
            }
        except Exception as e:
            return {"container_id": self._container_id, "error": str(e)}

    def _calculate_cpu_percent(self, stats: dict[str, Any]) -> float:
        """Calculate CPU usage percentage from Docker stats."""
        try:
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                stats["precpu_stats"]["system_cpu_usage"]
            num_cpus = stats["cpu_stats"]["online_cpus"]

            if system_delta > 0 and cpu_delta > 0:
                return (cpu_delta / system_delta) * num_cpus * 100.0
        except (KeyError, TypeError):
            pass
        return 0.0

    async def destroy(self) -> None:
        """Destroy the sandbox container."""
        if not self._container_id:
            return

        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(self._container_id)
            container.remove(force=True)
            logger.info("sandbox_destroyed", container_id=self._container_id)
        except Exception as e:
            logger.error("sandbox_destroy_error", error=str(e))
        finally:
            self._container_id = None

    @property
    def is_running(self) -> bool:
        """Check if the sandbox is running."""
        return self._container_id is not None

    @property
    def container_id(self) -> Optional[str]:
        """Get the container ID."""
        return self._container_id
