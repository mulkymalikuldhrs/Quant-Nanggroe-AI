"""Trading profile SL/TP computation tests."""
from __future__ import annotations

from quant_nanggroe.engine.risk.trading_profile import (
    compute_sl_tp,
    detect_profile,
)


class TestProfiles:
    def test_scalp_for_m15(self):
        p = detect_profile("M15")
        assert p.name == "scalp"
        assert p.sl_atr_mult == 1.0

    def test_day_for_h1(self):
            p = detect_profile("H1")
            assert p.name == "day"
            assert p.sl_atr_mult == 2.0
            assert p.rr_target == 2.5

    def test_swing_for_d1(self):
        p = detect_profile("D1")
        assert p.name == "swing"

    def test_unknown_defaults_to_day(self):
        p = detect_profile("garbage")
        assert p.name == "day"


class TestComputeSLTP:
    def test_buy_long_sl_tp(self):
        r = compute_sl_tp("buy", 2000.0, 10.0, "H1")
        # day profile: sl_atr=1.5 -> sl_dist=20; rr=2.5 -> tp_dist=50
        assert r["sl"] < 2000.0
        assert r["tp"] > 2000.0
        assert abs(r["sl"] - (2000.0 - 20.0)) < 0.01
        assert abs(r["tp"] - (2000.0 + 50.0)) < 0.01
        assert r["profile"] == "day"

    def test_sell_short_sl_tp(self):
        r = compute_sl_tp("sell", 2000.0, 10.0, "H1")
        assert r["sl"] > 2000.0
        assert r["tp"] < 2000.0

    def test_scalp_tighter_than_swing(self):
        scalp = compute_sl_tp("buy", 2000.0, 10.0, "M15")
        swing = compute_sl_tp("buy", 2000.0, 10.0, "D1")
        scalp_dist = abs(2000.0 - scalp["sl"])
        swing_dist = abs(swing["sl"] - 2000.0)
        assert scalp_dist < swing_dist

    def test_rr_override(self):
        r = compute_sl_tp("buy", 100.0, 5.0, "H1", rr_override=3.0)
        sl_dist = abs(100.0 - r["sl"])
        tp_dist = abs(r["tp"] - 100.0)
        assert abs(tp_dist / sl_dist - 3.0) < 0.01

    def test_zero_atr_fallback(self):
        r = compute_sl_tp("buy", 100.0, 0.0, "H1")
        # floor at 0.5% of entry
        assert abs(r["sl_distance"] - 0.5) < 0.01
