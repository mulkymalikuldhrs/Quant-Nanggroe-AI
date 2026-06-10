"""
Technical Indicators Library
Implementation of common technical analysis indicators for trading systems.
Based on Zenbot and Freqtrade implementations.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class IndicatorResult:
    """Container for indicator results"""

    name: str
    value: float
    signal: str  # BUY, SELL, NEUTRAL
    metadata: Dict = None


class TechnicalIndicators:
    """
    Comprehensive technical indicators library.
    Implements common indicators used in quantitative trading.
    """

    def __init__(self):
        self.cache = {}

    def clear_cache(self):
        """Clear indicator cache"""
        self.cache = {}

    def _ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average

        Args:
            data: Price series
            period: EMA period

        Returns:
            EMA series
        """
        return data.ewm(span=period, adjust=False).mean()

    def _sma(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average

        Args:
            data: Price series
            period: SMA period

        Returns:
            SMA series
        """
        return data.rolling(window=period).mean()

    def _stddev(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Standard Deviation

        Args:
            data: Price series
            period: Period for std dev

        Returns:
            Std dev series
        """
        return data.rolling(window=period).std()

    def rsi(self, closes: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)

        Args:
            closes: Close price series
            period: RSI period (default: 14)

        Returns:
            RSI series (0-100)
        """
        delta = closes.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rs = rs.replace([np.inf, -np.inf], np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)

        return rsi

    def macd(self, closes: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Moving Average Convergence Divergence (MACD)

        Args:
            closes: Close price series
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)

        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = self._ema(closes, fast_period)
        ema_slow = self._ema(closes, slow_period)

        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def bollinger_bands(self, closes: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands

        Args:
            closes: Close price series
            period: BB period (default: 20)
            std_dev: Number of standard deviations (default: 2.0)

        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        middle = self._sma(closes, period)
        std = self._stddev(closes, period)

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return upper, middle, lower

    def stochastic(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic Oscillator

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            k_period: %K period (default: 14)
            d_period: %D period (default: 3)

        Returns:
            Tuple of (%K, %D)
        """
        lowest_low = lows.rolling(window=k_period).min()
        highest_high = highs.rolling(window=k_period).max()

        k = 100 * (closes - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return k, d

    def atr(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: ATR period (default: 14)

        Returns:
            ATR series
        """
        prev_close = closes.shift(1)

        tr1 = highs - lows
        tr2 = abs(highs - prev_close)
        tr3 = abs(lows - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    def adx(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Average Directional Index (ADX)

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: ADX period (default: 14)

        Returns:
            Tuple of (+DI, -DI, ADX)
        """
        prev_close = closes.shift(1)

        plus_dm = highs - highs.shift(1)
        minus_dm = lows.shift(1) - lows

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr1 = highs - lows
        tr2 = abs(highs - prev_close)
        tr3 = abs(lows - prev_close)
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = true_range.rolling(window=period).mean()

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return plus_di, minus_di, adx

    def cci(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 20) -> pd.Series:
        """
        Calculate Commodity Channel Index (CCI)

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: CCI period (default: 20)

        Returns:
            CCI series
        """
        typical_price = (highs + lows + closes) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)

        cci = (typical_price - sma) / (0.015 * mad)
        return cci

    def obv(self, closes: pd.Series, volumes: pd.Series) -> pd.Series:
        """
        Calculate On Balance Volume (OBV)

        Args:
            closes: Close price series
            volumes: Volume series

        Returns:
            OBV series
        """
        obv = pd.Series(index=closes.index, dtype=float)

        for i in range(len(closes)):
            if i == 0:
                obv.iloc[i] = volumes.iloc[i]
            else:
                if closes.iloc[i] > closes.iloc[i - 1]:
                    obv.iloc[i] = obv.iloc[i - 1] + volumes.iloc[i]
                elif closes.iloc[i] < closes.iloc[i - 1]:
                    obv.iloc[i] = obv.iloc[i - 1] - volumes.iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i - 1]

        return obv

    def vwap(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series) -> pd.Series:
        """
        Calculate Volume Weighted Average Price (VWAP)

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            volumes: Volume series

        Returns:
            VWAP series
        """
        typical_price = (highs + lows + closes) / 3
        vp = typical_price * volumes

        vwap = vp.cumsum() / volumes.cumsum()
        return vwap

    def parabolic_sar(self, highs: pd.Series, lows: pd.Series, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
        """
        Calculate Parabolic SAR (Stop and Reverse)

        Args:
            highs: High price series
            lows: Low price series
            step: Acceleration factor step (default: 0.02)
            max_step: Maximum acceleration factor (default: 0.2)

        Returns:
            Parabolic SAR series
        """
        sar = pd.Series(index=highs.index, dtype=float)
        trend = pd.Series(index=highs.index, dtype=float)
        ep = pd.Series(index=highs.index, dtype=float)
        af = pd.Series(index=highs.index, dtype=float)

        for i in range(len(highs)):
            if i == 0:
                sar.iloc[i] = lows.iloc[i]
                trend.iloc[i] = 1
                ep.iloc[i] = highs.iloc[i]
                af.iloc[i] = step
            else:
                if trend.iloc[i - 1] == 1:
                    sar.iloc[i] = sar.iloc[i - 1] + af.iloc[i - 1] * (ep.iloc[i - 1] - sar.iloc[i - 1])
                    if highs.iloc[i] > ep.iloc[i - 1]:
                        ep.iloc[i] = highs.iloc[i]
                        af.iloc[i] = min(af.iloc[i - 1] + step, max_step)
                    else:
                        ep.iloc[i] = ep.iloc[i - 1]
                        af.iloc[i] = af.iloc[i - 1]

                    if lows.iloc[i] < sar.iloc[i]:
                        trend.iloc[i] = -1
                        sar.iloc[i] = ep.iloc[i - 1]
                        ep.iloc[i] = lows.iloc[i]
                        af.iloc[i] = step
                    else:
                        trend.iloc[i] = 1
                else:
                    sar.iloc[i] = sar.iloc[i - 1] + af.iloc[i - 1] * (ep.iloc[i - 1] - sar.iloc[i - 1])
                    if lows.iloc[i] < ep.iloc[i - 1]:
                        ep.iloc[i] = lows.iloc[i]
                        af.iloc[i] = min(af.iloc[i - 1] + step, max_step)
                    else:
                        ep.iloc[i] = ep.iloc[i - 1]
                        af.iloc[i] = af.iloc[i - 1]

                    if highs.iloc[i] > sar.iloc[i]:
                        trend.iloc[i] = 1
                        sar.iloc[i] = ep.iloc[i - 1]
                        ep.iloc[i] = highs.iloc[i]
                        af.iloc[i] = step
                    else:
                        trend.iloc[i] = -1

        return sar

    def momentum(self, closes: pd.Series, period: int = 10) -> pd.Series:
        """
        Calculate Momentum

        Args:
            closes: Close price series
            period: Momentum period (default: 10)

        Returns:
            Momentum series
        """
        return closes - closes.shift(period)

    def rate_of_change(self, closes: pd.Series, period: int = 10) -> pd.Series:
        """
        Calculate Rate of Change (ROC)

        Args:
            closes: Close price series
            period: ROC period (default: 10)

        Returns:
            ROC series (percentage)
        """
        return ((closes - closes.shift(period)) / closes.shift(period)) * 100

    def williams_r(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Williams %R

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: Period (default: 14)

        Returns:
            Williams %R series (-100 to 0)
        """
        highest_high = highs.rolling(window=period).max()
        lowest_low = lows.rolling(window=period).min()

        williams_r = -100 * (highest_high - closes) / (highest_high - lowest_low)
        return williams_r


    def mfi(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series, period: int = 14) -> pd.Series:
        import numpy as np
        typical_price = (highs + lows + closes) / 3
        raw_money_flow = typical_price * volumes
        money_flow = pd.DataFrame({
            "positive": np.where(typical_price > typical_price.shift(1), raw_money_flow, 0),
            "negative": np.where(typical_price < typical_price.shift(1), raw_money_flow, 0)
        })
        positive_flow = money_flow["positive"].rolling(window=period).sum()
        negative_flow = money_flow["negative"].rolling(window=period).sum()
        money_ratio = positive_flow / negative_flow
        mfi = 100 - (100 / (1 + money_ratio))
        return mfi


    def average_price(self, highs: pd.Series, lows: pd.Series, closes: pd.Series) -> pd.Series:
        """
        Calculate Typical Price

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series

        Returns:
            Typical price series
        """
        return (highs + lows + closes) / 3

    def price_oscillator(self, closes: pd.Series, fast_period: int = 12, slow_period: int = 26) -> pd.Series:
        """
        Calculate Price Oscillator (PPO)

        Args:
            closes: Close price series
            fast_period: Fast period (default: 12)
            slow_period: Slow period (default: 26)

        Returns:
            PPO series (percentage)
        """
        ema_fast = self._ema(closes, fast_period)
        ema_slow = self._ema(closes, slow_period)

        return ((ema_fast - ema_slow) / ema_slow) * 100

    def trix(self, closes: pd.Series, period: int = 15) -> pd.Series:
        """
        Triple Exponential Moving Average (TRIX)

        Args:
            closes: Close price series
            period: TRIX period (default: 15)

        Returns:
            TRIX series
        """
        ema1 = self._ema(closes, period)
        ema2 = self._ema(ema1, period)
        ema3 = self._ema(ema2, period)

        trix = ema3.pct_change() * 100
        return trix

    def keltner_channels(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, ema_period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Keltner Channels

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            ema_period: EMA period (default: 20)
            atr_period: ATR period (default: 10)
            multiplier: ATR multiplier (default: 2.0)

        Returns:
            Tuple of (Upper channel, Middle EMA, Lower channel)
        """
        ema = self._ema(closes, ema_period)
        atr = self.atr(highs, lows, closes, atr_period)

        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)

        return upper, ema, lower

    def ichimoku_cloud(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, conversion_period: int = 9, base_period: int = 26, lagging_span: int = 52, displacement: int = 26) -> Dict[str, pd.Series]:
        """
        Calculate Ichimoku Cloud components

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            conversion_period: Conversion line period (default: 9)
            base_period: Base line period (default: 26)
            lagging_span: Leading span B period (default: 52)
            displacement: Displacement (default: 26)

        Returns:
            Dictionary of Ichimoku components
        """
        conversion_line = (highs.rolling(window=conversion_period).max() + lows.rolling(window=conversion_period).min()) / 2
        base_line = (highs.rolling(window=base_period).max() + lows.rolling(window=base_period).min()) / 2
        leading_span_a = ((conversion_line + base_line) / 2).shift(displacement)
        leading_span_b = ((highs.rolling(window=lagging_span).max() + lows.rolling(window=lagging_span).min()) / 2).shift(displacement)
        lagging_line = closes.shift(-displacement)

        return {"conversion": conversion_line, "base": base_line, "leading_a": leading_span_a, "leading_b": leading_span_b, "lagging": lagging_line}

    def supertrend(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate SuperTrend indicator

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            period: ATR period (default: 10)
            multiplier: ATR multiplier (default: 3.0)

        Returns:
            Tuple of (SuperTrend line, Direction)
        """
        atr = self.atr(highs, lows, closes, period)

        hl2 = (highs + lows) / 2

        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        supertrend = pd.Series(index=closes.index, dtype=float)
        direction = pd.Series(index=closes.index, dtype=int)

        for i in range(len(closes)):
            if i == 0:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = 1
            else:
                if closes.iloc[i] > supertrend.iloc[i - 1]:
                    supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i - 1])
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i - 1])
                    direction.iloc[i] = -1

        return supertrend, direction

    def get_all_indicators(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series = None) -> Dict[str, pd.Series]:
        """
        Calculate all major indicators

        Args:
            highs: High price series
            lows: Low price series
            closes: Close price series
            volumes: Volume series (optional)

        Returns:
            Dictionary of all indicator values
        """
        indicators = {}

        # RSI
        indicators["rsi_14"] = self.rsi(closes, 14)
        indicators["rsi_7"] = self.rsi(closes, 7)
        indicators["rsi_21"] = self.rsi(closes, 21)

        # MACD
        macd, signal, hist = self.macd(closes)
        indicators["macd"] = macd
        indicators["macd_signal"] = signal
        indicators["macd_histogram"] = hist

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.bollinger_bands(closes)
        indicators["bb_upper"] = bb_upper
        indicators["bb_middle"] = bb_middle
        indicators["bb_lower"] = bb_lower
        indicators["bb_width"] = (bb_upper - bb_lower) / bb_middle
        indicators["bb_position"] = (closes - bb_lower) / (bb_upper - bb_lower)

        # Stochastic
        stoch_k, stoch_d = self.stochastic(highs, lows, closes)
        indicators["stoch_k"] = stoch_k
        indicators["stoch_d"] = stoch_d

        # ATR
        indicators["atr_14"] = self.atr(highs, lows, closes, 14)

        # ADX
        plus_di, minus_di, adx = self.adx(highs, lows, closes)
        indicators["adx"] = adx
        indicators["plus_di"] = plus_di
        indicators["minus_di"] = minus_di

        # CCI
        indicators["cci_20"] = self.cci(highs, lows, closes, 20)

        # Momentum
        indicators["momentum_10"] = self.momentum(closes, 10)
        indicators["roc_10"] = self.rate_of_change(closes, 10)

        # Williams %R
        indicators["williams_r_14"] = self.williams_r(highs, lows, closes, 14)

        # Price Oscillator
        indicators["ppo"] = self.price_oscillator(closes)

        # TRIX
        indicators["trix_15"] = self.trix(closes, 15)

        # Keltner Channels
        kc_upper, kc_middle, kc_lower = self.keltner_channels(highs, lows, closes)
        indicators["kc_upper"] = kc_upper
        indicators["kc_middle"] = kc_middle
        indicators["kc_lower"] = kc_lower

        # SuperTrend
        supertrend, direction = self.supertrend(highs, lows, closes)
        indicators["supertrend"] = supertrend
        indicators["supertrend_direction"] = direction

        # Moving Averages
        indicators["sma_20"] = self._sma(closes, 20)
        indicators["sma_50"] = self._sma(closes, 50)
        indicators["sma_200"] = self._sma(closes, 200)
        indicators["ema_12"] = self._ema(closes, 12)
        indicators["ema_26"] = self._ema(closes, 26)

        # Volume indicators
        if volumes is not None:
            indicators["obv"] = self.obv(closes, volumes)

        return indicators


# Convenience functions
def calculate_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI"""
    return TechnicalIndicators().rsi(closes, period)


def calculate_macd(closes: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD"""
    return TechnicalIndicators().macd(closes, fast_period, slow_period, signal_period)


def calculate_bollinger_bands(closes: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    return TechnicalIndicators().bollinger_bands(closes, period, std_dev)


def calculate_stochastic(highs: pd.Series, lows: pd.Series, closes: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator"""
    return TechnicalIndicators().stochastic(highs, lows, closes, k_period, d_period)


def calculate_atr(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate ATR"""
    return TechnicalIndicators().atr(highs, lows, closes, period)


def calculate_vwap(highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """Calculate VWAP"""
    return TechnicalIndicators().vwap(highs, lows, closes, volumes)


def calculate_stochastic(highs: pd.Series, lows: pd.Series, closes: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator"""
    return TechnicalIndicators().stochastic(highs, lows, closes, k_period, d_period)


def calculate_adx(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate ADX"""
    return TechnicalIndicators().adx(highs, lows, closes, period)


def calculate_cci(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 20) -> pd.Series:
    """Calculate CCI"""
    return TechnicalIndicators().cci(highs, lows, closes, period)


def calculate_obv(closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """Calculate OBV"""
    return TechnicalIndicators().obv(closes, volumes)


def calculate_mfi(highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Money Flow Index (MFI)"""
    typical_price = (highs + lows + closes) / 3
    raw_money = typical_price * volumes

    positive_flow = pd.Series(index=closes.index, dtype=float)
    negative_flow = pd.Series(index=closes.index, dtype=float)

    for i in range(1, len(closes)):
        if typical_price.iloc[i] > typical_price.iloc[i - 1]:
            positive_flow.iloc[i] = raw_money.iloc[i]
            negative_flow.iloc[i] = 0
        else:
            negative_flow.iloc[i] = raw_money.iloc[i]
            positive_flow.iloc[i] = 0

    money_ratio = positive_flow.rolling(window=period).sum() / negative_flow.rolling(window=period).sum()
    money_ratio = money_ratio.replace([np.inf, -np.inf], np.nan).fillna(1)

    mfi = 100 - (100 / (1 + money_ratio))
    return mfi


def calculate_cmfi(highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series, period: int = 21) -> pd.Series:
    """Calculate Chaikin Money Flow (CMF)"""
    mfv = ((closes - lows) - (highs - closes)) / (highs - lows) * volumes
    mfv = mfv.replace([np.inf, -np.inf], 0).fillna(0)

    cmf = mfv.rolling(window=period).sum() / volumes.rolling(window=period).sum()
    return cmf


def calculate_ao(highs: pd.Series, lows: pd.Series, fast_period: int = 5, slow_period: int = 34) -> pd.Series:
    """Calculate Awesome Oscillator"""
    median_price = (highs + lows) / 2
    fast_ma = median_price.rolling(window=fast_period).mean()
    slow_ma = median_price.rolling(window=slow_period).mean()

    ao = fast_ma - slow_ma
    return ao


def calculate_bbands(closes: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    return TechnicalIndicators().bollinger_bands(closes, period, std_dev)


def calculate_kc(highs: pd.Series, lows: pd.Series, closes: pd.Series, ema_period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Keltner Channels"""
    return TechnicalIndicators().keltner_channels(highs, lows, closes, ema_period, atr_period, multiplier)


def calculate_dc(highs: pd.Series, lows: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Donchian Channels"""
    upper = highs.rolling(window=period).max()
    lower = lows.rolling(window=period).min()
    middle = (upper + lower) / 2

    return upper, middle, lower


def calculate_aroon(highs: pd.Series, lows: pd.Series, period: int = 25) -> Tuple[pd.Series, pd.Series]:
    """Calculate Aroon Oscillator"""
    aroon_up = 100 * (period - highs.rolling(window=period).apply(lambda x: period - x[::-1].argmax(), raw=False)) / period
    aroon_down = 100 * (period - lows.rolling(window=period).apply(lambda x: period - x[::-1].argmin(), raw=False)) / period

    return aroon_up, aroon_down


def calculate_ultimate_oscillator(highs: pd.Series, lows: pd.Series, closes: pd.Series, period1: int = 7, period2: int = 14, period3: int = 28) -> pd.Series:
    """Calculate Ultimate Oscillator"""
    bp = closes - pd.concat([lows.shift(1), closes.shift(1)], axis=1).min(axis=1)
    tr = pd.concat([highs.shift(1) - lows.shift(1), abs(highs.shift(1) - closes), abs(lows.shift(1) - closes)], axis=1).max(axis=1)

    avg7 = bp.rolling(window=period1).sum() / tr.rolling(window=period1).sum()
    avg14 = bp.rolling(window=period2).sum() / tr.rolling(window=period2).sum()
    avg28 = bp.rolling(window=period3).sum() / tr.rolling(window=period3).sum()

    uo = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
    return uo


def calculate_vroc(volumes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Volume Rate of Change"""
    vroc = ((volumes - volumes.shift(period)) / volumes.shift(period)) * 100
    return vroc


def calculate_pvt(closes: pd.Series, volumes: pd.Series) -> pd.Series:
    """Calculate Price Volume Trend"""
    pvt = (closes.pct_change() * volumes).cumsum()
    return pvt


def calculate_wma(closes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Weighted Moving Average"""
    weights = np.arange(1, period + 1)
    wma = closes.rolling(window=period).apply(lambda prices: np.dot(prices, weights) / weights.sum(), raw=True)
    return wma


def calculate_hma(closes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Hull Moving Average"""
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))

    wma_half = closes.rolling(window=half_period).apply(lambda x: np.arange(1, half_period + 1).dot(x) / (half_period * (half_period + 1) / 2), raw=True)
    wma_full = closes.rolling(window=period).apply(lambda x: np.arange(1, period + 1).dot(x) / (period * (period + 1) / 2), raw=True)

    hma = (2 * wma_half - wma_full).rolling(window=sqrt_period).apply(lambda x: np.arange(1, sqrt_period + 1).dot(x) / (sqrt_period * (sqrt_period + 1) / 2), raw=True)

    return hma


def calculate_kama(closes: pd.Series, period: int = 14, fast_ema: int = 2, slow_ema: int = 30) -> pd.Series:
    """Calculate Kaufman Adaptive Moving Average"""
    closes = closes.astype(float)

    change = abs(closes - closes.shift(period))
    volatility = abs(closes - closes.shift(1)).rolling(window=period).sum()

    er = change / volatility
    er = er.replace([np.inf, -np.inf], 0).fillna(0.5)

    fast_alpha = 2 / (fast_ema + 1)
    slow_alpha = 2 / (slow_ema + 1)

    sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2

    kama = pd.Series(index=closes.index, dtype=float)
    kama.iloc[period] = closes.iloc[period]

    for i in range(period + 1, len(closes)):
        kama.iloc[i] = kama.iloc[i - 1] + sc.iloc[i] * (closes.iloc[i] - kama.iloc[i - 1])

    return kama


def calculate_alma(closes: pd.Series, period: int = 9, sigma: float = 6, offset: float = 0.85) -> pd.Series:
    """Calculate Arnaud Legoux Moving Average"""
    window = np.arange(period)

    m = offset * (period - 1)
    s = period / sigma

    weights = np.exp(-((window - m) ** 2) / (2 * s**2))
    weights = weights / weights.sum()

    alma = closes.rolling(window=period).apply(lambda x: np.dot(x, weights), raw=True)
    return alma


def calculate_t3(closes: pd.Series, period: int = 14, vfactor: float = 0.7) -> pd.Series:
    """Calculate T3 Moving Average"""
    ema1 = closes.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()

    c1 = -vfactor * vfactor * vfactor
    c2 = 3 * vfactor * vfactor + 3 * vfactor**3
    c3 = -6 * vfactor * vfactor - 3 * vfactor - 3 * vfactor**3
    c4 = 1 + 3 * vfactor + vfactor**3 + 3 * vfactor * vfactor

    t3 = c1 * ema3 + c2 * ema2 + c3 * ema1 + c4 * closes
    return t3


def calculate_beta(asset_closes: pd.Series, benchmark_closes: pd.Series, period: int = 21) -> pd.Series:
    """Calculate Beta relative to benchmark"""
    asset_returns = asset_closes.pct_change()
    benchmark_returns = benchmark_closes.pct_change()

    covariance = asset_returns.rolling(window=period).cov(benchmark_returns)
    variance = benchmark_returns.rolling(window=period).var()

    beta = covariance / variance
    return beta


def calculate_correlation(asset1: pd.Series, asset2: pd.Series, period: int = 21) -> pd.Series:
    """Calculate Rolling Correlation"""
    return asset1.rolling(window=period).corr(asset2)


def calculate_elders_ray(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 13) -> Tuple[pd.Series, pd.Series]:
    """Calculate Elder-Ray Index"""
    ema = closes.ewm(span=period, adjust=False).mean()

    bull_power = highs - ema
    bear_power = lows - ema

    return bull_power, bear_power


def calculate_force_index(closes: pd.Series, volumes: pd.Series, period: int = 13) -> pd.Series:
    """Calculate Force Index"""
    fi = closes.diff(period) * volumes.rolling(window=period).mean()
    return fi


def calculate_mass_index(highs: pd.Series, lows: pd.Series, period: int = 25) -> pd.Series:
    """Calculate Mass Index"""
    ema_range = (highs - lows).ewm(span=9, adjust=False).mean()
    mass = ema_range.rolling(window=period).sum()
    return mass


def calculate_zlema(closes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Zero Lag Exponential Moving Average"""
    lag = int((period - 1) / 2)
    zlema = closes.ewm(span=period, adjust=False).mean()
    zlema = (2 * zlema - zlema.shift(lag)).ewm(span=period, adjust=False).mean()
    return zlema


def calculate_psar(highs: pd.Series, lows: pd.Series, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    """Calculate Parabolic SAR"""
    return TechnicalIndicators().parabolic_sar(highs, lows, step, max_step)


def calculate_supertrend(highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """Calculate SuperTrend"""
    return TechnicalIndicators().supertrend(highs, lows, closes, period, multiplier)


def calculate_ichimoku(highs: pd.Series, lows: pd.Series, closes: pd.Series, conversion_period: int = 9, base_period: int = 26, lagging_span: int = 52, displacement: int = 26) -> Dict[str, pd.Series]:
    """Calculate Ichimoku Cloud"""
    return TechnicalIndicators().ichimoku_cloud(highs, lows, conversion_period, base_period, lagging_span, displacement)


def calculate_all(highs: pd.Series, lows: pd.Series, closes: pd.Series, volumes: pd.Series = None) -> Dict[str, pd.Series]:
    """Calculate all indicators (convenience function)"""
    return TechnicalIndicators().get_all_indicators(highs, lows, closes, volumes)
