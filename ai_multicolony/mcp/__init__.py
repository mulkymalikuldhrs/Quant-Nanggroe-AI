"""MCP Server/Client for AI-MultiColony."""

from .protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCBatchRequest,
    JSONRPCBatchResponse,
    JSONRPCError,
    JSONRPCErrorCodes,
    parse_request,
    parse_batch_request,
    parse_message,
    make_success_response,
    make_error_response,
    make_response,
    make_notification,
)
from .server import MCPServer, RateLimiter, CircuitBreaker
from .client import MCPClient
from .permissions import PermissionEngine

__all__ = [
    # Protocol
    "JSONRPCRequest", "JSONRPCResponse", "JSONRPCNotification",
    "JSONRPCBatchRequest", "JSONRPCBatchResponse",
    "JSONRPCError", "JSONRPCErrorCodes",
    "parse_request", "parse_batch_request", "parse_message",
    "make_success_response", "make_error_response", "make_response",
    "make_notification",
    # Server
    "MCPServer", "RateLimiter", "CircuitBreaker",
    # Client
    "MCPClient",
    # Permissions
    "PermissionEngine",
]
