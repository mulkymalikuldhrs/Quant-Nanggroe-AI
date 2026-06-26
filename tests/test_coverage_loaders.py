#!/usr/bin/env python3
"""Coverage push: loaders/, optimizers/base_optimizer.py, execution.py.

Coverage target: loaders/, optimizers/base_optimizer.py, execution.py

Run: python3 -m unittest tests.test_coverage_loaders -v
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.loaders.base_loader import (
    BaseLoader,
    validate_date_range,
    check_budget,
    retry_with_budget,
)
from quant_nanggroe.engine.backtest.loaders.yfinance_loader import (
    YFinanceLoader,
    _to_yfinance_symbol,
    _to_yfinance_interval,
    _flatten_columns,
    _normalize_frame,
    _extract_symbol_frame,
)
from quant_nanggroe.engine.backtest.loaders.ccxt_loader import (
    CCXTLoader,
    _INTERVAL_MAP,
)
from quant_nanggroe.engine.backtest.optimizers.base_optimizer import BaseOptimizer
from quant_nanggroe.engine.backtest.execution import (
    ExecutionConfig,
    ExecutionSimulator,
)


# ════════════════════════════════════════════════════════════════════════════
# A — base_loader.py  (46.7% → deeper)
# ════════════════════════════════════════════════════════════════════════════

class _ConcreteLoader(BaseLoader):
    name = "test_loader"
    markets = {"test_market"}
    requires_auth = False
    def is_available(self) -> bool:
        return True
    def fetch(self, codes, start_date, end_date, *, interval="1D", fields=None):
        return {}


class TestBaseLoaderDeepEdges(unittest.TestCase):
    """Edge cases not yet covered: equal dates, None input, budget message."""

    def test_validate_date_range_equal_dates(self):
        validate_date_range("2024-01-01", "2024-01-01")

    def test_validate_date_range_invalid_type(self):
        with self.assertRaises(ValueError):
            validate_date_range([], "2024-01-01")  # type: ignore[arg-type]

    def test_check_budget_message_with_budget_s(self):
        deadline = time.monotonic() - 1.0
        with self.assertRaises(TimeoutError) as cm:
            check_budget(deadline, "label", budget_s=30.0)
        self.assertIn("30s", str(cm.exception))

    def test_check_budget_message_without_budget_s(self):
        deadline = time.monotonic() - 1.0
        with self.assertRaises(TimeoutError) as cm:
            check_budget(deadline, "label")
        self.assertNotIn("30s", str(cm.exception))

    def test_retry_with_budget_exact_max_retries(self):
        deadline = time.monotonic() + 10.0
        result = retry_with_budget(
            lambda: "ok",
            transient=ValueError,
            deadline=deadline,
            label="test",
            max_retries=2,
            backoff=(0.01, 0.01),
        )
        self.assertEqual(result, "ok")

    def test_retry_with_budget_transient_count(self):
        deadline = time.monotonic() + 10.0
        calls = [0]
        def fail():
            calls[0] += 1
            raise ValueError("transient")
        with self.assertRaises(TimeoutError):
            retry_with_budget(
                fail,
                transient=ValueError,
                deadline=deadline,
                label="test",
                max_retries=1,
                backoff=(0.01,),
            )
        self.assertEqual(calls[0], 2)

    def test_retry_with_budget_deadline_expired(self):
        deadline = time.monotonic() - 1.0
        calls = [0]
        def fail():
            calls[0] += 1
            raise ValueError("too late")
        with self.assertRaises(TimeoutError):
            retry_with_budget(
                fail,
                transient=ValueError,
                deadline=deadline,
                label="test",
                max_retries=3,
                backoff=(0.01, 0.01, 0.01),
            )
        self.assertEqual(calls[0], 1)

    def test_retry_with_budget_wraps_cause(self):
        deadline = time.monotonic() + 10.0
        def fail():
            raise ValueError("inner")
        with self.assertRaises(TimeoutError) as cm:
            retry_with_budget(
                fail,
                transient=ValueError,
                deadline=deadline,
                label="test",
                max_retries=1,
                backoff=(0.01,),
            )
        self.assertIsInstance(cm.exception.__cause__, ValueError)


# ════════════════════════════════════════════════════════════════════════════
# B — ccxt_loader.py  (25.9% → deeper)
# ════════════════════════════════════════════════════════════════════════════

class TestCCXTLoaderDeepEdges(unittest.TestCase):
    """CCXTLoader — _get_exchange, symbol mapping, fetch with mock."""

    def test_interval_map_all_keys(self):
        self.assertEqual(_INTERVAL_MAP["1m"], "1m")
        self.assertEqual(_INTERVAL_MAP["5m"], "5m")
        self.assertEqual(_INTERVAL_MAP["30m"], "30m")
        self.assertEqual(_INTERVAL_MAP["1H"], "1h")
        self.assertEqual(_INTERVAL_MAP["4H"], "4h")
        self.assertEqual(_INTERVAL_MAP["1D"], "1d")

    def test_fetch_empty_codes(self):
        loader = CCXTLoader()
        result = loader.fetch([], "2024-01-01", "2024-01-10")
        self.assertEqual(result, {})

    def test_get_exchange_known(self):
        mock_ccxt = MagicMock()
        mock_cls = MagicMock()
        mock_ccxt.binance = mock_cls
        with patch.dict("sys.modules", {"ccxt": mock_ccxt}):
            with patch.dict(os.environ, {"CCXT_EXCHANGE": "binance"}):
                loader = CCXTLoader()
                exchange = loader._get_exchange()
        mock_cls.assert_called_once_with(
            {"enableRateLimit": True, "timeout": 15000}
        )

    def test_get_exchange_fallback_to_binance(self):
        mock_ccxt = MagicMock(spec=[])
        mock_cls = MagicMock()
        mock_ccxt.binance = mock_cls
        with patch.dict("sys.modules", {"ccxt": mock_ccxt}):
            with patch.dict(os.environ, {"CCXT_EXCHANGE": "nonexistent"}):
                loader = CCXTLoader()
                exchange = loader._get_exchange()
        mock_cls.assert_called_once()

    def test_fetch_symbol_mapping(self):
        mock_ccxt = MagicMock()
        mock_ccxt.NetworkError = ConnectionError
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1704067200000, 100.0, 101.0, 99.0, 100.5, 10000],
            [1704153600000, 101.0, 102.0, 100.0, 101.5, 11000],
        ]
        mock_cls = MagicMock(return_value=mock_exchange)
        mock_ccxt.binance = mock_cls
        with patch.dict("sys.modules", {"ccxt": mock_ccxt}):
            with patch.dict(os.environ, {"CCXT_EXCHANGE": "binance"}):
                loader = CCXTLoader()
                result = loader.fetch(["BTC-USDT"], "2024-01-01", "2024-01-03")
        self.assertIn("BTC-USDT", result)
        df = result["BTC-USDT"]
        self.assertIn("open", df.columns)
        self.assertEqual(len(df), 2)
        args, _ = mock_exchange.fetch_ohlcv.call_args
        self.assertEqual(args[0], "BTC/USDT")

    def test_fetch_exception_skips_symbol(self):
        mock_ccxt = MagicMock()
        mock_ccxt.NetworkError = ConnectionError
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.side_effect = RuntimeError("API error")
        mock_cls = MagicMock(return_value=mock_exchange)
        mock_ccxt.binance = mock_cls
        with patch.dict("sys.modules", {"ccxt": mock_ccxt}):
            with patch.dict(os.environ, {"CCXT_EXCHANGE": "binance"}):
                loader = CCXTLoader()
                result = loader.fetch(["BTC-USDT"], "2024-01-01", "2024-01-03")
        self.assertEqual(result, {})

    def test_fetch_import_error(self):
        loader = CCXTLoader()
        with patch.object(loader, "_get_exchange", side_effect=ImportError("no ccxt")):
            result = loader.fetch(["BTC-USDT"], "2024-01-01", "2024-01-03")
        self.assertEqual(result, {})

    def test_fetch_none_result_filtered(self):
        mock_ccxt = MagicMock()
        mock_ccxt.NetworkError = ConnectionError
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.return_value = []
        mock_cls = MagicMock(return_value=mock_exchange)
        mock_ccxt.binance = mock_cls
        with patch.dict("sys.modules", {"ccxt": mock_ccxt}):
            with patch.dict(os.environ, {"CCXT_EXCHANGE": "binance"}):
                loader = CCXTLoader()
                result = loader.fetch(["BTC-USDT"], "2024-01-01", "2024-01-03")
        self.assertEqual(result, {})


# ════════════════════════════════════════════════════════════════════════════
# C — yfinance_loader.py  (20.0% → deeper)
# ════════════════════════════════════════════════════════════════════════════

class TestYFinanceLoaderDeepEdges(unittest.TestCase):
    """YFinanceLoader — fetch with mock, helpers, normalizers."""

    def test_is_available(self):
        self.assertTrue(YFinanceLoader().is_available())

    def test_fetch_empty_codes(self):
        loader = YFinanceLoader()
        result = loader.fetch([], "2024-01-01", "2024-01-10")
        self.assertEqual(result, {})

    @patch("quant_nanggroe.engine.backtest.loaders.yfinance_loader._download_history")
    def test_fetch_single_symbol(self, mock_dl):
        dates = pd.date_range("2024-01-01", periods=3, freq="D")
        mock_dl.return_value = pd.DataFrame(
            {"Open": [100.0, 101.0, 102.0],
             "Close": [101.0, 102.0, 103.0],
             "High": [102.0, 103.0, 104.0],
             "Low": [99.0, 100.0, 101.0],
             "Volume": [1000, 2000, 3000]},
            index=dates,
        )
        loader = YFinanceLoader()
        result = loader.fetch(["AAPL.US"], "2024-01-01", "2024-01-05")
        self.assertIn("AAPL.US", result)
        df = result["AAPL.US"]
        self.assertIn("open", df.columns)
        self.assertEqual(len(df), 3)

    @patch("quant_nanggroe.engine.backtest.loaders.yfinance_loader._download_history")
    def test_fetch_bulk_empty_fallback(self, mock_dl):
        dates = pd.date_range("2024-01-01", periods=2, freq="D")
        mock_dl.side_effect = [
            pd.DataFrame(),  # bulk empty
            pd.DataFrame(    # single-symbol fallback
                {"Open": [100.0, 101.0],
                 "Close": [101.0, 102.0],
                 "High": [102.0, 103.0],
                 "Low": [99.0, 100.0],
                 "Volume": [1000, 2000]},
                index=dates,
            ),
        ]
        loader = YFinanceLoader()
        result = loader.fetch(["AAPL.US"], "2024-01-01", "2024-01-05")
        self.assertIn("AAPL.US", result)

    def test_to_yfinance_symbol_variants(self):
        self.assertEqual(_to_yfinance_symbol("700.HK"), "0700.HK")
        self.assertEqual(_to_yfinance_symbol("5.HK"), "0005.HK")
        self.assertEqual(_to_yfinance_symbol(" AAPL.US "), "AAPL")
        self.assertEqual(_to_yfinance_symbol("BTC-USD"), "BTC-USD")

    def test_to_yfinance_interval_variants(self):
        self.assertEqual(_to_yfinance_interval(None), "1d")
        self.assertEqual(_to_yfinance_interval(""), "1d")
        self.assertEqual(_to_yfinance_interval(" 1H "), "1h")

    def test_extract_symbol_frame_empty(self):
        result = _extract_symbol_frame(pd.DataFrame(), "AAPL", 1)
        self.assertTrue(result.empty)

    def test_extract_symbol_frame_single_no_multiindex(self):
        dates = pd.date_range("2024-01-01", periods=2, freq="D")
        df = pd.DataFrame({"Open": [100.0, 101.0], "Close": [101.0, 102.0]}, index=dates)
        result = _extract_symbol_frame(df, "AAPL", 1)
        pd.testing.assert_frame_equal(result, df)

    def test_extract_symbol_frame_single_multi_symbols_no_multiindex(self):
        dates = pd.date_range("2024-01-01", periods=2, freq="D")
        df = pd.DataFrame({"Open": [100.0, 101.0], "Close": [101.0, 102.0]}, index=dates)
        result = _extract_symbol_frame(df, "AAPL", 2)
        self.assertTrue(result.empty)

    def test_extract_symbol_frame_multiindex_found(self):
        dates = pd.date_range("2024-01-01", periods=1, freq="D")
        arrays = [["AAPL", "AAPL"], ["Open", "Close"]]
        columns = pd.MultiIndex.from_tuples(list(zip(*arrays)))
        df = pd.DataFrame([[100.0, 101.0]], index=dates, columns=columns)
        result = _extract_symbol_frame(df, "AAPL", 2)
        self.assertFalse(result.empty)
        self.assertIn("Open", result.columns)

    def test_normalize_frame_missing_price_cols(self):
        df = pd.DataFrame({"volume": [1000]})
        result = _normalize_frame(df, "1D")
        self.assertTrue(result.empty)

    def test_normalize_frame_missing_volume(self):
        dates = pd.date_range("2024-01-01", periods=2, freq="D")
        df = pd.DataFrame(
            {"Open": [100.0, 101.0], "Close": [101.0, 102.0],
             "High": [102.0, 103.0], "Low": [99.0, 100.0]},
            index=dates,
        )
        result = _normalize_frame(df, "1D")
        self.assertIn("volume", result.columns)
        self.assertTrue((result["volume"] == 0.0).all())

    def test_normalize_frame_4h_resample(self):
        dates = pd.date_range("2024-01-01", periods=8, freq="h")
        df = pd.DataFrame(
            {"Open": range(100, 108), "High": range(101, 109),
             "Low": range(99, 107), "Close": range(100, 108),
             "Volume": [1000] * 8},
            index=dates,
        )
        result = _normalize_frame(df, "4H")
        self.assertEqual(len(result), 2)
        self.assertIn("open", result.columns)

    def test_normalize_frame_tz_aware_index(self):
        dates = pd.date_range("2024-01-01", periods=2, freq="D", tz="US/Eastern")
        df = pd.DataFrame(
            {"Open": [100.0, 101.0], "Close": [101.0, 102.0],
             "High": [102.0, 103.0], "Low": [99.0, 100.0],
             "Volume": [1000, 2000]},
            index=dates,
        )
        result = _normalize_frame(df, "1D")
        self.assertIsNone(result.index.tz)

    def test_flatten_columns_multiindex(self):
        arrays = [["AAPL", "AAPL"], ["Open", "Close"]]
        columns = pd.MultiIndex.from_tuples(list(zip(*arrays)))
        df = pd.DataFrame([[100.0, 101.0]], columns=columns)
        result = _flatten_columns(df, "AAPL")
        self.assertNotIsInstance(result.columns, pd.MultiIndex)
        self.assertIn("Open", result.columns)

    def test_flatten_columns_non_multiindex(self):
        df = pd.DataFrame({"open": [1.0], "close": [2.0]})
        result = _flatten_columns(df, "TEST")
        pd.testing.assert_frame_equal(result, df)


# ════════════════════════════════════════════════════════════════════════════
# D — base_optimizer.py  (28.0% → deeper)
# ════════════════════════════════════════════════════════════════════════════

class _FixedWeightOptimizer(BaseOptimizer):
    def __init__(self, weights, lookback=60, **kwargs):
        super().__init__(lookback=lookback, **kwargs)
        self._weights = np.array(weights)
    def _calc_weights(self, ctx):
        return self._weights

class _NoneReturner(BaseOptimizer):
    def _calc_weights(self, ctx):
        return None

class _NoneContextBuilder(BaseOptimizer):
    def _build_context(self, window, active):
        return None
    def _calc_weights(self, ctx):
        return np.array([0.5, 0.5])


class TestBaseOptimizerDeepEdges(unittest.TestCase):
    """BaseOptimizer — optimize loop branches, context, edge cases."""

    def test_optimize_applies_weights(self):
        opt = _FixedWeightOptimizer([0.6, 0.4], lookback=5)
        dates = pd.date_range("2024-01-01", periods=12, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (12, 2)), columns=["A", "B"], index=dates)
        pos = pd.DataFrame(np.ones((12, 2)), columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        self.assertAlmostEqual(result.iloc[5, 0], 0.6)
        self.assertAlmostEqual(result.iloc[5, 1], 0.4)

    def test_optimize_preserves_sign(self):
        opt = _FixedWeightOptimizer([0.6, 0.4], lookback=5)
        dates = pd.date_range("2024-01-01", periods=12, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (12, 2)), columns=["A", "B"], index=dates)
        pos = pd.DataFrame([[1.0, -1.0]] * 12, columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        self.assertGreater(result.iloc[5, 0], 0)
        self.assertLess(result.iloc[5, 1], 0)

    def test_optimize_ctx_none_skips(self):
        opt = _NoneContextBuilder(lookback=5)
        dates = pd.date_range("2024-01-01", periods=12, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (12, 2)), columns=["A", "B"], index=dates)
        pos = pd.DataFrame(np.ones((12, 2)), columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        pd.testing.assert_frame_equal(result, pos)

    def test_optimize_weights_none_skips(self):
        opt = _NoneReturner(lookback=5)
        dates = pd.date_range("2024-01-01", periods=12, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (12, 2)), columns=["A", "B"], index=dates)
        pos = pd.DataFrame(np.ones((12, 2)), columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        pd.testing.assert_frame_equal(result, pos)

    def test_optimize_wrong_weights_length_skips(self):
        opt = _FixedWeightOptimizer([0.6, 0.4, 0.3], lookback=5)
        dates = pd.date_range("2024-01-01", periods=12, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (12, 2)), columns=["A", "B"], index=dates)
        pos = pd.DataFrame(np.ones((12, 2)), columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        pd.testing.assert_frame_equal(result, pos)

    def test_optimize_no_active_assets_skips(self):
        opt = _FixedWeightOptimizer([0.5, 0.5], lookback=5)
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (10, 2)), columns=["A", "B"], index=dates)
        pos = pd.DataFrame(np.zeros((10, 2)), columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        pd.testing.assert_frame_equal(result, pos)

    def test_optimize_short_window_skips(self):
        opt = _FixedWeightOptimizer([0.5, 0.5], lookback=50)
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        rng = np.random.default_rng(42)
        ret = pd.DataFrame(rng.normal(0, 0.01, (10, 2)), columns=["A", "B"], index=dates)
        pos = pd.DataFrame(np.ones((10, 2)), columns=["A", "B"], index=dates)
        result = opt.optimize(ret, pos, dates)
        pd.testing.assert_frame_equal(result, pos)

    def test_build_context_nan_cov_returns_none(self):
        opt = _FixedWeightOptimizer([0.5, 0.5])
        window = pd.DataFrame({"A": [np.nan, 1.0], "B": [1.0, np.nan]})
        ctx = opt._build_context(window, ["A", "B"])
        self.assertIsNone(ctx)

    def test_build_context_returns_cov(self):
        opt = _FixedWeightOptimizer([0.5, 0.5])
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        window = pd.DataFrame(np.random.randn(10, 3), columns=["A", "B", "C"], index=dates)
        ctx = opt._build_context(window, ["A", "B", "C"])
        self.assertIsNotNone(ctx)
        self.assertIn("cov", ctx)
        self.assertEqual(ctx["cov"].shape, (3, 3))

    def test_normalize_all_negative(self):
        w = np.array([-2.0, -3.0, -5.0])
        result = BaseOptimizer._normalize(w)
        self.assertTrue((result >= 0).all())
        self.assertAlmostEqual(result.sum(), 1.0)

    def test_equal_weight_zero(self):
        result = BaseOptimizer._equal_weight(0)
        self.assertEqual(len(result), 0)

    def test_equal_weight_positive(self):
        result = BaseOptimizer._equal_weight(5)
        self.assertEqual(len(result), 5)
        self.assertAlmostEqual(result.sum(), 1.0)


# ════════════════════════════════════════════════════════════════════════════
# E — execution.py  (53.7% → full)
# ════════════════════════════════════════════════════════════════════════════

class TestExecutionConfig(unittest.TestCase):
    """ExecutionConfig dataclass — default and custom."""

    def test_default_config(self):
        cfg = ExecutionConfig()
        self.assertEqual(cfg.commission_rate, 0.001)
        self.assertEqual(cfg.slippage_bps, 5.0)
        self.assertEqual(cfg.market, "equity")
        self.assertEqual(cfg.min_commission, 1.0)
        self.assertEqual(cfg.market_impact_coeff, 0.0)

    def test_custom_config(self):
        cfg = ExecutionConfig(
            commission_rate=0.002, slippage_bps=10.0, market="crypto",
            min_commission=0.5, market_impact_coeff=0.1,
        )
        self.assertEqual(cfg.commission_rate, 0.002)
        self.assertEqual(cfg.slippage_bps, 10.0)
        self.assertEqual(cfg.market, "crypto")
        self.assertEqual(cfg.min_commission, 0.5)
        self.assertEqual(cfg.market_impact_coeff, 0.1)


class TestExecutionSimulatorInit(unittest.TestCase):
    """ExecutionSimulator — init and market-specific defaults."""

    def test_default(self):
        sim = ExecutionSimulator()
        self.assertEqual(sim._commission_rate, 0.001)
        self.assertEqual(sim._slippage_bps, 5.0)

    def test_market_crypto_defaults(self):
        cfg = ExecutionConfig(market="crypto")
        sim = ExecutionSimulator(cfg)  # rate=0.001,bps=5.0 but market=crypto -> override
        self.assertEqual(sim._commission_rate, 0.002)
        self.assertEqual(sim._slippage_bps, 10.0)

    def test_market_forex_defaults(self):
        cfg = ExecutionConfig(market="forex")
        sim = ExecutionSimulator(cfg)
        self.assertEqual(sim._commission_rate, 0.0002)
        self.assertEqual(sim._slippage_bps, 2.0)

    def test_market_futures_defaults(self):
        cfg = ExecutionConfig(market="futures")
        sim = ExecutionSimulator(cfg)
        self.assertEqual(sim._commission_rate, 0.0005)
        self.assertEqual(sim._slippage_bps, 3.0)

    def test_custom_overrides_market_defaults(self):
        cfg = ExecutionConfig(market="crypto", commission_rate=0.005, slippage_bps=20.0)
        sim = ExecutionSimulator(cfg)
        self.assertEqual(sim._commission_rate, 0.005)
        self.assertEqual(sim._slippage_bps, 20.0)

    def test_unknown_market_uses_defaults(self):
        cfg = ExecutionConfig(market="unknown")
        sim = ExecutionSimulator(cfg)
        self.assertEqual(sim._commission_rate, 0.001)
        self.assertEqual(sim._slippage_bps, 5.0)

    def test_equity_market_keeps_values(self):
        cfg = ExecutionConfig(market="equity", commission_rate=0.001, slippage_bps=5.0)
        sim = ExecutionSimulator(cfg)
        self.assertEqual(sim._commission_rate, 0.001)
        self.assertEqual(sim._slippage_bps, 5.0)


class TestExecutionSimulatorSlippage(unittest.TestCase):
    """ExecutionSimulator.apply_slippage."""

    def setUp(self):
        self.sim = ExecutionSimulator()

    def test_buy_increases_price(self):
        result = self.sim.apply_slippage(100.0, 1)
        self.assertGreater(result, 100.0)

    def test_sell_decreases_price(self):
        result = self.sim.apply_slippage(100.0, -1)
        self.assertLess(result, 100.0)

    def test_neutral_direction(self):
        result = self.sim.apply_slippage(100.0, 0)
        self.assertEqual(result, 100.0)

    def test_custom_slippage_bps(self):
        cfg = ExecutionConfig(slippage_bps=20.0)
        sim = ExecutionSimulator(cfg)
        result = sim.apply_slippage(100.0, 1)
        self.assertAlmostEqual(result, 100.2)

    def test_zero_slippage(self):
        cfg = ExecutionConfig(slippage_bps=0.0)
        sim = ExecutionSimulator(cfg)
        result = sim.apply_slippage(100.0, 1)
        self.assertEqual(result, 100.0)


class TestExecutionSimulatorCommission(unittest.TestCase):
    """ExecutionSimulator.calc_commission."""

    def setUp(self):
        self.sim = ExecutionSimulator()

    def test_standard_commission(self):
        result = self.sim.calc_commission(100, 150.0)
        self.assertAlmostEqual(result, 15.0)

    def test_minimum_commission(self):
        result = self.sim.calc_commission(1, 1.0)
        self.assertEqual(result, 1.0)

    def test_negative_size(self):
        result = self.sim.calc_commission(-100, 150.0)
        self.assertAlmostEqual(result, 15.0)

    def test_closing_trade(self):
        result = self.sim.calc_commission(100, 150.0, is_closing=True)
        self.assertAlmostEqual(result, 15.0)


class TestExecutionSimulatorMarketImpact(unittest.TestCase):
    """ExecutionSimulator.calc_market_impact."""

    def test_zero_coeff_returns_zero(self):
        sim = ExecutionSimulator()
        result = sim.calc_market_impact(1000, 100.0, avg_volume=1e6)
        self.assertEqual(result, 0.0)

    def test_with_impact(self):
        cfg = ExecutionConfig(market_impact_coeff=0.1)
        sim = ExecutionSimulator(cfg)
        result = sim.calc_market_impact(1000, 100.0, avg_volume=1e6)
        self.assertGreater(result, 0.0)

    def test_zero_avg_volume(self):
        cfg = ExecutionConfig(market_impact_coeff=0.1)
        sim = ExecutionSimulator(cfg)
        result = sim.calc_market_impact(1000, 100.0, avg_volume=0.0)
        self.assertEqual(result, 0.0)

    def test_negative_size(self):
        cfg = ExecutionConfig(market_impact_coeff=0.1)
        sim = ExecutionSimulator(cfg)
        result = sim.calc_market_impact(-1000, 100.0, avg_volume=1e6)
        self.assertGreater(result, 0.0)


class TestExecutionSimulatorFill(unittest.TestCase):
    """ExecutionSimulator.simulate_fill."""

    def test_fill_buy_returns_all_keys(self):
        sim = ExecutionSimulator()
        result = sim.simulate_fill(100.0, 1, 100)
        self.assertIn("fill_price", result)
        self.assertIn("commission", result)
        self.assertIn("market_impact", result)
        self.assertIn("slippage_cost", result)
        self.assertIn("total_cost", result)

    def test_fill_buy_price_increased(self):
        sim = ExecutionSimulator()
        result = sim.simulate_fill(100.0, 1, 100)
        self.assertGreater(result["fill_price"], 100.0)

    def test_fill_sell_price_decreased(self):
        sim = ExecutionSimulator()
        result = sim.simulate_fill(100.0, -1, 100)
        self.assertLess(result["fill_price"], 100.0)

    def test_fill_with_market_impact(self):
        cfg = ExecutionConfig(market_impact_coeff=0.1)
        sim = ExecutionSimulator(cfg)
        result = sim.simulate_fill(100.0, 1, 1000, avg_volume=1e6)
        self.assertGreater(result["market_impact"], 0.0)
        self.assertGreater(
            result["total_cost"],
            result["slippage_cost"] + result["commission"],
        )

    def test_fill_total_cost_sum(self):
        sim = ExecutionSimulator()
        result = sim.simulate_fill(100.0, 1, 100)
        expected = result["commission"] + result["slippage_cost"] + result["market_impact"]
        self.assertAlmostEqual(result["total_cost"], expected)

    def test_fill_sell_impact_subtracted(self):
        cfg = ExecutionConfig(market_impact_coeff=0.1)
        sim = ExecutionSimulator(cfg)
        result = sim.simulate_fill(100.0, -1, 1000, avg_volume=1e6)
        slipped = sim.apply_slippage(100.0, -1)
        impact = sim.calc_market_impact(1000, 100.0, 1e6)
        expected_fill = slipped - impact
        self.assertAlmostEqual(result["fill_price"], expected_fill)


# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
