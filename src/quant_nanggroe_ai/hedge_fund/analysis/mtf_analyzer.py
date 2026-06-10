"""
Multi-Timeframe Analyzer for AI Quant Hedge Fund
Higher timeframe bias detection and cross-timeframe signal combination
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class Timeframe(Enum):
    """Supported timeframes."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1H"
    H4 = "4H"
    D1 = "1D"
    W1 = "1W"
    MN1 = "1M"


@dataclass
class HTFBias:
    """Higher timeframe market bias."""

    timeframe: str
    trend: str  # BULLISH, BEARISH, NEUTRAL
    strength: float  # 0.0 to 1.0
    key_levels: Dict[str, float] = field(default_factory=dict)
    structure: str = ""
    liquidity_levels: Dict[str, float] = field(default_factory=dict)


@dataclass
class MultiTimeframeSignal:
    """Combined signal from multiple timeframes."""

    symbol: str
    htf_bias: HTFBias
    ltf_signals: List[Dict]
    combined_confidence: float
    direction: str  # BUY, SELL, HOLD
    reasoning: List[str]
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    timestamp: datetime = field(default_factory=datetime.now)


class MultiTimeframeAnalyzer:
    """
    Analyzes multiple timeframes to generate combined signals.

    Features:
    - Higher timeframe bias detection
    - HTF/LTF alignment scoring
    - Market structure analysis
    - Liquidity level identification
    - Signal combination logic
    """

    def __init__(self, data_provider=None, htf_timeframes: List[str] = None, ltf_timeframes: List[str] = None):
        self.data_provider = data_provider
        self.htf_timeframes = htf_timeframes or ["4H", "1D", "1W"]
        self.ltf_timeframes = ltf_timeframes or ["1m", "5m", "15m", "1H"]

        self._trend_indicators = ["sma20", "sma50", "sma200", "ema12", "ema26"]
        self._momentum_indicators = ["rsi", "macd", "stoch"]

        self._bias_cache: Dict[str, HTFBias] = {}

    def analyze(self, symbol: str, htf: str = "4H", ltf: str = "15m", lookback_days: int = 30) -> MultiTimeframeSignal:
        """
        Perform multi-timeframe analysis.

        Args:
            symbol: Trading symbol
            htf: Higher timeframe for bias
            ltf: Lower timeframe for signals
            lookback_days: Days of historical data

        Returns:
            MultiTimeframeSignal with combined analysis
        """
        logger.info(f"Starting MTF analysis for {symbol} (HTF: {htf}, LTF: {ltf})")

        htf_bias = self._analyze_htf_bias(symbol, htf, lookback_days)
        ltf_signals = self._analyze_ltf_signals(symbol, ltf, lookback_days)

        combined = self._combine_signals(htf_bias, ltf_signals, symbol)

        return combined

    def _analyze_htf_bias(self, symbol: str, timeframe: str, lookback_days: int) -> HTFBias:
        """Analyze higher timeframe bias."""
        cache_key = f"{symbol}_{timeframe}"

        if cache_key in self._bias_cache:
            return self._bias_cache[cache_key]

        df = self._get_data(symbol, timeframe, lookback_days)
        if df is None or df.empty:
            return HTFBias(timeframe=timeframe, trend="NEUTRAL", strength=0.0, key_levels={}, structure="UNKNOWN")

        trend = self._determine_trend(df)
        strength = self._calculate_trend_strength(df)
        key_levels = self._identify_key_levels(df)
        structure = self._analyze_structure(df)
        liquidity = self._find_liquidity_levels(df)

        bias = HTFBias(timeframe=timeframe, trend=trend, strength=strength, key_levels=key_levels, structure=structure, liquidity_levels=liquidity)

        self._bias_cache[cache_key] = bias
        return bias

    def _analyze_ltf_signals(self, symbol: str, timeframe: str, lookback_days: int) -> List[Dict]:
        """Analyze lower timeframe for signals."""
        df = self._get_data(symbol, timeframe, lookback_days)
        if df is None or df.empty:
            return []

        signals = []

        for indicator in self._trend_indicators + self._momentum_indicators:
            if indicator in df.columns:
                signal = self._analyze_indicator(df, indicator, timeframe)
                if signal:
                    signals.append(signal)

        return signals

    def _analyze_indicator(self, df: pd.DataFrame, indicator: str, timeframe: str) -> Optional[Dict]:
        """Analyze a single indicator."""
        if indicator not in df.columns:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        if indicator.startswith("sma") or indicator.startswith("ema"):
            return self._analyze_moving_average(latest, prev, indicator)
        elif indicator == "rsi":
            return self._analyze_rsi(latest, indicator)
        elif indicator == "macd":
            return self._analyze_macd(latest, prev, indicator)
        elif indicator == "stoch":
            return self._analyze_stoch(latest, indicator)

        return None

    def _analyze_moving_average(self, latest: pd.Series, prev: pd.Series, indicator: str) -> Dict:
        """Analyze moving average signal."""
        current = latest[indicator]
        price = latest.get("close", 0)

        if indicator in ["sma200", "ema26"]:
            above = price > current
            trend = "BULLISH" if above else "BEARISH"
            strength = min(abs(price - current) / current * 10, 1.0)

            return {"indicator": indicator, "signal": trend, "strength": strength, "value": current, "price": price, "bias": above}

        return None

    def _analyze_rsi(self, latest: pd.Series, indicator: str) -> Dict:
        """Analyze RSI signal."""
        rsi = latest.get(indicator, 50)

        if rsi > 70:
            signal = "OVERBOUGHT"
            strength = (rsi - 70) / 30
        elif rsi < 30:
            signal = "OVERSOLD"
            strength = (30 - rsi) / 30
        else:
            signal = "NEUTRAL"
            strength = 0.0

        return {"indicator": indicator, "signal": signal, "strength": strength, "value": rsi, "bias": rsi < 50}

    def _analyze_macd(self, latest: pd.Series, prev: pd.Series, indicator: str) -> Dict:
        """Analyze MACD signal."""
        macd = latest.get("macd", 0)
        signal = latest.get("macd_signal", 0)
        hist = latest.get("macd_hist", 0)
        prev_hist = prev.get("macd_hist", 0)

        bullish = macd > signal
        strengthening = hist > prev_hist

        strength = abs(hist) / latest.get("close", 1) * 100

        return {"indicator": indicator, "signal": "BULLISH" if bullish else "BEARISH", "strength": min(strength, 1.0), "value": hist, "bias": bullish and strengthening}

    def _analyze_stoch(self, latest: pd.Series, indicator: str) -> Dict:
        """Analyze Stochastic signal."""
        k = latest.get("stoch_k", 50)
        d = latest.get("stoch_d", 50)

        if k > 80 and d > 80:
            signal = "OVERBOUGHT"
            strength = (k - 80) / 20
        elif k < 20 and d < 20:
            signal = "OVERSOLD"
            strength = (20 - k) / 20
        else:
            signal = "NEUTRAL"
            strength = 0.0

        return {"indicator": indicator, "signal": signal, "strength": strength, "value": k, "bias": k < 30 or (k > d and k < 50)}

    def _determine_trend(self, df: pd.DataFrame) -> str:
        """Determine market trend from data."""
        if len(df) < 50:
            return "NEUTRAL"

        sma20 = df["close"].rolling(20).mean().iloc[-1]
        sma50 = df["close"].rolling(50).mean().iloc[-1]
        sma200 = df["close"].rolling(200).mean().iloc[-1]
        current_price = df["close"].iloc[-1]

        close_above_ma200 = current_price > sma200
        sma20_above_ma50 = sma20 > sma50
        sma50_above_ma200 = sma50 > sma200

        if close_above_ma200 and sma20_above_ma50 and sma50_above_ma200:
            return "STRONG_BULLISH"
        elif close_above_ma200 and sma20_above_ma50:
            return "BULLISH"
        elif not close_above_ma200 and not sma20_above_ma50 and not sma50_above_ma200:
            return "STRONG_BEARISH"
        elif not close_above_ma200 and not sma20_above_ma50:
            return "BEARISH"
        elif close_above_ma200:
            return "BULLISH"
        elif not close_above_ma200:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength (0.0 to 1.0)."""
        if len(df) < 20:
            return 0.5

        closes = df["close"].values
        adx = self._calculate_adx(df)

        return min(adx / 50, 1.0)

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average Directional Index."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        plus_dm = np.where(high[1:] - high[:-1] > low[:-1] - low[1:], np.maximum(high[1:] - high[:-1], 0), 0)
        minus_dm = np.where(low[:-1] - low[1:] > high[1:] - high[:-1], np.maximum(low[:-1] - low[1:], 0), 0)

        atr = self._calculate_atr(df, period)

        if np.mean(atr) == 0:
            return 25.0

        plus_di = 100 * np.mean(plus_dm) / np.mean(atr)
        minus_di = 100 * np.mean(minus_dm) / np.mean(atr)

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = np.mean(dx)

        return adx if not np.isnan(adx) else 25.0

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> np.ndarray:
        """Calculate Average True Range."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr1 = high - low
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])

        tr = np.concatenate([tr1[0:1], np.maximum(tr1[1:], np.maximum(tr2, tr3))])

        atr = np.zeros_like(tr)
        atr[period] = np.mean(tr[:period])

        for i in range(period + 1, len(tr)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        return atr

    def _identify_key_levels(self, df: pd.DataFrame) -> Dict[str, float]:
        """Identify key support and resistance levels."""
        if len(df) < 50:
            return {}

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        current_price = closes[-1]

        highs_above = highs[highs > current_price]
        lows_below = lows[lows < current_price]

        resistance = np.min(highs_above) if len(highs_above) > 0 else current_price * 1.02
        support = np.max(lows_below) if len(lows_below) > 0 else current_price * 0.98

        pivot = (highs.max() + lows.min() + closes[-1]) / 3

        return {"current_price": current_price, "support": support, "resistance": resistance, "pivot": pivot, "r1": pivot * 2 - lows.min(), "s1": pivot * 2 - highs.max()}

    def _analyze_structure(self, df: pd.DataFrame) -> str:
        """Analyze market structure (higher highs/lower lows)."""
        if len(df) < 20:
            return "UNDEFINED"

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        higher_highs = 0
        higher_lows = 0
        lower_highs = 0
        lower_lows = 0

        for i in range(5, len(highs)):
            if highs[i] > highs[i - 5]:
                higher_highs += 1
            else:
                lower_highs += 1

            if lows[i] > lows[i - 5]:
                higher_lows += 1
            else:
                lower_lows += 1

        if higher_highs > lower_highs and higher_lows > lower_lows:
            return "STRONG_UPTREND"
        elif higher_highs > lower_highs:
            return "UPTREND"
        elif lower_highs > higher_highs and lower_highs > higher_lows:
            return "STRONG_DOWNTREND"
        elif lower_highs > higher_highs:
            return "DOWNTREND"
        else:
            return "CONSOLIDATING"

    def _find_liquidity_levels(self, df: pd.DataFrame) -> Dict[str, float]:
        """Find liquidity levels (stop hunts, liquidity pools)."""
        if len(df) < 50:
            return {}

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        current_price = closes[-1]

        liquidity_above = highs[highs > current_price]
        liquidity_below = lows[lows < current_price]

        buy_side_liquidity = np.min(liquidity_above) if len(liquidity_above) > 0 else None
        sell_side_liquidity = np.max(liquidity_below) if len(liquidity_below) > 0 else None

        return {"buy_side_liquidity": buy_side_liquidity, "sell_side_liquidity": sell_side_liquidity, "distance_to_bsl": (buy_side_liquidity - current_price) / current_price if buy_side_liquidity else None, "distance_to_ssl": (current_price - sell_side_liquidity) / current_price if sell_side_liquidity else None}

    def _combine_signals(self, htf_bias: HTFBias, ltf_signals: List[Dict], symbol: str) -> MultiTimeframeSignal:
        """Combine HTF bias and LTF signals."""
        reasoning = []

        reasoning.append(f"HTF ({htf_bias.timeframe}) Bias: {htf_bias.trend} (strength: {htf_bias.strength:.2f})")
        reasoning.append(f"Structure: {htf_bias.structure}")

        if htf_bias.key_levels:
            reasoning.append(f"Key Levels - Support: {htf_bias.key_levels.get('support', 0):.5f}, Resistance: {htf_bias.key_levels.get('resistance', 0):.5f}")

        bullish_ltf = sum(1 for s in ltf_signals if s.get("bias", False))
        bearish_ltf = len(ltf_signals) - bullish_ltf

        reasoning.append(f"LTF Signals - Bullish: {bullish_ltf}, Bearish: {bearish_ltf}")

        htf_direction = 1 if "BULLISH" in htf_bias.trend else (-1 if "BEARISH" in htf_bias.trend else 0)
        ltf_direction = (bullish_ltf - bearish_ltf) / max(len(ltf_signals), 1)

        combined_confidence = (abs(htf_direction) * htf_bias.strength + abs(ltf_direction)) / 2

        if htf_direction > 0 and ltf_direction > 0:
            direction = "BUY"
            confidence = min(combined_confidence * 1.2, 1.0)
            reasoning.append("HTF & LTF aligned BULLISH - FAVORABLE")
        elif htf_direction < 0 and ltf_direction < 0:
            direction = "SELL"
            confidence = min(combined_confidence * 1.2, 1.0)
            reasoning.append("HTF & LTF aligned BEARISH - FAVORABLE")
        elif htf_direction != 0:
            direction = "BUY" if htf_direction > 0 else "SELL"
            confidence = combined_confidence * 0.7
            reasoning.append("Counter-trend LTF signal - LOWER CONFIDENCE")
        else:
            direction = "HOLD"
            confidence = 0.3
            reasoning.append("No clear direction - HOLD")

        entry_price = htf_bias.key_levels.get("current_price", 0)

        if htf_bias.trend == "STRONG_BULLISH":
            sl_pct = 0.02
            tp_pct = 0.06
        elif htf_bias.trend == "BULLISH":
            sl_pct = 0.015
            tp_pct = 0.045
        elif htf_bias.trend == "STRONG_BEARISH":
            sl_pct = 0.02
            tp_pct = 0.06
        elif htf_bias.trend == "BEARISH":
            sl_pct = 0.015
            tp_pct = 0.045
        else:
            sl_pct = 0.01
            tp_pct = 0.03

        if direction == "BUY":
            stop_loss = entry_price * (1 - sl_pct)
            take_profit = entry_price * (1 + tp_pct)
        elif direction == "SELL":
            stop_loss = entry_price * (1 + sl_pct)
            take_profit = entry_price * (1 - tp_pct)
        else:
            stop_loss = 0
            take_profit = 0

        risk_reward = tp_pct / sl_pct if sl_pct > 0 else 0

        return MultiTimeframeSignal(symbol=symbol, htf_bias=htf_bias, ltf_signals=ltf_signals, combined_confidence=confidence, direction=direction, reasoning=reasoning, entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit, risk_reward_ratio=risk_reward)

    def _get_data(self, symbol: str, timeframe: str, lookback_days: int) -> Optional[pd.DataFrame]:
        """Get data from provider or generate demo data."""
        if self.data_provider:
            try:
                df = self.data_provider.get_rates(symbol, timeframe, lookback_days * 1440)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"Error getting data from provider: {e}")

        return self._generate_demo_data(timeframe, lookback_days)

    def _generate_demo_data(self, timeframe: str, lookback_days: int) -> pd.DataFrame:
        """Generate demo data for testing."""
        import random
        from datetime import timedelta

        timeframe_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1H": 60, "4H": 240, "1D": 1440, "1W": 10080, "1M": 43200}

        minutes = timeframe_minutes.get(timeframe, 60)
        periods = (lookback_days * 1440) // minutes

        now = datetime.now()
        times = [now - timedelta(minutes=minutes * i) for i in range(periods)]
        times.reverse()

        base_price = 1.0850 if "USD" in "EURUSD" else 100.0
        prices = []
        for _ in range(periods):
            change = random.uniform(-0.002, 0.002)
            base_price += change
            prices.append(base_price)

        df = pd.DataFrame({"time": times, "open": prices, "close": [p + random.uniform(-0.0005, 0.0005) for p in prices], "high": [p + random.uniform(0, 0.001) for p in prices], "low": [p - random.uniform(0, 0.001) for p in prices], "volume": [random.randint(1000, 10000) for _ in range(periods)]})

        df["sma20"] = df["close"].rolling(20).mean()
        df["sma50"] = df["close"].rolling(50).mean()
        df["sma200"] = df["close"].rolling(200).mean()
        df["ema12"] = df["close"].ewm(span=12).mean()
        df["ema26"] = df["close"].ewm(span=26).mean()

        df["rsi"] = self._calculate_rsi(df["close"], 14)
        df["macd"] = df["ema12"] - df["ema26"]
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        low_min = df["low"].rolling(14).min()
        high_max = df["high"].rolling(14).max()
        df["stoch_k"] = 100 * (df["close"] - low_min) / (high_max - low_min + 0.0001)
        df["stoch_d"] = df["stoch_k"].rolling(3).mean()

        return df

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI."""
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / (loss + 0.0001)
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def get_market_summary(self, symbol: str) -> Dict:
        """Get summary of market across all timeframes."""
        summary = {"symbol": symbol, "timeframes_analyzed": {}, "alignment_score": 0.0, "overall_bias": "NEUTRAL", "recommendation": "HOLD"}

        biases = []

        for tf in self.htf_timeframes:
            bias = self._analyze_htf_bias(symbol, tf, 30)
            summary["timeframes_analyzed"][tf] = {"trend": bias.trend, "strength": bias.strength, "structure": bias.structure}
            biases.append(bias)

        bullish_count = sum(1 for b in biases if "BULLISH" in b.trend)
        bearish_count = sum(1 for b in biases if "BEARISH" in b.trend)

        if bullish_count > bearish_count:
            summary["overall_bias"] = "BULLISH"
            summary["alignment_score"] = bullish_count / len(biases)
        elif bearish_count > bullish_count:
            summary["overall_bias"] = "BEARISH"
            summary["alignment_score"] = bearish_count / len(biases)

        avg_strength = np.mean([b.strength for b in biases])

        if summary["alignment_score"] >= 0.7 and avg_strength >= 0.5:
            summary["recommendation"] = "BUY" if summary["overall_bias"] == "BULLISH" else "SELL"
        elif summary["alignment_score"] <= 0.3:
            summary["recommendation"] = "HOLD"

        return summary


def create_mtf_analyzer(data_provider=None, htf_timeframes: List[str] = None, ltf_timeframes: List[str] = None) -> MultiTimeframeAnalyzer:
    """Factory function to create MTF analyzer."""
    return MultiTimeframeAnalyzer(data_provider=data_provider, htf_timeframes=htf_timeframes, ltf_timeframes=ltf_timeframes)


if __name__ == "__main__":
    analyzer = create_mtf_analyzer()

    print("Multi-Timeframe Analyzer Demo")
    print("=" * 50)

    summary = analyzer.get_market_summary("EURUSD")
    print(f"\nMarket Summary for {summary['symbol']}:")
    print(f"Overall Bias: {summary['overall_bias']}")
    print(f"Alignment Score: {summary['alignment_score']:.2%}")
    print(f"Recommendation: {summary['recommendation']}")

    print("\nTimeframes:")
    for tf, data in summary["timeframes_analyzed"].items():
        print(f"  {tf}: {data['trend']} ({data['strength']:.2f}) - {data['structure']}")
