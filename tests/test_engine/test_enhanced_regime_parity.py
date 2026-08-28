"""Enhanced Regime + Risk Parity Native tests."""
from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.portfolio.risk_parity_native import (
    erc_weights,
    hrp_weights,
)
from quant_nanggroe.engine.regime.enhanced_regime import (
    RegimeResult,
    detect_enhanced_regime,
)


def _trending_df(n=300, direction=1):
    rng = np.random.default_rng(42)
    drift = 0.3 * direction
    close = 100 + np.cumsum(drift + rng.normal(0, 1, n))
    high = close + np.abs(rng.normal(0, 0.5, n))
    low = close - np.abs(rng.normal(0, 0.5, n))
    open_ = close + rng.normal(0, 0.2, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close},
        index=pd.date_range("2025-01-01", periods=n, freq="h"),
    )


class TestEnhancedRegime:
    def test_returns_valid_result(self):
        df = _trending_df()
        r = detect_enhanced_regime(df)
        assert isinstance(r, RegimeResult)
        assert r.regime in ("bull_trend", "bear_trend", "ranging", "crisis")
        assert 0 <= r.confidence <= 1

    def test_uptrend_detected(self):
        df = _trending_df(300, direction=1)  # strong uptrend
        r = detect_enhanced_regime(df)
        # Should detect trend (bull or at least not bear in a clear uptrend)
        assert r.scores.get("is_trending") == 1 or r.scores.get("hmm_direction", 0) > 0

    def test_short_data_defaults_to_ranging(self):
        df = _trending_df(30)
        r = detect_enhanced_regime(df)
        assert r.regime == "ranging"

    def test_scores_present(self):
        df = _trending_df()
        r = detect_enhanced_regime(df)
        assert "adx" in r.scores
        assert "volatility" in r.scores


class TestRiskParity:
    def test_hrp_weights_sum_to_one(self):
        rets = {
            "strat_a": list(np.random.default_rng(1).normal(0.001, 0.02, 50)),
            "strat_b": list(np.random.default_rng(2).normal(0.001, 0.03, 50)),
            "strat_c": list(np.random.default_rng(3).normal(0.001, 0.01, 50)),
        }
        w = hrp_weights(rets)
        assert abs(sum(w.values()) - 1.0) < 0.01
        assert all(v > 0 for v in w.values())

    def test_erc_lower_vol_gets_more_weight(self):
        vols = {"low_vol": 0.05, "high_vol": 0.30}
        w = erc_weights(vols)
        assert w["low_vol"] > w["high_vol"]

    def test_single_strategy_gets_all_weight(self):
        w = hrp_weights({"only_one": [0.01, 0.02, 0.03]})
        assert abs(w["only_one"] - 1.0) < 0.01

    def test_insufficient_data_fallback(self):
        w = hrp_weights({
            "a": [0.01],
            "b": [0.02],
            "c": [0.03],
        })
        # fallback: equal weight
        assert all(abs(v - 1/3) < 0.01 for v in w.values())
