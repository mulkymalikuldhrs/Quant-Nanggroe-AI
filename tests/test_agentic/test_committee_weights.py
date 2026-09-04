"""Unit tests for committee vote weights / quorum / veto.

Verifies quant_nanggroe/engine/agentic/committee/vote_chamber.py behavior:
  - QUORUM=3 enforced (only real analyst votes count, not error fallbacks)
  - CONFIDENCE_THRESHOLD=0.10 enforced (below → hold)
  - risk_officer veto absolute (VETO_POWERS) — forces hold @ 0.0
Analysts are stubbed for determinism; the risk veto test drives the REAL
RiskOfficer.analyze with a breached daily-loss portfolio state.
"""
from __future__ import annotations

import pytest

from quant_nanggroe.engine.agentic.committee import vote_chamber
from quant_nanggroe.engine.agentic.committee.agents import AgentVote
from quant_nanggroe.engine.agentic.committee.vote_chamber import (
    CONFIDENCE_THRESHOLD,
    QUORUM,
    VETO_POWERS,
    VoteChamber,
    resolve_committee_threshold,
)


def _vote(name: str, bias: str, conf: float) -> AgentVote:
    return AgentVote(agent_name=name, bias=bias, confidence=conf, evidence=[f"{name}:{bias}"])


@pytest.fixture
def chamber() -> VoteChamber:
    return VoteChamber()


def _stub(chamber: VoteChamber, bull=None, bear=None, macro=None):
    if bull is not None:
        chamber.bull.analyze = lambda *a, **k: bull  # type: ignore[method-assign]
    if bear is not None:
        chamber.bear.analyze = lambda *a, **k: bear  # type: ignore[method-assign]
    if macro is not None:
        chamber.macro.analyze = lambda *a, **k: macro  # type: ignore[method-assign]
    # risk officer approves by default (empty portfolio state)
    chamber.risk.analyze = lambda *a, **k: _vote("risk_officer", "neutral", 1.0)  # type: ignore[method-assign]


def test_threshold_constants():
    assert QUORUM == 3
    assert CONFIDENCE_THRESHOLD == 0.10
    assert VETO_POWERS == {"risk_officer"}


def test_strong_bullish_consensus_buys(chamber):
    _stub(chamber,
          bull=_vote("bull_analyst", "bullish", 0.8),
          bear=_vote("bear_analyst", "neutral", 0.0),
          macro=_vote("macro_analyst", "bullish", 0.5))
    out = chamber.convene("EURUSD", None, entry_price=1.1, atr=0.001)
    assert out.quorum_met is True
    assert out.final_action == "buy"
    assert out.final_confidence >= CONFIDENCE_THRESHOLD
    assert out.risk_vetoed is False


def test_below_threshold_holds(chamber):
    _stub(chamber,
          bull=_vote("bull_analyst", "bullish", 0.05),
          bear=_vote("bear_analyst", "neutral", 0.0),
          macro=_vote("macro_analyst", "neutral", 0.0))
    out = chamber.convene("EURUSD", None)
    assert out.quorum_met is True
    assert out.final_action == "hold"
    assert out.risk_vetoed is False


def test_bearish_consensus_sells(chamber):
    _stub(chamber,
          bull=_vote("bull_analyst", "neutral", 0.0),
          bear=_vote("bear_analyst", "bearish", 0.9),
          macro=_vote("macro_analyst", "bearish", 0.4))
    out = chamber.convene("EURUSD", None, entry_price=1.1, atr=0.001)
    assert out.final_action == "sell"
    assert out.final_confidence >= CONFIDENCE_THRESHOLD


