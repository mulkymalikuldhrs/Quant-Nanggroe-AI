# Coverage target: report.py, walk_forward.py, composite_engine.py, crypto_engine.py

from __future__ import annotations

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.report import BacktestReport
from quant_nanggroe.engine.backtest.walk_forward import (
    WalkForwardAnalyzer,
    WalkForwardResult,
    WalkForwardStability,
)
from quant_nanggroe.engine.backtest.engines.composite_engine import CompositeEngine
from quant_nanggroe.engine.backtest.engines.crypto_engine import (
    CryptoEngine,
    calc_crypto_funding_fee,
    check_crypto_liquidation,
)
from quant_nanggroe.engine.backtest.portfolio import TradeRecord
from quant_nanggroe.engine.backtest.engines.base_engine import Position


def _make_trade(
    symbol: str = "AAPL",
    direction: int = 1,
    entry: float = 100.0,
    exit: float = 105.0,
    pnl: float = 5.0,
    pnl_pct: float = 0.05,
    reason: str = "signal",
    bars: int = 5,
) -> TradeRecord:
    ts = pd.Timestamp("2024-01-01")
    return TradeRecord(
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        exit_price=exit,
        entry_time=ts,
        exit_time=ts + pd.Timedelta(days=bars),
        size=100.0,
        pnl=pnl,
        pnl_pct=pnl_pct,
        exit_reason=reason,
        commission=1.0,
        holding_bars=bars,
    )


def _dummy_metrics(
    total_return: float = 0.15,
    sharpe: float = 1.5,
) -> dict:
    return {
        "total_return": total_return,
        "cagr": total_return,
        "annual_return": total_return,
        "max_drawdown": -0.10,
        "max_drawdown_duration": 15,
        "sharpe_ratio": sharpe,
        "sortino_ratio": 1.2,
        "calmar_ratio": 1.5,
        "volatility": 0.12,
        "var_95": -0.02,
        "cvar_95": -0.03,
        "downside_deviation": 0.08,
        "recovery_factor": 2.0,
        "tail_ratio": 1.1,
        "ulcer_index": 5.0,
        "total_trades": 10,
        "win_rate": 0.6,
        "profit_factor": 1.8,
        "avg_trade_pnl": 0.02,
        "avg_win": 0.05,
        "avg_loss": -0.02,
        "profit_loss_ratio": 2.5,
        "avg_holding_bars": 5,
        "max_consecutive_losses": 2,
    }


# ── Module A: BacktestReport ───────────────────────────────────────


