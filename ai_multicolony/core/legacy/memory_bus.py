"""
🧠 Memory Bus - Shared Memory System
Persistent storage and inter-agent communication

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import json
import sqlite3
try:
    import redis
except ImportError:
    redis = None
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import threading
import os

@dataclass 
class MemoryEntry:
    entry_id: str
    agent_id: str
    data_type: str  # task, result, log, metric, conversation
    content: Any
    timestamp: datetime
    ttl: Optional[int] = None  # Time to live in seconds
    tags: List[str] = None

class MemoryBus:
    """
    Centralized memory system for all agents
    
    Features:
    - SQLite for persistent storage
    - Redis for fast caching (optional)
    - JSON for simple data
    - Memory cleanup and TTL
    - Search and filtering
    """
    
    def __init__(self):
        self.db_path = "data/memory.db"
        self.json_path = "data/memory.json"
        self.redis_client = None
        self.lock = threading.Lock()
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Initialize storage
        self._init_sqlite()
        self._init_redis()
        self._init_json()
        
        # Load in-memory cache
        self.cache = {}
        self._load_recent_memory()
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                entry_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                data_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ttl INTEGER,
                tags TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                task_type TEXT,
                status TEXT DEFAULT 'pending',
                assigned_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                result TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_metrics (
                metric_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON memory(agent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_data_type ON memory(data_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory(timestamp)")
        
        conn.commit()
        conn.close()
    
    def _init_redis(self):
        """Initialize Redis connection (optional)"""
        if redis is None:
            print("⚠️ Redis package not installed, using SQLite only")
            self.redis_client = None
            return
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            print("✅ Redis connected")
        except Exception as e:
            print(f"⚠️ Redis not available: {e}")
            self.redis_client = None
    
    def _init_json(self):
        """Initialize JSON storage"""
        if not os.path.exists(self.json_path):
            with open(self.json_path, 'w') as f:
                json.dump({
                    "system_config": {},
                    "agent_registry": {},
                    "conversations": {},
                    "workflows": {}
                }, f, indent=2)
    
    def _load_recent_memory(self):
        """Load recent memory into cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT entry_id, agent_id, data_type, content, timestamp
                FROM memory 
                WHERE timestamp > datetime('now', '-1 hour')
                ORDER BY timestamp DESC
                LIMIT 1000
            """)
            
            for row in cursor:
                self.cache[row[0]] = {
                    "agent_id": row[1],
                    "data_type": row[2], 
                    "content": json.loads(row[3]),
                    "timestamp": row[4]
                }
            
            conn.close()
        except Exception as e:
            print(f"Error loading memory cache: {e}")
    
    def store(self, entry: MemoryEntry) -> bool:
        """Store memory entry"""
        try:
            with self.lock:
                # Store in SQLite
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT OR REPLACE INTO memory
                    (entry_id, agent_id, data_type, content, timestamp, ttl, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.entry_id,
                    entry.agent_id,
                    entry.data_type,
                    json.dumps(entry.content, default=str),
                    entry.timestamp.isoformat(),
                    entry.ttl,
                    json.dumps(entry.tags) if entry.tags else None
                ))
                conn.commit()
                conn.close()
                
                # Store in Redis cache
                if self.redis_client:
                    redis_key = f"memory:{entry.entry_id}"
                    redis_data = json.dumps(asdict(entry), default=str)
                    if entry.ttl:
                        self.redis_client.setex(redis_key, entry.ttl, redis_data)
                    else:
                        self.redis_client.set(redis_key, redis_data)
                
                # Update local cache
                self.cache[entry.entry_id] = {
                    "agent_id": entry.agent_id,
                    "data_type": entry.data_type,
                    "content": entry.content,
                    "timestamp": entry.timestamp.isoformat()
                }
                
                return True
                
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve memory entry by ID"""
        try:
            # Check cache first
            if entry_id in self.cache:
                cached = self.cache[entry_id]
                return MemoryEntry(
                    entry_id=entry_id,
                    agent_id=cached["agent_id"],
                    data_type=cached["data_type"],
                    content=cached["content"],
                    timestamp=datetime.fromisoformat(cached["timestamp"])
                )
            
            # Check Redis
            if self.redis_client:
                redis_data = self.redis_client.get(f"memory:{entry_id}")
                if redis_data:
                    data = json.loads(redis_data)
                    return MemoryEntry(**data)
            
            # Check SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT agent_id, data_type, content, timestamp, ttl, tags
                FROM memory WHERE entry_id = ?
            """, (entry_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return MemoryEntry(
                    entry_id=entry_id,
                    agent_id=row[0],
                    data_type=row[1],
                    content=json.loads(row[2]),
                    timestamp=datetime.fromisoformat(row[3]),
                    ttl=row[4],
                    tags=json.loads(row[5]) if row[5] else None
                )
                
        except Exception as e:
            print(f"Error retrieving memory: {e}")
        
        return None
    
    def search(self, agent_id: str = None, data_type: str = None, 
               tags: List[str] = None, limit: int = 100) -> List[MemoryEntry]:
        """Search memory entries"""
        try:
            query = "SELECT entry_id, agent_id, data_type, content, timestamp, ttl, tags FROM memory WHERE 1=1"
            params = []
            
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            
            if data_type:
                query += " AND data_type = ?"
                params.append(data_type)
            
            if tags:
                for tag in tags:
                    query += " AND tags LIKE ?"
                    params.append(f"%{tag}%")
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor:
                results.append(MemoryEntry(
                    entry_id=row[0],
                    agent_id=row[1],
                    data_type=row[2],
                    content=json.loads(row[3]),
                    timestamp=datetime.fromisoformat(row[4]),
                    ttl=row[5],
                    tags=json.loads(row[6]) if row[6] else None
                ))
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Error searching memory: {e}")
            return []
    
    def store_task(self, task) -> bool:
        """Store task information"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO tasks
                (task_id, prompt, task_type, status, assigned_agent, created_at, completed_at, result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.prompt,
                task.task_type,
                task.status,
                task.assigned_agent,
                task.created_at.isoformat() if task.created_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                json.dumps(task.result, default=str) if task.result else None
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error storing task: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "task_id": row[0],
                    "prompt": row[1],
                    "task_type": row[2],
                    "status": row[3],
                    "assigned_agent": row[4],
                    "created_at": row[5],
                    "completed_at": row[6],
                    "result": json.loads(row[7]) if row[7] else None
                }
        except Exception as e:
            print(f"Error getting task: {e}")
        return None
    
    def get_recent_tasks(self, limit: int = 50) -> List[Dict]:
        """Get recent tasks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT task_id, prompt, task_type, status, assigned_agent, created_at
                FROM tasks 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            tasks = []
            for row in cursor:
                tasks.append({
                    "task_id": row[0],
                    "prompt": row[1],
                    "task_type": row[2],
                    "status": row[3],
                    "assigned_agent": row[4],
                    "created_at": row[5]
                })
            
            conn.close()
            return tasks
        except Exception as e:
            print(f"Error getting recent tasks: {e}")
            return []
    
    def store_workflow_step(self, task_id: str, agent_name: str, result: Any):
        """Store workflow step result"""
        entry = MemoryEntry(
            entry_id=f"{task_id}_step_{agent_name}",
            agent_id=agent_name,
            data_type="workflow_step",
            content={
                "task_id": task_id,
                "agent": agent_name,
                "result": result
            },
            timestamp=datetime.now(),
            tags=["workflow", task_id]
        )
        return self.store(entry)
    
    def store_metric(self, agent_id: str, metric_type: str, value: float):
        """Store agent performance metric"""
        try:
            metric_id = f"{agent_id}_{metric_type}_{int(datetime.now().timestamp())}"
            
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO agent_metrics
                (metric_id, agent_id, metric_type, value)
                VALUES (?, ?, ?, ?)
            """, (metric_id, agent_id, metric_type, value))
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error storing metric: {e}")
            return False
    
    def get_agent_metrics(self, agent_id: str, metric_type: str = None, 
                         hours: int = 24) -> List[Dict]:
        """Get agent metrics"""
        try:
            query = """
                SELECT metric_type, value, timestamp
                FROM agent_metrics 
                WHERE agent_id = ? AND timestamp > datetime('now', '-' || ? || ' hours')
            """
            
            params = [agent_id, str(int(hours))]
            
            if metric_type:
                query += " AND metric_type = ?"
                params.append(metric_type)
            
            query += " ORDER BY timestamp DESC"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(query, params)
            
            metrics = []
            for row in cursor:
                metrics.append({
                    "metric_type": row[0],
                    "value": row[1],
                    "timestamp": row[2]
                })
            
            conn.close()
            return metrics
        except Exception as e:
            print(f"Error getting metrics: {e}")
            return []
    
    def cleanup_expired(self):
        """Clean up expired entries"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                
                # Clean up expired memory entries
                conn.execute("""
                    DELETE FROM memory 
                    WHERE ttl IS NOT NULL 
                    AND datetime(timestamp, '+' || ttl || ' seconds') < datetime('now')
                """)
                
                # Clean up old tasks (older than 30 days)
                conn.execute("""
                    DELETE FROM tasks 
                    WHERE created_at < datetime('now', '-30 days')
                """)
                
                # Clean up old metrics (older than 7 days)
                conn.execute("""
                    DELETE FROM agent_metrics 
                    WHERE timestamp < datetime('now', '-7 days')
                """)
                
                conn.commit()
                conn.close()
                
                # Clean Redis cache
                if self.redis_client:
                    # Redis handles TTL automatically
                    pass
                
                print("✅ Memory cleanup completed")
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get table sizes
            cursor = conn.execute("SELECT COUNT(*) FROM memory")
            memory_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            tasks_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM agent_metrics")
            metrics_count = cursor.fetchone()[0]
            
            # Get database size
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size = page_count * page_size
            
            conn.close()
            
            return {
                "memory_entries": memory_count,
                "tasks": tasks_count,
                "metrics": metrics_count,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "cache_entries": len(self.cache),
                "redis_connected": self.redis_client is not None
            }
            
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return {}
    
    def get_conversation_history(self, user_id: str = None, limit: int = 50) -> List[Dict]:
        """Get conversation history"""
        return self.search(
            data_type="conversation",
            tags=[user_id] if user_id else None,
            limit=limit
        )
    
    def store_conversation(self, user_id: str, message: str, response: str):
        """Store conversation exchange"""
        entry = MemoryEntry(
            entry_id=f"conv_{user_id}_{int(datetime.now().timestamp())}",
            agent_id="prompt_master",
            data_type="conversation",
            content={
                "user_id": user_id,
                "message": message,
                "response": response
            },
            timestamp=datetime.now(),
            ttl=86400 * 30,  # 30 days
            tags=["conversation", user_id]
        )
        return self.store(entry)

# Global instance
memory_bus = MemoryBus()
