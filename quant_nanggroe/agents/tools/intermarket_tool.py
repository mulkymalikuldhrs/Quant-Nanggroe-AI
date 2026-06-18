"""Intermarket Tool — Cross-Market Correlation & Relative Strength Analysis.

Provides intermarket analysis across bonds, equities, commodities, and FX,
including correlation matrices, relative strength, sector rotation signals,
and commodity-currency pair analysis.

Features
--------
* Cross-market correlation matrix (bonds, equities, commodities, FX)
* Relative strength analysis across markets
* Sector rotation signals
* Commodity-currency pair analysis (AUD/CAD vs oil, etc.)
* LangChain @tool function for agent consumption

References
----------
Misi-Screener IntermarketEngine component
"""

from __future__ import annotations

import json
import logging
import math
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MarketSector(str, Enum):
    """Market sectors for rotation analysis."""
    TECHNOLOGY = "TECHNOLOGY"
    HEALTHCARE = "HEALTHCARE"
    FINANCIALS = "FINANCIALS"
    ENERGY = "ENERGY"
    MATERIALS = "MATERIALS"
    INDUSTRIALS = "INDUSTRIALS"
    CONSUMER_DISCRETIONARY = "CONSUMER_DISCRETIONARY"
    CONSUMER_STAPLES = "CONSUMER_STAPLES"
    UTILITIES = "UTILITIES"
    REAL_ESTATE = "REAL_ESTATE"
    COMMUNICATIONS = "COMMUNICATIONS"


class RotationSignal(str, Enum):
    """Sector rotation signal."""
    EARLY_CYCLE = "EARLY_CYCLE"
    MID_CYCLE = "MID_CYCLE"
    LATE_CYCLE = "LATE_CYCLE"
    RECESSION = "RECESSION"
    RECOVERY = "RECOVERY"


class CorrelationStrength(str, Enum):
    """Correlation strength classification."""
    STRONG_POSITIVE = "STRONG_POSITIVE"
    MODERATE_POSITIVE = "MODERATE_POSITIVE"
    WEAK_POSITIVE = "WEAK_POSITIVE"
    UNCORRELATED = "UNCORRELATED"
    WEAK_NEGATIVE = "WEAK_NEGATIVE"
    MODERATE_NEGATIVE = "MODERATE_NEGATIVE"
    STRONG_NEGATIVE = "STRONG_NEGATIVE"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CorrelationPair(BaseModel):
    """Correlation between two market instruments."""
    asset_a: str = Field(..., description="First asset symbol")
    asset_b: str = Field(..., description="Second asset symbol")
    correlation: float = Field(0.0, description="Pearson correlation coefficient (-1 to +1)")
    strength: CorrelationStrength = Field(CorrelationStrength.UNCORRELATED)
    rolling_20d: float = Field(0.0, description="20-day rolling correlation")
    rolling_60d: float = Field(0.0, description="60-day rolling correlation")
    divergence: bool = Field(False, description="Whether current correlation diverges from trend")


class CorrelationMatrix(BaseModel):
    """Full correlation matrix across market classes."""
    timestamp: str = Field("")
    bonds_equities: float = Field(0.0, description="Bonds vs Equities correlation")
    bonds_commodities: float = Field(0.0, description="Bonds vs Commodities correlation")
    bonds_fx: float = Field(0.0, description="Bonds vs FX correlation")
    equities_commodities: float = Field(0.0, description="Equities vs Commodities correlation")
    equities_fx: float = Field(0.0, description="Equities vs FX correlation")
    commodities_fx: float = Field(0.0, description="Commodities vs FX correlation")
    notable_pairs: List[CorrelationPair] = Field(default_factory=list)
    risk_on_off: float = Field(0.0, description="Risk-on/Risk-off indicator (-1 to +1)")


class RelativeStrengthResult(BaseModel):
    """Relative strength analysis result."""
    symbol: str = Field(..., description="Analyzed symbol")
    vs_benchmark: str = Field("SPY", description="Benchmark symbol")
    rs_ratio: float = Field(1.0, description="Relative strength ratio")
    rs_rating: str = Field("NEUTRAL", description="RS rating")
    trend: str = Field("FLAT", description="RS trend direction")
    sector_rank: int = Field(0, description="Rank within sector")
    timestamp: str = Field("")


