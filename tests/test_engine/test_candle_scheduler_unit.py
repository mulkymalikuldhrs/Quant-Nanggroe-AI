"""Unit tests for CandleScheduler PURE logic (no MT5, no threads, no network).

Scope note: quant_nanggroe/engine/candle_scheduler.py contains NO week-reset
heuristic and NO weekly_override 72h-cap logic (verified by grep — those live
in launch.bat weekly-reset + data/weekly_override.json + manager.py WIB
handling, not in this module). What IS testable here without MT5:
  - timeframe tables (TIMEFRAME_SECONDS, MT5_TF_MAP)
  - CandleState / CycleResult dataclass defaults
  - recent_results 50-item cap + field mapping
  - _check_mtf_alignment bias math (SMA20/SMA50)
  - _check_all_closes_sync close detection + probe_empty counting
    (via stubbed broker — the "probe 0/32" heartbeat stat)
  - _save_state persistence round-trip (data/candle_scheduler_state.json)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.candle_scheduler import (
    ANALYSIS_TIMEFRAMES,
    MT5_TF_MAP,
    TIMEFRAME_SECONDS,
    CandleScheduler,
    CandleState,
    CycleResult,
)


def _trend_df(n: int = 100, slope: float = 1.0, seed: int = 7, noise: float = 0.05) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 + slope * np.arange(n) + rng.normal(0, noise, n)
    return pd.DataFrame({
        "open": close, "high": close + 0.1, "low": close - 0.1,
        "close": close, "volume": np.full(n, 1000.0),
    })


class FakeBroker:
    """Minimal broker stub exposing get_rates(sym, tf_enum, count)."""

    def __init__(self, bars: dict | None = None, connected: bool = True):
        self.connected = connected
        self._bars = bars or {}
        self.calls = 0

    def get_rates(self, sym, tf_enum, count=2):
        self.calls += 1
        return self._bars.get((sym, tf_enum))


def _rates(bar_time: float) -> np.ndarray:
    return np.array(
        [(bar_time - 900.0, 1.0, 1.0, 1.0, 1.0, 10),
         (bar_time, 1.0, 1.0, 1.0, 1.0, 10)],
        dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"),
               ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")],
    )


# ── tables ──────────────────────────────────────────────────────────────

def test_timeframe_seconds_values():
    assert TIMEFRAME_SECONDS["M15"] == 900
    assert TIMEFRAME_SECONDS["H1"] == 3600
    assert TIMEFRAME_SECONDS["H4"] == 14400
    assert TIMEFRAME_SECONDS["D1"] == 86400
    assert set(ANALYSIS_TIMEFRAMES) == {"M15", "H1", "H4", "D1"}


def test_mt5_tf_map_values():
    assert MT5_TF_MAP["M15"] == 15
    assert MT5_TF_MAP["H1"] == 16385
    assert MT5_TF_MAP["H4"] == 16388
    assert MT5_TF_MAP["D1"] == 16408


def test_candle_state_defaults():
    s = CandleState(symbol="EURUSD", timeframe="M15")
    assert s.last_close_time == 0.0
    assert s.last_check == 0.0
    assert s.bars_processed == 0


# ── recent_results ──────────────────────────────────────────────────────

def test_recent_results_caps_at_50_with_field_mapping():
    sched = CandleScheduler(symbols=["EURUSD"], timeframes=["M15"])
    for i in range(60):
        sched._results.append(CycleResult(
            symbol="EURUSD", timeframe="M15", timestamp=f"2026-01-01T00:{i:02d}:00+00:00",
            signal="buy", confidence=0.8, traded=True))
    recent = sched.recent_results
    assert len(recent) == 50
    assert recent[0]["timestamp"] == "2026-01-01T00:10:00+00:00"
    assert set(recent[0]) == {"symbol", "timeframe", "signal", "confidence",
                              "traded", "notified", "error", "timestamp", "duration_ms"}


# ── MTF alignment ───────────────────────────────────────────────────────

def test_mtf_alignment_bullish():
    sched = CandleScheduler(symbols=["EURUSD"])
    out = sched._check_mtf_alignment({"M15": _trend_df(slope=1.0)}, "M15")
    assert out["biases"]["M15"] == "bullish"
    assert out["direction"] == "bullish"
    assert out["aligned"] is True


def test_mtf_alignment_bearish_and_mixed_neutral():
    sched = CandleScheduler(symbols=["EURUSD"])
    out = sched._check_mtf_alignment({"M15": _trend_df(slope=-1.0)}, "M15")
    assert out["biases"]["M15"] == "bearish"
    assert out["direction"] == "bearish"
    flat = _trend_df(slope=0.0, noise=0.0)
    out2 = sched._check_mtf_alignment({"M15": flat}, "M15")
    assert out2["biases"]["M15"] == "neutral"
    short = pd.DataFrame({"close": [1.0, 2.0]})
    out3 = sched._check_mtf_alignment({"M15": short}, "M15")
    assert out3["biases"] == {}


# ── close detection + probe_empty counting ──────────────────────────────

def test_check_all_closes_sync_detects_new_bar_no_false_positive_and_counts_empty():
    sched = CandleScheduler(symbols=["EURUSD"], timeframes=["M15"])
    broker = FakeBroker(bars={("EURUSD", 15): _rates(1_700_000_000.0)})
    sched._get_broker_mt5 = lambda: broker  # type: ignore[method-assign]
    sched._candle_states["EURUSD:M15"] = CandleState(
        symbol="EURUSD", timeframe="M15", last_close_time=0.0)
    # first probe seeds state, no close reported
    assert sched._check_all_closes_sync(["EURUSD"]) == []
    stats = sched._last_probe_stats
    assert stats == {"empty": 0, "total": 1}
    # same bar again → no false positive
    assert sched._check_all_closes_sync(["EURUSD"]) == []
    # new bar → one close detected, state advanced
    broker._bars[("EURUSD", 15)] = _rates(1_700_000_900.0)
    detected = sched._check_all_closes_sync(["EURUSD"])
    assert detected == [("EURUSD", "M15", 1_700_000_900.0)]
    assert sched._candle_states["EURUSD:M15"].last_close_time == 1_700_000_900.0
    # empty feed → probe_empty counting (the "probe 0/32" heartbeat stat)
    broker._bars.clear()
    assert sched._check_all_closes_sync(["EURUSD"]) == []
    assert sched._last_probe_stats == {"empty": 1, "total": 1}


# ── state persistence round-trip ────────────────────────────────────────

def test_save_state_roundtrip(monkeypatch):
    import shutil
    import tempfile
    from pathlib import Path

    workdir = Path(tempfile.mkdtemp(prefix="qna_sched_"))
    try:
        monkeypatch.chdir(workdir)
        sched = CandleScheduler(symbols=["EURUSD"], timeframes=["M15"])
        sched._results.append(CycleResult(
            symbol="EURUSD", timeframe="M15", timestamp="2026-01-01T00:00:00+00:00",
            signal="buy", confidence=0.75, traded=False, duration_ms=12.5))
        sched._save_state()
        state = json.loads((workdir / "data" / "candle_scheduler_state.json").read_text())
        assert state["total_events"] == 1
        assert state["events"][0]["signal"] == "buy"
        assert state["events"][0]["confidence"] == 0.75
        notif = json.loads((workdir / "data" / "notifications.json").read_text())
        assert len(notif["notifications"]) == 1
        assert "BUY" in notif["notifications"][0]["message"]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
