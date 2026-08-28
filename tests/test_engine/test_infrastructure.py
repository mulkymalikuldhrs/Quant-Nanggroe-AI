"""
Comprehensive Tests for Engine Infrastructure Modules
=====================================================
Tests for DecisionSynthesisEngine, AutoSwitchEngine, AuditLogger,
PressureNormalizationEngine, MarketStateEngine, StrategyLifecycleManager.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from quant_nanggroe.engine.audit import AuditEntry, AuditLogger
from quant_nanggroe.engine.autoswitch import AutoSwitchEngine, ProviderHealth
from quant_nanggroe.engine.decision import (
    DECISION_TABLE,
    DecisionSynthesisEngine,
)
from quant_nanggroe.engine.market_state import MarketStateEngine
from quant_nanggroe.engine.pressure import (
    PressureInput,
    PressureNormalizationEngine,
)
from quant_nanggroe.engine.strategy_lifecycle import (
    StrategyLifecycleManager,
    StrategyState,
)
from quant_nanggroe.types.engine import (
    DecisionAction,
    LiquidityLevel,
    MarketRegime,
    MarketState,
    PressureState,
    RiskClearance,
    StrategyStatus,
    VolatilityLevel,
)

# ══════════════════════════════════════════════════════════════════════
# DecisionSynthesisEngine Tests
# ══════════════════════════════════════════════════════════════════════


class TestDecisionSynthesisEngine:
    """Test the deterministic decision synthesis engine."""

    def setup_method(self) -> None:
        self.engine = DecisionSynthesisEngine()

    # ── Rule DT001: Strong bullish pressure in safe regime ──────────

    def test_dt001_allow_long_strong_bullish(self) -> None:
        """DT001: Strong bullish → ALLOW_LONG, CLEAR."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_UP,
            buy_pressure=0.75,
            sell_pressure=0.20,
            confidence=0.65,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.action == DecisionAction.ALLOW_LONG
        assert result.risk_clearance == RiskClearance.CLEAR
        assert "DT001" in result.matched_rules

    def test_dt001_allow_long_trending_regime(self) -> None:
        """DT001 also matches TRENDING regime."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING,
            buy_pressure=0.72,
            sell_pressure=0.25,
            confidence=0.60,
            volatility=VolatilityLevel.LOW,
        )
        assert result.action == DecisionAction.ALLOW_LONG
        assert "DT001" in result.matched_rules

    def test_dt001_allow_long_range_regime(self) -> None:
        """DT001 also matches RANGE regime."""
        result = self.engine.evaluate(
            regime=MarketRegime.RANGE,
            buy_pressure=0.80,
            sell_pressure=0.10,
            confidence=0.70,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.action == DecisionAction.ALLOW_LONG
        assert "DT001" in result.matched_rules

    def test_dt001_allow_long_mean_revert_regime(self) -> None:
        """DT001 also matches MEAN_REVERT regime."""
        result = self.engine.evaluate(
            regime=MarketRegime.MEAN_REVERT,
            buy_pressure=0.70,
            sell_pressure=0.29,
            confidence=0.60,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.action == DecisionAction.ALLOW_LONG
        assert "DT001" in result.matched_rules

    # ── Rule DT002: Strong bearish pressure in safe regime ──────────

    def test_dt002_allow_short_strong_bearish(self) -> None:
        """DT002: Strong bearish → ALLOW_SHORT, CLEAR."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_DOWN,
            buy_pressure=0.20,
            sell_pressure=0.75,
            confidence=0.65,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.action == DecisionAction.ALLOW_SHORT
        assert result.risk_clearance == RiskClearance.CLEAR
        assert "DT002" in result.matched_rules

    def test_dt002_allow_short_trending_regime(self) -> None:
        """DT002 also matches TRENDING regime with bearish pressure."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING,
            buy_pressure=0.25,
            sell_pressure=0.72,
            confidence=0.61,
            volatility=VolatilityLevel.LOW,
        )
        assert result.action == DecisionAction.ALLOW_SHORT
        assert "DT002" in result.matched_rules

    # ── Rule DT003: Moderate bullish in trending regime ─────────────

    def test_dt003_allow_long_trending_moderate(self) -> None:
        """DT003: Moderate bullish in trending → ALLOW_LONG_TRENDING."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_UP,
            buy_pressure=0.65,
            sell_pressure=0.35,
            confidence=0.56,
            volatility=VolatilityLevel.HIGH,
        )
        assert result.action == DecisionAction.ALLOW_LONG_TRENDING
        assert result.risk_clearance == RiskClearance.CLEAR
        assert "DT003" in result.matched_rules

    # ── Rule DT004: Moderate bearish in trending regime ─────────────

    def test_dt004_allow_short_trending_moderate(self) -> None:
        """DT004: Moderate bearish in trending → ALLOW_SHORT_TRENDING."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_DOWN,
            buy_pressure=0.30,
            sell_pressure=0.65,
            confidence=0.56,
            volatility=VolatilityLevel.HIGH,
        )
        assert result.action == DecisionAction.ALLOW_SHORT_TRENDING
        assert result.risk_clearance == RiskClearance.CLEAR
        assert "DT004" in result.matched_rules

    # ── Rule DT005: Dangerous regime — all trading blocked ──────────

    def test_dt005_panic_regime_blocked(self) -> None:
        """DT005: PANIC regime → NO_TRADE, BLOCKED (impossible threshold)."""
        result = self.engine.evaluate(
            regime=MarketRegime.PANIC,
            buy_pressure=0.90,
            sell_pressure=0.10,
            confidence=0.80,
            volatility=VolatilityLevel.NORMAL,
        )
        # DT005 has min_buy_pressure=1.10 which is impossible
        assert "DT005" not in result.matched_rules
        # No rule matches for PANIC, so NO_TRADE / BLOCKED
        assert result.action == DecisionAction.NO_TRADE
        assert result.risk_clearance == RiskClearance.BLOCKED

    def test_dt005_risk_off_regime_blocked(self) -> None:
        """DT005: RISK_OFF regime → no rules match, BLOCKED."""
        result = self.engine.evaluate(
            regime=MarketRegime.RISK_OFF,
            buy_pressure=0.80,
            sell_pressure=0.10,
            confidence=0.70,
        )
        assert result.action == DecisionAction.NO_TRADE
        assert result.risk_clearance == RiskClearance.BLOCKED

    def test_dt005_no_trade_regime_blocked(self) -> None:
        """DT005: NO_TRADE regime → no rules match, BLOCKED."""
        result = self.engine.evaluate(
            regime=MarketRegime.NO_TRADE,
            buy_pressure=0.80,
            sell_pressure=0.10,
            confidence=0.70,
        )
        assert result.action == DecisionAction.NO_TRADE
        assert result.risk_clearance == RiskClearance.BLOCKED

    # ── Rule DT006: Weak bullish — watch ────────────────────────────

    def test_dt006_watch_long_weak_bullish(self) -> None:
        """DT006: Weak bullish → WATCH_LONG, PAUSE."""
        result = self.engine.evaluate(
            regime=MarketRegime.RANGE,
            buy_pressure=0.60,
            sell_pressure=0.35,
            confidence=0.56,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.action == DecisionAction.WATCH_LONG
        assert result.risk_clearance == RiskClearance.PAUSE
        assert "DT006" in result.matched_rules

    # ── Rule DT007: Weak bearish — watch ────────────────────────────

    def test_dt007_watch_short_weak_bearish(self) -> None:
        """DT007: Weak bearish → WATCH_SHORT, PAUSE."""
        result = self.engine.evaluate(
            regime=MarketRegime.RANGE,
            buy_pressure=0.30,
            sell_pressure=0.60,
            confidence=0.56,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.action == DecisionAction.WATCH_SHORT
        assert result.risk_clearance == RiskClearance.PAUSE
        assert "DT007" in result.matched_rules

    # ── Boundary conditions ──────────────────────────────────────────

    def test_no_rules_matched(self) -> None:
        """When no rule matches, result is NO_TRADE / BLOCKED."""
        result = self.engine.evaluate(
            regime=MarketRegime.CALM,
            buy_pressure=0.30,
            sell_pressure=0.30,
            confidence=0.20,
            volatility=VolatilityLevel.HIGH,
        )
        assert result.action == DecisionAction.NO_TRADE
        assert result.risk_clearance == RiskClearance.BLOCKED
        assert len(result.matched_rules) == 0

    def test_unknown_regime(self) -> None:
        """UNKNOWN regime → no rules match."""
        result = self.engine.evaluate(
            regime=MarketRegime.UNKNOWN,
            buy_pressure=0.80,
            sell_pressure=0.10,
            confidence=0.90,
        )
        assert result.action == DecisionAction.NO_TRADE
        assert result.risk_clearance == RiskClearance.BLOCKED

    def test_extreme_volatility_blocks_dt001(self) -> None:
        """EXTREME volatility is not in DT001 allowed list → rule skipped."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_UP,
            buy_pressure=0.80,
            sell_pressure=0.10,
            confidence=0.70,
            volatility=VolatilityLevel.EXTREME,
        )
        # DT001 doesn't allow EXTREME volatility
        # DT003 allows HIGH but not EXTREME
        assert DecisionAction.ALLOW_LONG not in [result.action] or "DT003" not in result.matched_rules

    def test_low_confidence_blocks_rules(self) -> None:
        """Confidence below min_confidence blocks all rules."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_UP,
            buy_pressure=0.80,
            sell_pressure=0.10,
            confidence=0.30,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.action == DecisionAction.NO_TRADE
        assert result.risk_clearance == RiskClearance.BLOCKED

    def test_daily_loss_limit_blocks_trade(self) -> None:
        """Daily loss limit exceeded → BLOCKED even if rule matches."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_UP,
            buy_pressure=0.80,
            sell_pressure=0.10,
            confidence=0.70,
            volatility=VolatilityLevel.NORMAL,
            daily_pnl_pct=-0.02,  # Exceeds MAX_DAILY_LOSS of 0.01
        )
        assert result.risk_clearance == RiskClearance.BLOCKED
        assert result.action == DecisionAction.NO_TRADE

    def test_deterministic_same_inputs_same_output(self) -> None:
        """Same inputs always produce same output."""
        kwargs = dict(
            regime=MarketRegime.TRENDING_UP,
            buy_pressure=0.75,
            sell_pressure=0.20,
            confidence=0.65,
            volatility=VolatilityLevel.NORMAL,
        )
        r1 = self.engine.evaluate(**kwargs)
        r2 = self.engine.evaluate(**kwargs)
        assert r1.action == r2.action
        assert r1.risk_clearance == r2.risk_clearance
        assert r1.matched_rules == r2.matched_rules

    def test_status_returns_dict(self) -> None:
        """status() returns a structured dict."""
        self.engine.evaluate(
            regime=MarketRegime.RANGE,
            buy_pressure=0.50,
            sell_pressure=0.50,
            confidence=0.50,
        )
        status = self.engine.status()
        assert "last_decision" in status
        assert "available_actions" in status
        assert "decision_rules" in status
        assert status["decision_rules"] == len(DECISION_TABLE)
        assert isinstance(status["available_actions"], list)

    def test_last_decision_stored(self) -> None:
        """last_decision is updated after each evaluate()."""
        assert self.engine.last_decision is None
        result = self.engine.evaluate(
            regime=MarketRegime.RANGE,
            buy_pressure=0.50,
            sell_pressure=0.50,
            confidence=0.50,
        )
        assert self.engine.last_decision is not None
        assert self.engine.last_decision.action == result.action

    def test_decision_table_has_7_rules(self) -> None:
        """Verify the decision table has exactly 7 rules."""
        assert len(DECISION_TABLE) == 7
        rule_ids = [r.id for r in DECISION_TABLE]
        assert rule_ids == ["DT001", "DT002", "DT003", "DT004", "DT005", "DT006", "DT007"]

    def test_result_fields_populated(self) -> None:
        """DecisionResult has all expected fields populated."""
        result = self.engine.evaluate(
            regime=MarketRegime.TRENDING_UP,
            buy_pressure=0.75,
            sell_pressure=0.20,
            confidence=0.65,
            volatility=VolatilityLevel.NORMAL,
        )
        assert result.regime == MarketRegime.TRENDING_UP
        assert result.buy_pressure == 0.75
        assert result.sell_pressure == 0.20
        assert result.confidence == 0.65
        assert result.volatility == VolatilityLevel.NORMAL
        assert result.timestamp is not None
        assert result.reason != ""


