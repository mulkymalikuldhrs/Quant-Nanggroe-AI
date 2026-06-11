"""JSON-RPC 2.0 protocol for MCP (Model Context Protocol).

Provides message types, serialization/deserialization, standard error codes,
and batch request support per the JSON-RPC 2.0 specification.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict, model_validator


# ── Standard JSON-RPC 2.0 error codes ───────────────────────────

class JSONRPCErrorCodes:
    """Standard and server-specific error codes.

    Standard codes (-32700 to -32603) are defined by the JSON-RPC 2.0 spec.
    Server-specific codes (-32001 to -32006) are defined by this MCP
    implementation.
    """
    # Standard
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Server-specific
    PERMISSION_DENIED = -32001
    RATE_LIMITED = -32002
    TOOL_UNAVAILABLE = -32003
    TIMEOUT = -32004
    SANDBOX_ERROR = -32005
    CREDENTIAL_REQUIRED = -32006

    _MESSAGES: Dict[int, str] = {
        -32700: "Parse error",
        -32600: "Invalid request",
        -32601: "Method not found",
        -32602: "Invalid params",
        -32603: "Internal error",
        -32001: "Permission denied",
        -32002: "Rate limited",
        -32003: "Tool unavailable",
        -32004: "Timeout",
        -32005: "Sandbox error",
        -32006: "Credential required",
    }

    @classmethod
    def message(cls, code: int) -> str:
        """Return the default message for a known error code."""
        return cls._MESSAGES.get(code, "Unknown error")

    @classmethod
    def is_standard(cls, code: int) -> bool:
        """Return True if the code is in the JSON-RPC 2.0 standard range."""
        return -32768 <= code <= -32000


# ── Pydantic models ──────────────────────────────────────────────

class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""
    model_config = ConfigDict(frozen=False)

    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_code(cls, code: int, message: Optional[str] = None, data: Optional[Dict] = None) -> "JSONRPCError":
        """Create an error from a known code, auto-filling the default message."""
        return cls(
            code=code,
            message=message or JSONRPCErrorCodes.message(code),
            data=data,
        )

    @classmethod
    def parse_error(cls, data: Optional[Dict] = None) -> "JSONRPCError":
        return cls.from_code(JSONRPCErrorCodes.PARSE_ERROR, data=data)

    @classmethod
    def invalid_request(cls, data: Optional[Dict] = None) -> "JSONRPCError":
        return cls.from_code(JSONRPCErrorCodes.INVALID_REQUEST, data=data)

    @classmethod
    def method_not_found(cls, method: str = "") -> "JSONRPCError":
        return cls.from_code(
            JSONRPCErrorCodes.METHOD_NOT_FOUND,
            message=f"Method not found: {method}" if method else None,
        )

    @classmethod
    def invalid_params(cls, detail: str = "") -> "JSONRPCError":
        return cls.from_code(
            JSONRPCErrorCodes.INVALID_PARAMS,
            message=f"Invalid params: {detail}" if detail else None,
        )

    @classmethod
    def internal_error(cls, detail: str = "") -> "JSONRPCError":
        return cls.from_code(
            JSONRPCErrorCodes.INTERNAL_ERROR,
            message=f"Internal error: {detail}" if detail else None,
        )

    @classmethod
    def permission_denied(cls, data: Optional[Dict] = None) -> "JSONRPCError":
        return cls.from_code(JSONRPCErrorCodes.PERMISSION_DENIED, data=data)

    @classmethod
    def rate_limited(cls, retry_after: float = 0) -> "JSONRPCError":
        return cls.from_code(
            JSONRPCErrorCodes.RATE_LIMITED,
            data={"retry_after": retry_after} if retry_after else None,
        )

    @classmethod
    def tool_unavailable(cls, tool_name: str = "") -> "JSONRPCError":
        return cls.from_code(
            JSONRPCErrorCodes.TOOL_UNAVAILABLE,
            message=f"Tool unavailable: {tool_name}" if tool_name else None,
        )

    @classmethod
    def timeout(cls, tool_name: str = "", timeout_ms: int = 0) -> "JSONRPCError":
        return cls.from_code(
            JSONRPCErrorCodes.TIMEOUT,
            message=f"Timeout: {tool_name}" if tool_name else None,
            data={"timeout_ms": timeout_ms} if timeout_ms else None,
        )

    @classmethod
    def sandbox_error(cls, detail: str = "") -> "JSONRPCError":
        return cls.from_code(
            JSONRPCErrorCodes.SANDBOX_ERROR,
            message=f"Sandbox error: {detail}" if detail else None,
        )

    @classmethod
    def credential_required(cls, data: Optional[Dict] = None) -> "JSONRPCError":
        return cls.from_code(JSONRPCErrorCodes.CREDENTIAL_REQUIRED, data=data)


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message."""
    model_config = ConfigDict(frozen=False)

    jsonrpc: str = "2.0"
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    method: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request(self) -> "JSONRPCRequest":
        if self.jsonrpc != "2.0":
            raise ValueError(f"Invalid jsonrpc version: {self.jsonrpc}")
        return self

    def serialize(self) -> bytes:
        """Serialize to JSON bytes."""
        return self.model_dump_json().encode("utf-8")


