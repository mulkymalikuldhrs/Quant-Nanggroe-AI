"""Committee floor UI wiring — effective-config overrides + settings-page contract.

Default behavior unchanged (0.10). Pins:
  1. get_effective_config returns custom floor for perSymbol override.
  2. get_effective_config / resolve_committee_threshold return custom floor
     for perRegime override.
  3. UI contract: settings page source wires minCommitteeConfidence in
     load + save sections (cheap file-text assertion).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from quant_nanggroe.api.routes.risk_config import (
    _DEFAULTS,
    get_effective_config,
)
from quant_nanggroe.engine.agentic.committee.vote_chamber import (
    resolve_committee_threshold,
)


def _base(**overrides):
    cfg = dict(_DEFAULTS)
    cfg.update(overrides)
    return cfg


def test_effective_config_symbol_override_floor(monkeypatch):
    import quant_nanggroe.api.routes.risk_config as rc

    monkeypatch.setattr(
        rc, "_load",
        lambda: _base(perSymbol={"EURUSD": {"minCommitteeConfidence": 0.40}}),
    )
    assert get_effective_config(symbol="EURUSD")["minCommitteeConfidence"] == pytest.approx(0.40)
    assert resolve_committee_threshold(symbol="EURUSD") == pytest.approx(0.40)
    # unrelated symbol falls back to default 0.10
    assert get_effective_config(symbol="GBPUSD")["minCommitteeConfidence"] == pytest.approx(0.10)
    assert resolve_committee_threshold(symbol="GBPUSD") == pytest.approx(0.10)


def test_effective_config_regime_override_floor(monkeypatch):
    import quant_nanggroe.api.routes.risk_config as rc

    monkeypatch.setattr(
        rc, "_load",
        lambda: _base(perRegime={"trending": {"minCommitteeConfidence": 0.50}}),
    )
    assert get_effective_config(regime="trending")["minCommitteeConfidence"] == pytest.approx(0.50)
    assert resolve_committee_threshold(regime="trending") == pytest.approx(0.50)
    # unrelated regime falls back to default 0.10
    assert get_effective_config(regime="ranging")["minCommitteeConfidence"] == pytest.approx(0.10)
    assert resolve_committee_threshold(regime="ranging") == pytest.approx(0.10)


def test_settings_page_wires_committee_floor():
    src = (
        Path(__file__).resolve().parents[2]
        / "dashboard" / "src" / "app" / "settings" / "page.tsx"
    ).read_text(encoding="utf-8")
    # key present in load/merge, save payload, and Risk Limits row + perRegime option
    assert src.count("minCommitteeConfidence") >= 4
    assert "rc.minCommitteeConfidence" in src  # load/merge section
    assert "payload.minCommitteeConfidence" in src  # save PUT section
    assert "Committee Floor" in src  # Risk Limits row label
    assert "0.05-0.65" in src  # range hint
