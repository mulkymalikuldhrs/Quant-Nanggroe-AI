"""BlackHornet ↔ QNA Bridge.

Enables BlackHornet AGI swarm to query QNA market state, trigger strategies,
and inject decisions into the trading pipeline — and QNA to feed performance
data back to BH for learning.

Usage::
    bridge = BHQNABridge()
    bridge.sync_performance()
    bridge.inject_decision("BH:MarketIntel", {"action": "reduce", "symbol": "TSLA"})
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BHDecision:
    agent_id: str
    action: str
    symbol: str
    confidence: float = 0.5
    reasoning: str = ""
    timestamp: float = 0.0


@dataclass
class QNAState:
    total_pnl: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    positions: int = 0
    kill_switch_active: bool = False
    last_cycle: float = 0.0


class BHQNABridge:
    """Bi-directional bridge between BlackHornet and QNA.

    BH feeds: market intelligence, risk assessments, sentiment overlays, strategy ideas.
    QNA feeds: performance, P&L, drawdown, signals, kill-switch status.

    Data flows through a shared JSON file for filesystem-level IPC (no HTTP needed).
    """

    def __init__(self, bridge_path: Optional[str] = None) -> None:
        self._bridge_path = bridge_path or os.environ.get(
            "QNAI_BH_BRIDGE_PATH",
            "/tmp/qna_bh_bridge.json",
        )

    # ── BH → QNA direction ──────────────────────────────────────────

    def inject_decision(self, agent_id: str, action: str, symbol: str = "", confidence: float = 0.5, reasoning: str = "") -> None:
        """Inject a BH agent decision into QNA's decision pipeline."""
        decision = {
            "agent_id": agent_id,
            "action": action,
            "symbol": symbol,
            "confidence": confidence,
            "reasoning": reasoning,
            "timestamp": time.time(),
            "direction": "BH→QNA",
        }
        self._append_to_bridge("bh_decisions", decision)
        logger.info("BH→QNA: %s/%s %s %s (%.2f)", agent_id, action, symbol, reasoning[:50], confidence)

    def inject_sentiment(self, symbol: str, score: float, source: str = "BH") -> None:
        """Inject a sentiment score (0-1) for a symbol."""
        self.inject_decision(source, f"sentiment:{score:.2f}", symbol, score, f"Sentiment overlay from {source}")

    # ── QNA → BH direction ──────────────────────────────────────────

    def sync_performance(self, state: QNAState) -> None:
        """Push QNA performance snapshot to BH."""
        snapshot = {
            "event": "qna_performance",
            "data": {
                "total_pnl": state.total_pnl,
                "sharpe": state.sharpe,
                "max_drawdown": state.max_drawdown,
                "positions": state.positions,
                "kill_switch_active": state.kill_switch_active,
                "last_cycle": state.last_cycle or time.time(),
            },
            "timestamp": time.time(),
            "direction": "QNA→BH",
        }
        self._append_to_bridge("qna_performance", snapshot)
        logger.info("QNA→BH: state synced (PnL=%.2f, Sharpe=%.2f)", state.total_pnl, state.sharpe)

    # ── Read bridge ─────────────────────────────────────────────────

    def read_bh_decisions(self, since: float = 0.0) -> List[Dict[str, Any]]:
        """Read all BH decisions since a given timestamp."""
        return self._read_from_bridge("bh_decisions", since)

    def read_qna_performance(self, since: float = 0.0) -> List[Dict[str, Any]]:
        """Read all QNA performance snapshots since a given timestamp."""
        return self._read_from_bridge("qna_performance", since)

    # ── IPC helpers ─────────────────────────────────────────────────

    def _append_to_bridge(self, key: str, entry: Dict[str, Any]) -> None:
        try:
            data: Dict[str, List[Any]] = {}
            if os.path.exists(self._bridge_path):
                with open(self._bridge_path) as f:
                    data = json.load(f)
            data.setdefault(key, []).append(entry)
            # Keep last 1000 entries per key
            if len(data[key]) > 1000:
                data[key] = data[key][-1000:]
            with open(self._bridge_path, "w") as f:
                json.dump(data, f, indent=2)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("BH bridge write failed: %s", exc)

    def _read_from_bridge(self, key: str, since: float = 0.0) -> List[Dict[str, Any]]:
        try:
            if not os.path.exists(self._bridge_path):
                return []
            with open(self._bridge_path) as f:
                data: Dict[str, List[Any]] = json.load(f)
            entries = data.get(key, [])
            if since > 0:
                return [e for e in entries if e.get("timestamp", 0) > since]
            return entries
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("BH bridge read failed: %s", exc)
            return []

    def clear(self) -> None:
        """Clear the bridge file."""
        try:
            if os.path.exists(self._bridge_path):
                os.remove(self._bridge_path)
                logger.info("BH bridge cleared")
        except OSError as exc:
            logger.warning("BH bridge clear failed: %s", exc)
