"""
Market State Engine — Regime Detection
=======================================
From HermesQuantOS + Quant-Nanggroe-AI — Enhanced for multi-timeframe analysis.

Deterministic classification based on ADX, RSI, price change, volume, and ATR.
If regime is NO_TRADE → the entire system must stop.

Regimes: TRENDING_UP, TRENDING_DOWN, TRENDING, RANGE, MEAN_REVERT,
         RISK_OFF, PANIC, NO_TRADE, CALM, VOLATILE
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.types import (
    MarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    MarketState,
)


class MarketStateResult(BaseModel):
    """Result of market state detection."""

    symbol: str
    regime: MarketRegime
    base_regime: MarketRegime  # Before NO_TRADE override
    volatility: VolatilityLevel
    liquidity: LiquidityLevel
    no_trade_reasons: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    trade_allowed: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class MarketStateEngine:
    """
    Determines current market regime for decision gating.

    If NO_TRADE → entire system stops. No agent can override this.
    Multi-timeframe analysis considers both short-term and long-term context.

    Source: Best of HermesQuantOS (Python) + Quant-Nanggroe-AI (TypeScript).
    """

    # Regime detection thresholds
    PANIC_THRESHOLD = -5.0       # 5% drop triggers PANIC
    RISK_OFF_THRESHOLD = -2.0    # 2% drop triggers RISK_OFF
    TRENDING_ADX_THRESHOLD = 25  # ADX > 25 indicates trend
    MEAN_REVERT_RSI_HIGH = 75    # RSI > 75
    MEAN_REVERT_RSI_LOW = 25     # RSI < 25

    # Volatility thresholds
    HIGH_VOL_ATR_PCT = 2.5      # ATR > 2.5% of price
    LOW_VOL_ATR_PCT = 0.5       # ATR < 0.5% of price

    # Liquidity thresholds
    THIN_LIQUIDITY_RATIO = 0.4   # Volume < 40% of average
    DEEP_LIQUIDITY_RATIO = 1.8   # Volume > 180% of average

    def __init__(self) -> None:
        self.current_regime: MarketRegime = MarketRegime.UNKNOWN
        self.regime_history: list[MarketStateResult] = []

    def detect_regime(
        self,
        symbol: str = "XAUUSD",
        price_change_5d: float = 0.0,
        price_change_1d: float = 0.0,
        adx: float = 20.0,
        rsi: float = 50.0,
        atr_pct: float = 1.0,
        volume_ratio: float = 1.0,
        ema_trend: str = "neutral",  # bullish / bearish / neutral
    ) -> MarketStateResult:
        """
        Deterministic regime classification.

        Priority order (highest to lowest):
        1. PANIC — Extreme sell-off (> 5% in 5 days)
        2. RISK_OFF — Significant decline (> 2% in 5 days)
        3. TRENDING_UP / TRENDING_DOWN — ADX > 25 with EMA direction
        4. MEAN_REVERT — RSI at extremes
        5. RANGE — Default when no other regime detected

        NO_TRADE override conditions:
        - PANIC regime
        - High volatility + thin liquidity
        - Extremely low volume

        Args:
            symbol: Trading symbol
            price_change_5d: 5-day price change percentage
            price_change_1d: 1-day price change percentage
            adx: Average Directional Index value
            rsi: RSI(14) value
            atr_pct: ATR as percentage of price
            volume_ratio: Current volume / average volume
            ema_trend: EMA trend direction

        Returns:
            MarketStateResult with regime classification
        """
        # ── Regime determination (priority order) ────────────────────
        if price_change_5d < self.PANIC_THRESHOLD:
            regime = MarketRegime.PANIC
        elif price_change_5d < self.RISK_OFF_THRESHOLD:
            regime = MarketRegime.RISK_OFF
        elif adx > self.TRENDING_ADX_THRESHOLD:
            if ema_trend == "bullish" or price_change_1d > 0.5:
                regime = MarketRegime.TRENDING_UP
            elif ema_trend == "bearish" or price_change_1d < -0.5:
                regime = MarketRegime.TRENDING_DOWN
            else:
                regime = MarketRegime.TRENDING
        elif rsi > self.MEAN_REVERT_RSI_HIGH or rsi < self.MEAN_REVERT_RSI_LOW:
            regime = MarketRegime.MEAN_REVERT
        elif atr_pct < self.LOW_VOL_ATR_PCT and volume_ratio < self.THIN_LIQUIDITY_RATIO:
            regime = MarketRegime.CALM
        elif atr_pct > self.HIGH_VOL_ATR_PCT:
            regime = MarketRegime.VOLATILE
        else:
            regime = MarketRegime.RANGE

        # ── Volatility classification ────────────────────────────────
        if atr_pct > self.HIGH_VOL_ATR_PCT:
            volatility = VolatilityLevel.HIGH
        elif atr_pct < self.LOW_VOL_ATR_PCT:
            volatility = VolatilityLevel.LOW
        else:
            volatility = VolatilityLevel.NORMAL

        # ── Liquidity classification ─────────────────────────────────
        if volume_ratio < self.THIN_LIQUIDITY_RATIO:
            liquidity = LiquidityLevel.THIN
        elif volume_ratio > self.DEEP_LIQUIDITY_RATIO:
            liquidity = LiquidityLevel.DEEP
        else:
            liquidity = LiquidityLevel.NORMAL

        # ── NO_TRADE override conditions ─────────────────────────────
        no_trade_reasons: list[str] = []
        if regime == MarketRegime.PANIC:
            no_trade_reasons.append("Panic regime — extreme sell-off")
        if volatility == VolatilityLevel.HIGH and liquidity == LiquidityLevel.THIN:
            no_trade_reasons.append("High volatility + thin liquidity = dangerous")
        if volume_ratio < 0.2:
            no_trade_reasons.append("Extremely low volume — no liquidity")

        final_regime = MarketRegime.NO_TRADE if no_trade_reasons else regime

        result = MarketStateResult(
            symbol=symbol,
            regime=final_regime,
            base_regime=regime,
            volatility=volatility,
            liquidity=liquidity,
            no_trade_reasons=no_trade_reasons,
            inputs={
                "price_change_5d": f"{price_change_5d:.2f}%",
                "price_change_1d": f"{price_change_1d:.2f}%",
                "adx": round(adx, 2),
                "rsi": round(rsi, 2),
                "atr_pct": f"{atr_pct:.2f}%",
                "volume_ratio": f"{volume_ratio:.2f}x",
                "ema_trend": ema_trend,
            },
            trade_allowed=final_regime
            not in {MarketRegime.PANIC, MarketRegime.RISK_OFF, MarketRegime.NO_TRADE},
        )

        self.current_regime = final_regime
        self.regime_history.append(result)

        # Keep last 100 regime checks
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]

        return result

    def get_regime(self) -> MarketRegime:
        """Get current regime."""
        return self.current_regime

    def get_market_state(self) -> MarketState:
        """Get current market state as a MarketState model."""
        if self.regime_history:
            latest = self.regime_history[-1]
            return MarketState(
                regime=latest.regime,
                volatility=latest.volatility,
                liquidity=latest.liquidity,
                timestamp=latest.timestamp,
            )
        return MarketState(regime=MarketRegime.UNKNOWN)