class TestBacktestReportGenerate(unittest.TestCase):
    """Tests for BacktestReport.generate() and related methods."""

    def setUp(self):
        self.metrics = _dummy_metrics()
        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        self.equity_curve = pd.Series(
            np.linspace(100_000, 115_000, 50), index=dates
        )
        self.trades = [
            _make_trade("AAPL", 1, 100, 110, 10.0, 0.10),
            _make_trade("AAPL", -1, 110, 105, -5.0, -0.045),
        ]

    def test_generate_json_returns_valid_json(self):
        result = BacktestReport.generate(self.metrics, self.equity_curve, self.trades)
        parsed = json.loads(result)
        self.assertIn("summary", parsed)
        self.assertIn("trade_count", parsed)
        self.assertEqual(parsed["trade_count"], 2)
        self.assertIn("equity_curve", parsed)
        self.assertIn("drawdown", parsed)
        self.assertIn("monthly_returns", parsed)
        self.assertIn("trade_distribution", parsed)

    def test_generate_json_via_convenience_method(self):
        result = BacktestReport.generate_json(
            self.metrics, self.equity_curve, self.trades
        )
        parsed = json.loads(result)
        self.assertIn("strategy_name", parsed)

    def test_generate_text_returns_formatted_string(self):
        result = BacktestReport.generate(
            self.metrics, self.equity_curve, self.trades, format="text"
        )
        self.assertIn("TOTAL", result.upper())
        self.assertIn("15.00%", result)
        self.assertIn("SHARPE", result.upper())

    def test_generate_text_with_benchmark(self):
        bm = {"benchmark_return": 0.08, "excess_return": 0.07, "alpha": 0.03, "beta": 0.9}
        result = BacktestReport.generate(
            self.metrics, self.equity_curve, self.trades,
            format="text", benchmark_comparison=bm,
        )
        self.assertIn("BENCHMARK", result.upper())

    def test_generate_text_without_benchmark_still_works(self):
        result = BacktestReport.generate(
            self.metrics, self.equity_curve, self.trades, format="text"
        )
        self.assertIn("PERFORMANCE", result.upper())

    def test_generate_html_returns_html_string(self):
        result = BacktestReport.generate(
            self.metrics, self.equity_curve, self.trades, format="html"
        )
        self.assertIn("<!DOCTYPE html>", result)
        self.assertIn("Backtest Report", result)

    def test_generate_html_via_convenience_method(self):
        result = BacktestReport.generate_html(
            self.metrics, self.equity_curve, self.trades
        )
        self.assertIn("<html", result)

    def test_generate_html_includes_strategy_name(self):
        result = BacktestReport.generate(
            self.metrics, self.equity_curve, self.trades,
            format="html", strategy_name="TestStrat",
        )
        self.assertIn("TestStrat", result)

    def test_generate_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            BacktestReport.generate(
                self.metrics, self.equity_curve, self.trades, format="xml"
            )

    def test_generate_with_benchmark_and_sensitivity_in_json(self):
        bm = {"benchmark_return": 0.08}
        sa = {"param_name": "leverage", "optimal": {"optimal_value": 2.0}}
        result = BacktestReport.generate(
            self.metrics, self.equity_curve, self.trades,
            format="json", benchmark_comparison=bm, sensitivity_analysis=sa,
        )
        parsed = json.loads(result)
        self.assertIn("benchmark_comparison", parsed)
        self.assertIn("sensitivity_analysis", parsed)
        self.assertEqual(parsed["sensitivity_analysis"]["param_name"], "leverage")

    def test_generate_empty_equity_curve(self):
        empty_eq = pd.Series(dtype=float)
        result = BacktestReport.generate(
            self.metrics, empty_eq, [], format="json"
        )
        parsed = json.loads(result)
        self.assertEqual(parsed["trade_count"], 0)
        self.assertEqual(parsed["equity_curve"], [])

    def test_generate_empty_trades(self):
        result = BacktestReport.generate(
            self.metrics, self.equity_curve, [], format="json"
        )
        parsed = json.loads(result)
        self.assertEqual(parsed["trade_count"], 0)
        self.assertEqual(parsed["trades"], [])

    def test_generate_json_strategy_name(self):
        result = BacktestReport.generate_json(
            self.metrics, self.equity_curve, self.trades, strategy_name="MyStrategy"
        )
        parsed = json.loads(result)
        self.assertEqual(parsed["strategy_name"], "MyStrategy")

    def test_json_summary_filters_nested_dicts(self):
        nested_metrics = {**self.metrics, "nested": {"a": 1}}
        result = BacktestReport.generate_json(
            nested_metrics, self.equity_curve, self.trades
        )
        parsed = json.loads(result)
        self.assertNotIn("nested", parsed["summary"])


class TestBacktestReportCompute(unittest.TestCase):
    """Tests for BacktestReport static compute methods."""

    def test_compute_equity_chart_data_empty(self):
        result = BacktestReport._compute_equity_chart_data(pd.Series(dtype=float))
        self.assertEqual(result, [])

    def test_compute_equity_chart_data_nonempty(self):
        s = pd.Series([100.0, 101.0, 102.0], index=pd.date_range("2024-01-01", periods=3, freq="D"))
        result = BacktestReport._compute_equity_chart_data(s)
        self.assertEqual(len(result), 3)
        self.assertIn("t", result[0])
        self.assertIn("e", result[0])

    def test_compute_drawdown_data_empty(self):
        result = BacktestReport._compute_drawdown_data(pd.Series(dtype=float))
        self.assertEqual(result, [])

    def test_compute_drawdown_data_single_point(self):
        s = pd.Series([100.0], index=pd.DatetimeIndex(["2024-01-01"]))
        result = BacktestReport._compute_drawdown_data(s)
        self.assertEqual(result, [])

    def test_compute_drawdown_data_multiple(self):
        s = pd.Series([100.0, 105.0, 102.0, 110.0],
                      index=pd.date_range("2024-01-01", periods=4, freq="D"))
        result = BacktestReport._compute_drawdown_data(s)
        self.assertGreater(len(result), 0)
        self.assertIn("d", result[0])

    def test_compute_monthly_returns_empty(self):
        result = BacktestReport._compute_monthly_returns(pd.Series(dtype=float))
        self.assertEqual(result, {"years": [], "months": [], "data": {}})

    def test_compute_monthly_returns_with_data(self):
        dates = pd.date_range("2024-01-01", periods=400, freq="D")
        s = pd.Series(np.linspace(100, 110, 400), index=dates)
        result = BacktestReport._compute_monthly_returns(s)
        self.assertIn("years", result)
        self.assertIn("data", result)

    def test_compute_trade_distribution_empty(self):
        result = BacktestReport._compute_trade_distribution([])
        self.assertEqual(result["bins"], [])

    def test_compute_trade_distribution_with_trades(self):
        trades = [_make_trade(pnl_pct=0.1), _make_trade(pnl_pct=-0.05)]
        result = BacktestReport._compute_trade_distribution(trades)
        self.assertIn("bins", result)
        self.assertIn("counts", result)
        self.assertGreater(len(result["bins"]), 0)

    def test_html_monthly_returns_heatmap_empty(self):
        html = BacktestReport._html_monthly_returns_heatmap({"years": [], "months": [], "data": {}})
        self.assertIn("No monthly return", html)

    def test_html_trade_distribution_empty(self):
        html = BacktestReport._html_trade_distribution({"bins": [], "counts": []})
        self.assertIn("No trade distribution", html)

    def test_html_trade_distribution_with_data(self):
        data = {"bins": [-5.0, 0.0, 5.0], "counts": [1, 2, 1]}
        html = BacktestReport._html_trade_distribution(data)
        self.assertIn("<table>", html)

    def test_html_metrics_section(self):
        html = BacktestReport._html_metrics_section(self._metrics(), "Test Title")
        self.assertIn("Test Title", html)

    def test_html_risk_section(self):
        html = BacktestReport._html_risk_section(self._metrics())
        self.assertIn("Risk", html)

    def test_html_trade_section(self):
        html = BacktestReport._html_trade_section(self._metrics())
        self.assertIn("Trade", html)

    def test_html_benchmark_section(self):
        bm = {"benchmark_return": 0.08, "excess_return": 0.02, "alpha": 0.01, "beta": 0.9}
        html = BacktestReport._html_benchmark_section(bm)
        self.assertIn("Benchmark", html)

    def test_html_sensitivity_section(self):
        sa = {"param_name": "leverage", "optimal": {"optimal_value": 2.0, "metric_name": "Sharpe", "optimal_metric": 1.5}}
        html = BacktestReport._html_sensitivity_section(sa)
        self.assertIn("leverage", html)

    def _metrics(self):
        return _dummy_metrics()


