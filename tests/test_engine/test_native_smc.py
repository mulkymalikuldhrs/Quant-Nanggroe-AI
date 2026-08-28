"""Native SMC Engine tests — Order Block, FVG, BOS/CHoCH, Liquidity Sweep."""
from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.smc.native_smc import (
    SMCEngine,
    bos_choch,
    fair_value_gaps,
    liquidity_sweep,
    order_blocks,
    swing_highs_lows,
)


def make_df(n=200, seed=42):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.5, n))
    high = close + np.abs(rng.normal(0, 0.8, n))
    low = close - np.abs(rng.normal(0, 0.8, n))
    open_ = close + rng.normal(0, 0.3, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close},
        index=pd.date_range("2025-01-01", periods=n, freq="h"),
    )


class TestSwingDetection:
    def test_finds_swing_highs_and_lows(self):
        df = make_df()
        result = swing_highs_lows(df, swing_length=10)
        assert "high_swing" in result.columns
        assert result["high_swing"].sum() > 0
        assert result["low_swing"].sum() > 0


class TestFVG:
    def test_bullish_fvg_detection(self):
        # Construct explicit bullish FVG: candle[i].low > candle[i-2].high
        data = {
            "open": [100, 102, 106],
            "high": [101, 103, 110],   # gap between high[0]=101 and low[2]=106
            "low": [99, 101.5, 106],   # low[2]=106 > high[0]=101 → bullish FVG
            "close": [101.5, 105, 109],
        }
        df = pd.DataFrame(data)
        result = fair_value_gaps(df)
        assert result["fvg_bullish"].iloc[2] == True  # noqa: E712

    def test_bearish_fvg_detection(self):
        data = {
            "open": [106, 103, 96],
            "high": [107, 104, 98],    # high[2]=98 < low[0]=105? No.
            "low": [105, 101, 94],     # Let me fix: need high[2] < low[0]
            "close": [104, 97, 95],
        }
        # Actually for bearish FVG: highs[i] < lows[i-2]
        # i.e. high of current < low of 2 candles ago (price gapped down)
        data = {
            "open": [100, 96, 90],
            "high": [101, 97, 92],    # high[2]=92 < low[0]=99 → bearish FVG
            "low": [99, 95, 88],
            "close": [96, 93, 91],
        }
        df = pd.DataFrame(data)
        result = fair_value_gaps(df)
        assert result["fvg_bearish"].iloc[2] == True  # noqa: E712


class TestBOSCHoCH:
    def test_detects_breaks(self):
        df = make_df(300, seed=7)
        result = bos_choch(df, swing_length=10)
        total_bos = result["bos_bullish"].sum() + result["bos_bearish"].sum()
        total_choch = result["choch_bullish"].sum() + result["choch_bearish"].sum()
        assert total_bos + total_choch > 0, "should detect at least one break"


class TestOrderBlocks:
    def test_order_blocks_detected(self):
        df = make_df(300, seed=7)
        result = order_blocks(df, swing_length=10)
        assert "ob_bullish" in result.columns
        assert "ob_bull_top" in result.columns


class TestLiquiditySweep:
    def test_sweep_detected(self):
        df = make_df(300, seed=7)
        result = liquidity_sweep(df, swing_length=10)
        assert "sweep_bullish" in result.columns


class TestSMCEngine:
    def test_analyze_returns_structure(self):
        engine = SMCEngine(swing_length=10)
        df = make_df(300)
        r = engine.analyze(df)
        assert "direction" in r
        assert "confidence" in r
        assert r["direction"] in ("buy", "sell", "hold")
        assert 0 <= r["confidence"] <= 1
        assert "signals" in r

    def test_analyze_missing_columns(self):
        engine = SMCEngine()
        bad_df = pd.DataFrame({"close": [1, 2, 3]})
        r = engine.analyze(bad_df)
        assert "error" in r

    def test_composite_score(self):
        engine = SMCEngine(swing_length=10)
        df = make_df(500, seed=99)
        r = engine.analyze(df)
        assert "bull_score" in r
        assert "bear_score" in r
