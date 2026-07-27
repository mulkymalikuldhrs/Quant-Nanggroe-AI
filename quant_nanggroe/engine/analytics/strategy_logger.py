"""Strategy Logger - Log Every Strategy Trigger + Attribution Tracking."""
from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class StrategyLogEntry:
    log_id: str = ""; symbol: str = ""; strategy_name: str = ""
    action: str = "hold"; confidence: float = 0.0; market_regime: str = "unknown"
    entry_price: float = 0.0; volume: float = 0.0; sl: float = 0.0; tp: float = 0.0
    atr: float = 0.0; timestamp: str = ""; pipeline_duration_ms: float = 0.0
    pnl: Optional[float] = None; exit_price: float = 0.0; exit_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.log_id: self.log_id = str(uuid.uuid4())[:12]
        if not self.timestamp: self.timestamp = datetime.now(timezone.utc).isoformat()
    def to_dict(self) -> dict[str, Any]:
        d = {"log_id": self.log_id, "symbol": self.symbol, "strategy_name": self.strategy_name, "action": self.action, "confidence": round(self.confidence,4), "market_regime": self.market_regime, "entry_price": round(self.entry_price,2), "volume": round(self.volume,4), "sl": round(self.sl,2), "tp": round(self.tp,2), "atr": round(self.atr,4), "timestamp": self.timestamp, "pipeline_duration_ms": round(self.pipeline_duration_ms,2)}
        if self.pnl is not None:
            d["pnl"] = round(self.pnl, 2)
            d["exit_price"] = round(self.exit_price, 2)
            d["exit_reason"] = self.exit_reason
        return d

@dataclass
class AttributionResult:
    strategy_name: str = ""; total_triggers: int = 0; winning_triggers: int = 0
    losing_triggers: int = 0; total_pnl: float = 0.0; win_rate: float = 0.0; avg_confidence: float = 0.0

class StrategyLogger:
    def __init__(self, log_dir: str = "data"):
        self._log_dir = Path(log_dir) / "strategy_logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._entries: list[StrategyLogEntry] = []; self._load()
    def log_trigger(self, entry: dict[str, Any]) -> StrategyLogEntry:
        le = StrategyLogEntry(symbol=entry.get("symbol",""), strategy_name=entry.get("strategy_name","unknown"), action=entry.get("action","hold"), confidence=float(entry.get("confidence",0.0)), market_regime=entry.get("market_regime","unknown"), entry_price=float(entry.get("entry_price",0.0)), volume=float(entry.get("volume",0.0)), sl=float(entry.get("sl",0.0)), tp=float(entry.get("tp",0.0)), atr=float(entry.get("atr",0.0)), pipeline_duration_ms=float(entry.get("pipeline_duration_ms",0.0)), pnl=entry.get("pnl"), exit_price=float(entry.get("exit_price",0.0)), exit_reason=entry.get("exit_reason",""), metadata=entry.get("metadata",{}))
        self._entries.append(le); self._save()
        logger.info("StrategyLogger: %s %s %s @ %.1f%%", le.strategy_name, le.action, le.symbol, le.confidence*100)
        return le

    def log_trade_result(self, log_id: str, pnl: float, exit_price: float, exit_reason: str = "") -> bool:
        for i, e in enumerate(self._entries):
            if e.log_id == log_id:
                self._entries[i].pnl = pnl
                self._entries[i].exit_price = exit_price
                self._entries[i].exit_reason = exit_reason
                self._save()
                logger.info("TradeResult: %s %s pnl=%.2f reason=%s", e.strategy_name, e.symbol, pnl, exit_reason)
                return True
        return False

    def get_attribution(self, strategy_name: Optional[str] = None) -> list[AttributionResult]:
        stats: dict = defaultdict(lambda: {"triggers":0,"wins":0,"losses":0,"pnl":0.0,"conf_sum":0.0})
        for e in self._entries:
            if strategy_name and e.strategy_name != strategy_name: continue
            s = stats[e.strategy_name]; s["triggers"]+=1; s["conf_sum"]+=e.confidence
            if e.pnl is not None:
                s["pnl"] += e.pnl
                if e.pnl > 0:
                    s["wins"] += 1
                elif e.pnl < 0:
                    s["losses"] += 1
        return [AttributionResult(strategy_name=n, total_triggers=s["triggers"], winning_triggers=s["wins"], losing_triggers=s["losses"], total_pnl=round(s["pnl"],2), win_rate=round(s["wins"]/s["triggers"]*100,1) if s["triggers"]>0 else 0.0, avg_confidence=round(s["conf_sum"]/s["triggers"],4) if s["triggers"]>0 else 0.0) for n, s in sorted(stats.items(), key=lambda x: -x[1]["triggers"])]
    def get_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._entries[-limit:]]
    def _save(self):
        (self._log_dir/"strategy_log.json").write_text(json.dumps([e.to_dict() for e in self._entries], indent=2, default=str), encoding="utf-8")
    def _load(self):
        p = self._log_dir/"strategy_log.json"
        if p.exists():
            try:
                for item in json.loads(p.read_text(encoding="utf-8")): self._entries.append(StrategyLogEntry(**item))
                logger.info("Loaded %d strategy log entries", len(self._entries))
            except Exception as exc: logger.warning("Failed to load: %s", exc)

__all__ = ["StrategyLogger", "StrategyLogEntry", "AttributionResult"]
