"""oos_win_rate passthrough tests for WalkForwardResult pipeline.

Covers: (a) passthrough when engine metrics carry win_rate,
(b) 0.0 default when absent, (c) trade-weighted aggregate mean on
synthetic windows, (d) CPCV entry picks it up end-to-end.
No network, no yfinance.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from quant_nanggroe.engine.backtest.walk_forward import (
    WalkForwardAnalyzer,
    WalkForwardResult,
)
from scripts.run_cpcv_validation import build_cpcv_entry


def _w(**kw):
    base = dict(
        train_start=pd.Timestamp("2024-01-01"),
        train_end=pd.Timestamp("2024-02-01"),
        test_start=pd.Timestamp("2024-02-02"),
        test_end=pd.Timestamp("2024-03-01"),
        in_sample_return=0.05,
        out_of_sample_return=0.03,
        in_sample_sharpe=1.0,
        out_of_sample_sharpe=0.8,
        in_sample_max_dd=-0.02,
        out_of_sample_max_dd=-0.03,
        degradation_ratio=0.8,
        is_trades=20,
        oos_trades=10,
    )
    base.update(kw)
    return WalkForwardResult(**base)


def _analyzer_with_metrics(oos_metrics):
    engine = MagicMock()
    is_res = {"metrics": {"total_return": 0.05, "sharpe_ratio": 1.0,
                          "max_drawdown": -0.02, "total_trades": 20,
                          "win_rate": 0.55},
              "equity_curve": pd.Series(dtype=float)}
    oos_res = {"metrics": oos_metrics,
               "equity_curve": pd.Series(dtype=float)}
    engine.run.side_effect = [is_res, oos_res]
    analyzer = WalkForwardAnalyzer(engine=engine, train_window=30,
                                   test_window=10, min_observations=5)
    return analyzer


def _prices(n=60):
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    df = pd.DataFrame({"close": [100.0 + i for i in range(n)]}, index=idx)
    sig = pd.DataFrame({"close": [1.0] * n}, index=idx)
    return df, sig


def test_passthrough_present_when_metrics_have_it():
    analyzer = _analyzer_with_metrics(
        {"total_return": 0.03, "sharpe_ratio": 0.8,
         "max_drawdown": -0.03, "total_trades": 8, "win_rate": 0.625})
    prices, signals = _prices()
    res = analyzer.analyze(prices, signals)
    assert len(res["windows"]) >= 1
    assert res["windows"][0].oos_win_rate == 0.625


def test_default_zero_when_metrics_absent():
    analyzer = _analyzer_with_metrics(
        {"total_return": 0.03, "sharpe_ratio": 0.8,
         "max_drawdown": -0.03, "total_trades": 8})
    prices, signals = _prices()
    res = analyzer.analyze(prices, signals)
    assert len(res["windows"]) >= 1
    assert res["windows"][0].oos_win_rate == 0.0


def test_dataclass_default_is_zero():
    w = _w()
    assert w.oos_win_rate == 0.0


def test_aggregate_trade_weighted_mean_correct():
    analyzer = WalkForwardAnalyzer(engine=MagicMock())
    windows = [_w(oos_win_rate=0.6, oos_trades=10,
                  out_of_sample_return=0.02),
               _w(oos_win_rate=0.4, oos_trades=30,
                  out_of_sample_return=-0.01)]
    agg = analyzer._calculate_aggregate(
        windows, [0.02, -0.01], [0.5, -0.2], [10, 30])
    expected = (0.6 * 10 + 0.4 * 30) / 40
    assert agg["oos_win_rate_mean"] == expected
    # legacy fold-rate key untouched
    assert agg["win_rate"] == 0.5
    assert agg["fold_profit_share"] == 0.5


def test_cpcv_entry_picks_up_oos_win_rate_end_to_end():
    windows = [_w(oos_win_rate=0.6, oos_trades=10),
               _w(oos_win_rate=0.4, oos_trades=6)]
    entry = build_cpcv_entry("BTC-USD", windows)
    assert entry["win_rate"] == round((0.6 + 0.4) / 2, 4)
    # legacy SimpleNamespace path still works
    legacy = [SimpleNamespace(out_of_sample_sharpe=0.3)]
    assert build_cpcv_entry("X", legacy)["win_rate"] is None
