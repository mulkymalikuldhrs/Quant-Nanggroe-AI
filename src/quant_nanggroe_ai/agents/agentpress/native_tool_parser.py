"""
Native Tool Call Parser Module

Adapted from suna AgentPress for Quant-Nanggroe-AI trading platform.
Provides utilities for parsing OpenAI-style native tool calls from LLM responses.
"""

import json
import uuid
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def extract_tool_call_chunk_data(tool_call_chunk: Any) -> Dict[str, Any]:
    """Extract tool call chunk data from a LiteLLM tool_call_chunk object.
    
    Args:
        tool_call_chunk: LiteLLM tool_call_chunk object (may have model_dump or manual attributes)
        
    Returns:
        Dictionary with 'id', 'index', 'type', 'function' keys
    """
    tool_call_data_chunk = {}
    
    if hasattr(tool_call_chunk, 'model_dump'):
        tool_call_data_chunk = tool_call_chunk.model_dump()
    else:
        # Manual extraction for compatibility
        if hasattr(tool_call_chunk, 'id'):
            tool_call_data_chunk['id'] = tool_call_chunk.id
        if hasattr(tool_call_chunk, 'index'):
            tool_call_data_chunk['index'] = tool_call_chunk.index
        if hasattr(tool_call_chunk, 'type'):
            tool_call_data_chunk['type'] = tool_call_chunk.type
        if hasattr(tool_call_chunk, 'function'):
            tool_call_data_chunk['function'] = {}
            if hasattr(tool_call_chunk.function, 'name'):
                tool_call_data_chunk['function']['name'] = tool_call_chunk.function.name
            if hasattr(tool_call_chunk.function, 'arguments'):
                args = tool_call_chunk.function.arguments
                if isinstance(args, str):
                    tool_call_data_chunk['function']['arguments'] = args
                else:
                    tool_call_data_chunk['function']['arguments'] = json.dumps(args)
    
    return tool_call_data_chunk


def is_tool_call_complete(tool_call_buffer_entry: Dict[str, Any]) -> bool:
    """Check if a buffered tool call is complete (has all required fields and valid JSON arguments).
    
    Args:
        tool_call_buffer_entry: Dictionary from tool_calls_buffer with 'id', 'function' keys
        
    Returns:
        True if tool call is complete and ready to execute
    """
    if not tool_call_buffer_entry:
        return False
    
    if not (tool_call_buffer_entry.get('id') and
            tool_call_buffer_entry.get('function', {}).get('name') and
            tool_call_buffer_entry.get('function', {}).get('arguments')):
        return False
    
    try:
        parsed = safe_json_parse(tool_call_buffer_entry['function']['arguments'])
        return isinstance(parsed, dict)
    except (json.JSONDecodeError, TypeError):
        return False


def _normalize_json_string_values(value: Any) -> Any:
    """Recursively normalize JSON string values within a data structure.
    
    LLMs often pass arrays/objects as JSON strings instead of native types.
    For example: {"query": "[\"a\", \"b\"]"} instead of {"query": ["a", "b"]}
    
    Args:
        value: Any value to normalize
        
    Returns:
        Normalized value with JSON strings parsed into native types
    """
    if isinstance(value, dict):
        return {k: _normalize_json_string_values(v) for k, v in value.items()}
    
    if isinstance(value, list):
        return [_normalize_json_string_values(item) for item in value]
    
    if isinstance(value, str):
        stripped = value.strip()
        if (stripped.startswith('[') and stripped.endswith(']')) or \
           (stripped.startswith('{') and stripped.endswith('}')):
            try:
                parsed = json.loads(stripped)
                return _normalize_json_string_values(parsed)
            except (json.JSONDecodeError, ValueError):
                pass
    
    return value


def safe_json_parse(text: str) -> Any:
    """Safely parse JSON with fallback for common LLM output issues.
    
    Args:
        text: JSON string to parse
        
    Returns:
        Parsed JSON object
    """
    if not text:
        return {}
    
    text = text.strip()
    
    # Direct parse attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try fixing common issues: trailing commas, single quotes
    try:
        # Replace single quotes with double quotes
        fixed = text.replace("'", '"')
        # Remove trailing commas before closing brackets
        fixed = fixed.replace(',}', '}').replace(',]', ']')
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # Return original text if all parsing fails
    return text


def parse_native_tool_call_arguments(arguments: Any) -> Dict[str, Any]:
    """Parse native tool call arguments, handling both string and dict formats.
    Also normalizes nested JSON strings (e.g. arrays passed as strings).
    
    Args:
        arguments: Arguments as string (JSON) or dict
        
    Returns:
        Parsed arguments as dict, or original value if parsing fails
    """
    if isinstance(arguments, dict):
        return _normalize_json_string_values(arguments)
    
    if isinstance(arguments, str):
        parsed = safe_json_parse(arguments)
        if isinstance(parsed, dict):
            return _normalize_json_string_values(parsed)
        try:
            result = json.loads(arguments)
            if isinstance(result, dict):
                return _normalize_json_string_values(result)
            return result
        except (json.JSONDecodeError, ValueError):
            return arguments
    
    return arguments


