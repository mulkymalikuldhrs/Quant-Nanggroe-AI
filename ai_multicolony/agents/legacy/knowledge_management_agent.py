"""
🧠 Knowledge Management Agent - Advanced Memory and Data Storage System
Intelligent agent for comprehensive knowledge management, learning, and data organization

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import logging
import hashlib
import sqlite3
import pickle
import gzip
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import requests
import subprocess
import threading
from collections import defaultdict, Counter

# Heavy ML dependencies - made optional for graceful degradation
try:
    import numpy as np
except ImportError:
    np = None

try:
    import nltk
except ImportError:
    nltk = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None
    KMeans = None

try:
    import spacy
except ImportError:
    spacy = None

@dataclass
class KnowledgeItem:
    """Knowledge item data structure"""
    item_id: str
    title: str
    content: str
    content_type: str  # text, code, image, video, document, url, conversation
    category: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    source: str
    relevance_score: float = 0.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class SearchResult:
    """Search result data structure"""
    item_id: str
    title: str
    content_preview: str
    relevance_score: float
    category: str
    tags: List[str]
    created_at: datetime
    source: str

@dataclass
class LearningPattern:
    """Learning pattern identification"""
    pattern_id: str
    pattern_type: str  # frequent_topic, user_behavior, content_trend
    pattern_data: Dict[str, Any]
    confidence: float
    discovered_at: datetime
    applications: List[str]

class KnowledgeManagementAgent:
    """
    Knowledge Management Agent: Advanced memory and intelligent data organization
    
    Capabilities:
    - 🧠 Intelligent knowledge storage and retrieval
    - 🔍 Advanced semantic search
    - 📚 Automatic categorization and tagging
    - 🔗 Knowledge graph construction
    - 📊 Learning pattern recognition
    - 🎯 Personalized content recommendations
    - 🌐 Multi-language support
    - 📈 Knowledge analytics and insights
    - 🔄 Real-time knowledge updates
    - 🤖 AI-powered knowledge synthesis
    """
    
    def __init__(self):
        self.agent_id = "knowledge_management_agent"
        self.name = "Knowledge Management Agent"
        self.status = "initializing"
        self.version = "1.0.0"
        self.start_time = datetime.now()
        
        # Core capabilities
        self.capabilities = [
            "intelligent_storage",
            "semantic_search",
            "auto_categorization",
            "knowledge_graph",
            "pattern_recognition",
            "content_recommendation",
            "multi_language_support",
            "knowledge_analytics",
            "real_time_updates",
            "ai_synthesis"
        ]
        
        # Knowledge storage
        self.knowledge_items = {}
        self.knowledge_graph = {}
        self.categories = set()
        self.tags = set()
        self.learning_patterns = {}
        
        # Search and retrieval
        if TfidfVectorizer is not None:
            self.tfidf_vectorizer = TfidfVectorizer(max_features=10000, stop_words='english')
        else:
            self.tfidf_vectorizer = None
        self.document_vectors = None
        self.search_cache = {}
        
        # Configuration
        self.config = {
            "max_cache_size": 1000,
            "auto_tag_threshold": 0.7,
            "similarity_threshold": 0.3,
            "max_recommendations": 10,
            "learning_update_interval": 3600,  # 1 hour
            "supported_languages": ["en", "id", "es", "fr", "de", "zh"],
            "max_content_length": 100000,  # 100KB per item
            "enable_auto_learning": True
        }
        
        # Analytics
        self.analytics = {
            "total_items": 0,
            "total_searches": 0,
            "successful_retrievals": 0,
            "patterns_discovered": 0,
            "last_updated": datetime.now()
        }
        
        # Language processing
        self.nlp = None
        self.language_detectors = {}
        
        # Initialize logging
        self.setup_logging()
        
        # Initialize knowledge infrastructure
        self.initialize_knowledge_infrastructure()
        
        # Load existing knowledge
        self.load_existing_knowledge()
        
        # Initialize NLP components
        self.initialize_nlp_components()
        
        self.logger.info("Knowledge Management Agent initialized successfully")
        self.status = "ready"
    
    def setup_logging(self):
        """Setup logging for Knowledge Management Agent"""
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "knowledge_management.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("KnowledgeManagementAgent")
    
    def initialize_knowledge_infrastructure(self):
        """Initialize knowledge management infrastructure"""
        # Create knowledge directories
        knowledge_dirs = [
            "data/knowledge",
            "data/knowledge/items",
            "data/knowledge/categories",
            "data/knowledge/patterns",
            "data/knowledge/cache",
            "data/knowledge/vectors",
            "data/knowledge/analytics"
        ]
        
        for directory in knowledge_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.initialize_knowledge_database()
        
        # Initialize search infrastructure
        self.initialize_search_infrastructure()
    
    def initialize_knowledge_database(self):
        """Initialize SQLite database for knowledge storage"""
        db_dir = Path("data/knowledge")
        self.db_path = db_dir / "knowledge.db"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    item_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_type TEXT DEFAULT 'text',
                    category TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    relevance_score REAL DEFAULT 0.0,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_graph (
                    edge_id TEXT PRIMARY KEY,
                    source_item TEXT,
                    target_item TEXT,
                    relationship_type TEXT,
                    weight REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_item) REFERENCES knowledge_items (item_id),
                    FOREIGN KEY (target_item) REFERENCES knowledge_items (item_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    search_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    results_count INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    execution_time REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    confidence REAL,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applications TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    category_id TEXT PRIMARY KEY,
                    category_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    item_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON knowledge_items(content_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON knowledge_items(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON knowledge_items(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relevance ON knowledge_items(relevance_score)')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Knowledge database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize knowledge database: {e}")
    
    def initialize_search_infrastructure(self):
        """Initialize search and indexing infrastructure"""
        try:
            # Load or create TF-IDF vectorizer
            # SECURITY NOTE: pickle.load is inherently unsafe for untrusted data.
            # We only load from our own data directory which should be protected.
            # If these files are tampered with, arbitrary code execution is possible.
            # Consider migrating to a safer serialization format (e.g., JSON, safetensors).
            vectorizer_path = Path("data/knowledge/vectors/tfidf_vectorizer.pkl")
            if vectorizer_path.exists():
                # Verify the file is within the expected data directory (path traversal check)
                resolved = vectorizer_path.resolve()
                data_dir = Path("data").resolve()
                if not str(resolved).startswith(str(data_dir)):
                    self.logger.error(f"Security: vectorizer path escapes data directory: {resolved}")
                    return
                with open(vectorizer_path, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
            
            # Load document vectors if available
            vectors_path = Path("data/knowledge/vectors/document_vectors.pkl")
            if vectors_path.exists():
                resolved = vectors_path.resolve()
                data_dir = Path("data").resolve()
                if not str(resolved).startswith(str(data_dir)):
                    self.logger.error(f"Security: vectors path escapes data directory: {resolved}")
                    return
                with open(vectors_path, 'rb') as f:
                    self.document_vectors = pickle.load(f)
            
            self.logger.info("Search infrastructure initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize search infrastructure: {e}")
    
    def load_existing_knowledge(self):
        """Load existing knowledge from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load knowledge items
            cursor.execute('''
                SELECT item_id, title, content, content_type, category, tags, 
                       created_at, updated_at, source, relevance_score, 
                       access_count, last_accessed, metadata
                FROM knowledge_items
            ''')
            
            for row in cursor.fetchall():
                item_id = row[0]
                knowledge_item = KnowledgeItem(
                    item_id=item_id,
                    title=row[1],
                    content=row[2],
                    content_type=row[3],
                    category=row[4],
                    tags=json.loads(row[5]) if row[5] else [],
                    created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                    updated_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    source=row[8],
                    relevance_score=row[9] or 0.0,
                    access_count=row[10] or 0,
                    last_accessed=datetime.fromisoformat(row[11]) if row[11] else None,
                    metadata=json.loads(row[12]) if row[12] else {}
                )
                
                self.knowledge_items[item_id] = knowledge_item
                self.categories.add(knowledge_item.category)
                self.tags.update(knowledge_item.tags)
            
            # Load learning patterns
            cursor.execute('SELECT pattern_id, pattern_type, pattern_data, confidence, discovered_at, applications FROM learning_patterns')
            for row in cursor.fetchall():
                pattern = LearningPattern(
                    pattern_id=row[0],
                    pattern_type=row[1],
                    pattern_data=json.loads(row[2]),
                    confidence=row[3],
                    discovered_at=datetime.fromisoformat(row[4]),
                    applications=json.loads(row[5]) if row[5] else []
                )
                self.learning_patterns[row[0]] = pattern
            
            conn.close()
            
            self.analytics["total_items"] = len(self.knowledge_items)
            self.analytics["patterns_discovered"] = len(self.learning_patterns)
            
            self.logger.info(f"Loaded {len(self.knowledge_items)} knowledge items and {len(self.learning_patterns)} patterns")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing knowledge: {e}")
    
    def initialize_nlp_components(self):
        """Initialize natural language processing components"""
        try:
            # Download required NLTK data
            if nltk is not None:
                try:
                    nltk.download('punkt', quiet=True)
                    nltk.download('stopwords', quiet=True)
                    nltk.download('wordnet', quiet=True)
                except:
                    pass  # Ignore download errors
            else:
                self.logger.warning("NLTK not installed. Some NLP features may be limited.")
            
            # Initialize spaCy model for advanced NLP
            if spacy is not None:
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                except OSError:
                    self.logger.warning("spaCy English model not found. Some NLP features may be limited.")
                    self.nlp = None
            else:
                self.logger.warning("spaCy not installed. Some NLP features may be limited.")
                self.nlp = None
            
            self.logger.info("NLP components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NLP components: {e}")
    
    async def store_knowledge(self, title: str, content: str, content_type: str = "text",
                            category: str = None, tags: List[str] = None, 
                            source: str = "manual", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Store new knowledge item"""
        self.logger.info(f"Storing new knowledge item: {title}")
        
        try:
            # Generate unique item ID
            item_id = hashlib.md5(f"{title}_{content[:100]}_{datetime.now()}".encode()).hexdigest()[:12]
            
            # Auto-categorize if not provided
            if not category:
                category = await self._auto_categorize_content(content, content_type)
            
            # Auto-generate tags if not provided
            if not tags:
                tags = await self._auto_generate_tags(content, title)
            
            # Calculate initial relevance score
            relevance_score = await self._calculate_relevance_score(content, title, category, tags)
            
            # Create knowledge item
            knowledge_item = KnowledgeItem(
                item_id=item_id,
                title=title,
                content=content,
                content_type=content_type,
                category=category,
                tags=tags or [],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                source=source,
                relevance_score=relevance_score,
                metadata=metadata or {}
            )
            
            # Store in memory
            self.knowledge_items[item_id] = knowledge_item
            self.categories.add(category)
            self.tags.update(tags or [])
            
            # Store in database
            await self._save_knowledge_item_to_database(knowledge_item)
            
            # Update search vectors
            await self._update_search_vectors()
            
            # Create knowledge graph connections
            await self._create_knowledge_connections(item_id)
            
            # Update analytics
            self.analytics["total_items"] += 1
            self.analytics["last_updated"] = datetime.now()
            
            self.logger.info(f"Knowledge item stored successfully: {item_id}")
            
            return {
                "success": True,
                "item_id": item_id,
                "category": category,
                "tags": tags,
                "relevance_score": relevance_score,
                "message": "Knowledge item stored successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to store knowledge item: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_knowledge(self, query: str, content_types: List[str] = None,
                             categories: List[str] = None, limit: int = 10,
                             user_id: str = None) -> Dict[str, Any]:
        """Search knowledge using advanced semantic search"""
        self.logger.info(f"Searching knowledge: {query}")
        
        search_start_time = time.time()
        
        try:
            # Check cache first
            cache_key = hashlib.md5(f"{query}_{content_types}_{categories}_{limit}".encode()).hexdigest()
            if cache_key in self.search_cache:
                cached_result = self.search_cache[cache_key]
                if (datetime.now() - cached_result["timestamp"]).seconds < 300:  # 5 minutes cache
                    return cached_result["results"]
            
            # Perform semantic search
            search_results = await self._perform_semantic_search(query, content_types, categories, limit)
            
            # Apply filters
            filtered_results = await self._apply_search_filters(search_results, content_types, categories)
            
            # Rank results
            ranked_results = await self._rank_search_results(filtered_results, query, user_id)
            
            # Create search result objects
            results = []
            for item_id, score in ranked_results[:limit]:
                if item_id in self.knowledge_items:
                    item = self.knowledge_items[item_id]
                    
                    # Update access statistics
                    item.access_count += 1
                    item.last_accessed = datetime.now()
                    
                    result = SearchResult(
                        item_id=item.item_id,
                        title=item.title,
                        content_preview=item.content[:200] + "..." if len(item.content) > 200 else item.content,
                        relevance_score=score,
                        category=item.category,
                        tags=item.tags,
                        created_at=item.created_at,
                        source=item.source
                    )
                    results.append(result)
            
            execution_time = time.time() - search_start_time
            
            # Cache results
            self.search_cache[cache_key] = {
                "results": {
                    "success": True,
                    "results": [asdict(r) for r in results],
                    "total_found": len(ranked_results),
                    "execution_time": execution_time,
                    "query": query
                },
                "timestamp": datetime.now()
            }
            
            # Log search
            await self._log_search(query, len(results), execution_time, user_id)
            
            # Update analytics
            self.analytics["total_searches"] += 1
            self.analytics["successful_retrievals"] += len(results)
            
            self.logger.info(f"Search completed: {len(results)} results in {execution_time:.3f}s")
            
            return {
                "success": True,
                "results": [asdict(r) for r in results],
                "total_found": len(ranked_results),
                "execution_time": execution_time,
                "query": query
            }
            
        except Exception as e:
            self.logger.error(f"Knowledge search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_recommendations(self, user_id: str = None, context: str = None,
                                count: int = 5) -> Dict[str, Any]:
        """Get personalized knowledge recommendations"""
        self.logger.info(f"Generating recommendations for user: {user_id}")
        
        try:
            recommendations = []
            
            # Get recommendations based on different strategies
            
            # 1. Content-based recommendations
            content_recs = await self._get_content_based_recommendations(context, count)
            recommendations.extend(content_recs)
            
            # 2. Popular content recommendations
            popular_recs = await self._get_popular_content_recommendations(count)
            recommendations.extend(popular_recs)
            
            # 3. Recent content recommendations
            recent_recs = await self._get_recent_content_recommendations(count)
            recommendations.extend(recent_recs)
            
            # 4. Learning pattern based recommendations
            if user_id:
                pattern_recs = await self._get_pattern_based_recommendations(user_id, count)
                recommendations.extend(pattern_recs)
            
            # Remove duplicates and rank
            unique_recommendations = []
            seen_ids = set()
            
            for rec in recommendations:
                if rec["item_id"] not in seen_ids:
                    unique_recommendations.append(rec)
                    seen_ids.add(rec["item_id"])
            
            # Sort by recommendation score
            unique_recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            return {
                "success": True,
                "recommendations": unique_recommendations[:count],
                "total_available": len(unique_recommendations),
                "strategies_used": ["content_based", "popularity", "recency", "patterns"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_knowledge_patterns(self) -> Dict[str, Any]:
        """Analyze and discover knowledge patterns"""
        self.logger.info("Analyzing knowledge patterns")
        
        try:
            patterns_discovered = []
            
            # 1. Content clustering analysis
            content_patterns = await self._analyze_content_clusters()
            patterns_discovered.extend(content_patterns)
            
            # 2. Tag co-occurrence analysis
            tag_patterns = await self._analyze_tag_cooccurrence()
            patterns_discovered.extend(tag_patterns)
            
            # 3. Temporal patterns analysis
            temporal_patterns = await self._analyze_temporal_patterns()
            patterns_discovered.extend(temporal_patterns)
            
            # 4. Category distribution analysis
            category_patterns = await self._analyze_category_distribution()
            patterns_discovered.extend(category_patterns)
            
            # Store discovered patterns
            for pattern_data in patterns_discovered:
                pattern_id = hashlib.md5(f"{pattern_data['type']}_{datetime.now()}".encode()).hexdigest()[:8]
                
                pattern = LearningPattern(
                    pattern_id=pattern_id,
                    pattern_type=pattern_data["type"],
                    pattern_data=pattern_data["data"],
                    confidence=pattern_data.get("confidence", 0.5),
                    discovered_at=datetime.now(),
                    applications=pattern_data.get("applications", [])
                )
                
                self.learning_patterns[pattern_id] = pattern
                await self._save_learning_pattern(pattern)
            
            self.analytics["patterns_discovered"] += len(patterns_discovered)
            
            return {
                "success": True,
                "patterns_discovered": len(patterns_discovered),
                "pattern_types": [p["type"] for p in patterns_discovered],
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Pattern analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_knowledge_analytics(self) -> Dict[str, Any]:
        """Get comprehensive knowledge analytics"""
        try:
            # Basic statistics
            total_items = len(self.knowledge_items)
            categories_count = len(self.categories)
            tags_count = len(self.tags)
            
            # Content type distribution
            content_type_dist = defaultdict(int)
            category_dist = defaultdict(int)
            source_dist = defaultdict(int)
            
            for item in self.knowledge_items.values():
                content_type_dist[item.content_type] += 1
                category_dist[item.category] += 1
                source_dist[item.source] += 1
            
            # Most accessed items
            most_accessed = sorted(
                self.knowledge_items.values(),
                key=lambda x: x.access_count,
                reverse=True
            )[:10]
            
            # Recent activity
            recent_items = sorted(
                self.knowledge_items.values(),
                key=lambda x: x.created_at,
                reverse=True
            )[:10]
            
            # Search analytics
            search_analytics = {
                "total_searches": self.analytics["total_searches"],
                "successful_retrievals": self.analytics["successful_retrievals"],
                "cache_size": len(self.search_cache)
            }
            
            return {
                "success": True,
                "overview": {
                    "total_items": total_items,
                    "categories": categories_count,
                    "tags": tags_count,
                    "learning_patterns": len(self.learning_patterns)
                },
                "distributions": {
                    "content_types": dict(content_type_dist),
                    "categories": dict(category_dist),
                    "sources": dict(source_dist)
                },
                "most_accessed": [
                    {
                        "item_id": item.item_id,
                        "title": item.title,
                        "access_count": item.access_count,
                        "category": item.category
                    }
                    for item in most_accessed
                ],
                "recent_items": [
                    {
                        "item_id": item.item_id,
                        "title": item.title,
                        "created_at": item.created_at.isoformat(),
                        "category": item.category
                    }
                    for item in recent_items
                ],
                "search_analytics": search_analytics,
                "agent_status": self.status,
                "last_updated": self.analytics["last_updated"].isoformat(),
                "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get analytics: {e}")
            return {"success": False, "error": str(e)}
    
    # Private helper methods
    
    async def _auto_categorize_content(self, content: str, content_type: str) -> str:
        """Automatically categorize content based on its text"""
        try:
            # Simple keyword-based categorization
            content_lower = content.lower()
            
            if content_type == "code":
                if any(keyword in content_lower for keyword in ["python", "def ", "import "]):
                    return "python_code"
                elif any(keyword in content_lower for keyword in ["javascript", "function", "const ", "let "]):
                    return "javascript_code"
                elif any(keyword in content_lower for keyword in ["html", "<div", "<span"]):
                    return "web_development"
                else:
                    return "programming"
            
            elif any(keyword in content_lower for keyword in ["ai", "machine learning", "neural network", "algorithm"]):
                return "artificial_intelligence"
            elif any(keyword in content_lower for keyword in ["database", "sql", "query", "table"]):
                return "database"
            elif any(keyword in content_lower for keyword in ["security", "vulnerability", "encryption", "authentication"]):
                return "cybersecurity"
            elif any(keyword in content_lower for keyword in ["api", "endpoint", "request", "response"]):
                return "api_development"
            elif any(keyword in content_lower for keyword in ["deployment", "server", "cloud", "infrastructure"]):
                return "devops"
            else:
                return "general"
                
        except Exception as e:
            self.logger.error(f"Auto-categorization failed: {e}")
            return "uncategorized"
    
    async def _auto_generate_tags(self, content: str, title: str) -> List[str]:
        """Automatically generate tags for content"""
        try:
            tags = set()
            
            # Extract from title
            title_words = re.findall(r'\w+', title.lower())
            tags.update([word for word in title_words if len(word) > 3])
            
            # Extract technical keywords
            technical_keywords = [
                "python", "javascript", "react", "node", "api", "database", "sql",
                "machine learning", "ai", "neural network", "deep learning",
                "security", "encryption", "authentication", "vulnerability",
                "docker", "kubernetes", "aws", "cloud", "deployment",
                "frontend", "backend", "fullstack", "framework", "library"
            ]
            
            content_lower = content.lower()
            for keyword in technical_keywords:
                if keyword in content_lower:
                    tags.add(keyword.replace(" ", "_"))
            
            # Limit to top 10 most relevant tags
            return list(tags)[:10]
            
        except Exception as e:
            self.logger.error(f"Auto-tag generation failed: {e}")
            return []
    
    async def _calculate_relevance_score(self, content: str, title: str, category: str, tags: List[str]) -> float:
        """Calculate relevance score for content"""
        try:
            score = 0.0
            
            # Base score from content length (normalized)
            content_length_score = min(len(content) / 1000, 1.0) * 20
            score += content_length_score
            
            # Title quality score
            title_score = min(len(title) / 50, 1.0) * 10
            score += title_score
            
            # Category bonus
            if category and category != "uncategorized":
                score += 15
            
            # Tags bonus
            score += len(tags) * 2
            
            # Technical content bonus
            technical_keywords = ["code", "algorithm", "api", "framework", "library"]
            for keyword in technical_keywords:
                if keyword in content.lower() or keyword in title.lower():
                    score += 5
            
            return min(score, 100.0)  # Cap at 100
            
        except Exception as e:
            self.logger.error(f"Relevance score calculation failed: {e}")
            return 50.0  # Default score
    
    async def _perform_semantic_search(self, query: str, content_types: List[str], 
                                     categories: List[str], limit: int) -> List[tuple]:
        """Perform semantic search using TF-IDF and cosine similarity"""
        try:
            if not self.knowledge_items:
                return []
            
            # If sklearn is not available, fall back to simple text search
            if self.tfidf_vectorizer is None or cosine_similarity is None:
                return self._simple_text_search(query, content_types, categories, limit)
            
            # Prepare documents for search
            documents = []
            item_ids = []
            
            for item_id, item in self.knowledge_items.items():
                # Apply pre-filters
                if content_types and item.content_type not in content_types:
                    continue
                if categories and item.category not in categories:
                    continue
                
                # Combine title and content for search
                search_text = f"{item.title} {item.content}"
                documents.append(search_text)
                item_ids.append(item_id)
            
            if not documents:
                return []
            
            # Vectorize documents and query
            all_docs = documents + [query]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(all_docs)
            
            # Calculate similarities
            query_vector = tfidf_matrix[-1]
            doc_vectors = tfidf_matrix[:-1]
            
            similarities = cosine_similarity(query_vector, doc_vectors)[0]
            
            # Create results with similarity scores
            results = []
            for i, score in enumerate(similarities):
                if score > self.config["similarity_threshold"]:
                    results.append((item_ids[i], float(score)))
            
            # Sort by similarity score
            results.sort(key=lambda x: x[1], reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return []
    
    def _simple_text_search(self, query: str, content_types: List[str],
                           categories: List[str], limit: int) -> List[tuple]:
        """Fallback simple text search when sklearn is not available"""
        query_lower = query.lower()
        results = []
        
        for item_id, item in self.knowledge_items.items():
            if content_types and item.content_type not in content_types:
                continue
            if categories and item.category not in categories:
                continue
            
            text = f"{item.title} {item.content}".lower()
            # Simple keyword matching score
            score = 0.0
            for word in query_lower.split():
                if word in text:
                    score += 1.0
            
            if score > 0:
                results.append((item_id, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

# Global instance
knowledge_management_agent = KnowledgeManagementAgent()

# Export for use by other modules
__all__ = ['KnowledgeManagementAgent', 'knowledge_management_agent', 'KnowledgeItem', 'SearchResult', 'LearningPattern']
