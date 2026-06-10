"""
⚡ QUANTA AI - Memory Management System
========================================
Advanced memory system inspired by OpenHands with
multiple memory layers for autonomous operation.

Memory Types:
- SHORT_TERM: Conversation context, current task
- LONG_TERM: Learned patterns, strategy performance
- WORKING: Active analysis, calculations
- EPISODIC: Completed tasks, trade history
- SEMANTIC: Knowledge base, facts

Author: Quanta AI Team
Version: 3.0.0
"""

import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import logging


class MemoryType(Enum):
    """Types of memory in the system."""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryPriority(Enum):
    """Memory priority levels."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class MemoryItem:
    """A single memory item."""
    memory_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    priority: MemoryPriority = MemoryPriority.MEDIUM
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    importance_score: float = 0.5
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'memory_id': self.memory_id,
            'memory_type': self.memory_type.value,
            'content': self.content,
            'priority': self.priority.value,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count,
            'importance_score': self.importance_score,
            'tags': self.tags,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        return cls(
            memory_id=data['memory_id'],
            memory_type=MemoryType(data['memory_type']),
            content=data['content'],
            priority=MemoryPriority(data['priority']),
            created_at=data.get('created_at', time.time()),
            last_accessed=data.get('last_accessed', time.time()),
            access_count=data.get('access_count', 0),
            importance_score=data.get('importance_score', 0.5),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {})
        )
    
    def get_hash(self) -> str:
        """Generate hash for deduplication."""
        content_str = json.dumps(self.content, sort_keys=True)
        return hashlib.md5(f"{self.memory_type.value}:{content_str}".encode()).hexdigest()[:16]


@dataclass
class ConversationContext:
    """Context for a conversation session."""
    session_id: str
    user_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    current_task: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    state: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': time.time()
        })
        self.last_activity = time.time()
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.messages[-limit:]
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable."""
        self.variables[key] = value
        self.last_activity = time.time()
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable."""
        return self.variables.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'messages': self.messages,
            'current_task': self.current_task,
            'variables': self.variables,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'state': self.state
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        return cls(
            session_id=data['session_id'],
            user_id=data.get('user_id'),
            messages=data.get('messages', []),
            current_task=data.get('current_task'),
            variables=data.get('variables', {}),
            created_at=data.get('created_at', time.time()),
            last_activity=data.get('last_activity', time.time()),
            state=data.get('state', {})
        )


@dataclass
class KnowledgeFact:
    """A semantic knowledge fact."""
    fact_id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = "inferred"
    created_at: float = field(default_factory=time.time)
    verified: bool = False
    uses: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'fact_id': self.fact_id,
            'subject': self.subject,
            'predicate': self.predicate,
            'object': self.object,
            'confidence': self.confidence,
            'source': self.source,
            'created_at': self.created_at,
            'verified': self.verified,
            'uses': self.uses
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeFact':
        return cls(
            fact_id=data['fact_id'],
            subject=data['subject'],
            predicate=data['predicate'],
            object=data['object'],
            confidence=data.get('confidence', 1.0),
            source=data.get('source', 'inferred'),
            created_at=data.get('created_at', time.time()),
            verified=data.get('verified', False),
            uses=data.get('uses', 0)
        )


class MemoryManager:
    """
    Central memory management system.
    
    Provides:
    - Multi-type memory storage
    - Automatic memory consolidation
    - Importance-based retrieval
    - Context-aware recall
    - Session management
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("Quanta.Memory")
        
        # Memory storage
        self.memories: Dict[MemoryType, List[MemoryItem]] = defaultdict(list)
        self.conversations: Dict[str, ConversationContext] = {}
        self.knowledge_graph: Dict[str, KnowledgeFact] = {}
        
        # Indexes for fast retrieval
        self.tag_index: Dict[str, List[str]] = defaultdict(list)  # tag -> memory_ids
        self.type_index: Dict[MemoryType, List[str]] = defaultdict(list)
        self.vector_index: Dict[str, List[str]] = defaultdict(list)  # placeholder for embeddings
        
        # Configuration
        self.short_term_limit = self.config.get('short_term_limit', 100)
        self.long_term_limit = self.config.get('long_term_limit', 1000)
        self.working_limit = self.config.get('working_limit', 50)
        self.consolidation_interval = self.config.get('consolidation_interval', 3600)  # 1 hour
        self.importance_threshold = self.config.get('importance_threshold', 0.5)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Auto-consolidation
        self._last_consolidation = time.time()
        
        # Load existing memories
        self._load_memories()
        
        self.logger.info("Memory Manager initialized")
    
    # ==================== MEMORY OPERATIONS ====================
    
    def remember(self, memory_type: MemoryType, content: Dict[str, Any],
                priority: MemoryPriority = MemoryPriority.MEDIUM,
                tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Store a new memory."""
        memory_id = self._generate_id()
        
        # Calculate importance
        importance = self._calculate_importance(content, priority)
        
        memory = MemoryItem(
            memory_id=memory_id,
            memory_type=memory_type,
            content=content,
            priority=priority,
            importance_score=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        with self._lock:
            self.memories[memory_type].append(memory)
            self._index_memory(memory)
        
        self.logger.debug(f"Remembered: {memory_type.value} ({memory_id})")
        return memory_id
    
    def recall(self, memory_type: MemoryType = None, 
              query: str = None, tags: List[str] = None,
              limit: int = 10, min_importance: float = 0.0) -> List[MemoryItem]:
        """Recall memories based on criteria."""
        with self._lock:
            candidates = []
            
            # Get from specific type or all types
            if memory_type:
                candidates = list(self.memories[memory_type])
            else:
                for memories in self.memories.values():
                    candidates.extend(memories)
            
            # Filter by tags
            if tags:
                candidates = [m for m in candidates if any(t in m.tags for t in tags)]
            
            # Filter by importance
            candidates = [m for m in candidates if m.importance_score >= min_importance]
            
            # Sort by importance and recency
            candidates.sort(key=lambda m: (m.importance_score, m.last_accessed), reverse=True)
            
            # Update access counts
            for memory in candidates[:limit]:
                memory.last_accessed = time.time()
                memory.access_count += 1
            
            return candidates[:limit]
    
    def forget(self, memory_id: str) -> bool:
        """Remove a specific memory."""
        with self._lock:
            for memory_type, memories in self.memories.items():
                for i, memory in enumerate(memories):
                    if memory.memory_id == memory_id:
                        del memories[i]
                        self._remove_from_index(memory)
                        return True
        return False
    
    def update_memory(self, memory_id: str, content: Dict[str, Any]) -> bool:
        """Update an existing memory."""
        with self._lock:
            for memories in self.memories.values():
                for memory in memories:
                    if memory.memory_id == memory_id:
                        memory.content.update(content)
                        memory.importance_score = self._calculate_importance(
                            memory.content, memory.priority
                        )
                        memory.last_accessed = time.time()
                        return True
        return False
    
    # ==================== CONVERSATION MANAGEMENT ====================
    
    def start_conversation(self, session_id: str, user_id: str = None) -> ConversationContext:
        """Start a new conversation session."""
        with self._lock:
            ctx = ConversationContext(
                session_id=session_id,
                user_id=user_id
            )
            self.conversations[session_id] = ctx
            return ctx
    
    def get_conversation(self, session_id: str) -> Optional[ConversationContext]:
        """Get a conversation context."""
        return self.conversations.get(session_id)
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Add a message to a conversation."""
        ctx = self.get_conversation(session_id)
        if ctx:
            ctx.add_message(role, content)
            
            # Remember important messages in long-term memory
            if role == 'assistant':
                self.remember(
                    MemoryType.EPISODIC,
                    {
                        'session_id': session_id,
                        'type': 'conversation_message',
                        'content': content,
                        'role': role
                    },
                    priority=MemoryPriority.LOW,
                    tags=['conversation', session_id]
                )
            return True
        return False
    
    def end_conversation(self, session_id: str) -> Optional[ConversationContext]:
        """End a conversation and consolidate."""
        ctx = self.conversations.pop(session_id, None)
        if ctx:
            # Remember key points in long-term memory
            self.remember(
                MemoryType.EPISODIC,
                {
                    'type': 'conversation_summary',
                    'session_id': session_id,
                    'message_count': len(ctx.messages),
                    'duration': time.time() - ctx.created_at
                },
                tags=['conversation', session_id]
            )
        return ctx
    
    # ==================== KNOWLEDGE MANAGEMENT ====================
    
    def learn_fact(self, subject: str, predicate: str, object: str,
                  confidence: float = 1.0, source: str = "inferred") -> str:
        """Learn a new fact for semantic memory."""
        fact_id = self._generate_id()
        
        fact = KnowledgeFact(
            fact_id=fact_id,
            subject=subject,
            predicate=predicate,
            object=object,
            confidence=confidence,
            source=source
        )
        
        with self._lock:
            self.knowledge_graph[fact_id] = fact
            
            # Index by subject
            if subject not in self.vector_index:
                self.vector_index[subject] = []
            self.vector_index[subject].append(fact_id)
        
        return fact_id
    
    def query_knowledge(self, subject: str = None, 
                       predicate: str = None) -> List[KnowledgeFact]:
        """Query knowledge graph."""
        results = []
        
        with self._lock:
            for fact in self.knowledge_graph.values():
                if subject and fact.subject != subject:
                    continue
                if predicate and fact.predicate != predicate:
                    continue
                results.append(fact)
                fact.uses += 1
        
        # Sort by confidence and usage
        results.sort(key=lambda f: (f.confidence, f.uses), reverse=True)
        return results
    
    def infer_relationship(self, subject1: str, subject2: str) -> Optional[str]:
        """Infer relationship between two subjects."""
        with self._lock:
            # Find common predicates
            facts1 = self.vector_index.get(subject1, [])
            facts2 = self.vector_index.get(subject2, [])
            
            predicates1 = {f.predicate for f in self.knowledge_graph.values() if f.fact_id in facts1}
            predicates2 = {f.predicate for f in self.knowledge_graph.values() if f.fact_id in facts2}
            
            common = predicates1 & predicates2
            if common:
                return f"shares {', '.join(common)} with"
        
        return None
    
    # ==================== TRADE MEMORY ====================
    
    def remember_trade(self, trade: Dict[str, Any]) -> str:
        """Remember a trade for episodic memory."""
        return self.remember(
            MemoryType.EPISODIC,
            {
                'type': 'trade',
                **trade
            },
            priority=MemoryPriority.HIGH if trade.get('pnl', 0) > 0 else MemoryPriority.MEDIUM,
            tags=['trade', trade.get('symbol', 'unknown')]
        )
    
    def get_trade_history(self, symbol: str = None, 
                         limit: int = 50) -> List[Dict[str, Any]]:
        """Get trade history."""
        trades = self.recall(
            memory_type=MemoryType.EPISODIC,
            query='trade',
            tags=['trade'] + ([symbol] if symbol else []),
            limit=limit
        )
        
        return [t.content for t in trades]
    
    def remember_strategy_performance(self, strategy: str, performance: Dict[str, Any]) -> str:
        """Remember strategy performance for learning."""
        return self.remember(
            MemoryType.LONG_TERM,
            {
                'type': 'strategy_performance',
                'strategy': strategy,
                **performance
            },
            priority=MemoryPriority.HIGH,
            tags=['strategy', strategy, 'performance']
        )
    
    def get_strategy_insights(self) -> Dict[str, Any]:
        """Get insights from strategy performance."""
        performances = self.recall(
            memory_type=MemoryType.LONG_TERM,
            query='strategy_performance',
            tags=['strategy', 'performance'],
            limit=100
        )
        
        insights = {
            'best_strategy': None,
            'worst_strategy': None,
            'avg_return': 0,
            'total_trades': 0
        }
        
        if not performances:
            return insights
        
        strategy_returns = defaultdict(list)
        
        for perf in performances:
            content = perf.content
            if 'strategy' in content:
                strategy = content['strategy']
                ret = content.get('return', 0)
                strategy_returns[strategy].append(ret)
        
        if strategy_returns:
            avg_returns = {s: np.mean(rs) for s, rs in strategy_returns.items()}
            insights['best_strategy'] = max(avg_returns, key=avg_returns.get)
            insights['worst_strategy'] = min(avg_returns, key=avg_returns.get)
            all_returns = [r for rs in strategy_returns.values() for r in rs]
            insights['avg_return'] = np.mean(all_returns)
            insights['total_trades'] = sum(len(rs) for rs in strategy_returns.values())
        
        return insights
    
    # ==================== MEMORY CONSOLIDATION ====================
    
    def consolidate(self) -> Dict[str, Any]:
        """Consolidate memories from short-term to long-term."""
        stats = {
            'consolidated': 0,
            'forgotten': 0,
            'promoted': 0
        }
        
        with self._lock:
            # Check if consolidation is needed
            if time.time() - self._last_consolidation < self.consolidation_interval:
                return stats
            
            # Promote important short-term memories
            short_term = self.memories[MemoryType.SHORT_TERM]
            to_promote = []
            
            for memory in short_term:
                if memory.importance_score >= self.importance_threshold:
                    to_promote.append(memory)
                elif time.time() - memory.created_at > 86400:  # 24 hours
                    stats['forgotten'] += 1
            
            for memory in to_promote:
                self.memories[MemoryType.LONG_TERM].append(memory)
                memory.memory_type = MemoryType.LONG_TERM
                stats['promoted'] += 1
            
            # Remove old short-term memories
            if len(short_term) > self.short_term_limit:
                to_remove = len(short_term) - self.short_term_limit
                short_term.sort(key=lambda m: m.importance_score)
                for _ in range(to_remove):
                    if short_term:
                        removed = short_term.pop(0)
                        self._remove_from_index(removed)
                        stats['forgotten'] += 1
            
            # Limit long-term memory
            long_term = self.memories[MemoryType.LONG_TERM]
            if len(long_term) > self.long_term_limit:
                to_remove = len(long_term) - self.long_term_limit
                long_term.sort(key=lambda m: (m.importance_score, m.created_at))
                for _ in range(to_remove):
                    if long_term:
                        removed = long_term.pop(0)
                        self._remove_from_index(removed)
                        stats['forgotten'] += 1
            
            self._last_consolidation = time.time()
        
        self.logger.info(f"Memory consolidation: {stats}")
        return stats
    
    def auto_consolidate(self, interval: int = None) -> None:
        """Start automatic consolidation."""
        if interval:
            self.consolidation_interval = interval
        
        def consolidation_loop():
            while True:
                time.sleep(self.consolidation_interval)
                self.consolidate()
        
        thread = threading.Thread(target=consolidation_loop, daemon=True)
        thread.start()
        self.logger.info("Auto-consolidation started")
    
    # ==================== PERSISTENCE ====================
    
    def save(self, path: str = None) -> None:
        """Save all memories to disk."""
        if path is None:
            path = self.config.get('memory_path', '~/.quanta_memory')
        
        save_path = Path(path).expanduser()
        save_path.mkdir(parents=True, exist_ok=True)
        
        with self._lock:
            # Save memories
            all_memories = {}
            for mem_type, memories in self.memories.items():
                all_memories[mem_type.value] = [m.to_dict() for m in memories]
            
            with open(save_path / 'memories.json', 'w') as f:
                json.dump(all_memories, f, indent=2)
            
            # Save conversations
            conversations = {
                sid: ctx.to_dict() 
                for sid, ctx in self.conversations.items()
            }
            with open(save_path / 'conversations.json', 'w') as f:
                json.dump(conversations, f, indent=2)
            
            # Save knowledge graph
            knowledge = {
                fid: fact.to_dict() 
                for fid, fact in self.knowledge_graph.items()
            }
            with open(save_path / 'knowledge.json', 'w') as f:
                json.dump(knowledge, f, indent=2)
        
        self.logger.info(f"Memories saved to {save_path}")
    
    def load(self, path: str = None) -> None:
        """Load memories from disk."""
        if path is None:
            path = self.config.get('memory_path', '~/.quanta_memory')
        
        load_path = Path(path).expanduser()
        
        if not load_path.exists():
            return
        
        with self._lock:
            # Load memories
            memories_file = load_path / 'memories.json'
            if memories_file.exists():
                with open(memories_file, 'r') as f:
                    all_memories = json.load(f)
                    for mem_type_str, memories in all_memories.items():
                        mem_type = MemoryType(mem_type_str)
                        self.memories[mem_type] = [
                            MemoryItem.from_dict(m) for m in memories
                        ]
            
            # Load conversations
            conversations_file = load_path / 'conversations.json'
            if conversations_file.exists():
                with open(conversations_file, 'r') as f:
                    conversations = json.load(f)
                    for sid, ctx_data in conversations.items():
                        self.conversations[sid] = ConversationContext.from_dict(ctx_data)
            
            # Load knowledge
            knowledge_file = load_path / 'knowledge.json'
            if knowledge_file.exists():
                with open(knowledge_file, 'r') as f:
                    knowledge = json.load(f)
                    for fid, fact_data in knowledge.items():
                        self.knowledge_graph[fid] = KnowledgeFact.from_dict(fact_data)
        
        self.logger.info(f"Memories loaded from {load_path}")
    
    # ==================== HELPER METHODS ====================
    
    def _generate_id(self) -> str:
        """Generate a unique memory ID."""
        return f"mem_{int(time.time() * 1000000)}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
    
    def _calculate_importance(self, content: Dict[str, Any], 
                             priority: MemoryPriority) -> float:
        """Calculate importance score for a memory."""
        base_score = priority.value / 3.0  # 0-1 scale
        
        # Content-based scoring
        if content.get('type') == 'trade':
            pnl = abs(content.get('pnl', 0))
            base_score += min(pnl / 10000, 0.3)  # Up to 0.3 for large trades
        
        if content.get('success', False):
            base_score += 0.1
        
        # Size adjustment
        content_size = len(str(content))
        if content_size > 10000:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _index_memory(self, memory: MemoryItem) -> None:
        """Add memory to indexes."""
        # Tag index
        for tag in memory.tags:
            self.tag_index[tag].append(memory.memory_id)
        
        # Type index
        self.type_index[memory.memory_type].append(memory.memory_id)
    
    def _remove_from_index(self, memory: MemoryItem) -> None:
        """Remove memory from indexes."""
        # Tag index
        for tag in memory.tags:
            if memory.memory_id in self.tag_index[tag]:
                self.tag_index[tag].remove(memory.memory_id)
        
        # Type index
        if memory.memory_id in self.type_index[memory.memory_type]:
            self.type_index[memory.memory_type].remove(memory.memory_id)
    
    def _load_memories(self) -> None:
        """Load memories on initialization."""
        self.load()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            return {
                'memory_counts': {
                    mt.value: len(memories) 
                    for mt, memories in self.memories.items()
                },
                'conversations': len(self.conversations),
                'knowledge_facts': len(self.knowledge_graph),
                'total_memories': sum(len(m) for m in self.memories.values()),
                'last_consolidation': self._last_consolidation
            }
    
    def clear(self, memory_type: MemoryType = None) -> int:
        """Clear memories of a specific type or all."""
        with self._lock:
            if memory_type:
                count = len(self.memories[memory_type])
                self.memories[memory_type] = []
                self.type_index[memory_type] = []
                return count
            else:
                total = sum(len(m) for m in self.memories.values())
                self.memories = defaultdict(list)
                self.type_index = defaultdict(list)
                return total


# Import numpy for calculations
import numpy as np
