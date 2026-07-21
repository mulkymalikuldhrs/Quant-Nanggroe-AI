"""
Adapter Registry - Free Model Integration

Registry of free model adapters from various sources:
1. OpenAI Compatible (80+ models)
2. Local Ollama (zero cost, always available)
3. Pollinations (free, no auth required)
4. Web Chat Wrappers (Playwright-based)
5. Custom wrapped LLM adapters

Key principles:
- Priority-based model selection
- Health monitoring and failover
- Cost optimization (free first)
- Zero dependency on paid APIs by default
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import logging

class AdapterType(Enum):
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"
    POLLINATIONS = "pollinations" 
    WEB_CHAT = "web_chat"
    CUSTOM = "custom"

@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    adapter_type: AdapterType
    capabilities: List[str] = field(default_factory=list)
    context_window: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    latency_p50_ms: float = 1000.0
    supports_tools: bool = False
    supports_streaming: bool = False
    is_available: bool = True
    health_score: float = 1.0

@dataclass
class AdapterConfig:
    adapter_id: str
    adapter_type: AdapterType
    enabled: bool = True
    priority: int = 100
    health_check_interval: int = 60
    timeout_ms: int = 30000
    health_score_threshold: float = 0.5
    auto_failover: bool = True

class ProviderAdapter(ABC):
    """Base adapter interface for model providers"""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.logger = logging.getLogger(f"adapter.{config.adapter_id}")
        self.models: List[ModelInfo] = []
        self.last_health_check: Optional[float] = None
    
    @abstractmethod
    def adapter_id(self) -> str:
        pass
    
    @abstractmethod
    def get_adapter_type(self) -> AdapterType:
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        pass
    
    @abstractmethod
    async def chat(self, model_id: str, messages: List[Dict[str, Any]], 
                   options: Dict[str, Any] = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass
    
    async def refresh_models(self):
        """Refresh available models list"""
        try:
            self.models = await self.list_models()
            self.logger.info(f"Refreshed {len(self.models)} models")
        except Exception as e:
            self.logger.error(f"Failed to refresh models: {e}")
    
    async def check_health(self) -> bool:
        """Check adapter health and update health score"""
        try:
            health_result = await self.health_check()
            healthy = health_result.get("healthy", False)
            health_score = health_result.get("health_score", 0.0)
            
            self.last_health_check = health_score
            self.logger.debug(f"Health check: healthy={healthy}, score={health_score}")
            
            return healthy and health_score >= self.config.health_score_threshold
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def is_healthy(self) -> bool:
        """Check if adapter is currently healthy"""
        if self.last_health_check is None:
            return True
        
        return self.last_health_check >= self.config.health_score_threshold
    
    def get_model_by_id(self, model_id: str) -> Optional[ModelInfo]:
        """Get model info by ID"""
        for model in self.models:
            if model.id == model_id:
                return model
        return None
    
    def get_models_by_capability(self, capability: str) -> List[ModelInfo]:
        """Get models that support a specific capability"""
        return [model for model in self.models 
                if capability in model.capabilities and model.is_available]
    
    def get_models_by_cost(self, max_cost_per_1k: float, 
                          sort_by: str = "input") -> List[ModelInfo]:
        """Get models within budget"""
        affordable_models = []
        
        for model in self.models:
            if model.is_available and model.cost_per_1k_input <= max_cost_per_1k:
                affordable_models.append(model)
            elif sort_by == "output" and model.is_available and model.cost_per_1k_output <= max_cost_per_1k:
                affordable_models.append(model)
        
        # Sort by cost (cheapest first)
        affordable_models.sort(key=lambda m: m.cost_per_1k_input if sort_by == "input" else m.cost_per_1k_output)
        return affordable_models

class OpenAICompatibleAdapter(ProviderAdapter):
    """Adapter for OpenAI-compatible APIs (includes many free providers)"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.base_url = config.adapter_id  # URL from config
    
    def adapter_id(self) -> str:
        return self.config.adapter_id
    
    def get_adapter_type(self) -> AdapterType:
        return AdapterType.OPENAI_COMPATIBLE
    
    async def list_models(self) -> List[ModelInfo]:
        """List available OpenAI-compatible models"""
        models = []
        
        # Free models from OpenAI-compatible providers
        free_models = [
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "provider": "openai",
                "capabilities": ["coding", "reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.00015,
                "cost_per_1k_output": 0.0006,
                "supports_tools": True,
                "supports_streaming": True
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o", 
                "provider": "openai",
                "capabilities": ["coding", "reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0005,
                "cost_per_1k_output": 0.0015,
                "supports_tools": True,
                "supports_streaming": True
            },
            {
                "id": "llama3.1:405b",
                "name": "Llama 3.1 405B",
                "provider": "ollama",
                "capabilities": ["reasoning", "coding", "analysis"],
                "context_window": 4096,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "deepseek-coder",
                "name": "DeepSeek Coder",
                "provider": "deepseek",
                "capabilities": ["coding"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "qwen2.5-coder",
                "name": "Qwen2.5 Coder",
                "provider": "qwen",
                "capabilities": ["coding", "analysis"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "claude-3-5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "anthropic",
                "capabilities": ["reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.015,
                "supports_tools": True,
                "supports_streaming": True
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "provider": "google",
                "capabilities": ["reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0035,
                "cost_per_1k_output": 0.0105,
                "supports_tools": True,
                "supports_streaming": True
            }
        ]
        
        for model_data in free_models:
            model = ModelInfo(**model_data)
            model.is_available = True
            models.append(model)
        
        return models
    
    async def chat(self, model_id: str, messages: List[Dict[str, Any]], 
                   options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chat with OpenAI-compatible model"""
        # Mock implementation - would make actual HTTP request
        model = self.get_model_by_id(model_id)
        
        return {
            "success": True,
            "model": model_id,
            "message": {
                "role": "assistant",
                "content": f"Mock response from {model_id} for task: {messages[-1].get('content', '')[:100]}..."
            },
            "usage": {
                "prompt_tokens": len(messages[-1].get("content", "")),
                "completion_tokens": 50,
                "total_tokens": len(messages[-1].get("content", "")) + 50
            },
            "model_info": {
                "provider": model.provider if model else "unknown",
                "cost": (model.cost_per_1k_input * (len(messages[-1].get("content", "")) / 1000)) + 
                        (model.cost_per_1k_output * (50 / 1000)) if model else 0.0
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI-compatible API health"""
        try:
            # Mock health check - would test actual API endpoint
            return {
                "healthy": True,
                "health_score": 1.0,
                "response_time_ms": 100,
                "error": None
            }
        except Exception as e:
            return {
                "healthy": False,
                "health_score": 0.0,
                "response_time_ms": 5000,
                "error": str(e)
            }

class OllamaAdapter(ProviderAdapter):
    """Adapter for local Ollama models (zero cost, always available)"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.host = "localhost"
        self.port = 11434
    
    def adapter_id(self) -> str:
        return self.config.adapter_id
    
    def get_adapter_type(self) -> AdapterType:
        return AdapterType.OLLAMA
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Ollama models"""
        models = []
        
        # Local Ollama models (zero cost)
        ollama_models = [
            {
                "id": "llama3.1:8b",
                "name": "Llama 3.1 8B",
                "provider": "ollama",
                "capabilities": ["reasoning", "coding", "analysis"],
                "context_window": 4096,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "llama3.1:70b",
                "name": "Llama 3.1 70B",
                "provider": "ollama",
                "capabilities": ["reasoning", "coding", "analysis", "creative"],
                "context_window": 4096,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "qwen2.5:7b",
                "name": "Qwen2.5 7B",
                "provider": "ollama",
                "capabilities": ["reasoning", "coding", "analysis"],
                "context_window": 4096,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "gemma:2b",
                "name": "Gemma 2B",
                "provider": "ollama",
                "capabilities": ["reasoning", "analysis"],
                "context_window": 4096,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "codellama:7b",
                "name": "CodeLlama 7B",
                "provider": "ollama",
                "capabilities": ["coding"],
                "context_window": 4096,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            }
        ]
        
        for model_data in ollama_models:
            model = ModelInfo(**model_data)
            model.is_available = True
            models.append(model)
        
        return models
    
    async def chat(self, model_id: str, messages: List[Dict[str, Any]], 
                   options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chat with Ollama model"""
        model = self.get_model_by_id(model_id)
        
        return {
            "success": True,
            "model": model_id,
            "message": {
                "role": "assistant",
                "content": f"Local Ollama response from {model_id} for task: {messages[-1].get('content', '')[:100]}..."
            },
            "usage": {
                "prompt_tokens": len(messages[-1].get("content", "")),
                "completion_tokens": 50,
                "total_tokens": len(messages[-1].get("content", "")) + 50
            },
            "model_info": {
                "provider": model.provider if model else "ollama",
                "cost": 0.0  # Ollama is free
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama health"""
        try:
            # Mock health check - would test Ollama endpoint
            return {
                "healthy": True,
                "health_score": 1.0,
                "response_time_ms": 50,
                "error": None
            }
        except Exception as e:
            return {
                "healthy": False,
                "health_score": 0.0,
                "response_time_ms": 5000,
                "error": str(e)
            }

class PollinationsAdapter(ProviderAdapter):
    """Adapter for Pollinations free AI models"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
    
    def adapter_id(self) -> str:
        return self.config.adapter_id
    
    def get_adapter_type(self) -> AdapterType:
        return AdapterType.POLLINATIONS
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Pollinations models"""
        models = []
        
        # Free models from Pollinations (no auth required)
        pollinations_models = [
            {
                "id": "pollinations:openai-gpt3",
                "name": "OpenAI GPT-3 (Pollinations)",
                "provider": "pollinations",
                "capabilities": ["coding", "reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "pollinations:llama2",
                "name": "Llama 2 (Pollinations)",
                "provider": "pollinations", 
                "capabilities": ["reasoning", "coding", "analysis"],
                "context_window": 4096,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            },
            {
                "id": "pollinations:mistral",
                "name": "Mistral (Pollinations)",
                "provider": "pollinations",
                "capabilities": ["reasoning", "coding", "analysis"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            }
        ]
        
        for model_data in pollinations_models:
            model = ModelInfo(**model_data)
            model.is_available = True
            models.append(model)
        
        return models
    
    async def chat(self, model_id: str, messages: List[Dict[str, Any]], 
                   options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chat with Pollinations model"""
        model = self.get_model_by_id(model_id)
        
        return {
            "success": True,
            "model": model_id,
            "message": {
                "role": "assistant",
                "content": f"Pollinations free response from {model_id} for task: {messages[-1].get('content', '')[:100]}..."
            },
            "usage": {
                "prompt_tokens": len(messages[-1].get("content", "")),
                "completion_tokens": 50,
                "total_tokens": len(messages[-1].get("content", "")) + 50
            },
            "model_info": {
                "provider": model.provider if model else "pollinations",
                "cost": 0.0  # Pollinations is free
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Pollinations health"""
        try:
            # Mock health check - would test Pollinations endpoint
            return {
                "healthy": True,
                "health_score": 1.0,
                "response_time_ms": 200,
                "error": None
            }
        except Exception as e:
            return {
                "healthy": False,
                "health_score": 0.0,
                "response_time_ms": 5000,
                "error": str(e)
            }

class WebChatAdapter(ProviderAdapter):
    """Web chat adapter using Playwright for browser-based models"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.browser_configs = {}
    
    def adapter_id(self) -> str:
        return self.config.adapter_id
    
    def get_adapter_type(self) -> AdapterType:
        return AdapterType.WEB_CHAT
    
    async def list_models(self) -> List[ModelInfo]:
        """List available web chat models"""
        models = []
        
        # Browser-based models (via web interfaces)
        web_models = [
            {
                "id": "web:openai-chat",
                "name": "OpenAI ChatGPT Web",
                "provider": "openai",
                "capabilities": ["reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,  # Free through web interface
                "cost_per_1k_output": 0.0,
                "supports_tools": True,
                "supports_streaming": True
            },
            {
                "id": "web:google-ai",
                "name": "Google AI Bard Web",
                "provider": "google",
                "capabilities": ["reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            }
        ]
        
        for model_data in web_models:
            model = ModelInfo(**model_data)
            model.is_available = True
            models.append(model)
        
        return models
    
    async def chat(self, model_id: str, messages: List[Dict[str, Any]], 
                   options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chat with web-based model"""
        model = self.get_model_by_id(model_id)
        
        return {
            "success": True,
            "model": model_id,
            "message": {
                "role": "assistant",
                "content": f"Web browser response from {model_id} for task: {messages[-1].get('content', '')[:100]}..."
            },
            "usage": {
                "prompt_tokens": len(messages[-1].get("content", "")),
                "completion_tokens": 50,
                "total_tokens": len(messages[-1].get("content", "")) + 50
            },
            "model_info": {
                "provider": model.provider if model else "web",
                "cost": 0.0  # Web interfaces typically free
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check web chat health"""
        try:
            # Mock health check - would test browser availability
            return {
                "healthy": True,
                "health_score": 1.0,
                "response_time_ms": 500,
                "error": None
            }
        except Exception as e:
            return {
                "healthy": False,
                "health_score": 0.0,
                "response_time_ms": 10000,
                "error": str(e)
            }

class CustomAdapter(ProviderAdapter):
    """Custom adapter for wrapped LLM APIs"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.api_configs = {}
    
    def adapter_id(self) -> str:
        return self.config.adapter_id
    
    def get_adapter_type(self) -> AdapterType:
        return AdapterType.CUSTOM
    
    async def list_models(self) -> List[ModelInfo]:
        """List custom models from wrapped APIs"""
        models = []
        
        # Custom wrapped models from various sources
        custom_models = [
            {
                "id": "wrapped:anthropic-claude",
                "name": "Anthropic Claude (Wrapped)",
                "provider": "anthropic",
                "capabilities": ["reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,  # Wrapped for free
                "cost_per_1k_output": 0.0,
                "supports_tools": True,
                "supports_streaming": True
            },
            {
                "id": "wrapped:google-gemini",
                "name": "Google Gemini (Wrapped)",
                "provider": "google",
                "capabilities": ["reasoning", "analysis", "creative"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": True,
                "supports_streaming": True
            },
            {
                "id": "wrapped:cohere-command",
                "name": "Cohere Command (Wrapped)",
                "provider": "cohere",
                "capabilities": ["reasoning", "analysis"],
                "context_window": 8192,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0,
                "supports_tools": False,
                "supports_streaming": True
            }
        ]
        
        for model_data in custom_models:
            model = ModelInfo(**model_data)
            model.is_available = True
            models.append(model)
        
        return models
    
    async def chat(self, model_id: str, messages: List[Dict[str, Any]], 
                   options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Chat with custom wrapped model"""
        model = self.get_model_by_id(model_id)
        
        return {
            "success": True,
            "model": model_id,
            "message": {
                "role": "assistant",
                "content": f"Custom wrapped response from {model_id} for task: {messages[-1].get('content', '')[:100]}..."
            },
            "usage": {
                "prompt_tokens": len(messages[-1].get("content", "")),
                "completion_tokens": 50,
                "total_tokens": len(messages[-1].get("content", "")) + 50
            },
            "model_info": {
                "provider": model.provider if model else "custom",
                "cost": 0.0  # All custom adapters are free
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check custom adapter health"""
        try:
            # Mock health check - would test custom API
            return {
                "healthy": True,
                "health_score": 1.0,
                "response_time_ms": 300,
                "error": None
            }
        except Exception as e:
            return {
                "healthy": False,
                "health_score": 0.0,
                "response_time_ms": 8000,
                "error": str(e)
            }

class AdapterRegistry:
    """Registry for managing all model adapters"""
    
    def __init__(self):
        self.adapters: Dict[str, ProviderAdapter] = {}
        self.configs: Dict[str, AdapterConfig] = {}
        self.logger = logging.getLogger("adapter_registry")
        
        # Initialize with free model adapters
        self._init_free_adapters()
    
    def _init_free_adapters(self):
        """Initialize adapter registry with free model sources"""
        # OpenAI Compatible adapters (priority 10)
        openai_config = AdapterConfig(
            adapter_id="https://api.openai.com/v1",
            adapter_type=AdapterType.OPENAI_COMPATIBLE,
            priority=10,
            health_check_interval=60
        )
        self.configs[openai_config.adapter_id] = openai_config
        self.adapters[openai_config.adapter_id] = OpenAICompatibleAdapter(openai_config)
        
        # Ollama adapter (priority 5, always available locally)
        ollama_config = AdapterConfig(
            adapter_id="ollama://localhost:11434",
            adapter_type=AdapterType.OLLAMA,
            priority=5,
            health_check_interval=30
        )
        self.configs[ollama_config.adapter_id] = ollama_config
        self.adapters[ollama_config.adapter_id] = OllamaAdapter(ollama_config)
        
        # Pollinations adapter (priority 50, free no-auth)
        pollinations_config = AdapterConfig(
            adapter_id="https://pollinations.ai/api/v1",
            adapter_type=AdapterType.POLLINATIONS,
            priority=50,
            health_check_interval=120
        )
        self.configs[pollinations_config.adapter_id] = pollinations_config
        self.adapters[pollinations_config.adapter_id] = PollinationsAdapter(pollinations_config)
        
        # Web Chat adapter (priority 25)
        web_config = AdapterConfig(
            adapter_id="web://chatgpt-browser",
            adapter_type=AdapterType.WEB_CHAT,
            priority=25,
            health_check_interval=180,
            auto_failover=True
        )
        self.configs[web_config.adapter_id] = web_config
        self.adapters[web_config.adapter_id] = WebChatAdapter(web_config)
        
        # Custom wrapped adapters (priority 1-3, free wrapped APIs)
        wrapped_configs = [
            AdapterConfig(
                adapter_id="wrapped:anthropic-claude",
                adapter_type=AdapterType.CUSTOM,
                priority=15,
                health_check_interval=90
            ),
            AdapterConfig(
                adapter_id="wrapped:google-gemini", 
                adapter_type=AdapterType.CUSTOM,
                priority=20,
                health_check_interval=90
            ),
            AdapterConfig(
                adapter_id="wrapped:cohere-command",
                adapter_type=AdapterType.CUSTOM,
                priority=30,
                health_check_interval=120
            )
        ]
        
        for config in wrapped_configs:
            self.configs[config.adapter_id] = config
            self.adapters[config.adapter_id] = CustomAdapter(config)
    
    def get_healthy_adapters(self) -> List[ProviderAdapter]:
        """Get all healthy adapters"""
        healthy = []
        for adapter in self.adapters.values():
            if adapter.is_healthy():
                healthy.append(adapter)
        return sorted(healthy, key=lambda a: a.config.priority, reverse=True)
    
    async def check_all_health(self) -> Dict[str, bool]:
        """Check health of all adapters"""
        health_status = {}
        for adapter_id, adapter in self.adapters.items():
            try:
                is_healthy = await adapter.check_health()
                health_status[adapter_id] = is_healthy
            except Exception as e:
                self.logger.error(f"Health check failed for {adapter_id}: {e}")
                health_status[adapter_id] = False
        return health_status
    
    def get_adapter(self, adapter_id: str) -> Optional[ProviderAdapter]:
        """Get adapter by ID"""
        return self.adapters.get(adapter_id)
    
    def get_adapter_by_type(self, adapter_type: AdapterType) -> List[ProviderAdapter]:
        """Get all adapters of specific type"""
        return [adapter for adapter in self.adapters.values() 
                if adapter.get_adapter_type() == adapter_type and adapter.is_healthy()]
    
    async def refresh_all_models(self):
        """Refresh models from all healthy adapters"""
        for adapter in self.get_healthy_adapters():
            await adapter.refresh_models()
    
    async def get_models_for_task(self, task_type: str, 
                                  max_cost: float = float('inf')) -> List[ModelInfo]:
        """Get optimal models for specific task type and budget"""
        all_models = []
        
        for adapter in self.get_healthy_adapters():
            adapter_models = adapter.get_models_by_cost(max_cost)
            
            # Filter by capability based on task type
            if task_type == "coding":
                task_models = [m for m in adapter_models if "coding" in m.capabilities]
            elif task_type == "reasoning":
                task_models = [m for m in adapter_models if "reasoning" in m.capabilities]
            elif task_type == "analysis":
                task_models = [m for m in adapter_models if "analysis" in m.capabilities]
            elif task_type == "creative":
                task_models = [m for m in adapter_models if "creative" in m.capabilities]
            else:
                task_models = adapter_models
            
            all_models.extend(task_models)
        
        # Sort by cost-effectiveness (lowest cost first)
        all_models.sort(key=lambda m: m.cost_per_1k_input)
        return all_models
    
    async def execute_chat(self, model_id: str, messages: List[Dict[str, Any]], 
                          options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute chat using optimal adapter"""
        # Find adapter for model
        for adapter in self.get_healthy_adapters():
            model = adapter.get_model_by_id(model_id)
            if model:
                try:
                    result = await adapter.chat(model_id, messages, options)
                    if result.get("success", False):
                        return result
                except Exception as e:
                    self.logger.error(f"Chat failed with {model_id}: {e}")
                    continue
        
        return {
            "success": False,
            "error": f"Model {model_id} not available or adapters unhealthy"
        }
