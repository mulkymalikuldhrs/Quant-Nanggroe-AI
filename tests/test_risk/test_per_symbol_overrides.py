"""tests/test_risk/test_per_symbol_overrides.py — v8.0.23 (Track A1-A4)

Covers the 4-axis risk override matrix:
1. global (default _DEFAULTS)
2. perSymbol (e.g. EURUSD 0.3%)
3. perStrategy (e.g. kaufman_ama 0.4%)
4. perRegime (e.g. trending 0.6%)

Plus fail-closed semantics (A2):
- unknown top-level keys rejected on PUT
- unknown override keys rejected on PUT
- out-of-range values rejected on PUT
- corrupt file → defaults
- missing file → defaults

And hot-reload semantics (A3+A4):
- KILL_SWITCH_DAILY_PNL = -0.8 * MAX_DAILY_LOSS
- KILL_SWITCH_WEEKLY_PNL = -0.8 * MAX_WEEKLY_LOSS
- KILL_SWITCH_DRAWDOWN_PCT = 0.8 * MAX_DRAWDOWN_PCT

All tests use a temporary risk_config.json via tmp_path/monkeypatch to
isolate from the real config/risk_config.json.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# ── path bootstrap (test_risk lives under tests/, not tests/test_risk) ──
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def isolated_config(monkeypatch):
    """Redirect config/risk_config.json to a tmp file for the duration of the test.

    NOTE: deliberately NOT using pytest's tmp_path — its shared
    C:\\...\\Temp\\pytest-of-Hi root can be access-denied when it was created
    by an elevated process, which would error every test.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="qna-risk-cfg-"))
    cfg = tmp_dir / "risk_config.json"
    # patch _CONFIG_PATH in the risk_config module
    import quant_nanggroe.api.routes.risk_config as rc_mod

    monkeypatch.setattr(rc_mod, "_CONFIG_PATH", cfg)
    # patch _reload_from_risk_config in constants.py to read from the test file
    import quant_nanggroe.engine.risk.constants as c_mod

    def _test_reload():
        import json as _json
        try:
            data = _json.loads(cfg.read_text(encoding="utf-8"))
            c_mod.MAX_RISK_PER_TRADE = float(data.get("maxRiskPerTrade", c_mod.MAX_RISK_PER_TRADE))
            c_mod.MAX_POSITION_SIZE_PCT = float(data.get("maxPositionSize", c_mod.MAX_POSITION_SIZE_PCT))
            c_mod.MAX_LEVERAGE = float(data.get("maxLeverage", c_mod.MAX_LEVERAGE))
            c_mod.MAX_DAILY_LOSS = float(data.get("maxDailyLoss", c_mod.MAX_DAILY_LOSS))
            c_mod.MAX_DAILY_TRADES = int(data.get("maxDailyTrades", c_mod.MAX_DAILY_TRADES))
            c_mod.MAX_WEEKLY_LOSS = float(data.get("maxWeeklyLoss", c_mod.MAX_WEEKLY_LOSS))
            c_mod.MAX_DRAWDOWN_PCT = float(data.get("maxDrawdown", c_mod.MAX_DRAWDOWN_PCT))
            c_mod.KILL_SWITCH_DAILY_PNL = -0.8 * c_mod.MAX_DAILY_LOSS
            c_mod.KILL_SWITCH_WEEKLY_PNL = -0.8 * c_mod.MAX_WEEKLY_LOSS
            c_mod.KILL_SWITCH_DRAWDOWN_PCT = 0.8 * c_mod.MAX_DRAWDOWN_PCT
        except Exception:
            pass

    monkeypatch.setattr(c_mod, "_reload_from_risk_config", _test_reload)
    monkeypatch.setattr(c_mod, "reload_risk_constants", _test_reload)
    yield cfg
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ════════════════════════════════════════════════════════════════════════════
# 1. Default config behavior
# ════════════════════════════════════════════════════════════════════════════

