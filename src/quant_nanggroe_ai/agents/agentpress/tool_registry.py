"""
Tool Registry - Central registry for managing and discovering tools.

Adapted from suna AgentPress for Quant-Nanggroe-AI trading platform.
Manages tool registration, schema caching, and function lookup.
"""

from typing import Dict, Type, Any, List, Optional, Callable
import logging

from quant_nanggroe_ai.agents.agentpress.tool import Tool, SchemaType

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for managing tools and their schemas.
    
    Handles registration, caching, and lookup of tools and their
    OpenAPI schemas for LLM function calling.
    
    Usage:
        registry = ToolRegistry()
        registry.register_tool(MarketDataTool)
        schemas = registry.get_openapi_schemas()
        functions = registry.get_available_functions()
    """
    
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._cached_openapi_schemas: Optional[List[Dict[str, Any]]] = None
        self._cached_functions: Optional[Dict[str, Callable]] = None
        logger.debug("Initialized new ToolRegistry instance")
    
    def register_tool(
        self,
        tool_class: Type[Tool],
        function_names: Optional[List[str]] = None,
        **kwargs
    ):
        """Register a tool class with the registry.
        
        Args:
            tool_class: The Tool class to register
            function_names: Optional list of specific function names to register
            **kwargs: Arguments to pass to the tool class constructor
        """
        tool_instance = tool_class(**kwargs)
        schemas = tool_instance.get_schemas()
        
        # Invalidate caches on new registration
        self._cached_openapi_schemas = None
        self._cached_functions = None
        
        registered_count = 0
        for func_name, schema_list in schemas.items():
            if function_names is None or func_name in function_names:
                for schema in schema_list:
                    if schema.schema_type == SchemaType.OPENAPI:
                        self.tools[func_name] = {
                            "instance": tool_instance,
                            "schema": schema
                        }
                        registered_count += 1
        
        logger.debug(
            f"Registered {registered_count} functions from {tool_class.__name__}"
        )
    
    def get_available_functions(self) -> Dict[str, Callable]:
        """Get all available tool functions.
        
        Returns:
            Dict mapping function names to callable methods
        """
        if self._cached_functions is not None:
            return self._cached_functions
        
        available_functions = {}
        for tool_name, tool_info in self.tools.items():
            tool_instance = tool_info['instance']
            function = getattr(tool_instance, tool_name)
            available_functions[tool_name] = function
        
        self._cached_functions = available_functions
        logger.debug(f"Cached {len(available_functions)} available functions")
        return available_functions
    
    def invalidate_function_cache(self):
        """Invalidate the cached function lookup."""
        self._cached_functions = None
    
    def get_tool(self, tool_name: str) -> Dict[str, Any]:
        """Get a specific tool by name.
        
        Args:
            tool_name: Name of the tool function
            
        Returns:
            Dict with 'instance' and 'schema' keys, or empty dict if not found
        """
        tool = self.tools.get(tool_name, {})
        if not tool:
            logger.warning(f"Tool not found: {tool_name}")
        return tool
    
    def get_openapi_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAPI schemas for all registered tools.
        
        Returns schemas suitable for LLM function calling.
        
        Returns:
            List of OpenAPI schema dicts
        """
        if self._cached_openapi_schemas is not None:
            return self._cached_openapi_schemas
        
        schemas = []
        for tool_name, tool_info in self.tools.items():
            if tool_info['schema'].schema_type == SchemaType.OPENAPI:
                schemas.append(tool_info['schema'].schema)
        
        self._cached_openapi_schemas = schemas
        logger.debug(f"Generated {len(schemas)} OpenAPI schemas")
        return schemas
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all schemas including MCP tools.
        
        Returns:
            List of all OpenAPI schema dicts
        """
        return [
            tool_info['schema'].schema
            for tool_info in self.tools.values()
            if tool_info['schema'].schema_type == SchemaType.OPENAPI
        ]
    
    def invalidate_schema_cache(self):
        """Invalidate the cached schema list."""
        self._cached_openapi_schemas = None
    
    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools.
        
        Returns:
            List of tool function names
        """
        return list(self.tools.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered.
        
        Args:
            tool_name: Name of the tool function
            
        Returns:
            True if the tool is registered
        """
        return tool_name in self.tools
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Remove a tool from the registry.
        
        Args:
            tool_name: Name of the tool function to remove
            
        Returns:
            True if the tool was removed, False if not found
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            self._cached_openapi_schemas = None
            self._cached_functions = None
            logger.debug(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    def get_tool_metadata(self) -> Dict[str, Any]:
        """Get metadata summary for all registered tools.
        
        Returns:
            Dict with tool names and their metadata
        """
        result = {}
        for tool_name, tool_info in self.tools.items():
            instance = tool_info['instance']
            metadata = instance.get_metadata()
            if metadata:
                result[tool_name] = {
                    "display_name": metadata.display_name,
                    "description": metadata.description,
                    "is_core": metadata.is_core,
                    "weight": metadata.weight,
                    "visible": metadata.visible,
                }
        return result
