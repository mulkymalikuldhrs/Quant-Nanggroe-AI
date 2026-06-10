"""
Memory Store - Storage and retrieval for agent memories.

Adapted from suna's memory system for Quant-Nanggroe-AI trading platform.
Provides a flexible memory store supporting facts, preferences, context, and summaries.
"""

import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    CONVERSATION_SUMMARY = "conversation_summary"
    MARKET_INSIGHT = "market_insight"
    TRADING_DECISION = "trading_decision"


@dataclass
class MemoryEntry:
    """A single memory entry.
    
    Attributes:
        id: Unique identifier
        content: The memory content as a complete sentence
        memory_type: Type of memory
        confidence_score: How confident we are (0.0-1.0)
        metadata: Additional metadata
        created_at: Unix timestamp of creation
        updated_at: Unix timestamp of last update
        access_count: Number of times this memory has been accessed
        source: Where this memory came from (e.g., 'conversation', 'market_data')
    """
    id: str
    content: str
    memory_type: MemoryType
    confidence_score: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    source: str = "conversation"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['memory_type'] = self.memory_type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary."""
        if isinstance(data.get('memory_type'), str):
            data['memory_type'] = MemoryType(data['memory_type'])
        return cls(**data)


class MemoryStore:
    """In-memory and file-backed store for agent memories.
    
    Adapted from suna's memory system for Quant-Nanggroe-AI.
    Supports storing, retrieving, and managing memories with
    confidence scoring and type-based filtering.
    
    Usage:
        store = MemoryStore()
        entry = store.add_memory(
            content="User prefers low-risk strategies",
            memory_type=MemoryType.PREFERENCE,
            confidence_score=0.9
        )
        preferences = store.get_memories_by_type(MemoryType.PREFERENCE)
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """Initialize the memory store.
        
        Args:
            persist_path: Optional path to persist memories to disk (JSON file)
        """
        self._memories: Dict[str, MemoryEntry] = {}
        self._persist_path = persist_path
        self._type_index: Dict[MemoryType, List[str]] = {mt: [] for mt in MemoryType}
        
        if persist_path:
            self._load_from_disk()
    
    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        confidence_score: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "conversation",
        memory_id: Optional[str] = None,
    ) -> MemoryEntry:
        """Add a new memory.
        
        Args:
            content: The memory content
            memory_type: Type of memory
            confidence_score: Confidence score (0.0-1.0)
            metadata: Additional metadata
            source: Source of the memory
            memory_id: Optional custom ID (auto-generated if not provided)
            
        Returns:
            The created MemoryEntry
        """
        import uuid
        entry_id = memory_id or str(uuid.uuid4())
        
        # Check for duplicate content
        for existing in self._memories.values():
            if existing.content == content and existing.memory_type == memory_type:
                # Update confidence if higher
                if confidence_score > existing.confidence_score:
                    existing.confidence_score = confidence_score
                    existing.updated_at = time.time()
                    self._persist()
                return existing
        
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            memory_type=memory_type,
            confidence_score=confidence_score,
            metadata=metadata or {},
            source=source,
        )
        
        self._memories[entry_id] = entry
        self._type_index[memory_type].append(entry_id)
        
        logger.debug(f"Added {memory_type.value} memory: {content[:50]}...")
        self._persist()
        
        return entry
    
    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a memory by ID.
        
        Args:
            memory_id: The memory ID
            
        Returns:
            MemoryEntry or None if not found
        """
        entry = self._memories.get(memory_id)
        if entry:
            entry.access_count += 1
            entry.updated_at = time.time()
        return entry
    
    def get_memories_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """Get all memories of a specific type.
        
        Args:
            memory_type: The type to filter by
            
        Returns:
            List of MemoryEntry objects
        """
        entries = []
        for entry_id in self._type_index.get(memory_type, []):
            entry = self._memories.get(entry_id)
            if entry:
                entries.append(entry)
        return sorted(entries, key=lambda e: e.confidence_score, reverse=True)
    
    def search_memories(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Simple keyword-based search across all memories.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching MemoryEntry objects, sorted by relevance
        """
        query_lower = query.lower()
        results = []
        
        for entry in self._memories.values():
            content_lower = entry.content.lower()
            # Simple scoring: count query word occurrences
            score = 0
            for word in query_lower.split():
                if word in content_lower:
                    score += content_lower.count(word)
                    score += entry.confidence_score  # Boost by confidence
            
            if score > 0:
                results.append((score, entry))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]
    
    def get_all_memories(self) -> List[MemoryEntry]:
        """Get all stored memories.
        
        Returns:
            List of all MemoryEntry objects
        """
        return list(self._memories.values())
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID.
        
        Args:
            memory_id: The memory ID to delete
            
        Returns:
            True if the memory was deleted
        """
        entry = self._memories.pop(memory_id, None)
        if entry:
            if memory_id in self._type_index.get(entry.memory_type, []):
                self._type_index[entry.memory_type].remove(memory_id)
            self._persist()
            return True
        return False
    
    def clear_memories(self, memory_type: Optional[MemoryType] = None):
        """Clear memories, optionally filtered by type.
        
        Args:
            memory_type: If provided, only clear memories of this type
        """
        if memory_type:
            for entry_id in self._type_index.get(memory_type, []):
                self._memories.pop(entry_id, None)
            self._type_index[memory_type] = []
        else:
            self._memories.clear()
            self._type_index = {mt: [] for mt in MemoryType}
        
        self._persist()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory store.
        
        Returns:
            Dict with memory store statistics
        """
        return {
            "total_memories": len(self._memories),
            "by_type": {
                mt.value: len(ids) for mt, ids in self._type_index.items()
            },
            "avg_confidence": (
                sum(e.confidence_score for e in self._memories.values()) / len(self._memories)
                if self._memories else 0.0
            ),
        }
    
    def get_context_for_prompt(self, max_entries: int = 10) -> str:
        """Format memories as context for LLM prompts.
        
        Args:
            max_entries: Maximum number of memories to include
            
        Returns:
            Formatted string of memories for prompt injection
        """
        if not self._memories:
            return ""
        
        # Prioritize: preferences > context > facts > summaries > market insights > trading decisions
        type_priority = [
            MemoryType.PREFERENCE,
            MemoryType.CONTEXT,
            MemoryType.FACT,
            MemoryType.CONVERSATION_SUMMARY,
            MemoryType.MARKET_INSIGHT,
            MemoryType.TRADING_DECISION,
        ]
        
        entries = []
        for mt in type_priority:
            entries.extend(self.get_memories_by_type(mt))
        
        entries = entries[:max_entries]
        
        if not entries:
            return ""
        
        lines = ["## Agent Memory"]
        for entry in entries:
            lines.append(f"- [{entry.memory_type.value}] {entry.content} (confidence: {entry.confidence_score:.1f})")
        
        return "\n".join(lines)
    
    def _persist(self):
        """Persist memories to disk if a path is configured."""
        if not self._persist_path:
            return
        
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "memories": {eid: entry.to_dict() for eid, entry in self._memories.items()}
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist memories: {e}")
    
    def _load_from_disk(self):
        """Load memories from disk if a path is configured."""
        if not self._persist_path:
            return
        
        try:
            path = Path(self._persist_path)
            if not path.exists():
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for eid, entry_data in data.get("memories", {}).items():
                try:
                    entry = MemoryEntry.from_dict(entry_data)
                    self._memories[eid] = entry
                    self._type_index[entry.memory_type].append(eid)
                except Exception as e:
                    logger.warning(f"Failed to load memory {eid}: {e}")
            
            logger.info(f"Loaded {len(self._memories)} memories from {self._persist_path}")
        except Exception as e:
            logger.error(f"Failed to load memories from disk: {e}")
