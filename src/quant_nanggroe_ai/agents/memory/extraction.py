"""
Memory Extraction - Extract memorable information from conversations.

Adapted from suna's memory extraction system for Quant-Nanggroe-AI trading platform.
Uses LLM prompts to analyze conversations and extract key facts, preferences,
and context that should be remembered for future interactions.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

from quant_nanggroe_ai.agents.memory.memory_store import MemoryStore, MemoryType

logger = logging.getLogger(__name__)


MEMORY_EXTRACTION_PROMPT = """You are an AI assistant for a quantitative trading platform. Your task is to analyze conversations and decide if they contain important, memorable information that will help serve the user better in future interactions.

STEP 1: EVALUATE THE CONVERSATION
First, decide if this conversation is worth extracting memories from.

DO NOT extract memories if:
- The conversation is just casual greetings or small talk with no substance
- The user is only asking generic questions with no personal information revealed
- The conversation is purely transactional with no preferences or context revealed
- There's nothing that would be useful to remember for future conversations

DO extract memories if the user reveals:
- Personal information (name, role, company, trading experience level)
- Preferences (risk tolerance, trading style, preferred markets, timeframes)
- Project context (what they're building, their strategy, goals)
- Market insights or important decisions from a meaningful conversation
- Trading rules or constraints they want to follow

STEP 2: EXTRACT MEMORIES (only if worth extracting)
If the conversation contains memorable information:
1. Extract ONLY factual information explicitly stated by the user
2. DO NOT infer, assume, or hallucinate information
3. Each memory should be a clear, standalone fact
4. Assign confidence scores (0.0-1.0) based on how explicitly stated the fact is

MEMORY TYPES:
- "fact": Personal facts (name, role, experience level, company, etc.)
- "preference": User preferences (risk tolerance, trading style, markets, timeframes, etc.)
- "context": Project or domain context (what they're working on, strategy, goals, etc.)
- "conversation_summary": Key insights or decisions from important conversations
- "market_insight": Market observations or analysis preferences
- "trading_decision": Trading rules, constraints, or decisions

CONVERSATION:
{conversation}

OUTPUT FORMAT (JSON only, no other text):
{{
  "worth_extracting": true/false,
  "reason": "Brief explanation of why this conversation is/isn't worth extracting memories from",
  "memories": [
    {{
      "content": "The actual memory fact as a complete sentence",
      "memory_type": "fact|preference|context|conversation_summary|market_insight|trading_decision",
      "confidence_score": 0.0-1.0,
      "metadata": {{"key": "value"}}
    }}
  ]
}}

If worth_extracting is false, memories should be an empty array [].

Analyze and respond:"""


@dataclass
class ExtractionResult:
    """Result of memory extraction from a conversation.
    
    Attributes:
        worth_extracting: Whether the conversation had extractable memories
        reason: Explanation of why memories were/weren't extracted
        memories: List of extracted memory dicts
    """
    worth_extracting: bool
    reason: str
    memories: List[Dict[str, Any]]


class MemoryExtractor:
    """Extract memorable information from conversations using LLM analysis.
    
    Adapted from suna's memory extraction for Quant-Nanggroe-AI.
    Uses structured prompts to analyze conversations and extract
    facts, preferences, and context that should be stored for future use.
    
    Usage:
        extractor = MemoryExtractor()
        result = await extractor.extract("User: I prefer low-risk strategies\nAgent: ...")
        for memory_data in result.memories:
            store.add_memory(
                content=memory_data["content"],
                memory_type=MemoryType(memory_data["memory_type"]),
                confidence_score=memory_data["confidence_score"],
            )
    """
    
    def __init__(self, llm_call_fn=None):
        """Initialize the memory extractor.
        
        Args:
            llm_call_fn: Async function that takes a prompt string and returns LLM response.
                         If None, extraction will use rule-based fallback.
        """
        self._llm_call_fn = llm_call_fn
    
    async def extract(self, conversation: str) -> ExtractionResult:
        """Extract memories from a conversation.
        
        Args:
            conversation: The conversation text to analyze
            
        Returns:
            ExtractionResult with extracted memories
        """
        if not conversation or len(conversation.strip()) < 50:
            return ExtractionResult(
                worth_extracting=False,
                reason="Conversation too short for memory extraction",
                memories=[]
            )
        
        if self._llm_call_fn:
            return await self._extract_with_llm(conversation)
        else:
            return self._extract_with_rules(conversation)
    
    async def _extract_with_llm(self, conversation: str) -> ExtractionResult:
        """Extract memories using LLM analysis."""
        try:
            prompt = MEMORY_EXTRACTION_PROMPT.format(conversation=conversation)
            response = await self._llm_call_fn(prompt)
            
            # Parse the JSON response
            result = self._parse_extraction_response(response)
            return result
            
        except Exception as e:
            logger.error(f"LLM memory extraction failed: {e}")
            return self._extract_with_rules(conversation)
    
    def _extract_with_rules(self, conversation: str) -> ExtractionResult:
        """Rule-based memory extraction fallback when LLM is not available."""
        memories = []
        conv_lower = conversation.lower()
        
        # Trading preferences
        preference_keywords = {
            "risk tolerance": ("low", "medium", "high"),
            "trading style": ("day trading", "swing trading", "position trading", "scalping"),
            "market": ("crypto", "forex", "stocks", "options", "futures", "commodities"),
            "timeframe": ("1m", "5m", "15m", "1h", "4h", "1d", "1w"),
        }
        
        for category, values in preference_keywords.items():
            for value in values:
                if value in conv_lower:
                    memories.append({
                        "content": f"User mentioned {category}: {value}",
                        "memory_type": "preference",
                        "confidence_score": 0.6,
                        "metadata": {"category": category, "source": "rule_extraction"}
                    })
        
        worth_extracting = len(memories) > 0
        reason = f"Rule-based extraction found {len(memories)} potential memories" if worth_extracting else "No extractable information found by rules"
        
        return ExtractionResult(
            worth_extracting=worth_extracting,
            reason=reason,
            memories=memories
        )
    
    def _parse_extraction_response(self, response: str) -> ExtractionResult:
        """Parse the LLM extraction response."""
        try:
            # Try to find JSON in the response
            json_str = response.strip()
            
            # Handle markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            
            worth_extracting = data.get("worth_extracting", False)
            reason = data.get("reason", "")
            memories = data.get("memories", [])
            
            # Validate memory types
            valid_memories = []
            for mem in memories:
                memory_type = mem.get("memory_type", "fact")
                try:
                    MemoryType(memory_type)
                    valid_memories.append(mem)
                except ValueError:
                    mem["memory_type"] = "fact"
                    valid_memories.append(mem)
            
            return ExtractionResult(
                worth_extracting=worth_extracting,
                reason=reason,
                memories=valid_memories
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            return ExtractionResult(
                worth_extracting=False,
                reason=f"Failed to parse LLM response: {str(e)}",
                memories=[]
            )
    
    async def extract_and_store(self, conversation: str, store: MemoryStore) -> int:
        """Extract memories from a conversation and store them.
        
        Args:
            conversation: The conversation text to analyze
            store: The MemoryStore to save memories to
            
        Returns:
            Number of memories stored
        """
        result = await self.extract(conversation)
        
        stored_count = 0
        for mem_data in result.memories:
            try:
                memory_type = MemoryType(mem_data.get("memory_type", "fact"))
                store.add_memory(
                    content=mem_data["content"],
                    memory_type=memory_type,
                    confidence_score=mem_data.get("confidence_score", 0.8),
                    metadata=mem_data.get("metadata", {}),
                    source="extraction",
                )
                stored_count += 1
            except Exception as e:
                logger.warning(f"Failed to store extracted memory: {e}")
        
        logger.info(f"Extracted and stored {stored_count} memories from conversation")
        return stored_count
