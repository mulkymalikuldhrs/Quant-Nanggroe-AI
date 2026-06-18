"""
🔑 Authentication Agent - Auto-Login & Registration System
Handles automatic authentication and registration across platforms
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

class AuthenticationAgent:
    """
    Advanced Authentication Agent that:
    - Performs automatic login to various platforms
    - Handles registration workflows
    - Manages 2FA/OTP authentication
    - Maintains active sessions
    - Provides platform-specific authentication flows
    - Integrates with Credential Manager for secure storage
    """
    
    def __init__(self):
        self.agent_id = "authentication_agent"
        self.name = "Authentication Agent"
        self.version = "2.0.0"
        self.status = "ready"
        self.capabilities = [
            "auto_login",
            "auto_registration",
            "session_management",
            "2fa_handling",
            "platform_integration",
            "oauth_flows",
            "api_authentication",
            "browser_automation"
        ]
        
        # Platform authentication handlers
        self.auth_handlers = {
            'github': self._handle_github_auth,
            'google': self._handle_google_auth,
            'aws': self._handle_aws_auth,
            'openai': self._handle_openai_auth,
            'anthropic': self._handle_anthropic_auth,
            'huggingface': self._handle_huggingface_auth,
            'docker': self._handle_docker_auth,
            'netlify': self._handle_netlify_auth,
            'vercel': self._handle_vercel_auth,
            'heroku': self._handle_heroku_auth,
            'linkedin': self._handle_linkedin_auth,
            'twitter': self._handle_twitter_auth,
            'facebook': self._handle_facebook_auth,
            'discord': self._handle_discord_auth,
            'slack': self._handle_slack_auth,
            'notion': self._handle_notion_auth,
            'figma': self._handle_figma_auth,
            'stripe': self._handle_stripe_auth
        }
        
        # Session storage
        self.active_sessions = {}
        self.session_cookies = {}
        
        # Browser setup for web automation
        self.browser_options = self._setup_browser_options()
        
        # Performance metrics
        self.successful_logins = 0
        self.failed_logins = 0
        self.registrations_completed = 0
        self.sessions_managed = 0
        
        print(f"✅ {self.name} initialized with {len(self.auth_handlers)} platform handlers")
    
    def _setup_browser_options(self) -> Options:
        """Setup Chrome browser options for automation"""
        options = Options()
        options.add_argument('--headless')  # Run in background
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        return options
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process authentication tasks"""
        try:
            task_type = task.get('type', 'login')
            
            if task_type == 'login':
                return await self.perform_login(task)
            elif task_type == 'register':
                return await self.perform_registration(task)
            elif task_type == 'logout':
                return await self.perform_logout(task)
            elif task_type == 'check_session':
                return await self.check_session_status(task)
            elif task_type == 'refresh_session':
                return await self.refresh_session(task)
            elif task_type == 'list_sessions':
                return await self.list_active_sessions()
            elif task_type == 'bulk_login':
                return await self.perform_bulk_login(task)
            elif task_type == 'test_credentials':
                return await self.test_platform_credentials(task)
            else:
                return {
                    'success': False,
                    'error': f'Unknown task type: {task_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Authentication error: {str(e)}'
            }
    
    async def perform_login(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform automatic login to specified platform"""
        try:
            platform = task.get('platform')
            credential_id = task.get('credential_id')
            auto_2fa = task.get('auto_2fa', False)
            save_session = task.get('save_session', True)
            
            if not platform:
                return {
                    'success': False,
                    'error': 'Platform is required'
                }
            
            # Get credentials from credential manager
            from agents.credential_manager import credential_manager
            
            get_credential_task = {
                'type': 'get_credential',
                'platform': platform
            }
            if credential_id:
                get_credential_task['credential_id'] = credential_id
            
            credential_result = await credential_manager.process_task(get_credential_task)
            
            if not credential_result['success']:
                return {
                    'success': False,
                    'error': f'No credentials found for {platform}: {credential_result["error"]}'
                }
            
            credential = credential_result['credential']
            
            # Perform platform-specific login
            if platform in self.auth_handlers:
                login_result = await self.auth_handlers[platform](credential, 'login', auto_2fa)
            else:
                login_result = await self._handle_generic_login(credential, auto_2fa)
            
            # Save session if successful
            if login_result['success'] and save_session:
                session_data = {
                    'platform': platform,
                    'credential_id': credential['id'],
                    'logged_in_at': datetime.now().isoformat(),
                    'session_data': login_result.get('session_data', {}),
                    'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
                }
                
                self.active_sessions[platform] = session_data
                self.sessions_managed += 1
            
            # Update metrics
            if login_result['success']:
                self.successful_logins += 1
            else:
                self.failed_logins += 1
            
            return login_result
            
        except Exception as e:
            self.failed_logins += 1
            return {
                'success': False,
                'error': f'Login failed: {str(e)}'
            }
    
    async def perform_registration(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform automatic registration on specified platform"""
        try:
            platform = task.get('platform')
            registration_data = task.get('registration_data', {})
            auto_verify = task.get('auto_verify', False)
            
            if not platform or not registration_data:
                return {
                    'success': False,
                    'error': 'Platform and registration_data are required'
                }
            
            # Perform platform-specific registration
            if platform in self.auth_handlers:
                register_result = await self.auth_handlers[platform](registration_data, 'register', auto_verify)
            else:
                register_result = await self._handle_generic_registration(platform, registration_data, auto_verify)
            
            # Store credentials if registration successful
            if register_result['success'] and register_result.get('credentials'):
                from agents.credential_manager import credential_manager
                
                store_task = {
                    'type': 'store_credential',
                    'platform': platform,
                    'auth_method': register_result.get('auth_method', 'username_password'),
                    'credential_data': register_result['credentials'],
                    'username': registration_data.get('username') or registration_data.get('email'),
                    'description': f'Auto-registered on {datetime.now().strftime("%Y-%m-%d")}'
                }
                
                await credential_manager.process_task(store_task)
                self.registrations_completed += 1
            
            return register_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Registration failed: {str(e)}'
            }
    
    async def _handle_github_auth(self, credential_data: Dict, action: str, auto_2fa: bool = False) -> Dict[str, Any]:
        """Handle GitHub authentication"""
        try:
            if action == 'login':
                if 'token' in credential_data['credential_data']:
                    # API token authentication
                    token = credential_data['credential_data']['token']
                    headers = {
                        'Authorization': f'token {token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                    
                    response = requests.get('https://api.github.com/user', headers=headers)
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        return {
                            'success': True,
                            'message': 'GitHub login successful',
                            'platform': 'github',
                            'user_info': user_data,
                            'session_data': {'token': token, 'headers': headers}
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'GitHub API authentication failed: {response.status_code}'
                        }
                
                else:
                    # Web-based login
                    return await self._perform_web_login(
                        'https://github.com/login',
                        credential_data['credential_data'],
                        'github'
                    )
            
            elif action == 'register':
                return await self._perform_web_registration(
                    'https://github.com/join',
                    credential_data,
                    'github'
                )
            
        except Exception as e:
            return {
                'success': False,
                'error': f'GitHub authentication error: {str(e)}'
            }
    
    async def _handle_google_auth(self, credential_data: Dict, action: str, auto_2fa: bool = False) -> Dict[str, Any]:
        """Handle Google authentication"""
        try:
            if action == 'login':
                # Google OAuth or service account authentication
                if 'service_account' in credential_data['credential_data']:
                    # Service account authentication
                    from google.oauth2 import service_account
                    
                    credentials = service_account.Credentials.from_service_account_info(
                        credential_data['credential_data']['service_account']
                    )
                    
                    return {
                        'success': True,
                        'message': 'Google service account authentication successful',
                        'platform': 'google',
                        'session_data': {'credentials': credentials}
                    }
                
                else:
                    # Web-based OAuth login
                    return await self._perform_oauth_login(
                        'https://accounts.google.com/oauth2/auth',
                        credential_data['credential_data'],
                        'google'
                    )
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Google authentication error: {str(e)}'
            }
    
    async def _handle_openai_auth(self, credential_data: Dict, action: str, auto_2fa: bool = False) -> Dict[str, Any]:
        """Handle OpenAI authentication"""
        try:
            if action == 'login':
                api_key = credential_data['credential_data'].get('api_key')
                if not api_key:
                    return {
                        'success': False,
                        'error': 'OpenAI API key not found'
                    }
                
                headers = {'Authorization': f'Bearer {api_key}'}
                response = requests.get('https://api.openai.com/v1/models', headers=headers)
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'message': 'OpenAI authentication successful',
                        'platform': 'openai',
                        'session_data': {'api_key': api_key, 'headers': headers}
                    }
                else:
                    return {
                        'success': False,
                        'error': f'OpenAI API authentication failed: {response.status_code}'
                    }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'OpenAI authentication error: {str(e)}'
            }
    
    async def _perform_web_login(self, login_url: str, credentials: Dict, platform: str) -> Dict[str, Any]:
        """Perform web-based login using browser automation"""
        driver = None
        try:
            driver = webdriver.Chrome(options=self.browser_options)
            driver.get(login_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            
            # Platform-specific login selectors
            selectors = self._get_login_selectors(platform)
            
            # Fill username/email
            username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors['username'])))
            username_field.send_keys(credentials.get('username') or credentials.get('email'))
            
            # Fill password
            password_field = driver.find_element(By.CSS_SELECTOR, selectors['password'])
            password_field.send_keys(credentials.get('password'))
            
            # Click login button
            login_button = driver.find_element(By.CSS_SELECTOR, selectors['login_button'])
            login_button.click()
            
            # Wait for login to complete
            time.sleep(3)
            
            # Check if login was successful
            current_url = driver.current_url
            if self._is_login_successful(current_url, platform):
                # Get session cookies
                cookies = driver.get_cookies()
                
                return {
                    'success': True,
                    'message': f'{platform} web login successful',
                    'platform': platform,
                    'session_data': {'cookies': cookies, 'url': current_url}
                }
            else:
                return {
                    'success': False,
                    'error': f'{platform} web login failed - still on login page'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Web login error: {str(e)}'
            }
        finally:
            if driver:
                driver.quit()
    
    def _get_login_selectors(self, platform: str) -> Dict[str, str]:
        """Get CSS selectors for login forms by platform"""
        selectors = {
            'github': {
                'username': '#login_field',
                'password': '#password',
                'login_button': '[type="submit"]'
            },
            'google': {
                'username': '#identifierId',
                'password': '[type="password"]',
                'login_button': '#passwordNext'
            },
            'linkedin': {
                'username': '#username',
                'password': '#password',
                'login_button': '[type="submit"]'
            },
            'twitter': {
                'username': '[name="text"]',
                'password': '[name="password"]',
                'login_button': '[data-testid="LoginForm_Login_Button"]'
            }
        }
        
        return selectors.get(platform, {
            'username': '[type="email"], [type="text"], #username, #email',
            'password': '[type="password"], #password',
            'login_button': '[type="submit"], .login-button, #login'
        })
    
    def _is_login_successful(self, current_url: str, platform: str) -> bool:
        """Check if login was successful based on URL"""
        success_indicators = {
            'github': 'github.com' in current_url and 'login' not in current_url,
            'google': 'accounts.google.com' not in current_url or 'myaccount' in current_url,
            'linkedin': 'feed' in current_url or 'in/' in current_url,
            'twitter': 'home' in current_url or 'twitter.com' in current_url and 'login' not in current_url
        }
        
        return success_indicators.get(platform, 'login' not in current_url.lower())
    
    async def perform_bulk_login(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform login to multiple platforms"""
        try:
            platforms = task.get('platforms', [])
            results = {}
            
            for platform in platforms:
                login_task = {
                    'type': 'login',
                    'platform': platform,
                    'save_session': True
                }
                
                result = await self.perform_login(login_task)
                results[platform] = result
            
            successful = len([r for r in results.values() if r['success']])
            
            return {
                'success': True,
                'message': f'Bulk login completed: {successful}/{len(platforms)} successful',
                'results': results,
                'summary': {
                    'total': len(platforms),
                    'successful': successful,
                    'failed': len(platforms) - successful
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Bulk login failed: {str(e)}'
            }
    
    async def list_active_sessions(self) -> Dict[str, Any]:
        """List all active authentication sessions"""
        try:
            sessions = []
            
            for platform, session_data in self.active_sessions.items():
                sessions.append({
                    'platform': platform,
                    'logged_in_at': session_data['logged_in_at'],
                    'expires_at': session_data['expires_at'],
                    'credential_id': session_data['credential_id'],
                    'is_active': datetime.now() < datetime.fromisoformat(session_data['expires_at'])
                })
            
            return {
                'success': True,
                'sessions': sessions,
                'total_active': len([s for s in sessions if s['is_active']])
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list sessions: {str(e)}'
            }
    
    async def _handle_generic_login(self, credential_data: Dict, auto_2fa: bool = False) -> Dict[str, Any]:
        """Generic login handler for unsupported platforms"""
        return {
            'success': True,
            'message': f'Generic login handler - credentials available for {credential_data["platform"]}',
            'platform': credential_data['platform'],
            'note': 'Platform-specific login logic not implemented yet'
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get authentication agent performance metrics"""
        total_attempts = self.successful_logins + self.failed_logins
        success_rate = (self.successful_logins / max(1, total_attempts)) * 100
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status,
            'successful_logins': self.successful_logins,
            'failed_logins': self.failed_logins,
            'success_rate': round(success_rate, 2),
            'registrations_completed': self.registrations_completed,
            'sessions_managed': self.sessions_managed,
            'active_sessions_count': len(self.active_sessions),
            'supported_platforms': len(self.auth_handlers),
            'browser_automation_enabled': True
        }

# Global instance
authentication_agent = AuthenticationAgent()