# ── Module B: WalkForwardAnalyzer ──────────────────────────────────


class _MockEngine:
    """Mock BacktestEngine for WalkForwardAnalyzer tests."""

    def __init__(self):
        self.call_count = 0

    def run(self, prices, signals, **kwargs):
        self.call_count += 1
        n = len(prices)
        mock_eq = pd.Series(np.linspace(100, 110, n), index=prices.index) if n > 0 else pd.Series(dtype=float)
        return {
            "metrics": {
                "sharpe_ratio": 1.5,
                "total_return": 0.10,
                "max_drawdown": -0.05,
            },
            "equity_curve": mock_eq,
            "trades": [],
        }


class _MockStrategy:
    """Mock strategy for analyze_strategy tests."""

    def __init__(self, **kwargs):
        pass

    @staticmethod
    def required_columns():
        return ["close"]

    @staticmethod
    def warmup_period():
        return 2

    @staticmethod
    def generate_signal(data_slice):
        class _Signal:
            signal = 0.5
        return _Signal()


class TestWalkForwardDataclasses(unittest.TestCase):
    """Tests for WalkForwardResult and WalkForwardStability dataclasses."""

    def test_walk_forward_result_defaults(self):
        ts = pd.Timestamp("2024-01-01")
        r = WalkForwardResult(
            train_start=ts, train_end=ts, test_start=ts, test_end=ts,
            in_sample_return=0.1, out_of_sample_return=0.05,
            in_sample_sharpe=1.5, out_of_sample_sharpe=1.0,
            in_sample_max_dd=-0.1, out_of_sample_max_dd=-0.05,
            degradation_ratio=0.67,
        )
        self.assertEqual(r.in_sample_return, 0.1)
        self.assertEqual(r.degradation_ratio, 0.67)

    def test_walk_forward_stability_defaults(self):
        s = WalkForwardStability()
        self.assertEqual(s.sharpe_stability, 0.0)
        self.assertEqual(s.return_stability, 0.0)
        self.assertEqual(s.sharpe_positive_rate, 0.0)
        self.assertEqual(s.return_positive_rate, 0.0)
        self.assertEqual(s.degradation_consistency, 0.0)
        self.assertEqual(s.sharpe_rank_correlation, 0.0)
        self.assertEqual(s.effective_tests, 0)


class TestWalkForwardAnalyzerInit(unittest.TestCase):
    """Tests for WalkForwardAnalyzer construction."""

    def test_default_init(self):
        engine = _MockEngine()
        a = WalkForwardAnalyzer(engine)
        self.assertEqual(a.train_window, 252)
        self.assertEqual(a.test_window, 63)
        self.assertEqual(a.mode, "rolling")
        self.assertEqual(a.min_observations, 60)

    def test_custom_init(self):
        engine = _MockEngine()
        a = WalkForwardAnalyzer(engine, train_window=100, test_window=20, mode="anchored")
        self.assertEqual(a.train_window, 100)
        self.assertEqual(a.test_window, 20)
        self.assertEqual(a.mode, "anchored")

    def test_anchored_backward_compat(self):
        engine = _MockEngine()
        a = WalkForwardAnalyzer(engine, anchored=True)
        self.assertEqual(a.mode, "anchored")

    def test_cpcv_init(self):
        engine = _MockEngine()
        a = WalkForwardAnalyzer(engine, mode="cpcv", n_groups=6, n_test_groups=2)
        self.assertEqual(a.mode, "cpcv")
        self.assertEqual(a.n_groups, 6)


