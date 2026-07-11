# JeumpaLLM provider — mandatory per Dhaher Labs Constitution
# Connects to JeumpaLLM gateway at port 3456 (OpenAI-compatible API)
# Falls back to openrouter/ollama if JeumpaLLM unavailable

import os

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

JEUMPA_BASE_URL = os.getenv("JEUMPA_LLM_URL", "http://127.0.0.1:3456/v1")
JEUMPA_API_KEY = os.getenv("JEUMPA_LLM_KEY", "sk-jeumpa")
JEUMPA_MODEL = os.getenv("JEUMPA_LLM_MODEL", "deepseek-v4-flash-free")
FALLBACK_MODEL = os.getenv("FALLBACK_LLM_MODEL", "gpt-4o-mini")


def get_jeumpa_llm(**kwargs) -> BaseChatModel:
    """Get JeumpaLLM chat model. Falls back to OpenAI if JeumpaLLM unavailable."""
    try:
        r = httpx.get(f"{JEUMPA_BASE_URL.rstrip('/v1')}/health", timeout=2)
        if r.status_code == 200:
            return ChatOpenAI(
                base_url=JEUMPA_BASE_URL,
                api_key=JEUMPA_API_KEY,
                model=JEUMPA_MODEL,
                **kwargs
            )
    except Exception:
        pass
    return ChatOpenAI(model=FALLBACK_MODEL, **kwargs)


async def acheck_jeumpa_health() -> bool:
    """Async health check for JeumpaLLM gateway."""
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{JEUMPA_BASE_URL.rstrip('/v1')}/health")
            return r.status_code == 200
    except Exception:
        return False
