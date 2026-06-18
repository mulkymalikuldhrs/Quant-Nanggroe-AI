"""Tests for Audit Trail — Append-only audit logging.

All tests use in-memory SQLite databases — no file I/O required.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from quant_nanggroe.security.audit import AuditLogger, AuditRecord, DailyAuditReport


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def audit_logger():
    """Create an in-memory AuditLogger for testing."""
    logger = AuditLogger(db_path=None, auto_create=True)
    yield logger
    logger.close()


# ======================================================================
# AuditRecord
# ======================================================================

class TestAuditRecord:
    """Tests for the AuditRecord model."""

    def test_create_record(self):
        record = AuditRecord(
            agent="risk_agent",
            event_type="risk_check",
            symbol="BTC/USDT",
            action="check",
            verdict="approved",
        )
        assert record.agent == "risk_agent"
        assert record.event_type == "risk_check"
        assert record.symbol == "BTC/USDT"
        assert record.verdict == "approved"

    def test_default_values(self):
        record = AuditRecord()
        assert record.id is None
        assert record.agent == ""
        assert record.event_type == ""
        assert record.details == "{}"
        assert record.metadata == "{}"
        assert record.timestamp is not None

    def test_json_details(self):
        details = {"order_id": "123", "amount": 100.0}
        record = AuditRecord(
            agent="trader",
            event_type="order_placed",
            details=json.dumps(details),
        )
        parsed = json.loads(record.details)
        assert parsed["order_id"] == "123"


# ======================================================================
# Log Events
# ======================================================================

class TestLogEvents:
    """Tests for the log_event method."""

    @pytest.mark.asyncio
    async def test_log_basic_event(self, audit_logger):
        """Should log a basic audit event."""
        record = await audit_logger.log_event(
            agent="risk_agent",
            event_type="risk_check",
            symbol="BTC/USDT",
            verdict="approved",
        )
        assert record.id is not None
        assert record.id > 0
        assert record.agent == "risk_agent"
        assert record.event_type == "risk_check"
        assert record.symbol == "BTC/USDT"
        assert record.verdict == "approved"

    @pytest.mark.asyncio
    async def test_log_event_with_details(self, audit_logger):
        """Should log an event with JSON details."""
        record = await audit_logger.log_event(
            agent="trader",
            event_type="order_placed",
            symbol="ETH/USDT",
            action="buy",
            verdict="executed",
            details={"order_id": "ord-001", "amount": 1.5},
            metadata={"strategy": "momentum"},
        )
        assert record.agent == "trader"
        details = json.loads(record.details)
        assert details["order_id"] == "ord-001"
        metadata = json.loads(record.metadata)
        assert metadata["strategy"] == "momentum"

    @pytest.mark.asyncio
    async def test_log_event_auto_timestamp(self, audit_logger):
        """Should auto-generate timestamp."""
        record = await audit_logger.log_event(
            agent="test",
            event_type="test_event",
        )
        assert record.timestamp is not None
        # Should be close to now
        now = datetime.now(tz=timezone.utc)
        diff = abs((now - record.timestamp).total_seconds())
        assert diff < 5.0

    @pytest.mark.asyncio
    async def test_log_multiple_events(self, audit_logger):
        """Should log multiple events with auto-incrementing IDs."""
        r1 = await audit_logger.log_event(agent="a1", event_type="e1")
        r2 = await audit_logger.log_event(agent="a2", event_type="e2")
        r3 = await audit_logger.log_event(agent="a3", event_type="e3")
        assert r1.id < r2.id < r3.id


# ======================================================================
# Query Events
# ======================================================================

class TestQueryEvents:
    """Tests for the query method."""

    @pytest.mark.asyncio
    async def test_query_all(self, audit_logger):
        """Should return all events."""
        await audit_logger.log_event(agent="a1", event_type="e1")
        await audit_logger.log_event(agent="a2", event_type="e2")
        records = await audit_logger.query()
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_query_by_agent(self, audit_logger):
        """Should filter by agent."""
        await audit_logger.log_event(agent="risk_agent", event_type="e1")
        await audit_logger.log_event(agent="trader_agent", event_type="e2")
        records = await audit_logger.query(agent="risk_agent")
        assert len(records) == 1
        assert records[0].agent == "risk_agent"

    @pytest.mark.asyncio
    async def test_query_by_symbol(self, audit_logger):
        """Should filter by symbol."""
        await audit_logger.log_event(agent="a1", event_type="e1", symbol="BTC/USDT")
        await audit_logger.log_event(agent="a2", event_type="e2", symbol="ETH/USDT")
        records = await audit_logger.query(symbol="BTC/USDT")
        assert len(records) == 1
        assert records[0].symbol == "BTC/USDT"

    @pytest.mark.asyncio
    async def test_query_by_event_type(self, audit_logger):
        """Should filter by event type."""
        await audit_logger.log_event(agent="a1", event_type="risk_check")
        await audit_logger.log_event(agent="a2", event_type="order_placed")
        records = await audit_logger.query(event_type="risk_check")
        assert len(records) == 1
        assert records[0].event_type == "risk_check"

    @pytest.mark.asyncio
    async def test_query_by_verdict(self, audit_logger):
        """Should filter by verdict."""
        await audit_logger.log_event(agent="a1", event_type="risk_check", verdict="approved")
        await audit_logger.log_event(agent="a2", event_type="risk_check", verdict="rejected")
        records = await audit_logger.query(verdict="rejected")
        assert len(records) == 1
        assert records[0].verdict == "rejected"

    @pytest.mark.asyncio
    async def test_query_by_date_range(self, audit_logger):
        """Should filter by date range."""
        now = datetime.now(tz=timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        await audit_logger.log_event(agent="a1", event_type="e1")
        records = await audit_logger.query(start_date=yesterday, end_date=tomorrow)
        assert len(records) == 1

    @pytest.mark.asyncio
    async def test_query_with_limit(self, audit_logger):
        """Should respect the limit parameter."""
        for i in range(10):
            await audit_logger.log_event(agent="a1", event_type=f"e{i}")
        records = await audit_logger.query(limit=5)
        assert len(records) == 5

    @pytest.mark.asyncio
    async def test_query_combined_filters(self, audit_logger):
        """Should combine multiple filters."""
        await audit_logger.log_event(
            agent="risk_agent", event_type="risk_check",
            symbol="BTC/USDT", verdict="approved"
        )
        await audit_logger.log_event(
            agent="risk_agent", event_type="risk_check",
            symbol="ETH/USDT", verdict="rejected"
        )
        records = await audit_logger.query(
            agent="risk_agent",
            verdict="approved",
        )
        assert len(records) == 1
        assert records[0].symbol == "BTC/USDT"


# ======================================================================
# Get Record
# ======================================================================

class TestGetRecord:
    """Tests for the get_record method."""

    @pytest.mark.asyncio
    async def test_get_existing_record(self, audit_logger):
        """Should return a specific record by ID."""
        created = await audit_logger.log_event(
            agent="test", event_type="test_event"
        )
        fetched = await audit_logger.get_record(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.agent == "test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_record(self, audit_logger):
        """Should return None for non-existent ID."""
        result = await audit_logger.get_record(99999)
        assert result is None


# ======================================================================
# Count
# ======================================================================

class TestCount:
    """Tests for the count method."""

    @pytest.mark.asyncio
    async def test_count_all(self, audit_logger):
        """Should count all records."""
        await audit_logger.log_event(agent="a1", event_type="e1")
        await audit_logger.log_event(agent="a2", event_type="e2")
        count = await audit_logger.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_by_agent(self, audit_logger):
        """Should count records by agent."""
        await audit_logger.log_event(agent="a1", event_type="e1")
        await audit_logger.log_event(agent="a1", event_type="e2")
        await audit_logger.log_event(agent="a2", event_type="e3")
        count = await audit_logger.count(agent="a1")
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_by_event_type(self, audit_logger):
        """Should count records by event type."""
        await audit_logger.log_event(agent="a1", event_type="risk_check")
        await audit_logger.log_event(agent="a2", event_type="risk_check")
        await audit_logger.log_event(agent="a3", event_type="order_placed")
        count = await audit_logger.count(event_type="risk_check")
        assert count == 2


# ======================================================================
# Daily Audit Report
# ======================================================================

class TestDailyAuditReport:
    """Tests for the daily audit report generation."""

    @pytest.mark.asyncio
    async def test_generate_report(self, audit_logger):
        """Should generate a daily report."""
        await audit_logger.log_event(
            agent="risk_agent", event_type="risk_check",
            symbol="BTC/USDT", verdict="approved",
        )
        await audit_logger.log_event(
            agent="trader_agent", event_type="order_placed",
            symbol="BTC/USDT", verdict="executed",
        )
        await audit_logger.log_event(
            agent="risk_agent", event_type="risk_check",
            symbol="ETH/USDT", verdict="rejected",
        )

        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        report = await audit_logger.generate_daily_report(date=today)

        assert isinstance(report, DailyAuditReport)
        assert report.total_events == 3
        assert report.events_by_type.get("risk_check") == 2
        assert report.events_by_type.get("order_placed") == 1
        assert report.events_by_agent.get("risk_agent") == 2
        assert report.risk_rejections == 1
        assert report.orders_placed == 1
        assert "BTC/USDT" in report.symbols_traded

    @pytest.mark.asyncio
    async def test_generate_report_default_date(self, audit_logger):
        """Should use today's date by default."""
        await audit_logger.log_event(agent="a1", event_type="e1")
        report = await audit_logger.generate_daily_report()
        assert report.total_events == 1
        assert report.date == datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    @pytest.mark.asyncio
    async def test_generate_report_empty_day(self, audit_logger):
        """Should handle days with no events."""
        report = await audit_logger.generate_daily_report(date="2000-01-01")
        assert report.total_events == 0
        assert report.symbols_traded == []
        assert report.risk_rejections == 0


# ======================================================================
# Immutability
# ======================================================================

class TestAuditImmutability:
    """Tests verifying that the audit log is append-only."""

    @pytest.mark.asyncio
    async def test_no_update_method(self, audit_logger):
        """AuditLogger should not have an update method."""
        assert not hasattr(audit_logger, "update_record")
        assert not hasattr(audit_logger, "update")

    @pytest.mark.asyncio
    async def test_no_delete_method(self, audit_logger):
        """AuditLogger should not have a delete method."""
        assert not hasattr(audit_logger, "delete_record")
        assert not hasattr(audit_logger, "delete")


# ======================================================================
# Close
# ======================================================================

class TestAuditLoggerClose:
    """Tests for AuditLogger cleanup."""

    def test_close(self, audit_logger):
        """Should close the database connection."""
        audit_logger.close()
        assert audit_logger._conn is None

    def test_repr(self, audit_logger):
        """Test AuditLogger repr."""
        result = repr(audit_logger)
        assert "AuditLogger" in result
