#!/usr/bin/env python3
"""Coverage push: loaders/, optimizers/, execution/guards/, execution/manager.py.

Target modules:
  A: quant_nanggroe/engine/backtest/loaders/  (base_loader 46.7%, ccxt_loader 25.9%, yfinance_loader 20%)
  B: quant_nanggroe/engine/backtest/optimizers/ (mean_variance 30.8%, risk_parity 32.3%)
  C: quant_nanggroe/engine/execution/guards/    (cooldown 50%, max_position 45.7%, whitelist 43.6%)
  D: quant_nanggroe/engine/execution/manager.py (38.5%)

Coverage target: loaders/, optimizers/, execution/guards/, execution/manager.py

Run: python3 -m unittest tests.test_coverage_execution -v
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import time
import unittest
import uuid
from typing import Optional

import numpy as np
import pandas as pd

# ── Module A imports ───────────────────────────────────────────────────────
from quant_nanggroe.engine.backtest.loaders.base_loader import (
    BaseLoader,
    NoAvailableSourceError,
    check_budget,
    retry_with_budget,
    validate_date_range,
)
from quant_nanggroe.engine.backtest.loaders.ccxt_loader import CCXTLoader
from quant_nanggroe.engine.backtest.loaders.yfinance_loader import (
    _flatten_columns,
    _normalize_frame,
    _to_yfinance_interval,
    _to_yfinance_symbol,
)

# ── Module B imports ───────────────────────────────────────────────────────
from quant_nanggroe.engine.backtest.optimizers.base_optimizer import BaseOptimizer
from quant_nanggroe.engine.backtest.optimizers.mean_variance_optimizer import (
    MeanVarianceOptimizer,
)
from quant_nanggroe.engine.backtest.optimizers.mean_variance_optimizer import (
    optimize as mv_optimize,
)
from quant_nanggroe.engine.backtest.optimizers.risk_parity_optimizer import (
    RiskParityOptimizer,
)
from quant_nanggroe.engine.backtest.optimizers.risk_parity_optimizer import (
    optimize as rp_optimize,
)
from quant_nanggroe.engine.execution.base import (
    AccountInfo,
    Broker,
    Order,
    OrderSide,
    OrderType,
)

# ── Module C imports ───────────────────────────────────────────────────────
from quant_nanggroe.engine.execution.guards.cooldown import CooldownGuard, GuardCheckResult
from quant_nanggroe.engine.execution.guards.max_position import MaxPositionGuard
from quant_nanggroe.engine.execution.guards.whitelist import WhitelistGuard

# ── Module D imports ───────────────────────────────────────────────────────
from quant_nanggroe.engine.execution.manager import ExecutionManager, GuardResult

# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

class _MockBroker(Broker):
    """Minimal Broker implementation for ExecutionManager tests."""

    def __init__(self, name: str = "mock_broker"):
        self._broker_name = name
        self._connected = True

    @property
    def name(self) -> str:
        return self._broker_name

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def get_account(self) -> AccountInfo:
        return AccountInfo(balance=1_000_000.0, equity=1_000_000.0)

    async def submit_order(self, order: Order) -> Order:
        return order

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_order(self, order_id: str) -> Optional[Order]:
        return None

    async def get_positions(self):
        return []

    async def get_price(self, symbol: str) -> float:
        return 100.0


def _make_order(
    symbol: str = "AAPL",
    side: OrderSide = OrderSide.BUY,
    quantity: float = 100,
    price: Optional[float] = 150.0,
) -> Order:
    return Order(
        id=str(uuid.uuid4()),
        symbol=symbol,
        side=side,
        order_type=OrderType.MARKET,
        quantity=quantity,
        price=price,
    )


# ════════════════════════════════════════════════════════════════════════════
# Module A: Loaders
# ════════════════════════════════════════════════════════════════════════════

class _ConcreteLoader(BaseLoader):
    """Minimal concrete subclass for BaseLoader tests."""
    name = "test_loader"
    markets = {"test_market"}
    requires_auth = False

    def is_available(self) -> bool:
        return True

    def fetch(self, codes, start_date, end_date, *, interval="1D", fields=None):
        return {}


class TestBaseLoaderInterface(unittest.TestCase):
    """BaseLoader — abstract interface, subclassing, defaults."""

    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            BaseLoader()

    def test_concrete_subclass_works(self):
        loader = _ConcreteLoader()
        self.assertEqual(loader.name, "test_loader")
        self.assertEqual(loader.markets, {"test_market"})
        self.assertFalse(loader.requires_auth)

    def test_default_attributes(self):
        self.assertEqual(BaseLoader.name, "base")
        self.assertEqual(BaseLoader.markets, set())
        self.assertFalse(BaseLoader.requires_auth)

    def test_is_available(self):
        loader = _ConcreteLoader()
        self.assertTrue(loader.is_available())

    def test_fetch_returns_dict(self):
        loader = _ConcreteLoader()
        result = loader.fetch(["AAPL"], "2024-01-01", "2024-01-10")
        self.assertEqual(result, {})


class TestLoaderHelpers(unittest.TestCase):
    """validate_date_range, check_budget, retry_with_budget, NoAvailableSourceError."""

    def test_no_available_source_error(self):
        with self.assertRaises(NoAvailableSourceError):
            raise NoAvailableSourceError("no source")

    def test_validate_date_range_valid(self):
        validate_date_range("2024-01-01", "2024-12-31")

    def test_validate_date_range_inverted(self):
        with self.assertRaises(ValueError):
            validate_date_range("2024-12-31", "2024-01-01")

    def test_validate_date_range_invalid_format(self):
        with self.assertRaises(ValueError):
            validate_date_range("not-a-date", "2024-01-01")

    def test_check_budget_expired(self):
        deadline = time.monotonic() - 1.0
        with self.assertRaises(TimeoutError):
            check_budget(deadline, "test_label")

    def test_check_budget_within_budget(self):
        deadline = time.monotonic() + 60.0
        check_budget(deadline, "test_label")

    def test_retry_with_budget_success(self):
        deadline = time.monotonic() + 10.0
        result = retry_with_budget(
            lambda: "ok",
            transient=ValueError,
            deadline=deadline,
            label="test",
            max_retries=1,
            backoff=(0.01,),
        )
        self.assertEqual(result, "ok")

    def test_retry_with_budget_transient_exhausted(self):
        deadline = time.monotonic() + 5.0
        calls = 0

        def fail():
            nonlocal calls
            calls += 1
            raise ValueError("transient")

        with self.assertRaises(TimeoutError):
            retry_with_budget(
                fail,
                transient=ValueError,
                deadline=deadline,
                label="test",
                max_retries=2,
                backoff=(0.01, 0.01),
            )
        self.assertEqual(calls, 3)

    def test_retry_with_budget_non_transient_propagates(self):
        deadline = time.monotonic() + 10.0

        def fail():
            raise TypeError("not transient")

        with self.assertRaises(TypeError):
            retry_with_budget(
                fail,
                transient=ValueError,
                deadline=deadline,
                label="test",
                max_retries=1,
                backoff=(0.01,),
            )

    def test_retry_with_budget_short_backoff_raises(self):
        deadline = time.monotonic() + 10.0
        with self.assertRaises(ValueError):
            retry_with_budget(
                lambda: "x",
                transient=ValueError,
                deadline=deadline,
                label="test",
                max_retries=3,
                backoff=(0.01,),  # only 1 entry, need >= 3
            )


class TestYFinanceHelpers(unittest.TestCase):
    """yfinance symbol / interval helpers and data normalisation."""

    def test_to_yfinance_symbol_us(self):
        self.assertEqual(_to_yfinance_symbol("AAPL.US"), "AAPL")

    def test_to_yfinance_symbol_hk(self):
        self.assertEqual(_to_yfinance_symbol("700.HK"), "0700.HK")

    def test_to_yfinance_symbol_no_suffix(self):
        self.assertEqual(_to_yfinance_symbol("BTC-USD"), "BTC-USD")

    def test_to_yfinance_symbol_lowercase(self):
        self.assertEqual(_to_yfinance_symbol("aapl.us"), "AAPL")

    def test_to_yfinance_interval_1D(self):
        self.assertEqual(_to_yfinance_interval("1D"), "1d")

    def test_to_yfinance_interval_1H(self):
        self.assertEqual(_to_yfinance_interval("1H"), "1h")

    def test_to_yfinance_interval_4H(self):
        self.assertEqual(_to_yfinance_interval("4H"), "1h")

    def test_to_yfinance_interval_unknown(self):
        self.assertEqual(_to_yfinance_interval("5m"), "5m")

    def test_flatten_columns_non_multiindex(self):
        df = pd.DataFrame({"open": [1.0], "close": [2.0]})
        result = _flatten_columns(df, "TEST")
        pd.testing.assert_frame_equal(result, df)

    def test_normalize_frame_empty(self):
        result = _normalize_frame(pd.DataFrame(), "1D")
        self.assertTrue(result.empty)

    def test_normalize_frame_basic(self):
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        raw = pd.DataFrame(
            {"Open": [100.0, 101.0, 102.0], "Close": [101.0, 102.0, 103.0],
             "High": [102.0, 103.0, 104.0], "Low": [99.0, 100.0, 101.0],
             "Volume": [1000, 2000, 3000]},
            index=dates,
        )
        result = _normalize_frame(raw, "1D")
        self.assertIsNotNone(result)
        self.assertIn("open", result.columns)
        self.assertEqual(len(result), 3)


class TestCCXTLoaderAttrs(unittest.TestCase):
    """CCXTLoader — attribute checks (no network)."""

    def test_name_and_markets(self):
        loader = CCXTLoader()
        self.assertEqual(loader.name, "ccxt")
        self.assertEqual(loader.markets, {"crypto"})
        self.assertFalse(loader.requires_auth)

    def test_is_available_no_side_effect(self):
        loader = CCXTLoader()
        result = loader.is_available()
        self.assertIn(result, (True, False))  # depends on ccxt being installed


# ════════════════════════════════════════════════════════════════════════════
# Module B: Optimizers
# ════════════════════════════════════════════════════════════════════════════

class _ConcreteOptimizer(BaseOptimizer):
    """Minimal concrete optimizer for testing base class."""

    def _calc_weights(self, ctx):
        n = ctx["cov"].shape[0]
        return self._equal_weight(n)


class TestBaseOptimizer(unittest.TestCase):
    """BaseOptimizer — abstract interface, utilities."""

    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            BaseOptimizer()

    def test_init_default_lookback(self):
        opt = _ConcreteOptimizer()
        self.assertEqual(opt.lookback, 60)

    def test_init_custom_lookback(self):
        opt = _ConcreteOptimizer(lookback=120)
        self.assertEqual(opt.lookback, 120)

    def test_normalize_all_positive(self):
        w = np.array([2.0, 3.0, 5.0])
        result = BaseOptimizer._normalize(w)
        self.assertAlmostEqual(result.sum(), 1.0)

    def test_normalize_clamps_negative(self):
        w = np.array([1.0, -1.0, 1.0])
        result = BaseOptimizer._normalize(w)
        self.assertTrue((result >= 0).all())
        self.assertAlmostEqual(result.sum(), 1.0)

    def test_normalize_all_zero(self):
        w = np.array([0.0, 0.0, 0.0])
        result = BaseOptimizer._normalize(w)
        self.assertAlmostEqual(result.sum(), 1.0)
        self.assertTrue((result == (1.0 / 3)).all())

    def test_equal_weight_n_positive(self):
        result = BaseOptimizer._equal_weight(4)
        self.assertEqual(len(result), 4)
        self.assertAlmostEqual(result.sum(), 1.0)

    def test_equal_weight_n_zero(self):
        result = BaseOptimizer._equal_weight(0)
        self.assertEqual(len(result), 0)

    def test_optimize_single_code_returns_pos(self):
        opt = _ConcreteOptimizer()
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        ret = pd.DataFrame({"A": np.random.randn(10)}, index=dates)
        pos = pd.DataFrame({"A": np.ones(10)}, index=dates)
        result = opt.optimize(ret, pos, dates)
        pd.testing.assert_frame_equal(result, pos)

    def test_optimize_two_codes_short_history_skips(self):
        opt = _ConcreteOptimizer()
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        ret = pd.DataFrame(np.random.randn(5, 2), columns=["A", "B"], index=dates)
        pos = pd.DataFrame(np.ones((5, 2)), columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        # All dates have i < lookback (60) or window too short
        pd.testing.assert_frame_equal(result, pos)


class TestMeanVarianceOptimizer(unittest.TestCase):
    """MeanVarianceOptimizer — init, _build_context, _calc_weights."""

    def test_init_default(self):
        opt = MeanVarianceOptimizer()
        self.assertEqual(opt.lookback, 60)
        self.assertEqual(opt.risk_free, 0.0)

    def test_init_custom_risk_free(self):
        opt = MeanVarianceOptimizer(lookback=30, risk_free=0.02)
        self.assertEqual(opt.lookback, 30)
        self.assertEqual(opt.risk_free, 0.02)

    def test_build_context_returns_dict(self):
        opt = MeanVarianceOptimizer()
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        window = pd.DataFrame(np.random.randn(10, 3), columns=["A", "B", "C"], index=dates)
        ctx = opt._build_context(window, ["A", "B", "C"])
        self.assertIsNotNone(ctx)
        self.assertIn("cov", ctx)
        self.assertIn("mu", ctx)
        self.assertEqual(ctx["cov"].shape, (3, 3))
        self.assertEqual(len(ctx["mu"]), 3)

    def test_build_context_nan_returns_none(self):
        opt = MeanVarianceOptimizer()
        window = pd.DataFrame({"A": [1.0], "B": [2.0]})
        ctx = opt._build_context(window, ["A", "B"])
        self.assertIsNone(ctx)

    def test_calc_weights_zero_assets(self):
        opt = MeanVarianceOptimizer()
        ctx = {"cov": np.zeros((0, 0)), "mu": np.array([])}
        w = opt._calc_weights(ctx)
        self.assertEqual(len(w), 0)

    def test_calc_weights_nonnegative_sum_one(self):
        opt = MeanVarianceOptimizer()
        n = 4
        ctx = {"cov": np.eye(n), "mu": np.array([0.1, 0.05, 0.02, 0.01])}
        w = opt._calc_weights(ctx)
        self.assertEqual(len(w), n)
        self.assertAlmostEqual(w.sum(), 1.0)
        self.assertTrue((w >= -1e-10).all())

    def test_module_level_optimize(self):
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (100, 3)), columns=["A", "B", "C"], index=dates)
        pos = pd.DataFrame(np.ones((100, 3)), columns=["A", "B", "C"], index=dates)
        result = mv_optimize(ret, pos, dates, lookback=60)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.shape, (100, 3))


class TestRiskParityOptimizer(unittest.TestCase):
    """RiskParityOptimizer — init, _calc_weights."""

    def test_init(self):
        opt = RiskParityOptimizer()
        self.assertEqual(opt.lookback, 60)

    def test_calc_weights_identity_cov(self):
        opt = RiskParityOptimizer()
        ctx = {"cov": np.eye(4)}
        w = opt._calc_weights(ctx)
        self.assertEqual(len(w), 4)
        self.assertAlmostEqual(w.sum(), 1.0)

    def test_calc_weights_zero_vol_equal_weight(self):
        opt = RiskParityOptimizer()
        ctx = {"cov": np.zeros((4, 4))}
        w = opt._calc_weights(ctx)
        np.testing.assert_array_almost_equal(w, np.ones(4) / 4)

    def test_calc_weights_zero_assets(self):
        opt = RiskParityOptimizer()
        ctx = {"cov": np.zeros((0, 0))}
        w = opt._calc_weights(ctx)
        self.assertEqual(len(w), 0)

    def test_calc_weights_asymmetric_cov(self):
        opt = RiskParityOptimizer()
        cov = np.array([[0.04, 0.01], [0.01, 0.09]])
        ctx = {"cov": cov}
        w = opt._calc_weights(ctx)
        self.assertEqual(len(w), 2)
        self.assertAlmostEqual(w.sum(), 1.0)
        # Lower-vol asset should get higher weight
        self.assertGreater(w[0], w[1])

    def test_module_level_optimize(self):
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (100, 3)), columns=["A", "B", "C"], index=dates)
        pos = pd.DataFrame(np.ones((100, 3)), columns=["A", "B", "C"], index=dates)
        result = rp_optimize(ret, pos, dates, lookback=60)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.shape, (100, 3))


# ════════════════════════════════════════════════════════════════════════════
# Module C: Execution Guards
# ════════════════════════════════════════════════════════════════════════════

class TestCooldownGuard(unittest.TestCase):
    """CooldownGuard — check, record, remaining, reset."""

    def setUp(self):
        self.guard = CooldownGuard(seconds=60.0)
        self.order = _make_order(symbol="AAPL")

    def test_check_passes_no_history(self):
        result = self.guard.check(self.order)
        self.assertIsInstance(result, GuardCheckResult)
        self.assertTrue(result.allowed)

    def test_check_blocks_after_trade(self):
        self.guard.record_trade("AAPL")
        result = self.guard.check(self.order)
        self.assertFalse(result.allowed)
        self.assertIn("Cooldown", result.reason)

    def test_get_cooldown_remaining_positive(self):
        self.guard.record_trade("AAPL")
        remaining = self.guard.get_cooldown_remaining("AAPL")
        self.assertGreater(remaining, 0.0)

    def test_get_cooldown_remaining_no_history(self):
        remaining = self.guard.get_cooldown_remaining("UNKNOWN")
        self.assertEqual(remaining, 0.0)

    def test_reset_single_symbol(self):
        self.guard.record_trade("AAPL")
        self.guard.reset("AAPL")
        result = self.guard.check(self.order)
        self.assertTrue(result.allowed)

    def test_reset_all_symbols(self):
        self.guard.record_trade("AAPL")
        self.guard.record_trade("GOOGL")
        self.guard.reset()
        result_aapl = self.guard.check(_make_order(symbol="AAPL"))
        result_goog = self.guard.check(_make_order(symbol="GOOGL"))
        self.assertTrue(result_aapl.allowed)
        self.assertTrue(result_goog.allowed)

    def test_cooldown_per_symbol_independent(self):
        self.guard.record_trade("AAPL")
        result_aapl = self.guard.check(_make_order(symbol="AAPL"))
        result_goog = self.guard.check(_make_order(symbol="GOOGL"))
        self.assertFalse(result_aapl.allowed)
        self.assertTrue(result_goog.allowed)

    def test_guard_check_result_dataclass(self):
        r = GuardCheckResult(allowed=True, reason="")
        self.assertTrue(r.allowed)
        self.assertEqual(r.reason, "")


class TestMaxPositionGuard(unittest.TestCase):
    """MaxPositionGuard — check, update, remove."""

    def setUp(self):
        self.guard = MaxPositionGuard(max_pct=0.10, max_notional=None)

    def test_check_passes_default(self):
        order = _make_order(symbol="AAPL", quantity=10, price=100.0)
        result = self.guard.check(order)
        self.assertTrue(result["allowed"])

    def test_check_fails_percentage(self):
        self.guard = MaxPositionGuard(max_pct=0.01)
        order = _make_order(symbol="AAPL", quantity=200, price=100.0)
        result = self.guard.check(order)
        self.assertFalse(result["allowed"])
        self.assertIn("exceed", result["reason"])

    def test_check_fails_notional(self):
        self.guard = MaxPositionGuard(max_notional=5000.0)
        order = _make_order(symbol="AAPL", quantity=100, price=100.0)
        result = self.guard.check(order)
        self.assertFalse(result["allowed"])
        self.assertIn("notional", result["reason"])

    def test_check_sell_reduces_notional(self):
        self.guard = MaxPositionGuard(max_pct=0.10)
        self.guard.update_position("AAPL", 80000.0)
        # SELL reduces notional; 80000 - 100 = 79900 > 100000 (10% of 1M) -> allowed
        order = _make_order(symbol="AAPL", side=OrderSide.SELL, quantity=1, price=100.0)
        result = self.guard.check(order)
        self.assertTrue(result["allowed"])

    def test_check_with_existing_position(self):
        self.guard = MaxPositionGuard(max_pct=0.05)
        self.guard.update_position("AAPL", 40000.0)
        order = _make_order(symbol="AAPL", quantity=100, price=100.0)
        # current = 40000, new = 50000, max_allowed = 0.05 * 1M = 50000
        # 50000 <= 50000 -> allowed
        result = self.guard.check(order)
        self.assertTrue(result["allowed"])

    def test_update_position(self):
        self.guard.update_position("AAPL", 50000.0)
        self.assertEqual(self.guard._current_positions["AAPL"], 50000.0)

    def test_remove_position(self):
        self.guard.update_position("AAPL", 50000.0)
        self.guard.remove_position("AAPL")
        self.assertNotIn("AAPL", self.guard._current_positions)

    def test_update_portfolio_value(self):
        self.guard.update_portfolio_value(2_000_000.0)
        self.assertEqual(self.guard._portfolio_value, 2_000_000.0)

    def test_zero_price_order_notional_zero(self):
        order = _make_order(symbol="AAPL", quantity=100, price=None)
        result = self.guard.check(order)
        self.assertTrue(result["allowed"])


class TestWhitelistGuard(unittest.TestCase):
    """WhitelistGuard — check, add, remove, block."""

    def test_check_allowed_no_whitelist(self):
        guard = WhitelistGuard()
        order = _make_order(symbol="AAPL")
        result = guard.check(order)
        self.assertTrue(result["allowed"])

    def test_check_blocked_symbol(self):
        guard = WhitelistGuard(blocked_symbols=["AAPL"])
        order = _make_order(symbol="AAPL")
        result = guard.check(order)
        self.assertFalse(result["allowed"])
        self.assertIn("blocked", result["reason"])

    def test_check_allowed_symbol(self):
        guard = WhitelistGuard(allowed_symbols=["AAPL", "GOOGL"])
        order = _make_order(symbol="AAPL")
        result = guard.check(order)
        self.assertTrue(result["allowed"])

    def test_check_non_allowed_symbol(self):
        guard = WhitelistGuard(allowed_symbols=["GOOGL"])
        order = _make_order(symbol="AAPL")
        result = guard.check(order)
        self.assertFalse(result["allowed"])
        self.assertIn("whitelist", result["reason"])

    def test_blocked_overrides_allowed(self):
        guard = WhitelistGuard(allowed_symbols=["AAPL"], blocked_symbols=["AAPL"])
        order = _make_order(symbol="AAPL")
        result = guard.check(order)
        self.assertFalse(result["allowed"])

    def test_case_insensitive_blocked(self):
        guard = WhitelistGuard(blocked_symbols=["aapl"])
        order = _make_order(symbol="AAPL")
        result = guard.check(order)
        self.assertFalse(result["allowed"])

    def test_add_symbol(self):
        guard = WhitelistGuard(allowed_symbols=["INIT"])
        guard.add_symbol("AAPL")
        self.assertIn("AAPL", guard.allowed_symbols)

    def test_remove_symbol(self):
        guard = WhitelistGuard(allowed_symbols=["AAPL"])
        guard.remove_symbol("AAPL")
        self.assertNotIn("AAPL", guard.allowed_symbols)

    def test_block_unblock_symbol(self):
        guard = WhitelistGuard()
        guard.block_symbol("AAPL")
        self.assertIn("AAPL", guard.blocked_symbols)
        guard.unblock_symbol("AAPL")
        self.assertNotIn("AAPL", guard.blocked_symbols)

    def test_allowed_symbols_property(self):
        guard = WhitelistGuard(allowed_symbols=["AAPL"])
        self.assertIsNotNone(guard.allowed_symbols)
        self.assertIn("AAPL", guard.allowed_symbols)

    def test_blocked_symbols_property(self):
        guard = WhitelistGuard(blocked_symbols=["AAPL"])
        self.assertIn("AAPL", guard.blocked_symbols)


# ════════════════════════════════════════════════════════════════════════════
# Module D: ExecutionManager
# ════════════════════════════════════════════════════════════════════════════

class TestExecutionManager(unittest.TestCase):
    """ExecutionManager — init, broker CRUD, routing, guards, audit."""

    def setUp(self):
        self.manager = ExecutionManager()
        self.broker = _MockBroker("paper")
        self.order = _make_order()

    def test_init(self):
        self.assertEqual(len(self.manager._brokers), 0)
        self.assertIsNone(self.manager._primary_broker)
        self.assertIsNotNone(self.manager._order_manager)
        self.assertIsNotNone(self.manager._fill_tracker)
        self.assertIsNotNone(self.manager._cooldown_guard)
        self.assertIsNotNone(self.manager._max_position_guard)
        self.assertIsNotNone(self.manager._whitelist_guard)
        self.assertEqual(self.manager._audit_log, [])

    def test_add_broker(self):
        self.manager.add_broker(self.broker)
        self.assertIn("paper", self.manager._brokers)
        self.assertEqual(self.manager._primary_broker, "paper")

    def test_add_broker_non_primary(self):
        b1 = _MockBroker("b1")
        b2 = _MockBroker("b2")
        self.manager.add_broker(b1, primary=True)
        self.manager.add_broker(b2, primary=False)
        self.assertEqual(self.manager._primary_broker, "b1")

    def test_remove_broker(self):
        self.manager.add_broker(self.broker)
        self.manager.remove_broker("paper")
        self.assertNotIn("paper", self.manager._brokers)
        self.assertIsNone(self.manager._primary_broker)

    def test_remove_broker_updates_primary(self):
        b1 = _MockBroker("b1")
        b2 = _MockBroker("b2")
        self.manager.add_broker(b1, primary=True)
        self.manager.add_broker(b2)
        self.manager.remove_broker("b1")
        self.assertEqual(self.manager._primary_broker, "b2")

    def test_remove_broker_nonexistent(self):
        self.manager.remove_broker("nonexistent")

    def test_route_order_primary(self):
        self.manager.add_broker(_MockBroker("primary"), primary=True)
        self.manager.add_broker(_MockBroker("secondary"))
        route = self.manager._route_order(self.order)
        self.assertEqual(route, "primary")

    def test_route_order_no_primary(self):
        b1 = _MockBroker("first")
        self.manager.add_broker(b1)
        self.manager._primary_broker = None
        route = self.manager._route_order(self.order)
        self.assertEqual(route, "first")

    def test_route_order_no_brokers(self):
        route = self.manager._route_order(self.order)
        self.assertEqual(route, "paper")

    def test_audit_log_returns_copy(self):
        log = self.manager.get_audit_log()
        log.append({"fake": True})
        self.assertEqual(len(self.manager.get_audit_log()), 0)

    def test_order_manager_property(self):
        self.assertIs(self.manager.order_manager, self.manager._order_manager)

    def test_fill_tracker_property(self):
        self.assertIs(self.manager.fill_tracker, self.manager._fill_tracker)

    def test_set_kill_switch(self):
        from quant_nanggroe.engine.risk.kill_switch import KillSwitch
        ks = KillSwitch()
        self.manager.set_kill_switch(ks)
        self.assertIs(self.manager._kill_switch, ks)

    def test_cancel_order_not_found(self):
        result = asyncio.run(self.manager.cancel_order("nonexistent"))
        self.assertFalse(result)

    def test_run_guards_cooldown_blocks(self):
        self.manager._cooldown_guard.record_trade(self.order.symbol)
        result = self.manager._run_guards(self.order)
        self.assertIsInstance(result, GuardResult)
        self.assertFalse(result.allowed)
        self.assertEqual(result.guard_name, "cooldown")

    def test_execute_order_blocked_by_cooldown(self):
        async def run():
            self.manager._cooldown_guard.record_trade(self.order.symbol)
            fill = await self.manager.execute_order(self.order)
            self.assertIsNone(fill)
            log = self.manager.get_audit_log()
            self.assertEqual(len(log), 1)
            self.assertEqual(log[0]["action"], "GUARD_BLOCKED")
            self.assertEqual(log[0]["guard"], "cooldown")
            return True

        self.assertTrue(asyncio.run(run()))

    def test_guard_result_dataclass(self):
        r = GuardResult(allowed=True, guard_name="test")
        self.assertTrue(r.allowed)
        self.assertEqual(r.guard_name, "test")
        self.assertEqual(r.reason, "")

    def test_guard_result_with_reason(self):
        r = GuardResult(allowed=False, guard_name="test", reason="blocked")
        self.assertFalse(r.allowed)
        self.assertEqual(r.reason, "blocked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
