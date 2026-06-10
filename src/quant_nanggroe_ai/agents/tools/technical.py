"""
Technical Analysis Tool — Full Indicator Suite for Agents
==========================================================
Wraps MathEngine.analyze_sequence() and augments the result with
Smart Money Concepts (SMC) signals, trend classification, computed
fields (EMA trend, trend strength, price changes, volume ratio),
and support/resistance level detection.

All calculations are 100% deterministic — no AI, no approximation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from quant_nanggroe_ai.engine.math_lib import MathEngine
from quant_nanggroe_ai.exceptions import DataError, InsufficientDataError

logger = logging.getLogger(__name__)

# Minimum bars needed for a meaningful full analysis
_MIN_BARS = 50


class _SMCDetector:
    """
    Smart Money Concepts detector — BOS & CHoCH from swing pivots.

    This is a deterministic implementation that identifies:
      - Break of Structure (BOS): Price breaks a previous swing in the
        direction of the prevailing trend → trend continuation signal.
      - Change of Character (CHoCH): Price breaks a previous swing
        *against* the prevailing trend → trend reversal signal.

    The algorithm works on swing highs/lows with a configurable lookback.
    """

    @staticmethod
    def detect(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        lookback: int = 5,
    ) -> dict[str, Any]:
        """
        Detect SMC signals from OHLC data.

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            lookback: Swing pivot lookback period (default 5).

        Returns:
            Dict with 'signals' list, 'latest_signal', 'structure_state'.
        """
        n = len(closes)
        if n < lookback * 2 + 1:
            return {
                "signals": [],
                "latest_signal": None,
                "structure_state": "NEUTRAL",
            }

        # Step 1: Identify swing highs and lows
        swing_highs: list[tuple[int, float]] = []
        swing_lows: list[tuple[int, float]] = []

        for i in range(lookback, n - lookback):
            is_high = all(highs[i] >= highs[i - j] for j in range(1, lookback + 1)) and \
                      all(highs[i] >= highs[i + j] for j in range(1, lookback + 1))
            is_low = all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)) and \
                     all(lows[i] <= lows[i + j] for j in range(1, lookback + 1))

            if is_high:
                swing_highs.append((i, highs[i]))
            if is_low:
                swing_lows.append((i, lows[i]))

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {
                "signals": [],
                "latest_signal": None,
                "structure_state": "NEUTRAL",
            }

        # Step 2: Determine trend from swing structure
        higher_highs = sum(
            1 for i in range(1, len(swing_highs))
            if swing_highs[i][1] > swing_highs[i - 1][1]
        )
        higher_lows = sum(
            1 for i in range(1, len(swing_lows))
            if swing_lows[i][1] > swing_lows[i - 1][1]
        )

        bull_swings = higher_highs + higher_lows
        bear_swings = (len(swing_highs) - 1 - higher_highs) + (len(swing_lows) - 1 - higher_lows)

        is_bullish_trend = bull_swings > bear_swings

        # Step 3: Detect BOS and CHoCH
        signals: list[dict[str, Any]] = []

        # Check last close against recent swing levels
        last_close = closes[-1]
        recent_swing_high = swing_highs[-1]
        recent_swing_low = swing_lows[-1]

        if last_close > recent_swing_high[1]:
            if is_bullish_trend:
                signals.append({
                    "type": "BOS",
                    "direction": "BULL",
                    "level": recent_swing_high[1],
                    "bar_index": n - 1,
                    "description": "Break of Structure — bullish continuation above swing high",
                })
            else:
                signals.append({
                    "type": "CHoCH",
                    "direction": "BULL",
                    "level": recent_swing_high[1],
                    "bar_index": n - 1,
                    "description": "Change of Character — bearish to bullish reversal above swing high",
                })

        if last_close < recent_swing_low[1]:
            if not is_bullish_trend:
                signals.append({
                    "type": "BOS",
                    "direction": "BEAR",
                    "level": recent_swing_low[1],
                    "bar_index": n - 1,
                    "description": "Break of Structure — bearish continuation below swing low",
                })
            else:
                signals.append({
                    "type": "CHoCH",
                    "direction": "BEAR",
                    "level": recent_swing_low[1],
                    "bar_index": n - 1,
                    "description": "Change of Character — bullish to bearish reversal below swing low",
                })

        latest_signal = signals[-1] if signals else None
        structure_state = "BULL" if is_bullish_trend else "BEAR" if bear_swings > bull_swings else "NEUTRAL"

        return {
            "signals": signals,
            "latest_signal": latest_signal,
            "structure_state": structure_state,
            "swing_highs": [{"bar": idx, "price": price} for idx, price in swing_highs[-5:]],
            "swing_lows": [{"bar": idx, "price": price} for idx, price in swing_lows[-5:]],
        }


class _SupportResistanceDetector:
    """
    Support and resistance level detection using swing pivot clustering.

    Groups nearby swing levels into zones and ranks them by the number
    of times price has reacted from each zone.
    """

    @staticmethod
    def detect(
        highs: list[float],
        lows: list[float],
        closes: list[float],
        lookback: int = 5,
        tolerance_pct: float = 0.005,
    ) -> dict[str, Any]:
        """
        Detect support and resistance levels.

        Args:
            highs: High price series.
            lows: Low price series.
            closes: Close price series.
            lookback: Pivot lookback period.
            tolerance_pct: Clustering tolerance as percentage.

        Returns:
            Dict with 'support_levels', 'resistance_levels', 'nearest_support', 'nearest_resistance'.
        """
        n = len(closes)
        if n < lookback * 2 + 1:
            return {
                "support_levels": [],
                "resistance_levels": [],
                "nearest_support": None,
                "nearest_resistance": None,
            }

        # Collect pivot points
        pivot_highs: list[float] = []
        pivot_lows: list[float] = []

        for i in range(lookback, n - lookback):
            if all(highs[i] >= highs[i - j] for j in range(1, lookback + 1)):
                pivot_highs.append(highs[i])
            if all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)):
                pivot_lows.append(lows[i])

        # Cluster into levels
        resistance_levels = _SupportResistanceDetector._cluster_levels(
            pivot_highs, tolerance_pct
        )
        support_levels = _SupportResistanceDetector._cluster_levels(
            pivot_lows, tolerance_pct
        )

        # Find nearest levels to current price
        current = closes[-1]
        nearest_support = None
        nearest_resistance = None

        below_price = [s for s in support_levels if s["price"] < current]
        above_price = [r for r in resistance_levels if r["price"] > current]

        if below_price:
            nearest = max(below_price, key=lambda s: s["price"])
            nearest_support = nearest
        if above_price:
            nearest = min(above_price, key=lambda r: r["price"])
            nearest_resistance = nearest

        return {
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
        }

    @staticmethod
    def _cluster_levels(
        levels: list[float], tolerance_pct: float
    ) -> list[dict[str, Any]]:
        """Cluster nearby price levels into zones."""
        if not levels:
            return []

        sorted_levels = sorted(levels)
        clusters: list[list[float]] = [[sorted_levels[0]]]

        for level in sorted_levels[1:]:
            cluster_avg = sum(clusters[-1]) / len(clusters[-1])
            if abs(level - cluster_avg) / cluster_avg <= tolerance_pct:
                clusters[-1].append(level)
            else:
                clusters.append([level])

        result: list[dict[str, Any]] = []
        for cluster in clusters:
            avg_price = sum(cluster) / len(cluster)
            result.append({
                "price": round(avg_price, 6),
                "touches": len(cluster),
                "strength": min(len(cluster) / 5.0, 1.0),  # Normalized 0-1
            })

        return sorted(result, key=lambda x: x["touches"], reverse=True)


class TechnicalAnalysisTool:
    """
    Full technical analysis tool for agent consumption.

    Combines MathEngine's deterministic indicator calculations with
    Smart Money Concepts detection, trend classification, support/
    resistance levels, and computed derivative fields.

    Usage::

        tool = TechnicalAnalysisTool(market_data_tool=mdt)
        result = await tool.analyze("AAPL", "1d")
        print(result["trend"]["direction"])  # "BULL" | "BEAR" | "NEUTRAL"
    """

    def __init__(self, market_data_tool: Any | None = None) -> None:
        """
        Initialize the TechnicalAnalysisTool.

        Args:
            market_data_tool: Optional MarketDataTool instance for
                auto-fetching data. If None, raw data must be provided.
        """
        self._market_data = market_data_tool
        self._smc = _SMCDetector()
        self._sr = _SupportResistanceDetector()

    async def analyze(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 200,
    ) -> dict[str, Any]:
        """
        Run full technical analysis on a symbol.

        Fetches OHLCV data (if a MarketDataTool was provided), runs all
        MathEngine indicators, SMC detection, support/resistance, and
        computes trend + derivative fields.

        Args:
            symbol: Ticker symbol to analyze.
            timeframe: Candle interval.
            limit: Number of candles to analyze.

        Returns:
            Comprehensive analysis dict with keys:
              - 'symbol', 'timeframe', 'timestamp'
              - 'indicators': Raw MathEngine output
              - 'smc': Smart Money Concepts signals
              - 'support_resistance': S/R levels
              - 'trend': direction, strength, ema_trend
              - 'derived': price_change_1d, price_change_5d, volume_ratio

        Raises:
            DataError: If data cannot be fetched.
            InsufficientDataError: If not enough bars for analysis.
        """
        # Fetch data
        if self._market_data is None:
            raise DataError(
                "No MarketDataTool configured — provide one at init or "
                "use analyze_raw() with pre-fetched data."
            )

        ohlcv_result = await self._market_data.get_ohlcv(symbol, timeframe, limit)
        candles = ohlcv_result.get("candles", [])

        if len(candles) < _MIN_BARS:
            raise InsufficientDataError(_MIN_BARS, len(candles), "full_technical_analysis")

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c["volume"] for c in candles]

        return self.analyze_raw(closes, highs, lows, volumes, symbol, timeframe)

    def analyze_raw(
        self,
        closes: list[float],
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        volumes: list[float] | None = None,
        symbol: str = "UNKNOWN",
        timeframe: str = "1d",
    ) -> dict[str, Any]:
        """
        Run full technical analysis on raw price arrays.

        This is the synchronous path — useful when data is already available.

        Args:
            closes: Close price series (minimum 50 bars).
            highs: High price series (defaults to closes).
            lows: Low price series (defaults to closes).
            volumes: Volume series (defaults to flat 1.0).
            symbol: Symbol label for the result dict.
            timeframe: Timeframe label for the result dict.

        Returns:
            Comprehensive analysis dict.
        """
        if len(closes) < _MIN_BARS:
            raise InsufficientDataError(_MIN_BARS, len(closes), "full_technical_analysis")

        highs = highs or closes
        lows = lows or closes
        volumes = volumes or [1.0] * len(closes)

        # ── Core MathEngine analysis ──────────────────────────────────
        engine_result = MathEngine.analyze_sequence(closes, highs, lows, volumes)

        # ── SMC detection ─────────────────────────────────────────────
        smc_result = self._smc.detect(highs, lows, closes)

        # ── Support / Resistance ──────────────────────────────────────
        sr_result = self._sr.detect(highs, lows, closes)

        # ── Trend classification ──────────────────────────────────────
        trend = self._classify_trend(closes, engine_result)

        # ── Derived fields ────────────────────────────────────────────
        derived = self._compute_derived(closes, volumes)

        # ── Assemble final result ─────────────────────────────────────
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now(UTC).isoformat(),
            "bars_analyzed": len(closes),
            "indicators": engine_result.get("indicators", {}),
            "smc": smc_result,
            "support_resistance": sr_result,
            "trend": trend,
            "derived": derived,
        }

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _classify_trend(
        closes: list[float], engine_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Classify trend direction and strength from EMA alignment + ADX.

        EMA trend logic:
          - BULL: EMA9 > EMA20 > EMA50 (aligned bullish)
          - BEAR: EMA9 < EMA20 < EMA50 (aligned bearish)
          - NEUTRAL: EMAs are not aligned

        Strength:
          - ADX > 25: strong trend
          - ADX 20-25: moderate trend
          - ADX < 20: weak / no trend
        """
        indicators = engine_result.get("indicators", {})
        ema_9 = indicators.get("ema_9")
        ema_20 = indicators.get("ema_20")
        ema_50 = indicators.get("ema_50")
        ema_200 = indicators.get("ema_200")
        adx_val = indicators.get("adx", {}).get("adx")
        plus_di = indicators.get("adx", {}).get("plus_di")
        minus_di = indicators.get("adx", {}).get("minus_di")

        # EMA trend direction
        ema_trend = "NEUTRAL"
        if all(v is not None for v in (ema_9, ema_20, ema_50)):
            if ema_9 > ema_20 > ema_50:  # type: ignore[operator]
                ema_trend = "BULL"
            elif ema_9 < ema_20 < ema_50:  # type: ignore[operator]
                ema_trend = "BEAR"

        # ADX strength
        trend_strength = 0.0
        if adx_val is not None:
            trend_strength = min(adx_val / 50.0, 1.0)  # Normalize to 0-1

        # DI-based direction confirmation
        di_direction = "NEUTRAL"
        if plus_di is not None and minus_di is not None:
            if plus_di > minus_di:
                di_direction = "BULL"
            elif minus_di > plus_di:
                di_direction = "BEAR"

        # Combined direction (EMA takes priority, DI confirms)
        if ema_trend != "NEUTRAL" and ema_trend == di_direction:
            direction = ema_trend
            direction_confidence = "HIGH"
        elif ema_trend != "NEUTRAL":
            direction = ema_trend
            direction_confidence = "MODERATE"
        elif di_direction != "NEUTRAL":
            direction = di_direction
            direction_confidence = "LOW"
        else:
            direction = "NEUTRAL"
            direction_confidence = "NONE"

        # Price vs EMA200 (long-term bias)
        long_term_bias = None
        if ema_200 is not None and closes:
            long_term_bias = "ABOVE" if closes[-1] > ema_200 else "BELOW"

        return {
            "direction": direction,
            "ema_trend": ema_trend,
            "di_direction": di_direction,
            "trend_strength": round(trend_strength, 4),
            "direction_confidence": direction_confidence,
            "long_term_bias": long_term_bias,
            "adx": adx_val,
        }

    @staticmethod
    def _compute_derived(
        closes: list[float], volumes: list[float]
    ) -> dict[str, Any]:
        """
        Compute derived fields: price changes, volume ratio.

        Args:
            closes: Close price series.
            volumes: Volume series.

        Returns:
            Dict with price_change_1d, price_change_5d, volume_ratio.
        """
        n = len(closes)
        result: dict[str, Any] = {}

        # Price change 1-day
        if n >= 2:
            result["price_change_1d"] = round(
                (closes[-1] - closes[-2]) / closes[-2] * 100, 4
            )
        else:
            result["price_change_1d"] = None

        # Price change 5-day
        if n >= 6:
            result["price_change_5d"] = round(
                (closes[-1] - closes[-6]) / closes[-6] * 100, 4
            )
        else:
            result["price_change_5d"] = None

        # Volume ratio: current volume / 20-day average volume
        vol_len = min(20, len(volumes))
        if vol_len >= 2 and sum(volumes[-vol_len:]) > 0:
            avg_vol = sum(volumes[-vol_len:]) / vol_len
            result["volume_ratio"] = round(volumes[-1] / avg_vol, 4) if avg_vol > 0 else 0.0
        else:
            result["volume_ratio"] = None

        # Current price position (high-low range over 20 bars)
        if n >= 20:
            recent_high = max(closes[-20:])
            recent_low = min(closes[-20:])
            price_range = recent_high - recent_low
            if price_range > 0:
                result["price_position"] = round(
                    (closes[-1] - recent_low) / price_range, 4
                )
            else:
                result["price_position"] = 0.5
        else:
            result["price_position"] = None

        return result
