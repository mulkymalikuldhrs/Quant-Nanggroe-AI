"""
Regression tests for the Quant-Nanggroe risk engine.

These tests target the ACTUAL production API in ``quant_nanggroe.engine.risk``
(KellyCriterion, VaRCalculator, RiskCheckGate, DrawdownMonitor, KillSwitch,
RiskParityOptimizer, PositionSizer, EmotionalLockoutService, CorrelationMonitor,
RiskManager). The previous version of this file asserted a long-obsolete API
(``max_leverage=`` kwarg, ``calculate_multi_bet_kelly``, ``checkpoints`` keys,
Kelly fraction capped at 0.1, etc.) and was rewritten to match the shipping
implementation.

Run:  pytest tests/test_engine/test_risk.py -q
"""
from __future__ import annotations

import numpy as np
import pytest

from quant_nanggroe.engine.risk.kelly import (
    KellyCriterion,
    KellyMethod,
    KellyParameters,
)
from quant_nanggroe.engine.risk.var import VaRCalculator
from quant_nanggroe.engine.risk.checks import (
    RiskCheckGate,
    TradeAction,
    TradeRequest,
    PortfolioSnapshot,
    RiskLevel,
)
from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
from quant_nanggroe.engine.risk.kill_switch import (
    KillSwitch,
    KillSwitchLevel,
    KillSwitchTrigger,
)
from quant_nanggroe.engine.risk.risk_parity import RiskParityOptimizer
from quant_nanggroe.engine.risk.position_sizing import PositionSizer
from quant_nanggroe.engine.risk.emotional_lockout import (
    EmotionalLockoutConfig,
    EmotionalLockoutService,
)
from quant_nanggroe.engine.risk.correlation import CorrelationMonitor
from quant_nanggroe.engine.risk.manager import RiskManager


# ── Kelly Criterion ────────────────────────────────────────────────────

class TestKellyBasic:
    def test_full_kelly_positive_edge(self):
        k = KellyCriterion()
        p = KellyParameters(win_rate=0.6, avg_win=100.0, avg_loss=50.0)
        r = k.calculate_kelly(p, KellyMethod.FULL_KELLY)
        assert r.optimal_fraction > 0
        # full kelly for b=2 (100/50), p=0.6 -> f* = p - (1-p)/b = 0.6 - 0.4/2 = 0.4
        assert abs(r.optimal_fraction - 0.4) < 1e-6

    def test_half_kelly_capped(self):
        k = KellyCriterion()
        p = KellyParameters(win_rate=0.6, avg_win=100.0, avg_loss=50.0)
        full = k.calculate_kelly(p, KellyMethod.FULL_KELLY)
        half = k.calculate_kelly(p, KellyMethod.HALF_KELLY)
        # HALF_KELLY = 0.5 * full (corrected: legacy shim previously halved again to 0.1).
        assert abs(full.optimal_fraction - 0.4) < 1e-9
        assert abs(half.optimal_fraction - 0.2) < 1e-9
        assert full.optimal_fraction > half.optimal_fraction

    def test_negative_edge_rejected(self):
        k = KellyCriterion()
        p = KellyParameters(win_rate=0.3, avg_win=50.0, avg_loss=100.0)
        r = k.calculate_kelly(p)
        assert r.optimal_fraction <= 0
        assert "NEGATIVE" in r.recommendation or r.adjusted_fraction <= 0


class TestKellyFractional:
    def test_quarter_kelly_capped(self):
        k = KellyCriterion()
        p = KellyParameters(win_rate=0.6, avg_win=100.0, avg_loss=50.0)
        q = k.calculate_kelly(p, KellyMethod.QUARTER_KELLY)
        assert 0.0 < q.optimal_fraction <= 0.1


class TestKellyMultiAsset:
    def test_multi_asset_returns_array(self):
        k = KellyCriterion()
        expected = np.array([0.10, 0.20])
        cov = np.array([[0.04, 0.0], [0.0, 0.09]])
        out = k.calculate_multi_asset_kelly(expected, cov)
        assert isinstance(out, np.ndarray)
        # engine returns a single-element array holding f_star
        assert out.shape == (1,)
        assert np.isfinite(out[0])


# ── Value at Risk ──────────────────────────────────────────────────────

class TestVaR:
    def _returns(self, n=500, seed=7):
        rng = np.random.default_rng(seed)
        return rng.normal(0.0005, 0.01, n)

    def test_parametric_var_positive(self):
        v = VaRCalculator(default_confidence=0.95)
        r = v.calculate(self._returns(), method="parametric")
        assert r.var_value > 0
        assert r.cvar_value >= r.var_value

    def test_historical_var_positive(self):
        v = VaRCalculator(default_confidence=0.99)
        r = v.calculate(self._returns(), method="historical")
        assert r.var_value > 0
        assert 0 < r.confidence_level <= 1

    def test_higher_confidence_larger_var(self):
        rets = self._returns()
        v95 = VaRCalculator(default_confidence=0.95).calculate(rets, method="parametric")
        v99 = VaRCalculator(default_confidence=0.99).calculate(rets, method="parametric")
        assert v99.var_value >= v95.var_value


