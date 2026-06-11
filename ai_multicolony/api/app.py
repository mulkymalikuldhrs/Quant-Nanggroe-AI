"""FastAPI application factory and configuration.

Creates the FastAPI app instance with middleware, CORS, exception
handlers, lifespan events, and mounted route routers.
"""

from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from ..config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: Any):
    """ASGI lifespan handler – startup and shutdown logic."""
    logger.info("AI-MultiColony API starting up")
    # Startup: initialise services, warm connections, etc.
    settings = get_settings()
    logger.info("Settings loaded: debug=%s, log_level=%s", settings.debug, settings.log_level)
    yield
    # Shutdown: flush logs, close connections, etc.
    logger.info("AI-MultiColony API shutting down")


def create_app(
    agent_registry: Any = None,
    colony_manager: Any = None,
    mcp_server: Any = None,
    memory_manager: Any = None,
    task_scheduler: Any = None,
    audit_trail: Any = None,
) -> "FastAPIApp":
    """Factory function that creates and returns a configured FastAPIApp.

    Parameters
    ----------
    agent_registry : AgentRegistry, optional
    colony_manager : ColonyManager, optional
    mcp_server : MCPServer, optional
    memory_manager : MemoryManager, optional
    task_scheduler : TaskScheduler, optional
    audit_trail : AuditTrail, optional

    Returns
    -------
    FastAPIApp
    """
    from .routes.agents import AgentRoutes
    from .routes.colony import ColonyRoutes
    from .routes.tools import ToolRoutes
    from .routes.memory import MemoryRoutes
    from .routes.tasks import TaskRoutes

    app = FastAPIApp(
        agent_registry=agent_registry,
        colony_manager=colony_manager,
        mcp_server=mcp_server,
        memory_manager=memory_manager,
        task_scheduler=task_scheduler,
        audit_trail=audit_trail,
    )

    # Attach route handlers
    app._agent_routes = AgentRoutes(agent_registry)
    app._colony_routes = ColonyRoutes(colony_manager)
    app._tool_routes = ToolRoutes(mcp_server)
    app._memory_routes = MemoryRoutes(memory_manager)
    app._task_routes = TaskRoutes(colony_manager, task_scheduler)

    logger.info("FastAPI app created with routes")
    return app


