"""
Context Manager - Token counting and conversation context compression.

Adapted from suna AgentPress for Quant-Nanggroe-AI trading platform.
Manages thread context including token counting and summarization to prevent
reaching context window limitations of LLM models.
"""

import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_THRESHOLD = 120000
DEFAULT_KEEP_RECENT_TOOL_OUTPUTS = 5
DEFAULT_KEEP_RECENT_USER_MESSAGES = 10
DEFAULT_KEEP_RECENT_ASSISTANT_MESSAGES = 10
DEFAULT_COMPRESSION_TARGET_RATIO = 0.6


class ContextManager:
    """Manages thread context including token counting and summarization.
    
    Adapted from suna AgentPress for Quant-Nanggroe-AI.
    Provides tool call validation, message grouping, and compression strategies
    to keep conversations within LLM context windows.
    
    Usage:
        manager = ContextManager()
        is_valid, orphans, unanswered = manager.validate_tool_call_pairing(messages)
        if not is_valid:
            messages = manager.repair_tool_call_pairing(messages)
    """
    
    def __init__(
        self,
        token_threshold: int = DEFAULT_TOKEN_THRESHOLD,
        keep_recent_tool_outputs: int = DEFAULT_KEEP_RECENT_TOOL_OUTPUTS,
        keep_recent_user_messages: int = DEFAULT_KEEP_RECENT_USER_MESSAGES,
        keep_recent_assistant_messages: int = DEFAULT_KEEP_RECENT_ASSISTANT_MESSAGES,
        compression_target_ratio: float = DEFAULT_COMPRESSION_TARGET_RATIO,
    ):
        self.token_threshold = token_threshold
        self.keep_recent_tool_outputs = keep_recent_tool_outputs
        self.keep_recent_user_messages = keep_recent_user_messages
        self.keep_recent_assistant_messages = keep_recent_assistant_messages
        self.compression_target_ratio = compression_target_ratio
    
    def is_tool_result_message(self, msg: Dict[str, Any]) -> bool:
        """Check if a message is a tool result message.
        
        Detects tool results from:
        1. Native tool calls: role="tool"
        2. Native tool calls: has tool_call_id field
        3. XML tool calls: role="user" with JSON content containing tool result structure
        """
        if not isinstance(msg, dict):
            return False
        
        if msg.get('role') == 'tool':
            return True
        
        if 'tool_call_id' in msg:
            return True
        
        if msg.get('role') == 'user':
            content = msg.get('content')
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        if 'success' in parsed or 'output' in parsed or 'error' in parsed:
                            return True
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return False
    
    def get_tool_call_ids_from_message(self, msg: Dict[str, Any]) -> List[str]:
        """Extract tool_call IDs from an assistant message with tool_calls."""
        if not isinstance(msg, dict) or msg.get('role') != 'assistant':
            return []
        
        tool_calls = msg.get('tool_calls') or []
        if not tool_calls or not isinstance(tool_calls, list):
            return []
        
        ids = []
        for tc in tool_calls:
            if isinstance(tc, dict):
                tc_id = tc.get('id')
                if tc_id:
                    ids.append(tc_id)
        return ids
    
    def get_tool_call_id_from_result(self, msg: Dict[str, Any]) -> Optional[str]:
        """Extract the tool_call_id from a tool result message."""
        if not isinstance(msg, dict):
            return None
        
        if 'tool_call_id' in msg:
            return msg.get('tool_call_id')
        
        if msg.get('role') == 'tool':
            return msg.get('tool_call_id')
        
        return None
    
    def group_messages_by_tool_calls(self, messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group messages into atomic units respecting tool call pairing.
        
        CRITICAL: Ensures assistant messages with tool_calls are always grouped
        with their corresponding tool result messages. These groups must be treated
        as atomic units that cannot be split during compression or caching.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            List of message groups, where each group is a list of messages
        """
        if not messages:
            return []
        
        groups: List[List[Dict[str, Any]]] = []
        current_group: List[Dict[str, Any]] = []
        expected_tool_call_ids: set = set()
        
        for msg in messages:
            role = msg.get('role', '')
            tool_call_ids = self.get_tool_call_ids_from_message(msg)
            
            if tool_call_ids:
                if current_group:
                    groups.append(current_group)
                current_group = [msg]
                expected_tool_call_ids = set(tool_call_ids)
                
            elif self.is_tool_result_message(msg):
                tool_call_id = self.get_tool_call_id_from_result(msg)
                
                if tool_call_id and tool_call_id in expected_tool_call_ids:
                    current_group.append(msg)
                    expected_tool_call_ids.discard(tool_call_id)
                    if not expected_tool_call_ids:
                        groups.append(current_group)
                        current_group = []
                else:
                    if current_group:
                        groups.append(current_group)
                        current_group = []
                        expected_tool_call_ids = set()
                    groups.append([msg])
            else:
                if current_group:
                    if expected_tool_call_ids:
                        logger.warning(f"Closing tool call group with {len(expected_tool_call_ids)} missing tool results")
                    groups.append(current_group)
                    current_group = []
                    expected_tool_call_ids = set()
                groups.append([msg])
        
        if current_group:
            if expected_tool_call_ids:
                logger.warning(f"Final group has {len(expected_tool_call_ids)} missing tool results")
            groups.append(current_group)
        
        return groups
    
    def flatten_message_groups(self, groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Flatten message groups back into a flat list."""
        result = []
        for group in groups:
            result.extend(group)
        return result
    
    def validate_tool_call_pairing(self, messages: List[Dict[str, Any]]) -> tuple:
        """Validate that tool calls and tool results are properly paired.
        
        Args:
            messages: List of messages to validate
            
        Returns:
            Tuple of (is_valid, orphaned_tool_result_ids, unanswered_tool_call_ids)
        """
        all_tool_call_ids: set = set()
        answered_tool_call_ids: set = set()
        orphaned_tool_result_ids: List[str] = []
        
        for msg in messages:
            tool_call_ids = self.get_tool_call_ids_from_message(msg)
            all_tool_call_ids.update(tool_call_ids)
        
        for msg in messages:
            if self.is_tool_result_message(msg):
                tool_call_id = self.get_tool_call_id_from_result(msg)
                if tool_call_id:
                    if tool_call_id not in all_tool_call_ids:
                        orphaned_tool_result_ids.append(tool_call_id)
                    else:
                        answered_tool_call_ids.add(tool_call_id)
        
        unanswered_tool_call_ids = list(all_tool_call_ids - answered_tool_call_ids)
        is_valid = len(orphaned_tool_result_ids) == 0 and len(unanswered_tool_call_ids) == 0
        
        return is_valid, orphaned_tool_result_ids, unanswered_tool_call_ids
    
    def remove_orphaned_tool_results(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove orphaned tool results that have no matching assistant message."""
        valid_tool_call_ids: set = set()
        for msg in messages:
            tool_call_ids = self.get_tool_call_ids_from_message(msg)
            valid_tool_call_ids.update(tool_call_ids)
        
        result = []
        removed_count = 0
        
        for msg in messages:
            if self.is_tool_result_message(msg):
                tool_call_id = self.get_tool_call_id_from_result(msg)
                if tool_call_id and tool_call_id not in valid_tool_call_ids:
                    logger.warning(f"Removing orphaned tool result: {tool_call_id}")
                    removed_count += 1
                    continue
            result.append(msg)
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} orphaned tool results")
        
        return result
    
    def remove_unanswered_tool_calls(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove or fix assistant messages with tool_calls that have no matching tool results."""
        answered_tool_call_ids: set = set()
        for msg in messages:
            if self.is_tool_result_message(msg):
                tool_call_id = self.get_tool_call_id_from_result(msg)
                if tool_call_id:
                    answered_tool_call_ids.add(tool_call_id)
        
        result = []
        fixed_count = 0
        removed_count = 0
        
        for msg in messages:
            tool_call_ids = self.get_tool_call_ids_from_message(msg)
            
            if tool_call_ids:
                unanswered = [tc_id for tc_id in tool_call_ids if tc_id not in answered_tool_call_ids]
                
                if unanswered:
                    answered = [tc_id for tc_id in tool_call_ids if tc_id in answered_tool_call_ids]
                    content = msg.get('content', '')
                    has_content = bool(content and str(content).strip())
                    
                    if not answered and not has_content:
                        removed_count += 1
                        continue
                    elif not answered and has_content:
                        fixed_msg = msg.copy()
                        fixed_msg.pop('tool_calls', None)
                        result.append(fixed_msg)
                        fixed_count += 1
                        continue
                    else:
                        fixed_msg = msg.copy()
                        original_tool_calls = fixed_msg.get('tool_calls') or []
                        fixed_msg['tool_calls'] = [
                            tc for tc in original_tool_calls
                            if isinstance(tc, dict) and tc.get('id') in answered_tool_call_ids
                        ] if isinstance(original_tool_calls, list) else []
                        result.append(fixed_msg)
                        fixed_count += 1
                        continue
            
            result.append(msg)
        
        if fixed_count > 0 or removed_count > 0:
            logger.info(f"Fixed {fixed_count} assistant messages, removed {removed_count}")
        
        return result
    
    def repair_tool_call_pairing(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Repair both directions of tool call pairing issues."""
        result = self.remove_orphaned_tool_results(messages)
        result = self.remove_unanswered_tool_calls(result)
        
        is_valid, orphaned, unanswered = self.validate_tool_call_pairing(result)
        if not is_valid:
            logger.error(f"Could not fully repair message structure. Orphaned: {len(orphaned)}, Unanswered: {len(unanswered)}")
        else:
            logger.info("Message structure successfully repaired")
        
        return result
    
    def compress_old_tool_outputs(
        self,
        messages: List[Dict[str, Any]],
        keep_last_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Compress old tool output messages, keeping only the most recent N uncompressed.
        
        CRITICAL: This compresses CONTENT only - it never removes messages.
        This preserves the tool_call_id field and maintains the assistant+tool_result pairing.
        
        Args:
            messages: List of conversation messages
            keep_last_n: Number of most recent tool outputs to preserve (default: self.keep_recent_tool_outputs)
            
        Returns:
            Messages with old tool outputs' content replaced by summaries
        """
        if keep_last_n is None:
            keep_last_n = self.keep_recent_tool_outputs
        
        if not messages:
            return messages
        
        # Validate and repair pairing first
        is_valid, orphaned_ids, unanswered_ids = self.validate_tool_call_pairing(messages)
        if not is_valid:
            messages = self.repair_tool_call_pairing(messages)
        
        # Identify tool result positions
        tool_result_positions = []
        for i, msg in enumerate(messages):
            if self.is_tool_result_message(msg):
                tool_result_positions.append(i)
        
        total_tool_results = len(tool_result_positions)
        if total_tool_results <= keep_last_n:
            return messages
        
        num_to_compress = total_tool_results - keep_last_n
        positions_to_compress = set(tool_result_positions[:num_to_compress])
        
        result = []
        for i, msg in enumerate(messages):
            if i in positions_to_compress:
                message_id = msg.get('message_id', 'unknown')
                summary_content = f"[Tool output compressed for token management] message_id: \"{message_id}\""
                compressed_msg = msg.copy()
                compressed_msg['content'] = summary_content
                result.append(compressed_msg)
            else:
                result.append(msg)
        
        return result
    
    def compress_user_messages(
        self,
        messages: List[Dict[str, Any]],
        keep_last_n: Optional[int] = None,
        max_length: int = 3000
    ) -> List[Dict[str, Any]]:
        """Compress user messages, keeping only the most recent N uncompressed.
        
        Args:
            messages: List of conversation messages
            keep_last_n: Number of recent user messages to preserve
            max_length: Maximum length before truncating old messages
            
        Returns:
            Messages with old user messages compressed
        """
        if keep_last_n is None:
            keep_last_n = self.keep_recent_user_messages
        
        if not messages:
            return messages
        
        user_positions = [i for i, msg in enumerate(messages) if isinstance(msg, dict) and msg.get('role') == 'user']
        total_user_messages = len(user_positions)
        
        if total_user_messages <= keep_last_n:
            return messages
        
        num_to_compress = total_user_messages - keep_last_n
        positions_to_compress = set(user_positions[:num_to_compress])
        
        result = []
        for i, msg in enumerate(messages):
            if i in positions_to_compress:
                original_content = msg.get('content', '')
                if isinstance(original_content, str) and len(original_content) > max_length:
                    summary = original_content[:max_length] + "... (truncated)"
                    compressed_msg = msg.copy()
                    compressed_msg['content'] = summary
                    result.append(compressed_msg)
                else:
                    result.append(msg)
            else:
                result.append(msg)
        
        return result
    
    def estimate_tokens(self, messages: List[Dict[str, Any]], chars_per_token: float = 4.0) -> int:
        """Estimate token count for a list of messages.
        
        Uses simple character-based estimation. For accurate counts,
        use litellm.token_counter or tiktoken directly.
        
        Args:
            messages: List of messages
            chars_per_token: Estimated characters per token
            
        Returns:
            Estimated token count
        """
        total_chars = 0
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and 'text' in block:
                        total_chars += len(block['text'])
        
        return int(total_chars / chars_per_token)