class TestWalkForwardAnalyzerAnalyze(unittest.TestCase):
    """Tests for WalkForwardAnalyzer.analyze()."""

    def setUp(self):
        self.mock_engine = _MockEngine()
        n = 100
        self.dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            {"ASSET": 100.0 * np.exp(np.cumsum(rng.normal(0, 0.005, n)))},
            index=self.dates,
        )
        self.signals = pd.DataFrame(
            {"ASSET": [1.0 if i % 2 == 0 else -1.0 for i in range(n)]},
            index=self.dates,
        )

    def test_analyze_returns_expected_keys(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5,
        )
        result = a.analyze(self.prices, self.signals)
        expected = {"windows", "aggregate", "degradation_stats", "stability", "mode", "oos_equity_curve"}
        self.assertTrue(expected.issubset(result.keys()))

    def test_analyze_rolling_produces_windows(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5
        )
        result = a.analyze(self.prices, self.signals)
        self.assertGreater(len(result["windows"]), 0)

    def test_analyze_aggregate_has_num_windows(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5
        )
        result = a.analyze(self.prices, self.signals)
        agg = result["aggregate"]
        self.assertIn("num_windows", agg)
        self.assertGreater(agg["num_windows"], 0)

    def test_analyze_stability_is_walk_forward_stability(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5
        )
        result = a.analyze(self.prices, self.signals)
        self.assertIsInstance(result["stability"], WalkForwardStability)

    def test_analyze_mode_in_result(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5
        )
        result = a.analyze(self.prices, self.signals)
        self.assertEqual(result["mode"], "rolling")

    def test_analyze_oos_equity_curve_not_empty(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5
        )
        result = a.analyze(self.prices, self.signals)
        self.assertGreater(len(result["oos_equity_curve"]), 0)

    def test_analyze_insufficient_data_returns_empty(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5
        )
        small_prices = self.prices.iloc[:5]
        small_signals = self.signals.iloc[:5]
        result = a.analyze(small_prices, small_signals)
        self.assertEqual(result["windows"], [])
        self.assertEqual(result["aggregate"], {})
        self.assertIsInstance(result["stability"], WalkForwardStability)

    def test_analyze_anchored_mode(self):
        anchored = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5,
            min_observations=5, mode="anchored",
        )
        result = anchored.analyze(self.prices, self.signals)
        self.assertEqual(result["mode"], "anchored")
        self.assertGreater(len(result["windows"]), 0)

    def test_analyze_with_purge_gap(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5,
            min_observations=5, purge_gap=2,
        )
        result = a.analyze(self.prices, self.signals)
        self.assertIn("windows", result)

    def test_engine_run_called(self):
        a = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5
        )
        self.mock_engine.call_count = 0
        a.analyze(self.prices, self.signals)
        self.assertGreater(self.mock_engine.call_count, 0)


class TestWalkForwardAnalyzerCPCV(unittest.TestCase):
    """Tests for CPCV mode."""

    def setUp(self):
        self.mock_engine = _MockEngine()
        self.analyzer = WalkForwardAnalyzer(
            self.mock_engine, mode="cpcv", n_groups=6, n_test_groups=2,
            min_observations=5,
        )
        n = 120
        self.dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rng = np.random.default_rng(42)
        self.prices = pd.DataFrame(
            {"ASSET": 100.0 * np.exp(np.cumsum(rng.normal(0, 0.005, n)))},
            index=self.dates,
        )
        self.signals = pd.DataFrame(
            {"ASSET": [1.0] * n}, index=self.dates
        )

    def test_cpcv_returns_cpcv_mode(self):
        result = self.analyzer.analyze(self.prices, self.signals)
        self.assertEqual(result["mode"], "cpcv")

    def test_cpcv_returns_windows(self):
        result = self.analyzer.analyze(self.prices, self.signals)
        self.assertIn("windows", result)

    def test_cpcv_returns_n_groups(self):
        result = self.analyzer.analyze(self.prices, self.signals)
        self.assertEqual(result["n_groups"], 6)

    def test_cpcv_returns_n_combinations(self):
        result = self.analyzer.analyze(self.prices, self.signals)
        self.assertGreater(result["n_combinations"], 0)