def test_risk_veto_absolute_overrides_strong_buy(chamber):
    """REAL RiskOfficer with breached daily loss must force hold @ 0.0."""
    _stub(chamber,
          bull=_vote("bull_analyst", "bullish", 0.95),
          bear=_vote("bear_analyst", "neutral", 0.0),
          macro=_vote("macro_analyst", "bullish", 0.9))
    # restore the REAL risk officer: 5% daily loss vs 1% limit → VETO
    real_risk = VoteChamber().risk
    chamber.risk = real_risk
    out = chamber.convene(
        "EURUSD", None, entry_price=1.1, atr=0.001,
        portfolio_state={"equity": 10_000.0, "daily_pnl": -500.0,
                         "open_positions": 0, "max_drawdown": 0.0})
    assert out.risk_vetoed is True
    assert out.final_action == "hold"
    assert out.final_confidence == 0.0
    assert "Daily loss limit" in out.risk_reason


def test_quorum_not_met_blocks_trade(chamber):
    def _boom(*a, **k):
        raise RuntimeError("analyst down")

    chamber.bull.analyze = _boom  # type: ignore[method-assign]
    chamber.bear.analyze = _boom  # type: ignore[method-assign]
    chamber.macro.analyze = lambda *a, **k: _vote("macro_analyst", "bullish", 0.9)  # type: ignore[method-assign]
    out = chamber.convene("EURUSD", None)
    assert out.quorum_met is False
    assert out.final_action == "hold"
    assert "Quorum not met: 1/3" in out.risk_reason


def test_module_constants_are_single_source():
    assert vote_chamber.QUORUM == QUORUM
    assert vote_chamber.CONFIDENCE_THRESHOLD == CONFIDENCE_THRESHOLD


def test_committee_floor_default_unchanged(chamber, monkeypatch):
    """Default effective config → floor 0.10; weak single-factor vote still passes."""
    monkeypatch.setattr(
        "quant_nanggroe.api.routes.risk_config._load",
        lambda: dict(vote_chamber_default_config()),
    )
    assert resolve_committee_threshold(symbol="EURUSD") == pytest.approx(0.10)
    # 0.35 weight * 0.30 conf = 0.105 >= 0.10 → buy (legacy behavior preserved)
    _stub(chamber,
          bull=_vote("bull_analyst", "bullish", 0.30),
          bear=_vote("bear_analyst", "neutral", 0.0),
          macro=_vote("macro_analyst", "neutral", 0.0))
    out = chamber.convene("EURUSD", None)
    assert out.final_action == "buy"


def test_committee_floor_custom_blocks_weak_vote(chamber, monkeypatch):
    """minCommitteeConfidence=0.30 blocks the weak single-factor vote 0.10 passes."""
    monkeypatch.setattr(
        "quant_nanggroe.api.routes.risk_config._load",
        lambda: {**vote_chamber_default_config(), "minCommitteeConfidence": 0.30},
    )
    assert resolve_committee_threshold(symbol="EURUSD") == pytest.approx(0.30)
    _stub(chamber,
          bull=_vote("bull_analyst", "bullish", 0.30),
          bear=_vote("bear_analyst", "neutral", 0.0),
          macro=_vote("macro_analyst", "neutral", 0.0))
    out = chamber.convene("EURUSD", None)
    assert out.final_action == "hold"


def test_committee_floor_invalid_falls_back(chamber, monkeypatch):
    """Out-of-range / non-numeric floor → fail-closed 0.10."""
    monkeypatch.setattr(
        "quant_nanggroe.api.routes.risk_config._load",
        lambda: {**vote_chamber_default_config(), "minCommitteeConfidence": 0.99},
    )
    assert resolve_committee_threshold(symbol="EURUSD") == pytest.approx(0.10)
    monkeypatch.setattr(
        "quant_nanggroe.api.routes.risk_config._load",
        lambda: {**vote_chamber_default_config(), "minCommitteeConfidence": "junk"},
    )
    assert resolve_committee_threshold(symbol="EURUSD") == pytest.approx(0.10)


def vote_chamber_default_config() -> dict:
    from quant_nanggroe.api.routes.risk_config import _DEFAULTS

    return dict(_DEFAULTS)
