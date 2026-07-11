"""Technical Factors — Momentum, Mean-Reversion, Volatility.

Implements standard technical analysis factors commonly used in quantitative
trading strategies. These are market-agnostic and work across equities,
crypto, forex, and futures.

Categories:
- Momentum: price momentum, rate of change, relative strength
- Mean-Reversion: distance from moving averages, z-scores
- Volatility: realized vol, ATR, Bollinger width
- Volume: OBV, volume ratio, VWAP deviation
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import AlphaFactor, FactorMeta


class MomentumFactor(AlphaFactor):
    """Price momentum factor (N-period return).

    Formula: close / close.shift(n) - 1
    """

    @property
    def name(self) -> str:
        return "momentum"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="technical_momentum",
            zoo="technical",
            theme=["momentum"],
            formula_latex=r"\frac{C_t}{C_{t-n}} - 1",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=20,
            min_warmup_bars=21,
        )

    def __init__(self, period: int = 20) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        result = close / close.shift(self._period) - 1.0
        return result.replace([np.inf, -np.inf], np.nan)


class RateOfChangeFactor(AlphaFactor):
    """Rate of Change (ROC) factor.

    Formula: (close - close.shift(n)) / close.shift(n) * 100
    """

    @property
    def name(self) -> str:
        return f"roc_{self._period}"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id=f"technical_roc_{self._period}",
            zoo="technical",
            theme=["momentum"],
            formula_latex=r"\frac{C_t - C_{t-n}}{C_{t-n}} \times 100",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=self._period,
            min_warmup_bars=self._period + 1,
        )

    def __init__(self, period: int = 12) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        prev = close.shift(self._period)
        result = (close - prev) / prev * 100.0
        return result.replace([np.inf, -np.inf], np.nan)


class MeanReversionFactor(AlphaFactor):
    """Mean reversion factor — z-score of price vs moving average.

    Formula: (close - SMA(close, n)) / STD(close, n)
    """

    @property
    def name(self) -> str:
        return f"mean_reversion_{self._period}"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id=f"technical_mean_reversion_{self._period}",
            zoo="technical",
            theme=["reversal"],
            formula_latex=r"\frac{C_t - \text{SMA}(C, n)}{\sigma(C, n)}",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=self._period,
            min_warmup_bars=self._period + 1,
            notes="Z-score distance from moving average; negative = oversold",
        )

    def __init__(self, period: int = 20) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        ma = close.rolling(window=self._period, min_periods=self._period).mean()
        std = close.rolling(window=self._period, min_periods=self._period).std(ddof=1)
        result = (close - ma) / std.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class RealizedVolatilityFactor(AlphaFactor):
    """Realized volatility factor.

    Formula: STD(returns, n) * sqrt(252)
    """

    @property
    def name(self) -> str:
        return f"realized_vol_{self._period}"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id=f"technical_realized_vol_{self._period}",
            zoo="technical",
            theme=["volatility"],
            formula_latex=r"\sigma(r, n) \times \sqrt{252}",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=self._period,
            min_warmup_bars=self._period + 1,
        )

    def __init__(self, period: int = 20) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        returns = df["close"].pct_change()
        result = returns.rolling(window=self._period, min_periods=self._period).std(ddof=1) * np.sqrt(252)
        return result


class ATRFactor(AlphaFactor):
    """Average True Range (ATR) factor.

    Formula: ATR(n) / close (normalized)
    """

    @property
    def name(self) -> str:
        return f"atr_{self._period}"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id=f"technical_atr_{self._period}",
            zoo="technical",
            theme=["volatility"],
            formula_latex=r"\frac{\text{ATR}(n)}{C_t}",
            columns_required=["high", "low", "close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=self._period,
            min_warmup_bars=self._period + 1,
            notes="Normalized ATR for cross-asset comparison",
        )

    def __init__(self, period: int = 14) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=self._period, min_periods=self._period).mean()
        result = atr / close.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class BollingerWidthFactor(AlphaFactor):
    """Bollinger Band Width factor.

    Formula: 2 * STD(close, n) / SMA(close, n)
    """

    @property
    def name(self) -> str:
        return f"bollinger_width_{self._period}"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id=f"technical_bollinger_width_{self._period}",
            zoo="technical",
            theme=["volatility"],
            formula_latex=r"\frac{2\sigma(C, n)}{\text{SMA}(C, n)}",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=self._period,
            min_warmup_bars=self._period + 1,
        )

    def __init__(self, period: int = 20) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        ma = close.rolling(window=self._period, min_periods=self._period).mean()
        std = close.rolling(window=self._period, min_periods=self._period).std(ddof=1)
        result = 2.0 * std / ma.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class VolumeRatioFactor(AlphaFactor):
    """Volume ratio factor — current volume vs average volume.

    Formula: volume / SMA(volume, n)
    """

    @property
    def name(self) -> str:
        return f"volume_ratio_{self._period}"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id=f"technical_volume_ratio_{self._period}",
            zoo="technical",
            theme=["volume"],
            formula_latex=r"\frac{V_t}{\text{SMA}(V, n)}",
            columns_required=["volume"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=self._period,
            min_warmup_bars=self._period + 1,
        )

    def __init__(self, period: int = 20) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        vol = df["volume"]
        avg_vol = vol.rolling(window=self._period, min_periods=self._period).mean()
        result = vol / avg_vol.replace(0, np.nan)
        return result.replace([np.inf, -np.inf], np.nan)


class RSIFactor(AlphaFactor):
    """Relative Strength Index (RSI) factor.

    Formula: 100 - 100 / (1 + avg_gain / avg_loss)
    """

    @property
    def name(self) -> str:
        return f"rsi_{self._period}"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id=f"technical_rsi_{self._period}",
            zoo="technical",
            theme=["reversal", "momentum"],
            formula_latex=r"100 - \frac{100}{1 + \frac{\text{avg\_gain}}{\text{avg\_loss}}}",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=self._period,
            min_warmup_bars=self._period + 1,
        )

    def __init__(self, period: int = 14) -> None:
        self._period = period

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=self._period, min_periods=self._period).mean()
        avg_loss = loss.rolling(window=self._period, min_periods=self._period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        result = 100.0 - 100.0 / (1.0 + rs)
        return result


class MACDHistogramFactor(AlphaFactor):
    """MACD Histogram factor.

    Formula: MACD_line - Signal_line
    Where MACD_line = EMA(12) - EMA(26), Signal_line = EMA(MACD, 9)
    """

    @property
    def name(self) -> str:
        return "macd_histogram"

    @property
    def meta(self) -> FactorMeta:
        return FactorMeta(
            id="technical_macd_histogram",
            zoo="technical",
            theme=["momentum", "reversal"],
            formula_latex=r"\text{MACD} - \text{Signal}",
            columns_required=["close"],
            universe=["equity_us", "equity_cn", "crypto", "forex", "futures"],
            decay_horizon=26,
            min_warmup_bars=35,
        )

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line - signal_line


def get_all_technical_factors() -> list:
    """Return instances of all implemented technical factors."""
    return [
        MomentumFactor(20),
        RateOfChangeFactor(12),
        MeanReversionFactor(20),
        RealizedVolatilityFactor(20),
        ATRFactor(14),
        BollingerWidthFactor(20),
        VolumeRatioFactor(20),
        RSIFactor(14),
        MACDHistogramFactor(),
    ]
