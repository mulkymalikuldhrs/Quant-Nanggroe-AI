"""
Secure Credential Manager for Agentic AI System
Manages authentication credentials and web automation

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class SecureCredentialManager:
    """Secure credential storage and management"""
    
    def __init__(self, master_password: Optional[str] = None):
        self.db_path = "data/credentials.db"
        self.master_password = master_password
        self.encryption_key = None
        
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        
        # Initialize encryption
        self._initialize_encryption()
        
        # Setup database
        self._setup_database()
    
    def _initialize_encryption(self):
        """Initialize encryption system"""
        if not self.master_password:
            # Read master password from environment; fail if not set
            self.master_password = os.getenv("AGENTIC_AI_MASTER_PASSWORD")
            if not self.master_password:
                raise ValueError(
                    "AGENTIC_AI_MASTER_PASSWORD environment variable is required. "
                    "Set it before running the application."
                )
        
        # Derive encryption key from master password
        password = self.master_password.encode()
        # Use a salt derived from the master password hash for per-user uniqueness
        salt = hashlib.sha256(b"agentic_ai_salt_" + password).digest()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.fernet = Fernet(key)
    
    def _setup_database(self):
        """Setup SQLite database for credentials"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website_name TEXT NOT NULL,
                    website_url TEXT NOT NULL,
                    username TEXT,
                    email TEXT,
                    password_encrypted BLOB NOT NULL,
                    additional_fields TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME,
                    usage_count INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credential_id INTEGER,
                    website_url TEXT,
                    action_type TEXT,
                    success BOOLEAN,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (credential_id) REFERENCES credentials (id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_website_name ON credentials(website_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_website_url ON credentials(website_url)")
    
    def store_credential(self, website_name: str, website_url: str, 
                        username: str = None, email: str = None, 
                        password: str = None, additional_fields: Dict = None,
                        notes: str = None) -> bool:
        """Store encrypted credentials"""
        try:
            if not password:
                raise ValueError("Password is required")
            
            # Encrypt password
            encrypted_password = self.fernet.encrypt(password.encode())
            
            # Prepare additional fields
            additional_fields_json = json.dumps(additional_fields or {})
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO credentials 
                    (website_name, website_url, username, email, password_encrypted, 
                     additional_fields, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    website_name, website_url, username, email, 
                    encrypted_password, additional_fields_json, notes
                ))
            
            return True
            
        except Exception as e:
            print(f"Error storing credential: {e}")
            return False
    
    def get_credential(self, website_name: str = None, 
                      website_url: str = None, 
                      credential_id: int = None) -> Optional[Dict]:
        """Retrieve and decrypt credentials"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if credential_id:
                    cursor = conn.execute(
                        "SELECT * FROM credentials WHERE id = ?", 
                        (credential_id,)
                    )
                elif website_name:
                    cursor = conn.execute(
                        "SELECT * FROM credentials WHERE website_name = ? ORDER BY last_used DESC LIMIT 1", 
                        (website_name,)
                    )
                elif website_url:
                    cursor = conn.execute(
                        "SELECT * FROM credentials WHERE website_url = ? ORDER BY last_used DESC LIMIT 1", 
                        (website_url,)
                    )
                else:
                    return None
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Decrypt password
                decrypted_password = self.fernet.decrypt(row[5]).decode()
                
                # Parse additional fields
                additional_fields = json.loads(row[6]) if row[6] else {}
                
                credential = {
                    'id': row[0],
                    'website_name': row[1],
                    'website_url': row[2],
                    'username': row[3],
                    'email': row[4],
                    'password': decrypted_password,
                    'additional_fields': additional_fields,
                    'created_at': row[7],
                    'last_used': row[8],
                    'usage_count': row[9],
                    'notes': row[10]
                }
                
                # Update usage statistics
                self._update_usage_stats(row[0])
                
                return credential
                
        except Exception as e:
            print(f"Error retrieving credential: {e}")
            return None
    
    def list_credentials(self) -> List[Dict]:
        """List all stored credentials (without passwords)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, website_name, website_url, username, email, 
                           created_at, last_used, usage_count, notes
                    FROM credentials 
                    ORDER BY last_used DESC, website_name
                """)
                
                credentials = []
                for row in cursor.fetchall():
                    credentials.append({
                        'id': row[0],
                        'website_name': row[1],
                        'website_url': row[2],
                        'username': row[3],
                        'email': row[4],
                        'created_at': row[5],
                        'last_used': row[6],
                        'usage_count': row[7],
                        'notes': row[8]
                    })
                
                return credentials
                
        except Exception as e:
            print(f"Error listing credentials: {e}")
            return []
    
    def update_credential(self, credential_id: int, **updates) -> bool:
        """Update existing credential"""
        try:
            # Get current credential
            current = self.get_credential(credential_id=credential_id)
            if not current:
                return False
            
            # Prepare update fields
            set_clauses = []
            values = []
            
            for field, value in updates.items():
                if field == 'password':
                    # Encrypt new password
                    encrypted_password = self.fernet.encrypt(value.encode())
                    set_clauses.append("password_encrypted = ?")
                    values.append(encrypted_password)
                elif field == 'additional_fields':
                    set_clauses.append("additional_fields = ?")
                    values.append(json.dumps(value))
                elif field in ['website_name', 'website_url', 'username', 'email', 'notes']:
                    set_clauses.append(f"{field} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            values.append(credential_id)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"UPDATE credentials SET {', '.join(set_clauses)} WHERE id = ?",
                    values
                )
            
            return True
            
        except Exception as e:
            print(f"Error updating credential: {e}")
            return False
    
    def delete_credential(self, credential_id: int) -> bool:
        """Delete credential"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error deleting credential: {e}")
            return False
    
    def _update_usage_stats(self, credential_id: int):
        """Update usage statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE credentials 
                    SET last_used = CURRENT_TIMESTAMP, usage_count = usage_count + 1 
                    WHERE id = ?
                """, (credential_id,))
                
        except Exception as e:
            print(f"Error updating usage stats: {e}")
    
    def log_usage(self, credential_id: int, website_url: str, 
                  action_type: str, success: bool, error_message: str = None):
        """Log credential usage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO login_history 
                    (credential_id, website_url, action_type, success, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """, (credential_id, website_url, action_type, success, error_message))
                
        except Exception as e:
            print(f"Error logging usage: {e}")
    
    def get_usage_history(self, credential_id: int = None, limit: int = 50) -> List[Dict]:
        """Get usage history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if credential_id:
                    cursor = conn.execute("""
                        SELECT lh.*, c.website_name 
                        FROM login_history lh
                        JOIN credentials c ON lh.credential_id = c.id
                        WHERE lh.credential_id = ?
                        ORDER BY lh.timestamp DESC LIMIT ?
                    """, (credential_id, limit))
                else:
                    cursor = conn.execute("""
                        SELECT lh.*, c.website_name 
                        FROM login_history lh
                        JOIN credentials c ON lh.credential_id = c.id
                        ORDER BY lh.timestamp DESC LIMIT ?
                    """, (limit,))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'id': row[0],
                        'credential_id': row[1],
                        'website_url': row[2],
                        'action_type': row[3],
                        'success': bool(row[4]),
                        'timestamp': row[5],
                        'error_message': row[6],
                        'website_name': row[7]
                    })
                
                return history
                
        except Exception as e:
            print(f"Error getting usage history: {e}")
            return []
    
    def search_credentials(self, query: str) -> List[Dict]:
        """Search credentials by website name, URL, username, or email"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, website_name, website_url, username, email, 
                           created_at, last_used, usage_count, notes
                    FROM credentials 
                    WHERE website_name LIKE ? OR website_url LIKE ? 
                          OR username LIKE ? OR email LIKE ?
                    ORDER BY usage_count DESC, last_used DESC
                """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'website_name': row[1],
                        'website_url': row[2],
                        'username': row[3],
                        'email': row[4],
                        'created_at': row[5],
                        'last_used': row[6],
                        'usage_count': row[7],
                        'notes': row[8]
                    })
                
                return results
                
        except Exception as e:
            print(f"Error searching credentials: {e}")
            return []
    
    def export_credentials(self, include_passwords: bool = False) -> Dict:
        """Export credentials (for backup)"""
        try:
            credentials = []
            
            with sqlite3.connect(self.db_path) as conn:
                if include_passwords:
                    cursor = conn.execute("SELECT * FROM credentials")
                    for row in cursor.fetchall():
                        # Decrypt password for export
                        decrypted_password = self.fernet.decrypt(row[5]).decode()
                        credentials.append({
                            'website_name': row[1],
                            'website_url': row[2],
                            'username': row[3],
                            'email': row[4],
                            'password': decrypted_password,
                            'additional_fields': json.loads(row[6]) if row[6] else {},
                            'notes': row[10]
                        })
                else:
                    cursor = conn.execute("""
                        SELECT website_name, website_url, username, email, additional_fields, notes
                        FROM credentials
                    """)
                    for row in cursor.fetchall():
                        credentials.append({
                            'website_name': row[0],
                            'website_url': row[1],
                            'username': row[2],
                            'email': row[3],
                            'additional_fields': json.loads(row[4]) if row[4] else {},
                            'notes': row[5]
                        })
            
            return {
                'exported_at': datetime.now().isoformat(),
                'total_credentials': len(credentials),
                'include_passwords': include_passwords,
                'credentials': credentials
            }
            
        except Exception as e:
            print(f"Error exporting credentials: {e}")
            return {}

# Global credential manager instance
credential_manager = SecureCredentialManager()
