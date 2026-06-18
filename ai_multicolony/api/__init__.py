"""FastAPI API layer for AI-MultiColony.

Provides the FastAPI application, middleware, Pydantic schemas,
route handlers, and WebSocket support.
"""

from .app import FastAPIApp, create_app, lifespan
from .schemas import (
    # Agent schemas
    AgentCreateRequest,
    AgentCreateResponse,
    AgentStatusResponse,
    AgentListResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentDeleteResponse,
    # Colony schemas
    ColonyCreateRequest,
    ColonyCreateResponse,
    ColonyStatusResponse,
    ColonyListResponse,
    ColonyScaleRequest,
    ColonyScaleResponse,
    # Tool schemas
    ToolListResponse,
    ToolDescribeResponse,
    ToolCallRequest,
    ToolCallResponse,
    # Memory schemas
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryCompactRequest,
    MemoryCompactResponse,
    MemoryPagesResponse,
    # Task schemas
    TaskCreateRequest,
    TaskCreateResponse,
    TaskStatusResponse,
    TaskResultResponse,
    # Health/Error schemas
    HealthResponse,
    ErrorResponse,
    # WebSocket schemas
    WSMessage,
    WSTaskUpdate,
    WSHeartbeat,
    WSAlert,
    WSLog,
)
from .middleware import (
    AuthMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
)
from .routes import (
    AgentRoutes,
    ColonyRoutes,
    ToolRoutes,
    MemoryRoutes,
    TaskRoutes,
    WebSocketHandler,
)

__all__ = [
    # App
    "FastAPIApp",
    "create_app",
    "lifespan",
    # Agent schemas
    "AgentCreateRequest",
    "AgentCreateResponse",
    "AgentStatusResponse",
    "AgentListResponse",
    "AgentExecuteRequest",
    "AgentExecuteResponse",
    "AgentDeleteResponse",
    # Colony schemas
    "ColonyCreateRequest",
    "ColonyCreateResponse",
    "ColonyStatusResponse",
    "ColonyListResponse",
    "ColonyScaleRequest",
    "ColonyScaleResponse",
    # Tool schemas
    "ToolListResponse",
    "ToolDescribeResponse",
    "ToolCallRequest",
    "ToolCallResponse",
    # Memory schemas
    "MemoryStoreRequest",
    "MemoryStoreResponse",
    "MemoryQueryRequest",
    "MemoryQueryResponse",
    "MemoryCompactRequest",
    "MemoryCompactResponse",
    "MemoryPagesResponse",
    # Task schemas
    "TaskCreateRequest",
    "TaskCreateResponse",
    "TaskStatusResponse",
    "TaskResultResponse",
    # Health/Error schemas
    "HealthResponse",
    "ErrorResponse",
    # WebSocket schemas
    "WSMessage",
    "WSTaskUpdate",
    "WSHeartbeat",
    "WSAlert",
    "WSLog",
    # Middleware
    "AuthMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "ErrorHandlingMiddleware",
    # Routes
    "AgentRoutes",
    "ColonyRoutes",
    "ToolRoutes",
    "MemoryRoutes",
    "TaskRoutes",
    "WebSocketHandler",
]