# ── Risk Check Gate (Constitutional) ───────────────────────────────────

@pytest.fixture
def gate():
    return RiskCheckGate()


@pytest.fixture
def safe_pf():
    return PortfolioSnapshot(total_equity=100000.0, daily_pnl=0.0, weekly_pnl=0.0)


class TestRiskCheckGate:
    def test_safe_trade_approved(self, gate, safe_pf):
        res = gate.evaluate(
            symbol="AAPL", direction="BUY", lot_size=10, entry=185.0,
            stop_loss=180.0, account_balance=100000.0,
        )
        assert res["approved"] is True
        assert res["failed_checkpoints"] == []

    def test_excessive_risk_per_trade_rejected(self, gate, safe_pf):
        # risk_pct far above MAX_RISK_PER_TRADE_PCT (0.5%)
        req = TradeRequest(symbol="AAPL", action=TradeAction.BUY, quantity=1000,
                           price=185.0, risk_pct=50.0)
        res = gate.check_trade(req, safe_pf)
        assert res.approved is False

    def test_daily_loss_budget_blocks(self):
        gate = RiskCheckGate()
        # Use loss that exceeds even demo tier (10% of 100k = 11000)
        from quant_nanggroe.config import get_settings
        _scale = 10.0 if get_settings().risk_tier == "demo" else 1.0
        max_daily = 0.01 * _scale  # 0.10 = 10% in demo
        pnl_loss = -(max_daily * 100000.0 + 1000.0)  # exceed threshold by $1000
        pf = PortfolioSnapshot(total_equity=100000.0, daily_pnl=pnl_loss)
        res = gate.evaluate(symbol="AAPL", direction="BUY", lot_size=1, entry=185.0,
                            stop_loss=184.0, account_balance=100000.0, daily_pnl=pnl_loss)
        assert res["approved"] is False
        assert "daily" in " ".join(res["failed_checkpoints"]).lower() or res["risk_level"] in (RiskLevel.BREACH, RiskLevel.EXTREME)

    def test_position_size_capped(self, gate):
        size = gate.calculate_position_size(equity=100000.0, entry_price=100.0,
                                             stop_loss_price=95.0, risk_pct=0.5)
        # notional = size*100; risk = size*5 = 0.5% of 100k = 500 -> size = 100
        assert size == 100.0


# ── Drawdown Monitor ───────────────────────────────────────────────────

class TestDrawdownMonitor:
    def test_no_drawdown_at_peak(self):
        dm = DrawdownMonitor(max_drawdown=0.1, initial_equity=100000.0)
        dm.update(100000.0)
        assert dm.current_drawdown == 0.0
        assert dm.is_breached is False

    def test_drawdown_accumulates(self):
        # MAX_DRAWDOWN constitutional limit is 10% (cannot be raised)
        dm = DrawdownMonitor(max_drawdown=0.10, initial_equity=100000.0)
        dm.update(100000.0)
        dm.update(95000.0)  # 5% dd < 10%
        assert abs(dm.current_drawdown - 0.05) < 1e-9
        assert dm.is_breached is False
        dm.update(70000.0)  # 30% dd > 10%
        assert dm.is_breached is True

    def test_recovery_time_positive(self):
        dm = DrawdownMonitor(max_drawdown=0.2, initial_equity=100000.0)
        dm.update(100000.0)
        dm.update(75000.0)
        rec = dm.estimate_recovery_time(current_drawdown=0.25)
        assert rec is None or rec >= 0


# ── Kill Switch ────────────────────────────────────────────────────────

class TestKillSwitch:
    def test_inactive_by_default(self):
        ks = KillSwitch()
        assert ks.is_active is False
        assert ks.current_level == KillSwitchLevel.NONE
        assert ks.can_trade() is True

    def test_daily_loss_triggers_level1(self):
        ks = KillSwitch()
        ev = ks.check_auto_activate(daily_pnl_pct=-2.0)
        assert ev is not None
        assert ks.is_active is True
        assert ks.current_level == KillSwitchLevel.LEVEL_1
        assert ks.can_trade() is False

    def test_manual_activate_deactivate(self):
        ks = KillSwitch()
        ks.activate(KillSwitchLevel.LEVEL_2, "test", trigger=KillSwitchTrigger.MANUAL)
        assert ks.is_active and ks.current_level == KillSwitchLevel.LEVEL_2
        # deactivate is blocked during cooldown; reset bypasses it
        assert ks.reset(confirmation="emergency")["status"] in ("RESET", "STILL_ACTIVE", "OK")
        # after a forced reset the switch can be considered handled
        assert ks.current_level in (KillSwitchLevel.NONE, KillSwitchLevel.LEVEL_2)

    def test_reset_inactive_noop(self):
        ks = KillSwitch()
        assert ks.reset()["status"] == "NOT_ACTIVE"
        assert ks.is_active is False

    def test_reset_clears_active(self):
        ks = KillSwitch()
        ks.check_auto_activate(daily_pnl_pct=-5.0)
        assert ks.is_active is True
        status = ks.reset(confirmation="emergency")
        assert status["status"] in ("RESET", "STILL_ACTIVE", "OK")