class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification (no id, no response expected)."""
    model_config = ConfigDict(frozen=False)

    jsonrpc: str = "2.0"
    method: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)

    def serialize(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response message."""
    model_config = ConfigDict(frozen=False)

    jsonrpc: str = "2.0"
    id: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_response(self) -> "JSONRPCResponse":
        # A response must have either result or error, but not both
        if self.result is not None and self.error is not None:
            raise ValueError("Response must not have both result and error")
        return self

    def is_success(self) -> bool:
        return self.error is None

    def serialize(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


# ── Batch support ────────────────────────────────────────────────

class JSONRPCBatchRequest(BaseModel):
    """A batch of JSON-RPC 2.0 requests."""
    model_config = ConfigDict(frozen=False)

    requests: List[JSONRPCRequest] = Field(default_factory=list)

    def add(self, request: JSONRPCRequest) -> None:
        self.requests.append(request)

    def serialize(self) -> bytes:
        return json.dumps([r.model_dump() for r in self.requests]).encode("utf-8")


class JSONRPCBatchResponse(BaseModel):
    """A batch of JSON-RPC 2.0 responses."""
    model_config = ConfigDict(frozen=False)

    responses: List[JSONRPCResponse] = Field(default_factory=list)

    def add(self, response: JSONRPCResponse) -> None:
        self.responses.append(response)

    def serialize(self) -> bytes:
        return json.dumps([r.model_dump() for r in self.responses]).encode("utf-8")


# ── Parsing / factory functions ──────────────────────────────────

def parse_request(data: Union[bytes, str, Dict]) -> Optional[JSONRPCRequest]:
    """Parse raw data into a JSONRPCRequest.

    Returns None if the data is malformed.
    """
    try:
        if isinstance(data, bytes):
            obj = json.loads(data.decode("utf-8"))
        elif isinstance(data, str):
            obj = json.loads(data)
        elif isinstance(data, dict):
            obj = data
        else:
            return None
        return JSONRPCRequest(**obj)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def parse_batch_request(data: Union[bytes, str]) -> Optional[JSONRPCBatchRequest]:
    """Parse raw data into a JSONRPCBatchRequest.

    Returns None if the data is malformed or not a batch.
    """
    try:
        if isinstance(data, bytes):
            obj = json.loads(data.decode("utf-8"))
        else:
            obj = json.loads(data)
        if not isinstance(obj, list):
            return None
        requests = [JSONRPCRequest(**item) for item in obj]
        return JSONRPCBatchRequest(requests=requests)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def parse_message(data: Union[bytes, str, Dict]) -> Union[JSONRPCRequest, JSONRPCNotification, JSONRPCBatchRequest, None]:
    """Auto-detect and parse a JSON-RPC message.

    Returns the appropriate message type, or None on parse failure.
    """
    try:
        if isinstance(data, bytes):
            obj = json.loads(data.decode("utf-8"))
        elif isinstance(data, str):
            obj = json.loads(data)
        elif isinstance(data, dict):
            obj = data
        else:
            return None

        # Batch
        if isinstance(obj, list):
            return parse_batch_request(json.dumps(obj))

        # Notification (no id)
        if "id" not in obj:
            return JSONRPCNotification(**obj)

        # Request
        return JSONRPCRequest(**obj)

    except (json.JSONDecodeError, ValueError, TypeError):
        return None


# ── Response factory functions ───────────────────────────────────

def make_response(
    request_id: str,
    result: Optional[Dict] = None,
    error: Optional[Dict] = None,
) -> JSONRPCResponse:
    """Create a raw JSONRPCResponse."""
    return JSONRPCResponse(id=request_id, result=result, error=error)


def make_success_response(request_id: str, data: Dict[str, Any]) -> JSONRPCResponse:
    """Create a success response with standard envelope."""
    return JSONRPCResponse(
        id=request_id,
        result={"status": "success", "data": data},
    )


def make_error_response(
    request_id: str,
    code: int,
    message: str,
    data: Optional[Dict] = None,
) -> JSONRPCResponse:
    """Create an error response."""
    error_obj: Dict[str, Any] = {"code": code, "message": message}
    if data:
        error_obj["data"] = data
    return JSONRPCResponse(id=request_id, error=error_obj)


def make_notification(method: str, params: Optional[Dict] = None) -> JSONRPCNotification:
    """Create a JSON-RPC notification."""
    return JSONRPCNotification(method=method, params=params or {})
