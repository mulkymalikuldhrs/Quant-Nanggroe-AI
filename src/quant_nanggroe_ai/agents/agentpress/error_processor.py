"""
Error Processor - Standardized error handling for tool execution.

Adapted from suna AgentPress for Quant-Nanggroe-AI trading platform.
"""

import traceback
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ErrorProcessor:
    """Process and format errors from tool execution.
    
    Provides standardized error handling, categorization, and formatting
    for errors that occur during tool execution in the agent framework.
    
    Usage:
        processor = ErrorProcessor()
        result = processor.process_error(
            error=ValueError("Invalid symbol"),
            tool_name="get_price",
            tool_call_id="call_123"
        )
    """
    
    # Error categories for classification
    CATEGORY_VALIDATION = "validation"
    CATEGORY_NETWORK = "network"
    CATEGORY_TIMEOUT = "timeout"
    CATEGORY_AUTH = "authentication"
    CATEGORY_RATE_LIMIT = "rate_limit"
    CATEGORY_INTERNAL = "internal"
    CATEGORY_UNKNOWN = "unknown"
    
    # Map exception types to categories
    ERROR_TYPE_MAP = {
        ValueError: CATEGORY_VALIDATION,
        TypeError: CATEGORY_VALIDATION,
        KeyError: CATEGORY_VALIDATION,
        ConnectionError: CATEGORY_NETWORK,
        ConnectionRefusedError: CATEGORY_NETWORK,
        ConnectionResetError: CATEGORY_NETWORK,
        TimeoutError: CATEGORY_TIMEOUT,
        PermissionError: CATEGORY_AUTH,
    }
    
    def classify_error(self, error: Exception) -> str:
        """Classify an error into a category.
        
        Args:
            error: The exception to classify
            
        Returns:
            Error category string
        """
        for error_type, category in self.ERROR_TYPE_MAP.items():
            if isinstance(error, error_type):
                return category
        
        # Check error message for common patterns
        msg = str(error).lower()
        if any(kw in msg for kw in ['rate limit', 'too many requests', '429']):
            return self.CATEGORY_RATE_LIMIT
        if any(kw in msg for kw in ['unauthorized', 'forbidden', '401', '403']):
            return self.CATEGORY_AUTH
        if any(kw in msg for kw in ['timeout', 'timed out']):
            return self.CATEGORY_TIMEOUT
        if any(kw in msg for kw in ['connection', 'network', 'dns']):
            return self.CATEGORY_NETWORK
        
        return self.CATEGORY_UNKNOWN
    
    def process_error(
        self,
        error: Exception,
        tool_name: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        include_traceback: bool = False
    ) -> Dict[str, Any]:
        """Process and format an error from tool execution.
        
        Args:
            error: The exception that occurred
            tool_name: Name of the tool that failed
            tool_call_id: ID of the tool call that failed
            include_traceback: Whether to include traceback in output
            
        Returns:
            Dict with error details
        """
        category = self.classify_error(error)
        
        result = {
            "success": False,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "category": category,
            },
            "output": f"Error in {tool_name or 'unknown tool'}: {str(error)}"
        }
        
        if tool_name:
            result["error"]["tool_name"] = tool_name
        if tool_call_id:
            result["error"]["tool_call_id"] = tool_call_id
        if include_traceback:
            result["error"]["traceback"] = traceback.format_exc()
        
        # Log based on category severity
        if category in [self.CATEGORY_INTERNAL, self.CATEGORY_UNKNOWN]:
            logger.error(f"Tool execution error [{category}]: {tool_name} - {error}")
        elif category in [self.CATEGORY_NETWORK, self.CATEGORY_TIMEOUT]:
            logger.warning(f"Tool execution error [{category}]: {tool_name} - {error}")
        else:
            logger.info(f"Tool execution error [{category}]: {tool_name} - {error}")
        
        return result
    
    def format_user_facing_error(self, error_result: Dict[str, Any]) -> str:
        """Format an error result for display to users.
        
        Args:
            error_result: Error result dict from process_error
            
        Returns:
            Human-readable error string
        """
        error_info = error_result.get("error", {})
        category = error_info.get("category", "unknown")
        message = error_info.get("message", "Unknown error")
        tool_name = error_info.get("tool_name", "tool")
        
        category_messages = {
            self.CATEGORY_VALIDATION: f"Invalid input for {tool_name}: {message}",
            self.CATEGORY_NETWORK: f"Network error connecting to {tool_name}. Please try again.",
            self.CATEGORY_TIMEOUT: f"{tool_name} timed out. The service may be slow or unavailable.",
            self.CATEGORY_AUTH: f"Authentication failed for {tool_name}. Check your credentials.",
            self.CATEGORY_RATE_LIMIT: f"Rate limit exceeded for {tool_name}. Please wait and try again.",
            self.CATEGORY_INTERNAL: f"Internal error in {tool_name}. Please report this issue.",
            self.CATEGORY_UNKNOWN: f"Error in {tool_name}: {message}",
        }
        
        return category_messages.get(category, f"Error in {tool_name}: {message}")
