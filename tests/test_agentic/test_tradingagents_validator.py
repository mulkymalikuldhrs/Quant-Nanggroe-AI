"""Q3 — TradingAgents v0.3.1 as 2nd-opinion validator.

Reality check (2026-07-23):
- tradingagents v0.3.1 ``propagate()`` returns ``(final_state, rating_string)``
  where rating_string is the 5-tier scale Buy/Overweight/Hold/Underweight/Sell.
- The legacy adapter did ``decision.get("action")`` on that STRING -> AttributeError
  swallowed -> ALWAYS returned neutral (dead adapter).
- tradingagents has NO free/official local LLM backend; its default provider is a
  PAID OpenAI model (gpt-5.5). Under the Dhaher Labs no-paid-API rule the live call
  must be blocked by default.

These tests exercise the FIXED parse path + cost-guard + the new
``TradingAgentsValidator`` arbitrator WITHOUT invoking any paid LLM. A fake
in-process ``TradingAgentsGraph`` stands in for the real one.
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest

from quant_nanggroe.engine.agentic.adapters import (
    TradingAgentsAdapter,
    TradingAgentsValidator,
    _map_ta_rating,
    _ta_should_block,
)
from quant_nanggroe.engine.agentic.voting import Bias, Signal, VoteResult


# ── unit: rating mapping (the exact spec from tradingagents v0.3.1) ──────────
@pytest.mark.parametrize(
    "rating,bias,conf",
    [
        ("Buy", Bias.BUY, 0.5),
        ("Overweight", Bias.BUY, 0.5),
        ("Hold", Bias.NEUTRAL, 0.0),
        ("Underweight", Bias.SELL, 0.5),
        ("Sell", Bias.SELL, 0.5),
        ("buy", Bias.BUY, 0.5),          # case-insensitive
        ("garbage", Bias.NEUTRAL, 0.0),  # unknown -> neutral
        (123, Bias.NEUTRAL, 0.0),        # non-str -> neutral
    ],
)
def test_map_ta_rating(rating, bias, conf):
    got_bias, got_conf = _map_ta_rating(rating)
    assert got_bias == bias
    assert got_conf == conf


# ── unit: cost-guard (fail-closed) ─────────────────────────────────────────
def test_should_block_default_blocks_paid(monkeypatch):
    monkeypatch.delenv("QNA_ALLOW_PAID_LLM", raising=False)
    assert _ta_should_block({"llm_provider": "openai"}) is True
    assert _ta_should_block({"llm_provider": "anthropic"}) is True
    assert _ta_should_block({"llm_provider": "azure"}) is True
    assert _ta_should_block({"llm_provider": "bedrock"}) is True
    assert _ta_should_block({"llm_provider": "google"}) is True


def test_should_block_optin_allows(monkeypatch):
    monkeypatch.setenv("QNA_ALLOW_PAID_LLM", "1")
    assert _ta_should_block({"llm_provider": "openai"}) is False
    monkeypatch.setenv("QNA_ALLOW_PAID_LLM", "true")
    assert _ta_should_block({"llm_provider": "openai"}) is False
    monkeypatch.setenv("QNA_ALLOW_PAID_LLM", "yes")
    assert _ta_should_block({"llm_provider": "openai"}) is False


def test_should_block_unknown_provider_treated_paid(monkeypatch):
    # Fail-closed: anything we don't recognise as free is treated as paid.
    monkeypatch.delenv("QNA_ALLOW_PAID_LLM", raising=False)
    assert _ta_should_block({"llm_provider": "some_new_cloud"}) is True


# ── integration: adapter never bills a paid LLM by default ─────────────────
class _FakeTA:
    """Stands in for TradingAgentsGraph. Raises if instantiated while blocked."""

    def __init__(self, *a, **k):
        raise AssertionError("TradingAgentsGraph was instantiated -> paid LLM would be billed!")

    def propagate(self, *a, **k):  # pragma: no cover - defensive
        return ("state", "Buy")


def _patch_imports(monkeypatch, fake_graph_class=None, fake_config=None):
    """Make _safe_import return fakes instead of touching E:/tradingagents."""
    if fake_graph_class is None:
        # Default: if reached, would bill -> assert it's never reached.
        fake_graph_class = _FakeTA
    if fake_config is None:
        fake_config = {"llm_provider": "openai"}

    def fake_safe_import(self, module_path, module_name, attr=None):
        if "trading_graph" in module_name:
            return fake_graph_class
        if "default_config" in module_name:
            return fake_config
        return None

    monkeypatch.setattr(TradingAgentsAdapter, "_safe_import", fake_safe_import)


def test_adapter_refuses_paid_by_default(monkeypatch):
    monkeypatch.delenv("QNA_ALLOW_PAID_LLM", raising=False)
    _patch_imports(monkeypatch)  # FakeTA raises if ever instantiated
    sig = TradingAgentsAdapter().fetch_signal("EURUSD")
    # Must NOT bill: returns None, never instantiates the graph.
    assert sig is None


def test_adapter_runs_when_optin(monkeypatch):
    monkeypatch.setenv("QNA_ALLOW_PAID_LLM", "1")

    class _FakeTARun:
        def __init__(self, *a, **k):
            pass

        def propagate(self, symbol, today):
            # Same contract as real v0.3.1: (final_state, rating_string)
            return ("final_state", "Buy")

    _patch_imports(monkeypatch, fake_graph_class=_FakeTARun,
                   fake_config={"llm_provider": "openai"})
    sig = TradingAgentsAdapter().fetch_signal("EURUSD")
    assert sig is not None
    assert sig.bias == Bias.BUY
    assert sig.confidence == 0.5
    assert sig.source == "tradingagents"


def test_adapter_maps_sell_rating_when_optin(monkeypatch):
    monkeypatch.setenv("QNA_ALLOW_PAID_LLM", "1")

    class _FakeTASell:
        def __init__(self, *a, **k):
            pass

        def propagate(self, symbol, today):
            return ("final_state", "Sell")

    _patch_imports(monkeypatch, fake_graph_class=_FakeTASell,
                   fake_config={"llm_provider": "openai"})
    sig = TradingAgentsAdapter().fetch_signal("EURUSD")
    assert sig is not None
    assert sig.bias == Bias.SELL


# ── the 2nd-opinion validator arbitrator ───────────────────────────────────
def _vote(bias, strength=0.8):
    return VoteResult(
        final_bias=bias,
        weighted_confidence=strength,
        votes=[Signal(bias, strength, "wyckoff")],
        consensus_strength=strength,
        dissenters=[],
    )


def test_validator_confirm(monkeypatch):
    monkeypatch.delenv("QNA_ALLOW_PAID_LLM", raising=False)

    class _FakeAdapterConfirm(TradingAgentsAdapter):
        def fetch_signal(self, symbol, **kw):
            return Signal(Bias.BUY, 0.5, "tradingagents")

    v = TradingAgentsValidator(_FakeAdapterConfirm())
    verdict = v.evaluate(_vote(Bias.BUY), "EURUSD")
    assert verdict.status == "confirm"
    assert "primary buy" in verdict.reason.lower()


def test_validator_contradict(monkeypatch):
    monkeypatch.delenv("QNA_ALLOW_PAID_LLM", raising=False)

    class _FakeAdapterContra(TradingAgentsAdapter):
        def fetch_signal(self, symbol, **kw):
            return Signal(Bias.SELL, 0.5, "tradingagents")

    v = TradingAgentsValidator(_FakeAdapterContra())
    verdict = v.evaluate(_vote(Bias.BUY), "EURUSD")
    assert verdict.status == "contradict"
    assert "ext=sell" in verdict.reason.lower()


def test_validator_neutral(monkeypatch):
    monkeypatch.delenv("QNA_ALLOW_PAID_LLM", raising=False)

    class _FakeAdapterNeutral(TradingAgentsAdapter):
        def fetch_signal(self, symbol, **kw):
            return Signal(Bias.NEUTRAL, 0.0, "tradingagents")

    v = TradingAgentsValidator(_FakeAdapterNeutral())
    verdict = v.evaluate(_vote(Bias.BUY), "EURUSD")
    assert verdict.status == "neutral"


def test_validator_abstains_when_unavailable(monkeypatch):
    monkeypatch.delenv("QNA_ALLOW_PAID_LLM", raising=False)

    class _FakeAdapterDown(TradingAgentsAdapter):
        def fetch_signal(self, symbol, **kw):
            return None  # e.g. paid-LLM guard or import failure

    v = TradingAgentsValidator(_FakeAdapterDown())
    verdict = v.evaluate(_vote(Bias.BUY), "EURUSD")
    assert verdict.status == "abstain"
    # Crucial: a broken external model can NEVER silently flip the primary trade.
    assert verdict.signal is None


# ── regression: legacy hedge_fund.signal_tradingagents parse fix ───────────
def test_legacy_signal_tradingagents_rating_parse(monkeypatch):
    """signal_tradingagents must map the 5-tier rating, not decision.get('action')."""
    mod = pytest.importorskip("quant_nanggroe.hedge_fund.hedge_fund")

    monkeypatch.setenv("QNA_ALLOW_PAID_LLM", "1")

    class _FakeTABuy:
        def __init__(self, *a, **k):
            pass

        def propagate(self, symbol, today):
            return ("state", "Overweight")

    # signal_tradingagents imports tradingagents locally; patch sys.modules so
    # the local import resolves to our fakes (no E:/tradingagents / paid LLM).
    fake_mod = type("ta", (), {})()
    fake_mod.DEFAULT_CONFIG = {"llm_provider": "openai"}
    fake_mod.TradingAgentsGraph = _FakeTABuy
    monkeypatch.setitem(sys.modules, "tradingagents.graph.trading_graph", fake_mod)
    monkeypatch.setitem(sys.modules, "tradingagents.default_config", fake_mod)
    # Prevent the real E:/tradingagents path from being inserted/imported.
    monkeypatch.setattr(
        "sys.path",
        [p for p in sys.path if p != "E:/tradingagents"],
    )

    result = mod.signal_tradingagents("EURUSD")
    assert result["bias"] == "buy"   # Overweight maps to buy
    assert result["confidence"] == 0.5
