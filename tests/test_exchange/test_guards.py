"""Comprehensive tests for the Trading Guards Pipeline.

Tests cover:
- WhitelistGuard: whitelist and blocklist enforcement
- CooldownGuard: cooldown period enforcement and recording
- MaxPositionGuard: position size limit enforcement
- GuardPipeline: composition, fail-fast, and run-all modes
- GuardResult and PipelineResult types
- Edge cases and state management
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional

import pytest

from quant_nanggroe.exchange.guards import (
    BaseGuard,
    WhitelistGuard,
    CooldownGuard,
    MaxPositionGuard,
    GuardPipeline,
    GuardVerdict,
    GuardResult,
    PipelineResult,
)
from quant_nanggroe.types.orders import (
    Order,
    MarketOrder,
    LimitOrder,
    OrderSide,
    OrderType,
    OrderStatus,
)


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def buy_order() -> Order:
    """A standard buy order for BTC/USDT."""
    return LimitOrder(
        id="test-001",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        quantity=1.0,
        price=42000.0,
    )


@pytest.fixture
def sell_order() -> Order:
    """A standard sell order for ETH/USDT."""
    return LimitOrder(
        id="test-002",
        symbol="ETH/USDT",
        side=OrderSide.SELL,
        quantity=10.0,
        price=3000.0,
    )


@pytest.fixture
def blocked_order() -> Order:
    """An order for a blocked symbol."""
    return MarketOrder(
        id="test-003",
        symbol="SCAM/USDT",
        side=OrderSide.BUY,
        quantity=1000.0,
    )


# ======================================================================
# 1. WhitelistGuard
# ======================================================================

class TestWhitelistGuard:

    def test_name(self):
        guard = WhitelistGuard()
        assert guard.name == "WhitelistGuard"

    def test_no_whitelist_allows_all(self, buy_order: Order):
        guard = WhitelistGuard()
        result = guard.check(buy_order)
        assert result.passed
        assert result.verdict == GuardVerdict.PASS

    def test_whitelist_allows_approved(self, buy_order: Order):
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT", "ETH/USDT"])
        result = guard.check(buy_order)
        assert result.passed

    def test_whitelist_blocks_unapproved(self, sell_order: Order):
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT"])
        result = guard.check(sell_order)
        assert not result.passed
        assert "not on the approved whitelist" in result.reason

    def test_whitelist_case_insensitive(self):
        guard = WhitelistGuard(allowed_symbols=["btc/usdt"])
        order = LimitOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=1.0, price=42000.0)
        result = guard.check(order)
        assert result.passed

    def test_blocked_symbol_always_blocked(self, buy_order: Order):
        guard = WhitelistGuard(blocked_symbols=["BTC/USDT"])
        result = guard.check(buy_order)
        assert not result.passed
        assert "blocked list" in result.reason

    def test_blocked_takes_precedence_over_whitelist(self, buy_order: Order):
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT"], blocked_symbols=["BTC/USDT"])
        result = guard.check(buy_order)
        assert not result.passed
        assert "blocked list" in result.reason

    def test_add_symbol(self, sell_order: Order):
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT"])
        result_before = guard.check(sell_order)
        assert not result_before.passed

        guard.add_symbol("ETH/USDT")
        result_after = guard.check(sell_order)
        assert result_after.passed

    def test_remove_symbol(self, buy_order: Order):
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT", "ETH/USDT"])
        guard.remove_symbol("BTC/USDT")
        result = guard.check(buy_order)
        assert not result.passed

    def test_block_symbol(self, buy_order: Order):
        guard = WhitelistGuard()
        assert guard.check(buy_order).passed

        guard.block_symbol("BTC/USDT")
        assert not guard.check(buy_order).passed

    def test_unblock_symbol(self, buy_order: Order):
        guard = WhitelistGuard(blocked_symbols=["BTC/USDT"])
        assert not guard.check(buy_order).passed

        guard.unblock_symbol("BTC/USDT")
        assert guard.check(buy_order).passed

    def test_allowed_symbols_property(self):
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT"])
        assert "BTC/USDT" in guard.allowed_symbols

    def test_blocked_symbols_property(self):
        guard = WhitelistGuard(blocked_symbols=["SCAM/USDT"])
        assert "SCAM/USDT" in guard.blocked_symbols

    def test_no_whitelist_returns_none(self):
        guard = WhitelistGuard()
        assert guard.allowed_symbols is None

    def test_result_details(self, buy_order: Order):
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT"])
        result = guard.check(buy_order)
        assert "symbol" in result.details
        assert result.details["symbol"] == "BTC/USDT"

    def test_is_base_guard(self):
        guard = WhitelistGuard()
        assert isinstance(guard, BaseGuard)


# ======================================================================
# 2. CooldownGuard
# ======================================================================

class TestCooldownGuard:

    def test_name(self):
        guard = CooldownGuard()
        assert guard.name == "CooldownGuard"

    def test_no_cooldown_allows(self, buy_order: Order):
        guard = CooldownGuard(seconds=0.0)
        result = guard.check(buy_order)
        assert result.passed

    def test_cooldown_blocks_immediate_retrade(self, buy_order: Order):
        guard = CooldownGuard(seconds=60.0)
        guard.record_trade("BTC/USDT")
        result = guard.check(buy_order)
        assert not result.passed
        assert "Cooldown active" in result.reason

    def test_cooldown_allows_after_period(self, buy_order: Order):
        guard = CooldownGuard(seconds=0.01)  # Very short
        guard.record_trade("BTC/USDT")
        time.sleep(0.02)
        result = guard.check(buy_order)
        assert result.passed

    def test_cooldown_per_symbol(self, buy_order: Order, sell_order: Order):
        guard = CooldownGuard(seconds=60.0, per_symbol=True)
        guard.record_trade("BTC/USDT")
        # BTC should be blocked
        assert not guard.check(buy_order).passed
        # ETH should be allowed (different symbol)
        assert guard.check(sell_order).passed

    def test_cooldown_global(self, buy_order: Order, sell_order: Order):
        guard = CooldownGuard(seconds=60.0, per_symbol=False)
        guard.record_trade("BTC/USDT")
        # Both should be blocked
        assert not guard.check(buy_order).passed
        assert not guard.check(sell_order).passed

    def test_get_cooldown_remaining(self):
        guard = CooldownGuard(seconds=60.0)
        guard.record_trade("BTC/USDT")
        remaining = guard.get_cooldown_remaining("BTC/USDT")
        assert 0 < remaining <= 60.0

    def test_get_cooldown_remaining_no_trade(self):
        guard = CooldownGuard(seconds=60.0)
        remaining = guard.get_cooldown_remaining("BTC/USDT")
        assert remaining == 0.0

    def test_reset_specific_symbol(self, buy_order: Order):
        guard = CooldownGuard(seconds=60.0)
        guard.record_trade("BTC/USDT")
        guard.reset("BTC/USDT")
        result = guard.check(buy_order)
        assert result.passed

    def test_reset_all(self, buy_order: Order):
        guard = CooldownGuard(seconds=60.0)
        guard.record_trade("BTC/USDT")
        guard.reset()
        result = guard.check(buy_order)
        assert result.passed

    def test_result_details(self, buy_order: Order):
        guard = CooldownGuard(seconds=60.0)
        guard.record_trade("BTC/USDT")
        result = guard.check(buy_order)
        assert "cooldown_seconds" in result.details
        assert "remaining_seconds" in result.details

    def test_is_base_guard(self):
        guard = CooldownGuard()
        assert isinstance(guard, BaseGuard)


# ======================================================================
# 3. MaxPositionGuard
# ======================================================================

class TestMaxPositionGuard:

    def test_name(self):
        guard = MaxPositionGuard()
        assert guard.name == "MaxPositionGuard"

    def test_small_order_passes(self, buy_order: Order):
        guard = MaxPositionGuard(max_pct=0.10, portfolio_value=1_000_000.0)
        # 1 BTC * 42000 = 42000, which is 4.2% of 1M — should pass
        result = guard.check(buy_order)
        assert result.passed

    def test_large_order_fails(self, buy_order: Order):
        guard = MaxPositionGuard(max_pct=0.01, portfolio_value=1_000_000.0)
        # 1 BTC * 42000 = 42000, which is 4.2% of 1M — exceeds 1%
        result = guard.check(buy_order)
        assert not result.passed
        assert "exceed" in result.reason.lower()

    def test_sell_reduces_position(self, sell_order: Order):
        guard = MaxPositionGuard(max_pct=0.10, portfolio_value=1_000_000.0)
        guard.update_position("ETH/USDT", 50000.0)
        # Sell reduces position from 50000 to 20000 — well under 10%
        result = guard.check(sell_order)
        assert result.passed

    def test_max_notional_limit(self, buy_order: Order):
        guard = MaxPositionGuard(max_notional=10000.0)
        # 42000 > 10000
        result = guard.check(buy_order)
        assert not result.passed
        assert "max notional" in result.reason.lower()

    def test_max_notional_passes_under_limit(self):
        guard = MaxPositionGuard(max_notional=50000.0)
        order = LimitOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=1.0, price=42000.0)
        result = guard.check(order)
        assert result.passed

    def test_update_position(self, buy_order: Order):
        guard = MaxPositionGuard(max_pct=0.05, portfolio_value=1_000_000.0)
        guard.update_position("BTC/USDT", 40000.0)  # Already at 4%
        # Adding 42000 more = 82000, which is 8.2% — exceeds 5%
        result = guard.check(buy_order)
        assert not result.passed

    def test_update_portfolio_value(self, buy_order: Order):
        guard = MaxPositionGuard(max_pct=0.10, portfolio_value=100_000.0)
        # 42000 is 42% of 100k — fails
        result = guard.check(buy_order)
        assert not result.passed

        guard.update_portfolio_value(1_000_000.0)
        # 42000 is 4.2% of 1M — passes
        result = guard.check(buy_order)
        assert result.passed

    def test_remove_position(self, buy_order: Order):
        guard = MaxPositionGuard(max_pct=0.05, portfolio_value=1_000_000.0)
        guard.update_position("BTC/USDT", 49000.0)  # 4.9% — just under
        result = guard.check(buy_order)
        assert not result.passed  # 49000 + 42000 > 50000

        guard.remove_position("BTC/USDT")
        result = guard.check(buy_order)
        assert result.passed  # Now just 42000

    def test_context_override(self, buy_order: Order):
        guard = MaxPositionGuard(max_pct=0.10, portfolio_value=1_000_000.0)
        # With default portfolio, passes
        assert guard.check(buy_order).passed

        # With tiny portfolio from context, fails
        context = {"portfolio_value": 100_000.0}
        result = guard.check(buy_order, context=context)
        assert not result.passed

    def test_zero_price_order(self):
        guard = MaxPositionGuard(max_pct=0.10)
        order = MarketOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=1.0)
        # Market order with no price — notional is 0
        result = guard.check(order)
        assert result.passed  # 0 notional is always under limit

    def test_is_base_guard(self):
        guard = MaxPositionGuard()
        assert isinstance(guard, BaseGuard)


# ======================================================================
# 4. GuardPipeline
# ======================================================================

class TestGuardPipeline:

    def test_name(self):
        pipeline = GuardPipeline(name="test_pipeline")
        assert pipeline.name == "test_pipeline"

    def test_add_guard(self):
        pipeline = GuardPipeline()
        guard = WhitelistGuard(allowed_symbols=["BTC/USDT"])
        pipeline.add_guard(guard)
        assert len(pipeline.guards) == 1

    def test_add_non_guard_raises(self):
        pipeline = GuardPipeline()
        with pytest.raises(TypeError, match="Expected BaseGuard"):
            pipeline.add_guard("not a guard")  # type: ignore

    def test_remove_guard(self):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard())
        pipeline.add_guard(CooldownGuard())
        assert len(pipeline.guards) == 2

        removed = pipeline.remove_guard("WhitelistGuard")
        assert removed is True
        assert len(pipeline.guards) == 1

    def test_remove_nonexistent_guard(self):
        pipeline = GuardPipeline()
        removed = pipeline.remove_guard("NonExistent")
        assert removed is False

    def test_clear(self):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard())
        pipeline.add_guard(CooldownGuard())
        pipeline.clear()
        assert len(pipeline.guards) == 0

    def test_all_pass(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["BTC/USDT"]))
        pipeline.add_guard(CooldownGuard(seconds=0.0))
        pipeline.add_guard(MaxPositionGuard(max_pct=1.0))

        result = pipeline.check(buy_order)
        assert result.passed
        assert len(result.results) == 3
        assert len(result.failed_guards) == 0
        assert len(result.reasons) == 0

    def test_fail_fast_stops_on_first_failure(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["ETH/USDT"]))  # Will fail
        pipeline.add_guard(CooldownGuard(seconds=0.0))

        result = pipeline.check(buy_order, fail_fast=True)
        assert not result.passed
        assert len(result.results) == 1  # Stopped after first guard

    def test_run_all_guards(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["ETH/USDT"]))  # Fails
        pipeline.add_guard(CooldownGuard(seconds=0.0))  # Would pass

        result = pipeline.check(buy_order, fail_fast=False)
        assert not result.passed
        assert len(result.results) == 2  # Both guards ran
        assert "WhitelistGuard" in result.failed_guards

    def test_failed_guards_listed(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["ETH/USDT"]))

        result = pipeline.check(buy_order)
        assert "WhitelistGuard" in result.failed_guards

    def test_reasons_collected(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["ETH/USDT"]))

        result = pipeline.check(buy_order)
        assert len(result.reasons) == 1
        assert "not on the approved whitelist" in result.reasons[0]

    def test_check_single_guard(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["ETH/USDT"]))
        pipeline.add_guard(CooldownGuard(seconds=0.0))

        result = pipeline.check_single("CooldownGuard", buy_order)
        assert result is not None
        assert result.passed

    def test_check_single_nonexistent(self, buy_order: Order):
        pipeline = GuardPipeline()
        result = pipeline.check_single("NonExistent", buy_order)
        assert result is None

    def test_get_guard(self):
        pipeline = GuardPipeline()
        guard = WhitelistGuard()
        pipeline.add_guard(guard)

        found = pipeline.get_guard("WhitelistGuard")
        assert found is guard

    def test_get_guard_nonexistent(self):
        pipeline = GuardPipeline()
        found = pipeline.get_guard("NonExistent")
        assert found is None

    def test_multiple_failures(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(WhitelistGuard(allowed_symbols=["ETH/USDT"]))  # Fail
        pipeline.add_guard(CooldownGuard(seconds=60.0))  # Would fail if checked
        pipeline.add_guard(MaxPositionGuard(max_pct=0.001))  # Would fail if checked

        result = pipeline.check(buy_order, fail_fast=False)
        assert not result.passed
        # At least one guard should fail
        assert len(result.failed_guards) >= 1

    def test_pipeline_with_context(self, buy_order: Order):
        pipeline = GuardPipeline()
        pipeline.add_guard(MaxPositionGuard(max_pct=0.10))

        # Pass context with tiny portfolio
        context = {"portfolio_value": 100_000.0}
        result = pipeline.check(buy_order, context=context)
        assert not result.passed


# ======================================================================
# 5. GuardResult and PipelineResult types
# ======================================================================

class TestResultTypes:

    def test_guard_result_pass(self):
        result = GuardResult(verdict=GuardVerdict.PASS, guard_name="TestGuard")
        assert result.passed
        assert result.verdict == GuardVerdict.PASS

    def test_guard_result_fail(self):
        result = GuardResult(
            verdict=GuardVerdict.FAIL,
            guard_name="TestGuard",
            reason="Something failed",
        )
        assert not result.passed
        assert result.verdict == GuardVerdict.FAIL
        assert result.reason == "Something failed"

    def test_guard_result_details(self):
        result = GuardResult(
            verdict=GuardVerdict.PASS,
            guard_name="TestGuard",
            details={"key": "value"},
        )
        assert result.details["key"] == "value"

    def test_pipeline_result_passed(self):
        result = PipelineResult(passed=True)
        assert result.passed
        assert result.failed_guards == []
        assert result.reasons == []

    def test_pipeline_result_failed(self):
        result = PipelineResult(
            passed=False,
            failed_guards=["Guard1"],
            reasons=["Reason 1"],
        )
        assert not result.passed
        assert "Guard1" in result.failed_guards

    def test_guard_verdict_enum(self):
        assert GuardVerdict.PASS.value == "pass"
        assert GuardVerdict.FAIL.value == "fail"


# ======================================================================
# 6. Edge cases
# ======================================================================

class TestEdgeCases:

    def test_whitelist_empty_symbol(self):
        """Orders with empty symbols should still work with no whitelist."""
        guard = WhitelistGuard()
        order = MarketOrder(symbol="ANY/USDT", side=OrderSide.BUY, quantity=1.0)
        result = guard.check(order)
        assert result.passed

    def test_cooldown_zero_seconds(self, buy_order: Order):
        guard = CooldownGuard(seconds=0.0)
        guard.record_trade("BTC/USDT")
        result = guard.check(buy_order)
        assert result.passed

    def test_max_position_zero_portfolio(self, buy_order: Order):
        """With zero portfolio value, position check cannot compute a limit."""
        guard = MaxPositionGuard(max_pct=0.10, portfolio_value=0.0)
        # With 0 portfolio, max_allowed = 0, and portfolio_value > 0 is False,
        # so the percentage check is skipped. Order passes.
        result = guard.check(buy_order)
        assert result.passed

    def test_pipeline_empty(self, buy_order: Order):
        """Empty pipeline should pass all orders."""
        pipeline = GuardPipeline()
        result = pipeline.check(buy_order)
        assert result.passed

    def test_guard_result_serialization(self):
        """GuardResult should be serializable as a Pydantic model."""
        result = GuardResult(
            verdict=GuardVerdict.FAIL,
            guard_name="Test",
            reason="test reason",
            details={"key": 42},
        )
        data = result.model_dump()
        assert data["verdict"] == GuardVerdict.FAIL
        assert data["guard_name"] == "Test"
        assert data["details"]["key"] == 42

    def test_pipeline_result_serialization(self):
        """PipelineResult should be serializable."""
        result = PipelineResult(
            passed=False,
            results=[
                GuardResult(verdict=GuardVerdict.FAIL, guard_name="G1", reason="r1"),
            ],
            failed_guards=["G1"],
            reasons=["r1"],
        )
        data = result.model_dump()
        assert data["passed"] is False
        assert len(data["results"]) == 1
