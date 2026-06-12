"""
Audit Logger — Full Traceability Across All Decision Layers
=============================================================
From Quant-Nanggroe-AI — Layers: MARKET → SENSOR → PRESSURE → DECISION → RISK → EXECUTION → SYSTEM

Max 1000 entries per session, filterable by layer and severity.
Supports file-based persistence via flush() for crash recovery.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEntry(BaseModel):
    """Single audit trail entry."""

    id: int
    layer: str
    severity: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class AuditLogger:
    """
    Comprehensive audit trail across all decision layers.

    Layers: MARKET, SENSOR, PRESSURE, DECISION, RISK, EXECUTION, SYSTEM
    Severities: INFO, WARNING, ERROR, CRITICAL

    Max 1000 entries per session by default. Filterable by layer and severity.
    Can persist to file for crash recovery.
    """

    LAYERS = ["MARKET", "SENSOR", "PRESSURE", "DECISION", "RISK", "EXECUTION", "SYSTEM"]
    SEVERITIES = ["INFO", "WARNING", "ERROR", "CRITICAL"]

    def __init__(self, max_entries: int = 1000, log_dir: str | None = None) -> None:
        self.entries: list[AuditEntry] = []
        self.max_entries = max_entries
        self.log_dir = Path(log_dir) if log_dir else None
        self.counts: dict[str, int] = {layer: 0 for layer in self.LAYERS}

    def log(
        self,
        layer: str,
        severity: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """
        Log an audit entry.

        Args:
            layer: Decision layer (MARKET, SENSOR, PRESSURE, DECISION, RISK, EXECUTION, SYSTEM)
            severity: Severity level (INFO, WARNING, ERROR, CRITICAL)
            message: Human-readable message
            details: Optional structured details

        Returns:
            The created AuditEntry
        """
        if layer not in self.LAYERS:
            layer = "SYSTEM"
        if severity not in self.SEVERITIES:
            severity = "INFO"

        entry = AuditEntry(
            id=len(self.entries) + 1,
            layer=layer,
            severity=severity,
            message=message,
            details=details or {},
        )

        self.entries.append(entry)
        self.counts[layer] = self.counts.get(layer, 0) + 1

        # Trim if over max
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        return entry

    def get_entries(
        self,
        layer: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[AuditEntry]:
        """Get filtered audit entries."""
        filtered = self.entries

        if layer:
            filtered = [e for e in filtered if e.layer == layer]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        return filtered[-limit:]

    def get_summary(self) -> dict[str, Any]:
        """Get audit trail summary."""
        severity_counts = {s: len([e for e in self.entries if e.severity == s]) for s in self.SEVERITIES}

        return {
            "total_entries": len(self.entries),
            "by_layer": self.counts,
            "by_severity": severity_counts,
            "recent_critical": [e.model_dump() for e in self.entries if e.severity == "CRITICAL"][-5:],
            "timestamp": datetime.now().isoformat(),
        }

    def save_to_file(self) -> None:
        """Save audit trail to JSON file."""
        if not self.log_dir:
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.json"
        filepath.write_text(
            json.dumps(
                {"summary": self.get_summary(), "entries": [e.model_dump() for e in self.entries]},
                indent=2,
                default=str,
            )
        )

    def flush(self) -> None:
        """Write audit log entries to disk as JSONL for crash recovery.

        Appends the most recent entries to a JSONL file, ensuring audit
        records survive process crashes.  The file path is configurable
        via the ``QNAI_AUDIT_FILE`` environment variable (defaults to
        ``/tmp/qnai_audit.jsonl``).

        Only the last 100 entries are flushed to keep file size bounded.
        """
        try:
            audit_file = os.environ.get("QNAI_AUDIT_FILE", "/tmp/qnai_audit.jsonl")
            entries_to_flush = self.entries[-100:]
            with open(audit_file, "a") as f:
                for entry in entries_to_flush:
                    f.write(json.dumps(entry.model_dump(), default=str) + "\n")
            logger.info("audit_flushed: entries=%d, file=%s", len(entries_to_flush), audit_file)
        except Exception as e:
            logger.warning("audit_flush_error: %s", e)
