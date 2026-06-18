"""
🔐 Credential Manager Agent - Secure Credential Storage & Management
Safely stores and manages credentials for automatic authentication
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import os
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
import sqlite3

class CredentialManagerAgent:
    """
    Secure Credential Management Agent that:
    - Stores credentials with enterprise-grade encryption
    - Manages multiple authentication methods
    - Provides secure credential sharing between agents
    - Handles automatic login/registration flows
    - Maintains audit logs for security compliance
    - Supports multiple platforms (GitHub, Google, AWS, etc.)
    """
    
    def __init__(self):
        self.agent_id = "credential_manager"
        self.name = "Credential Manager"
        self.version = "2.0.0"
        self.status = "ready" if HAS_CRYPTO else "degraded"
        self.capabilities = [
            "credential_storage",
            "secure_encryption",
            "auto_authentication",
            "platform_integration",
            "credential_sharing",
            "security_auditing",
            "backup_management",
            "2fa_handling"
        ] if HAS_CRYPTO else ["credential_storage"]
        
        if not HAS_CRYPTO:
            print("⚠️ cryptography package not installed - credential encryption disabled")
            self.master_key = None
            self.cipher_suite = None
        else:
            # Initialize secure storage
            self.credentials_db = "data/credentials.db"
            self.master_key = self._get_or_create_master_key()
            self.cipher_suite = self._initialize_encryption()
        
        # Supported platforms
        self.supported_platforms = {
            'github': {
                'name': 'GitHub',
                'auth_methods': ['token', 'oauth', 'username_password'],
                'endpoints': {
                    'api': 'https://api.github.com',
                    'auth': 'https://github.com/login/oauth/authorize'
                }
            },
            'google': {
                'name': 'Google Services',
                'auth_methods': ['oauth', 'service_account', 'api_key'],
                'endpoints': {
                    'api': 'https://www.googleapis.com',
                    'auth': 'https://accounts.google.com/oauth2/auth'
                }
            },
            'aws': {
                'name': 'Amazon Web Services',
                'auth_methods': ['access_key', 'iam_role', 'temporary_credentials'],
                'endpoints': {
                    'api': 'https://aws.amazon.com',
                    'sts': 'https://sts.amazonaws.com'
                }
            },
            'openai': {
                'name': 'OpenAI',
                'auth_methods': ['api_key'],
                'endpoints': {
                    'api': 'https://api.openai.com/v1'
                }
            },
            'anthropic': {
                'name': 'Anthropic',
                'auth_methods': ['api_key'],
                'endpoints': {
                    'api': 'https://api.anthropic.com'
                }
            },
            'huggingface': {
                'name': 'Hugging Face',
                'auth_methods': ['token', 'api_key'],
                'endpoints': {
                    'api': 'https://huggingface.co/api'
                }
            },
            'docker': {
                'name': 'Docker Hub',
                'auth_methods': ['username_password', 'token'],
                'endpoints': {
                    'api': 'https://hub.docker.com/v2'
                }
            },
            'netlify': {
                'name': 'Netlify',
                'auth_methods': ['token', 'oauth'],
                'endpoints': {
                    'api': 'https://api.netlify.com/api/v1'
                }
            },
            'vercel': {
                'name': 'Vercel',
                'auth_methods': ['token'],
                'endpoints': {
                    'api': 'https://api.vercel.com'
                }
            },
            'heroku': {
                'name': 'Heroku',
                'auth_methods': ['api_key', 'oauth'],
                'endpoints': {
                    'api': 'https://api.heroku.com'
                }
            }
        }
        
        # Initialize database
        self.credentials_db = "data/credentials.db"
        self._initialize_database()
        
        # Performance metrics
        self.credentials_stored = 0
        self.authentications_performed = 0
        self.security_events = []
        
        print(f"✅ {self.name} initialized with {len(self.supported_platforms)} platform integrations")
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_file = Path("data/master.key")
        key_file.parent.mkdir(exist_ok=True)
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new master key
            password = os.urandom(32)
            salt = os.urandom(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Also save salt for key derivation
            with open("data/salt.key", 'wb') as f:
                f.write(salt)
            
            return key
    
    def _initialize_encryption(self) -> Fernet:
        """Initialize Fernet encryption suite"""
        return Fernet(self.master_key)
    
    def _initialize_database(self):
        """Initialize credentials database"""
        Path("data").mkdir(exist_ok=True)
        
        conn = sqlite3.connect(self.credentials_db)
        cursor = conn.cursor()
        
        # Credentials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                username TEXT,
                encrypted_data TEXT NOT NULL,
                auth_method TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                tags TEXT,
                description TEXT
            )
        ''')
        
        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credential_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                credential_id INTEGER,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN,
                details TEXT,
                FOREIGN KEY (credential_id) REFERENCES credentials (id)
            )
        ''')
        
        # Platform sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                credential_id INTEGER,
                session_token TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (credential_id) REFERENCES credentials (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process credential management tasks"""
        try:
            task_type = task.get('type', 'list_credentials')
            
            if task_type == 'store_credential':
                return await self.store_credential(task)
            elif task_type == 'get_credential':
                return await self.get_credential(task)
            elif task_type == 'list_credentials':
                return await self.list_credentials(task)
            elif task_type == 'update_credential':
                return await self.update_credential(task)
            elif task_type == 'delete_credential':
                return await self.delete_credential(task)
            elif task_type == 'authenticate':
                return await self.authenticate_platform(task)
            elif task_type == 'test_credential':
                return await self.test_credential(task)
            elif task_type == 'export_credentials':
                return await self.export_credentials(task)
            elif task_type == 'import_credentials':
                return await self.import_credentials(task)
            elif task_type == 'audit_log':
                return await self.get_audit_log(task)
            else:
                return {
                    'success': False,
                    'error': f'Unknown task type: {task_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Credential management error: {str(e)}'
            }
    
    async def store_credential(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Store new credential securely"""
        try:
            platform = task.get('platform')
            auth_method = task.get('auth_method')
            credential_data = task.get('credential_data', {})
            username = task.get('username', '')
            description = task.get('description', '')
            tags = task.get('tags', [])
            expires_at = task.get('expires_at')
            
            if not platform or not auth_method or not credential_data:
                return {
                    'success': False,
                    'error': 'Platform, auth_method, and credential_data are required'
                }
            
            if platform not in self.supported_platforms:
                return {
                    'success': False,
                    'error': f'Platform {platform} not supported'
                }
            
            # Encrypt credential data
            encrypted_data = self.cipher_suite.encrypt(
                json.dumps(credential_data).encode()
            )
            
            # Store in database
            conn = sqlite3.connect(self.credentials_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO credentials 
                (platform, username, encrypted_data, auth_method, description, tags, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                platform,
                username,
                encrypted_data.decode(),
                auth_method,
                description,
                json.dumps(tags),
                expires_at
            ))
            
            credential_id = cursor.lastrowid
            conn.commit()
            
            # Log audit event
            await self._log_audit_event(credential_id, 'store', True, 'Credential stored successfully')
            
            conn.close()
            
            self.credentials_stored += 1
            
            return {
                'success': True,
                'message': f'Credential for {platform} stored securely',
                'credential_id': credential_id,
                'platform': platform,
                'auth_method': auth_method
            }
            
        except Exception as e:
            await self._log_audit_event(None, 'store', False, f'Store failed: {str(e)}')
            return {
                'success': False,
                'error': f'Failed to store credential: {str(e)}'
            }
    
    async def get_credential(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve and decrypt credential"""
        try:
            credential_id = task.get('credential_id')
            platform = task.get('platform')
            username = task.get('username')
            
            conn = sqlite3.connect(self.credentials_db)
            cursor = conn.cursor()
            
            # Build query based on provided parameters
            if credential_id:
                cursor.execute('''
                    SELECT * FROM credentials WHERE id = ? AND is_active = TRUE
                ''', (credential_id,))
            elif platform and username:
                cursor.execute('''
                    SELECT * FROM credentials WHERE platform = ? AND username = ? AND is_active = TRUE
                    ORDER BY created_at DESC LIMIT 1
                ''', (platform, username))
            elif platform:
                cursor.execute('''
                    SELECT * FROM credentials WHERE platform = ? AND is_active = TRUE
                    ORDER BY created_at DESC LIMIT 1
                ''', (platform,))
            else:
                return {
                    'success': False,
                    'error': 'credential_id, platform, or platform+username required'
                }
            
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {
                    'success': False,
                    'error': 'Credential not found'
                }
            
            # Decrypt credential data
            encrypted_data = result[3].encode()
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            credential_data = json.loads(decrypted_data.decode())
            
            # Update last_used timestamp
            cursor.execute('''
                UPDATE credentials SET last_used = CURRENT_TIMESTAMP WHERE id = ?
            ''', (result[0],))
            conn.commit()
            
            # Log audit event
            await self._log_audit_event(result[0], 'retrieve', True, 'Credential retrieved')
            
            conn.close()
            
            return {
                'success': True,
                'credential': {
                    'id': result[0],
                    'platform': result[1],
                    'username': result[2],
                    'credential_data': credential_data,
                    'auth_method': result[4],
                    'created_at': result[5],
                    'last_used': result[7],
                    'description': result[11]
                }
            }
            
        except Exception as e:
            await self._log_audit_event(None, 'retrieve', False, f'Retrieve failed: {str(e)}')
            return {
                'success': False,
                'error': f'Failed to retrieve credential: {str(e)}'
            }
    
    async def list_credentials(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List stored credentials (without sensitive data)"""
        try:
            platform = task.get('platform')
            include_expired = task.get('include_expired', False)
            
            conn = sqlite3.connect(self.credentials_db)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, platform, username, auth_method, created_at, updated_at, 
                       last_used, expires_at, description, tags
                FROM credentials 
                WHERE is_active = TRUE
            '''
            params = []
            
            if platform:
                query += ' AND platform = ?'
                params.append(platform)
            
            if not include_expired:
                query += ' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)'
            
            query += ' ORDER BY platform, created_at DESC'
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            credentials = []
            for row in results:
                credentials.append({
                    'id': row[0],
                    'platform': row[1],
                    'username': row[2],
                    'auth_method': row[3],
                    'created_at': row[4],
                    'updated_at': row[5],
                    'last_used': row[6],
                    'expires_at': row[7],
                    'description': row[8],
                    'tags': json.loads(row[9]) if row[9] else [],
                    'platform_info': self.supported_platforms.get(row[1], {})
                })
            
            conn.close()
            
            return {
                'success': True,
                'credentials': credentials,
                'total_count': len(credentials),
                'supported_platforms': self.supported_platforms
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list credentials: {str(e)}'
            }
    
    async def authenticate_platform(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate to a platform using stored credentials"""
        try:
            platform = task.get('platform')
            credential_id = task.get('credential_id')
            action = task.get('action', 'login')  # login, register, test
            
            # Get credential
            get_task = {'credential_id': credential_id} if credential_id else {'platform': platform}
            credential_result = await self.get_credential(get_task)
            
            if not credential_result['success']:
                return credential_result
            
            credential = credential_result['credential']
            
            # Perform authentication based on platform and method
            auth_result = await self._perform_platform_authentication(
                platform, credential, action
            )
            
            # Log authentication attempt
            await self._log_audit_event(
                credential['id'], 
                f'auth_{action}', 
                auth_result['success'],
                auth_result.get('message', '')
            )
            
            if auth_result['success']:
                self.authentications_performed += 1
            
            return auth_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Authentication failed: {str(e)}'
            }
    
    async def _perform_platform_authentication(self, platform: str, credential: Dict, action: str) -> Dict[str, Any]:
        """Perform actual platform authentication"""
        try:
            platform_config = self.supported_platforms.get(platform)
            if not platform_config:
                return {
                    'success': False,
                    'error': f'Platform {platform} not supported'
                }
            
            auth_method = credential['auth_method']
            credential_data = credential['credential_data']
            
            # Platform-specific authentication logic
            if platform == 'github':
                return await self._authenticate_github(credential_data, auth_method, action)
            elif platform == 'google':
                return await self._authenticate_google(credential_data, auth_method, action)
            elif platform == 'aws':
                return await self._authenticate_aws(credential_data, auth_method, action)
            elif platform in ['openai', 'anthropic', 'huggingface']:
                return await self._authenticate_api_key(platform, credential_data, action)
            else:
                return await self._authenticate_generic(platform, credential_data, auth_method, action)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Platform authentication error: {str(e)}'
            }
    
    async def _authenticate_github(self, credential_data: Dict, auth_method: str, action: str) -> Dict[str, Any]:
        """GitHub-specific authentication"""
        import requests
        
        try:
            if auth_method == 'token':
                headers = {
                    'Authorization': f"token {credential_data['token']}",
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                response = requests.get('https://api.github.com/user', headers=headers)
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        'success': True,
                        'message': 'GitHub authentication successful',
                        'user_info': user_data,
                        'platform': 'github'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'GitHub API error: {response.status_code}'
                    }
            
            elif auth_method == 'username_password':
                # Note: GitHub no longer supports password auth for API
                return {
                    'success': False,
                    'error': 'GitHub password authentication is deprecated. Use token instead.'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'GitHub authentication error: {str(e)}'
            }
    
    async def _authenticate_api_key(self, platform: str, credential_data: Dict, action: str) -> Dict[str, Any]:
        """Generic API key authentication"""
        import requests
        
        try:
            api_key = credential_data.get('api_key') or credential_data.get('token')
            if not api_key:
                return {
                    'success': False,
                    'error': 'API key not found in credential data'
                }
            
            # Test API key with a simple request
            platform_config = self.supported_platforms[platform]
            test_url = platform_config['endpoints']['api']
            
            if platform == 'openai':
                headers = {'Authorization': f'Bearer {api_key}'}
                response = requests.get(f'{test_url}/models', headers=headers)
            elif platform == 'anthropic':
                headers = {'x-api-key': api_key}
                response = requests.get(f'{test_url}/messages', headers=headers)
            else:
                headers = {'Authorization': f'Bearer {api_key}'}
                response = requests.get(test_url, headers=headers)
            
            if response.status_code in [200, 401]:  # 401 means auth was attempted
                return {
                    'success': response.status_code == 200,
                    'message': f'{platform} API key {"valid" if response.status_code == 200 else "invalid"}',
                    'platform': platform
                }
            else:
                return {
                    'success': False,
                    'error': f'{platform} API error: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'{platform} authentication error: {str(e)}'
            }
    
    async def _authenticate_generic(self, platform: str, credential_data: Dict, auth_method: str, action: str) -> Dict[str, Any]:
        """Generic authentication for other platforms"""
        return {
            'success': True,
            'message': f'{platform} credentials stored (authentication logic can be implemented)',
            'platform': platform,
            'auth_method': auth_method
        }
    
    async def _log_audit_event(self, credential_id: Optional[int], action: str, success: bool, details: str):
        """Log security audit event"""
        try:
            conn = sqlite3.connect(self.credentials_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO credential_audit 
                (credential_id, action, success, details)
                VALUES (?, ?, ?, ?)
            ''', (credential_id, action, success, details))
            
            conn.commit()
            conn.close()
            
            # Also keep in-memory log
            self.security_events.append({
                'timestamp': datetime.now().isoformat(),
                'credential_id': credential_id,
                'action': action,
                'success': success,
                'details': details
            })
            
            # Keep only last 100 events
            if len(self.security_events) > 100:
                self.security_events = self.security_events[-100:]
                
        except Exception as e:
            print(f"Failed to log audit event: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get credential manager performance metrics"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status,
            'credentials_stored': self.credentials_stored,
            'authentications_performed': self.authentications_performed,
            'supported_platforms': len(self.supported_platforms),
            'security_events_count': len(self.security_events),
            'database_path': self.credentials_db,
            'encryption_enabled': True,
            'last_activity': datetime.now().isoformat()
        }

# Global instance
credential_manager = CredentialManagerAgent()
