"""MonitorHub — Lightweight live monitoring singleton (~150 lines).

7 metrics, 3 endpoints, append-only JSONL storage.
Per Theme 5 council decision, P1 priority.
"""

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    execution_latency_ms: float = 0.0
    error_rate: float = 0.0
    signal_freshness_sec: float = 0.0
    pnl_per_cycle: float = 0.0
    risk_score: float = 0.0
    correlation: float = 0.0
    system_health: float = 1.0
    cycle_count: int = 0
    timestamp: str = ""


class MonitorHub:
    def __init__(self, log_dir: str | Path | None = None, window: int = 20):
        self.window = window
        self.execution_latencies: deque[float] = deque(maxlen=window)
        self.error_count = 0
        self.total_cycles = 0
        self.last_signal_time: float = 0.0
        self.cycle_pnl: deque[float] = deque(maxlen=window)
        self.risk_scores: deque[float] = deque(maxlen=window)
        self.correlations: deque[float] = deque(maxlen=window)
        self.last_metric_time: float = time.time()
        self.attribution_records: deque[dict] = deque(maxlen=window)
        self.log_dir = Path(log_dir) if log_dir else None
        self._log_fd: Any = None

    def record_execution(self, latency_ms: float) -> None:
        self.execution_latencies.append(latency_ms)

    def record_error(self) -> None:
        self.error_count += 1

    def record_signal(self) -> None:
        self.last_signal_time = time.time()

    def record_pnl(self, pnl: float) -> None:
        self.cycle_pnl.append(pnl)

    def record_risk(self, score: float) -> None:
        self.risk_scores.append(score)

    def record_correlation(self, corr: float) -> None:
        self.correlations.append(corr)

    def record_attribution(self, attribution: dict) -> None:
        self.attribution_records.append(attribution)

    def record_cycle(self) -> None:
        self.total_cycles += 1

    def snapshot(self) -> MetricSnapshot:
        now = time.time()
        avg_lat = sum(self.execution_latencies) / max(len(self.execution_latencies), 1)
        err_rate = self.error_count / max(self.total_cycles, 1)
        freshness = now - self.last_signal_time if self.last_signal_time > 0 else 0.0
        avg_pnl = sum(self.cycle_pnl) / max(len(self.cycle_pnl), 1)
        avg_risk = sum(self.risk_scores) / max(len(self.risk_scores), 1)
        avg_corr = sum(self.correlations) / max(len(self.correlations), 1)
        return MetricSnapshot(
            execution_latency_ms=round(avg_lat, 2),
            error_rate=round(err_rate, 4),
            signal_freshness_sec=round(freshness, 1),
            pnl_per_cycle=round(avg_pnl, 4),
            risk_score=round(avg_risk, 4),
            correlation=round(avg_corr, 4),
            system_health=1.0,
            cycle_count=self.total_cycles,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def log_metric(self, snapshot: MetricSnapshot) -> None:
        if self.log_dir is None:
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / "metrics.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(asdict(snapshot)) + "\n")

    def health(self) -> dict:
        s = self.snapshot()
        return {
            "status": "ok" if s.system_health > 0.5 else "degraded",
            "cycle_count": s.cycle_count,
            "error_rate": s.error_rate,
            "signal_freshness_sec": s.signal_freshness_sec,
            "uptime_sec": round(time.time() - self.last_metric_time, 1),
        }

    def metrics(self) -> dict:
        s = self.snapshot()
        return {
            "execution_latency_ms": s.execution_latency_ms,
            "error_rate": s.error_rate,
            "signal_freshness_sec": s.signal_freshness_sec,
            "pnl_per_cycle": s.pnl_per_cycle,
            "risk_score": s.risk_score,
            "correlation": s.correlation,
            "system_health": s.system_health,
            "cycle_count": s.cycle_count,
        }

    def summary(self) -> dict:
        s = self.snapshot()
        return {
            "status": "ok" if s.system_health > 0.5 else "degraded",
            "metrics": asdict(s),
            "window": self.window,
            "last_metric": s.timestamp,
        }

    def close(self) -> None:
        if self._log_fd:
            self._log_fd.close()
