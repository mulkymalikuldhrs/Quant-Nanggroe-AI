"""Base Investor Agent.

Simple non-LLM base class with shared analysis helpers and investor tools.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# =============================================================================
# Shared Investor Tools
# =============================================================================


@tool
def valuation_metrics(symbol: str, metric_type: str = "overview") -> str:
    """Get valuation metrics for a symbol.

    Args:
        symbol: Stock ticker symbol
        metric_type: Type of metrics (overview, dcf, relative, owner_earnings)

    Returns:
        JSON string with valuation data
    """
    result = {
        "symbol": symbol.upper(),
        "metric_type": metric_type,
        "pe_ratio": 25.0,
        "pb_ratio": 4.5,
        "ps_ratio": 8.2,
        "ev_ebitda": 18.5,
        "fcf_yield": 0.035,
        "peg_ratio": 1.8,
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def financial_health(symbol: str) -> str:
    """Assess financial health of a company.

    Args:
        symbol: Stock ticker symbol

    Returns:
        JSON string with financial health assessment
    """
    result = {
        "symbol": symbol.upper(),
        "roe": 0.18,
        "debt_to_equity": 0.55,
        "current_ratio": 1.8,
        "operating_margin": 0.22,
        "free_cash_flow": "positive",
        "book_value_growth": 0.12,
        "earnings_consistency": "stable",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def competitive_moat(symbol: str) -> str:
    """Analyze competitive moat strength.

    Args:
        symbol: Stock ticker symbol

    Returns:
        JSON string with moat analysis
    """
    result = {
        "symbol": symbol.upper(),
        "moat_type": "brand_and_network_effects",
        "moat_strength": "wide",
        "pricing_power": True,
        "switching_costs": True,
        "network_effects": True,
        "brand_strength": "strong",
        "patent_protection": "moderate",
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


@tool
def management_quality(symbol: str) -> str:
    """Assess management quality and capital allocation.

    Args:
        symbol: Stock ticker symbol

    Returns:
        JSON string with management quality assessment
    """
    result = {
        "symbol": symbol.upper(),
        "shareholder_friendly": True,
        "buyback_history": "consistent",
        "dividend_policy": "growing",
        "capital_allocation": "excellent",
        "insider_ownership": "moderate",
        "governance_score": 0.78,
        "timestamp": datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


INVESTOR_TOOLS = [valuation_metrics, financial_health, competitive_moat, management_quality]


# =============================================================================
# Base Investor Agent
# =============================================================================


class BaseInvestorAgent:
    """Base class for investor persona agents.

    Each persona inherits from this class and provides:
    - A unique name and style
    - An analyze() method that returns an investment thesis dict

    The base class provides shared non-LLM analysis helpers that subclasses
    can use or override.
    """

    def __init__(self, name: str = "", style: str = "", **kwargs: Any) -> None:
        self.name = name
        self.style = style
        self.tools = INVESTOR_TOOLS
        for k, v in kwargs.items():
            setattr(self, k, v)

    def analyze(self, symbol: str, **kwargs: Any) -> Dict[str, Any]:
        """Analyze a symbol and return a basic investment thesis.

        Args:
            symbol: Stock ticker symbol
            **kwargs: Additional analysis parameters

        Returns:
            Dict with signal, confidence, and supporting data
        """
        vals = json.loads(valuation_metrics(symbol))
        health = json.loads(financial_health(symbol))
        moat = json.loads(competitive_moat(symbol))
        mgmt = json.loads(management_quality(symbol))

        signal = "NEUTRAL"
        confidence = 0.5
        # Simple heuristic: wide moat + positive FCF + good governance = bullish
        if moat.get("moat_strength") == "wide" and health.get("free_cash_flow") == "positive":
            signal = "BULLISH"
            confidence = 0.65
        if mgmt.get("governance_score", 0) < 0.4:
            signal = "BEARISH"
            confidence = 0.55

        return {
            "symbol": symbol.upper(),
            "investor_name": self.name,
            "investor_style": self.style,
            "signal": signal,
            "confidence": confidence,
            "valuation": vals,
            "financial_health": health,
            "competitive_moat": moat,
            "management_quality": mgmt,
            "timestamp": datetime.now().isoformat(),
        }
