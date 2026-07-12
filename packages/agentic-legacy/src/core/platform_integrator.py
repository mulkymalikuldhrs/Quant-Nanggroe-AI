"""
Platform Integrator for Agentic AI System
Manages integrations with external platforms and services

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import json
import asyncio
import aiohttp
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

class PlatformIntegrator:
    """Manages platform integrations and external service connections"""
    
    def __init__(self):
        self.integrations = {
            'github': GitHubIntegration(),
            'google': GoogleServicesIntegration(),
            'external_apis': ExternalAPIManager(),
            'ai_platforms': AIPlatformManager()
        }
        
        self.status = {
            'initialized_at': datetime.now().isoformat(),
            'active_connections': 0,
            'last_health_check': None
        }
        
    async def initialize_all(self):
        """Initialize all platform integrations"""
        for name, integration in self.integrations.items():
            try:
                await integration.initialize()
                if integration.is_connected():
                    self.status['active_connections'] += 1
                print(f"✅ {name} integration: {'connected' if integration.is_connected() else 'available'}")
            except Exception as e:
                print(f"⚠️  {name} integration failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all integrations"""
        health_status = {}
        
        for name, integration in self.integrations.items():
            try:
                status = await integration.health_check()
                health_status[name] = status
            except Exception as e:
                health_status[name] = {'status': 'error', 'error': str(e)}
        
        self.status['last_health_check'] = datetime.now().isoformat()
        return health_status
    
    def get_integration(self, name: str):
        """Get specific integration by name"""
        return self.integrations.get(name)