class TestWalkForwardAnalyzerAnalyzeStrategy(unittest.TestCase):
    """Tests for WalkForwardAnalyzer.analyze_strategy()."""

    def setUp(self):
        self.mock_engine = _MockEngine()
        self.analyzer = WalkForwardAnalyzer(
            self.mock_engine, train_window=20, test_window=5, min_observations=5,
        )
        n = 100
        self.dates = pd.date_range("2024-01-01", periods=n, freq="D")
        self.prices = pd.DataFrame(
            {"close": np.linspace(100, 110, n)}, index=self.dates
        )

    def test_analyze_strategy_returns_expected_keys(self):
        result = self.analyzer.analyze_strategy(self.prices, _MockStrategy)
        expected = {"windows", "aggregate", "degradation_stats", "stability", "mode", "oos_equity_curve", "n_folds"}
        self.assertTrue(expected.issubset(result.keys()))

    def test_analyze_strategy_produces_windows(self):
        result = self.analyzer.analyze_strategy(self.prices, _MockStrategy)
        self.assertGreater(len(result["windows"]), 0)

    def test_analyze_strategy_n_folds_positive(self):
        result = self.analyzer.analyze_strategy(self.prices, _MockStrategy)
        self.assertGreater(result["n_folds"], 0)

    def test_analyze_strategy_insufficient_data(self):
        small = self.prices.iloc[:5]
        result = self.analyzer.analyze_strategy(small, _MockStrategy)
        self.assertEqual(result["windows"], [])

    def test_analyze_strategy_with_params(self):
        result = self.analyzer.analyze_strategy(
            self.prices, _MockStrategy, strategy_params={"param": 1}
        )
        self.assertIn("windows", result)


class TestWalkForwardInternalMethods(unittest.TestCase):
    """Tests for internal helpers."""

    def setUp(self):
        self.a = WalkForwardAnalyzer(_MockEngine())

    def test_calculate_aggregate_empty(self):
        result = self.a._calculate_aggregate([], [], [])
        self.assertEqual(result, {})

    def test_calculate_degradation_stats_empty(self):
        result = self.a._calculate_degradation_stats([])
        self.assertEqual(result, {})

    def test_calculate_stability_empty(self):
        result = self.a._calculate_stability([], [], [])
        self.assertEqual(result.sharpe_stability, 0.0)

    def test_combine_oos_equity_empty(self):
        result = WalkForwardAnalyzer._combine_oos_equity([])
        self.assertTrue(result.empty)

    def test_combine_oos_equity_single(self):
        s = pd.Series([100.0, 101.0, 102.0])
        result = WalkForwardAnalyzer._combine_oos_equity([s])
        self.assertEqual(len(result), 3)


# ── Module C: CompositeEngine ──────────────────────────────────────


class TestCompositeEngineInit(unittest.TestCase):
    """Tests for CompositeEngine construction."""

    def test_default_init_no_codes(self):
        engine = CompositeEngine({"initial_cash": 500_000})
        self.assertEqual(engine.initial_capital, 500_000)
        self.assertEqual(engine._symbol_market, {})
        self.assertEqual(engine._rule_engines, {})

    def test_init_with_codes_detects_markets(self):
        codes = ["AAPL.US", "BTC-USDT", "EUR/USD"]
        engine = CompositeEngine({"initial_cash": 100_000}, codes=codes)
        self.assertIn("us_equity", engine._rule_engines)
        self.assertIn("crypto", engine._rule_engines)

    def test_init_with_codes_populates_symbol_market(self):
        codes = ["AAPL.US"]
        engine = CompositeEngine({}, codes=codes)
        self.assertEqual(engine._symbol_market["AAPL.US"], "us_equity")

    def test_init_empty_config(self):
        engine = CompositeEngine({})
        self.assertEqual(engine.initial_capital, 1_000_000)  # default from BaseEngine

    def test_init_funding_and_swap_tracking(self):
        engine = CompositeEngine({})
        self.assertEqual(engine._funding_applied, set())
        self.assertEqual(engine._funding_daily_done, set())
        self.assertEqual(engine._last_swap_dates, {})


class TestCompositeEngineRuleFor(unittest.TestCase):
    """Tests for CompositeEngine._rule_for()."""

    def setUp(self):
        self.engine = CompositeEngine({}, codes=["AAPL.US", "BTC-USDT", "000001.SZ"])

    def test_rule_for_known_symbol(self):
        r = self.engine._rule_for("AAPL.US")
        from quant_nanggroe.engine.backtest.engines.equity_engine import EquityEngine
        self.assertIsInstance(r, EquityEngine)

    def test_rule_for_crypto_symbol(self):
        r = self.engine._rule_for("BTC-USDT")
        self.assertIsInstance(r, CryptoEngine)

    def test_rule_for_unknown_symbol_auto_registers_equity(self):
        r = self.engine._rule_for("UNKNOWN")
        from quant_nanggroe.engine.backtest.engines.equity_engine import EquityEngine
        self.assertIsInstance(r, EquityEngine)

    def test_rule_for_raises_for_unhandled_market(self):
        """A symbol that maps to a non-registered, non-auto market raises."""
        engine = CompositeEngine({})
        # Force a market not in _rule_engines and not auto-registerable
        engine._symbol_market["TEST"] = "bogus_market"
        with self.assertRaises(ValueError):
            engine._rule_for("TEST")


