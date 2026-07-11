"""
Council Decision Logger — Persistent audit trail for multi-agent council decisions.

Logs every council debate result to a structured JSON log file with
query/filter capabilities for audit, compliance, and performance tracking.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CouncilDecision:
    """A single council decision record."""
    decision_id: str
    timestamp: str
    symbols: List[str]
    direction: str  # BUY, SELL, HOLD
    confidence: float
    reasoning: str
    agent_opinions: List[Dict[str, Any]]
    risk_metrics: Dict[str, Any]
    debate_rounds: int
    final_outcome: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CouncilDecisionLogger:
    """Thread-safe logger for council decisions with file-based persistence.

    Each decision is appended to a JSON Lines file for easy append/read.
    """

    def __init__(self, log_dir: Optional[str] = None):
        self._lock = threading.Lock()
        log_dir = log_dir or os.environ.get(
            "QNA_COUNCIL_LOG_DIR",
            str(Path.cwd() / "data" / "council_logs"),
        )
        self._log_path = Path(log_dir)
        self._log_path.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_path / "council_decisions.jsonl"
        self._sequence = 0

    def log_decision(self, decision: CouncilDecision) -> str:
        """Log a council decision and return its ID."""
        with self._lock:
            self._sequence += 1
            decision_id = f"CD-{self._sequence:06d}"
            decision.decision_id = decision_id
            record = decision.to_dict()
            record["logged_at"] = datetime.now(timezone.utc).isoformat()

            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            logger.info(f"Council decision logged: {decision_id} → {decision.direction} ({decision.confidence:.2f})")
            return decision_id

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the most recent council decisions."""
        if not self._log_file.exists():
            return []

        decisions = []
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    decisions.append(json.loads(line))

        return decisions[-limit:]

    def query_decisions(
        self,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query decisions with filters."""
        if not self._log_file.exists():
            return []

        results = []
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)

                if symbol and symbol not in record.get("symbols", []):
                    continue
                if direction and record.get("direction") != direction:
                    continue
                if record.get("confidence", 0) < min_confidence:
                    continue

                results.append(record)

        return results[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics of council decisions."""
        decisions = self.query_decisions(limit=10000)

        if not decisions:
            return {"total_decisions": 0}

        total = len(decisions)
        directions: Dict[str, int] = {}
        avg_confidence = 0.0

        for d in decisions:
            dir_ = d.get("direction", "UNKNOWN")
            directions[dir_] = directions.get(dir_, 0) + 1
            avg_confidence += d.get("confidence", 0)

        avg_confidence /= total if total else 1

        return {
            "total_decisions": total,
            "direction_counts": directions,
            "avg_confidence": round(avg_confidence, 4),
            "unique_symbols": len(set(
                s for d in decisions for s in d.get("symbols", [])
            )),
        }

    def clear(self) -> int:
        """Clear all logged decisions. Returns count removed."""
        with self._lock:
            count = 0
            if self._log_file.exists():
                with open(self._log_file, "r") as f:
                    count = sum(1 for line in f if line.strip())
                self._log_file.unlink(missing_ok=True)
            self._sequence = 0
            return count
