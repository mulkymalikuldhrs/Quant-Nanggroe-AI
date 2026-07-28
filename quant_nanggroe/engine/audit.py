#!/usr/bin/env python3
"""
Audit Logger (from Quant-Nanggroe-AI)
=======================================
Full traceability across all decision layers.
Layers: MARKET → SENSOR → PRESSURE → DECISION → RISK → EXECUTION → SYSTEM
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("HermesQuantOS.AuditLogger")


class AuditEntry:
    """Audit entry with both attribute and dict-style access."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return key in self.__dict__

    def keys(self):
        return self.__dict__.keys()

    def __repr__(self):
        return repr(self.__dict__)


class AuditLogger:
    """
    Comprehensive audit trail across all decision layers.

    Source: Quant-Nanggroe-AI v5.1.0 Audit Logger
    Max 1000 entries per session, filterable by layer and severity.
    """

    LAYERS = ["MARKET", "SENSOR", "PRESSURE", "DECISION", "RISK", "EXECUTION", "SYSTEM"]
    SEVERITIES = ["INFO", "WARNING", "ERROR", "CRITICAL"]

    def __init__(self, max_entries: int = 1000, log_dir: str = None):
        self.entries: List[AuditEntry] = []
        self.max_entries = max_entries
        self.log_dir = Path(log_dir) if log_dir else None
        self.counts = {layer: 0 for layer in self.LAYERS}

    def log(self, layer: str, severity: str, message: str, details: Dict = None):
        """Log an audit entry"""
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
            timestamp=datetime.now().isoformat()
        )

        self.entries.append(entry)
        self.counts[layer] = self.counts.get(layer, 0) + 1

        # Trim if over max
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        # Also log to Python logger
        log_method = getattr(logger, severity.lower(), logger.info)
        log_method(f"[{layer}] {message}")

        return entry

    def get_entries(self, layer: str = None, severity: str = None,
                     limit: int = 50) -> List[AuditEntry]:
        """Get filtered audit entries"""
        filtered = self.entries

        if layer:
            filtered = [e for e in filtered if e.layer == layer]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        return filtered[-limit:]

    def get_summary(self) -> dict:
        """Get audit trail summary"""
        severity_counts = {}
        for s in self.SEVERITIES:
            severity_counts[s] = len([e for e in self.entries if e.severity == s])

        return {
            "total_entries": len(self.entries),
            "by_layer": self.counts,
            "by_severity": severity_counts,
            "recent_critical": [e for e in self.entries if e.severity == "CRITICAL"][-5:],
            "timestamp": datetime.now().isoformat()
        }

    def flush(self) -> str:
        """Flush audit trail to disk. Alias for save_to_file() for compatibility."""
        return self.save_to_file()

    def save_to_file(self, filepath: str = None) -> str:
        """Save audit trail to JSON file."""
        if filepath is None:
            if self.log_dir:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                filepath = str(self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            else:
                filepath = "audit_trail.json"

        with open(filepath, 'w') as f:
            json.dump({
                "summary": self.get_summary(),
                "entries": [dict(e.__dict__) for e in self.entries]
            }, f, indent=2)

        return filepath
