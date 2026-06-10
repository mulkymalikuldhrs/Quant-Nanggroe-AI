"""
Alpha101 Factors — Top 20 WorldQuant Alpha factors
====================================================
Implementation of the most commonly used factors from
"101 Formulaic Alphas" by Zura Kakushadze.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def alpha001(close: pd.Series, returns: pd.Series, volume: pd.Series) -> pd.Series:
    """Alpha#1: (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)"""
    inner = close.copy()
    inner[returns < 0] = returns[returns < 0].rolling(20).std()
    return inner.rolling(5).apply(lambda x: np.argmax(x ** 2)).rank(pct=True) - 0.5


def alpha002(close: pd.Series, open_: pd.Series, volume: pd.Series) -> pd.Series:
    """Alpha#2: (-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))"""
    delta_log_vol = np.log(volume).diff(2).rank(pct=True)
    price_ratio = ((close - open_) / open_).rank(pct=True)
    return -1 * delta_log_vol.rolling(6).corr(price_ratio)


def alpha003(close: pd.Series, open_: pd.Series, volume: pd.Series) -> pd.Series:
    """Alpha#3: (-1 * correlation(rank(open), rank(volume), 10))"""
    return -1 * open_.rank(pct=True).rolling(10).corr(volume.rank(pct=True))


def alpha006(close: pd.Series, open_: pd.Series, volume: pd.Series) -> pd.Series:
    """Alpha#6: (-1 * correlation(open, volume, 10))"""
    return -1 * open_.rolling(10).corr(volume)


def alpha012(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Alpha#12: (sign(delta(volume, 1)) * (-1 * delta(close, 1)))"""
    return np.sign(volume.diff(1)) * (-1 * close.diff(1))


def alpha014(close: pd.Series, open_: pd.Series, volume: pd.Series, returns: pd.Series) -> pd.Series:
    """Alpha#14: (-1 * rank(delta(returns, 3)) * correlation(open, volume, 10))"""
    return -1 * returns.diff(3).rank(pct=True) * open_.rolling(10).corr(volume)


def alpha015(close: pd.Series, high: pd.Series, volume: pd.Series) -> pd.Series:
    """Alpha#15: (-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3))"""
    corr = high.rank(pct=True).rolling(3).corr(volume.rank(pct=True))
    return -1 * corr.rank(pct=True).rolling(3).sum()


def alpha020(close: pd.Series, open_: pd.Series, high: pd.Series, low: pd.Series) -> pd.Series:
    """Alpha#20: (((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1)))) * rank((open - delay(low, 1))))"""
    return (
        -1
        * (open_ - high.shift(1)).rank(pct=True)
        * (open_ - close.shift(1)).rank(pct=True)
        * (open_ - low.shift(1)).rank(pct=True)
    )


def alpha023(high: pd.Series) -> pd.Series:
    """Alpha#23: (((sum(high, 20) / 20) < high) ? (-1 * delta(high, 2)) : 0)"""
    sma20 = high.rolling(20).mean()
    result = pd.Series(0.0, index=high.index)
    mask = sma20 < high
    result[mask] = -1 * high.diff(2)[mask]
    return result


def alpha026(close: pd.Series, high: pd.Series, volume: pd.Series, returns: pd.Series) -> pd.Series:
    """Alpha#26: (-1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3))"""
    vol_rank = volume.rolling(5).rank(pct=True)
    high_rank = high.rolling(5).rank(pct=True)
    corr = vol_rank.rolling(5).corr(high_rank)
    return -1 * corr.rolling(3).max()


# Registry of all alpha factors
ALPHA_FACTORS: dict[str, object] = {
    "alpha001": alpha001,
    "alpha002": alpha002,
    "alpha003": alpha003,
    "alpha006": alpha006,
    "alpha012": alpha012,
    "alpha014": alpha014,
    "alpha015": alpha015,
    "alpha020": alpha020,
    "alpha023": alpha023,
    "alpha026": alpha026,
}