class TestCompositeEngineDelegation(unittest.TestCase):
    """Tests for CompositeEngine delegation methods."""

    def setUp(self):
        self.engine = CompositeEngine({}, codes=["AAPL.US", "BTC-USDT"])
        self.engine._active_symbol = "AAPL.US"
        self.bar = pd.Series({"close": 150.0, "high": 151.0, "low": 149.0}, name=pd.Timestamp("2024-01-01"))

    def test_can_execute_us_equity_delegates(self):
        result = self.engine.can_execute("AAPL.US", 1, self.bar)
        self.assertTrue(result)

    def test_can_execute_crypto_delegates(self):
        result = self.engine.can_execute("BTC-USDT", 1, self.bar)
        self.assertTrue(result)

    def test_can_execute_a_share_t1_block(self):
        engine = CompositeEngine({}, codes=["000001.SZ"])
        engine._active_symbol = "000001.SZ"
        from quant_nanggroe.engine.backtest.engines.base_engine import Position
        pos = Position(
            symbol="000001.SZ",
            direction=1,
            entry_price=10.0,
            entry_time=pd.Timestamp("2024-01-01"),
            size=100.0,
        )
        engine.positions["000001.SZ"] = pos
        bar = pd.Series({"close": 11.0}, name=pd.Timestamp("2024-01-01"))
        self.assertFalse(engine.can_execute("000001.SZ", 0, bar))

    def test_round_size(self):
        result = self.engine.round_size(100.567, 150.0)
        self.assertAlmostEqual(result, 100.57, places=2)

    def test_calc_commission(self):
        result = self.engine.calc_commission(100.0, 150.0, 1, True)
        self.assertGreaterEqual(result, 0)

    def test_apply_slippage(self):
        result = self.engine.apply_slippage(150.0, 1)
        self.assertNotEqual(result, 150.0)

    def test_calc_pnl_delegation(self):
        pnl = self.engine._calc_pnl("AAPL.US", 1, 100.0, 100.0, 105.0)
        self.assertEqual(pnl, 500.0)

    def test_calc_margin_delegation(self):
        margin = self.engine._calc_margin("AAPL.US", 100.0, 100.0, 2.0)
        self.assertEqual(margin, 5000.0)

    def test_calc_raw_size_delegation(self):
        size = self.engine._calc_raw_size("AAPL.US", 10_000.0, 100.0)
        self.assertEqual(size, 100.0)


class TestCompositeEngineResetState(unittest.TestCase):
    """Tests for CompositeEngine._reset_state()."""

    def test_reset_state_clears_funding_and_swap(self):
        engine = CompositeEngine({}, codes=["BTC-USDT"])
        engine._funding_applied.add(("BTC-USDT", "2024-01-01", 8))
        engine._funding_daily_done.add(("BTC-USDT", "2024-01-01"))
        engine._last_swap_dates["EUR/USD"] = "2024-01-01"
        engine._reset_state()
        self.assertEqual(engine._funding_applied, set())
        self.assertEqual(engine._funding_daily_done, set())
        self.assertEqual(engine._last_swap_dates, {})


class TestCompositeEngineOnBar(unittest.TestCase):
    """Tests for CompositeEngine.on_bar() - crypto funding path."""

    def test_on_bar_crypto_no_position_no_change(self):
        engine = CompositeEngine({}, codes=["BTC-USDT"])
        capital_before = engine.capital
        bar = pd.Series({"close": 50_000.0}, name=pd.Timestamp("2024-01-01"))
        engine.on_bar("BTC-USDT", bar, pd.Timestamp("2024-01-01 08:00"))
        self.assertEqual(engine.capital, capital_before)

    def test_on_bar_with_crypto_position_deducts_funding(self):
        engine = CompositeEngine({"leverage": 10.0}, codes=["BTC-USDT"])
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0, leverage=10.0,
        )
        engine.positions["BTC-USDT"] = pos
        capital_before = engine.capital
        bar = pd.Series({"close": 51_000.0}, name=pd.Timestamp("2024-01-01"))
        engine.on_bar("BTC-USDT", bar, pd.Timestamp("2024-01-01 08:00"))
        # Funding fee was deducted
        self.assertLess(engine.capital, capital_before)

    def test_on_bar_daily_bar_fallback_deducts_once(self):
        engine = CompositeEngine({"leverage": 10.0}, codes=["BTC-USDT"])
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0, leverage=10.0,
        )
        engine.positions["BTC-USDT"] = pos
        bar = pd.Series({"close": 51_000.0})
        ts1 = pd.Timestamp("2024-01-01")
        ts2 = pd.Timestamp("2024-01-01")  # same date
        capital_before = engine.capital
        engine.on_bar("BTC-USDT", bar, ts1)
        after_first = engine.capital
        engine.on_bar("BTC-USDT", bar, ts2)
        # Should not deduct twice on same date
        self.assertEqual(engine.capital, after_first)