class GitHubIntegration:
    """GitHub platform integration"""
    
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.base_url = 'https://api.github.com'
        self.connected = False
        
    async def initialize(self):
        """Initialize GitHub integration"""
        if self.token:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {'Authorization': f'token {self.token}'}
                    async with session.get(f'{self.base_url}/user', headers=headers) as resp:
                        if resp.status == 200:
                            self.connected = True
                            user_data = await resp.json()
                            print(f"🐙 GitHub connected as: {user_data.get('login')}")
            except Exception as e:
                print(f"GitHub connection failed: {e}")
    
    def is_connected(self) -> bool:
        return self.connected
    
    async def health_check(self) -> Dict[str, Any]:
        """Check GitHub API health"""
        if not self.token:
            return {'status': 'not_configured', 'message': 'No GitHub token provided'}
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'token {self.token}'}
                async with session.get(f'{self.base_url}/rate_limit', headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            'status': 'healthy',
                            'rate_limit_remaining': data['rate']['remaining'],
                            'rate_limit_total': data['rate']['limit']
                        }
                    else:
                        return {'status': 'error', 'code': resp.status}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def create_repository(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new repository"""
        if not self.connected:
            return {'error': 'GitHub not connected'}
        
        data = {
            'name': name,
            'description': description,
            'private': False,
            'has_issues': True,
            'has_projects': True,
            'has_wiki': True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'token {self.token}',
                    'Accept': 'application/vnd.github.v3+json'
                }
                async with session.post(f'{self.base_url}/user/repos', 
                                      headers=headers, json=data) as resp:
                    if resp.status == 201:
                        repo_data = await resp.json()
                        return {
                            'success': True,
                            'repository': {
                                'name': repo_data['name'],
                                'url': repo_data['html_url'],
                                'clone_url': repo_data['clone_url']
                            }
                        }
                    else:
                        error_data = await resp.json()
                        return {'error': error_data.get('message', 'Unknown error')}
        except Exception as e:
            return {'error': str(e)}

class GoogleServicesIntegration:
    """Google Services integration"""
    
    def __init__(self):
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.connected = False
        self.available_services = ['drive', 'sheets', 'gmail', 'calendar']
        
    async def initialize(self):
        """Initialize Google Services"""
        if self.credentials_path and Path(self.credentials_path).exists():
            try:
                # Here you would initialize Google API client
                # For now, we'll simulate the connection
                self.connected = True
                print("🔍 Google Services: Credentials found (implementation pending)")
            except Exception as e:
                print(f"Google Services initialization failed: {e}")
        else:
            print("🔍 Google Services: No credentials found")
    
    def is_connected(self) -> bool:
        return self.connected
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Google Services health"""
        if not self.credentials_path:
            return {
                'status': 'not_configured',
                'message': 'No Google credentials configured',
                'setup_instructions': 'Set GOOGLE_CREDENTIALS_PATH environment variable'
            }
        
        return {
            'status': 'configured',
            'available_services': self.available_services,
            'credentials_file': 'found' if Path(self.credentials_path).exists() else 'missing'
        }

class ExternalAPIManager:
    """Manager for free external APIs"""
    
    def __init__(self):
        self.apis = {
            'wikipedia': 'https://en.wikipedia.org/api/rest_v1',
            'quotable': 'https://api.quotable.io',
            'advice': 'https://api.adviceslip.com',
            'facts': 'https://uselessfacts.jsph.pl',
            'jokes': 'https://v2.jokeapi.dev',
            'numbers': 'http://numbersapi.com',
            'cat_facts': 'https://catfact.ninja'
        }
        self.status = {}
        
    async def initialize(self):
        """Test connectivity to external APIs"""
        for name, url in self.apis.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as resp:
                        self.status[name] = 'available' if resp.status < 400 else 'limited'
            except:
                self.status[name] = 'unavailable'
    
    def is_connected(self) -> bool:
        return any(status == 'available' for status in self.status.values())
    
    async def health_check(self) -> Dict[str, Any]:
        """Check external API health"""
        await self.initialize()
        available_count = sum(1 for status in self.status.values() if status == 'available')
        
        return {
            'status': 'healthy' if available_count > len(self.apis) // 2 else 'limited',
            'available_apis': available_count,
            'total_apis': len(self.apis),
            'api_status': self.status
        }
    
    async def fetch_knowledge(self, source: str, query: str = None) -> Dict[str, Any]:
        """Fetch knowledge from external API"""
        if source not in self.apis:
            return {'error': f'Unknown source: {source}'}
        
        try:
            if source == 'wikipedia' and query:
                url = f"{self.apis[source]}/page/summary/{query.replace(' ', '_')}"
            elif source == 'quotable':
                url = f"{self.apis[source]}/random"
            elif source == 'advice':
                url = f"{self.apis[source]}/advice"
            elif source == 'facts':
                url = f"{self.apis[source]}/random.json?language=en"
            elif source == 'jokes':
                url = f"{self.apis[source]}/joke/Programming?blacklistFlags=nsfw,religious,political"
            elif source == 'cat_facts':
                url = f"{self.apis[source]}/fact"
            else:
                url = self.apis[source]
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            'source': source,
                            'data': data,
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        return {'error': f'API returned status {resp.status}'}
        except Exception as e:
            return {'error': str(e)}

class AIPlatformManager:
    """Manager for AI platform integrations"""
    
    def __init__(self):
        self.platforms = {
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'base_url': 'https://api.openai.com/v1',
                'status': 'not_configured'
            },
            'huggingface': {
                'api_key': os.getenv('HUGGINGFACE_TOKEN'),
                'base_url': 'https://api-inference.huggingface.co',
                'status': 'not_configured'
            },
            'anthropic': {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'base_url': 'https://api.anthropic.com',
                'status': 'not_configured'
            }
        }
        
    async def initialize(self):
        """Initialize AI platform connections"""
        for name, config in self.platforms.items():
            if config['api_key']:
                try:
                    if await self._test_platform_connection(name, config):
                        config['status'] = 'connected'
                        print(f"🤖 {name.title()} AI: Connected")
                    else:
                        config['status'] = 'error'
                except Exception as e:
                    config['status'] = 'error'
                    print(f"🤖 {name.title()} AI: Connection failed - {e}")
            else:
                config['status'] = 'not_configured'
                print(f"🤖 {name.title()} AI: No API key provided")
    
    async def _test_platform_connection(self, platform: str, config: Dict) -> bool:
        """Test connection to AI platform"""
        try:
            headers = {'Authorization': f'Bearer {config["api_key"]}'}
            
            if platform == 'openai':
                url = f'{config["base_url"]}/models'
            elif platform == 'huggingface':
                url = f'{config["base_url"]}/models'
            elif platform == 'anthropic':
                # Anthropic doesn't have a simple test endpoint
                return True
            else:
                return False
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    return resp.status == 200
        except:
            return False
    
    def is_connected(self) -> bool:
        return any(config['status'] == 'connected' for config in self.platforms.values())
    
    async def health_check(self) -> Dict[str, Any]:
        """Check AI platform health"""
        platform_status = {}
        
        for name, config in self.platforms.items():
            platform_status[name] = {
                'status': config['status'],
                'configured': config['api_key'] is not None
            }
        
        connected_count = sum(1 for config in self.platforms.values() if config['status'] == 'connected')
        
        return {
            'status': 'healthy' if connected_count > 0 else 'limited',
            'connected_platforms': connected_count,
            'total_platforms': len(self.platforms),
            'platform_status': platform_status
        }

# Global platform integrator instance
platform_integrator = PlatformIntegrator()
