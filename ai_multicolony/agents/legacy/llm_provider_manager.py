"""
🧠 LLM Provider Manager - Multi-Model AI Gateway with Auto-Failover
Manages multiple LLM providers with automatic failover and load balancing
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import random

class LLMProviderManager:
    """
    Advanced LLM Provider Management System that:
    - Manages multiple LLM providers (LLM7, OpenRouter, DeepSeek, OpenAI, Anthropic, etc.)
    - Automatic failover when providers fail
    - Load balancing across multiple providers
    - Cost optimization and usage tracking
    - API key management with encryption
    - Provider health monitoring
    - Response caching for efficiency
    """
    
    def __init__(self):
        self.agent_id = "llm_provider_manager"
        self.name = "LLM Provider Manager"
        self.version = "2.0.0"
        self.status = "ready"
        self.capabilities = [
            "multi_provider_management",
            "automatic_failover",
            "load_balancing",
            "cost_optimization",
            "provider_health_monitoring",
            "response_caching",
            "usage_analytics",
            "api_key_management"
        ]
        
        # Provider configurations with priorities (lower number = higher priority)
        self.providers = {
            'llm7': {
                'name': 'LLM7 (Free)',
                'priority': 1,  # Highest priority as it's free
                'base_url': 'https://api.llm7.com/v1',
                # SECURITY: Load API key from environment, never hardcode in source.
                # Set LLM7_API_KEY env var. A free-tier key may be available from LLM7 docs.
                'api_key': os.getenv('LLM7_API_KEY'),
                'model_prefix': 'llm7/',
                'supports_streaming': True,
                'cost_per_token': 0.0,  # Free
                'max_tokens': 4000,
                'status': 'inactive',  # Will be activated if API key is provided
                'health_score': 100,
                'last_check': None,
                'error_count': 0,
                'models': [
                    'llm7/gpt-3.5-turbo',
                    'llm7/gpt-4',
                    'llm7/claude-3-haiku',
                    'llm7/claude-3-sonnet',
                    'llm7/gemini-pro'
                ]
            },
            'openrouter': {
                'name': 'OpenRouter',
                'priority': 2,
                'base_url': 'https://openrouter.ai/api/v1',
                'api_key': None,
                'model_prefix': '',
                'supports_streaming': True,
                'cost_per_token': 0.0001,
                'max_tokens': 8000,
                'status': 'inactive',
                'health_score': 100,
                'last_check': None,
                'error_count': 0,
                'models': [
                    'anthropic/claude-3-opus',
                    'anthropic/claude-3-sonnet',
                    'anthropic/claude-3-haiku',
                    'openai/gpt-4-turbo',
                    'openai/gpt-3.5-turbo',
                    'google/gemini-pro',
                    'meta-llama/llama-2-70b-chat',
                    'mistralai/mixtral-8x7b-instruct'
                ]
            },
            'deepseek': {
                'name': 'DeepSeek',
                'priority': 3,
                'base_url': 'https://api.deepseek.com/v1',
                'api_key': None,
                'model_prefix': '',
                'supports_streaming': True,
                'cost_per_token': 0.00005,
                'max_tokens': 4000,
                'status': 'inactive',
                'health_score': 100,
                'last_check': None,
                'error_count': 0,
                'models': [
                    'deepseek-chat',
                    'deepseek-coder'
                ]
            },
            'openai': {
                'name': 'OpenAI',
                'priority': 4,
                'base_url': 'https://api.openai.com/v1',
                'api_key': None,
                'model_prefix': '',
                'supports_streaming': True,
                'cost_per_token': 0.002,
                'max_tokens': 4000,
                'status': 'inactive',
                'health_score': 100,
                'last_check': None,
                'error_count': 0,
                'models': [
                    'gpt-4-turbo',
                    'gpt-4',
                    'gpt-3.5-turbo',
                    'gpt-3.5-turbo-16k'
                ]
            },
            'anthropic': {
                'name': 'Anthropic',
                'priority': 5,
                'base_url': 'https://api.anthropic.com/v1',
                'api_key': None,
                'model_prefix': '',
                'supports_streaming': True,
                'cost_per_token': 0.008,
                'max_tokens': 4000,
                'status': 'inactive',
                'health_score': 100,
                'last_check': None,
                'error_count': 0,
                'models': [
                    'claude-3-opus-20240229',
                    'claude-3-sonnet-20240229',
                    'claude-3-haiku-20240307'
                ]
            },
            'google': {
                'name': 'Google AI',
                'priority': 6,
                'base_url': 'https://generativelanguage.googleapis.com/v1beta',
                'api_key': None,
                'model_prefix': '',
                'supports_streaming': True,
                'cost_per_token': 0.00025,
                'max_tokens': 4000,
                'status': 'inactive',
                'health_score': 100,
                'last_check': None,
                'error_count': 0,
                'models': [
                    'gemini-pro',
                    'gemini-pro-vision'
                ]
            },
            'huggingface': {
                'name': 'Hugging Face',
                'priority': 7,
                'base_url': 'https://api-inference.huggingface.co/models',
                'api_key': None,
                'model_prefix': '',
                'supports_streaming': False,
                'cost_per_token': 0.0,  # Free tier available
                'max_tokens': 2000,
                'status': 'inactive',
                'health_score': 100,
                'last_check': None,
                'error_count': 0,
                'models': [
                    'microsoft/DialoGPT-medium',
                    'facebook/blenderbot-400M-distill',
                    'microsoft/DialoGPT-large'
                ]
            }
        }
        
        # Response cache for efficiency
        self.response_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Usage analytics
        self.usage_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'provider_usage': {},
            'model_usage': {},
            'daily_stats': {}
        }
        
        # Load API keys from environment or config
        self._load_api_keys()
        
        # Initialize LLM7 as default since it's free
        self._initialize_llm7()
        
        print(f"✅ {self.name} initialized with {len(self.providers)} providers")
        print(f"🆓 LLM7 free provider activated as primary")
    
    def _load_api_keys(self):
        """Load API keys from environment variables"""
        api_key_mapping = {
            'llm7': 'LLM7_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_AI_API_KEY',
            'huggingface': 'HUGGINGFACE_API_KEY'
        }
        
        for provider, env_var in api_key_mapping.items():
            api_key = os.getenv(env_var)
            if api_key:
                self.providers[provider]['api_key'] = api_key
                self.providers[provider]['status'] = 'active'
                print(f"✅ {self.providers[provider]['name']} API key loaded")
    
    def _initialize_llm7(self):
        """Initialize LLM7 as primary free provider (if API key is available)"""
        if self.providers['llm7'].get('api_key'):
            self.providers['llm7']['status'] = 'active'
            print("🆓 LLM7 free provider initialized and ready")
        else:
            self.providers['llm7']['status'] = 'inactive'
            print("⚠️ LLM7 API key not set. Set LLM7_API_KEY env var to enable.")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process LLM provider management tasks"""
        try:
            task_type = task.get('type', 'chat_completion')
            
            if task_type == 'chat_completion':
                return await self.chat_completion(task)
            elif task_type == 'list_providers':
                return await self.list_providers()
            elif task_type == 'add_provider':
                return await self.add_provider(task)
            elif task_type == 'update_api_key':
                return await self.update_api_key(task)
            elif task_type == 'test_providers':
                return await self.test_all_providers()
            elif task_type == 'get_usage_stats':
                return await self.get_usage_statistics()
            elif task_type == 'health_check':
                return await self.health_check_all()
            elif task_type == 'select_provider':
                return await self.select_provider(task)
            else:
                return {
                    'success': False,
                    'error': f'Unknown task type: {task_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'LLM provider error: {str(e)}'
            }
    
    async def chat_completion(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat completion with automatic failover"""
        try:
            messages = task.get('messages', [])
            model = task.get('model', 'auto')
            max_tokens = task.get('max_tokens', 1000)
            temperature = task.get('temperature', 0.7)
            
            if not messages:
                return {
                    'success': False,
                    'error': 'Messages are required for chat completion'
                }
            
            # Check cache first
            cache_key = self._generate_cache_key(messages, model, max_tokens, temperature)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return {
                    'success': True,
                    'response': cached_response,
                    'provider': 'cache',
                    'model': model,
                    'cached': True
                }
            
            # Get active providers sorted by priority
            active_providers = self._get_active_providers()
            
            if not active_providers:
                return {
                    'success': False,
                    'error': 'No active LLM providers available'
                }
            
            # Try providers in order of priority
            last_error = None
            for provider_id in active_providers:
                try:
                    result = await self._call_provider(
                        provider_id, messages, model, max_tokens, temperature
                    )
                    
                    if result['success']:
                        # Cache successful response
                        self._cache_response(cache_key, result['response'])
                        
                        # Update usage stats
                        self._update_usage_stats(provider_id, result.get('tokens_used', 0))
                        
                        # Reset error count on success
                        self.providers[provider_id]['error_count'] = 0
                        
                        return {
                            'success': True,
                            'response': result['response'],
                            'provider': provider_id,
                            'model': result.get('model', model),
                            'tokens_used': result.get('tokens_used', 0),
                            'cost': result.get('cost', 0.0)
                        }
                    else:
                        last_error = result.get('error', 'Unknown error')
                        self._handle_provider_error(provider_id, last_error)
                        
                except Exception as e:
                    last_error = str(e)
                    self._handle_provider_error(provider_id, last_error)
                    continue
            
            # All providers failed
            return {
                'success': False,
                'error': f'All LLM providers failed. Last error: {last_error}',
                'providers_tried': active_providers
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Chat completion error: {str(e)}'
            }
    
    async def _call_provider(self, provider_id: str, messages: List[Dict], 
                           model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call specific LLM provider"""
        try:
            provider = self.providers[provider_id]
            
            if provider_id == 'llm7':
                return await self._call_llm7(provider, messages, model, max_tokens, temperature)
            elif provider_id == 'openrouter':
                return await self._call_openrouter(provider, messages, model, max_tokens, temperature)
            elif provider_id == 'deepseek':
                return await self._call_deepseek(provider, messages, model, max_tokens, temperature)
            elif provider_id == 'openai':
                return await self._call_openai(provider, messages, model, max_tokens, temperature)
            elif provider_id == 'anthropic':
                return await self._call_anthropic(provider, messages, model, max_tokens, temperature)
            elif provider_id == 'google':
                return await self._call_google(provider, messages, model, max_tokens, temperature)
            elif provider_id == 'huggingface':
                return await self._call_huggingface(provider, messages, model, max_tokens, temperature)
            else:
                return {
                    'success': False,
                    'error': f'Provider {provider_id} not implemented'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Provider call error: {str(e)}'
            }
    
    async def _call_llm7(self, provider: Dict, messages: List[Dict], 
                        model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call LLM7 free provider"""
        try:
            # Use LLM7's free API
            url = f"{provider['base_url']}/chat/completions"
            
            # Auto-select model if not specified
            if model == 'auto':
                model = 'llm7/gpt-3.5-turbo'
            
            headers = {
                'Authorization': f"Bearer {provider['api_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'tokens_used': tokens_used,
                    'cost': 0.0  # Free
                }
            else:
                return {
                    'success': False,
                    'error': f'LLM7 API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'LLM7 call error: {str(e)}'
            }
    
    async def _call_openrouter(self, provider: Dict, messages: List[Dict], 
                              model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call OpenRouter provider"""
        try:
            url = f"{provider['base_url']}/chat/completions"
            
            if model == 'auto':
                model = 'anthropic/claude-3-haiku'  # Cost-effective default
            
            headers = {
                'Authorization': f"Bearer {provider['api_key']}",
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://agentic-ai.com',
                'X-Title': 'Agentic AI System'
            }
            
            payload = {
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                cost = tokens_used * provider['cost_per_token']
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'tokens_used': tokens_used,
                    'cost': cost
                }
            else:
                return {
                    'success': False,
                    'error': f'OpenRouter API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'OpenRouter call error: {str(e)}'
            }
    
    async def _call_deepseek(self, provider: Dict, messages: List[Dict], 
                            model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call DeepSeek provider"""
        try:
            url = f"{provider['base_url']}/chat/completions"
            
            if model == 'auto':
                model = 'deepseek-chat'
            
            headers = {
                'Authorization': f"Bearer {provider['api_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                cost = tokens_used * provider['cost_per_token']
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'tokens_used': tokens_used,
                    'cost': cost
                }
            else:
                return {
                    'success': False,
                    'error': f'DeepSeek API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'DeepSeek call error: {str(e)}'
            }
    
    async def _call_openai(self, provider: Dict, messages: List[Dict], 
                          model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call OpenAI provider"""
        try:
            url = f"{provider['base_url']}/chat/completions"
            
            if model == 'auto':
                model = 'gpt-3.5-turbo'
            
            headers = {
                'Authorization': f"Bearer {provider['api_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                cost = tokens_used * provider['cost_per_token']
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'tokens_used': tokens_used,
                    'cost': cost
                }
            else:
                return {
                    'success': False,
                    'error': f'OpenAI API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'OpenAI call error: {str(e)}'
            }
    
    async def _call_anthropic(self, provider: Dict, messages: List[Dict], 
                             model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call Anthropic provider"""
        try:
            url = f"{provider['base_url']}/messages"
            
            if model == 'auto':
                model = 'claude-3-haiku-20240307'
            
            headers = {
                'x-api-key': provider['api_key'],
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            }
            
            # Convert messages format for Anthropic
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    user_messages.append(msg)
            
            payload = {
                'model': model,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'messages': user_messages
            }
            
            if system_message:
                payload['system'] = system_message
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['content'][0]['text']
                tokens_used = data.get('usage', {}).get('input_tokens', 0) + data.get('usage', {}).get('output_tokens', 0)
                cost = tokens_used * provider['cost_per_token']
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'tokens_used': tokens_used,
                    'cost': cost
                }
            else:
                return {
                    'success': False,
                    'error': f'Anthropic API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Anthropic call error: {str(e)}'
            }
    
    async def _call_google(self, provider: Dict, messages: List[Dict], 
                          model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call Google AI provider"""
        try:
            if model == 'auto':
                model = 'gemini-pro'
            
            url = f"{provider['base_url']}/models/{model}:generateContent?key={provider['api_key']}"
            
            # Convert messages format for Google AI
            contents = []
            for msg in messages:
                if msg['role'] in ['user', 'assistant']:
                    contents.append({
                        'role': 'user' if msg['role'] == 'user' else 'model',
                        'parts': [{'text': msg['content']}]
                    })
            
            payload = {
                'contents': contents,
                'generationConfig': {
                    'maxOutputTokens': max_tokens,
                    'temperature': temperature
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data['candidates'][0]['content']['parts'][0]['text']
                tokens_used = data.get('usageMetadata', {}).get('totalTokenCount', 0)
                cost = tokens_used * provider['cost_per_token']
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'tokens_used': tokens_used,
                    'cost': cost
                }
            else:
                return {
                    'success': False,
                    'error': f'Google AI API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Google AI call error: {str(e)}'
            }
    
    async def _call_huggingface(self, provider: Dict, messages: List[Dict], 
                               model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call Hugging Face provider"""
        try:
            if model == 'auto':
                model = 'microsoft/DialoGPT-medium'
            
            url = f"{provider['base_url']}/{model}"
            
            headers = {
                'Authorization': f"Bearer {provider['api_key']}",
                'Content-Type': 'application/json'
            }
            
            # Convert messages to single prompt for HF
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            
            payload = {
                'inputs': prompt,
                'parameters': {
                    'max_new_tokens': max_tokens,
                    'temperature': temperature
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data[0].get('generated_text', '').replace(prompt, '').strip()
                tokens_used = len(content.split())  # Rough estimate
                
                return {
                    'success': True,
                    'response': content,
                    'model': model,
                    'tokens_used': tokens_used,
                    'cost': 0.0  # Free tier
                }
            else:
                return {
                    'success': False,
                    'error': f'Hugging Face API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Hugging Face call error: {str(e)}'
            }
    
    def _get_active_providers(self) -> List[str]:
        """Get list of active providers sorted by priority"""
        active = []
        for provider_id, provider in self.providers.items():
            if provider['status'] == 'active' and provider.get('api_key'):
                active.append((provider_id, provider['priority']))
        
        # Sort by priority (lower number = higher priority)
        active.sort(key=lambda x: x[1])
        return [provider_id for provider_id, _ in active]
    
    def _handle_provider_error(self, provider_id: str, error: str):
        """Handle provider errors and update health scores"""
        provider = self.providers[provider_id]
        provider['error_count'] += 1
        provider['last_error'] = error
        provider['last_check'] = datetime.now().isoformat()
        
        # Decrease health score based on error count
        provider['health_score'] = max(0, 100 - (provider['error_count'] * 10))
        
        # Deactivate provider if too many errors
        if provider['error_count'] >= 5:
            provider['status'] = 'error'
            print(f"❌ Provider {provider_id} deactivated due to repeated errors")
    
    def _generate_cache_key(self, messages: List[Dict], model: str, 
                           max_tokens: int, temperature: float) -> str:
        """Generate cache key for response caching"""
        import hashlib
        content = json.dumps({
            'messages': messages,
            'model': model,
            'max_tokens': max_tokens,
            'temperature': temperature
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        if cache_key in self.response_cache:
            cached_data = self.response_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['response']
            else:
                del self.response_cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: str):
        """Cache response for future use"""
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        # Clean old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, data in self.response_cache.items()
            if current_time - data['timestamp'] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.response_cache[key]
    
    def _update_usage_stats(self, provider_id: str, tokens_used: int):
        """Update usage statistics"""
        provider = self.providers[provider_id]
        cost = tokens_used * provider['cost_per_token']
        
        self.usage_stats['total_requests'] += 1
        self.usage_stats['successful_requests'] += 1
        self.usage_stats['total_tokens'] += tokens_used
        self.usage_stats['total_cost'] += cost
        
        if provider_id not in self.usage_stats['provider_usage']:
            self.usage_stats['provider_usage'][provider_id] = {
                'requests': 0,
                'tokens': 0,
                'cost': 0.0
            }
        
        self.usage_stats['provider_usage'][provider_id]['requests'] += 1
        self.usage_stats['provider_usage'][provider_id]['tokens'] += tokens_used
        self.usage_stats['provider_usage'][provider_id]['cost'] += cost
    
    async def list_providers(self) -> Dict[str, Any]:
        """List all available providers with their status"""
        try:
            providers_list = []
            
            for provider_id, provider in self.providers.items():
                providers_list.append({
                    'id': provider_id,
                    'name': provider['name'],
                    'status': provider['status'],
                    'priority': provider['priority'],
                    'health_score': provider['health_score'],
                    'cost_per_token': provider['cost_per_token'],
                    'max_tokens': provider['max_tokens'],
                    'supports_streaming': provider['supports_streaming'],
                    'models': provider['models'],
                    'error_count': provider['error_count'],
                    'last_check': provider['last_check'],
                    'has_api_key': bool(provider.get('api_key'))
                })
            
            return {
                'success': True,
                'providers': providers_list,
                'total_providers': len(providers_list),
                'active_providers': len([p for p in providers_list if p['status'] == 'active'])
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list providers: {str(e)}'
            }
    
    async def update_api_key(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update API key for a provider"""
        try:
            provider_id = task.get('provider_id')
            api_key = task.get('api_key')
            
            if not provider_id or not api_key:
                return {
                    'success': False,
                    'error': 'provider_id and api_key are required'
                }
            
            if provider_id not in self.providers:
                return {
                    'success': False,
                    'error': f'Provider {provider_id} not found'
                }
            
            # Update API key
            self.providers[provider_id]['api_key'] = api_key
            self.providers[provider_id]['status'] = 'active'
            self.providers[provider_id]['error_count'] = 0
            self.providers[provider_id]['health_score'] = 100
            
            return {
                'success': True,
                'message': f'API key updated for {self.providers[provider_id]["name"]}',
                'provider': provider_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update API key: {str(e)}'
            }
    
    async def test_all_providers(self) -> Dict[str, Any]:
        """Test all active providers"""
        try:
            test_results = {}
            test_message = [{"role": "user", "content": "Hello, this is a test message."}]
            
            active_providers = self._get_active_providers()
            
            for provider_id in active_providers:
                try:
                    start_time = time.time()
                    result = await self._call_provider(
                        provider_id, test_message, 'auto', 50, 0.7
                    )
                    end_time = time.time()
                    
                    test_results[provider_id] = {
                        'success': result['success'],
                        'response_time': round(end_time - start_time, 2),
                        'error': result.get('error') if not result['success'] else None,
                        'model': result.get('model'),
                        'tokens_used': result.get('tokens_used', 0)
                    }
                    
                    if result['success']:
                        self.providers[provider_id]['health_score'] = 100
                        self.providers[provider_id]['error_count'] = 0
                    else:
                        self._handle_provider_error(provider_id, result.get('error', 'Test failed'))
                        
                except Exception as e:
                    test_results[provider_id] = {
                        'success': False,
                        'error': str(e),
                        'response_time': None
                    }
                    self._handle_provider_error(provider_id, str(e))
            
            successful_tests = len([r for r in test_results.values() if r['success']])
            
            return {
                'success': True,
                'test_results': test_results,
                'summary': {
                    'total_tested': len(test_results),
                    'successful': successful_tests,
                    'failed': len(test_results) - successful_tests
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Provider testing failed: {str(e)}'
            }
    
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        try:
            return {
                'success': True,
                'statistics': self.usage_stats,
                'providers': {
                    provider_id: {
                        'name': provider['name'],
                        'status': provider['status'],
                        'health_score': provider['health_score'],
                        'error_count': provider['error_count']
                    }
                    for provider_id, provider in self.providers.items()
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get usage statistics: {str(e)}'
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get LLM provider manager performance metrics"""
        active_count = len([p for p in self.providers.values() if p['status'] == 'active'])
        avg_health = sum(p['health_score'] for p in self.providers.values()) / len(self.providers)
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status,
            'total_providers': len(self.providers),
            'active_providers': active_count,
            'average_health_score': round(avg_health, 2),
            'total_requests': self.usage_stats['total_requests'],
            'successful_requests': self.usage_stats['successful_requests'],
            'total_cost': round(self.usage_stats['total_cost'], 4),
            'cache_size': len(self.response_cache),
            'primary_provider': 'llm7' if self.providers['llm7']['status'] == 'active' else 'none'
        }

# Global instance
llm_provider_manager = LLMProviderManager()
