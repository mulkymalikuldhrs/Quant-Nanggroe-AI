"""DockerTool – container lifecycle management with port forwarding.

Autonomy levels:
  - L1: create, list, inspect
  - L2: exec, port forwarding
  - L3: destroy, prune
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)


class ContainerRecord:
    """In-memory record of a managed container."""

    __slots__ = (
        "container_id", "image", "status", "created_at",
        "ports", "env", "labels", "working_dir", "command",
    )

    def __init__(
        self,
        container_id: str,
        image: str = "python:3.12",
        command: str = "",
        env: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        labels: Optional[Dict[str, str]] = None,
        working_dir: str = "/app",
    ) -> None:
        self.container_id = container_id
        self.image = image
        self.command = command
        self.status: str = "running"
        self.created_at: float = time.time()
        self.ports: Dict[str, int] = ports or {}
        self.env: Dict[str, str] = env or {}
        self.labels: Dict[str, str] = labels or {}
        self.working_dir = working_dir

    def to_dict(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id,
            "image": self.image,
            "status": self.status,
            "created_at": self.created_at,
            "ports": self.ports,
            "env_keys": list(self.env.keys()),
            "labels": self.labels,
            "working_dir": self.working_dir,
            "command": self.command,
        }


class DockerTool(MCPTool):
    """Container management: create, execute, destroy, and manage port forwarding.

    This is a simulated Docker interface.  Real Docker Engine integration
    would replace the simulation internals while preserving the same
    MCP interface.
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "sandbox.docker"

    def category(self) -> str:
        return "sandbox"

    def autonomy_level(self) -> int:
        return 1  # minimum; varies per action

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create", "exec", "destroy", "list", "inspect",
                        "port_forward", "stop", "start", "prune",
                    ],
                    "description": "Container action",
                },
                "image": {
                    "type": "string",
                    "default": "python:3.12",
                    "description": "Container image",
                },
                "command": {
                    "type": "string",
                    "description": "Command to run in container",
                },
                "container_id": {
                    "type": "string",
                    "description": "Target container ID",
                },
                "env": {
                    "type": "object",
                    "description": "Environment variables",
                    "additionalProperties": {"type": "string"},
                },
                "ports": {
                    "type": "object",
                    "description": "Port mappings {container_port: host_port}",
                    "additionalProperties": {"type": "integer"},
                },
                "labels": {
                    "type": "object",
                    "description": "Container labels",
                    "additionalProperties": {"type": "string"},
                },
                "working_dir": {
                    "type": "string",
                    "default": "/app",
                    "description": "Working directory inside container",
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "Execution timeout in seconds",
                },
                "remove": {
                    "type": "boolean",
                    "default": False,
                    "description": "Auto-remove container after execution",
                },
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "container_id": {"type": "string"},
                "output": {"type": "string"},
                "data": {"type": "object"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 6001, "message": "Container not found"},
            {"code": 6002, "message": "Image not available"},
            {"code": 6003, "message": "Container already running"},
            {"code": 6004, "message": "Container already stopped"},
            {"code": 6005, "message": "Execution timeout"},
            {"code": 6006, "message": "Port conflict"},
        ]

    # ── Constructor ──────────────────────────────────────────────

    def __init__(self) -> None:
        super().__init__()
        self._containers: Dict[str, ContainerRecord] = {}
        self._next_id: int = 1

    # ── Autonomy mapping ─────────────────────────────────────────

    @staticmethod
    def action_autonomy(action: str) -> int:
        mapping = {
            "create": 1, "list": 1, "inspect": 1,
            "exec": 2, "port_forward": 2, "start": 2, "stop": 2,
            "destroy": 3, "prune": 3,
        }
        return mapping.get(action, 2)

    # ── Execute ──────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action: str = params["action"]
        autonomy = context.get("autonomy_level", 0)
        required = self.action_autonomy(action)

        if autonomy < required:
            self.record_call(False)
            return {
                "success": False,
                "container_id": params.get("container_id", ""),
                "output": "",
                "data": {"error": f"Action '{action}' requires L{required}, current L{autonomy}"},
            }

        dispatch = {
            "create": self._create,
            "exec": self._exec,
            "destroy": self._destroy,
            "list": self._list,
            "inspect": self._inspect,
            "port_forward": self._port_forward,
            "stop": self._stop,
            "start": self._start,
            "prune": self._prune,
        }

        handler = dispatch.get(action)
        if handler is None:
            self.record_call(False)
            return {
                "success": False,
                "container_id": params.get("container_id", ""),
                "output": "",
                "data": {"error": f"Unknown action: {action}"},
            }

        start = time.monotonic()
        try:
            result = await handler(params)
            duration = (time.monotonic() - start) * 1000
            self.record_call(result.get("success", True), duration)
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {
                "success": False,
                "container_id": params.get("container_id", ""),
                "output": str(exc),
                "data": {},
            }

    # ── Action implementations ───────────────────────────────────

    async def _create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cid = f"container-{self._next_id}"
        self._next_id += 1

        container = ContainerRecord(
            container_id=cid,
            image=params.get("image", "python:3.12"),
            command=params.get("command", ""),
            env=params.get("env"),
            ports=params.get("ports"),
            labels=params.get("labels"),
            working_dir=params.get("working_dir", "/app"),
        )
        self._containers[cid] = container

        logger.info("Container created: %s (image=%s)", cid, container.image)
        return {
            "success": True,
            "container_id": cid,
            "output": "",
            "data": {
                "image": container.image,
                "status": container.status,
                "ports": container.ports,
                "working_dir": container.working_dir,
            },
        }

    async def _exec(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cid = params.get("container_id", "")
        command = params.get("command", "")
        timeout = params.get("timeout", 30)
        remove = params.get("remove", False)

        if cid not in self._containers:
            return {
                "success": False,
                "container_id": cid,
                "output": f"Container not found: {cid}",
                "data": {},
            }

        container = self._containers[cid]
        if container.status != "running":
            return {
                "success": False,
                "container_id": cid,
                "output": f"Container not running (status: {container.status})",
                "data": {},
            }

        # Simulate command execution
        output = f"[{container.image}] $ {command}\nCommand executed successfully in {container.working_dir}"

        if remove:
            del self._containers[cid]
            output += "\nContainer auto-removed."

        return {
            "success": True,
            "container_id": cid,
            "output": output,
            "data": {"exit_code": 0, "timeout": timeout},
        }

    async def _destroy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cid = params.get("container_id", "")

        if cid not in self._containers:
            return {
                "success": False,
                "container_id": cid,
                "output": f"Container not found: {cid}",
                "data": {},
            }

        container = self._containers.pop(cid)
        return {
            "success": True,
            "container_id": cid,
            "output": f"Container {cid} destroyed",
            "data": {"image": container.image, "previous_status": container.status},
        }

    async def _list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        containers = [c.to_dict() for c in self._containers.values()]
        return {
            "success": True,
            "container_id": "",
            "output": "",
            "data": {"containers": containers, "count": len(containers)},
        }

    async def _inspect(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cid = params.get("container_id", "")

        if cid not in self._containers:
            return {
                "success": False,
                "container_id": cid,
                "output": f"Container not found: {cid}",
                "data": {},
            }

        container = self._containers[cid]
        return {
            "success": True,
            "container_id": cid,
            "output": "",
            "data": container.to_dict(),
        }

    async def _port_forward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cid = params.get("container_id", "")
        ports = params.get("ports", {})

        if cid not in self._containers:
            return {
                "success": False,
                "container_id": cid,
                "output": f"Container not found: {cid}",
                "data": {},
            }

        container = self._containers[cid]
        # Check for port conflicts
        for container_port, host_port in ports.items():
            for other in self._containers.values():
                if other.container_id != cid and host_port in other.ports.values():
                    return {
                        "success": False,
                        "container_id": cid,
                        "output": f"Port conflict: host port {host_port} already in use by {other.container_id}",
                        "data": {},
                    }

        container.ports.update(ports)

        return {
            "success": True,
            "container_id": cid,
            "output": f"Port forwarding configured: {ports}",
            "data": {"ports": container.ports},
        }

    async def _stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cid = params.get("container_id", "")

        if cid not in self._containers:
            return {
                "success": False,
                "container_id": cid,
                "output": f"Container not found: {cid}",
                "data": {},
            }

        container = self._containers[cid]
        if container.status == "stopped":
            return {
                "success": False,
                "container_id": cid,
                "output": "Container already stopped",
                "data": {},
            }

        container.status = "stopped"
        return {
            "success": True,
            "container_id": cid,
            "output": f"Container {cid} stopped",
            "data": {},
        }

    async def _start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cid = params.get("container_id", "")

        if cid not in self._containers:
            return {
                "success": False,
                "container_id": cid,
                "output": f"Container not found: {cid}",
                "data": {},
            }

        container = self._containers[cid]
        if container.status == "running":
            return {
                "success": False,
                "container_id": cid,
                "output": "Container already running",
                "data": {},
            }

        container.status = "running"
        return {
            "success": True,
            "container_id": cid,
            "output": f"Container {cid} started",
            "data": {},
        }

    async def _prune(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Remove all stopped containers."""
        stopped = [
            cid for cid, c in self._containers.items() if c.status == "stopped"
        ]
        for cid in stopped:
            del self._containers[cid]

        return {
            "success": True,
            "container_id": "",
            "output": f"Pruned {len(stopped)} stopped containers",
            "data": {"pruned": stopped, "remaining": len(self._containers)},
        }