def convert_to_exec_tool_call(
    tool_call: Any,
    raw_arguments_str: Optional[str] = None
) -> Dict[str, Any]:
    """Convert a native tool call object to exec_tool_call format.
    
    Args:
        tool_call: Native tool call object (from LiteLLM response) or dict
        raw_arguments_str: Optional raw arguments string (if already extracted)
        
    Returns:
        Dictionary with 'function_name', 'arguments', 'id', 'raw_arguments', 'source'
    """
    if isinstance(tool_call, dict):
        function_name = tool_call.get('function', {}).get('name') or tool_call.get('function_name', 'unknown')
        tool_call_id = tool_call.get('id') or str(uuid.uuid4())
        if raw_arguments_str is None:
            raw_arguments_str = tool_call.get('function', {}).get('arguments') or tool_call.get('raw_arguments', '')
    else:
        function_name = tool_call.function.name if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'name') else 'unknown'
        tool_call_id = tool_call.id if hasattr(tool_call, 'id') else str(uuid.uuid4())
        if raw_arguments_str is None:
            if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                args = tool_call.function.arguments
                raw_arguments_str = args if isinstance(args, str) else json.dumps(args)
            else:
                raw_arguments_str = ''
    
    parsed_args = parse_native_tool_call_arguments(raw_arguments_str)
    
    return {
        "function_name": function_name,
        "arguments": parsed_args if isinstance(parsed_args, dict) else raw_arguments_str,
        "id": tool_call_id,
        "raw_arguments": raw_arguments_str if isinstance(raw_arguments_str, str) else json.dumps(raw_arguments_str),
        "source": "native"
    }


def convert_buffer_to_complete_tool_calls(tool_calls_buffer: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert buffered tool calls to complete format.
    
    Args:
        tool_calls_buffer: Dictionary mapping index -> buffered tool call data
        
    Returns:
        List of complete tool calls in OpenAI format
    """
    complete_tool_calls = []
    
    for idx, tc_buf in tool_calls_buffer.items():
        if tc_buf.get('id') and tc_buf.get('function', {}).get('name') and tc_buf.get('function', {}).get('arguments'):
            arguments_str = tc_buf['function']['arguments']
            try:
                parsed = json.loads(arguments_str)
                if not isinstance(parsed, dict):
                    logger.warning(f"Tool call {tc_buf.get('id')} has non-dict arguments, skipping")
                    continue
                complete_tool_calls.append({
                    "id": tc_buf['id'],
                    "type": "function",
                    "function": {
                        "name": tc_buf['function']['name'],
                        "arguments": arguments_str
                    }
                })
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Tool call {tc_buf.get('id')} has invalid JSON arguments, skipping: {str(e)[:100]}")
                continue
    
    return complete_tool_calls


def convert_to_unified_tool_call_format(
    tool_call: Dict[str, Any],
    parse_arguments: bool = True
) -> Dict[str, Any]:
    """Convert tool call to unified format.
    
    Args:
        tool_call: Tool call dictionary
        parse_arguments: Whether to parse arguments from JSON string
        
    Returns:
        Unified tool call dict
    """
    function_name = tool_call.get('function', {}).get('name', 'unknown')
    tool_call_id = tool_call.get('id', str(uuid.uuid4()))
    raw_arguments = tool_call.get('function', {}).get('arguments', '')
    
    if parse_arguments:
        arguments = parse_native_tool_call_arguments(raw_arguments)
    else:
        arguments = raw_arguments
    
    return {
        "tool_call_id": tool_call_id,
        "function_name": function_name,
        "arguments": arguments if isinstance(arguments, dict) else raw_arguments,
        "source": "native"
    }


def convert_buffer_to_metadata_tool_calls(
    tool_calls_buffer: Dict[int, Dict[str, Any]],
    include_partial: bool = False,
    delta_mode: bool = False,
    sent_lengths: Optional[Dict[int, int]] = None
) -> List[Dict[str, Any]]:
    """Convert buffered tool calls to unified metadata format for streaming chunks.
    
    Args:
        tool_calls_buffer: Dictionary mapping index -> buffered tool call data
        include_partial: Whether to include partial/incomplete tool calls
        delta_mode: If True, only send new data (delta) not full accumulated content
        sent_lengths: Dictionary tracking how much has been sent for each index
        
    Returns:
        List of tool calls in unified metadata format
    """
    unified_tool_calls = []
    for idx in sorted(tool_calls_buffer.keys()):
        tc_buf = tool_calls_buffer[idx]
        if tc_buf.get('function', {}).get('name'):
            arguments_str = tc_buf['function'].get('arguments', '')
            
            if delta_mode and sent_lengths is not None:
                prev_length = sent_lengths.get(idx, 0)
                current_length = len(arguments_str)
                
                if current_length <= prev_length:
                    continue
                
                arguments_delta = arguments_str[prev_length:]
                sent_lengths[idx] = current_length
                
                unified_tool_calls.append({
                    "tool_call_id": tc_buf.get('id', f"streaming_tool_{idx}_{str(uuid.uuid4())}"),
                    "function_name": tc_buf['function']['name'],
                    "arguments_delta": arguments_delta,
                    "is_delta": True,
                    "source": "native"
                })
            else:
                arguments: Any = arguments_str
                if arguments_str:
                    try:
                        parsed = json.loads(arguments_str)
                        arguments = parsed
                    except json.JSONDecodeError:
                        arguments = arguments_str
                
                unified_tool_calls.append({
                    "tool_call_id": tc_buf.get('id', f"streaming_tool_{idx}_{str(uuid.uuid4())}"),
                    "function_name": tc_buf['function']['name'],
                    "arguments": arguments,
                    "source": "native"
                })
    return unified_tool_calls
