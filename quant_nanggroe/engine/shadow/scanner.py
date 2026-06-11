"""Market Scanner — Scan for strategy opportunities.

Scans market data for strategy opportunities, backtests candidate
strategies, and ranks them by expected performance.

Ported from Vibe-Trading/agent/src/shadow_account/scanner.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result from a market scan."""

    symbol: str
    score: float
    signal: str  # 'bullish', 'bearish', 'neutral'
    strategy_match: str
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanConfig:
    """Configuration for market scanning."""

    min_score: float = 0.3
    max_results: int = 20
    lookback_periods: Tuple[int, ...] = (5, 10, 20, 50)
    volume_threshold: float = 1.5  # Volume ratio threshold
    momentum_threshold: float = 0.02  # 2% momentum threshold
    volatility_window: int = 20


class MarketScanner:
    """Market Scanner.

    Scans market data for trading opportunities by analyzing:
    - Trend strength and direction
    - Volume anomalies
    - Volatility regimes
    - Support/resistance proximity
    - Momentum signals

    Ported from Vibe-Trading/agent/src/shadow_account/scanner.py
    """

    def __init__(self, config: Optional[ScanConfig] = None) -> None:
        self._config = config or ScanConfig()

    def scan(
        self,
        data: Dict[str, pd.DataFrame],
        strategies: Optional[List[str]] = None,
    ) -> List[ScanResult]:
        """Scan market data for opportunities.

        Args:
            data: Dict mapping symbol -> OHLCV DataFrame.
            strategies: Optional list of strategy names to match.

        Returns:
            List of ScanResult sorted by score (descending).
        """
        results = []

        for symbol, df in data.items():
            if df.empty or len(df) < self._config.lookback_periods[-1]:
                continue

            try:
                result = self._scan_symbol(symbol, df, strategies)
                if result and result.score >= self._config.min_score:
                    results.append(result)
            except Exception as exc:
                logger.warning("Scan failed for %s: %s", symbol, exc)

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: self._config.max_results]

    def _scan_symbol(
        self,
        symbol: str,
        df: pd.DataFrame,
        strategies: Optional[List[str]] = None,
    ) -> Optional[ScanResult]:
        """Scan a single symbol for opportunities."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"] if "volume" in df.columns else pd.Series(np.ones(len(df)), index=df.index)

        # Calculate metrics
        momentum_score = self._calc_momentum(close)
        volume_score = self._calc_volume_anomaly(volume)
        volatility_score = self._calc_volatility_regime(close)
        sr_score = self._calc_support_resistance(high, low, close)
        trend_score = self._calc_trend_strength(close)

        # Composite score
        composite = (
            momentum_score * 0.25
            + volume_score * 0.20
            + volatility_score * 0.15
            + sr_score * 0.20
            + trend_score * 0.20
        )

        # Determine signal direction
        if momentum_score > 0 and trend_score > 0:
            signal = "bullish"
        elif momentum_score < 0 and trend_score < 0:
            signal = "bearish"
        else:
            signal = "neutral"

        # Determine strategy match
        strategy_match = self._match_strategy(
            momentum_score, volume_score, volatility_score, sr_score, trend_score, strategies
        )

        # Confidence
        confidence = min(1.0, abs(composite) * 0.5 + 0.3)

        return ScanResult(
            symbol=symbol,
            score=composite,
            signal=signal,
            strategy_match=strategy_match,
            confidence=confidence,
            details={
                "momentum_score": momentum_score,
                "volume_score": volume_score,
                "volatility_score": volatility_score,
                "sr_score": sr_score,
                "trend_score": trend_score,
            },
        )

    def _calc_momentum(self, close: pd.Series) -> float:
        """Calculate momentum score (-1 to 1)."""
        if len(close) < 20:
            return 0.0

        # Multi-timeframe momentum
        mom_5d = float(close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 5 else 0
        mom_20d = float(close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else 0

        score = (mom_5d * 0.6 + mom_20d * 0.4)
        return max(-1.0, min(1.0, score / self._config.momentum_threshold))

    def _calc_volume_anomaly(self, volume: pd.Series) -> float:
        """Calculate volume anomaly score (-1 to 1)."""
        if len(volume) < 20:
            return 0.0

        vol_ma = float(volume.rolling(20, min_periods=20).mean().iloc[-1])
        current_vol = float(volume.iloc[-1])

        if vol_ma == 0:
            return 0.0

        ratio = current_vol / vol_ma
        if ratio > self._config.volume_threshold:
            return min(1.0, (ratio - 1) / 2)
        elif ratio < 1 / self._config.volume_threshold:
            return max(-1.0, -(1 - ratio) / 2)
        return 0.0

    def _calc_volatility_regime(self, close: pd.Series) -> float:
        """Calculate volatility regime score (0 to 1, higher = more volatile)."""
        if len(close) < 20:
            return 0.0

        returns = close.pct_change().dropna()
        vol = float(returns.rolling(20, min_periods=20).std().iloc[-1])

        # Normalize: annualized vol > 40% is high, < 15% is low
        annual_vol = vol * np.sqrt(252)
        if annual_vol > 0.40:
            return 1.0
        elif annual_vol < 0.15:
            return 0.2
        else:
            return 0.5 + (annual_vol - 0.15) / 0.25 * 0.5

    def _calc_support_resistance(self, high: pd.Series, low: pd.Series, close: pd.Series) -> float:
        """Calculate proximity to support/resistance (-1 to 1)."""
        if len(close) < 20:
            return 0.0

        recent_high = float(high.iloc[-20:].max())
        recent_low = float(low.iloc[-20:].min())
        current = float(close.iloc[-1])

        range_val = recent_high - recent_low
        if range_val == 0:
            return 0.0

        position = (current - recent_low) / range_val

        # Near support = bullish (+), near resistance = bearish (-)
        if position < 0.3:
            return 1.0 - position  # Strong buy near support
        elif position > 0.7:
            return -(position)  # Sell near resistance
        return 0.0

    def _calc_trend_strength(self, close: pd.Series) -> float:
        """Calculate trend strength (-1 to 1)."""
        if len(close) < 50:
            return 0.0

        # SMA crossover
        sma_10 = float(close.rolling(10, min_periods=10).mean().iloc[-1])
        sma_50 = float(close.rolling(50, min_periods=50).mean().iloc[-1]) if len(close) >= 50 else sma_10

        if sma_50 == 0:
            return 0.0

        return max(-1.0, min(1.0, (sma_10 - sma_50) / sma_50 * 10))

    def _match_strategy(
        self,
        momentum: float,
        volume: float,
        volatility: float,
        sr: float,
        trend: float,
        strategies: Optional[List[str]] = None,
    ) -> str:
        """Match scan result to a strategy type."""
        if strategies and len(strategies) > 0:
            return strategies[0]

        if momentum > 0.5 and trend > 0.3:
            return "momentum"
        elif abs(momentum) < 0.2 and volatility > 0.5:
            return "breakout"
        elif sr > 0.5:
            return "mean_reversion"
        elif volume > 0.5:
            return "volume_profile"
        else:
            return "general"