# ── Module D: CryptoEngine ─────────────────────────────────────────


class TestCryptoEngineInit(unittest.TestCase):
    """Tests for CryptoEngine construction."""

    def test_default_config(self):
        engine = CryptoEngine({})
        self.assertEqual(engine.maker_rate, 0.0002)
        self.assertEqual(engine.taker_rate, 0.0005)
        self.assertEqual(engine.slippage_rate, 0.0005)
        self.assertEqual(engine.margin_mode, "isolated")
        self.assertEqual(engine.funding_rate, 0.0001)
        self.assertEqual(engine.default_leverage, 1.0)

    def test_custom_config(self):
        cfg = {
            "maker_rate": 0.0001,
            "taker_rate": 0.0004,
            "slippage": 0.001,
            "margin_mode": "cross",
            "funding_rate": 0.0002,
            "leverage": 5.0,
        }
        engine = CryptoEngine(cfg)
        self.assertEqual(engine.maker_rate, 0.0001)
        self.assertEqual(engine.taker_rate, 0.0004)
        self.assertEqual(engine.slippage_rate, 0.001)
        self.assertEqual(engine.margin_mode, "cross")
        self.assertEqual(engine.funding_rate, 0.0002)
        self.assertEqual(engine.default_leverage, 5.0)

    def test_initial_capital_default(self):
        engine = CryptoEngine({})
        self.assertEqual(engine.initial_capital, 1_000_000)

    def test_initial_capital_custom(self):
        engine = CryptoEngine({"initial_cash": 50_000})
        self.assertEqual(engine.initial_capital, 50_000)

    def test_funding_tracking_sets(self):
        engine = CryptoEngine({})
        self.assertEqual(engine._funding_applied, set())
        self.assertEqual(engine._funding_daily_done, set())


class TestCryptoEngineBehavior(unittest.TestCase):
    """Tests for CryptoEngine market-rule methods."""

    def setUp(self):
        self.engine = CryptoEngine({})

    def test_can_execute_always_true(self):
        bar = pd.Series({"close": 100.0}, name=pd.Timestamp("2024-01-01"))
        self.assertTrue(self.engine.can_execute("BTC-USDT", 1, bar))
        self.assertTrue(self.engine.can_execute("BTC-USDT", -1, bar))
        self.assertTrue(self.engine.can_execute("BTC-USDT", 0, bar))

    def test_round_size_rounds_to_6_decimals(self):
        self.assertAlmostEqual(self.engine.round_size(1.23456789, 100.0), 1.234568)
        self.assertAlmostEqual(self.engine.round_size(0.0, 100.0), 0.0)

    def test_round_size_no_negative(self):
        self.assertAlmostEqual(self.engine.round_size(-1.0, 100.0), 0.0)

    def test_calc_commission_open_uses_taker(self):
        result = self.engine.calc_commission(100.0, 50_000.0, 1, True)
        self.assertAlmostEqual(result, 100.0 * 50_000.0 * 0.0005)

    def test_calc_commission_close_uses_maker(self):
        result = self.engine.calc_commission(100.0, 50_000.0, 1, False)
        self.assertAlmostEqual(result, 100.0 * 50_000.0 * 0.0002)

    def test_apply_slippage_long(self):
        result = self.engine.apply_slippage(100.0, 1)
        expected = 100.0 * (1 + 1 * 0.0005)
        self.assertAlmostEqual(result, expected)

    def test_apply_slippage_short(self):
        result = self.engine.apply_slippage(100.0, -1)
        expected = 100.0 * (1 + (-1) * 0.0005)
        self.assertAlmostEqual(result, expected)

    def test_on_bar_no_position_no_change(self):
        capital_before = self.engine.capital
        bar = pd.Series({"close": 100.0}, name=pd.Timestamp("2024-01-01"))
        self.engine.on_bar("BTC-USDT", bar, pd.Timestamp("2024-01-01"))
        self.assertEqual(self.engine.capital, capital_before)


class TestCryptoEngineReset(unittest.TestCase):
    """Tests for CryptoEngine._reset_state()."""

    def test_reset_state_clears_funding_sets(self):
        engine = CryptoEngine({})
        engine._funding_applied.add(("BTC", "2024-01-01", 8))
        engine._funding_daily_done.add(("BTC", "2024-01-01"))
        engine._reset_state()
        self.assertEqual(engine._funding_applied, set())
        self.assertEqual(engine._funding_daily_done, set())


