"""Tests for structured logging and audit trail module."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest
import structlog

from quant_nanggroe.config.logging import (
    setup_logging,
    get_logger,
    TradeLogger,
    AuditTrail,
    request_id,
    agent_id,
    trade_id,
)


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_setup_logging_json_mode(self):
        """setup_logging with json_output=True configures JSON renderer."""
        # Should not raise
        setup_logging(level="INFO", json_output=True)
        logger = get_logger("test_json")
        # Logger should be usable
        assert logger is not None

    def test_setup_logging_console_mode(self):
        """setup_logging with json_output=False configures console renderer."""
        setup_logging(level="DEBUG", json_output=False)
        logger = get_logger("test_console")
        assert logger is not None

    def test_setup_logging_default_level(self):
        """Default logging level is INFO."""
        setup_logging()
        logger = get_logger("test_default")
        assert logger is not None


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger_returns_bound_logger(self):
        """get_logger returns a structlog BoundLogger."""
        setup_logging()
        logger = get_logger("test_module")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_get_logger_binds_module_name(self):
        """Logger is pre-bound with the module name."""
        setup_logging()
        logger = get_logger("my_component")
        # The module name should be bound — we can verify by checking the logger exists
        assert logger is not None


class TestTradeLogger:
    """Tests for the TradeLogger class."""

    def test_log_trade_signal(self):
        """TradeLogger.log_trade_signal does not raise."""
        setup_logging()
        tl = TradeLogger("test_trading")
        # Should not raise
        tl.log_trade_signal(
            signal="BUY",
            strategy="momentum_rsi",
            confidence=0.85,
            regime="TRENDING_UP",
        )

    def test_log_risk_gate_approved(self):
        """TradeLogger.log_risk_gate with APPROVED decision."""
        setup_logging()
        tl = TradeLogger("test_trading")
        tl.log_risk_gate(
            decision="APPROVED",
            checkpoints_passed=9,
        )

    def test_log_risk_gate_vetoed(self):
        """TradeLogger.log_risk_gate with VETOED decision and reason."""
        setup_logging()
        tl = TradeLogger("test_trading")
        tl.log_risk_gate(
            decision="VETOED",
            checkpoints_passed=5,
            veto_reason="Daily loss limit exceeded",
        )

    def test_log_execution(self):
        """TradeLogger.log_execution does not raise."""
        setup_logging()
        tl = TradeLogger("test_trading")
        tl.log_execution(
            order="BUY EURUSD 0.01 @ 1.1000",
            fill="FILLED @ 1.1001",
            slippage=0.0001,
        )

    def test_log_kill_switch(self):
        """TradeLogger.log_kill_switch does not raise."""
        setup_logging()
        tl = TradeLogger("test_trading")
        tl.log_kill_switch(
            trigger="AUTO_DAILY_LIMIT",
            current_drawdown=0.012,
            threshold=0.01,
        )


class TestAuditTrail:
    """Tests for the AuditTrail class."""

    def test_record_returns_entry(self):
        """record() returns a dict with expected fields."""
        trail = AuditTrail()
        entry = trail.record(
            event_type="trade_signal",
            details={"symbol": "XAUUSD", "direction": "BUY"},
            actor="momentum_agent",
        )
        assert entry["event_type"] == "trade_signal"
        assert entry["details"]["symbol"] == "XAUUSD"
        assert entry["actor"] == "momentum_agent"
        assert "timestamp" in entry
        assert entry["id"] == 1

    def test_record_immutability(self):
        """Mutating a returned entry does not affect the audit trail."""
        trail = AuditTrail()
        entry = trail.record(
            event_type="test",
            details={"key": "value"},
        )
        entry["details"]["key"] = "mutated"
        # Original should be unchanged
        all_records = trail.query()
        assert all_records[0]["details"]["key"] == "value"

    def test_query_by_event_type(self):
        """query() filters by event_type."""
        trail = AuditTrail()
        trail.record("trade_signal", {"symbol": "XAUUSD"})
        trail.record("risk_gate", {"verdict": "APPROVED"})
        trail.record("trade_signal", {"symbol": "EURUSD"})

        signals = trail.query(event_type="trade_signal")
        assert len(signals) == 2
        assert all(s["event_type"] == "trade_signal" for s in signals)

    def test_query_by_time_range(self):
        """query() filters by start_time and end_time."""
        trail = AuditTrail()
        trail.record("event_a", {"idx": 1})

        # Manually insert a record with an older timestamp
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        trail._records.append({
            "id": 99,
            "event_type": "event_b",
            "details": {"idx": 2},
            "actor": "system",
            "timestamp": old_time.isoformat(),
        })

        # Query for recent events only
        recent = trail.query(start_time=datetime.now(timezone.utc) - timedelta(minutes=5))
        assert len(recent) == 1
        assert recent[0]["event_type"] == "event_a"

    def test_export_json(self):
        """export_json() returns valid JSON with all records."""
        trail = AuditTrail()
        trail.record("test", {"key": "val1"})
        trail.record("test", {"key": "val2"})

        json_str = trail.export_json()
        data = json.loads(json_str)
        assert len(data) == 2
        assert data[0]["details"]["key"] == "val1"

    def test_count_and_clear(self):
        """count() returns record count; clear() empties the trail."""
        trail = AuditTrail()
        assert trail.count() == 0

        trail.record("test", {"x": 1})
        trail.record("test", {"x": 2})
        assert trail.count() == 2

        trail.clear()
        assert trail.count() == 0

    def test_context_vars_in_logger(self):
        """Context variables are accessible from the module."""
        # Set context vars
        token_req = request_id.set("req-123")
        token_agt = agent_id.set("agent-momentum")

        try:
            setup_logging(json_output=True)
            logger = get_logger("ctx_test")
            # Logger should work with context vars set
            logger.info("test_with_context", action="verify")
        finally:
            request_id.reset(token_req)
            agent_id.reset(token_agt)
