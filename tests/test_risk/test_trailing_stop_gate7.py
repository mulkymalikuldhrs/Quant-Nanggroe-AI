"""GATE-7 regression: breakeven ratchet + ATR trailing + monotonic stops."""
from __future__ import annotations

from quant_nanggroe.engine.risk.trailing_stop import (
    TrailingStopConfig,
    TrailingStopManager,
)


def test_breakeven_moves_stop_to_entry():
    cfg = TrailingStopConfig(
        activation_pct=0.05, trail_pct=0.01,
        breakeven_enabled=True, breakeven_trigger_pct=0.01,
        breakeven_buffer_pct=0.0005, min_stop_pct=0.02,
    )
    mgr = TrailingStopManager(cfg)
    mgr.add_position("BTCUSDT", 100.0)
    # price rises 1.5% -> breakeven should move stop to ~entry
    fired = mgr.update("BTCUSDT", 101.5)
    assert fired is None
    stop = mgr.get_stop_price("BTCUSDT")
    assert stop is not None and stop >= 100.0


def test_breakeven_protects_against_retracement():
    cfg = TrailingStopConfig(activation_pct=0.05, trail_pct=0.01,
                             breakeven_trigger_pct=0.01)
    mgr = TrailingStopManager(cfg)
    mgr.add_position("XAUUSD", 2000.0)
    mgr.update("XAUUSD", 2021.0)   # +1% -> BE moved to ~2001
    fired = mgr.update("XAUUSD", 2000.9)   # retracement below BE stop
    assert fired == "XAUUSD"


def test_atr_trail_used_when_configured_and_supplied():
    cfg = TrailingStopConfig(use_atr_multiple=True, atr_multiple=2.0,
                             activation_pct=0.01, trail_pct=0.01)
    mgr = TrailingStopManager(cfg)
    mgr.add_position("EURUSD", 1.1000)
    mgr.update("EURUSD", 1.1100, atr=0.0020)  # +0.9%? >= activation 1%? no:
    # 1.11/1.10 - 1 = 0.00909 < 0.01 -> not active yet; push further
    mgr.update("EURUSD", 1.1150, atr=0.0020)  # +1.36% -> active
    stop = mgr.get_stop_price("EURUSD")
    expected = 1.1150 - 2.0 * 0.0020
    assert abs(stop - expected) < 1e-6


def test_stop_never_loosens():
    cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.01)
    mgr = TrailingStopManager(cfg)
    mgr.add_position("SOLUSDT", 100.0)
    mgr.update("SOLUSDT", 105.0)          # active, stop ~103.95
    high_water = mgr.get_stop_price("SOLUSDT")
    # mild dip that does NOT touch the trail: stop must hold its level
    assert mgr.update("SOLUSDT", 104.2) is None
    assert mgr.get_stop_price("SOLUSDT") >= high_water


def test_fires_on_trail_touch():
    cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.01)
    mgr = TrailingStopManager(cfg)
    mgr.add_position("BTCUSDT", 100.0)
    assert mgr.update("BTCUSDT", 102.0) is None      # armed
    assert mgr.get_stop_price("BTCUSDT") > 100.0     # trailed up
    assert mgr.update("BTCUSDT", 100.8) == "BTCUSDT" # touched trail