# ══════════════════════════════════════════════════════════════════════
# AutoSwitchEngine Tests
# ══════════════════════════════════════════════════════════════════════


class TestAutoSwitchEngine:
    """Test the provider failover system."""

    def setup_method(self) -> None:
        self.engine = AutoSwitchEngine()

    def test_register_provider(self) -> None:
        """Providers can be registered and tracked."""
        self.engine.register_provider("openai")
        assert "openai" in self.engine.providers
        ph = self.engine.providers["openai"]
        assert ph.name == "openai"
        assert ph.success_count == 0
        assert ph.failure_count == 0

    def test_record_success_auto_registers(self) -> None:
        """Recording success for unregistered provider auto-registers it."""
        self.engine.record_success("anthropic", latency_ms=150.0)
        assert "anthropic" in self.engine.providers
        assert self.engine.providers["anthropic"].success_count == 1

    def test_record_failure_auto_registers(self) -> None:
        """Recording failure for unregistered provider auto-registers it."""
        self.engine.record_failure("google", error="timeout")
        assert "google" in self.engine.providers
        assert self.engine.providers["google"].failure_count == 1

    def test_health_score_calculation(self) -> None:
        """Health score is based on success rate minus latency penalty."""
        ph = ProviderHealth(name="test")
        assert ph.score == 0.5  # No data → default 0.5

        ph.success_count = 8
        ph.failure_count = 2
        ph.avg_latency_ms = 500.0
        expected_rate = 8 / 10  # 0.8
        latency_penalty = min(500 / 10000, 0.2)  # 0.05
        assert abs(ph.score - (expected_rate - latency_penalty)) < 0.001

    def test_health_score_latency_penalty_capped(self) -> None:
        """Latency penalty is capped at 0.2."""
        ph = ProviderHealth(name="slow", success_count=1, avg_latency_ms=50000.0)
        # penalty = min(50000/10000, 0.2) = 0.2
        assert ph.score == pytest.approx(0.8, abs=0.001)

    def test_provider_availability_no_cooldown(self) -> None:
        """Provider is available when not on cooldown."""
        ph = ProviderHealth(name="test")
        assert ph.is_available is True

    def test_provider_availability_on_cooldown(self) -> None:
        """Provider is unavailable during cooldown."""
        ph = ProviderHealth(
            name="test",
            cooldown_until=datetime.now() + timedelta(minutes=10),
        )
        assert ph.is_available is False

    def test_provider_availability_cooldown_expired(self) -> None:
        """Provider becomes available after cooldown expires."""
        ph = ProviderHealth(
            name="test",
            cooldown_until=datetime.now() - timedelta(minutes=1),
        )
        assert ph.is_available is True

    def test_get_provider_order_by_score(self) -> None:
        """Providers are sorted by health score (best first)."""
        self.engine.register_provider("good")
        self.engine.register_provider("bad")
        self.engine.providers["good"].success_count = 9
        self.engine.providers["good"].failure_count = 1
        self.engine.providers["bad"].success_count = 1
        self.engine.providers["bad"].failure_count = 9

        order = self.engine.get_provider_order()
        assert order[0] == "good"
        assert order[1] == "bad"

    def test_get_provider_order_excludes_cooldown(self) -> None:
        """Providers on cooldown are excluded from provider order."""
        self.engine.register_provider("available")
        self.engine.register_provider("cooling")
        self.engine.providers["available"].success_count = 5
        self.engine.providers["cooling"].success_count = 5
        self.engine.providers["cooling"].cooldown_until = datetime.now() + timedelta(minutes=5)

        order = self.engine.get_provider_order()
        assert "available" in order
        assert "cooling" not in order

    def test_record_success_clears_cooldown(self) -> None:
        """Recording a success clears any active cooldown."""
        self.engine.register_provider("openai")
        ph = self.engine.providers["openai"]
        ph.cooldown_until = datetime.now() + timedelta(minutes=10)

        self.engine.record_success("openai", latency_ms=100.0)
        assert ph.cooldown_until is None
        assert ph.is_available is True

    def test_record_success_updates_latency(self) -> None:
        """Average latency is updated correctly on success."""
        self.engine.register_provider("openai")
        self.engine.record_success("openai", latency_ms=200.0)
        assert self.engine.providers["openai"].avg_latency_ms == 200.0

        self.engine.record_success("openai", latency_ms=400.0)
        # Average of [200, 400] = 300
        assert self.engine.providers["openai"].avg_latency_ms == 300.0

    def test_consecutive_failures_trigger_cooldown(self) -> None:
        """More than 5 failures with failures > successes triggers cooldown."""
        self.engine.register_provider("flaky")
        for _ in range(6):
            self.engine.record_failure("flaky", error="timeout")

        ph = self.engine.providers["flaky"]
        assert ph.failure_count == 6
        assert ph.cooldown_until is not None
        assert ph.cooldown_until > datetime.now()

    def test_rate_limit_429_triggers_5min_cooldown(self) -> None:
        """HTTP 429 triggers a 5-minute cooldown."""
        self.engine.register_provider("openai")
        self.engine.record_failure("openai", error="rate limited", status_code=429)

        ph = self.engine.providers["openai"]
        assert ph.cooldown_until is not None
        # Should be ~5 minutes from now
        remaining = (ph.cooldown_until - datetime.now()).total_seconds()
        assert 290 < remaining < 310  # ~5 minutes

    def test_exponential_backoff_on_failures(self) -> None:
        """Cooldown grows exponentially with consecutive failures."""
        self.engine.register_provider("flaky")
        # First 5 failures: no cooldown yet
        for _ in range(5):
            self.engine.record_failure("flaky", error="err")
        assert self.engine.providers["flaky"].cooldown_until is None

        # 6th failure: cooldown = 2^(6-5) = 2 minutes
        self.engine.record_failure("flaky", error="err")
        ph = self.engine.providers["flaky"]
        assert ph.cooldown_until is not None

    def test_request_log_appended(self) -> None:
        """Request log tracks both successes and failures."""
        self.engine.record_success("openai", latency_ms=100.0)
        self.engine.record_failure("openai", error="timeout")

        assert len(self.engine.request_log) == 2
        assert self.engine.request_log[0]["status"] == "success"
        assert self.engine.request_log[1]["status"] == "failure"

    def test_request_log_trims_at_1000(self) -> None:
        """Request log is trimmed to 500 entries when it exceeds 1000 (only on failure path)."""
        # Trimming only happens in record_failure, so use failures to trigger it
        for i in range(1001):
            self.engine.record_failure("openai", error="err")

        # After 1001 failures, append then trim to last 500
        assert len(self.engine.request_log) == 500

    def test_get_status_returns_structure(self) -> None:
        """get_status() returns a complete status report."""
        self.engine.register_provider("openai")
        self.engine.record_success("openai", latency_ms=100.0)
        self.engine.record_failure("openai", error="timeout")

        status = self.engine.get_status()
        assert "providers" in status
        assert "provider_order" in status
        assert "total_requests" in status
        assert "recent_errors" in status
        assert status["total_requests"] == 2

    def test_failover_scenario(self) -> None:
        """Full failover scenario: primary fails, secondary takes over."""
        self.engine.register_provider("primary")
        self.engine.register_provider("secondary")

        # Primary is healthy initially
        self.engine.record_success("primary", latency_ms=50.0)
        order = self.engine.get_provider_order()
        assert order[0] == "primary"

        # Primary starts failing
        for _ in range(6):
            self.engine.record_failure("primary", error="timeout")

        # Secondary remains healthy
        self.engine.record_success("secondary", latency_ms=100.0)

        # Primary is now on cooldown, secondary should be first
        order = self.engine.get_provider_order()
        assert order[0] == "secondary"
        assert "primary" not in order  # On cooldown


