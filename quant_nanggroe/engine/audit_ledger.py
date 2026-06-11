"""Audit Ledger — 3-sink fanout compliance audit (from Vibe-Trading pattern).

Every trading action is recorded in 3 sinks simultaneously:
1. Append-only JSONL ledger (compliance-grade, never deleted)
2. Per-run trace file (for debugging)
3. SSE event stream (for real-time monitoring)

All broker request/response data is REDACTED before write
to prevent credential leakage in audit logs.

This is a P0 requirement for any live trading system.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default audit directory
_DEFAULT_AUDIT_DIR = os.getenv("QNAI_AUDIT_DIR", "/tmp/qnai/audit")

# Sensitive fields to redact from audit logs
_REDACT_FIELDS = frozenset({
    "api_key", "secret", "password", "token", "authorization",
    "cookie", "private_key", "passphrase", "signature",
    "x-api-key", "x-auth-token",
})


class AuditEventType(str, Enum):
    """Types of auditable events."""
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    MANDATE_COMMITTED = "mandate_committed"
    MANDATE_BREACH = "mandate_breach"
    RISK_CHECK_PASSED = "risk_check_passed"
    RISK_CHECK_FAILED = "risk_check_failed"
    KILL_SWITCH_TRIPPED = "kill_switch_tripped"
    KILL_SWITCH_CLEARED = "kill_switch_cleared"
    TRADE_SIGNAL = "trade_signal"
    REGIME_CHANGE = "regime_change"
    AGENT_DECISION = "agent_decision"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"


class AuditOutcome(str, Enum):
    """Outcome of an auditable event."""
    ACCEPTED = "accepted"
    FILLED = "filled"
    REJECTED = "rejected"
    ERROR = "error"
    BLOCKED = "blocked"
    INFO = "info"


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event record.

    All broker-related data is redacted before this record
    is created, ensuring no credentials leak into the audit log.
    """
    event_type: AuditEventType
    session_id: str
    outcome: AuditOutcome
    symbol: str = ""
    quantity: float = 0.0
    price: float = 0.0
    notional: float = 0.0
    direction: str = ""
    agent_id: str = ""
    user_id: str = ""
    mandate_snapshot_ref: Optional[str] = None
    consent_record_ref: Optional[str] = None
    broker_request: Optional[Dict[str, Any]] = None  # REDACTED
    broker_response: Optional[Dict[str, Any]] = None  # REDACTED
    gate_decision: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def redact_dict(data: Any) -> Any:
    """Recursively redact sensitive fields from a dict.

    Replaces values of sensitive keys with '***REDACTED***'.
    """
    if not isinstance(data, dict):
        return data

    redacted = {}
    for key, value in data.items():
        key_lower = key.lower() if isinstance(key, str) else str(key).lower()
        if any(field in key_lower for field in _REDACT_FIELDS):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = [redact_dict(item) if isinstance(item, dict) else item for item in value]
        else:
            redacted[key] = value
    return redacted


class AuditLedger:
    """3-sink compliance audit ledger.

    Writes every trading event to:
    1. Append-only JSONL file (permanent compliance record)
    2. Per-run trace file (rotated daily)
    3. Optional callback (for SSE/websocket real-time streaming)

    Usage
    -----
        ledger = AuditLedger()

        ledger.record(AuditEvent(
            event_type=AuditEventType.ORDER_PLACED,
            session_id="sess-001",
            outcome=AuditOutcome.ACCEPTED,
            symbol="BTC/USDT",
            quantity=0.1,
            price=50000.0,
        ))
    """

    def __init__(
        self,
        audit_dir: Optional[str] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self._audit_dir = Path(audit_dir or _DEFAULT_AUDIT_DIR)
        self._event_callback = event_callback
        self._session_id = session_id or datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")

        # Ensure audit directory exists
        self._audit_dir.mkdir(parents=True, exist_ok=True)

        # Ledger file paths
        self._ledger_path = self._audit_dir / "audit_ledger.jsonl"
        self._trace_path = self._audit_dir / f"trace_{self._session_id}.jsonl"

        # Event counter for this session
        self._event_count = 0

        logger.info("Audit ledger initialized: %s (session: %s)", self._audit_dir, self._session_id)

    def record(self, event: AuditEvent) -> None:
        """Record an audit event to all 3 sinks.

        Parameters
        ----------
        event:
            Immutable audit event to record.
        """
        self._event_count += 1

        # Convert to dict with redaction
        record = asdict(event)
        record["_seq"] = self._event_count
        record["session_id"] = self._session_id

        # Redact sensitive fields
        if record.get("broker_request"):
            record["broker_request"] = redact_dict(record["broker_request"])
        if record.get("broker_response"):
            record["broker_response"] = redact_dict(record["broker_response"])

        record_json = json.dumps(record, default=str, ensure_ascii=False)

        # Sink 1: Append-only compliance ledger (always)
        try:
            with open(self._ledger_path, "a", encoding="utf-8") as f:
                f.write(record_json + "\n")
        except OSError as e:
            logger.error("Failed to write audit ledger: %s", e)

        # Sink 2: Per-run trace file
        try:
            with open(self._trace_path, "a", encoding="utf-8") as f:
                f.write(record_json + "\n")
        except OSError as e:
            logger.error("Failed to write trace file: %s", e)

        # Sink 3: Event callback (SSE/websocket)
        if self._event_callback:
            try:
                self._event_callback(record)
            except Exception as e:
                logger.warning("Audit event callback failed: %s", e)

    def record_simple(
        self,
        event_type: AuditEventType,
        outcome: AuditOutcome,
        symbol: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Convenience method for simple audit events.

        Parameters
        ----------
        event_type:
            Type of event.
        outcome:
            Event outcome.
        symbol:
            Trading symbol (if applicable).
        metadata:
            Additional metadata.
        """
        self.record(AuditEvent(
            event_type=event_type,
            session_id=self._session_id,
            outcome=outcome,
            symbol=symbol,
            metadata=metadata or {},
        ))

    @property
    def event_count(self) -> int:
        """Number of events recorded in this session."""
        return self._event_count

    @property
    def ledger_path(self) -> str:
        """Path to the compliance ledger file."""
        return str(self._ledger_path)

    @property
    def trace_path(self) -> str:
        """Path to the current run's trace file."""
        return str(self._trace_path)

    def query(
        self,
        event_type: Optional[AuditEventType] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query the audit ledger for specific events.

        Parameters
        ----------
        event_type:
            Filter by event type.
        symbol:
            Filter by symbol.
        limit:
            Maximum records to return.

        Returns
        -------
        list[dict]
            Matching audit records.
        """
        results = []
        try:
            with open(self._ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        if event_type and record.get("event_type") != event_type.value:
                            continue
                        if symbol and record.get("symbol") != symbol:
                            continue
                        results.append(record)
                        if len(results) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass

        return results
