"""Hedge Fund Bridge - Weighted Vote from 10+ Providers."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class ProviderVote:
    provider: str; bias: str; confidence: float; weight: float; timestamp: str = ""
    def __post_init__(self):
        if not self.timestamp: self.timestamp = datetime.now(timezone.utc).isoformat()

class HedgeFundBridge:
    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = config or {}
        self._vote_history: list[dict[str, Any]] = []

    def get_signal(self, symbol: str) -> dict[str, Any]:
        raise RuntimeError(
            f"HedgeFundBridge cannot generate real signal for {symbol} — "
            "no real provider data available. Requires wired providers. "
            "Failing closed (no mock/simulated signals)."
        )

    def get_recent_votes(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._vote_history[-limit:]
    def get_stats(self) -> dict[str, Any]:
        return {"providers":self._providers,"active_providers":len(self._providers),"total_votes_cast":len(self._vote_history)}

__all__ = ["HedgeFundBridge", "ProviderVote"]