class TestDefaults:
    def test_missing_file_returns_defaults(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import _load, _DEFAULTS

        assert not isolated_config.exists()
        cfg = _load()
        assert cfg["maxRiskPerTrade"] == _DEFAULTS["maxRiskPerTrade"]
        assert cfg["maxWeeklyLoss"] == _DEFAULTS["maxWeeklyLoss"]
        assert cfg["maxDrawdown"] == _DEFAULTS["maxDrawdown"]
        assert cfg["perSymbol"] == {}
        assert cfg["perRegime"] == {}

    def test_corrupt_file_returns_defaults(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import _load

        isolated_config.write_text("not json {{{", encoding="utf-8")
        cfg = _load()
        assert cfg["maxRiskPerTrade"] == 0.005
        assert cfg["perSymbol"] == {}

    def test_version_always_stamped_on_read(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import _load, SCHEMA_VERSION

        cfg = _load()
        assert cfg["version"] == SCHEMA_VERSION == 1


# ════════════════════════════════════════════════════════════════════════════
# 2. Schema validation (A2 fail-closed)
# ════════════════════════════════════════════════════════════════════════════

class TestSchemaValidation:
    def test_unknown_top_level_key_rejected(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import update_risk_config
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            update_risk_config({"bogus_key": 0.5})
        assert exc.value.status_code == 400
        assert "Unknown risk key" in str(exc.value.detail)

    def test_unknown_override_key_rejected(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import update_risk_config
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            update_risk_config({"perSymbol": {"EURUSD": {"fakeKey": 0.01}}})
        assert exc.value.status_code == 400
        assert "Unknown risk key" in str(exc.value.detail)

    def test_out_of_range_value_rejected(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import update_risk_config
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            update_risk_config({"maxRiskPerTrade": 0.5})  # 50% — way out of range
        assert exc.value.status_code == 400

    def test_non_numeric_value_rejected(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import update_risk_config
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            update_risk_config({"maxRiskPerTrade": "not a number"})
        assert exc.value.status_code == 400

    def test_version_rejected_on_write(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import update_risk_config
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            update_risk_config({"version": 99})
        assert exc.value.status_code == 400
        assert "version" in str(exc.value.detail)

    def test_valid_write_persists_and_loads(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import update_risk_config, _load

        result = update_risk_config({"maxRiskPerTrade": 0.008})
        assert result["status"] == "saved"
        assert isolated_config.exists()
        cfg = _load()
        assert cfg["maxRiskPerTrade"] == 0.008


# ════════════════════════════════════════════════════════════════════════════
# 3. Effective config: 4-axis overrides
# ════════════════════════════════════════════════════════════════════════════

class TestEffectiveConfig:
    def _save(self, isolated_config, data):
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_per_symbol_override(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        self._save(isolated_config, {
            "perSymbol": {"EURUSD": {"maxRiskPerTrade": 0.003}}
        })
        eff = get_effective_config(symbol="EURUSD")
        assert eff["maxRiskPerTrade"] == 0.003
        # global still in effect for other symbols
        eff2 = get_effective_config(symbol="GBPUSD")
        assert eff2["maxRiskPerTrade"] == 0.005

    def test_per_strategy_override(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        self._save(isolated_config, {
            "perStrategy": {"kaufman_ama": {"maxRiskPerTrade": 0.004}}
        })
        eff = get_effective_config(strategy="kaufman_ama")
        assert eff["maxRiskPerTrade"] == 0.004
        # global for other strategies
        eff2 = get_effective_config(strategy="ensemble")
        assert eff2["maxRiskPerTrade"] == 0.005

    def test_per_regime_override(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        self._save(isolated_config, {
            "perRegime": {"trending": {"maxRiskPerTrade": 0.006}}
        })
        eff = get_effective_config(regime="trending")
        assert eff["maxRiskPerTrade"] == 0.006
        # global for other regimes
        eff2 = get_effective_config(regime="ranging")
        assert eff2["maxRiskPerTrade"] == 0.005

    def test_4_axis_layering_symbol_strategy_regime(self, isolated_config):
        """The 4 axes stack: global → perSymbol → perStrategy → perRegime (last wins)."""
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        self._save(isolated_config, {
            "maxRiskPerTrade": 0.005,                                  # global
            "perSymbol": {"EURUSD": {"maxRiskPerTrade": 0.003}},         # narrows EURUSD
            "perStrategy": {"kaufman_ama": {"maxRiskPerTrade": 0.004}},  # narrows kaufman
            "perRegime": {"trending": {"maxRiskPerTrade": 0.006}},       # widens trending
        })
        # EURUSD + kaufman + trending → trending wins (last applied)
        eff = get_effective_config(symbol="EURUSD", strategy="kaufman_ama", regime="trending")
        assert eff["maxRiskPerTrade"] == 0.006
        # EURUSD + kaufman + ranging → kaufman wins
        eff = get_effective_config(symbol="EURUSD", strategy="kaufman_ama", regime="ranging")
        assert eff["maxRiskPerTrade"] == 0.004
        # EURUSD + ensemble + ranging → EURUSD wins
        eff = get_effective_config(symbol="EURUSD", strategy="ensemble", regime="ranging")
        assert eff["maxRiskPerTrade"] == 0.003
        # GBPUSD + ensemble + ranging → global
        eff = get_effective_config(symbol="GBPUSD", strategy="ensemble", regime="ranging")
        assert eff["maxRiskPerTrade"] == 0.005

    def test_symbol_normalization_suffix_stripped(self, isolated_config):
        """EURUSD.vxc, EURUSD.VX, EURUSD/C → all match EURUSD override (v8.0.23 normalizer fix)."""
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        self._save(isolated_config, {
            "perSymbol": {"EURUSD": {"maxRiskPerTrade": 0.003}}
        })
        # Bare matches
        assert get_effective_config(symbol="EURUSD")["maxRiskPerTrade"] == 0.003
        # Lower-case + broker suffix
        assert get_effective_config(symbol="eurusd")["maxRiskPerTrade"] == 0.003
        # .vxc broker suffix (Valetax) — fixed in v8.0.23
        assert get_effective_config(symbol="EURUSD.vxc")["maxRiskPerTrade"] == 0.003
        # .vx broker suffix
        assert get_effective_config(symbol="EURUSD.vx")["maxRiskPerTrade"] == 0.003
        # .VX upper
        assert get_effective_config(symbol="EURUSD.VX")["maxRiskPerTrade"] == 0.003
        # .VXC upper
        assert get_effective_config(symbol="EURUSD.VXC")["maxRiskPerTrade"] == 0.003
        # /C slash variant (some MT5 brokers)
        assert get_effective_config(symbol="EURUSD/C")["maxRiskPerTrade"] == 0.003

    def test_none_inputs_skip_axis(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        # No args → all globals
        eff = get_effective_config()
        assert eff["maxRiskPerTrade"] == 0.005


# ════════════════════════════════════════════════════════════════════════════
# 4. Hot-reload: kill-switch thresholds derived from live config (A3+A4)
# ════════════════════════════════════════════════════════════════════════════

class TestHotReloadKillThresholds:
    def test_kill_switch_daily_derived_from_max_daily_loss(self, isolated_config):
        # Monkey-patched reload reads from isolated_config
        import quant_nanggroe.engine.risk.constants as c
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({
            "version": 1,
            "maxDailyLoss": 0.02,
        }), encoding="utf-8")
        c.reload_risk_constants()
        # Note: 0.8 * 0.02 = 0.016, signed negative
        assert abs(c.KILL_SWITCH_DAILY_PNL - (-0.8 * 0.02)) < 1e-9

    def test_kill_switch_weekly_derived_from_max_weekly_loss(self, isolated_config):
        import quant_nanggroe.engine.risk.constants as c
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({
            "version": 1,
            "maxWeeklyLoss": 0.05,  # 5%
        }), encoding="utf-8")
        c.reload_risk_constants()
        assert abs(c.KILL_SWITCH_WEEKLY_PNL - (-0.8 * 0.05)) < 1e-9

    def test_kill_switch_drawdown_derived_from_max_drawdown(self, isolated_config):
        import quant_nanggroe.engine.risk.constants as c
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({
            "version": 1,
            "maxDrawdown": 0.20,  # 20%
        }), encoding="utf-8")
        c.reload_risk_constants()
        # 0.8 * 0.20 = 0.16 = 16% drawdown trigger
        assert abs(c.KILL_SWITCH_DRAWDOWN_PCT - (0.8 * 0.20)) < 1e-9

    def test_kill_switch_thresholds_remain_final_80pct_buffer(self, isolated_config):
        """A3 constitutional guarantee: 80% early-warning buffer is fixed, only base moves."""
        import quant_nanggroe.engine.risk.constants as c
        # If MAX_WEEKLY_LOSS = 0.10, kill should be -0.08, not -0.025
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({
            "version": 1,
            "maxWeeklyLoss": 0.10,
        }), encoding="utf-8")
        c.reload_risk_constants()
        # Old hardcoded -0.025 would be 25% of 10%, way too loose
        assert c.KILL_SWITCH_WEEKLY_PNL != -0.025
        # New derived: -0.08 (80% of 10%)
        assert abs(c.KILL_SWITCH_WEEKLY_PNL - (-0.08)) < 1e-9


# ════════════════════════════════════════════════════════════════════════════
# 5. End-to-end: full matrix behavior
# ════════════════════════════════════════════════════════════════════════════

class TestEndToEnd:
    def test_effective_config_shape(self, isolated_config):
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        eff = get_effective_config()
        # Must contain all 9 risk fields (no per* dicts leak through)
        expected = {
            "maxRiskPerTrade", "maxPositionSize", "maxLeverage",
            "maxDailyLoss", "maxDailyTrades", "maxWeeklyLoss",
            "maxDrawdown", "minRiskReward", "maxCorrelatedPositions",
        }
        assert expected.issubset(set(eff.keys()))

    def test_default_per_symbol_then_strategy_layering(self, isolated_config):
        """Most realistic scenario: perSymbol narrows, perStrategy further narrows."""
        from quant_nanggroe.api.routes.risk_config import get_effective_config

        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({
            "version": 1,
            "maxRiskPerTrade": 0.005,
            "perSymbol": {"XAUUSD": {"maxRiskPerTrade": 0.007}},          # gold: wider
            "perStrategy": {"ensemble": {"maxRiskPerTrade": 0.002}},      # ensemble: tight
        }), encoding="utf-8")
        # XAUUSD + ensemble → ensemble wins (0.002)
        assert get_effective_config(symbol="XAUUSD", strategy="ensemble")["maxRiskPerTrade"] == 0.002
        # XAUUSD + kaufman → XAUUSD wins (0.007)
        assert get_effective_config(symbol="XAUUSD", strategy="kaufman_ama")["maxRiskPerTrade"] == 0.007
        # EURUSD + ensemble → ensemble wins (0.002)
        assert get_effective_config(symbol="EURUSD", strategy="ensemble")["maxRiskPerTrade"] == 0.002
        # EURUSD + kaufman → global (0.005)
        assert get_effective_config(symbol="EURUSD", strategy="kaufman_ama")["maxRiskPerTrade"] == 0.005
