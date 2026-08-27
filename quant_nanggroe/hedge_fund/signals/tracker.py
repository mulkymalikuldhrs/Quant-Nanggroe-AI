"""Performance tracker for signal providers — Bayesian-smoothed weight computation."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class SignalRecord:
    provider_name: str
    symbol: str
    timestamp: str
    bias: str
    confidence: float
    pnl: Optional[float] = None
    closed_at: Optional[str] = None


class SignalTracker:
    def __init__(self, path: Optional[str] = None):
        self.path = Path(path) if path else DATA_DIR / "signal_tracker.json"
        self.records: list[SignalRecord] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            self.records = [SignalRecord(**r) for r in data.get("records", [])]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.records = []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(
            {"records": [asdict(r) for r in self.records]}, indent=2
        ))

    def record_signal(self, provider: str, symbol: str, bias: str, confidence: float):
        self.records.append(SignalRecord(
            provider_name=provider,
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            bias=bias,
            confidence=confidence,
        ))
        self._save()

    def record_outcome(self, provider: str, symbol: str, pnl: float):
        for r in reversed(self.records):
            if r.provider_name == provider and r.symbol == symbol and r.pnl is None:
                r.pnl = pnl
                r.closed_at = datetime.now().isoformat()
                self._save()
                return

    def _closed(self, provider: str) -> list[SignalRecord]:
        return [r for r in self.records if r.provider_name == provider and r.pnl is not None]

    def win_rate(self, provider: str, window: int = 20) -> float:
        closed = self._closed(provider)[-window:]
        if not closed:
            return 0.0
        return sum(1 for r in closed if r.pnl > 0) / len(closed)

    def avg_confidence(self, provider: str, window: int = 20) -> float:
        recent = [r for r in self.records if r.provider_name == provider][-window:]
        if not recent:
            return 0.0
        return sum(r.confidence for r in recent) / len(recent)

    def expectancy(self, provider: str) -> float:
        closed = self._closed(provider)
        if not closed:
            return 0.0
        wins = [r for r in closed if r.pnl > 0]
        losses = [r for r in closed if r.pnl <= 0]
        wr = len(wins) / len(closed)
        avg_win = sum(r.pnl for r in wins) / len(wins) if wins else 0
        avg_loss = sum(r.pnl for r in losses) / len(losses) if losses else 0
        return avg_win * wr - avg_loss * (1 - wr)

    def get_weight(self, provider: str) -> float:
        closed = self._closed(provider)
        wins = sum(1 for r in closed if r.pnl > 0)
        total = len(closed)
        return (wins + 1) / (total + 2)
