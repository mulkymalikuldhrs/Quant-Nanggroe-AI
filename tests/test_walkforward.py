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