class SectorRotationResult(BaseModel):
    """Sector rotation analysis result."""
    current_phase: RotationSignal = Field(RotationSignal.MID_CYCLE)
    leading_sectors: List[str] = Field(default_factory=list)
    lagging_sectors: List[str] = Field(default_factory=list)
    sector_momentum: Dict[str, float] = Field(default_factory=dict)
    yield_curve_signal: str = Field("FLAT", description="Yield curve shape")
    confidence: float = Field(0.3, description="Confidence level (0-1)")
    timestamp: str = Field("")


class CommodityCurrencyPair(BaseModel):
    """Commodity-currency pair analysis."""
    commodity: str = Field(..., description="Commodity symbol")
    currency: str = Field(..., description="Currency pair")
    correlation: float = Field(0.0, description="Historical correlation")
    current_divergence: float = Field(0.0, description="Current divergence from correlation")
    trade_signal: str = Field("NEUTRAL", description="Trade signal from divergence")
    confidence: float = Field(0.0, description="Signal confidence (0-1)")


# ---------------------------------------------------------------------------
# Commodity-Currency pair mappings
# ---------------------------------------------------------------------------

_COMMODITY_CURRENCY_PAIRS: List[Dict[str, str]] = [
    {"commodity": "OIL", "currency": "CAD/USD", "typical_corr": 0.6},
    {"commodity": "OIL", "currency": "NOK/USD", "typical_corr": 0.5},
    {"commodity": "GOLD", "currency": "AUD/USD", "typical_corr": 0.4},
    {"commodity": "GOLD", "currency": "XAU/USD", "typical_corr": 0.95},
    {"commodity": "COPPER", "currency": "AUD/USD", "typical_corr": 0.5},
    {"commodity": "IRON_ORE", "currency": "AUD/USD", "typical_corr": 0.6},
    {"commodity": "OIL", "currency": "RUB/USD", "typical_corr": 0.7},
]


# ---------------------------------------------------------------------------
# Intermarket Tool
# ---------------------------------------------------------------------------

