"""
🧠 LLM Client - Multi-Provider AI Integration
Supports LLM7, Camel AI, OpenRouter, and other providers

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
try:
    import aiohttp
except ImportError:
    aiohttp = None
import json
import os
import time
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
try:
    import yaml
except ImportError:
    yaml = None
from pathlib import Path

@dataclass
class LLMResponse:
    """LLM response data structure"""
    content: str
    provider: str
    model: str
    usage: Dict[str, int]
    response_time: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None

class LLMClient:
    """
    Multi-provider LLM client with automatic failover
    
    Supported providers:
    - LLM7 (free API)
    - Camel AI
    - OpenRouter
    - OpenAI (backup)
    """
    
    def __init__(self):
        self.providers = {}
        self.current_provider = None
        self.fallback_providers = []
        self.request_counts = {}
        self.error_counts = {}
        
        # Setup logging FIRST (before other init methods that use self.logger)
        self.logger = logging.getLogger("LLMClient")
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize providers
        self._initialize_providers()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load LLM configuration"""
        config_file = Path("config/system_config.yaml")
        
        default_config = {
            "llm": {
                "primary_provider": "openrouter",
                "providers": {
                    "openai": {
                        "enabled": True,
                        "api_key": os.getenv("OPENAI_API_KEY", ""),
                        "base_url": "https://api.openai.com/v1",
                        "models": ["gpt-3.5-turbo", "gpt-4"],
                        "rate_limit": 60
                    },
                    "anthropic": {
                        "enabled": True,
                        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
                        "base_url": "https://api.anthropic.com/v1",
                        "models": ["claude-3-sonnet", "claude-3-haiku"],
                        "rate_limit": 50
                    },
                    "openrouter": {
                        "enabled": True,
                        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                        "base_url": "https://openrouter.ai/api/v1",
                        "models": ["openai/gpt-3.5-turbo", "anthropic/claude-3-sonnet"],
                        "rate_limit": 100
                    }
                },
                "failover": {
                    "enabled": True,
                    "retry_attempts": 3,
                    "retry_delay": 5,
                    "providers_order": ["openai", "anthropic", "openrouter"]
                }
            }
        }
        
        if config_file.exists() and yaml is not None:
            try:
                with open(config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                    if user_config and 'llm' in user_config:
                        # Deep merge config
                        for key, value in user_config['llm'].items():
                            if isinstance(value, dict) and key in default_config['llm']:
                                default_config['llm'][key].update(value)
                            else:
                                default_config['llm'][key] = value
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}")
        
        return default_config['llm']
    
    def _initialize_providers(self):
        """Initialize all enabled providers"""
        for provider_name, provider_config in self.config['providers'].items():
            if provider_config.get('enabled', False):
                self.providers[provider_name] = provider_config
                self.request_counts[provider_name] = 0
                self.error_counts[provider_name] = 0
        
        # Set primary provider
        primary = self.config.get('primary_provider', 'llm7')
        if primary in self.providers:
            self.current_provider = primary
        elif self.providers:
            self.current_provider = list(self.providers.keys())[0]
        
        # Set fallback order
        self.fallback_providers = self.config.get('failover', {}).get('providers_order', [])
        
        self.logger.info(f"Initialized {len(self.providers)} LLM providers")
        self.logger.info(f"Primary provider: {self.current_provider}")
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: str = None
    ) -> LLMResponse:
        """
        Send chat completion request with automatic failover
        """
        if aiohttp is None:
            return LLMResponse(
                content="",
                provider="none",
                model="none",
                usage={},
                response_time=0,
                timestamp=datetime.now(),
                success=False,
                error="aiohttp package not installed"
            )
        
        start_time = time.time()
        
        # Determine provider
        target_provider = provider or self.current_provider
        
        if not target_provider or target_provider not in self.providers:
            return LLMResponse(
                content="",
                provider="none",
                model="none",
                usage={},
                response_time=0,
                timestamp=datetime.now(),
                success=False,
                error="No valid provider available"
            )
        
        # Try primary provider first
        response = await self._try_provider(
            target_provider, messages, model, temperature, max_tokens
        )
        
        if response.success:
            return response
        
        # Try fallback providers if enabled
        if self.config.get('failover', {}).get('enabled', True):
            for fallback_provider in self.fallback_providers:
                if fallback_provider != target_provider and fallback_provider in self.providers:
                    self.logger.info(f"Trying fallback provider: {fallback_provider}")
                    
                    response = await self._try_provider(
                        fallback_provider, messages, model, temperature, max_tokens
                    )
                    
                    if response.success:
                        # Update current provider to working one
                        self.current_provider = fallback_provider
                        return response
        
        # All providers failed
        return LLMResponse(
            content="",
            provider=target_provider,
            model=model or "unknown",
            usage={},
            response_time=time.time() - start_time,
            timestamp=datetime.now(),
            success=False,
            error="All providers failed"
        )
    
    async def _try_provider(
        self,
        provider_name: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Try a specific provider"""
        start_time = time.time()
        provider_config = self.providers[provider_name]
        
        try:
            # Prepare request - all providers use OpenAI-compatible API
            if provider_name == "openrouter":
                response = await self._openrouter_request(
                    provider_config, messages, model, temperature, max_tokens
                )
            else:
                response = await self._generic_openai_request(
                    provider_config, messages, model, temperature, max_tokens
                )
            
            self.request_counts[provider_name] += 1
            
            return LLMResponse(
                content=response.get('content', ''),
                provider=provider_name,
                model=response.get('model', model or 'unknown'),
                usage=response.get('usage', {}),
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                success=True
            )
            
        except Exception as e:
            self.error_counts[provider_name] += 1
            self.logger.error(f"Provider {provider_name} failed: {e}")
            
            return LLMResponse(
                content="",
                provider=provider_name,
                model=model or "unknown",
                usage={},
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                success=False,
                error=str(e)
            )
    
    async def _openrouter_request(
        self,
        config: Dict[str, Any],
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Make request to OpenRouter API"""
        
        api_key = config.get('api_key')
        if not api_key:
            raise Exception("OpenRouter API key not configured")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://agentic-ai.local",
            "X-Title": "Agentic AI System"
        }
        
        # Default model for OpenRouter
        if not model:
            model = config.get('models', ['openai/gpt-3.5-turbo'])[0]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        'content': data['choices'][0]['message']['content'],
                        'model': data.get('model', model),
                        'usage': data.get('usage', {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter error {response.status}: {error_text}")
    
    async def _generic_openai_request(
        self,
        config: Dict[str, Any],
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Generic OpenAI-compatible API request"""
        
        api_key = config.get('api_key')
        if not api_key:
            raise Exception("API key not configured")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model or "gpt-3.5-turbo",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return {
                        'content': data['choices'][0]['message']['content'],
                        'model': data.get('model', model),
                        'usage': data.get('usage', {})
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
    
    async def simple_prompt(self, prompt: str, model: str = None) -> str:
        """Simple prompt interface"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat_completion(messages, model=model)
        return response.content if response.success else f"Error: {response.error}"
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        stats = {}
        
        for provider_name in self.providers:
            requests = self.request_counts.get(provider_name, 0)
            errors = self.error_counts.get(provider_name, 0)
            success_rate = ((requests - errors) / requests * 100) if requests > 0 else 0
            
            stats[provider_name] = {
                "requests": requests,
                "errors": errors,
                "success_rate": round(success_rate, 2),
                "enabled": self.providers[provider_name].get('enabled', False)
            }
        
        return {
            "current_provider": self.current_provider,
            "providers": stats,
            "total_requests": sum(self.request_counts.values()),
            "total_errors": sum(self.error_counts.values())
        }
    
    def get_available_models(self, provider: str = None) -> List[str]:
        """Get available models for a provider"""
        if provider and provider in self.providers:
            return self.providers[provider].get('models', [])
        elif self.current_provider:
            return self.providers[self.current_provider].get('models', [])
        else:
            return []

# Global instance
llm_client = LLMClient()

# Test function
async def test_llm_connection():
    """Test LLM connections"""
    print("🧠 Testing LLM connections...")
    
    test_prompt = "Hello! Please respond with 'Connection successful' if you can see this message."
    
    for provider_name in llm_client.providers:
        try:
            print(f"  Testing {provider_name}...")
            response = await llm_client.chat_completion(
                messages=[{"role": "user", "content": test_prompt}],
                provider=provider_name
            )
            
            if response.success:
                print(f"  ✅ {provider_name}: {response.content[:50]}...")
            else:
                print(f"  ❌ {provider_name}: {response.error}")
        except Exception as e:
            print(f"  ❌ {provider_name}: {e}")
    
    # Test stats
    stats = llm_client.get_provider_stats()
    print(f"\n📊 LLM Stats: {stats}")

if __name__ == "__main__":
    asyncio.run(test_llm_connection())