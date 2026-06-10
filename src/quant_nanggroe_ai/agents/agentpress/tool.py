"""
Core tool system providing the foundation for creating and managing tools.

Adapted from suna AgentPress for Quant-Nanggroe-AI trading platform.

This module defines the base classes and decorators for creating tools:
- Tool base class for implementing tool functionality
- Schema decorators for OpenAPI tool definitions
- Metadata decorators for tool and method information
- Result containers for standardized tool outputs
"""

from typing import Dict, Any, Union, Optional, List
from dataclasses import dataclass, field
from abc import ABC
import json
import inspect
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class SchemaType(Enum):
    """Enumeration of supported schema types for tool definitions."""
    OPENAPI = "openapi"


@dataclass
class ToolSchema:
    """Container for tool schemas with type information.
    
    Attributes:
        schema_type: Type of schema (OpenAPI)
        schema: The actual schema definition
    """
    schema_type: SchemaType
    schema: Dict[str, Any]


@dataclass
class ToolResult:
    """Container for tool execution results.
    
    Attributes:
        success: Whether the tool execution succeeded
        output: Output data (can be dict, list, or string)
    """
    success: bool
    output: Any

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {"success": self.success, "output": self.output}


@dataclass
class ToolMetadata:
    """Container for tool-level metadata.
    
    Attributes:
        display_name: Human-readable tool name
        description: Tool description (short, for minimal index)
        icon: Optional icon identifier for UI
        color: Optional color class for UI styling
        is_core: Whether this is a core tool (always enabled)
        weight: Sort order (lower = higher priority, default 100)
        visible: Whether tool is visible in frontend UI (default False)
        usage_guide: Detailed usage instructions loaded on-demand
    """
    display_name: str
    description: str
    icon: Optional[str] = None
    color: Optional[str] = None
    is_core: bool = False
    weight: int = 100
    visible: bool = False
    usage_guide: Optional[str] = None


@dataclass
class MethodMetadata:
    """Container for method-level metadata.
    
    Attributes:
        display_name: Human-readable method name
        description: Method description
        is_core: Whether this is a core method (always enabled)
        visible: Whether method is visible in frontend UI (default True)
    """
    display_name: str
    description: str
    is_core: bool = False
    visible: bool = True


class Tool(ABC):
    """Abstract base class for all tools.
    
    Provides the foundation for implementing tools with schema registration
    and result handling capabilities. Adapted from suna AgentPress for
    the Quant-Nanggroe-AI trading platform.
    
    Usage:
        @tool_metadata(display_name="Market Data", description="Fetch market data")
        class MarketDataTool(Tool):
            @openapi_schema({...})
            @method_metadata(display_name="Get Price", description="Get current price")
            def get_price(self, symbol: str) -> ToolResult:
                # implementation
                return self.success_response({"price": 100.0})
    
    Attributes:
        _schemas: Registered schemas for tool methods
        _metadata: Tool-level metadata
        _method_metadata: Method-level metadata
    """
    
    def __init__(self):
        """Initialize tool with empty schema registry."""
        self._schemas: Dict[str, List[ToolSchema]] = {}
        self._metadata: Optional[ToolMetadata] = None
        self._method_metadata: Dict[str, MethodMetadata] = {}
        self._register_metadata()
        self._register_schemas()

    def _register_metadata(self):
        """Register metadata from class and method decorators."""
        if hasattr(self.__class__, '__tool_metadata__'):
            self._metadata = self.__class__.__tool_metadata__
        
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, '__method_metadata__'):
                self._method_metadata[name] = method.__method_metadata__

    def _register_schemas(self):
        """Register schemas from all decorated methods."""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, 'tool_schemas'):
                self._schemas[name] = method.tool_schemas

    def get_schemas(self) -> Dict[str, List[ToolSchema]]:
        """Get all registered tool schemas.
        
        Returns:
            Dict mapping method names to their schema definitions
        """
        return self._schemas

    def get_metadata(self) -> Optional[ToolMetadata]:
        """Get tool-level metadata.
        
        Returns:
            ToolMetadata object or None if not set
        """
        return self._metadata

    def get_method_metadata(self) -> Dict[str, MethodMetadata]:
        """Get metadata for all methods.
        
        Returns:
            Dict mapping method names to their metadata
        """
        return self._method_metadata

    def success_response(self, data: Union[Dict[str, Any], str, list]) -> ToolResult:
        """Create a successful tool result.
        
        Args:
            data: Result data (dictionary, list, or string)
            
        Returns:
            ToolResult with success=True and data as JSON string (if dict/list) or plain string
        """
        if isinstance(data, (dict, list)):
            output = json.dumps(data)
        else:
            output = str(data)
        return ToolResult(success=True, output=output)

    def fail_response(self, msg: str) -> ToolResult:
        """Create a failed tool result.
        
        Args:
            msg: Error message describing the failure
            
        Returns:
            ToolResult with success=False and error message
        """
        logger.debug(f"Tool {self.__class__.__name__} returned failed result: {msg}")
        return ToolResult(success=False, output=msg)


