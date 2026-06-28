"""
🧠 LLM Gateway - Multi-LLM API Integration
Support for LLM7, OpenRouter, CAMEL, and other LLM providers

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
try:
    import aiohttp
except ImportError:
    aiohttp = None
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class LLMGateway:
    """
    Universal LLM Gateway supporting multiple providers:
    - LLM7 (Primary)
    - OpenRouter
    - CAMEL 
    - OpenAI
    - Anthropic
    - Local models
    """
    
    def __init__(self):
        self.providers = {
            "llm7": {
                "base_url": "https://api.llm7.com/v1",
                "api_key": os.getenv("LLM7_API_KEY"),  # Set LLM7_API_KEY env var
                "models": ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet"],
                "priority": 1,
                "rate_limit": 60,  # requests per minute
                "status": "active",
                "free_tier": True
            },
            "openrouter": {
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "models": ["anthropic/claude-3-sonnet", "meta-llama/llama-3-70b-instruct"],
                "priority": 2,
                "rate_limit": 30,
                "status": "available"
            },
            "camel": {
                "base_url": "https://api.camel-ai.org/v1",
                "api_key": os.getenv("CAMEL_API_KEY"),
                "models": ["camel-chat", "camel-agent"],
                "priority": 3,
                "rate_limit": 20,
                "status": "available"
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "models": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
                "priority": 4,
                "rate_limit": 50,
                "status": "fallback"
            },
            "local": {
                "base_url": "http://localhost:11434/v1",
                "api_key": "local",
                "models": ["llama3", "codellama", "mistral"],
                "priority": 5,
                "rate_limit": 100,
                "status": "optional"
            }
        }
        
        # Usage tracking
        self.usage_stats = {}
        self.rate_limits = {}
        self.last_requests = {}
        
        # Response cache
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Initialize provider status
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize and test provider connections"""
        for provider_name, config in self.providers.items():
            if config["api_key"] and config["api_key"] != "your-api-key":
                self.usage_stats[provider_name] = {
                    "requests": 0,
                    "errors": 0,
                    "total_tokens": 0,
                    "last_used": None
                }
                self.rate_limits[provider_name] = []
                logger.info("%s provider initialized", provider_name.upper())
            else:
                self.providers[provider_name]["status"] = "disabled"
                logger.warning("%s provider disabled (no API key)", provider_name.upper())
    
    async def chat_completion(self, messages: List[Dict], model: str = "auto", 
                             provider: str = "auto", **kwargs) -> Dict[str, Any]:
        """
        Universal chat completion across all providers
        """
        if aiohttp is None:
            raise Exception("aiohttp package not installed - cannot make LLM requests")
        
        # Select optimal provider and model
        selected_provider, selected_model = self._select_provider_and_model(provider, model)
        
        if not selected_provider:
            raise Exception("No available LLM providers")
        
        # Check cache first
        cache_key = self._generate_cache_key(messages, selected_model, kwargs)
        cached_response = self._get_cached_response(cache_key)
        
        if cached_response:
            logger.info("Cache hit for %s/%s", selected_provider, selected_model)
            return cached_response
        
        # Check rate limits
        if not self._check_rate_limit(selected_provider):
            # Try alternative provider
            alternative = self._get_alternative_provider(selected_provider)
            if alternative:
                selected_provider = alternative
            else:
                raise Exception(f"Rate limit exceeded for {selected_provider}")
        
        try:
            # Make API request
            response = await self._make_llm_request(
                selected_provider, selected_model, messages, **kwargs
            )
            
            # Cache successful response
            self._cache_response(cache_key, response)
            
            # Update usage stats
            self._update_usage_stats(selected_provider, response)
            
            return response
            
        except Exception as e:
            # Handle errors and retry with fallback
            logger.error("Error with %s: %s", selected_provider, e)
            
            fallback_provider = self._get_fallback_provider(selected_provider)
            if fallback_provider:
                logger.info("Retrying with fallback provider: %s", fallback_provider)
                return await self._make_llm_request(
                    fallback_provider, "auto", messages, **kwargs
                )
            
            raise e
    
    def _select_provider_and_model(self, provider: str, model: str) -> tuple:
        """Select optimal provider and model"""
        
        if provider != "auto":
            # Use specified provider
            if provider in self.providers and self.providers[provider]["status"] != "disabled":
                if model == "auto":
                    model = self.providers[provider]["models"][0]
                return provider, model
            else:
                raise Exception(f"Provider {provider} not available")
        
        # Auto-select based on priority and availability
        available_providers = [
            (name, config) for name, config in self.providers.items()
            if config["status"] in ["active", "available"] and config["api_key"]
        ]
        
        # Sort by priority
        available_providers.sort(key=lambda x: x[1]["priority"])
        
        if not available_providers:
            return None, None
        
        selected_provider_name = available_providers[0][0]
        selected_config = available_providers[0][1]
        
        # Select model
        if model == "auto":
            if model.startswith("llm7"):
                selected_model = selected_config["models"][0]
            else:
                selected_model = selected_config["models"][0]
        else:
            selected_model = model
        
        return selected_provider_name, selected_model
    
    async def _make_llm_request(self, provider: str, model: str, 
                               messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Make API request to specific LLM provider"""
        
        config = self.providers[provider]
        
        # Prepare request data
        request_data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": kwargs.get("stream", False)
        }
        
        # Provider-specific adjustments
        if provider == "llm7":
            request_data["model"] = "llm7-chat"
        elif provider == "openrouter":
            request_data["model"] = model if model != "auto" else "anthropic/claude-3-sonnet"
        elif provider == "camel":
            request_data["model"] = "camel-chat"
        elif provider == "local":
            request_data["model"] = model if model != "auto" else "llama3"
        
        # Make HTTP request
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        # Add provider-specific headers
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://agentic-ai-system.com"
            headers["X-Title"] = "Agentic AI System"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Standardize response format
                    return self._standardize_response(result, provider)
                else:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
    
    def _standardize_response(self, response: Dict, provider: str) -> Dict[str, Any]:
        """Standardize response format across providers"""
        
        # Most providers follow OpenAI format, but add provider info
        standardized = {
            **response,
            "provider": provider,
            "timestamp": datetime.now().isoformat()
        }
        
        # Provider-specific adjustments
        if provider == "camel":
            # CAMEL might have different response format
            if "response" in response:
                standardized["choices"] = [{
                    "message": {
                        "role": "assistant",
                        "content": response["response"]
                    },
                    "finish_reason": "stop"
                }]
        
        return standardized
    
    def _check_rate_limit(self, provider: str) -> bool:
        """Check if provider is within rate limits"""
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Clean old requests
        if provider in self.rate_limits:
            self.rate_limits[provider] = [
                req_time for req_time in self.rate_limits[provider]
                if req_time > minute_ago
            ]
            
            # Check if under limit
            return len(self.rate_limits[provider]) < self.providers[provider]["rate_limit"]
        
        return True
    
    def _update_rate_limit(self, provider: str):
        """Update rate limit tracking"""
        if provider not in self.rate_limits:
            self.rate_limits[provider] = []
        
        self.rate_limits[provider].append(time.time())
    
    def _get_alternative_provider(self, current_provider: str) -> Optional[str]:
        """Get alternative provider when current is rate limited"""
        available = [
            name for name, config in self.providers.items()
            if (name != current_provider and 
                config["status"] in ["active", "available"] and
                self._check_rate_limit(name))
        ]
        
        if available:
            # Return highest priority available
            return min(available, key=lambda x: self.providers[x]["priority"])
        
        return None
    
    def _get_fallback_provider(self, failed_provider: str) -> Optional[str]:
        """Get fallback provider when current fails"""
        fallbacks = ["openai", "llm7", "local"]
        
        for fallback in fallbacks:
            if (fallback != failed_provider and 
                fallback in self.providers and
                self.providers[fallback]["status"] != "disabled"):
                return fallback
        
        return None
    
    def _generate_cache_key(self, messages: List[Dict], model: str, kwargs: Dict) -> str:
        """Generate cache key for request"""
        cache_data = {
            "messages": messages,
            "model": model,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048)
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()[:32]
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if available and not expired"""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                return cached_data["response"]
            else:
                del self.cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: Dict):
        """Cache successful response"""
        self.cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }
        
        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k]["timestamp"]
            )[:100]
            
            for key in oldest_keys:
                del self.cache[key]
    
    def _update_usage_stats(self, provider: str, response: Dict):
        """Update usage statistics"""
        if provider not in self.usage_stats:
            self.usage_stats[provider] = {
                "requests": 0,
                "errors": 0,
                "total_tokens": 0,
                "last_used": None
            }
        
        stats = self.usage_stats[provider]
        stats["requests"] += 1
        stats["last_used"] = datetime.now().isoformat()
        
        # Update rate limit tracking
        self._update_rate_limit(provider)
        
        # Track token usage if available
        if "usage" in response:
            stats["total_tokens"] += response["usage"].get("total_tokens", 0)
    
    async def generate_text(self, prompt: str, model: str = "auto", 
                           provider: str = "auto", **kwargs) -> str:
        """Simple text generation interface"""
        
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat_completion(messages, model, provider, **kwargs)
        
        if "choices" in response and response["choices"]:
            return response["choices"][0]["message"]["content"]
        
        return ""
    
    async def generate_code(self, description: str, language: str = "python", 
                           model: str = "auto") -> str:
        """Code generation with specialized prompting"""
        
        code_prompt = f"""
        Generate {language} code for the following requirement:
        
        {description}
        
        Requirements:
        - Write clean, well-commented code
        - Follow best practices for {language}
        - Include error handling where appropriate
        - Make the code modular and reusable
        
        Return only the code without explanation.
        """
        
        # Prefer code-specialized models
        if model == "auto":
            # Try to use code-specific models
            for provider, config in self.providers.items():
                if "code" in str(config["models"]) and config["status"] != "disabled":
                    model = [m for m in config["models"] if "code" in m][0]
                    break
        
        return await self.generate_text(code_prompt, model=model, temperature=0.2)
    
    async def analyze_and_summarize(self, text: str, analysis_type: str = "general") -> str:
        """Text analysis and summarization"""
        
        analysis_prompts = {
            "general": "Analyze and summarize the following text, highlighting key points:",
            "technical": "Provide a technical analysis of the following content, focusing on implementation details:",
            "business": "Analyze from a business perspective, focusing on value and impact:",
            "security": "Analyze from a security perspective, identifying potential risks and recommendations:"
        }
        
        prompt = f"{analysis_prompts.get(analysis_type, analysis_prompts['general'])}\n\n{text}"
        
        return await self.generate_text(prompt, temperature=0.3)
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all LLM providers"""
        status = {}
        
        for provider_name, config in self.providers.items():
            stats = self.usage_stats.get(provider_name, {})
            
            status[provider_name] = {
                "status": config["status"],
                "priority": config["priority"],
                "models": config["models"],
                "rate_limit": config["rate_limit"],
                "requests_made": stats.get("requests", 0),
                "errors": stats.get("errors", 0),
                "total_tokens": stats.get("total_tokens", 0),
                "last_used": stats.get("last_used"),
                "current_rate_limit_usage": len(self.rate_limits.get(provider_name, []))
            }
        
        return status
    
    def get_available_providers(self) -> List[str]:
        """Get list of available (non-disabled) provider names"""
        return [
            name for name, config in self.providers.items()
            if config.get("status") != "disabled" and config.get("api_key")
        ]
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get overall usage summary"""
        total_requests = sum(stats.get("requests", 0) for stats in self.usage_stats.values())
        total_errors = sum(stats.get("errors", 0) for stats in self.usage_stats.values())
        total_tokens = sum(stats.get("total_tokens", 0) for stats in self.usage_stats.values())
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "total_tokens": total_tokens,
            "error_rate": total_errors / total_requests if total_requests > 0 else 0,
            "cache_size": len(self.cache),
            "active_providers": len([p for p in self.providers.values() if p["status"] != "disabled"]),
            "providers": self.get_provider_status()
        }
    
    async def test_all_providers(self) -> Dict[str, Any]:
        """Test all available providers"""
        test_message = [{"role": "user", "content": "Hello, please respond with 'Test successful'"}]
        results = {}
        
        for provider_name, config in self.providers.items():
            if config["status"] == "disabled":
                results[provider_name] = {"status": "disabled", "reason": "No API key"}
                continue
            
            try:
                start_time = time.time()
                response = await self._make_llm_request(
                    provider_name, "auto", test_message, max_tokens=50
                )
                response_time = time.time() - start_time
                
                results[provider_name] = {
                    "status": "success",
                    "response_time": round(response_time, 2),
                    "model_used": response.get("model", "unknown")
                }
                
            except Exception as e:
                results[provider_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results

# Global instance
llm_gateway = LLMGateway()