class FastAPIApp:
    """FastAPI application wrapper.

    Provides a framework-agnostic interface that mirrors what a real
    FastAPI app would expose.  Can be used standalone or adapted to
    work with an actual FastAPI instance.

    Parameters
    ----------
    agent_registry : AgentRegistry, optional
    colony_manager : ColonyManager, optional
    mcp_server : MCPServer, optional
    memory_manager : MemoryManager, optional
    """

    def __init__(
        self,
        agent_registry: Any = None,
        colony_manager: Any = None,
        mcp_server: Any = None,
        memory_manager: Any = None,
        task_scheduler: Any = None,
        audit_trail: Any = None,
    ):
        self.agent_registry = agent_registry
        self.colony_manager = colony_manager
        self.mcp_server = mcp_server
        self.memory_manager = memory_manager
        self.task_scheduler = task_scheduler
        self.audit_trail = audit_trail
        self._start_time = time.time()
        self._routes: Dict[str, Any] = {}

        # Route handlers (attached by create_app or manually)
        self._agent_routes: Any = None
        self._colony_routes: Any = None
        self._tool_routes: Any = None
        self._memory_routes: Any = None
        self._task_routes: Any = None

        # Middleware
        from .middleware import AuthMiddleware, RateLimitMiddleware, RequestLoggingMiddleware, ErrorHandlingMiddleware

        self.auth = AuthMiddleware()
        self.rate_limiter = RateLimitMiddleware()
        self.request_logger = RequestLoggingMiddleware()
        self.error_handler = ErrorHandlingMiddleware()

        # Settings
        self._settings = get_settings()

    # ── Health / Info ──────────────────────────────────────────────────────

    def get_health(self) -> Dict[str, Any]:
        """Return system health information."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "agents": self.agent_registry.total_agents if self.agent_registry and hasattr(self.agent_registry, "total_agents") else 0,
            "colonies": self.colony_manager.colony_count if self.colony_manager else 0,
            "tools": self.mcp_server.tool_count if self.mcp_server and hasattr(self.mcp_server, "tool_count") else 0,
        }

    # ── Route dispatch (generic) ──────────────────────────────────────────

    async def dispatch(self, method: str, path: str, **kwargs: Any) -> Any:
        """Dispatch a request to the appropriate route handler.

        This is a generic dispatcher that can be used programmatically
        or adapted to work with a real ASGI framework.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, DELETE, etc.)
        path : str
            URL path.
        **kwargs
            Additional parameters (body, headers, etc.)

        Returns
        -------
        Response data (dict or model).
        """
        start = time.time()
        status_code = 200

        try:
            result = await self._route_dispatch(method, path, **kwargs)
            return result
        except Exception as exc:
            status_code = self.error_handler.get_status_code(exc)
            error = self.error_handler.format_error(exc)
            return error
        finally:
            duration = (time.time() - start) * 1000
            self.request_logger.log_request(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration,
            )

    async def _route_dispatch(self, method: str, path: str, **kwargs: Any) -> Any:
        """Internal route dispatcher."""
        # ── Agent routes ───────────────────────────────────────────────
        if path == "/api/v1/agents" and method == "POST":
            return await self._agent_routes.create_agent(kwargs.get("body"))
        elif path == "/api/v1/agents" and method == "GET":
            return await self._agent_routes.list_agents()
        elif path.startswith("/api/v1/agents/") and method == "GET":
            agent_id = path.split("/")[-1]
            return await self._agent_routes.get_agent(agent_id)
        elif path.startswith("/api/v1/agents/") and path.endswith("/execute") and method == "POST":
            agent_id = path.split("/")[-2]
            return await self._agent_routes.execute_task(agent_id, kwargs.get("body"))
        elif path.startswith("/api/v1/agents/") and method == "DELETE":
            agent_id = path.split("/")[-1]
            return await self._agent_routes.terminate_agent(agent_id)

        # ── Colony routes ──────────────────────────────────────────────
        elif path == "/api/v1/colonies" and method == "POST":
            return await self._colony_routes.create_colony(kwargs.get("body"))
        elif path == "/api/v1/colonies" and method == "GET":
            return await self._colony_routes.list_colonies()
        elif path.startswith("/api/v1/colonies/") and path.endswith("/scale") and method == "POST":
            colony_id = path.split("/")[-2]
            return await self._colony_routes.scale_colony(colony_id, kwargs.get("body"))
        elif path.startswith("/api/v1/colonies/") and method == "GET":
            colony_id = path.split("/")[-1]
            return await self._colony_routes.get_colony(colony_id)

        # ── Tool routes ────────────────────────────────────────────────
        elif path == "/api/v1/tools" and method == "GET":
            return await self._tool_routes.list_tools()
        elif path.startswith("/api/v1/tools/") and path.endswith("/call") and method == "POST":
            tool_name = path.split("/")[-2]
            return await self._tool_routes.call_tool(tool_name, kwargs.get("body"))
        elif path.startswith("/api/v1/tools/") and method == "GET":
            tool_name = path.split("/")[-1]
            return await self._tool_routes.describe_tool(tool_name)

        # ── Memory routes ──────────────────────────────────────────────
        elif path == "/api/v1/memory/store" and method == "POST":
            return await self._memory_routes.store(kwargs.get("body"))
        elif path == "/api/v1/memory/query" and method == "POST":
            return await self._memory_routes.query(kwargs.get("body"))
        elif path == "/api/v1/memory/compact" and method == "POST":
            return await self._memory_routes.compact(kwargs.get("body"))
        elif path == "/api/v1/memory/pages" and method == "GET":
            return await self._memory_routes.list_pages()

        # ── Task routes ────────────────────────────────────────────────
        elif path == "/api/v1/tasks" and method == "POST":
            return await self._task_routes.create_task(kwargs.get("body"))
        elif path == "/api/v1/tasks" and method == "GET":
            return await self._task_routes.list_tasks()
        elif path.startswith("/api/v1/tasks/") and path.endswith("/result") and method == "GET":
            task_id = path.split("/")[-2]
            return await self._task_routes.get_task_result(task_id)
        elif path.startswith("/api/v1/tasks/") and method == "GET":
            task_id = path.split("/")[-1]
            return await self._task_routes.get_task(task_id)

        # ── Health ─────────────────────────────────────────────────────
        elif path == "/health":
            return self.get_health()

        else:
            return {"error": "Not found", "code": "NOT_FOUND", "status_code": 404}
