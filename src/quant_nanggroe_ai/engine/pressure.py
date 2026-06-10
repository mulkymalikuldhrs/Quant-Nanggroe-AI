"""
Pressure Normalization Engine
==============================
From Quant-Nanggroe-AI + HermesQuantOS — Multi-sensor input fusion.

Converts all sensor/agent outputs → BUY_PRESSURE / SELL_PRESSURE.
Normalized to 0.0 - 1.0 scale for deterministic decision synthesis.

Sensor weight allocation (per Blueprint Final):
  - QuantScanner: 25% (Trend/ADX signals)
  - SMCAgent: 30% (Smart Money Concepts)
  - NewsSentinel: 20% (News/sentiment impact)
  - FlowAgent: 25% (Whale/flow signals)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.types import PressureState, VolatilityLevel, LiquidityLevel


class PressureInput(BaseModel):
    """Input data for pressure calculation."""

    # Quant Scanner (25%)
    trend_direction: str = "neutral"  # bullish / bearish / neutral
    trend_strength: float = Field(ge=0.0, le=1.0, default=0.0)

    # SMC Agent (30%)
    smc_signal: str = "none"  # bullish_bos, bearish_bos, bullish_choch, bearish_choch, none
    displacement_strength: float = Field(ge=0.0, le=1.0, default=0.0)
    liquidity_sweep: bool = False

    # News Sentinel (20%)
    news_impact: float = Field(ge=0.0, le=1.0, default=0.0)
    news_uncertainty: float = Field(ge=0.0, le=1.0, default=0.5)

    # Flow Agent (25%)
    flow_direction: str = "neutral"  # long / short / neutral
    flow_imbalance: float = Field(ge=0.0, le=1.0, default=0.0)


class PressureResult(BaseModel):
    """Result of pressure calculation."""

    buy_pressure: float = Field(ge=0.0, le=1.0)
    sell_pressure: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    verdict: str  # STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
    raw_buy: float = 0.0
    raw_sell: float = 0.0
    sensor_inputs: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class PressureNormalizationEngine:
    """
    Compiles all sensor outputs into normalized pressure vectors.

    Weight allocation per Blueprint Final:
    - Quant Scanner: 25% (Trend/ADX)
    - SMC Agent: 30% (Smart Money Concepts)
    - News Sentinel: 20% (News/sentiment)
    - Flow Agent: 25% (Whale/flow)
    """

    SENSOR_WEIGHTS: dict[str, float] = {
        "quant_scanner": 0.25,
        "smc_agent": 0.30,
        "news_sentinel": 0.20,
        "flow_agent": 0.25,
    }

    def __init__(self) -> None:
        self.last_result: PressureResult | None = None

    def compile_pressure(self, inputs: PressureInput) -> PressureResult:
        """
        Compile all sensor outputs into normalized pressure vectors.

        Each sensor contributes proportionally to its weight, modulated
        by the signal strength. Pressures are then normalized to 0.0-1.0.

        Args:
            inputs: PressureInput with all sensor readings

        Returns:
            PressureResult with normalized pressures and verdict
        """
        buy = 0.0
        sell = 0.0

        # ── Quant Scanner contribution (Trend + ADX) — 25% ──────────
        weight = self.SENSOR_WEIGHTS["quant_scanner"]
        if inputs.trend_direction == "bullish":
            buy += weight * inputs.trend_strength
        elif inputs.trend_direction == "bearish":
            sell += weight * inputs.trend_strength

        # ── SMC Agent contribution — 30% ────────────────────────────
        weight = self.SENSOR_WEIGHTS["smc_agent"]
        if inputs.smc_signal in ("bullish_bos", "bullish_choch"):
            buy += weight * inputs.displacement_strength
        elif inputs.smc_signal in ("bearish_bos", "bearish_choch"):
            sell += weight * inputs.displacement_strength

        if inputs.liquidity_sweep:
            # Liquidity sweep adds to both sides (displacement direction unknown)
            buy += weight * 0.2 * inputs.displacement_strength
            sell += weight * 0.2 * inputs.displacement_strength

        # ── News Sentinel contribution — 20% ────────────────────────
        weight = self.SENSOR_WEIGHTS["news_sentinel"]
        directional_factor = 1.0 - inputs.news_uncertainty
        buy += weight * inputs.news_impact * directional_factor
        sell += weight * inputs.news_impact * inputs.news_uncertainty

        # ── Flow Agent contribution (Whale/COT) — 25% ──────────────
        weight = self.SENSOR_WEIGHTS["flow_agent"]
        if inputs.flow_direction == "long":
            buy += weight * inputs.flow_imbalance
        elif inputs.flow_direction == "short":
            sell += weight * inputs.flow_imbalance

        # ── Normalize pressures to 0.0 - 1.0 ───────────────────────
        total = buy + sell
        if total > 0:
            buy_pressure = buy / total
            sell_pressure = sell / total
            confidence = max(buy, sell) / total
        else:
            buy_pressure = 0.0
            sell_pressure = 0.0
            confidence = 0.0

        # ── Determine verdict ───────────────────────────────────────
        if buy_pressure > 0.70:
            verdict = "STRONG_BUY"
        elif buy_pressure > 0.55:
            verdict = "BUY"
        elif sell_pressure > 0.70:
            verdict = "STRONG_SELL"
        elif sell_pressure > 0.55:
            verdict = "SELL"
        else:
            verdict = "NEUTRAL"

        result = PressureResult(
            buy_pressure=round(buy_pressure, 4),
            sell_pressure=round(sell_pressure, 4),
            confidence=round(confidence, 4),
            verdict=verdict,
            raw_buy=round(buy, 4),
            raw_sell=round(sell, 4),
            sensor_inputs={
                "trend": f"{inputs.trend_direction} ({inputs.trend_strength:.2f})",
                "smc": inputs.smc_signal,
                "displacement": f"{inputs.displacement_strength:.2f}",
                "liquidity_sweep": inputs.liquidity_sweep,
                "news_impact": f"{inputs.news_impact:.2f}",
                "flow": f"{inputs.flow_direction} ({inputs.flow_imbalance:.2f})",
            },
        )

        self.last_result = result
        return result

    def get_pressure(self) -> PressureResult | None:
        """Get current pressure state."""
        return self.last_result

    def get_pressure_state(self) -> PressureState:
        """Get current pressure as a PressureState model."""
        if self.last_result:
            return PressureState(
                buy_pressure=self.last_result.buy_pressure,
                sell_pressure=self.last_result.sell_pressure,
                confidence_score=self.last_result.confidence,
            )
        return PressureState()
