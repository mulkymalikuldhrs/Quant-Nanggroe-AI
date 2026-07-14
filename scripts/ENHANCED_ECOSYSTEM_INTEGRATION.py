#!/usr/bin/env python3
"""
🌐 ENHANCED ECOSYSTEM INTEGRATION v5.0.0
Advanced Content Sharing, Collaboration & Document Management System

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
Ultimate Edition - Complete Ecosystem Integration
"""

import asyncio
import aiohttp
import json
import hashlib
import base64
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import sqlite3

# Heavy dependency - made optional for graceful degradation
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    Fernet = None
    _CRYPTOGRAPHY_AVAILABLE = False

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EnhancedEcosystem')

class ContentType(Enum):
    TEXT = "text"
    CODE = "code"
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    HTML = "html"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    RESEARCH = "research"
    PROMPT = "prompt"
    ANALYSIS = "analysis"

class PrivacyLevel(Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"
    ENCRYPTED = "encrypted"
    TEAM_ONLY = "team_only"

class SharePermission(Enum):
    READ_ONLY = "read_only"
    COMMENT = "comment"
    EDIT = "edit"
    ADMIN = "admin"

@dataclass
class ContentMetadata:
    id: str
    title: str
    content_type: ContentType
    privacy_level: PrivacyLevel
    created_at: datetime
    updated_at: datetime
    created_by: str
    file_size: int
    language: Optional[str] = None
    tags: List[str] = None
    description: Optional[str] = None
    version: str = "1.0"
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['content_type'] = self.content_type.value
        data['privacy_level'] = self.privacy_level.value
        return data

@dataclass
class ShareLink:
    share_id: str
    content_id: str
    permission: SharePermission
    expires_at: Optional[datetime] = None
    password_protected: bool = False
    access_count: int = 0
    max_access: Optional[int] = None
    
class EnhancedEcosystemManager:
    """
    🌐 Enhanced Ecosystem Manager - Complete Content & Collaboration Platform
    """
    
    def __init__(self, database_path: str = "ecosystem.db"):
        self.database_path = database_path
        self.content_storage = Path("content_storage")
        self.content_storage.mkdir(exist_ok=True)
        
        # Initialize encryption (optional - graceful degradation)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key) if (Fernet is not None and self.encryption_key) else None
        
        # Initialize database
        self._init_database()
        
        # Content type handlers
        self.content_handlers = {
            ContentType.TEXT: self._handle_text_content,
            ContentType.CODE: self._handle_code_content,
            ContentType.MARKDOWN: self._handle_markdown_content,
            ContentType.JSON: self._handle_json_content,
            ContentType.RESEARCH: self._handle_research_content,
            ContentType.PROMPT: self._handle_prompt_content,
            ContentType.ANALYSIS: self._handle_analysis_content,
        }
        
        logger.info("🌐 Enhanced Ecosystem Manager initialized")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Generate or load encryption key"""
        if not _CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography package not installed - encryption features disabled")
            return b""
        
        key_file = Path("ecosystem_key.key")
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            return key
    
    def _init_database(self):
        """Initialize SQLite database for content management"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Content metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_metadata (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,
                privacy_level TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                language TEXT,
                tags TEXT,
                description TEXT,
                version TEXT DEFAULT '1.0',
                parent_id TEXT,
                file_path TEXT NOT NULL
            )
        """)
        
        # Share links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS share_links (
                share_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                permission TEXT NOT NULL,
                expires_at TEXT,
                password_hash TEXT,
                access_count INTEGER DEFAULT 0,
                max_access INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (content_id) REFERENCES content_metadata (id)
            )
        """)
        
        # Collaboration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaborations (
                id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                permission TEXT NOT NULL,
                added_at TEXT NOT NULL,
                added_by TEXT NOT NULL,
                FOREIGN KEY (content_id) REFERENCES content_metadata (id)
            )
        """)
        
        # Comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                comment_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                parent_comment_id TEXT,
                FOREIGN KEY (content_id) REFERENCES content_metadata (id)
            )
        """)
        
        # Analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_analytics (
                id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (content_id) REFERENCES content_metadata (id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("📊 Database initialized successfully")
    
    async def create_content(
        self,
        title: str,
        content: Union[str, bytes],
        content_type: ContentType,
        privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC,
        created_by: str = "system",
        tags: List[str] = None,
        description: str = None,
        language: str = None
    ) -> str:
        """Create new content in the ecosystem"""
        
        content_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Process content based on type
        processed_content = await self._process_content(content, content_type)
        
        # Store content file
        file_path = self.content_storage / f"{content_id}.dat"
        
        if privacy_level == PrivacyLevel.ENCRYPTED:
            # Encrypt content
            if self.cipher_suite is None:
                logger.warning("Encryption requested but cryptography not available - storing unencrypted")
                if isinstance(processed_content, str):
                    file_path.write_text(processed_content, encoding='utf-8')
                else:
                    file_path.write_bytes(processed_content)
            else:
                if isinstance(processed_content, str):
                    processed_content = processed_content.encode()
                encrypted_content = self.cipher_suite.encrypt(processed_content)
                file_path.write_bytes(encrypted_content)
        else:
            if isinstance(processed_content, bytes):
                file_path.write_bytes(processed_content)
            else:
                file_path.write_text(processed_content, encoding='utf-8')
        
        # Calculate file size
        file_size = file_path.stat().st_size
        
        # Create metadata
        metadata = ContentMetadata(
            id=content_id,
            title=title,
            content_type=content_type,
            privacy_level=privacy_level,
            created_at=timestamp,
            updated_at=timestamp,
            created_by=created_by,
            file_size=file_size,
            language=language,
            tags=tags or [],
            description=description
        )
        
        # Store metadata in database
        await self._store_metadata(metadata, str(file_path))
        
        # Log analytics
        await self._log_analytics(content_id, "created", created_by)
        
        logger.info(f"📝 Content created: {content_id} ({title})")
        return content_id
    
    async def _process_content(self, content: Union[str, bytes], content_type: ContentType) -> Union[str, bytes]:
        """Process content based on its type"""
        
        if content_type in self.content_handlers:
            return await self.content_handlers[content_type](content)
        
        return content
    
    async def _handle_text_content(self, content: str) -> str:
        """Handle plain text content"""
        # Basic text processing - remove excessive whitespace
        return '\n'.join(line.strip() for line in content.split('\n') if line.strip())
    
    async def _handle_code_content(self, content: str) -> str:
        """Handle code content with syntax highlighting preparation"""
        # Detect programming language if not specified
        language = self._detect_programming_language(content)
        
        # Format code with metadata
        formatted_content = {
            "code": content,
            "language": language,
            "lines": len(content.split('\n')),
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(formatted_content, indent=2)
    
    async def _handle_markdown_content(self, content: str) -> str:
        """Handle Markdown content"""
        # Basic Markdown processing
        return content
    
    async def _handle_json_content(self, content: str) -> str:
        """Handle JSON content with validation"""
        try:
            # Validate and format JSON
            parsed = json.loads(content)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON content: {e}")
            return content
    
    async def _handle_research_content(self, content: str) -> str:
        """Handle research content with enhanced metadata"""
        research_data = {
            "content": content,
            "type": "research",
            "word_count": len(content.split()),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "research_metadata": {
                "citations_count": content.count("http"),
                "sections": content.count("#"),
                "references": content.count("ref:")
            }
        }
        
        return json.dumps(research_data, indent=2)
    
    async def _handle_prompt_content(self, content: str) -> str:
        """Handle AI prompt content"""
        prompt_data = {
            "prompt": content,
            "type": "ai_prompt",
            "length": len(content),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "prompt_metadata": {
                "contains_system": "system:" in content.lower(),
                "contains_user": "user:" in content.lower(),
                "contains_assistant": "assistant:" in content.lower(),
                "instruction_count": content.count("instruction:"),
                "example_count": content.count("example:")
            }
        }
        
        return json.dumps(prompt_data, indent=2)
    
    async def _handle_analysis_content(self, content: str) -> str:
        """Handle analysis and report content"""
        analysis_data = {
            "analysis": content,
            "type": "analysis",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "analysis_metadata": {
                "conclusion_sections": content.lower().count("conclusion"),
                "data_references": content.count("data:"),
                "chart_references": content.count("chart:"),
                "table_references": content.count("table:")
            }
        }
        
        return json.dumps(analysis_data, indent=2)
    
    def _detect_programming_language(self, code: str) -> str:
        """Detect programming language from code content"""
        code_lower = code.lower()
        
        # Simple language detection based on keywords
        if "def " in code or "import " in code or "class " in code:
            return "python"
        elif "function " in code or "const " in code or "let " in code:
            return "javascript"
        elif "public class" in code or "import java" in code:
            return "java"
        elif "#include" in code or "int main" in code:
            return "c++"
        elif "SELECT" in code.upper() or "INSERT" in code.upper():
            return "sql"
        elif "<!DOCTYPE" in code or "<html" in code:
            return "html"
        elif "body {" in code or ".class" in code:
            return "css"
        else:
            return "plaintext"
    
    async def _store_metadata(self, metadata: ContentMetadata, file_path: str):
        """Store content metadata in database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO content_metadata 
            (id, title, content_type, privacy_level, created_at, updated_at, 
             created_by, file_size, language, tags, description, version, 
             parent_id, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.id,
            metadata.title,
            metadata.content_type.value,
            metadata.privacy_level.value,
            metadata.created_at.isoformat(),
            metadata.updated_at.isoformat(),
            metadata.created_by,
            metadata.file_size,
            metadata.language,
            json.dumps(metadata.tags) if metadata.tags else None,
            metadata.description,
            metadata.version,
            metadata.parent_id,
            file_path
        ))
        
        conn.commit()
        conn.close()
    
    async def get_content(self, content_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Retrieve content by ID"""
        
        # Get metadata
        metadata = await self._get_metadata(content_id)
        if not metadata:
            return None
        
        # Check permissions
        if not await self._check_access_permission(content_id, user_id):
            logger.warning(f"Access denied for content {content_id} by user {user_id}")
            return None
        
        # Read content file
        file_path = Path(metadata['file_path'])
        if not file_path.exists():
            logger.error(f"Content file not found: {file_path}")
            return None
        
        # Decrypt if necessary
        if metadata['privacy_level'] == PrivacyLevel.ENCRYPTED.value:
            if self.cipher_suite is None:
                # Encryption was not available, read as plain text
                try:
                    content = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    content = base64.b64encode(file_path.read_bytes()).decode()
            else:
                encrypted_content = file_path.read_bytes()
                content = self.cipher_suite.decrypt(encrypted_content).decode()
        else:
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = base64.b64encode(file_path.read_bytes()).decode()
        
        # Log analytics
        await self._log_analytics(content_id, "accessed", user_id)
        
        return {
            "metadata": metadata,
            "content": content
        }
    
    async def _get_metadata(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content metadata from database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM content_metadata WHERE id = ?
        """, (content_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        metadata = dict(zip(columns, row))
        
        # Parse JSON fields
        if metadata['tags']:
            metadata['tags'] = json.loads(metadata['tags'])
        
        return metadata
    
    async def _check_access_permission(self, content_id: str, user_id: str = None) -> bool:
        """Check if user has permission to access content"""
        metadata = await self._get_metadata(content_id)
        if not metadata:
            return False
        
        privacy_level = metadata['privacy_level']
        
        # Public content is accessible to everyone
        if privacy_level == PrivacyLevel.PUBLIC.value:
            return True
        
        # Unlisted content is accessible with direct link
        if privacy_level == PrivacyLevel.UNLISTED.value:
            return True
        
        # Private and encrypted content requires ownership or collaboration
        if privacy_level in [PrivacyLevel.PRIVATE.value, PrivacyLevel.ENCRYPTED.value]:
            if user_id == metadata['created_by']:
                return True
            
            # Check collaboration permissions
            return await self._check_collaboration_permission(content_id, user_id)
        
        return False
    
    async def _check_collaboration_permission(self, content_id: str, user_id: str) -> bool:
        """Check if user has collaboration permission"""
        if not user_id:
            return False
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT permission FROM collaborations 
            WHERE content_id = ? AND user_id = ?
        """, (content_id, user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    async def create_share_link(
        self,
        content_id: str,
        permission: SharePermission = SharePermission.READ_ONLY,
        expires_at: Optional[datetime] = None,
        password: Optional[str] = None,
        max_access: Optional[int] = None
    ) -> str:
        """Create a shareable link for content"""
        
        share_id = str(uuid.uuid4())
        
        # Hash password if provided
        # SECURITY: Use PBKDF2 with salt for password hashing (SHA-256 alone is too fast)
        password_hash = None
        if password:
            import os as _os
            salt = _os.urandom(16)
            dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            password_hash = salt.hex() + ':' + dk.hex()
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO share_links 
            (share_id, content_id, permission, expires_at, password_hash, 
             max_access, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            share_id,
            content_id,
            permission.value,
            expires_at.isoformat() if expires_at else None,
            password_hash,
            max_access,
            datetime.now(timezone.utc).isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🔗 Share link created: {share_id} for content {content_id}")
        return share_id
    
    async def access_shared_content(
        self,
        share_id: str,
        password: Optional[str] = None,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Access content via share link"""
        
        # Get share link details
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM share_links WHERE share_id = ?
        """, (share_id,))
        
        share_link = cursor.fetchone()
        if not share_link:
            return None
        
        share_columns = [desc[0] for desc in cursor.description]
        share_data = dict(zip(share_columns, share_link))
        
        # Check expiration
        if share_data['expires_at']:
            expires_at = datetime.fromisoformat(share_data['expires_at'])
            if datetime.now(timezone.utc) > expires_at:
                logger.warning(f"Share link expired: {share_id}")
                return None
        
        # Check access limit
        if share_data['max_access'] and share_data['access_count'] >= share_data['max_access']:
            logger.warning(f"Share link access limit reached: {share_id}")
            return None
        
        # Check password
        if share_data['password_hash']:
            if not password:
                return {"error": "password_required"}
            
            # Support both old (plain SHA-256) and new (PBKDF2 with salt) hash formats
            stored_hash = share_data['password_hash']
            if ':' in stored_hash:
                # New PBKDF2 format: salt:hash
                salt_hex, expected_hash = stored_hash.split(':', 1)
                salt = bytes.fromhex(salt_hex)
                dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
                if dk.hex() != expected_hash:
                    return {"error": "invalid_password"}
            else:
                # Legacy SHA-256 format (deprecated, for backward compat)
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if password_hash != stored_hash:
                    return {"error": "invalid_password"}
        
        # Increment access count
        cursor.execute("""
            UPDATE share_links SET access_count = access_count + 1 
            WHERE share_id = ?
        """, (share_id,))
        
        conn.commit()
        conn.close()
        
        # Get content
        content = await self.get_content(share_data['content_id'], user_id)
        if content:
            content['share_permission'] = share_data['permission']
        
        # Log analytics
        await self._log_analytics(share_data['content_id'], "shared_access", user_id, {
            "share_id": share_id,
            "permission": share_data['permission']
        })
        
        return content
    
    async def search_content(
        self,
        query: str,
        content_type: Optional[ContentType] = None,
        user_id: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search content in the ecosystem"""
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Build search query
        where_conditions = []
        params = []
        
        # Text search in title and description
        where_conditions.append("(title LIKE ? OR description LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
        
        # Filter by content type
        if content_type:
            where_conditions.append("content_type = ?")
            params.append(content_type.value)
        
        # Only show accessible content
        where_conditions.append("(privacy_level = ? OR privacy_level = ? OR created_by = ?)")
        params.extend([PrivacyLevel.PUBLIC.value, PrivacyLevel.UNLISTED.value, user_id or ""])
        
        where_clause = " AND ".join(where_conditions)
        
        cursor.execute(f"""
            SELECT * FROM content_metadata 
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT ?
        """, params + [limit])
        
        results = []
        columns = [desc[0] for desc in cursor.description]
        
        for row in cursor.fetchall():
            metadata = dict(zip(columns, row))
            if metadata['tags']:
                metadata['tags'] = json.loads(metadata['tags'])
            results.append(metadata)
        
        conn.close()
        
        logger.info(f"🔍 Search completed: {len(results)} results for '{query}'")
        return results
    
    async def add_comment(
        self,
        content_id: str,
        user_id: str,
        comment_text: str,
        parent_comment_id: Optional[str] = None
    ) -> str:
        """Add comment to content"""
        
        comment_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO comments 
            (id, content_id, user_id, comment_text, created_at, parent_comment_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            comment_id,
            content_id,
            user_id,
            comment_text,
            datetime.now(timezone.utc).isoformat(),
            parent_comment_id
        ))
        
        conn.commit()
        conn.close()
        
        # Log analytics
        await self._log_analytics(content_id, "commented", user_id)
        
        logger.info(f"💬 Comment added: {comment_id} on content {content_id}")
        return comment_id
    
    async def get_comments(self, content_id: str) -> List[Dict[str, Any]]:
        """Get comments for content"""
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM comments 
            WHERE content_id = ? 
            ORDER BY created_at ASC
        """, (content_id,))
        
        results = []
        columns = [desc[0] for desc in cursor.description]
        
        for row in cursor.fetchall():
            comment = dict(zip(columns, row))
            results.append(comment)
        
        conn.close()
        
        return results
    
    async def _log_analytics(
        self,
        content_id: str,
        event_type: str,
        user_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log analytics event"""
        
        analytics_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO content_analytics 
            (id, content_id, event_type, user_id, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            analytics_id,
            content_id,
            event_type,
            user_id,
            datetime.now(timezone.utc).isoformat(),
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    async def get_analytics(self, content_id: str) -> Dict[str, Any]:
        """Get analytics for content"""
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Get basic analytics
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM content_analytics 
            WHERE content_id = ?
            GROUP BY event_type
        """, (content_id,))
        
        analytics = {}
        for row in cursor.fetchall():
            analytics[row[0]] = row[1]
        
        # Get recent activity
        cursor.execute("""
            SELECT event_type, user_id, timestamp, metadata
            FROM content_analytics 
            WHERE content_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (content_id,))
        
        recent_activity = []
        columns = [desc[0] for desc in cursor.description]
        
        for row in cursor.fetchall():
            activity = dict(zip(columns, row))
            if activity['metadata']:
                activity['metadata'] = json.loads(activity['metadata'])
            recent_activity.append(activity)
        
        conn.close()
        
        return {
            "summary": analytics,
            "recent_activity": recent_activity
        }
    
    async def export_content(
        self,
        content_id: str,
        export_format: str = "json",
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Export content in various formats"""
        
        content_data = await self.get_content(content_id, user_id)
        if not content_data:
            return None
        
        if export_format == "json":
            return {
                "export_format": "json",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "data": content_data
            }
        elif export_format == "markdown":
            # Convert to markdown format
            metadata = content_data['metadata']
            content = content_data['content']
            
            markdown_export = f"""# {metadata['title']}

**Created:** {metadata['created_at']}  
**Updated:** {metadata['updated_at']}  
**Type:** {metadata['content_type']}  
**Created by:** {metadata['created_by']}

{metadata['description'] if metadata['description'] else ''}

---

{content}
"""
            return {
                "export_format": "markdown",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "content": markdown_export
            }
        
        return None
    
    async def create_collection(
        self,
        name: str,
        description: str,
        content_ids: List[str],
        created_by: str,
        privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC
    ) -> str:
        """Create a collection of related content"""
        
        collection_data = {
            "name": name,
            "description": description,
            "content_ids": content_ids,
            "type": "collection",
            "created_by": created_by,
            "item_count": len(content_ids)
        }
        
        collection_id = await self.create_content(
            title=f"Collection: {name}",
            content=json.dumps(collection_data, indent=2),
            content_type=ContentType.JSON,
            privacy_level=privacy_level,
            created_by=created_by,
            description=description,
            tags=["collection"]
        )
        
        logger.info(f"📚 Collection created: {collection_id} ({name})")
        return collection_id
    
    async def backup_ecosystem(self, backup_path: str = None) -> str:
        """Create backup of entire ecosystem"""
        
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"ecosystem_backup_{timestamp}"
        
        backup_dir = Path(backup_path)
        backup_dir.mkdir(exist_ok=True)
        
        # Backup database
        import shutil
        shutil.copy2(self.database_path, backup_dir / "ecosystem.db")
        
        # Backup content storage
        shutil.copytree(self.content_storage, backup_dir / "content_storage", dirs_exist_ok=True)
        
        # Create backup metadata
        backup_metadata = {
            "backup_created_at": datetime.now(timezone.utc).isoformat(),
            "total_content_files": len(list(self.content_storage.glob("*.dat"))),
            "database_size": Path(self.database_path).stat().st_size,
            "content_storage_size": sum(f.stat().st_size for f in self.content_storage.glob("*.dat"))
        }
        
        (backup_dir / "backup_metadata.json").write_text(
            json.dumps(backup_metadata, indent=2)
        )
        
        logger.info(f"💾 Ecosystem backup created: {backup_path}")
        return str(backup_dir)


# Integration with existing Ultimate Agentic AI System
class EcosystemIntegrationAgent:
    """
    🤖 Integration agent for Enhanced Ecosystem
    """
    
    def __init__(self, ecosystem_manager: EnhancedEcosystemManager):
        self.ecosystem = ecosystem_manager
        self.name = "Ecosystem Integration Agent"
        
    async def auto_create_content_from_prompt(self, prompt: str, user_id: str) -> str:
        """Automatically create content from AI prompt"""
        
        content_id = await self.ecosystem.create_content(
            title=f"AI Prompt - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            content=prompt,
            content_type=ContentType.PROMPT,
            privacy_level=PrivacyLevel.PRIVATE,
            created_by=user_id,
            tags=["ai-prompt", "auto-generated"]
        )
        
        return content_id
    
    async def auto_create_content_from_response(self, response: str, prompt_id: str, user_id: str) -> str:
        """Automatically create content from AI response"""
        
        content_id = await self.ecosystem.create_content(
            title=f"AI Response - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            content=response,
            content_type=ContentType.TEXT,
            privacy_level=PrivacyLevel.PRIVATE,
            created_by=user_id,
            tags=["ai-response", "auto-generated"],
            parent_id=prompt_id
        )
        
        return content_id
    
    async def create_research_collection(self, research_data: List[str], user_id: str) -> str:
        """Create research collection from multiple sources"""
        
        content_ids = []
        
        for i, data in enumerate(research_data):
            content_id = await self.ecosystem.create_content(
                title=f"Research Data {i+1}",
                content=data,
                content_type=ContentType.RESEARCH,
                privacy_level=PrivacyLevel.PRIVATE,
                created_by=user_id,
                tags=["research", "collection-item"]
            )
            content_ids.append(content_id)
        
        # Create collection
        collection_id = await self.ecosystem.create_collection(
            name=f"Research Collection - {datetime.now().strftime('%Y-%m-%d')}",
            description="Automated research collection",
            content_ids=content_ids,
            created_by=user_id,
            privacy_level=PrivacyLevel.PRIVATE
        )
        
        return collection_id


# Example usage and testing
async def main():
    """Example usage of Enhanced Ecosystem Integration"""
    
    # Initialize ecosystem
    ecosystem = EnhancedEcosystemManager()
    agent = EcosystemIntegrationAgent(ecosystem)
    
    print("🌐 Enhanced Ecosystem Integration System")
    print("=" * 50)
    
    # Create sample content
    text_content_id = await ecosystem.create_content(
        title="Ultimate AI System Documentation",
        content="""# Ultimate Agentic AI System v5.0.0

This is the revolutionary AI automation platform that changes everything.

## Features
- Multi-LLM support
- Voice interaction
- Blockchain integration
- Enterprise security
""",
        content_type=ContentType.MARKDOWN,
        privacy_level=PrivacyLevel.PUBLIC,
        created_by="system",
        tags=["documentation", "ai", "ultimate"],
        description="Main documentation for Ultimate AI System"
    )
    
    print(f"✅ Text content created: {text_content_id}")
    
    # Create code content
    code_content_id = await ecosystem.create_content(
        title="AI Agent Implementation",
        content='''
class AutonomousAgent:
    def __init__(self, name, capabilities):
        self.name = name
        self.capabilities = capabilities
    
    async def process_task(self, task):
        """Process task with AI enhancement"""
        return await self.ai_process(task)
''',
        content_type=ContentType.CODE,
        privacy_level=PrivacyLevel.PUBLIC,
        created_by="developer",
        language="python",
        tags=["code", "ai-agent", "python"]
    )
    
    print(f"✅ Code content created: {code_content_id}")
    
    # Create share link
    share_id = await ecosystem.create_share_link(
        text_content_id,
        permission=SharePermission.READ_ONLY,
        max_access=100
    )
    
    print(f"🔗 Share link created: {share_id}")
    
    # Search content
    search_results = await ecosystem.search_content("AI System", user_id="system")
    print(f"🔍 Search results: {len(search_results)} items found")
    
    # Get analytics
    analytics = await ecosystem.get_analytics(text_content_id)
    print(f"📊 Analytics: {analytics}")
    
    # Create backup
    backup_path = await ecosystem.backup_ecosystem()
    print(f"💾 Backup created: {backup_path}")
    
    print("\n🎉 Enhanced Ecosystem Integration completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())