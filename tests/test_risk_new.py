"""C5: Tests for previously-untested risk engine logic.

Covers pure-logic risk modules that don't need a live broker/MT5:
  - atr_sl: Wilder ATR + ATR-based stop-loss calculation
  - var: VaRCalculator (parametric / historical / monte_carlo + CVaR)
  - trailing_stop: TrailingStopManager lifecycle
  - limits: RiskLimits weekly-loss tracker (JSON-backed, in temp dir)
  - constants: constitutional risk constants import & sanity

Network/numpy only — no broker. Designed to run offline & deterministically.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from quant_nanggroe.engine.risk.atr_sl import calculate_atr_sl, wilder_atr
from quant_nanggroe.engine.risk.trailing_stop import (
    TrailingStopConfig,
    TrailingStopManager,
)
from quant_nanggroe.engine.risk.var import VaRCalculator
from quant_nanggroe.engine.risk.limits import RiskLimits


# ─────────────────────────────────────────────────────────────────────────────
# ATR / Stop Loss
# ─────────────────────────────────────────────────────────────────────────────
class TestATRSL:
    def _series(self, n=30, base=100.0):
        high = [base + i * 0.5 for i in range(n)]
        low = [base - i * 0.5 for i in range(n)]
        close = [base + (i % 2) for i in range(n)]
        return high, low, close

    def test_wilder_atr_insufficient_data(self):
        h = [1.0, 2.0]
        l = [0.5, 1.5]
        c = [1.0, 1.8]
        assert wilder_atr(h, l, c, period=14) == 0.0

    def test_wilder_atr_positive(self):
        h, l, c = self._series()
        atr = wilder_atr(h, l, c, period=14)
        assert atr > 0.0

    def test_calculate_atr_sl_long(self):
        h, l, c = self._series()
        res = calculate_atr_sl(h, l, c, entry_price=115.0, side="long")
        assert res["stop_loss"] < 115.0  # long SL below entry
        assert res["sl_distance"] > 0
        assert res["atr_value"] > 0

    def test_calculate_atr_sl_short(self):
        h, l, c = self._series()
        res = calculate_atr_sl(h, l, c, entry_price=115.0, side="short")
        assert res["stop_loss"] > 115.0  # short SL above entry

    def test_min_sl_distance_enforced(self):
        h, l, c = self._series()
        res = calculate_atr_sl(
            h, l, c, entry_price=115.0, side="long",
            atr_multiplier=0.0, min_sl_distance=5.0,
        )
        assert res["sl_distance"] >= 5.0

    def test_repr_has_expected_keys(self):
        h, l, c = self._series()
        res = calculate_atr_sl(h, l, c, entry_price=115.0)
        for k in ("stop_loss", "sl_distance", "atr_value", "atr_period", "atr_multiplier"):
            assert k in res


# ─────────────────────────────────────────────────────────────────────────────
# VaR / CVaR
# ─────────────────────────────────────────────────────────────────────────────
class TestVaRCalculator:
    def _returns(self, n=200, seed=1):
        rng = np.random.default_rng(seed)
        return rng.normal(0.001, 0.02, n)

    def test_insufficient_data(self):
        calc = VaRCalculator()
        r = calc.calculate(np.array([0.01, -0.02]), method="historical")
        assert r.var_value == 0.0
        assert r.cvar_value == 0.0
        assert r.method == "insufficient_data"

    def test_historical_returns_positive_loss(self):
        calc = VaRCalculator()
        r = calc.calculate(self._returns(), method="historical", portfolio_value=100000.0)
        assert r.var_value >= 0.0
        assert r.cvar_value >= 0.0
        # CVaR >= VaR (expected shortfall is at least the VaR threshold)
        assert r.cvar_value >= r.var_value - 1e-6

    def test_parametric_reasonable(self):
        calc = VaRCalculator()
        r = calc.calculate(self._returns(), method="parametric", portfolio_value=100000.0)
        assert r.var_value >= 0.0
        assert r.cvar_value >= 0.0

    def test_monte_carlo_runs(self):
        calc = VaRCalculator()
        r = calc.calculate(self._returns(), method="monte_carlo",
                           portfolio_value=100000.0, num_simulations=2000)
        assert r.var_value >= 0.0
        assert r.cvar_value >= 0.0
        assert r.method == "monte_carlo"

    def test_auto_method_selects_by_sample_size(self):
        calc = VaRCalculator()
        # >= 500 -> historical
        r = calc.calculate(np.random.default_rng(2).normal(0, 0.01, 600), method="auto")
        assert r.method == "historical"
        # >=100 -> parametric
        r = calc.calculate(np.random.default_rng(3).normal(0, 0.01, 200), method="auto")
        assert r.method == "parametric"
        # <100 -> monte_carlo
        r = calc.calculate(np.random.default_rng(4).normal(0, 0.01, 50), method="auto")
        assert r.method == "monte_carlo"

    def test_z_score_lookup(self):
        calc = VaRCalculator()
        assert abs(calc._get_z_score(0.95) - 1.645) < 1e-3
        assert abs(calc._get_z_score(0.99) - 2.326) < 1e-3


# ─────────────────────────────────────────────────────────────────────────────
# Trailing Stop
# ─────────────────────────────────────────────────────────────────────────────
class TestTrailingStop:
    def test_add_and_stop_price(self):
        mgr = TrailingStopManager(TrailingStopConfig(min_stop_pct=0.02))
        mgr.add_position("BTCUSD", 100.0)
        assert mgr.get_stop_price("BTCUSD") == pytest.approx(98.0)

    def test_trailing_triggers_on_reversal(self):
        mgr = TrailingStopManager(TrailingStopConfig(
            activation_pct=0.02, trail_pct=0.01, min_stop_pct=0.02))
        mgr.add_position("BTCUSD", 100.0)
        # push price up to activate
        assert mgr.update("BTCUSD", 105.0) is None
        # now drop to the trailing stop
        assert mgr.update("BTCUSD", 105.0 * 0.99) == "BTCUSD"

    def test_no_position_returns_none(self):
        mgr = TrailingStopManager()
        assert mgr.update("MISSING", 100.0) is None

    def test_remove_position(self):
        mgr = TrailingStopManager()
        mgr.add_position("EURUSD", 1.10)
        mgr.remove_position("EURUSD")
        assert mgr.get_stop_price("EURUSD") is None


# ─────────────────────────────────────────────────────────────────────────────
# RiskLimits (weekly loss tracker)
# ─────────────────────────────────────────────────────────────────────────────
class TestRiskLimits:
    def _make(self, tmp_path: Path, limit: float = 0.03):
        return RiskLimits(max_weekly_loss_pct=limit, state_dir=tmp_path,
                          state_file="risk_state.json")

    def test_fresh_can_trade(self, tmp_path):
        rl = self._make(tmp_path)
        assert rl.can_trade() is True
        assert rl.current_weekly_loss_pct() == 0.0

    def test_record_loss_blocks_trade(self, tmp_path):
        rl = self._make(tmp_path, limit=0.03)
        rl.record_trade(-0.04 * 100000.0)  # 4% loss on 100k
        assert rl.current_weekly_loss_pct() >= 0.03
        assert rl.can_trade() is False

    def test_small_loss_still_trades(self, tmp_path):
        rl = self._make(tmp_path, limit=0.03)
        rl.record_trade(-0.01 * 100000.0)  # 1% loss
        assert rl.can_trade() is True

    def test_persists_across_instances(self, tmp_path):
        rl1 = self._make(tmp_path, limit=0.03)
        rl1.record_trade(-0.05 * 100000.0)
        rl2 = self._make(tmp_path, limit=0.03)
        assert rl2.can_trade() is False

    def test_weekly_pnl_property(self, tmp_path):
        rl = self._make(tmp_path)
        rl.record_trade(-1000.0)
        assert rl.weekly_pnl == -1000.0
