# Tests for walk-forward backtest runner

import sys, json, os, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.run_walkforward import load_candles, run_strategy_backtest

def test_load_candles_missing_file():
    # Provide a symbol that doesn't have data
    result = load_candles("NONEXISTENT")
    assert result == []

def test_load_candles_valid(tmp_path: Path):
    # Create a minimal candle file
    data = [{"close": 100.0, "open": 99.0, "high": 101.0, "low": 98.0, "volume": 1000}]
    file_path = tmp_path / "BTCUSDT_daily.json"
    file_path.write_text(json.dumps(data))
    # Override DATA_DIR in the module
    import importlib
    import scripts.run_walkforward as rw
    original_dir = rw.DATA_DIR
    rw.DATA_DIR = tmp_path
    try:
        result = load_candles("BTCUSDT")
        assert len(result) == 1
        assert result[0]["close"] == 100.0
    finally:
        rw.DATA_DIR = original_dir

def test_run_strategy_backtest_no_data():
    result = run_strategy_backtest("Momentum", [])
    assert result is not None
    assert result.get("total_trades", 0) == 0

def test_aggregate_significance_keys():
    # P1 regression: significance gate must expose per-trade expectancy +
    # median-fold trade count, and flag under-sampling by MEDIAN (not min).
    from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer, WalkForwardResult

    def mk(oos_trades, ret):
        return WalkForwardResult(
            train_start=None, train_end=None, test_start=None, test_end=None,
            in_sample_return=0.0, out_of_sample_return=ret, in_sample_sharpe=0.0,
            out_of_sample_sharpe=0.5, in_sample_max_dd=0.0, out_of_sample_max_dd=0.0,
            degradation_ratio=1.0, is_trades=oos_trades, oos_trades=oos_trades,
        )

    # Well-sampled: 3 folds, 50 trades each, +10% return per fold
    wins = [mk(50, 0.10), mk(50, 0.10), mk(50, 0.10)]
    # engine arg required by ctor but _calculate_aggregate doesn't touch it
    agg = WalkForwardAnalyzer(None)._calculate_aggregate(
        wins, [0.10, 0.10, 0.10], [0.5, 0.5, 0.5], [50, 50, 50]
    )
    assert agg["median_fold_oos_trades"] == 50
    assert abs(agg["avg_oos_return_per_trade"] - 0.002) < 1e-9  # 0.10 / 50
    assert agg["under_sampled"] is False
    assert abs(agg["avg_oos_return"] - 0.10) < 1e-9

    # Under-sampled: median fold has only 5 trades (< 30 threshold)
    small = [mk(5, 0.10), mk(5, 0.10), mk(5, 0.10)]
    agg2 = WalkForwardAnalyzer(None)._calculate_aggregate(
        small, [0.10, 0.10, 0.10], [0.5, 0.5, 0.5], [5, 5, 5]
    )
    assert agg2["median_fold_oos_trades"] == 5
    assert agg2["under_sampled"] is True
    # per-trade expectancy still computed (0.10/5 = 0.02) — not hidden by median flag
    assert abs(agg2["avg_oos_return_per_trade"] - 0.02) < 1e-9