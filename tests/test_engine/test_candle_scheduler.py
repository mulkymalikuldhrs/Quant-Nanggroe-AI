"""Tests for CandleScheduler — real-time candle-close multi-TF scheduler."""

from __future__ import annotations

import time

from quant_nanggroe.engine.candle_scheduler import (
    ANALYSIS_TIMEFRAMES,
    MT5_TF_MAP,
    TIMEFRAME_SECONDS,
    CandleScheduler,
    CandleState,
    CycleResult,
    start_candle_scheduler,
    stop_candle_scheduler,
)


class TestConstants:
    def test_timeframe_seconds(self):
        assert TIMEFRAME_SECONDS["M15"] == 900
        assert TIMEFRAME_SECONDS["H1"] == 3600
        assert TIMEFRAME_SECONDS["H4"] == 14400
        assert TIMEFRAME_SECONDS["D1"] == 86400

    def test_mt5_tf_map(self):
        assert MT5_TF_MAP["M15"] == 15
        assert MT5_TF_MAP["H1"] == 16385
        assert MT5_TF_MAP["D1"] == 16408

    def test_analysis_timeframes(self):
        assert ANALYSIS_TIMEFRAMES == ["M15", "H1", "H4", "D1"]


class TestCandleState:
    def test_init(self):
        state = CandleState(symbol="EURUSD", timeframe="H1")
        assert state.symbol == "EURUSD"
        assert state.timeframe == "H1"
        assert state.last_close_time == 0.0
        assert state.bars_processed == 0

    def test_with_values(self):
        state = CandleState(
            symbol="XAUUSD", timeframe="D1",
            last_close_time=1700000000.0, last_check=1700000001.0,
            bars_processed=42,
        )
        assert state.bars_processed == 42


class TestCycleResult:
    def test_init(self):
        result = CycleResult(symbol="EURUSD", timeframe="H1", timestamp="2026-01-01T00:00:00")
        assert result.symbol == "EURUSD"
        assert result.signal == "hold"
        assert result.confidence == 0.0
        assert result.traded is False
        assert result.error is None

    def test_with_values(self):
        result = CycleResult(
            symbol="GBPUSD", timeframe="M15",
            timestamp="2026-01-01T00:00:00",
            signal="buy", confidence=0.85, traded=True,
            duration_ms=123.4,
        )
        assert result.signal == "buy"
        assert result.traded is True


class TestCandleScheduler:
    def test_init_defaults(self):
        sched = CandleScheduler()
        assert sched.timeframes == ["M15", "H1", "H4", "D1"]
        assert sched.tick_interval == 1.0
        assert sched.min_confidence == 0.30
        assert sched.is_running is False

    def test_init_custom(self):
        sched = CandleScheduler(
            symbols=["EURUSD", "XAUUSD"],
            timeframes=["H1", "D1"],
            tick_interval=5.0,
            min_confidence=0.5,
        )
        assert sched.symbols == ["EURUSD", "XAUUSD"]
        assert sched.timeframes == ["H1", "D1"]
        assert sched.tick_interval == 5.0
        assert sched.min_confidence == 0.5

    def test_recent_results_empty(self):
        sched = CandleScheduler()
        assert sched.recent_results == []

    def test_recent_results_with_data(self):
        sched = CandleScheduler()
        sched._results.append(CycleResult(
            symbol="EURUSD", timeframe="H1",
            timestamp="2026-01-01T00:00:00",
            signal="buy", confidence=0.8, traded=True,
        ))
        results = sched.recent_results
        assert len(results) == 1
        assert results[0]["symbol"] == "EURUSD"
        assert results[0]["signal"] == "buy"

    def test_check_mtf_alignment_bullish(self):
        sched = CandleScheduler()
        import numpy as np
        import pandas as pd

        # Create bullish data: price > SMA20 > SMA50
        np.random.seed(42)
        n = 100
        closes = 100 + np.cumsum(np.ones(n) * 0.5)  # steadily rising
        tf_data = {
            "H1": pd.DataFrame({
                "open": closes - 0.1,
                "high": closes + 0.5,
                "low": closes - 0.5,
                "close": closes,
                "volume": np.ones(n) * 1e6,
            }),
            "D1": pd.DataFrame({
                "open": closes - 0.1,
                "high": closes + 0.5,
                "low": closes - 0.5,
                "close": closes,
                "volume": np.ones(n) * 1e6,
            }),
        }

        result = sched._check_mtf_alignment(tf_data, "H1")
        assert result["aligned"] is True
        assert result["direction"] == "bullish"

    def test_check_mtf_alignment_mixed(self):
        sched = CandleScheduler()
        import numpy as np
        import pandas as pd

        n = 100
        # H1 bullish (rising)
        h1_closes = 100 + np.cumsum(np.ones(n) * 0.5)
        # D1 bearish (falling)
        d1_closes = 200 - np.cumsum(np.ones(n) * 0.5)

        tf_data = {
            "H1": pd.DataFrame({
                "open": h1_closes - 0.1, "high": h1_closes + 0.5,
                "low": h1_closes - 0.5, "close": h1_closes,
                "volume": np.ones(n) * 1e6,
            }),
            "D1": pd.DataFrame({
                "open": d1_closes + 0.1, "high": d1_closes + 0.5,
                "low": d1_closes - 0.5, "close": d1_closes,
                "volume": np.ones(n) * 1e6,
            }),
        }

        result = sched._check_mtf_alignment(tf_data, "H1")
        assert result["aligned"] is False

    def test_save_state(self):
        sched = CandleScheduler(symbols=["EURUSD"], timeframes=["H1", "D1"])
        sched._running = True
        sched._start_time = time.time() - 100
        sched._results.append(CycleResult(
            symbol="EURUSD", timeframe="H1",
            timestamp="2026-01-01T00:00:00",
            signal="buy", confidence=0.8, traded=True,
        ))

        sched._save_state()

        from pathlib import Path
        state_file = Path("data/candle_scheduler_state.json")
        events_file = Path("data/notifications.json")
        assert state_file.exists()
        assert events_file.exists()

        import json
        state = json.loads(state_file.read_text())
        assert state["running"] is True
        assert state["symbols"] == ["EURUSD"]
        assert state["total_events"] == 1

        events = json.loads(events_file.read_text())
        assert len(events["notifications"]) == 1
        assert events["notifications"][0]["type"] == "trade"


class TestSingleton:
    def test_start_stop(self):
        # Reset singleton
        import quant_nanggroe.engine.candle_scheduler as mod
        mod._default_scheduler = None

        sched = start_candle_scheduler(symbols=["EURUSD"], timeframes=["H1"])
        assert sched is not None
        assert sched.is_running

        stop_candle_scheduler(timeout=1.0)
        # After stop, singleton should be cleared
        assert mod._default_scheduler is None
