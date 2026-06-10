"""Market regime detection engine.

Classifies the current market state into one of six regimes:
TRENDING, RANGE, MEAN_REVERT, RISK_OFF, PANIC, NO_TRADE.

Based on Quant-Nanggroe-AI's MarketStateEngine (ADX+RSI+price-drop)
but with the CRITICAL improvement of using properly implemented
Wilder's Smoothing for ADX instead of the SMA proxy.

The regime is the highest-level filter in the system. If the output
is NO_TRADE, all agents must remain idle — no exceptions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from quant_nanggroe.engine.indicators import TechnicalIndicators
from quant_nanggroe.types.decisions import (
    LiquidityLevel,
    MarketRegime,
    VolatilityLevel,
)
from quant_nanggroe.config.settings import get_settings

logger = logging.getLogger("quant_nanggroe.engine.market_state")


@dataclass(frozen=True)
class MarketState:
    """Complete market state analysis result.

    Combines regime, volatility, and liquidity classifications
    into a single state object used by the decision synthesis engine.
    """

    regime: MarketRegime
    volatility: VolatilityLevel
    liquidity: LiquidityLevel
    adx: float
    rsi: float
    atr_pct: float
    volume_ratio: float
    timestamp: float = 0.0


class MarketStateEngine:
    """MASTER REGIME ENGINE — Located above all agents.

    If output is NO_TRADE, all agents must remain idle.

    Algorithm:
    1. Require minimum candle count (default 50)
    2. Classify regime using ADX, RSI, and price-drop detection
       - ADX > threshold → TRENDING
       - RSI extreme (>70 or <30) with low ADX → MEAN_REVERT
       - Price drop > panic threshold → PANIC
       - Price drop > risk-off threshold → RISK_OFF
       - Otherwise → RANGE
    3. Classify volatility using ATR percentage
    4. Classify liquidity using volume ratio

    All thresholds are configurable via Settings.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._min_candles = settings.market_state_min_candles
        self._adx_trending = settings.adx_trending_threshold
        self._panic_drop = settings.panic_drop_threshold
        self._risk_off_drop = settings.risk_off_drop_threshold
        self._atr_high_pct = settings.atr_high_volatility_pct
        self._atr_low_pct = settings.atr_low_volatility_pct

    def analyze(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: Optional[np.ndarray] = None,
    ) -> MarketState:
        """Analyze market state from OHLCV data.

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            volumes: Volume series (optional, for liquidity classification).

        Returns:
            MarketState with regime, volatility, and liquidity classifications.
        """
        import time as _time

        h = np.asarray(highs, dtype=float)
        l = np.asarray(lows, dtype=float)
        c = np.asarray(closes, dtype=float)
        v = np.asarray(volumes, dtype=float) if volumes is not None else None

        # 1. Minimum data check
        if len(c) < self._min_candles:
            logger.warning(
                f"Insufficient candles for market state analysis: {len(c)} < {self._min_candles}"
            )
            return MarketState(
                regime=MarketRegime.NO_TRADE,
                volatility=VolatilityLevel.NORMAL,
                liquidity=LiquidityLevel.NORMAL,
                adx=0.0,
                rsi=50.0,
                atr_pct=0.0,
                volume_ratio=1.0,
                timestamp=_time.time(),
            )

        # 2. Regime Detection (Deterministic)
        adx_result = TechnicalIndicators.adx(h, l, c)
        rsi_value = TechnicalIndicators.rsi(c)

        regime = self._classify_regime(c, adx_result.adx, rsi_value)

        # 3. Volatility Classification (ATR-based)
        atr_value = TechnicalIndicators.atr(h, l, c)
        last_price = float(c[-1])
        atr_pct = (atr_value / last_price * 100) if last_price > 0 else 0.0

        volatility = self._classify_volatility(atr_pct)

        # 4. Liquidity Classification (Volume-based)
        volume_ratio = 1.0
        if v is not None and len(v) > 0:
            avg_vol = float(np.mean(v))
            last_vol = float(v[-1])
            if avg_vol > 0:
                volume_ratio = last_vol / avg_vol

        liquidity = self._classify_liquidity(volume_ratio)

        state = MarketState(
            regime=regime,
            volatility=volatility,
            liquidity=liquidity,
            adx=adx_result.adx,
            rsi=rsi_value,
            atr_pct=atr_pct,
            volume_ratio=volume_ratio,
            timestamp=_time.time(),
        )

        logger.info(
            f"Market State: regime={regime.value}, vol={volatility.value}, "
            f"liq={liquidity.value}, ADX={adx_result.adx:.1f}, RSI={rsi_value:.1f}"
        )

        return state

    def _classify_regime(
        self,
        closes: np.ndarray,
        adx_value: float,
        rsi_value: float,
    ) -> MarketRegime:
        """Classify market regime from ADX, RSI, and price drop.

        Priority order:
        1. PANIC (fast drop > threshold)
        2. RISK_OFF (moderate drop > threshold)
        3. TRENDING (ADX > threshold)
        4. MEAN_REVERT (RSI extreme with low ADX)
        5. RANGE (default)
        """
        last_price = float(closes[-1])

        # Check price drop (fast crash detection)
        # Use 5-candle lookback for crash detection
        lookback = min(5, len(closes) - 1)
        if lookback > 0:
            ref_price = float(closes[-(lookback + 1)])
            if ref_price > 0:
                price_change = (last_price - ref_price) / ref_price

                if price_change < self._panic_drop:
                    return MarketRegime.PANIC
                if price_change < self._risk_off_drop:
                    return MarketRegime.RISK_OFF

        # Trending vs Range (ADX-based)
        if adx_value > self._adx_trending:
            return MarketRegime.TRENDING

        # Mean Revert (RSI extremes with low ADX)
        if rsi_value > 70 or rsi_value < 30:
            return MarketRegime.MEAN_REVERT

        # Default: Range-bound market
        return MarketRegime.RANGE

    @staticmethod
    def _classify_volatility(atr_pct: float) -> VolatilityLevel:
        """Classify volatility from ATR percentage."""
        settings = get_settings()
        if atr_pct > settings.atr_high_volatility_pct:
            return VolatilityLevel.HIGH
        if atr_pct < settings.atr_low_volatility_pct:
            return VolatilityLevel.LOW
        return VolatilityLevel.NORMAL

    @staticmethod
    def _classify_liquidity(volume_ratio: float) -> LiquidityLevel:
        """Classify liquidity from volume ratio (current vs average)."""
        if volume_ratio < 0.4:
            return LiquidityLevel.THIN
        if volume_ratio > 1.8:
            return LiquidityLevel.DEEP
        return LiquidityLevel.NORMAL
