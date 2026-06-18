"""Docker sandbox management tool for the AI MultiColony Ecosystem.

Provides Docker container lifecycle management for isolated execution,
including container create/start/stop/remove, command execution inside
containers, file copy in/out, and resource limits.
"""

from __future__ import annotations

import io
import os
import tarfile
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError, SandboxError
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


class DockerTool(BaseTool):
    """Docker sandbox management tool.

    Features:
    - Create, start, stop, and remove containers
    - Execute commands inside containers
    - Copy files to/from containers using tar archives
    - Resource limits (memory, CPU, PIDs)
    - Network control
    - Container status tracking
    - Graceful fallback when Docker is unavailable
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._default_image = self._config.get("image", "python:3.12-slim")
        self._containers: dict[str, dict[str, Any]] = {}
        self._docker_available: Optional[bool] = None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="docker",
            description="Docker container management for sandboxed execution",
            tool_type=ToolType.DOCKER,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description=(
                        "Docker action: create, start, stop, remove, exec, "
                        "list, copy_in, copy_out, inspect"
                    ),
                    required=True,
                    enum=[
                        "create", "start", "stop", "remove", "exec",
                        "list", "copy_in", "copy_out", "inspect",
                    ],
                ),
                ToolParameter(
                    name="container_id",
                    type="string",
                    description="Container ID or name",
                    required=False,
                ),
                ToolParameter(
                    name="image",
                    type="string",
                    description="Docker image for container creation",
                    required=False,
                    default=self._default_image,
                ),
                ToolParameter(
                    name="command",
                    type="string",
                    description="Command to execute in container",
                    required=False,
                ),
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source path for copy operations",
                    required=False,
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination path for copy operations",
                    required=False,
                ),
                ToolParameter(
                    name="memory_limit",
                    type="string",
                    description="Memory limit (e.g., '512m', '1g')",
                    required=False,
                    default="512m",
                ),
                ToolParameter(
                    name="cpu_limit",
                    type="number",
                    description="CPU limit (number of CPUs, e.g., 1.0)",
                    required=False,
                    default=1.0,
                ),
                ToolParameter(
                    name="pids_limit",
                    type="integer",
                    description="Maximum number of processes",
                    required=False,
                    default=100,
                ),
                ToolParameter(
                    name="network_disabled",
                    type="boolean",
                    description="Disable network access",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="working_dir",
                    type="string",
                    description="Working directory inside the container",
                    required=False,
                ),
                ToolParameter(
                    name="env",
                    type="object",
                    description="Environment variables for the container",
                    required=False,
                ),
            ],
            tags=["docker", "sandbox", "container"],
            requires_permission="docker.manage",
            timeout=300,
        )

    # ------------------------------------------------------------------
    # Docker client
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Get a Docker client, caching availability status.

        Returns:
            Docker client instance.

        Raises:
            ToolExecutionError: If Docker is not available.
        """
        if self._docker_available is False:
            raise ToolExecutionError(
                "Docker is not available (previous check failed)",
                tool_name="docker",
            )

        try:
            import docker
            client = docker.from_env()
            client.ping()  # Verify daemon is responsive
            self._docker_available = True
            return client
        except ImportError:
            self._docker_available = False
            raise ToolExecutionError(
                "Docker SDK not installed. Install with: pip install docker",
                tool_name="docker",
            )
        except Exception as e:
            self._docker_available = False
            raise ToolExecutionError(
                f"Docker not available: {e}",
                tool_name="docker",
            )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a Docker action."""
        action = tool_call.arguments.get("action", "")

        try:
            client = self._get_client()
        except ToolExecutionError:
            raise

        dispatch = {
            "create": self._create,
            "start": self._start,
            "stop": self._stop,
            "remove": self._remove,
            "exec": self._exec,
            "list": self._list,
            "copy_in": self._copy_in,
            "copy_out": self._copy_out,
            "inspect": self._inspect,
        }

        handler = dispatch.get(action)
        if handler is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Unknown Docker action: {action}",
            )

        try:
            return await handler(tool_call, client)
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"Docker action failed: {e}", tool_name="docker")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _create(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Create a new container."""
        image = tool_call.arguments.get("image", self._default_image)
        memory_limit = tool_call.arguments.get("memory_limit", "512m")
        cpu_limit = tool_call.arguments.get("cpu_limit", 1.0)
        pids_limit = tool_call.arguments.get("pids_limit", 100)
        network_disabled = tool_call.arguments.get("network_disabled", True)
        working_dir = tool_call.arguments.get("working_dir")
        env = tool_call.arguments.get("env")

        try:
            create_kwargs: dict[str, Any] = {
                "image": image,
                "command": "tail -f /dev/null",  # Keep container running
                "detach": True,
                "mem_limit": memory_limit,
                "nano_cpus": int(cpu_limit * 1e9),
                "pids_limit": pids_limit,
                "network_mode": "none" if network_disabled else "bridge",
                "labels": {"ai_multicolony_sandbox": "true"},
            }

            if working_dir:
                create_kwargs["working_dir"] = working_dir
            if env and isinstance(env, dict):
                create_kwargs["environment"] = {k: str(v) for k, v in env.items()}

            container = client.containers.create(**create_kwargs)
            short_id = container.id[:12]

            self._containers[short_id] = {
                "id": container.id,
                "short_id": short_id,
                "image": image,
                "status": "created",
                "memory_limit": memory_limit,
                "cpu_limit": cpu_limit,
                "network_disabled": network_disabled,
            }

            logger.info("docker_container_created", container_id=short_id, image=image)

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True,
                output=f"Created container: {short_id} (image: {image})",
                metadata={"container_id": short_id, "image": image},
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to create container: {e}", tool_name="docker")

    async def _start(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Start a stopped container."""
        container_id = tool_call.arguments.get("container_id", "")
        if not container_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error="container_id is required",
            )

        try:
            container = client.containers.get(container_id)
            container.start()
            short_id = container_id[:12]
            if short_id in self._containers:
                self._containers[short_id]["status"] = "running"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True, output=f"Started container: {short_id}",
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Start failed: {e}",
            )

    async def _stop(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Stop a running container."""
        container_id = tool_call.arguments.get("container_id", "")
        if not container_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error="container_id is required",
            )

        try:
            container = client.containers.get(container_id)
            container.stop(timeout=10)
            short_id = container_id[:12]
            if short_id in self._containers:
                self._containers[short_id]["status"] = "stopped"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True, output=f"Stopped container: {short_id}",
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Stop failed: {e}",
            )

    async def _remove(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Remove a container (force-stops if running)."""
        container_id = tool_call.arguments.get("container_id", "")
        if not container_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error="container_id is required",
            )

        try:
            container = client.containers.get(container_id)
            container.remove(force=True)
            short_id = container_id[:12]
            self._containers.pop(short_id, None)
            logger.info("docker_container_removed", container_id=short_id)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True, output=f"Removed container: {short_id}",
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Remove failed: {e}",
            )

    async def _exec(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Execute a command inside a container."""
        container_id = tool_call.arguments.get("container_id", "")
        command = tool_call.arguments.get("command", "")
        working_dir = tool_call.arguments.get("working_dir")

        if not container_id or not command:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error="container_id and command are required",
            )

        try:
            container = client.containers.get(container_id)

            exec_kwargs: dict[str, Any] = {
                "cmd": ["/bin/sh", "-c", command],
                "stdout": True,
                "stderr": True,
                "demux": True,
            }
            if working_dir:
                exec_kwargs["workdir"] = working_dir

            exec_result = container.exec_run(**exec_kwargs)

            stdout_bytes = exec_result.output[0] or b""
            stderr_bytes = exec_result.output[1] or b""
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")

            output = stdout_str
            if stderr_str:
                output += f"\n[stderr]\n{stderr_str}" if stdout_str else stderr_str

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=exec_result.exit_code == 0,
                output=output[:50000],
                exit_code=exec_result.exit_code,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Container exec failed: {e}",
            )

    async def _list(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """List containers (optionally filtered to managed ones)."""
        try:
            all_containers = tool_call.arguments.get("all", True)
            containers = client.containers.list(all=all_containers)

            lines: list[str] = []
            for c in containers:
                short_id = c.id[:12]
                image_tags = ", ".join(c.image.tags) if c.image.tags else c.image.id[:12]
                status = c.status
                name = c.name if hasattr(c, "name") else ""
                managed = " [managed]" if short_id in self._containers else ""
                lines.append(
                    f"  {short_id} | {image_tags} | {status} | {name}{managed}"
                )

            output = "Containers:\n" + "\n".join(lines) if lines else "No containers found"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True, output=output,
                metadata={"container_count": len(containers)},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"List failed: {e}",
            )

    async def _copy_in(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Copy a file from the host into a container.

        Uses tar archives for reliable file transfer.
        """
        container_id = tool_call.arguments.get("container_id", "")
        source = tool_call.arguments.get("source", "")
        destination = tool_call.arguments.get("destination", "")

        if not container_id or not source or not destination:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error="container_id, source, and destination are required",
            )

        if not os.path.isfile(source):
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Source file not found: {source}",
            )

        try:
            container = client.containers.get(container_id)

            # Create a tar archive of the source file
            filename = os.path.basename(source)
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(source, arcname=filename)
            tar_stream.seek(0)

            # Determine the destination directory
            dest_dir = destination.rsplit("/", 1)[0] if "/" in destination else "/"

            # Ensure destination directory exists
            container.exec_run(f"mkdir -p {dest_dir}")

            # Put the archive into the container
            container.put_archive(dest_dir, tar_stream)

            # If the destination path differs from filename in dest_dir, move it
            final_dest = destination
            default_dest = f"{dest_dir}/{filename}" if dest_dir != "/" else f"/{filename}"
            if final_dest != default_dest:
                container.exec_run(f"mv {default_dest} {final_dest}")

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True,
                output=f"Copied {source} -> {container_id[:12]}:{destination}",
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Copy in failed: {e}",
            )

    async def _copy_out(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Copy a file from a container to the host.

        Uses tar archives for reliable file transfer.
        """
        container_id = tool_call.arguments.get("container_id", "")
        source = tool_call.arguments.get("source", "")
        destination = tool_call.arguments.get("destination", "")

        if not container_id or not source or not destination:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error="container_id, source, and destination are required",
            )

        try:
            container = client.containers.get(container_id)

            # Get the file as a tar archive
            bits, stats = container.get_archive(source)

            # Extract from tar and write to host
            tar_stream = io.BytesIO()
            for chunk in bits:
                tar_stream.write(chunk)
            tar_stream.seek(0)

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)

            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                members = tar.getmembers()
                if len(members) == 1:
                    # Single file
                    member = members[0]
                    member.name = os.path.basename(destination)
                    tar.extract(member, path=os.path.dirname(destination) or ".")
                else:
                    # Multiple files/directory
                    tar.extractall(path=destination)

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True,
                output=f"Copied {container_id[:12]}:{source} -> {destination}",
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Copy out failed: {e}",
            )

    async def _inspect(self, tool_call: ToolCall, client: Any) -> ToolResult:
        """Inspect a container's details."""
        container_id = tool_call.arguments.get("container_id", "")
        if not container_id:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error="container_id is required",
            )

        try:
            import json as json_mod
            container = client.containers.get(container_id)
            attrs = container.attrs

            # Extract key information
            info = {
                "id": container.id[:12],
                "name": container.name,
                "status": container.status,
                "image": str(container.image.tags) if container.image.tags else container.image.id[:12],
                "created": attrs.get("Created", ""),
                "network_mode": attrs.get("HostConfig", {}).get("NetworkMode", ""),
                "memory_limit": attrs.get("HostConfig", {}).get("Memory", 0),
                "cpu_quota": attrs.get("HostConfig", {}).get("CpuQuota", 0),
                "pids_limit": attrs.get("HostConfig", {}).get("PidsLimit", 0),
            }

            output = "Container Info:\n"
            output += "\n".join(f"  {k}: {v}" for k, v in info.items())

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=True, output=output,
                metadata=info,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="docker",
                success=False, error=f"Inspect failed: {e}",
            )
