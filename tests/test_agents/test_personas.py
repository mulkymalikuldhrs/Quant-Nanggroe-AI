"""
Tests for Investor Persona Agents (legendary investor perspectives).

Targets the ACTUAL production API in ``quant_nanggroe.agents.personas``:

    WarrenBuffettAgent        — analyze(ticker, price, intrinsic_value)
                                 + estimate_intrinsic_value() / assess_moat()
    PeterLynchAgent           — analyze(ticker, **kwargs)
    MichaelBurryAgent         — analyze(ticker, **kwargs)
    CathieWoodAgent           — analyze(ticker, **kwargs)
    StanleyDruckenmillerAgent — analyze(ticker, **kwargs)
    RayDalioAgent             — analyze(ticker, **kwargs)

Each persona is a plain non-LLM analyzer exposing ``.name`` and ``.style``
and an ``analyze()`` method returning a dict. (Legacy test rot referenced a
LangChain ``llm=`` / ``__call__`` / ``_system_prompt`` API that does not
exist in the current code; this file is the corrected source-of-truth test.)
"""

from __future__ import annotations

import pytest

from quant_nanggroe.agents.personas.base_investor import BaseInvestorAgent
from quant_nanggroe.agents.personas.cathie_wood import CathieWoodAgent
from quant_nanggroe.agents.personas.michael_burry import MichaelBurryAgent
from quant_nanggroe.agents.personas.peter_lynch import PeterLynchAgent
from quant_nanggroe.agents.personas.ray_dalio import RayDalioAgent
from quant_nanggroe.agents.personas.stanley_druckenmiller import (
    StanleyDruckenmillerAgent,
)
from quant_nanggroe.agents.personas.warren_buffett import WarrenBuffettAgent

KWARGS_PERSONAS = [
    PeterLynchAgent,
    MichaelBurryAgent,
    CathieWoodAgent,
    StanleyDruckenmillerAgent,
    RayDalioAgent,
]


class TestWarrenBuffettAgent:
    def test_agent_creation(self) -> None:
        agent = WarrenBuffettAgent()
        assert agent.name == "Warren Buffett"
        assert agent.style == "value_investing"
        assert agent.holding_period_years == 10

    def test_analyze_bullish_with_margin_of_safety(self) -> None:
        agent = WarrenBuffettAgent()
        out = agent.analyze("AAPL", price=150.0, intrinsic_value=200.0)
        assert out["agent"] == "Warren Buffett"
        assert out["ticker"] == "AAPL"
        assert out["current_price"] == 150.0
        assert out["intrinsic_value"] == 200.0
        # margin of safety = (200-150)/150 = 0.333... > 0.2 -> bullish
        assert out["signal"] == "bullish"
        assert out["margin_of_safety"] == pytest.approx(1 / 3, abs=1e-6)
        assert out["moat_rating"] == "narrow"

    def test_analyze_neutral_without_margin(self) -> None:
        agent = WarrenBuffettAgent()
        out = agent.analyze("KO", price=100.0, intrinsic_value=105.0)
        # moa = 0.05 < 0.2 -> neutral
        assert out["signal"] == "neutral"
        assert out["margin_of_safety"] == pytest.approx(0.05, abs=1e-6)

    def test_estimate_intrinsic_value_dcf(self) -> None:
        agent = WarrenBuffettAgent()
        iv = agent.estimate_intrinsic_value("AAPL", free_cash_flow=100.0)
        assert isinstance(iv, float)
        assert iv > 0

    def test_estimate_intrinsic_value_zero_discount(self) -> None:
        agent = WarrenBuffettAgent()
        # discount_rate <= 0 -> fcf * years
        iv = agent.estimate_intrinsic_value(
            "AAPL", free_cash_flow=100.0, discount_rate=0.0, years=10
        )
        assert iv == pytest.approx(1000.0, abs=1e-6)

    def test_assess_moat_wide(self) -> None:
        agent = WarrenBuffettAgent()
        moat = agent.assess_moat(
            "AAPL",
            "tech",
            {
                "brand": True,
                "network_effects": True,
                "switching_costs": True,
                "ip_protection": True,
                "scale": True,
            },
        )
        assert moat == "wide"

    def test_assess_moat_narrow(self) -> None:
        agent = WarrenBuffettAgent()
        moat = agent.assess_moat(
            "XYZ", "retail", {"brand": True, "network_effects": False,
                              "switching_costs": True}
        )
        assert moat == "narrow"

    def test_assess_moat_none(self) -> None:
        agent = WarrenBuffettAgent()
        moat = agent.assess_moat("XYZ", "retail", {})
        assert moat == "none"


class TestKwargsPersonas:
    @pytest.mark.parametrize("agent_cls", KWARGS_PERSONAS)
    def test_creation(self, agent_cls) -> None:
        agent = agent_cls()
        assert isinstance(agent.name, str) and len(agent.name) > 0
        assert isinstance(agent.style, str) and len(agent.style) > 0

    @pytest.mark.parametrize("agent_cls", KWARGS_PERSONAS)
    def test_analyze_shape(self, agent_cls) -> None:
        agent = agent_cls()
        out = agent.analyze("AAPL")
        assert isinstance(out, dict)
        for key in ("agent", "style", "ticker", "signal", "confidence",
                    "reasoning", "timestamp"):
            assert key in out, f"missing {key} in {agent_cls.__name__}"
        assert out["ticker"] == "AAPL"
        assert out["signal"] in ("bullish", "bearish", "neutral")
        assert 0.0 <= float(out["confidence"]) <= 1.0

    @pytest.mark.parametrize("agent_cls", KWARGS_PERSONAS)
    def test_analyze_is_deterministic(self, agent_cls) -> None:
        a1, a2 = agent_cls(), agent_cls()
        assert a1.analyze("MSFT") == a2.analyze("MSFT")


class TestPeterLynchAgent:
    def test_agent_creation(self) -> None:
        agent = PeterLynchAgent()
        assert agent.name == "Peter Lynch"
        assert agent.style == "growth_at_reasonable_price"


class TestMichaelBurryAgent:
    def test_agent_creation(self) -> None:
        agent = MichaelBurryAgent()
        assert agent.name == "Michael Burry"
        assert agent.style == "deep_value_contrarian"


class TestCathieWoodAgent:
    def test_agent_creation(self) -> None:
        agent = CathieWoodAgent()
        assert agent.name == "Cathie Wood"
        assert agent.style == "disruptive_innovation"


class TestStanleyDruckenmillerAgent:
    def test_agent_creation(self) -> None:
        agent = StanleyDruckenmillerAgent()
        assert agent.name == "Stanley Druckenmiller"
        assert agent.style == "macro_top_down"


class TestRayDalioAgent:
    def test_agent_creation(self) -> None:
        agent = RayDalioAgent()
        assert agent.name == "Ray Dalio"
        assert agent.style == "risk_parity_all_weather"


class TestPersonaDiversity:
    def test_unique_names(self) -> None:
        names = [cls().name for cls in (WarrenBuffettAgent, *KWARGS_PERSONAS)]
        assert len(names) == len(set(names))

    def test_unique_styles(self) -> None:
        styles = [cls().style for cls in (WarrenBuffettAgent, *KWARGS_PERSONAS)]
        assert len(styles) == len(set(styles))


class TestBaseInvestorAgent:
    def test_is_abstract_base(self) -> None:
        """Base class is not meant to be instantiated as a usable persona."""
        assert issubclass(WarrenBuffettAgent, BaseInvestorAgent)
        # All concrete personas subclass it
        for cls in KWARGS_PERSONAS:
            assert issubclass(cls, BaseInvestorAgent)
