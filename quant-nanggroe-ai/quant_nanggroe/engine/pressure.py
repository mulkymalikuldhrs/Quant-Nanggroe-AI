"""Pressure normalization engine.

Converts all agent sensor outputs into numerical pressures (0.0–1.0)
with configurable weights. Based on Quant-Nanggroe-AI's
PressureNormalizationEngine and the Blueprint Final specification.

Weight allocation per Blueprint Final:
- QuantScanner: 25%
- SMCAgent: 30%
- NewsSentinel: 20%
- FlowAgent: 25%

The engine is deterministic — given the same inputs, it always produces
the same output. This is critical for backtesting and audit trails.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from quant_nanggroe.config.settings import get_settings
from quant_nanggroe.types.decisions import (
    LiquidityLevel,
    MarketRegime,
    PressureState,
    VolatilityLevel,
)

logger = logging.getLogger("quant_nanggroe.engine.pressure")


@dataclass(frozen=True)
class QuantScannerOutput:
    """Output from the Quant Scanner (technical analysis) agent."""

    trend_strength: float  # 0.0–1.0
    structure_state: str  # "BULL", "BEAR", "NEUTRAL"
    volatility_expansion: bool


@dataclass(frozen=True)
class SMCOutput:
    """Output from the Smart Money Concepts agent."""

    liquidity_sweep: bool
    displacement_strength: float  # 0.0–1.0
    sweep_direction: str  # "HIGH", "LOW", "NONE"
    poi_validity: float  # 0.0–1.0


@dataclass(frozen=True)
class NewsSentinelOutput:
    """Output from the News Sentinel (macro/sentiment) agent."""

    event_type: str  # "MACRO", "SCHEDULED", "SHOCK", "NOISE"
    impact_score: float  # 0.0–1.0
    directional_uncertainty: float  # 0.0–1.0
    sentiment_bias: float  # -1.0 (bearish) to 1.0 (bullish)
    time_decay: float  # seconds


@dataclass(frozen=True)
class FlowWhaleOutput:
    """Output from the Flow/Whale tracking agent."""

    positioning_bias: str  # "LONG", "SHORT", "NEUTRAL"
    flow_imbalance: float  # 0.0–1.0
    net_flow: float  # absolute net flow value


class PressureNormalizationEngine:
    """Pressure Normalization Engine — converts sensor outputs to pressures.

    Algorithm:
    1. Each sensor contributes weighted pressure to buy or sell side
    2. Pressures are normalized to sum to 1.0
    3. Confidence score is the maximum directional pressure
    4. If market regime is NO_TRADE, all pressures are zeroed

    This engine is deterministic. Same inputs → same outputs.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._weight_quant = settings.weight_quant_scanner
        self._weight_smc = settings.weight_smc_agent
        self._weight_news = settings.weight_news_sentinel
        self._weight_flow = settings.weight_flow_agent

        # Validate weights sum to 1.0
        total = self._weight_quant + self._weight_smc + self._weight_news + self._weight_flow
        if abs(total - 1.0) > 0.01:
            logger.warning(
                f"Pressure weights sum to {total:.2f}, expected 1.0. Normalizing."
            )
            self._weight_quant /= total
            self._weight_smc /= total
            self._weight_news /= total
            self._weight_flow /= total

    def normalize(
        self,
        regime: MarketRegime,
        volatility: VolatilityLevel,
        liquidity: LiquidityLevel,
        quant: Optional[QuantScannerOutput] = None,
        smc: Optional[SMCOutput] = None,
        news: Optional[NewsSentinelOutput] = None,
        flow: Optional[FlowWhaleOutput] = None,
    ) -> PressureState:
        """Normalize all agent outputs into a unified pressure state.

        Args:
            regime: Current market regime from MarketStateEngine.
            volatility: Current volatility level.
            liquidity: Current liquidity level.
            quant: Quant Scanner output (technical analysis).
            smc: SMC Agent output (smart money concepts).
            news: News Sentinel output (macro/sentiment).
            flow: Flow Agent output (whale tracking).

        Returns:
            PressureState with normalized buy/sell pressures and confidence.
        """
        # If regime is NO_TRADE, zero out all pressures
        if regime == MarketRegime.NO_TRADE:
            return PressureState(
                buy_pressure=0.0,
                sell_pressure=0.0,
                volatility_risk=volatility,
                liquidity_condition=liquidity,
                confidence_score=0.0,
            )

        buy_pressure = 0.0
        sell_pressure = 0.0

        # 1. Quant Scanner Influence (Technical) — 25%
        if quant is not None:
            if quant.structure_state == "BULL":
                buy_pressure += self._weight_quant * quant.trend_strength
            elif quant.structure_state == "BEAR":
                sell_pressure += self._weight_quant * quant.trend_strength

        # 2. SMC Influence (Liquidity / Smart Money) — 30%
        if smc is not None and smc.liquidity_sweep:
            # Sweep direction determines pressure direction
            # Sweep HIGH (took out highs) → bearish reversal → sell pressure
            # Sweep LOW (took out lows) → bullish reversal → buy pressure
            if smc.sweep_direction == "LOW":
                buy_pressure += self._weight_smc * smc.displacement_strength
            elif smc.sweep_direction == "HIGH":
                sell_pressure += self._weight_smc * smc.displacement_strength

        # 3. News Sentinel Influence (Macro/Sentiment) — 20%
        if news is not None and news.impact_score > 0.3:
            # Use sentiment_bias for direction, impact_score for magnitude
            # Reduce by directional uncertainty
            directionality = 1.0 - news.directional_uncertainty
            impact = news.impact_score * directionality

            if news.sentiment_bias > 0:
                buy_pressure += self._weight_news * impact * abs(news.sentiment_bias)
            elif news.sentiment_bias < 0:
                sell_pressure += self._weight_news * impact * abs(news.sentiment_bias)

        # 4. Flow Influences (Whales) — 25%
        if flow is not None:
            if flow.positioning_bias == "LONG":
                buy_pressure += self._weight_flow * flow.flow_imbalance
            elif flow.positioning_bias == "SHORT":
                sell_pressure += self._weight_flow * flow.flow_imbalance

        # 5. Volatility risk adjustment
        # In high volatility, reduce pressures (less confident)
        if volatility == VolatilityLevel.HIGH:
            buy_pressure *= 0.7
            sell_pressure *= 0.7

        # 6. Liquidity adjustment
        # In thin liquidity, reduce pressures (harder to execute)
        if liquidity == LiquidityLevel.THIN:
            buy_pressure *= 0.5
            sell_pressure *= 0.5

        # 7. Normalization — pressures should sum to <= 1.0
        total = buy_pressure + sell_pressure
        if total > 1.0:
            buy_pressure /= total
            sell_pressure /= total
        elif total == 0:
            # No directional signal
            buy_pressure = 0.0
            sell_pressure = 0.0

        # 8. Confidence score — how aligned are the signals?
        # Maximum directional pressure = confidence
        confidence_score = max(buy_pressure, sell_pressure)

        state = PressureState(
            buy_pressure=round(buy_pressure, 4),
            sell_pressure=round(sell_pressure, 4),
            volatility_risk=volatility,
            liquidity_condition=liquidity,
            confidence_score=round(confidence_score, 4),
        )

        logger.info(
            f"Pressure: buy={buy_pressure:.3f}, sell={sell_pressure:.3f}, "
            f"confidence={confidence_score:.3f}, regime={regime.value}"
        )

        return state
