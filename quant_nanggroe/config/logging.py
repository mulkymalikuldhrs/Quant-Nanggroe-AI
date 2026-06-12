"""Structured logging and audit trail for Quant-Nanggroe-AI.

Provides:
- setup_logging(): Configure structlog for structured JSON (prod) or console (dev) output
- get_logger(): Get a named structlog logger bound with module context
- TradeLogger: Specialized logger for trade decisions
- AuditTrail: Immutable audit log for compliance

This module is separate from logging_config.py (which handles basic structlog setup).
This module adds context variables, trade-specific logging, and compliance audit trails.
"""

from __future__ import annotations

import copy
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

# ── Context variables for request/trade correlation ──────────────────────

request_id: ContextVar[str] = ContextVar("request_id", default="")
agent_id: ContextVar[str] = ContextVar("agent_id", default="")
trade_id: ContextVar[str] = ContextVar("trade_id", default="")


# ── Custom processors ────────────────────────────────────────────────────


def _add_context_vars(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject context variables into every log entry."""
    req = request_id.get("")
    if req:
        event_dict["request_id"] = req
    agt = agent_id.get("")
    if agt:
        event_dict["agent_id"] = agt
    tid = trade_id.get("")
    if tid:
        event_dict["trade_id"] = tid
    return event_dict


def _add_timestamp(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO-8601 UTC timestamp to every log entry."""
    event_dict.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    return event_dict


# ── Setup ────────────────────────────────────────────────────────────────


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
) -> None:
    """Configure structlog for structured logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: If True, render logs as JSON (for production).
                     If False, render as human-readable console (for development).
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_context_vars,
        _add_timestamp,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger bound with module name.

    Args:
        name: Module or component name for the logger.

    Returns:
        A structlog BoundLogger with the module name pre-bound.
    """
    return structlog.get_logger().bind(module=name)


# ── TradeLogger ──────────────────────────────────────────────────────────


class TradeLogger:
    """Specialized logger for trade decisions.

    Provides structured logging methods for each stage of the trade lifecycle:
    - signal generation
    - risk gate evaluation
    - order execution
    - kill switch activation
    """

    def __init__(self, name: str = "trading") -> None:
        self.log = get_logger(name)

    def log_trade_signal(
        self,
        signal: str,
        strategy: str,
        confidence: float,
        regime: str,
    ) -> None:
        """Log a trade signal generation event.

        Args:
            signal: Signal type (BUY, SELL, NEUTRAL).
            strategy: Strategy name that generated the signal.
            confidence: Signal confidence (0-1).
            regime: Current market regime.
        """
        self.log.info(
            "trade_signal",
            signal=signal,
            strategy=strategy,
            confidence=round(confidence, 4),
            regime=regime,
        )

    def log_risk_gate(
        self,
        decision: str,
        checkpoints_passed: int,
        veto_reason: Optional[str] = None,
    ) -> None:
        """Log a risk gate evaluation event.

        Args:
            decision: Risk gate verdict (APPROVED, VETOED).
            checkpoints_passed: Number of checkpoints that passed.
            veto_reason: Reason for veto if applicable.
        """
        entry: dict[str, Any] = {
            "decision": decision,
            "checkpoints_passed": checkpoints_passed,
        }
        if veto_reason:
            entry["veto_reason"] = veto_reason
        self.log.info("risk_gate", **entry)

    def log_execution(
        self,
        order: str,
        fill: str,
        slippage: float,
    ) -> None:
        """Log an order execution event.

        Args:
            order: Order description.
            fill: Fill description.
            slippage: Execution slippage in pips or basis points.
        """
        self.log.info(
            "execution",
            order=order,
            fill=fill,
            slippage=round(slippage, 4),
        )

    def log_kill_switch(
        self,
        trigger: str,
        current_drawdown: float,
        threshold: float,
    ) -> None:
        """Log a kill switch activation event.

        Args:
            trigger: What triggered the kill switch.
            current_drawdown: Current drawdown percentage.
            threshold: Drawdown threshold that was breached.
        """
        self.log.critical(
            "kill_switch",
            trigger=trigger,
            current_drawdown=round(current_drawdown, 4),
            threshold=round(threshold, 4),
        )


# ── AuditTrail ───────────────────────────────────────────────────────────


class AuditTrail:
    """Immutable audit log for compliance.

    Every record is stored with a timestamp, event type, actor, and details.
    Records are deep-copied on insertion to prevent mutation of audit data.

    Usage::

        trail = AuditTrail()
        trail.record("trade_signal", {"symbol": "XAUUSD", "direction": "BUY"})
        trail.record("risk_gate", {"verdict": "APPROVED", "checkpoints": 9})

        # Query by event type
        signals = trail.query(event_type="trade_signal")

        # Export for compliance
        json_export = trail.export_json()
    """

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def record(
        self,
        event_type: str,
        details: dict[str, Any],
        actor: str = "system",
    ) -> dict[str, Any]:
        """Record an immutable audit event.

        Args:
            event_type: Type of event (e.g., "trade_signal", "risk_gate").
            details: Event details dictionary.
            actor: Who or what triggered the event.

        Returns:
            The recorded audit entry (deep copy).
        """
        entry: dict[str, Any] = {
            "id": len(self._records) + 1,
            "event_type": event_type,
            "details": copy.deepcopy(details),
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._records.append(entry)
        return copy.deepcopy(entry)

    def query(
        self,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Query audit records with optional filters.

        Args:
            event_type: Filter by event type.
            start_time: Filter records after this time.
            end_time: Filter records before this time.

        Returns:
            List of matching audit records (deep copies).
        """
        results: list[dict[str, Any]] = []
        for rec in self._records:
            if event_type and rec["event_type"] != event_type:
                continue
            if start_time or end_time:
                rec_time = datetime.fromisoformat(rec["timestamp"])
                if start_time and rec_time < start_time:
                    continue
                if end_time and rec_time > end_time:
                    continue
            results.append(copy.deepcopy(rec))
        return results

    def export_json(self) -> str:
        """Export all audit records as a JSON string.

        Returns:
            JSON-formatted string of all records.
        """
        return json.dumps(self._records, indent=2, default=str)

    def count(self) -> int:
        """Return the total number of audit records."""
        return len(self._records)

    def clear(self) -> None:
        """Clear all audit records.

        WARNING: This destroys the audit trail. Use only in testing.
        """
        self._records.clear()
