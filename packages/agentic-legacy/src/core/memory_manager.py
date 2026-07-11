"""
Memory Manager for Agentic AI System
Manages shared memory, knowledge base, and external API integrations

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import json
import sqlite3
import requests
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib
import pickle
import threading
from dataclasses import dataclass, asdict

@dataclass
class MemoryEntry:
    """Data structure for memory entries"""
    id: str
    agent_id: str
    task_id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    memory_type: str  # 'interaction', 'knowledge', 'result', 'external'
    importance: int  # 1-10 scale
    
class MemoryManager:
    """Central memory management system for all agents"""
    
    def __init__(self, db_path: str = "data/agent_memory.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._setup_database()
        self._setup_external_apis()
        
    def _setup_database(self):
        """Initialize SQLite database for memory storage"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    importance INTEGER NOT NULL,
                    embedding BLOB,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    last_updated TEXT NOT NULL,
                    relevance_score REAL DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_interactions (
                    id TEXT PRIMARY KEY,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON agent_memory(agent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_memory_timestamp ON agent_memory(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_base_topic ON knowledge_base(topic)")
            
    def _setup_external_apis(self):
        """Setup external API configurations"""
        self.external_apis = {
            'wikipedia': {
                'base_url': 'https://en.wikipedia.org/api/rest_v1',
                'headers': {'User-Agent': 'Agentic-AI-System/1.0 (Indonesia)'}
            },
            'news': {
                'base_url': 'https://newsapi.org/v2',
                'headers': {}  # Free tier available
            },
            'weather': {
                'base_url': 'https://api.openweathermap.org/data/2.5',
                'headers': {}  # Free tier available
            },
            'quotes': {
                'base_url': 'https://api.quotable.io',
                'headers': {}
            },
            'facts': {
                'base_url': 'https://uselessfacts.jsph.pl/random.json',
                'headers': {}
            }
        }
        
    def store_memory(self, memory_entry: MemoryEntry) -> bool:
        """Store memory entry in database"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO agent_memory 
                        (id, agent_id, task_id, content, metadata, timestamp, memory_type, importance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        memory_entry.id,
                        memory_entry.agent_id,
                        memory_entry.task_id,
                        memory_entry.content,
                        json.dumps(memory_entry.metadata),
                        memory_entry.timestamp,
                        memory_entry.memory_type,
                        memory_entry.importance
                    ))
                    
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    def retrieve_memories(self, agent_id: Optional[str] = None, 
                         memory_type: Optional[str] = None,
                         limit: int = 100) -> List[MemoryEntry]:
        """Retrieve memories from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM agent_memory WHERE 1=1"
                params = []
                
                if agent_id:
                    query += " AND agent_id = ?"
                    params.append(agent_id)
                    
                if memory_type:
                    query += " AND memory_type = ?"
                    params.append(memory_type)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                memories = []
                for row in rows:
                    memory = MemoryEntry(
                        id=row[0],
                        agent_id=row[1],
                        task_id=row[2],
                        content=row[3],
                        metadata=json.loads(row[4]),
                        timestamp=row[5],
                        memory_type=row[6],
                        importance=row[7]
                    )
                    memories.append(memory)
                
                return memories
                
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return []
    
    def search_memories(self, query: str, agent_id: Optional[str] = None) -> List[MemoryEntry]:
        """Search memories by content"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                sql_query = """
                    SELECT * FROM agent_memory 
                    WHERE content LIKE ? 
                """
                params = [f"%{query}%"]
                
                if agent_id:
                    sql_query += " AND agent_id = ?"
                    params.append(agent_id)
                
                sql_query += " ORDER BY importance DESC, timestamp DESC LIMIT 50"
                
                cursor = conn.execute(sql_query, params)
                rows = cursor.fetchall()
                
                memories = []
                for row in rows:
                    memory = MemoryEntry(
                        id=row[0],
                        agent_id=row[1],
                        task_id=row[2],
                        content=row[3],
                        metadata=json.loads(row[4]),
                        timestamp=row[5],
                        memory_type=row[6],
                        importance=row[7]
                    )
                    memories.append(memory)
                
                return memories
                
        except Exception as e:
            print(f"Error searching memories: {e}")
            return []
    
    def store_agent_interaction(self, from_agent: str, to_agent: str, 
                               interaction_type: str, content: str, 
                               context: Optional[Dict] = None) -> bool:
        """Store interaction between agents"""
        try:
            interaction_id = hashlib.md5(
                f"{from_agent}_{to_agent}_{datetime.now().isoformat()}".encode()
            ).hexdigest()
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO agent_interactions 
                        (id, from_agent, to_agent, interaction_type, content, context, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        interaction_id,
                        from_agent,
                        to_agent,
                        interaction_type,
                        content,
                        json.dumps(context or {}),
                        datetime.now().isoformat()
                    ))
            
            return True
        except Exception as e:
            print(f"Error storing interaction: {e}")
            return False
    
    def get_agent_interactions(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """Get interactions for specific agent"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM agent_interactions 
                    WHERE from_agent = ? OR to_agent = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (agent_id, agent_id, limit))
                
                interactions = []
                for row in cursor.fetchall():
                    interactions.append({
                        'id': row[0],
                        'from_agent': row[1],
                        'to_agent': row[2],
                        'interaction_type': row[3],
                        'content': row[4],
                        'context': json.loads(row[5]),
                        'timestamp': row[6]
                    })
                
                return interactions
                
        except Exception as e:
            print(f"Error getting interactions: {e}")
            return []

class ExternalKnowledgeAPI:
    """Integration with external knowledge sources"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        
    async def fetch_wikipedia_knowledge(self, topic: str) -> Optional[Dict]:
        """Fetch knowledge from Wikipedia API"""
        try:
            # Search for the topic
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
            
            async with requests.Session() as session:
                response = requests.get(search_url, headers={
                    'User-Agent': 'Agentic-AI-System/1.0 (Indonesia)'
                })
                
                if response.status_code == 200:
                    data = response.json()
                    
                    knowledge = {
                        'topic': topic,
                        'content': data.get('extract', ''),
                        'source': 'Wikipedia',
                        'source_url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    # Store in knowledge base
                    self._store_knowledge(knowledge)
                    
                    return knowledge
                    
        except Exception as e:
            print(f"Error fetching Wikipedia knowledge: {e}")
            
        return None
    
    async def fetch_news_knowledge(self, query: str) -> List[Dict]:
        """Fetch news from public news API"""
        try:
            # Using free news API (no key required for basic usage)
            url = f"https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'sortBy': 'publishedAt',
                'pageSize': 5,
                'language': 'en'
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                news_items = []
                
                for article in data.get('articles', []):
                    knowledge = {
                        'topic': query,
                        'content': f"{article.get('title', '')} - {article.get('description', '')}",
                        'source': 'News API',
                        'source_url': article.get('url', ''),
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    news_items.append(knowledge)
                    self._store_knowledge(knowledge)
                
                return news_items
                
        except Exception as e:
            print(f"Error fetching news: {e}")
            
        return []
    
    async def fetch_general_facts(self) -> Optional[Dict]:
        """Fetch random facts from free API"""
        try:
            url = "https://uselessfacts.jsph.pl/random.json?language=en"
            
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                knowledge = {
                    'topic': 'Random Fact',
                    'content': data.get('text', ''),
                    'source': 'Useless Facts API',
                    'source_url': data.get('permalink', ''),
                    'last_updated': datetime.now().isoformat()
                }
                
                self._store_knowledge(knowledge)
                return knowledge
                
        except Exception as e:
            print(f"Error fetching facts: {e}")
            
        return None
    
    async def fetch_quotes(self, topic: Optional[str] = None) -> Optional[Dict]:
        """Fetch inspirational quotes"""
        try:
            url = "https://api.quotable.io/random"
            params = {}
            
            if topic:
                params['tags'] = topic
                
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                knowledge = {
                    'topic': f"Quote - {topic or 'General'}",
                    'content': f'"{data.get("content", "")}" - {data.get("author", "")}',
                    'source': 'Quotable API',
                    'source_url': 'https://quotable.io',
                    'last_updated': datetime.now().isoformat()
                }
                
                self._store_knowledge(knowledge)
                return knowledge
                
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            
        return None
    
    def _store_knowledge(self, knowledge: Dict):
        """Store knowledge in database"""
        try:
            knowledge_id = hashlib.md5(
                f"{knowledge['topic']}_{knowledge['source']}".encode()
            ).hexdigest()
            
            with sqlite3.connect(self.memory_manager.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO knowledge_base 
                    (id, topic, content, source, source_url, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    knowledge_id,
                    knowledge['topic'],
                    knowledge['content'],
                    knowledge['source'],
                    knowledge['source_url'],
                    knowledge['last_updated']
                ))
                
        except Exception as e:
            print(f"Error storing knowledge: {e}")

class AgentMemoryInterface:
    """Interface for agents to interact with memory system"""
    
    def __init__(self, memory_manager: MemoryManager, external_api: ExternalKnowledgeAPI):
        self.memory_manager = memory_manager
        self.external_api = external_api
        
    def log_agent_activity(self, agent_id: str, task_id: str, activity: str, 
                          metadata: Optional[Dict] = None, importance: int = 5):
        """Log agent activity to memory"""
        memory_id = hashlib.md5(
            f"{agent_id}_{task_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        memory_entry = MemoryEntry(
            id=memory_id,
            agent_id=agent_id,
            task_id=task_id,
            content=activity,
            metadata=metadata or {},
            timestamp=datetime.now().isoformat(),
            memory_type='interaction',
            importance=importance
        )
        
        return self.memory_manager.store_memory(memory_entry)
    
    def get_relevant_memories(self, agent_id: str, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Get memories relevant to current task"""
        # Search memories for relevant content
        memories = self.memory_manager.search_memories(query, agent_id)
        
        # Also get recent high-importance memories
        recent_memories = self.memory_manager.retrieve_memories(
            agent_id=agent_id, 
            limit=limit
        )
        
        # Combine and deduplicate
        all_memories = {}
        for memory in memories + recent_memories:
            all_memories[memory.id] = memory
        
        # Sort by importance and recency
        sorted_memories = sorted(
            all_memories.values(),
            key=lambda m: (m.importance, m.timestamp),
            reverse=True
        )
        
        return sorted_memories[:limit]
    
    async def enrich_with_external_knowledge(self, topic: str) -> Dict:
        """Enrich agent knowledge with external sources"""
        knowledge_sources = {}
        
        # Try multiple sources
        try:
            # Wikipedia
            wiki_knowledge = await self.external_api.fetch_wikipedia_knowledge(topic)
            if wiki_knowledge:
                knowledge_sources['wikipedia'] = wiki_knowledge
                
            # News
            news_knowledge = await self.external_api.fetch_news_knowledge(topic)
            if news_knowledge:
                knowledge_sources['news'] = news_knowledge
                
            # Quotes (if relevant)
            if any(word in topic.lower() for word in ['motivation', 'inspiration', 'quote']):
                quote_knowledge = await self.external_api.fetch_quotes(topic)
                if quote_knowledge:
                    knowledge_sources['quotes'] = quote_knowledge
                    
        except Exception as e:
            print(f"Error enriching knowledge: {e}")
        
        return knowledge_sources
    
    def store_agent_result(self, agent_id: str, task_id: str, result: Any, 
                          metadata: Optional[Dict] = None):
        """Store agent result for future reference"""
        memory_id = hashlib.md5(
            f"{agent_id}_result_{task_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        memory_entry = MemoryEntry(
            id=memory_id,
            agent_id=agent_id,
            task_id=task_id,
            content=str(result),
            metadata=metadata or {},
            timestamp=datetime.now().isoformat(),
            memory_type='result',
            importance=7  # Results are generally important
        )
        
        return self.memory_manager.store_memory(memory_entry)
    
    def get_agent_learning_history(self, agent_id: str) -> Dict:
        """Get learning and interaction history for agent"""
        memories = self.memory_manager.retrieve_memories(agent_id=agent_id, limit=100)
        interactions = self.memory_manager.get_agent_interactions(agent_id, limit=50)
        
        # Analyze patterns
        memory_types = {}
        for memory in memories:
            memory_types[memory.memory_type] = memory_types.get(memory.memory_type, 0) + 1
        
        return {
            'total_memories': len(memories),
            'memory_breakdown': memory_types,
            'recent_interactions': len(interactions),
            'avg_importance': sum(m.importance for m in memories) / len(memories) if memories else 0,
            'most_recent_activity': memories[0].timestamp if memories else None
        }

# Global memory system instance
memory_manager = MemoryManager()
external_knowledge_api = ExternalKnowledgeAPI(memory_manager)
agent_memory_interface = AgentMemoryInterface(memory_manager, external_knowledge_api)