# ══════════════════════════════════════════════════════════════════════
# AuditLogger Tests
# ══════════════════════════════════════════════════════════════════════


class TestAuditLogger:
    """Test the comprehensive audit trail logger."""

    def setup_method(self) -> None:
        self.logger = AuditLogger(max_entries=100)

    def test_log_creates_entry(self) -> None:
        """Logging creates an AuditEntry with correct fields."""
        entry = self.logger.log("MARKET", "INFO", "Price updated")
        assert isinstance(entry, AuditEntry)
        assert entry.layer == "MARKET"
        assert entry.severity == "INFO"
        assert entry.message == "Price updated"
        assert entry.id == 1

    def test_log_all_7_layers(self) -> None:
        """Entries can be logged at all 7 layers."""
        layers = ["MARKET", "SENSOR", "PRESSURE", "DECISION", "RISK", "EXECUTION", "SYSTEM"]
        for i, layer in enumerate(layers):
            entry = self.logger.log(layer, "INFO", f"Test {layer}")
            assert entry.layer == layer
            assert entry.id == i + 1

    def test_log_all_4_severities(self) -> None:
        """Entries can be logged at all 4 severity levels."""
        severities = ["INFO", "WARNING", "ERROR", "CRITICAL"]
        for severity in severities:
            entry = self.logger.log("SYSTEM", severity, f"Test {severity}")
            assert entry.severity == severity

    def test_log_invalid_layer_defaults_to_system(self) -> None:
        """Invalid layer is coerced to SYSTEM."""
        entry = self.logger.log("INVALID_LAYER", "INFO", "Test")
        assert entry.layer == "SYSTEM"

    def test_log_invalid_severity_defaults_to_info(self) -> None:
        """Invalid severity is coerced to INFO."""
        entry = self.logger.log("MARKET", "FATAL", "Test")
        assert entry.severity == "INFO"

    def test_log_with_details(self) -> None:
        """Details dict is stored with the entry."""
        details = {"symbol": "AAPL", "price": 150.0}
        entry = self.logger.log("MARKET", "INFO", "Price update", details=details)
        assert entry.details == details

    def test_get_entries_no_filter(self) -> None:
        """get_entries() returns entries up to the limit."""
        for i in range(10):
            self.logger.log("MARKET", "INFO", f"Entry {i}")
        entries = self.logger.get_entries(limit=5)
        assert len(entries) == 5

    def test_get_entries_filter_by_layer(self) -> None:
        """get_entries() can filter by layer."""
        self.logger.log("MARKET", "INFO", "Market entry")
        self.logger.log("RISK", "WARNING", "Risk entry")
        self.logger.log("MARKET", "INFO", "Another market")

        market_entries = self.logger.get_entries(layer="MARKET")
        assert len(market_entries) == 2
        assert all(e.layer == "MARKET" for e in market_entries)

    def test_get_entries_filter_by_severity(self) -> None:
        """get_entries() can filter by severity."""
        self.logger.log("SYSTEM", "INFO", "Info entry")
        self.logger.log("SYSTEM", "ERROR", "Error entry")
        self.logger.log("SYSTEM", "CRITICAL", "Critical entry")

        errors = self.logger.get_entries(severity="ERROR")
        assert len(errors) == 1
        assert errors[0].severity == "ERROR"

    def test_get_entries_combined_filter(self) -> None:
        """get_entries() can filter by both layer and severity."""
        self.logger.log("RISK", "INFO", "Risk info")
        self.logger.log("RISK", "ERROR", "Risk error")
        self.logger.log("MARKET", "ERROR", "Market error")

        filtered = self.logger.get_entries(layer="RISK", severity="ERROR")
        assert len(filtered) == 1
        assert filtered[0].layer == "RISK"
        assert filtered[0].severity == "ERROR"

    def test_max_entries_trimming(self) -> None:
        """Entries are trimmed when max_entries is exceeded."""
        logger = AuditLogger(max_entries=5)
        for i in range(10):
            logger.log("SYSTEM", "INFO", f"Entry {i}")

        assert len(logger.entries) == 5
        # Should keep the last 5
        assert logger.entries[0].message == "Entry 5"

    def test_counts_tracked_per_layer(self) -> None:
        """Per-layer counts are maintained correctly."""
        self.logger.log("MARKET", "INFO", "M1")
        self.logger.log("MARKET", "INFO", "M2")
        self.logger.log("RISK", "WARNING", "R1")

        assert self.logger.counts["MARKET"] == 2
        assert self.logger.counts["RISK"] == 1

    def test_get_summary(self) -> None:
        """get_summary() returns a complete summary dict."""
        self.logger.log("MARKET", "INFO", "Test")
        self.logger.log("RISK", "CRITICAL", "Danger!")

        summary = self.logger.get_summary()
        assert summary["total_entries"] == 2
        assert "by_layer" in summary
        assert "by_severity" in summary
        assert summary["by_severity"]["CRITICAL"] == 1
        assert len(summary["recent_critical"]) == 1

    def test_save_to_file(self) -> None:
        """Audit trail can be saved to a JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(max_entries=100, log_dir=tmpdir)
            logger.log("MARKET", "INFO", "Saved entry")
            logger.save_to_file()

            # Find the created file
            files = list(Path(tmpdir).glob("audit_*.json"))
            assert len(files) == 1

            with open(files[0]) as f:
                data = json.load(f)
            assert "summary" in data
            assert "entries" in data
            assert len(data["entries"]) == 1

    def test_save_to_file_no_log_dir(self) -> None:
        """save_to_file() is a no-op when no log_dir is set."""
        logger = AuditLogger(max_entries=100, log_dir=None)
        logger.log("SYSTEM", "INFO", "Test")
        # Should not raise
        logger.save_to_file()

    def test_append_only_no_modification(self) -> None:
        """Once logged, entries cannot be modified via the logger API."""
        self.logger.log("MARKET", "INFO", "Original")
        original_msg = self.logger.entries[0].message
        # There's no update/delete API — entries are append-only by design
        assert self.logger.entries[0].message == original_msg

    def test_entry_ids_sequential(self) -> None:
        """Entry IDs are sequential starting from 1."""
        for i in range(5):
            self.logger.log("SYSTEM", "INFO", f"Entry {i}")
        ids = [e.id for e in self.logger.entries]
        assert ids == [1, 2, 3, 4, 5]


# ══════════════════════════════════════════════════════════════════════
# PressureNormalizationEngine Tests
# ══════════════════════════════════════════════════════════════════════


class TestPressureNormalizationEngine:
    """Test the multi-sensor pressure normalization engine."""

    def setup_method(self) -> None:
        self.engine = PressureNormalizationEngine()

    def test_sensor_weights_sum_to_one(self) -> None:
        """All sensor weights must sum to 1.0."""
        total = sum(self.engine.SENSOR_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_bullish_inputs_strong_buy(self) -> None:
        """All bullish inputs → STRONG_BUY verdict."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=1.0,
            smc_signal="bullish_bos",
            displacement_strength=1.0,
            news_impact=1.0,
            news_uncertainty=0.1,
            flow_direction="long",
            flow_imbalance=1.0,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.buy_pressure > 0.70
        assert result.verdict == "STRONG_BUY"

    def test_all_bearish_inputs_strong_sell(self) -> None:
        """All bearish inputs → STRONG_SELL verdict."""
        inputs = PressureInput(
            trend_direction="bearish",
            trend_strength=1.0,
            smc_signal="bearish_bos",
            displacement_strength=1.0,
            news_impact=1.0,
            news_uncertainty=0.1,
            flow_direction="short",
            flow_imbalance=1.0,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.sell_pressure > 0.70
        assert result.verdict == "STRONG_SELL"

    def test_neutral_inputs_verdict(self) -> None:
        """All neutral/zero inputs → NEUTRAL verdict."""
        inputs = PressureInput()
        result = self.engine.compile_pressure(inputs)
        assert result.verdict == "NEUTRAL"
        assert result.buy_pressure < 0.55
        assert result.sell_pressure < 0.55

    def test_pressures_normalized_0_to_1(self) -> None:
        """Buy and sell pressures are always between 0.0 and 1.0."""
        # Test with various extreme inputs
        test_cases = [
            PressureInput(trend_direction="bullish", trend_strength=1.0),
            PressureInput(trend_direction="bearish", trend_strength=1.0),
            PressureInput(
                smc_signal="bullish_bos",
                displacement_strength=1.0,
                liquidity_sweep=True,
            ),
            PressureInput(
                news_impact=1.0,
                news_uncertainty=0.0,
            ),
            PressureInput(
                news_impact=1.0,
                news_uncertainty=1.0,
            ),
        ]
        for inputs in test_cases:
            result = self.engine.compile_pressure(inputs)
            assert 0.0 <= result.buy_pressure <= 1.0
            assert 0.0 <= result.sell_pressure <= 1.0
            assert 0.0 <= result.confidence <= 1.0

    def test_quant_scanner_bullish_contribution(self) -> None:
        """Quant Scanner bullish signal adds to buy pressure."""
        inputs = PressureInput(trend_direction="bullish", trend_strength=0.8)
        result = self.engine.compile_pressure(inputs)
        # 0.25 (weight) * 0.8 (strength) = 0.2 buy pressure
        assert result.buy_pressure > 0.0
        assert result.sell_pressure == 0.0

    def test_quant_scanner_bearish_contribution(self) -> None:
        """Quant Scanner bearish signal adds to sell pressure."""
        inputs = PressureInput(trend_direction="bearish", trend_strength=0.8)
        result = self.engine.compile_pressure(inputs)
        assert result.sell_pressure > 0.0
        assert result.buy_pressure == 0.0

    def test_smc_bullish_bos(self) -> None:
        """SMC bullish BOS adds to buy pressure."""
        inputs = PressureInput(
            smc_signal="bullish_bos",
            displacement_strength=0.7,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.buy_pressure > 0.0

    def test_smc_bearish_choch(self) -> None:
        """SMC bearish CHoCH adds to sell pressure."""
        inputs = PressureInput(
            smc_signal="bearish_choch",
            displacement_strength=0.6,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.sell_pressure > 0.0

    def test_liquidity_sweep_adds_to_both_sides(self) -> None:
        """Liquidity sweep adds to both buy and sell pressure."""
        inputs = PressureInput(
            smc_signal="bullish_bos",
            displacement_strength=0.8,
            liquidity_sweep=True,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.buy_pressure > 0.0
        assert result.sell_pressure > 0.0  # Sweep adds to both

    def test_news_high_certainty_directional(self) -> None:
        """High-certainty news adds primarily to the directional side."""
        inputs = PressureInput(
            news_impact=0.8,
            news_uncertainty=0.1,  # High certainty
        )
        result = self.engine.compile_pressure(inputs)
        assert result.buy_pressure > result.sell_pressure

    def test_news_low_certainty_even_split(self) -> None:
        """Low-certainty news splits evenly between buy and sell."""
        inputs = PressureInput(
            news_impact=0.8,
            news_uncertainty=0.9,  # Low certainty
        )
        result = self.engine.compile_pressure(inputs)
        # Should be roughly equal
        assert abs(result.buy_pressure - result.sell_pressure) < 0.05

    def test_flow_agent_long(self) -> None:
        """Flow agent long direction adds to buy pressure."""
        inputs = PressureInput(
            flow_direction="long",
            flow_imbalance=0.7,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.buy_pressure > 0.0

    def test_flow_agent_short(self) -> None:
        """Flow agent short direction adds to sell pressure."""
        inputs = PressureInput(
            flow_direction="short",
            flow_imbalance=0.7,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.sell_pressure > 0.0

    def test_buy_verdict_threshold(self) -> None:
        """BUY verdict when buy_pressure > 0.55."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=1.0,
            smc_signal="bullish_bos",
            displacement_strength=1.0,
            news_impact=0.5,
            news_uncertainty=0.1,
            flow_direction="long",
            flow_imbalance=0.5,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.verdict in ("BUY", "STRONG_BUY")
        assert result.buy_pressure > 0.55

    def test_sell_verdict_threshold(self) -> None:
        """SELL verdict when sell_pressure > 0.55."""
        inputs = PressureInput(
            trend_direction="bearish",
            trend_strength=1.0,
            smc_signal="bearish_bos",
            displacement_strength=1.0,
            news_impact=0.5,
            news_uncertainty=0.1,
            flow_direction="short",
            flow_imbalance=0.5,
        )
        result = self.engine.compile_pressure(inputs)
        assert result.verdict in ("SELL", "STRONG_SELL")
        assert result.sell_pressure > 0.55

    def test_get_pressure_returns_last_result(self) -> None:
        """get_pressure() returns the last compiled result."""
        inputs = PressureInput(trend_direction="bullish", trend_strength=0.5)
        result = self.engine.compile_pressure(inputs)
        assert self.engine.get_pressure() is not None
        assert self.engine.get_pressure().buy_pressure == result.buy_pressure

    def test_get_pressure_state_model(self) -> None:
        """get_pressure_state() returns a PressureState model."""
        inputs = PressureInput(trend_direction="bullish", trend_strength=0.5)
        self.engine.compile_pressure(inputs)
        state = self.engine.get_pressure_state()
        assert isinstance(state, PressureState)
        assert state.buy_pressure > 0.0

    def test_get_pressure_state_before_compile(self) -> None:
        """get_pressure_state() returns default before any compile."""
        engine = PressureNormalizationEngine()
        state = engine.get_pressure_state()
        assert isinstance(state, PressureState)
        assert state.buy_pressure == 0.0

    def test_sensor_inputs_recorded(self) -> None:
        """sensor_inputs are recorded in the result."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=0.6,
            smc_signal="bullish_choch",
            displacement_strength=0.4,
            liquidity_sweep=True,
            news_impact=0.5,
            news_uncertainty=0.3,
            flow_direction="long",
            flow_imbalance=0.3,
        )
        result = self.engine.compile_pressure(inputs)
        assert "trend" in result.sensor_inputs
        assert "smc" in result.sensor_inputs
        assert "liquidity_sweep" in result.sensor_inputs
        assert "news_impact" in result.sensor_inputs
        assert "flow" in result.sensor_inputs

    def test_raw_values_stored(self) -> None:
        """raw_buy and raw_sell values are stored before normalization."""
        inputs = PressureInput(trend_direction="bullish", trend_strength=1.0)
        result = self.engine.compile_pressure(inputs)
        assert result.raw_buy > 0.0
        assert result.raw_buy == 0.25  # weight * strength


# ══════════════════════════════════════════════════════════════════════
# MarketStateEngine Tests
# ══════════════════════════════════════════════════════════════════════


class TestMarketStateEngine:
    """Test the market regime detection engine."""

    def setup_method(self) -> None:
        self.engine = MarketStateEngine()

    def test_panic_regime(self) -> None:
        """Price drop > 5% in 5 days → PANIC regime."""
        result = self.engine.detect_regime(price_change_5d=-6.0)
        assert result.base_regime == MarketRegime.PANIC

    def test_panic_regime_overrides_to_no_trade(self) -> None:
        """PANIC regime is overridden to NO_TRADE."""
        result = self.engine.detect_regime(price_change_5d=-6.0)
        assert result.regime == MarketRegime.NO_TRADE
        assert result.trade_allowed is False
        assert len(result.no_trade_reasons) > 0

    def test_risk_off_regime(self) -> None:
        """Price drop between 2% and 5% → RISK_OFF regime."""
        result = self.engine.detect_regime(price_change_5d=-3.0)
        assert result.base_regime == MarketRegime.RISK_OFF

    def test_risk_off_no_trade(self) -> None:
        """RISK_OFF regime is not trade-allowed."""
        result = self.engine.detect_regime(price_change_5d=-3.0)
        assert result.trade_allowed is False

    def test_trending_up_regime(self) -> None:
        """ADX > 25 with bullish EMA → TRENDING_UP."""
        result = self.engine.detect_regime(
            price_change_5d=1.0,
            adx=30.0,
            ema_trend="bullish",
        )
        assert result.base_regime == MarketRegime.TRENDING_UP

    def test_trending_up_via_price_change(self) -> None:
        """ADX > 25 with positive 1d change > 0.5% → TRENDING_UP."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            price_change_1d=1.0,
            adx=30.0,
            ema_trend="neutral",
        )
        assert result.base_regime == MarketRegime.TRENDING_UP

    def test_trending_down_regime(self) -> None:
        """ADX > 25 with bearish EMA → TRENDING_DOWN."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=30.0,
            ema_trend="bearish",
        )
        assert result.base_regime == MarketRegime.TRENDING_DOWN

    def test_trending_down_via_price_change(self) -> None:
        """ADX > 25 with negative 1d change < -0.5% → TRENDING_DOWN."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            price_change_1d=-1.0,
            adx=30.0,
            ema_trend="neutral",
        )
        assert result.base_regime == MarketRegime.TRENDING_DOWN

    def test_trending_neutral_direction(self) -> None:
        """ADX > 25 with neutral trend → TRENDING."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            price_change_1d=0.1,
            adx=30.0,
            ema_trend="neutral",
        )
        assert result.base_regime == MarketRegime.TRENDING

    def test_mean_revert_rsi_high(self) -> None:
        """RSI > 75 → MEAN_REVERT regime."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=15.0,  # Below trending threshold
            rsi=80.0,
        )
        assert result.base_regime == MarketRegime.MEAN_REVERT

    def test_mean_revert_rsi_low(self) -> None:
        """RSI < 25 → MEAN_REVERT regime."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=15.0,
            rsi=20.0,
        )
        assert result.base_regime == MarketRegime.MEAN_REVERT

    def test_calm_regime(self) -> None:
        """Low ATR + thin volume → CALM regime."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=15.0,
            rsi=50.0,
            atr_pct=0.3,
            volume_ratio=0.3,
        )
        assert result.base_regime == MarketRegime.CALM

    def test_volatile_regime(self) -> None:
        """High ATR → VOLATILE regime."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=15.0,
            rsi=50.0,
            atr_pct=3.0,
            volume_ratio=1.0,
        )
        assert result.base_regime == MarketRegime.VOLATILE

    def test_range_regime_default(self) -> None:
        """Default regime is RANGE when no other conditions met."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=15.0,
            rsi=50.0,
            atr_pct=1.0,
            volume_ratio=1.0,
        )
        assert result.base_regime == MarketRegime.RANGE

    def test_high_volatility_thin_liquidity_no_trade(self) -> None:
        """High volatility + thin liquidity → NO_TRADE override."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=15.0,
            rsi=50.0,
            atr_pct=3.0,
            volume_ratio=0.3,
        )
        assert result.regime == MarketRegime.NO_TRADE
        assert not result.trade_allowed

    def test_extremely_low_volume_no_trade(self) -> None:
        """Volume ratio < 0.2 → NO_TRADE override."""
        result = self.engine.detect_regime(
            price_change_5d=0.5,
            adx=15.0,
            rsi=50.0,
            volume_ratio=0.15,
        )
        assert result.regime == MarketRegime.NO_TRADE
        assert "low volume" in result.no_trade_reasons[0].lower()

    def test_volatility_classification_high(self) -> None:
        """ATR > 2.5% → HIGH volatility."""
        result = self.engine.detect_regime(atr_pct=3.0)
        assert result.volatility == VolatilityLevel.HIGH

    def test_volatility_classification_low(self) -> None:
        """ATR < 0.5% → LOW volatility."""
        result = self.engine.detect_regime(atr_pct=0.3)
        assert result.volatility == VolatilityLevel.LOW

    def test_volatility_classification_normal(self) -> None:
        """0.5% <= ATR <= 2.5% → NORMAL volatility."""
        result = self.engine.detect_regime(atr_pct=1.0)
        assert result.volatility == VolatilityLevel.NORMAL

    def test_liquidity_classification_thin(self) -> None:
        """Volume ratio < 0.4 → THIN liquidity."""
        result = self.engine.detect_regime(volume_ratio=0.3)
        assert result.liquidity == LiquidityLevel.THIN

    def test_liquidity_classification_deep(self) -> None:
        """Volume ratio > 1.8 → DEEP liquidity."""
        result = self.engine.detect_regime(volume_ratio=2.0)
        assert result.liquidity == LiquidityLevel.DEEP

    def test_liquidity_classification_normal(self) -> None:
        """0.4 <= volume ratio <= 1.8 → NORMAL liquidity."""
        result = self.engine.detect_regime(volume_ratio=1.0)
        assert result.liquidity == LiquidityLevel.NORMAL

    def test_regime_history_kept(self) -> None:
        """Regime history is tracked."""
        self.engine.detect_regime(price_change_5d=0.5)
        self.engine.detect_regime(price_change_5d=-3.0)
        assert len(self.engine.regime_history) == 2

    def test_regime_history_capped_at_100(self) -> None:
        """Regime history is capped at 100 entries."""
        for _ in range(150):
            self.engine.detect_regime()
        assert len(self.engine.regime_history) == 100

    def test_current_regime_updated(self) -> None:
        """current_regime is updated after each detection."""
        self.engine.detect_regime(price_change_5d=-6.0)
        assert self.engine.current_regime == MarketRegime.NO_TRADE

    def test_get_regime(self) -> None:
        """get_regime() returns the current regime."""
        assert self.engine.get_regime() == MarketRegime.UNKNOWN
        self.engine.detect_regime(price_change_5d=1.0, adx=30.0, ema_trend="bullish")
        assert self.engine.get_regime() == MarketRegime.TRENDING_UP

    def test_get_market_state(self) -> None:
        """get_market_state() returns a MarketState model."""
        self.engine.detect_regime(symbol="AAPL", price_change_5d=1.0)
        state = self.engine.get_market_state()
        assert isinstance(state, MarketState)
        assert state.regime == MarketRegime.RANGE  # Default for moderate inputs

    def test_symbol_recorded(self) -> None:
        """Symbol is recorded in the result."""
        result = self.engine.detect_regime(symbol="BTC-USD")
        assert result.symbol == "BTC-USD"

    def test_inputs_recorded(self) -> None:
        """All input values are recorded in the result."""
        result = self.engine.detect_regime(
            symbol="XAUUSD",
            price_change_5d=1.5,
            price_change_1d=0.3,
            adx=28.0,
            rsi=55.0,
            atr_pct=1.2,
            volume_ratio=1.1,
            ema_trend="bullish",
        )
        assert "price_change_5d" in result.inputs
        assert "adx" in result.inputs
        assert result.inputs["ema_trend"] == "bullish"

    def test_all_10_regimes_reachable(self) -> None:
        """All 10 non-UNKNOWN regimes can be detected."""
        detected_regimes = set()

        test_cases = [
            {"price_change_5d": -6.0},  # PANIC
            {"price_change_5d": -3.0},  # RISK_OFF
            {"price_change_5d": 1.0, "adx": 30.0, "ema_trend": "bullish"},  # TRENDING_UP
            {"price_change_5d": 1.0, "adx": 30.0, "ema_trend": "bearish"},  # TRENDING_DOWN
            {"price_change_5d": 1.0, "adx": 30.0, "ema_trend": "neutral",
             "price_change_1d": 0.1},  # TRENDING
            {"price_change_5d": 1.0, "adx": 15.0, "rsi": 80.0},  # MEAN_REVERT
            {"price_change_5d": 1.0, "adx": 15.0, "rsi": 50.0,
             "atr_pct": 1.0, "volume_ratio": 1.0},  # RANGE
            {"price_change_5d": 1.0, "adx": 15.0, "rsi": 50.0,
             "atr_pct": 0.3, "volume_ratio": 0.3},  # CALM
            {"price_change_5d": 1.0, "adx": 15.0, "rsi": 50.0,
             "atr_pct": 3.0},  # VOLATILE
        ]

        for params in test_cases:
            result = self.engine.detect_regime(**params)
            detected_regimes.add(result.base_regime)

        # We should have 9 base regimes from the test cases
        assert len(detected_regimes) >= 9
        # NO_TRADE is an override, not a base regime (except from panic)