def _add_schema(func, schema: ToolSchema):
    """Helper to add schema to a function."""
    if not hasattr(func, 'tool_schemas'):
        func.tool_schemas = []
    func.tool_schemas.append(schema)
    return func


def openapi_schema(schema: Dict[str, Any]):
    """Decorator for OpenAPI schema tools.
    
    Args:
        schema: OpenAPI-compatible function schema definition
        
    Usage:
        @openapi_schema({
            "type": "function",
            "function": {
                "name": "get_price",
                "description": "Get current price for a symbol",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Trading symbol"}
                    },
                    "required": ["symbol"]
                }
            }
        })
        def get_price(self, symbol: str):
            ...
    """
    def decorator(func):
        return _add_schema(func, ToolSchema(
            schema_type=SchemaType.OPENAPI,
            schema=schema
        ))
    return decorator


def tool_metadata(
    display_name: str,
    description: str,
    icon: Optional[str] = None,
    color: Optional[str] = None,
    is_core: bool = False,
    weight: int = 100,
    visible: bool = False,
    usage_guide: Optional[str] = None
):
    """Decorator to add metadata to a Tool class.
    
    Args:
        display_name: Human-readable tool name
        description: Tool description (short, shown in minimal index)
        icon: Icon identifier for UI (optional)
        color: Color class for UI styling (optional)
        is_core: Whether this is a core tool that's always enabled
        weight: Sort order (lower = higher priority, default 100)
        visible: Whether tool is visible in frontend UI (default True)
        usage_guide: Detailed usage instructions loaded on-demand by the agent
    
    Usage:
        @tool_metadata(
            display_name="Market Data",
            description="Fetch market data and prices",
            icon="TrendingUp",
            weight=10,
            visible=True,
        )
        class MarketDataTool(Tool):
            ...
    """
    def decorator(cls):
        cls.__tool_metadata__ = ToolMetadata(
            display_name=display_name,
            description=description,
            icon=icon,
            color=color,
            is_core=is_core,
            weight=weight,
            visible=visible,
            usage_guide=usage_guide
        )
        return cls
    return decorator


def method_metadata(
    display_name: str,
    description: str,
    is_core: bool = False,
    visible: bool = True
):
    """Decorator to add metadata to a tool method.
    
    Args:
        display_name: Human-readable method name
        description: Method description
        is_core: Whether this is a core method that's always enabled
        visible: Whether method is visible in frontend UI (default True)
    
    Usage:
        @method_metadata(display_name="Get Price", description="Get current price")
        @openapi_schema({...})
        def get_price(self, symbol: str):
            ...
    """
    def decorator(func):
        func.__method_metadata__ = MethodMetadata(
            display_name=display_name,
            description=description,
            is_core=is_core,
            visible=visible
        )
        return func
    return decorator