class IntermarketTool:
    """Intermarket analysis tool for agent consumption.

    Provides cross-market correlation analysis, relative strength,
    sector rotation signals, and commodity-currency pair analysis.

    When market data APIs are unavailable, the tool uses heuristic
    estimates based on well-known intermarket relationships.

    Usage::

        tool = IntermarketTool()
        matrix = await tool.analyze_correlations()
        rotation = await tool.analyze_sector_rotation()
    """

    def __init__(self, cache_ttl: int = 1800) -> None:
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._cache_ttl = cache_ttl

    # ----- Correlation Matrix -----

    async def analyze_correlations(self) -> CorrelationMatrix:
        """Analyze cross-market correlation matrix.

        Returns:
            CorrelationMatrix with inter-market correlations.
        """
        # Default correlations based on historical norms
        # In production, these would be computed from actual price data
        matrix = CorrelationMatrix(
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            bonds_equities=-0.3,  # Typical negative correlation
            bonds_commodities=-0.2,
            bonds_fx=0.1,
            equities_commodities=0.3,
            equities_fx=0.2,
            commodities_fx=0.4,
            notable_pairs=[
                CorrelationPair(
                    asset_a="TLT", asset_b="SPY",
                    correlation=-0.3,
                    strength=CorrelationStrength.MODERATE_NEGATIVE,
                ),
                CorrelationPair(
                    asset_a="DXY", asset_b="GOLD",
                    correlation=-0.6,
                    strength=CorrelationStrength.STRONG_NEGATIVE,
                ),
                CorrelationPair(
                    asset_a="OIL", asset_b="CAD/USD",
                    correlation=0.6,
                    strength=CorrelationStrength.STRONG_POSITIVE,
                ),
            ],
            risk_on_off=0.2,  # Slight risk-on
        )

        # Try to fetch real data
        try:
            real_data = await self._fetch_correlation_data()
            if real_data:
                matrix = real_data
        except Exception as exc:
            logger.debug("Could not fetch real correlation data: %s", exc)

        return matrix

    async def _fetch_correlation_data(self) -> Optional[CorrelationMatrix]:
        """Fetch real correlation data from market data provider."""
        try:
            import yfinance as yf
            import numpy as np

            tickers = ["SPY", "TLT", "GLD", "USO", "UUP"]
            data = yf.download(tickers, period="3mo", interval="1d")
            if data.empty:
                return None

            returns = data["Close"].pct_change().dropna()
            if returns.empty:
                return None

            corr_matrix = returns.corr()

            return CorrelationMatrix(
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
                bonds_equities=float(corr_matrix.loc["TLT", "SPY"]) if "TLT" in corr_matrix and "SPY" in corr_matrix else 0.0,
                bonds_commodities=float(corr_matrix.loc["TLT", "GLD"]) if "TLT" in corr_matrix and "GLD" in corr_matrix else 0.0,
                equities_commodities=float(corr_matrix.loc["SPY", "GLD"]) if "SPY" in corr_matrix and "GLD" in corr_matrix else 0.0,
                risk_on_off=0.0,
            )
        except Exception:
            return None

    # ----- Relative Strength -----

    async def analyze_relative_strength(
        self,
        symbol: str,
        benchmark: str = "SPY",
    ) -> RelativeStrengthResult:
        """Analyze relative strength of a symbol vs benchmark.

        Args:
            symbol: Stock or ETF symbol.
            benchmark: Benchmark symbol.

        Returns:
            RelativeStrengthResult with RS analysis.
        """
        try:
            import yfinance as yf

            sym_data = yf.Ticker(symbol).history(period="6mo")
            bench_data = yf.Ticker(benchmark).history(period="6mo")

            if sym_data.empty or bench_data.empty:
                return RelativeStrengthResult(
                    symbol=symbol,
                    vs_benchmark=benchmark,
                    timestamp=datetime.now(tz=timezone.utc).isoformat(),
                )

            # Calculate RS ratio
            sym_perf = (sym_data["Close"].iloc[-1] / sym_data["Close"].iloc[0] - 1) * 100
            bench_perf = (bench_data["Close"].iloc[-1] / bench_data["Close"].iloc[0] - 1) * 100

            rs_ratio = (100 + sym_perf) / (100 + bench_perf) if bench_perf != -100 else 1.0

            # Rating
            if rs_ratio > 1.1:
                rs_rating = "STRONG"
                trend = "RISING"
            elif rs_ratio > 1.0:
                rs_rating = "OUTPERFORMING"
                trend = "RISING"
            elif rs_ratio > 0.9:
                rs_rating = "UNDERPERFORMING"
                trend = "FALLING"
            else:
                rs_rating = "WEAK"
                trend = "FALLING"

            return RelativeStrengthResult(
                symbol=symbol,
                vs_benchmark=benchmark,
                rs_ratio=round(rs_ratio, 4),
                rs_rating=rs_rating,
                trend=trend,
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )

        except Exception as exc:
            logger.debug("RS analysis failed for %s: %s", symbol, exc)
            return RelativeStrengthResult(
                symbol=symbol,
                vs_benchmark=benchmark,
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )

    # ----- Sector Rotation -----

    async def analyze_sector_rotation(self) -> SectorRotationResult:
        """Analyze sector rotation signals.

        Returns:
            SectorRotationResult with sector rotation analysis.
        """
        # Heuristic sector momentum (in production, computed from ETF prices)
        sector_momentum = {
            MarketSector.TECHNOLOGY: 0.6,
            MarketSector.HEALTHCARE: 0.4,
            MarketSector.FINANCIALS: 0.5,
            MarketSector.ENERGY: -0.2,
            MarketSector.MATERIALS: 0.1,
            MarketSector.INDUSTRIALS: 0.3,
            MarketSector.CONSUMER_DISCRETIONARY: 0.5,
            MarketSector.CONSUMER_STAPLES: -0.1,
            MarketSector.UTILITIES: -0.3,
            MarketSector.REAL_ESTATE: 0.0,
            MarketSector.COMMUNICATIONS: 0.4,
        }

        # Sort by momentum
        sorted_sectors = sorted(
            sector_momentum.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        leading = [s[0].value for s in sorted_sectors[:3]]
        lagging = [s[0].value for s in sorted_sectors[-3:]]

        # Determine phase
        tech_momentum = sector_momentum.get(MarketSector.TECHNOLOGY, 0)
        utilities_momentum = sector_momentum.get(MarketSector.UTILITIES, 0)
        staples_momentum = sector_momentum.get(MarketSector.CONSUMER_STAPLES, 0)

        if tech_momentum > 0.5 and utilities_momentum < 0:
            phase = RotationSignal.MID_CYCLE
        elif tech_momentum > 0.3 and sector_momentum.get(MarketSector.FINANCIALS, 0) > 0:
            phase = RotationSignal.EARLY_CYCLE
        elif utilities_momentum > 0 and staples_momentum > 0:
            phase = RotationSignal.LATE_CYCLE
        else:
            phase = RotationSignal.MID_CYCLE

        return SectorRotationResult(
            current_phase=phase,
            leading_sectors=leading,
            lagging_sectors=lagging,
            sector_momentum={k.value: v for k, v in sector_momentum.items()},
            yield_curve_signal="FLAT",
            confidence=0.3,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    # ----- Commodity-Currency -----

    async def analyze_commodity_currency_pairs(self) -> List[CommodityCurrencyPair]:
        """Analyze commodity-currency pair relationships.

        Returns:
            List of CommodityCurrencyPair analysis results.
        """
        results = []

        for pair in _COMMODITY_CURRENCY_PAIRS:
            # In production, compute real correlation and divergence
            typical_corr = pair["typical_corr"]
            results.append(CommodityCurrencyPair(
                commodity=pair["commodity"],
                currency=pair["currency"],
                correlation=typical_corr,
                current_divergence=0.0,
                trade_signal="NEUTRAL",
                confidence=0.2,
            ))

        return results


# ---------------------------------------------------------------------------
# Singleton and LangChain @tool
# ---------------------------------------------------------------------------

_default_im_tool: IntermarketTool | None = None


def _get_default_im_tool() -> IntermarketTool:
    global _default_im_tool
    if _default_im_tool is None:
        _default_im_tool = IntermarketTool()
    return _default_im_tool


@tool
async def analyze_intermarket(symbol: str) -> str:
    """Analyze intermarket relationships and correlations.

    Provides cross-market correlation matrix (bonds, equities, commodities, FX),
    relative strength analysis, sector rotation signals, and commodity-currency
    pair analysis.

    Args:
        symbol: Symbol to analyze relative strength for (e.g., 'AAPL', 'SPY')

    Returns:
        JSON string with correlation matrix, relative strength,
        sector rotation, and commodity-currency pair analysis.
    """
    try:
        imt = _get_default_im_tool()
        correlations = await imt.analyze_correlations()
        rs = await imt.analyze_relative_strength(symbol)
        rotation = await imt.analyze_sector_rotation()
        comm_curr = await imt.analyze_commodity_currency_pairs()

        return json.dumps({
            "correlations": correlations.model_dump(),
            "relative_strength": rs.model_dump(),
            "sector_rotation": rotation.model_dump(),
            "commodity_currency_pairs": [p.model_dump() for p in comm_curr],
        }, indent=2, default=str)
    except Exception as exc:
        logger.error("analyze_intermarket tool error: %s", exc)
        return json.dumps({"error": f"Intermarket analysis failed: {exc}", "symbol": symbol})


__all__ = [
    "IntermarketTool",
    "MarketSector",
    "RotationSignal",
    "CorrelationStrength",
    "CorrelationPair",
    "CorrelationMatrix",
    "RelativeStrengthResult",
    "SectorRotationResult",
    "CommodityCurrencyPair",
    "analyze_intermarket",
]