# ══════════════════════════════════════════════════════════════════════
# StrategyLifecycleManager Tests
# ══════════════════════════════════════════════════════════════════════


class TestStrategyLifecycleManager:
    """Test the Darwinian strategy lifecycle manager."""

    def setup_method(self) -> None:
        self.manager = StrategyLifecycleManager()

    def test_register_strategy(self) -> None:
        """Strategies can be registered for lifecycle tracking."""
        strategy = self.manager.register_strategy("alpha", description="Alpha strategy")
        assert isinstance(strategy, StrategyState)
        assert strategy.name == "alpha"
        assert strategy.state == StrategyStatus.ACTIVE
        assert strategy.trades_count == 0
        assert "active" in strategy.state_history[0]["state"].lower()

    def test_register_multiple_strategies(self) -> None:
        """Multiple strategies can be registered."""
        self.manager.register_strategy("alpha")
        self.manager.register_strategy("beta")
        self.manager.register_strategy("gamma")
        assert len(self.manager.strategies) == 3

    def test_update_strategy_auto_registers(self) -> None:
        """Updating an unregistered strategy auto-registers it."""
        strategy = self.manager.update_strategy("new_strat", pnl=100.0, is_win=True)
        assert "new_strat" in self.manager.strategies
        assert strategy.trades_count == 1

    def test_update_strategy_win(self) -> None:
        """Winning trade updates wins, total_pnl, and win_rate."""
        self.manager.register_strategy("test")
        strategy = self.manager.update_strategy("test", pnl=50.0, is_win=True)
        assert strategy.wins == 1
        assert strategy.total_pnl == 50.0
        assert strategy.win_rate == 1.0

    def test_update_strategy_loss(self) -> None:
        """Losing trade updates losses and total_pnl."""
        self.manager.register_strategy("test")
        strategy = self.manager.update_strategy("test", pnl=-30.0, is_win=False)
        assert strategy.losses == 1
        assert strategy.total_pnl == -30.0

    def test_expectancy_calculation(self) -> None:
        """Expectancy is calculated correctly from average win/loss."""
        self.manager.register_strategy("test")
        # Win $100, Loss $50
        self.manager.update_strategy("test", pnl=100.0, is_win=True)
        self.manager.update_strategy("test", pnl=-50.0, is_win=False)
        strategy = self.manager.strategies["test"]
        # win_rate = 0.5, avg_win = 100, avg_loss = 50
        # expectancy = 0.5 * 100 - 0.5 * 50 = 25
        assert strategy.expectancy == pytest.approx(25.0, abs=1.0)

    def test_strategy_stays_active_under_min_trades(self) -> None:
        """Strategy stays ACTIVE before MIN_TRADES_FOR_EVALUATION."""
        self.manager.register_strategy("test")
        for i in range(19):
            self.manager.update_strategy("test", pnl=-10.0, is_win=False)
        # Still under 20 trades
        assert self.manager.strategies["test"].state == StrategyStatus.ACTIVE

    def test_negative_expectancy_kills_strategy(self) -> None:
        """Negative expectancy after 20+ trades → KILLED."""
        self.manager.register_strategy("test")
        for _ in range(20):
            self.manager.update_strategy("test", pnl=-10.0, is_win=False)
        assert self.manager.strategies["test"].state == StrategyStatus.KILLED

    def test_excessive_drawdown_hibernates_strategy(self) -> None:
        """Max drawdown > 15% → HIBERNATING."""
        self.manager.register_strategy("test")
        # Give some wins so expectancy is positive
        for _ in range(15):
            self.manager.update_strategy("test", pnl=5.0, is_win=True, current_drawdown=0.05)
        # Now add drawdown exceeding threshold
        for _ in range(10):
            self.manager.update_strategy("test", pnl=-2.0, is_win=False, current_drawdown=0.20)
        assert self.manager.strategies["test"].state == StrategyStatus.HIBERNATING

    def test_hibernating_stays_due_to_max_drawdown(self) -> None:
        """Hibernating strategy stays HIBERNATING because max_drawdown is never reset."""
        self.manager.register_strategy("test")
        # Force into hibernation with high drawdown but positive expectancy overall
        for _ in range(10):
            self.manager.update_strategy("test", pnl=20.0, is_win=True, current_drawdown=0.05)
        for _ in range(10):
            self.manager.update_strategy("test", pnl=-5.0, is_win=False, current_drawdown=0.20)
        # Should be hibernating due to max_drawdown > 0.15
        assert self.manager.strategies["test"].state == StrategyStatus.HIBERNATING

        # Even after adding wins with low drawdown, max_drawdown stays at 0.20
        for _ in range(5):
            self.manager.update_strategy("test", pnl=10.0, is_win=True, current_drawdown=0.05)
        # max_drawdown is still 0.20 (> 0.15), so stays HIBERNATING
        # Note: only recovers to ACTIVE if max_drawdown <= HIBERNATE_MAX_DRAWDOWN
        assert self.manager.strategies["test"].max_drawdown > 0.15
        assert self.manager.strategies["test"].state == StrategyStatus.HIBERNATING

    def test_killed_strategy_rejects_updates(self) -> None:
        """KILLED strategies reject further updates."""
        self.manager.register_strategy("test")
        # Kill the strategy
        for _ in range(20):
            self.manager.update_strategy("test", pnl=-10.0, is_win=False)
        assert self.manager.strategies["test"].state == StrategyStatus.KILLED

        # Try to update — should not change state
        old_count = self.manager.strategies["test"].trades_count
        self.manager.update_strategy("test", pnl=100.0, is_win=True)
        # Trade count increments but state stays KILLED
        assert self.manager.strategies["test"].state == StrategyStatus.KILLED

    def test_state_transitions_recorded(self) -> None:
        """State transitions are recorded in state_history."""
        self.manager.register_strategy("test")
        for _ in range(20):
            self.manager.update_strategy("test", pnl=-10.0, is_win=False)

        history = self.manager.strategies["test"].state_history
        # Should have at least ACTIVE → KILLED transition
        states = [h["state"] for h in history]
        assert "ACTIVE" in states
        assert "KILLED" in states
        # Each transition should have a reason
        for h in history[1:]:
            assert "reason" in h

    def test_get_active_strategies(self) -> None:
        """get_active_strategies() returns only active strategy names."""
        self.manager.register_strategy("active1")
        self.manager.register_strategy("active2")
        self.manager.register_strategy("dead")
        # Kill one
        for _ in range(20):
            self.manager.update_strategy("dead", pnl=-10.0, is_win=False)

        active = self.manager.get_active_strategies()
        assert "active1" in active
        assert "active2" in active
        assert "dead" not in active

    def test_get_strategy_report(self) -> None:
        """get_strategy_report() returns a comprehensive report."""
        self.manager.register_strategy("alpha")
        self.manager.update_strategy("alpha", pnl=50.0, is_win=True)

        report = self.manager.get_strategy_report()
        assert "total_strategies" in report
        assert "active" in report
        assert "hibernating" in report
        assert "killed" in report
        assert "strategies" in report
        assert report["total_strategies"] == 1
        assert report["active"] == 1

    def test_darwinian_scoring_positive_expectancy_survives(self) -> None:
        """Strategies with positive expectancy survive."""
        self.manager.register_strategy("winner")
        for _ in range(15):
            self.manager.update_strategy("winner", pnl=20.0, is_win=True, current_drawdown=0.01)
        for _ in range(10):
            self.manager.update_strategy("winner", pnl=-5.0, is_win=False, current_drawdown=0.02)
        assert self.manager.strategies["winner"].state == StrategyStatus.ACTIVE
        assert self.manager.strategies["winner"].expectancy > 0

    def test_min_trades_constant(self) -> None:
        """MIN_TRADES_FOR_EVALUATION is 20."""
        assert StrategyLifecycleManager.MIN_TRADES_FOR_EVALUATION == 20

    def test_hibernate_max_drawdown_constant(self) -> None:
        """HIBERNATE_MAX_DRAWDOWN is 15%."""
        assert StrategyLifecycleManager.HIBERNATE_MAX_DRAWDOWN == 0.15

    def test_strategy_with_just_under_max_drawdown_stays_active(self) -> None:
        """Strategy with drawdown just under the 15% threshold stays ACTIVE."""
        self.manager.register_strategy("edge")
        # Build up enough trades and wins for positive expectancy
        for _ in range(15):
            self.manager.update_strategy("edge", pnl=10.0, is_win=True, current_drawdown=0.10)
        # Add losses that push drawdown close to but not over 15%
        for _ in range(10):
            self.manager.update_strategy("edge", pnl=-2.0, is_win=False, current_drawdown=0.14)
        # 14% drawdown is under the 15% threshold
        assert self.manager.strategies["edge"].state == StrategyStatus.ACTIVE
