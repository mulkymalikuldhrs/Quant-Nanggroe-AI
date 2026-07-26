"""AIHF Bridge - Interface to E:/ai-hedge-fund (20 AI Agents)."""
from __future__ import annotations
import asyncio, json, logging, os, random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum
logger = logging.getLogger(__name__)

class AIHFAction(str, Enum):
    BUY = "buy"; SELL = "sell"; HOLD = "hold"

@dataclass
class AIHFSignal:
    action: AIHFAction; confidence: float; agent_name: str; reasoning: str = ""
    timestamp: str = ""
    def __post_init__(self):
        if not self.timestamp: self.timestamp = datetime.now(timezone.utc).isoformat()
        self.confidence = max(0.0, min(1.0, self.confidence))

class AIHFBridge:
    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        self._hf_path = self.config.get("hf_path", os.environ.get("AIHF_PATH", ""))
        self._timeout = self.config.get("timeout", 30.0)
        self._cache: dict[str, tuple[float, list[AIHFSignal]]] = {}
        self._cache_ttl = self.config.get("cache_ttl", 60.0)

    async def get_all_signals(self, symbol: str) -> list[AIHFSignal]:
        now = datetime.now().timestamp()
        if symbol in self._cache:
            ct, cs = self._cache[symbol]
            if now - ct < self._cache_ttl: return cs
        signals: list[AIHFSignal] = []
        if self._hf_path:
            try:
                ext = await self._fetch_external(symbol)
                if ext: signals.extend(ext)
            except Exception as exc: logger.warning("AIHF ext failed: %s", exc)
        if not signals:
            raise RuntimeError(f"AIHF bridge: no external signals for {symbol}. Check AIHF path or network connectivity.")
        self._cache[symbol] = (now, signals)
        return signals

    async def _fetch_external(self, symbol: str) -> list[AIHFSignal]:
        import subprocess
        try:
            result = await asyncio.wait_for(asyncio.to_thread(subprocess.run, ["python", "-m", "ai_hedge_fund.main", "--symbol", symbol, "--json"], capture_output=True, text=True, timeout=self._timeout, cwd=self._hf_path if self._hf_path else None), timeout=self._timeout)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                return [AIHFSignal(action=AIHFAction(a.get("action","hold")), confidence=float(a.get("confidence",0.5)), agent_name=a.get("name","unknown"), reasoning=a.get("reasoning","")) for a in data.get("agents",[])]
        except Exception as exc: logger.debug("AIHF fetch failed: %s", exc)
        return []

    def get_stats(self) -> dict[str, Any]:
        return {"hf_path": self._hf_path or "not set", "cached_symbols": list(self._cache.keys()), "cache_ttl": self._cache_ttl}

__all__ = ["AIHFBridge", "AIHFSignal", "AIHFAction"]