class TestCryptoFundingFee(unittest.TestCase):
    """Tests for calc_crypto_funding_fee standalone function."""

    def test_no_timestamp_date_returns_zero(self):
        fee = calc_crypto_funding_fee(
            "BTC-USDT", pd.Series({"close": 100.0}),
            "no-date-object", {}, 0.0001, set(), set(),
        )
        self.assertEqual(fee, 0.0)

    def test_no_position_returns_zero(self):
        fee = calc_crypto_funding_fee(
            "BTC-USDT", pd.Series({"close": 100.0}),
            pd.Timestamp("2024-01-01 08:00"), {}, 0.0001, set(), set(),
        )
        self.assertEqual(fee, 0.0)

    def test_with_position_returns_notional_times_rate(self):
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0,
        )
        fee = calc_crypto_funding_fee(
            "BTC-USDT", pd.Series({"close": 51_000.0}),
            pd.Timestamp("2024-01-01 08:00"), {"BTC-USDT": pos},
            0.0001, set(), set(),
        )
        self.assertAlmostEqual(fee, 1.0 * 51_000.0 * 0.0001 * 1.0)

    def test_deduplication_hourly(self):
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0,
        )
        applied = set()
        fee1 = calc_crypto_funding_fee(
            "BTC-USDT", pd.Series({"close": 51_000.0}),
            pd.Timestamp("2024-01-01 08:00"), {"BTC-USDT": pos},
            0.0001, applied, set(),
        )
        fee2 = calc_crypto_funding_fee(
            "BTC-USDT", pd.Series({"close": 51_000.0}),
            pd.Timestamp("2024-01-01 08:00"), {"BTC-USDT": pos},
            0.0001, applied, set(),
        )
        self.assertNotEqual(fee1, 0.0)
        self.assertEqual(fee2, 0.0)

    def test_daily_fallback_dedup(self):
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0,
        )
        daily_done = set()
        ts = pd.Timestamp("2024-01-01 12:00")  # hour not in {0,8,16} -> daily fallback
        fee1 = calc_crypto_funding_fee(
            "BTC-USDT", pd.Series({"close": 51_000.0}),
            ts, {"BTC-USDT": pos},
            0.0001, set(), daily_done,
        )
        fee2 = calc_crypto_funding_fee(
            "BTC-USDT", pd.Series({"close": 51_000.0}),
            ts, {"BTC-USDT": pos},
            0.0001, set(), daily_done,
        )
        self.assertNotEqual(fee1, 0.0)
        self.assertEqual(fee2, 0.0)


class TestCryptoLiquidation(unittest.TestCase):
    """Tests for check_crypto_liquidation standalone function."""

    def test_no_position_returns_false(self):
        result = check_crypto_liquidation("BTC-USDT", pd.Series({"close": 100.0}), {})
        self.assertFalse(result)

    def test_low_leverage_returns_false(self):
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0, leverage=1.0,
        )
        result = check_crypto_liquidation(
            "BTC-USDT", pd.Series({"close": 51_000.0}), {"BTC-USDT": pos},
        )
        self.assertFalse(result)

    def test_high_leverage_favorable_move_no_liquidation(self):
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0, leverage=10.0,
        )
        result = check_crypto_liquidation(
            "BTC-USDT", pd.Series({"close": 55_000.0}), {"BTC-USDT": pos},
        )
        self.assertFalse(result)

    def test_high_leverage_adverse_move_can_liquidate(self):
        pos = Position(
            symbol="BTC-USDT", direction=1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0, leverage=100.0,
        )
        result = check_crypto_liquidation(
            "BTC-USDT", pd.Series({"close": 49_000.0}), {"BTC-USDT": pos},
        )
        # At 100x leverage, a 2% drop may trigger liquidation
        self.assertTrue(result)

    def test_short_position_adverse_move(self):
        pos = Position(
            symbol="BTC-USDT", direction=-1, entry_price=50_000.0,
            entry_time=pd.Timestamp("2024-01-01"), size=1.0, leverage=100.0,
        )
        result = check_crypto_liquidation(
            "BTC-USDT", pd.Series({"close": 51_500.0}), {"BTC-USDT": pos},
        )
        self.assertTrue(result)


class TestMaintenanceRate(unittest.TestCase):
    """Tests for the internal _maintenance_rate function."""

    def test_small_notional_low_rate(self):
        from quant_nanggroe.engine.backtest.engines.crypto_engine import _maintenance_rate
        self.assertEqual(_maintenance_rate(50_000), 0.004)

    def test_large_notional_high_rate(self):
        from quant_nanggroe.engine.backtest.engines.crypto_engine import _maintenance_rate
        self.assertEqual(_maintenance_rate(20_000_000), 0.10)

    def test_infinity_handling(self):
        from quant_nanggroe.engine.backtest.engines.crypto_engine import _maintenance_rate
        self.assertEqual(_maintenance_rate(float("inf")), 0.10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
