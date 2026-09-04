"""N4/N5/N6/N8 pin tests — governance hot-reload + default-derivation fixes.

Fail-closed, default behavior unchanged in every case.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("PERSISTENCE_BACKEND", "memory")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_nanggroe.engine.execution.base import Order, OrderSide, OrderType


@pytest.fixture
def isolated_config(monkeypatch):
    """Redirect config/risk_config.json to a tmp file (same pattern as
    test_per_symbol_overrides.py — NOT pytest tmp_path, which can be
    access-denied when created by an elevated process)."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="qna-gov-refresh-"))
    cfg = tmp_dir / "risk_config.json"
    import quant_nanggroe.api.routes.risk_config as rc_mod

    monkeypatch.setattr(rc_mod, "_CONFIG_PATH", cfg)
    yield cfg
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _tiny_order() -> Order:
    # Dust notional (0.001) so the per-trade check never interferes with
    # the daily/weekly/drawdown assertions below.
    return Order(
        id="gov-refresh-1",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.001,
        price=1.0,
    )


# ── N4: GovernanceVetoGuard refreshes limits from live constants ──────────

class TestGovernanceVetoLiveRefresh:
    def test_stale_constructed_guard_picks_up_reloaded_constant(self, monkeypatch):
        import quant_nanggroe.engine.risk.constants as c_mod
        from quant_nanggroe.engine.risk.veto_guard import GovernanceVetoGuard

        guard = GovernanceVetoGuard()  # binds construction-time defaults
        guard.update_pnl(-0.007, 0.0)  # inside the 1% default → allowed
        assert guard.check(_tiny_order()).allowed is True

        # UI hot-reload tightens the daily limit to 0.5% AFTER construction.
        monkeypatch.setattr(c_mod, "MAX_DAILY_LOSS", 0.005)
        result = guard.check(_tiny_order())
        assert result.allowed is False
        assert "Daily loss" in result.reason

    def test_fallback_on_broken_config_keeps_construction_values(self, monkeypatch):
        import quant_nanggroe.engine.risk.constants as c_mod
        from quant_nanggroe.engine.risk.veto_guard import GovernanceVetoGuard

        guard = GovernanceVetoGuard()
        before = guard._max_daily_loss
        # Corrupt live constant (e.g. half-written reload) → float() raises.
        monkeypatch.setattr(c_mod, "MAX_DAILY_LOSS", "broken")
        guard.update_pnl(-0.02, 0.0)  # beyond the 1% construction default
        result = guard.check(_tiny_order())
        assert result.allowed is False  # still enforced, not crashed/open
        assert guard._max_daily_loss == before


# ── N5: auto_max_drawdown_pct derived from constitutional MAX_DRAWDOWN_PCT ──

class TestKillSwitchDrawdownDefault:
    def test_default_derived_from_constitutional_max_drawdown(self):
        import quant_nanggroe.engine.risk.constants as c_mod
        from quant_nanggroe.engine.risk.kill_switch import KillSwitchConfig

        cfg = KillSwitchConfig()
        assert cfg.auto_max_drawdown_pct == pytest.approx(
            0.8 * float(c_mod.MAX_DRAWDOWN_PCT)
        )

    def test_explicit_value_preserved_for_existing_instances(self):
        from quant_nanggroe.engine.risk.kill_switch import KillSwitchConfig

        cfg = KillSwitchConfig(auto_max_drawdown_pct=0.05)
        assert cfg.auto_max_drawdown_pct == pytest.approx(0.05)


# ── N6: minRiskReward/maxCorrelatedPositions removed from editable set ─────

class TestNonEditableQualityGates:
    def test_file_values_fall_back_to_defaults(self, isolated_config):
        from quant_nanggroe.api.routes import risk_config as rc

        isolated_config.write_text(json.dumps({
            "version": 1,
            "minRiskReward": 5.0,
            "maxCorrelatedPositions": 1,
        }), encoding="utf-8")
        assert rc._load()["minRiskReward"] == 2.0
        assert rc._load()["maxCorrelatedPositions"] == 3
        eff = rc.get_effective_config()
        assert eff["minRiskReward"] == 2.0
        assert eff["maxCorrelatedPositions"] == 3

    def test_per_symbol_override_silently_inert(self, isolated_config):
        from quant_nanggroe.api.routes import risk_config as rc

        isolated_config.write_text(json.dumps({
            "version": 1,
            "perSymbol": {"EURUSD": {"minRiskReward": 5.0}},
        }), encoding="utf-8")
        assert rc.get_effective_config(symbol="EURUSD")["minRiskReward"] == 2.0

    def test_put_rejected_loudly(self, isolated_config):
        from fastapi import HTTPException
        from quant_nanggroe.api.routes import risk_config as rc

        with pytest.raises(HTTPException) as exc:
            rc.update_risk_config({"minRiskReward": 5.0})
        assert exc.value.status_code == 400
        with pytest.raises(HTTPException) as exc2:
            rc.update_risk_config(
                {"perSymbol": {"EURUSD": {"maxCorrelatedPositions": 1}}}
            )
        assert exc2.value.status_code == 400


# ── N8: check_cost_affordable is accounting-only ───────────────────────────

class TestCostAffordableAccountingOnly:
    def _manager(self, monkeypatch):
        monkeypatch.setenv("PERSISTENCE_BACKEND", "memory")
        from quant_nanggroe.engine.risk.manager import RiskManager

        return RiskManager(initial_equity=100_000.0)

    def test_pure_no_mutation_no_halt_coupling(self, monkeypatch):
        rm = self._manager(monkeypatch)
        budget_before = rm.trading_budget
        assert rm.check_cost_affordable(budget_before - 1.0) is True
        assert rm.check_cost_affordable(budget_before + 1.0) is False
        assert rm.trading_budget == budget_before  # no state mutation
        assert rm.kill_switch.is_active is False  # no halt coupling

    def test_no_callers_in_execution_path(self):
        import pathlib

        mgr = pathlib.Path(ROOT) / "quant_nanggroe" / "engine" / "execution" / "manager.py"
        assert "check_cost_affordable" not in mgr.read_text(encoding="utf-8")