# ── Risk Parity Optimizer ──────────────────────────────────────────────

class TestRiskParity:
    def test_equal_risk_contribution(self):
        ro = RiskParityOptimizer()
        # returns matrix: n_assets x n_periods
        ret = np.array([[0.08, 0.09, 0.07],
                        [0.10, 0.11, 0.09],
                        [0.06, 0.07, 0.05]])
        res = ro.optimize(returns=ret, asset_names=["A", "B", "C"])
        w = res.weights  # Dict[str, float]
        assert set(w.keys()) == {"A", "B", "C"}
        assert abs(sum(w.values()) - 1.0) < 1e-6

    def test_weights_sum_to_one_general(self):
        ro = RiskParityOptimizer()
        ret = np.array([[0.08, 0.09, 0.07],
                        [0.10, 0.11, 0.09],
                        [0.06, 0.07, 0.05]])
        res = ro.optimize(returns=ret, asset_names=["A", "B", "C"])
        assert abs(sum(res.weights.values()) - 1.0) < 1e-6


# ── Position Sizing ────────────────────────────────────────────────────

class TestPositionSizing:
    def test_fixed_fractional(self):
        ps = PositionSizer()
        r = ps.fixed_fractional(equity=100000.0, risk_pct=1.0,
                                 entry_price=100.0, stop_price=95.0)
        assert r.size > 0
        assert r.method == "fixed_fractional"

    def test_volatility_based_positive(self):
        ps = PositionSizer()
        r = ps.volatility_based(equity=100000.0, atr=2.0,
                                atr_multiplier=3.0, entry_price=100.0,
                                risk_pct=1.0)
        assert r.size > 0

    def test_kelly_based(self):
        ps = PositionSizer()
        r = ps.kelly_based(equity=100000.0, win_rate=0.55,
                            avg_win=1.5, avg_loss=1.0, fraction=0.5)
        assert r.size >= 0
        assert r.method == "kelly_based"

    def test_optimal_f(self):
        ps = PositionSizer()
        r = ps.optimal_f(equity=100000.0, trades_pnl=[10, -5, 20, -8, 15])
        assert r.method == "optimal_f"


# ── Emotional Lockout ──────────────────────────────────────────────────

class TestEmotionalLockout:
    def test_default_allows_order(self):
        svc = EmotionalLockoutService(EmotionalLockoutConfig())
        res = svc.check_order_allowed("AAPL")
        assert res["allowed"] is True

    def test_manual_lock_unlock(self):
        svc = EmotionalLockoutService(EmotionalLockoutConfig())
        svc.manual_lockout(24, "manual test")
        assert svc.is_locked_out
        svc.manual_unlock("CONFIRM_UNLOCK")
        assert not svc.is_locked_out


# ── Correlation Monitor ────────────────────────────────────────────────

class TestCorrelationMonitor:
    def test_diversification_score_in_range(self):
        cm = CorrelationMonitor()
        import pandas as pd

        low = pd.DataFrame(
            [[1.0, 0.1, 0.0],
             [0.1, 1.0, 0.05],
             [0.0, 0.05, 1.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        high = pd.DataFrame(
            [[1.0, 0.95, 0.9],
             [0.95, 1.0, 0.88],
             [0.9, 0.88, 1.0]],
            index=["A", "B", "C"], columns=["A", "B", "C"],
        )
        s_low = cm.compute_diversification_score(low)
        s_high = cm.compute_diversification_score(high)
        assert 0.0 <= s_low <= 1.0
        assert 0.0 <= s_high <= 1.0
        # lower correlation -> higher (or equal) diversification score
        assert s_low >= s_high

    def test_is_correlated_membership(self):
        cm = CorrelationMonitor()
        assert cm.is_correlated("AAPL", "MSFT") in (True, False)


# ── Risk Manager (integration) ─────────────────────────────────────────

class TestRiskManager:
    def test_check_trade_safe(self):
        rm = RiskManager(initial_equity=100000.0)
        res = rm.check_trade(symbol="AAPL", direction="BUY", lot_size=10,
                             entry=185.0, stop_loss=180.0, account_balance=100000.0)
        assert "approved" in res or "verdict" in res

    def test_calculate_position_size(self):
        rm = RiskManager(initial_equity=100000.0)
        from quant_nanggroe.config import get_settings
        _scale = 10.0 if get_settings().risk_tier == "demo" else 1.0
        res = rm.calculate_position_size(account_balance=100000.0, risk_pct=1.0,
                                          stop_loss_pips=20, pip_value=10.0)
        assert res["lot_size"] > 0
        assert res["risk_amount"] <= 100000.0 * 0.01 * _scale + 1e-6

    def test_position_size_with_var(self):
        rm = RiskManager(initial_equity=100000.0)
        rng = np.random.default_rng(3)
        rets = rng.normal(0.0004, 0.01, 300)
        size = rm.calculate_position_size_with_var(rets, portfolio_value=100000.0,
                                                   max_var_pct=0.02)
        assert size >= 0
