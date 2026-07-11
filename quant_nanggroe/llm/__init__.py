"""LLM Provider integration — wraps connectors/llm_gateway.py."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Import legacy LLMGateway
try:
    from quant_nanggroe.connectors.llm_gateway import LLMGateway as _LLMGateway
    _gateway = _LLMGateway()
    HAS_LLM = True
except ImportError as e:
    logger.warning("LLM gateway unavailable: %s", e)
    _gateway = None
    HAS_LLM = False


def get_llm_gateway():
    """Return the shared LLM gateway singleton."""
    return _gateway


def query_llm(prompt: str, provider: str = "openai") -> dict[str, Any]:
    """Send a prompt to the LLM and return the response."""
    if not _gateway:
        return {"success": False, "error": "LLM gateway not available"}
    try:
        result = _gateway.query(provider=provider, prompt=prompt)
        return {"success": True, "response": result}
    except Exception as e:
        logger.error("LLM query failed: %s", e)
        return {"success": False, "error": str(e)}


# JeumpaLLM bridge — standalone degradable
try:
    from quant_nanggroe.llm.jeumpa import acheck_jeumpa_health, get_jeumpa_llm
    HAS_JEUMPA = True
except ImportError:
    logger.warning("JeumpaLLM bridge unavailable (missing deps)")
    HAS_JEUMPA = False

    async def acheck_jeumpa_health() -> bool:
        return False

    def get_jeumpa_llm(**kwargs):
        raise ImportError("JeumpaLLM bridge unavailable — install httpx, langchain-openai, langchain-core")

__all__ = ["get_llm_gateway", "query_llm", "HAS_LLM", "HAS_JEUMPA", "get_jeumpa_llm", "acheck_jeumpa_health"]
