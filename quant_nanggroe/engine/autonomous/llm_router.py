"""Autonomous LLM Router — multi-provider fallback chain.

Free providers (no API key needed):
1. Nous Research (Hermes) — via OpenRouter free
2. DeepSeek — via OpenCode Zen free
3. HuggingFace inference — free tier
4. Groq — free tier (needs signup, no payment)
5. Fallback: local model (llama.cpp) if available

Strategy: tiered fallback. Each request tries providers in order.
If one fails, next is tried. All fail = error.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Provider definitions — free/no-key
PROVIDERS = {
    "deepseek": {
        "url": "https://api.opencode.com/v1/chat/completions",
        "model": "deepseek-v4-flash-free",
        "api_key": "",  # Free tier — no key needed
    },
    "nous": {
        "url": "https://api.openrouter.ai/v1/chat/completions",
        "model": "hermes-3-llama-3.1-405b",
        "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
    },
    "huggingface": {
        "url": "https://api-inference.huggingface.co/models/microsoft/phi-4",
        "model": "microsoft/phi-4",
        "api_key": os.environ.get("HF_API_KEY", ""),
    },
}

# Task routing: different models for different tasks
TASK_ROUTING = {
    "signal_generation": ["deepseek", "nous"],  # Fast, good for real-time
    "risk_analysis": ["nous", "deepseek"],       # Bigger model for complex risk
    "research": ["deepseek", "nous", "huggingface"],  # Deep research = try all
    "code": ["deepseek", "nous"],                # Code generation
    "analysis": ["nous", "deepseek"],             # Market analysis
}


class LLMRouter:
    """Multi-provider LLM router with automatic fallback."""

    def __init__(self, provider_chain: Optional[list] = None):
        self.provider_chain = provider_chain or ["deepseek", "nous", "huggingface"]

    def query(self, prompt: str, system_prompt: str = "",
              task_type: str = "analysis", timeout: int = 30) -> Dict[str, Any]:
        """Query LLM with automatic fallback across providers."""
        # Get provider chain for this task type
        chain = TASK_ROUTING.get(task_type, self.provider_chain)
        last_error = ""

        for provider_name in chain:
            provider = PROVIDERS.get(provider_name)
            if not provider:
                continue

            try:
                result = self._call_provider(provider, prompt, system_prompt, timeout)
                if result:
                    return {
                        "provider": provider_name,
                        "response": result,
                        "success": True,
                    }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue

        return {
            "provider": None,
            "response": f"All providers failed: {last_error}",
            "success": False,
        }

    def _call_provider(self, provider: dict, prompt: str,
                       system_prompt: str, timeout: int) -> Optional[str]:
        """Call a single provider."""
        import requests

        headers = {"Content-Type": "application/json"}
        if provider.get("api_key"):
            headers["Authorization"] = f"Bearer {provider['api_key']}"

        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": system_prompt or "You are a quant trading AI."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        resp = requests.post(
            provider["url"],
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if resp.status_code != 200:
            logger.warning(f"Provider returned {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


# Singleton
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


# Quick test
if __name__ == "__main__":
    router = get_router()
    result = router.query("What is the current BTC price?", task_type="analysis")
    print(f"Provider: {result['provider']}")
    print(f"Response: {result['response'][:200]}")
