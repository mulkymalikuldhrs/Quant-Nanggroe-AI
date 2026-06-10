"""WorldQuant 101 Alphas (Kakushadze 2015).

Implements ALL 101 alphas from:
"101 Formulaic Alphas" by Zura Kakushadze, arXiv:1601.00991

Each alpha uses the __alpha_meta__ + compute(panel) pattern.
Adapted to use Quant-Nanggroe-AI base.py operators.

Reference: https://arxiv.org/abs/1601.00991
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    decay_linear,
    delta,
    rank,
    safe_div,
    scale,
    signed_power,
    ts_argmax,
    ts_argmin,
    ts_corr,
    ts_cov,
    ts_max,
    ts_mean,
    ts_min,
    ts_rank,
    ts_std,
    vwap,
)

# ─── Shared Helper Functions ────────────────────────────────────────────

def _delay(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Backward shift by n (lookahead-safe; n>=1 required)."""
    if n < 1:
        raise ValueError("delay requires n >= 1 (lookahead ban)")
    return df.shift(n)


def _ind_neutralize(x: pd.DataFrame, panel: dict) -> pd.DataFrame:
    """Industry/sector neutralize: subtract the row-wise sector group mean.

    If panel has a 'sector' DataFrame (same shape as close), subtract the
    per-sector cross-sectional mean per row. If absent, degrade to global
    cross-sectional demean (subtract row mean). This is a degraded fallback
    relative to the paper's industry/subindustry neutralization; see notes.
    """
    sector_df = panel.get("sector")
    if sector_df is None:
        row_mean = x.mean(axis=1, skipna=True)
        return x.sub(row_mean, axis=0)
    # Per-row group demean. Iterate rows; numpy-fast enough for small panels.
    arr = x.to_numpy(dtype=np.float64, na_value=np.nan).copy()
    sec_arr = sector_df.to_numpy()
    n_rows = arr.shape[0]
    for i in range(n_rows):
        row = arr[i]
        sec_row = sec_arr[i]
        for tag in pd.unique(sec_row):
            mask = sec_row == tag
            vals = row[mask]
            finite = vals[~np.isnan(vals)]
            if finite.size == 0:
                continue
            mean = finite.mean()
            row[mask] = vals - mean
        arr[i] = row
    return pd.DataFrame(arr, index=x.index, columns=x.columns)


def _make_one(ref: pd.DataFrame) -> pd.DataFrame:
    """A DataFrame of 1.0 with the same shape/index/columns as ``ref``."""
    return pd.DataFrame(1.0, index=ref.index, columns=ref.columns)


def _rolling_prod(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Rolling window product; warmup -> NaN."""
    return df.rolling(window=n, min_periods=n).apply(np.prod, raw=True)


def _rolling_sum(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Rolling window sum; warmup -> NaN."""
    return df.rolling(window=n, min_periods=n).sum()


def _where_ternary(cond, a, b):
    """Vectorised ternary `(cond ? a : b)` returning a DataFrame.

    ``cond`` is a boolean DataFrame; ``a`` / ``b`` may be DataFrame or scalar.
    """
    if isinstance(a, (int, float)):
        a_arr = np.full_like(cond.to_numpy(dtype=np.float64), float(a))
    else:
        a_arr = a.to_numpy(dtype=np.float64, na_value=np.nan)
    if isinstance(b, (int, float)):
        b_arr = np.full_like(cond.to_numpy(dtype=np.float64), float(b))
    else:
        b_arr = b.to_numpy(dtype=np.float64, na_value=np.nan)
    cond_arr = cond.to_numpy(dtype=bool, na_value=False) if hasattr(cond, "to_numpy") else np.asarray(cond, dtype=bool)
    out = np.where(cond_arr, a_arr, b_arr)
    out = np.where(np.isfinite(out), out, np.nan)
    idx = cond.index if hasattr(cond, "index") else a.index
    cols = cond.columns if hasattr(cond, "columns") else a.columns
    return pd.DataFrame(out, index=idx, columns=cols)


__alpha_meta_alpha_001 = {
    'id': 'alpha101_001',
    'nickname': 'Kakushadze Alpha #1',
    'theme': ['reversal', 'volatility'],
    'formula_latex': 'rank(ts_argmax(SignedPower((returns<0)?stddev(returns,20):close, 2.), 5)) - 0.5',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_001(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    cond = (returns < 0).astype(float)
    x = ts_std(returns, 20) * cond + close * (1.0 - cond)
    out = rank(ts_argmax(signed_power(x, 2.0), 5)) - 0.5
    return out


__alpha_meta_alpha_002 = {
    'id': 'alpha101_002',
    'nickname': 'Kakushadze Alpha #2',
    'theme': ['volume', 'reversal'],
    'formula_latex': '-1 * correlation(rank(delta(log(volume), 2)), rank(((close-open)/open)), 6)',
    'columns_required': ['open', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_002(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * ts_corr(rank(delta(np.log(volume), 2)), rank((close - open_) / open_), 6)
    return out


__alpha_meta_alpha_003 = {
    'id': 'alpha101_003',
    'nickname': 'Kakushadze Alpha #3',
    'theme': ['volume', 'reversal'],
    'formula_latex': '-1 * correlation(rank(open), rank(volume), 10)',
    'columns_required': ['open', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_003(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * ts_corr(rank(open_), rank(volume), 10)
    return out


__alpha_meta_alpha_004 = {
    'id': 'alpha101_004',
    'nickname': 'Kakushadze Alpha #4',
    'theme': ['reversal'],
    'formula_latex': '-1 * Ts_Rank(rank(low), 9)',
    'columns_required': ['low', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 9,
    'notes': '',
}


def compute_alpha_004(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    low = panel["low"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * ts_rank(rank(low), 9)
    return out


__alpha_meta_alpha_005 = {
    'id': 'alpha101_005',
    'nickname': 'Kakushadze Alpha #5',
    'theme': ['reversal'],
    'formula_latex': 'rank((open - sum(vwap,10)/10)) * (-1 * abs(rank((close - vwap))))',
    'columns_required': ['open', 'close', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_005(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    out = rank(open_ - rolling_sum(vwap, 10) / 10.0) * (-1.0 * rank(close - vwap).abs())
    return out


__alpha_meta_alpha_006 = {
    'id': 'alpha101_006',
    'nickname': 'Kakushadze Alpha #6',
    'theme': ['volume', 'reversal'],
    'formula_latex': '-1 * correlation(open, volume, 10)',
    'columns_required': ['open', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_006(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * ts_corr(open_, volume, 10)
    return out


__alpha_meta_alpha_007 = {
    'id': 'alpha101_007',
    'nickname': 'Kakushadze Alpha #7',
    'theme': ['momentum', 'volume'],
    'formula_latex': '(adv20<volume)?((-1*ts_rank(abs(delta(close,7)),60))*sign(delta(close,7))):(-1)',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 67,
    'notes': '',
}


def compute_alpha_007(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    make_one = _make_one
    where_ternary = _where_ternary
    d7 = delta(close, 7)
    expr = (-1.0 * ts_rank(d7.abs(), 60)) * np.sign(d7)
    out = where_ternary(adv20 < volume, expr, -1.0 * make_one(close))
    return out


__alpha_meta_alpha_008 = {
    'id': 'alpha101_008',
    'nickname': 'Kakushadze Alpha #8',
    'theme': ['reversal'],
    'formula_latex': '-1 * rank((sum(open,5)*sum(returns,5)) - delay(sum(open,5)*sum(returns,5),10))',
    'columns_required': ['open', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 15,
    'notes': '',
}


def compute_alpha_008(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]

    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    s = rolling_sum(open_, 5) * rolling_sum(returns, 5)
    out = -1.0 * rank(s - delay(s, 10))
    return out


__alpha_meta_alpha_009 = {
    'id': 'alpha101_009',
    'nickname': 'Kakushadze Alpha #9',
    'theme': ['momentum'],
    'formula_latex': '(0<ts_min(delta(close,1),5))?delta(close,1):((ts_max(delta(close,1),5)<0)?delta(close,1):(-1*delta(close,1)))',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 6,
    'notes': '',
}


def compute_alpha_009(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    where_ternary = _where_ternary
    d1 = delta(close, 1)
    cond1 = ts_min(d1, 5) > 0
    cond2 = ts_max(d1, 5) < 0
    out = where_ternary(cond1, d1, where_ternary(cond2, d1, -1.0 * d1))
    return out


__alpha_meta_alpha_010 = {
    'id': 'alpha101_010',
    'nickname': 'Kakushadze Alpha #10',
    'theme': ['momentum'],
    'formula_latex': 'rank((0<ts_min(delta(close,1),4))?delta(close,1):((ts_max(delta(close,1),4)<0)?delta(close,1):(-1*delta(close,1))))',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
    'notes': '',
}


def compute_alpha_010(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    where_ternary = _where_ternary
    d1 = delta(close, 1)
    cond1 = ts_min(d1, 4) > 0
    cond2 = ts_max(d1, 4) < 0
    inner = where_ternary(cond1, d1, where_ternary(cond2, d1, -1.0 * d1))
    out = rank(inner)
    return out


__alpha_meta_alpha_011 = {
    'id': 'alpha101_011',
    'nickname': 'Kakushadze Alpha #11',
    'theme': ['volume', 'reversal'],
    'formula_latex': '(rank(ts_max(vwap-close,3))+rank(ts_min(vwap-close,3)))*rank(delta(volume,3))',
    'columns_required': ['close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
    'notes': '',
}


def compute_alpha_011(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    diff = vwap - close
    out = (rank(ts_max(diff, 3)) + rank(ts_min(diff, 3))) * rank(delta(volume, 3))
    return out


__alpha_meta_alpha_012 = {
    'id': 'alpha101_012',
    'nickname': 'Kakushadze Alpha #12',
    'theme': ['volume', 'reversal'],
    'formula_latex': 'sign(delta(volume,1)) * (-1 * delta(close,1))',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 2,
    'notes': '',
}


def compute_alpha_012(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = np.sign(delta(volume, 1)) * (-1.0 * delta(close, 1))
    return out


__alpha_meta_alpha_013 = {
    'id': 'alpha101_013',
    'nickname': 'Kakushadze Alpha #13',
    'theme': ['volume'],
    'formula_latex': '-1 * rank(covariance(rank(close), rank(volume), 5))',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
    'notes': '',
}


def compute_alpha_013(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * rank(ts_cov(rank(close), rank(volume), 5))
    return out


__alpha_meta_alpha_014 = {
    'id': 'alpha101_014',
    'nickname': 'Kakushadze Alpha #14',
    'theme': ['volume', 'momentum'],
    'formula_latex': '(-1*rank(delta(returns,3))) * correlation(open, volume, 10)',
    'columns_required': ['open', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_014(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    volume = panel["volume"]

    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = (-1.0 * rank(delta(returns, 3))) * ts_corr(open_, volume, 10)
    return out


__alpha_meta_alpha_015 = {
    'id': 'alpha101_015',
    'nickname': 'Kakushadze Alpha #15',
    'theme': ['volume'],
    'formula_latex': '-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3)',
    'columns_required': ['high', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 6,
    'notes': '',
}


def compute_alpha_015(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    out = -1.0 * rolling_sum(rank(ts_corr(rank(high), rank(volume), 3)), 3)
    return out


__alpha_meta_alpha_016 = {
    'id': 'alpha101_016',
    'nickname': 'Kakushadze Alpha #16',
    'theme': ['volume'],
    'formula_latex': '-1 * rank(covariance(rank(high), rank(volume), 5))',
    'columns_required': ['high', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
    'notes': '',
}


def compute_alpha_016(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * rank(ts_cov(rank(high), rank(volume), 5))
    return out


__alpha_meta_alpha_017 = {
    'id': 'alpha101_017',
    'nickname': 'Kakushadze Alpha #17',
    'theme': ['volume', 'reversal'],
    'formula_latex': '((-1*rank(ts_rank(close,10)))*rank(delta(delta(close,1),1)))*rank(ts_rank(volume/adv20,5))',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_017(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = (-1.0 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1)) * rank(ts_rank(safe_div(volume, adv20), 5))
    return out


__alpha_meta_alpha_018 = {
    'id': 'alpha101_018',
    'nickname': 'Kakushadze Alpha #18',
    'theme': ['volatility'],
    'formula_latex': '-1 * rank(stddev(abs(close-open),5) + (close-open) + correlation(close,open,10))',
    'columns_required': ['open', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_018(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    diff = (close - open_)
    out = -1.0 * rank(ts_std(diff.abs(), 5) + diff + ts_corr(close, open_, 10))
    return out


__alpha_meta_alpha_019 = {
    'id': 'alpha101_019',
    'nickname': 'Kakushadze Alpha #19',
    'theme': ['momentum'],
    'formula_latex': '(-1*sign((close-delay(close,7))+delta(close,7))) * (1+rank(1+sum(returns,250)))',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 250,
    'notes': 'Very long lookback (>= ~100 bars); produces NaN warmup on short panels which may trigger the >95% NaN registry guard.',
}


def compute_alpha_019(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    out = (-1.0 * np.sign((close - delay(close, 7)) + delta(close, 7))) * (1.0 + rank(1.0 + rolling_sum(returns, 250)))
    return out


__alpha_meta_alpha_020 = {
    'id': 'alpha101_020',
    'nickname': 'Kakushadze Alpha #20',
    'theme': ['reversal'],
    'formula_latex': '(((-1*rank(open-delay(high,1)))*rank(open-delay(close,1)))*rank(open-delay(low,1)))',
    'columns_required': ['open', 'high', 'low', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 2,
    'notes': '',
}


def compute_alpha_020(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    delay = _delay
    out = ((-1.0 * rank(open_ - delay(high, 1))) * rank(open_ - delay(close, 1))) * rank(open_ - delay(low, 1))
    return out


__alpha_meta_alpha_021 = {
    'id': 'alpha101_021',
    'nickname': 'Kakushadze Alpha #21',
    'theme': ['momentum', 'volatility'],
    'formula_latex': 'complex piecewise; see paper',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_021(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    make_one = _make_one
    where_ternary = _where_ternary
    m8 = rolling_sum(close, 8) / 8.0
    s8 = ts_std(close, 8)
    m2 = rolling_sum(close, 2) / 2.0
    v_adv = safe_div(volume, adv20)
    cond_a = (m8 + s8) < m2
    cond_b = m2 < (m8 - s8)
    cond_c = (v_adv >= 1.0)
    one = make_one(close)
    out = where_ternary(cond_a, -1.0 * one, where_ternary(cond_b, one, where_ternary(cond_c, one, -1.0 * one)))
    return out


__alpha_meta_alpha_022 = {
    'id': 'alpha101_022',
    'nickname': 'Kakushadze Alpha #22',
    'theme': ['volume', 'volatility'],
    'formula_latex': '-1 * (delta(correlation(high,volume,5),5) * rank(stddev(close,20)))',
    'columns_required': ['high', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_022(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * (delta(ts_corr(high, volume, 5), 5) * rank(ts_std(close, 20)))
    return out


__alpha_meta_alpha_023 = {
    'id': 'alpha101_023',
    'nickname': 'Kakushadze Alpha #23',
    'theme': ['momentum'],
    'formula_latex': '((sum(high,20)/20) < high) ? (-1*delta(high,2)) : 0',
    'columns_required': ['high', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_023(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    where_ternary = _where_ternary
    mh = rolling_sum(high, 20) / 20.0
    out = where_ternary(mh < high, -1.0 * delta(high, 2), 0.0 * close)
    return out


__alpha_meta_alpha_024 = {
    'id': 'alpha101_024',
    'nickname': 'Kakushadze Alpha #24',
    'theme': ['momentum'],
    'formula_latex': 'complex piecewise; see paper',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 200,
    'notes': 'Very long lookback (>= ~100 bars); produces NaN warmup on short panels which may trigger the >95% NaN registry guard.',
}


def compute_alpha_024(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    where_ternary = _where_ternary
    m100 = rolling_sum(close, 100) / 100.0
    x = safe_div(delta(m100, 100), delay(close, 100))
    cond = x <= 0.05
    left = -1.0 * (close - ts_min(close, 100))
    right = -1.0 * delta(close, 3)
    out = where_ternary(cond, left, right)
    return out


__alpha_meta_alpha_025 = {
    'id': 'alpha101_025',
    'nickname': 'Kakushadze Alpha #25',
    'theme': ['momentum', 'volume'],
    'formula_latex': 'rank((((-1*returns)*adv20)*vwap)*(high-close))',
    'columns_required': ['high', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_025(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv20 = ts_mean(volume, 20)
    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = rank(((-1.0 * returns) * adv20) * vwap * (high - close))
    return out


__alpha_meta_alpha_026 = {
    'id': 'alpha101_026',
    'nickname': 'Kakushadze Alpha #26',
    'theme': ['volume'],
    'formula_latex': '-1 * ts_max(correlation(ts_rank(volume,5),ts_rank(high,5),5),3)',
    'columns_required': ['high', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 13,
    'notes': '',
}


def compute_alpha_026(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * ts_max(ts_corr(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)
    return out


__alpha_meta_alpha_027 = {
    'id': 'alpha101_027',
    'nickname': 'Kakushadze Alpha #27',
    'theme': ['volume'],
    'formula_latex': '(0.5<rank((sum(correlation(rank(volume),rank(vwap),6),2)/2.0)))?(-1):1',
    'columns_required': ['volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_027(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    make_one = _make_one
    where_ternary = _where_ternary
    x = rank(rolling_sum(ts_corr(rank(volume), rank(vwap), 6), 2) / 2.0)
    out = where_ternary(x > 0.5, -1.0 * make_one(close), make_one(close))
    return out


__alpha_meta_alpha_028 = {
    'id': 'alpha101_028',
    'nickname': 'Kakushadze Alpha #28',
    'theme': ['volume'],
    'formula_latex': 'scale((correlation(adv20,low,5) + (high+low)/2) - close)',
    'columns_required': ['high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_028(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = scale(ts_corr(adv20, low, 5) + (high + low) / 2.0 - close)
    return out


__alpha_meta_alpha_029 = {
    'id': 'alpha101_029',
    'nickname': 'Kakushadze Alpha #29',
    'theme': ['reversal', 'volume'],
    'formula_latex': 'min(product(rank(rank(scale(log(sum(ts_min(rank(rank(-1*rank(delta(close-1,5)))),2),1))))),1),5) + ts_rank(delay(-1*returns,6),5)',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 12,
    'notes': '',
}


def compute_alpha_029(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    rolling_prod = _rolling_prod
    delay = _delay
    inner = rank(rank(-1.0 * rank(delta(close - 1.0, 5))))
    inner = ts_min(inner, 2)
    inner = rolling_sum(inner, 1)
    inner = np.log(inner.where(inner > 0))
    inner = scale(inner)
    inner = rank(rank(inner))
    inner = rolling_prod(inner, 1)
    term1 = ts_min(inner, 5)
    term2 = ts_rank(delay(-1.0 * returns, 6), 5)
    out = term1 + term2
    return out


__alpha_meta_alpha_030 = {
    'id': 'alpha101_030',
    'nickname': 'Kakushadze Alpha #30',
    'theme': ['momentum', 'volume'],
    'formula_latex': '((1-rank(sign(d1)+sign(d2)+sign(d3))) * sum(volume,5)) / sum(volume,20)',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 20,
    'notes': '',
}


def compute_alpha_030(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    s = np.sign(close - delay(close, 1)) + np.sign(delay(close, 1) - delay(close, 2)) + np.sign(delay(close, 2) - delay(close, 3))
    out = safe_div((1.0 - rank(s)) * rolling_sum(volume, 5), rolling_sum(volume, 20))
    return out


__alpha_meta_alpha_031 = {
    'id': 'alpha101_031',
    'nickname': 'Kakushadze Alpha #31',
    'theme': ['momentum'],
    'formula_latex': 'rank(rank(rank(decay_linear(-1*rank(rank(delta(close,10))),10)))) + rank(-1*delta(close,3)) + sign(scale(correlation(adv20,low,12)))',
    'columns_required': ['low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_031(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    low = panel["low"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    t1 = rank(rank(rank(decay_linear(-1.0 * rank(rank(delta(close, 10))), 10))))
    t2 = rank(-1.0 * delta(close, 3))
    t3 = pd.DataFrame(np.sign(scale(ts_corr(adv20, low, 12)).to_numpy(dtype=np.float64, na_value=np.nan)), index=close.index, columns=close.columns)
    out = t1 + t2 + t3
    return out


__alpha_meta_alpha_032 = {
    'id': 'alpha101_032',
    'nickname': 'Kakushadze Alpha #32',
    'theme': ['momentum'],
    'formula_latex': 'scale(sum(close,7)/7 - close) + 20*scale(correlation(vwap, delay(close,5), 230))',
    'columns_required': ['close', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 235,
    'notes': 'Very long lookback (>= ~100 bars); produces NaN warmup on short panels which may trigger the >95% NaN registry guard.',
}


def compute_alpha_032(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    out = scale(rolling_sum(close, 7) / 7.0 - close) + 20.0 * scale(ts_corr(vwap, delay(close, 5), 230))
    return out


__alpha_meta_alpha_033 = {
    'id': 'alpha101_033',
    'nickname': 'Kakushadze Alpha #33',
    'theme': ['reversal'],
    'formula_latex': 'rank(-1*(1-open/close))',
    'columns_required': ['open', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_033(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = rank(-1.0 * (1.0 - safe_div(open_, close)))
    return out


__alpha_meta_alpha_034 = {
    'id': 'alpha101_034',
    'nickname': 'Kakushadze Alpha #34',
    'theme': ['volatility'],
    'formula_latex': 'rank((1-rank(stddev(returns,2)/stddev(returns,5))) + (1-rank(delta(close,1))))',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 6,
    'notes': '',
}


def compute_alpha_034(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = rank((1.0 - rank(safe_div(ts_std(returns, 2), ts_std(returns, 5)))) + (1.0 - rank(delta(close, 1))))
    return out


__alpha_meta_alpha_035 = {
    'id': 'alpha101_035',
    'nickname': 'Kakushadze Alpha #35',
    'theme': ['volume', 'momentum'],
    'formula_latex': 'ts_rank(volume,32) * (1 - ts_rank((close+high-low),16)) * (1 - ts_rank(returns,32))',
    'columns_required': ['high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 33,
    'notes': '',
}


def compute_alpha_035(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]

    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = ts_rank(volume, 32) * (1.0 - ts_rank((close + high - low), 16)) * (1.0 - ts_rank(returns, 32))
    return out


__alpha_meta_alpha_036 = {
    'id': 'alpha101_036',
    'nickname': 'Kakushadze Alpha #36',
    'theme': ['momentum', 'volume'],
    'formula_latex': 'weighted sum; see paper',
    'columns_required': ['open', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 200,
    'notes': 'Very long lookback (>= ~100 bars); produces NaN warmup on short panels which may trigger the >95% NaN registry guard.',
}


def compute_alpha_036(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv20 = ts_mean(volume, 20)
    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    t1 = 2.21 * rank(ts_corr((close - open_), delay(volume, 1), 15))
    t2 = 0.7 * rank(open_ - close)
    t3 = 0.73 * rank(ts_rank(delay(-1.0 * returns, 6), 5))
    t4 = rank(ts_corr(vwap, adv20, 6).abs())
    t5 = 0.6 * rank((rolling_sum(close, 200) / 200.0 - open_) * (close - open_))
    out = t1 + t2 + t3 + t4 + t5
    return out


__alpha_meta_alpha_037 = {
    'id': 'alpha101_037',
    'nickname': 'Kakushadze Alpha #37',
    'theme': ['momentum'],
    'formula_latex': 'rank(correlation(delay(open-close,1),close,200)) + rank(open-close)',
    'columns_required': ['open', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 201,
    'notes': 'Very long lookback (>= ~100 bars); produces NaN warmup on short panels which may trigger the >95% NaN registry guard.',
}


def compute_alpha_037(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    delay = _delay
    out = rank(ts_corr(delay(open_ - close, 1), close, 200)) + rank(open_ - close)
    return out


__alpha_meta_alpha_038 = {
    'id': 'alpha101_038',
    'nickname': 'Kakushadze Alpha #38',
    'theme': ['reversal'],
    'formula_latex': '(-1*rank(ts_rank(close,10))) * rank(close/open)',
    'columns_required': ['open', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_038(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = (-1.0 * rank(ts_rank(close, 10))) * rank(safe_div(close, open_))
    return out


__alpha_meta_alpha_039 = {
    'id': 'alpha101_039',
    'nickname': 'Kakushadze Alpha #39',
    'theme': ['momentum', 'volume'],
    'formula_latex': '(-1*rank(delta(close,7)*(1-rank(decay_linear(volume/adv20,9))))) * (1+rank(sum(returns,250)))',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 250,
    'notes': 'Very long lookback (>= ~100 bars); produces NaN warmup on short panels which may trigger the >95% NaN registry guard.',
}


def compute_alpha_039(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)
    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    out = (-1.0 * rank(delta(close, 7) * (1.0 - rank(decay_linear(safe_div(volume, adv20), 9))))) * (1.0 + rank(rolling_sum(returns, 250)))
    return out


__alpha_meta_alpha_040 = {
    'id': 'alpha101_040',
    'nickname': 'Kakushadze Alpha #40',
    'theme': ['volatility', 'volume'],
    'formula_latex': '(-1*rank(stddev(high,10))) * correlation(high,volume,10)',
    'columns_required': ['high', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_040(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = (-1.0 * rank(ts_std(high, 10))) * ts_corr(high, volume, 10)
    return out


__alpha_meta_alpha_041 = {
    'id': 'alpha101_041',
    'nickname': 'Kakushadze Alpha #41',
    'theme': ['reversal'],
    'formula_latex': '(high*low)^0.5 - vwap',
    'columns_required': ['high', 'low', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_041(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    low = panel["low"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = (high * low).pow(0.5) - vwap
    return out


__alpha_meta_alpha_042 = {
    'id': 'alpha101_042',
    'nickname': 'Kakushadze Alpha #42',
    'theme': ['reversal'],
    'formula_latex': 'rank(vwap-close) / rank(vwap+close)',
    'columns_required': ['close', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_042(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = safe_div(rank(vwap - close), rank(vwap + close))
    return out


__alpha_meta_alpha_043 = {
    'id': 'alpha101_043',
    'nickname': 'Kakushadze Alpha #43',
    'theme': ['volume', 'momentum'],
    'formula_latex': 'ts_rank(volume/adv20,20) * ts_rank(-1*delta(close,7),8)',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 39,
    'notes': '',
}


def compute_alpha_043(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = ts_rank(safe_div(volume, adv20), 20) * ts_rank(-1.0 * delta(close, 7), 8)
    return out


__alpha_meta_alpha_044 = {
    'id': 'alpha101_044',
    'nickname': 'Kakushadze Alpha #44',
    'theme': ['volume'],
    'formula_latex': '-1 * correlation(high, rank(volume), 5)',
    'columns_required': ['high', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
    'notes': '',
}


def compute_alpha_044(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * ts_corr(high, rank(volume), 5)
    return out


__alpha_meta_alpha_045 = {
    'id': 'alpha101_045',
    'nickname': 'Kakushadze Alpha #45',
    'theme': ['momentum', 'volume'],
    'formula_latex': '-1 * (rank(sum(delay(close,5),20)/20)*correlation(close,volume,2)*rank(correlation(sum(close,5),sum(close,20),2)))',
    'columns_required': ['close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_045(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    out = -1.0 * (rank(rolling_sum(delay(close, 5), 20) / 20.0) * ts_corr(close, volume, 2) * rank(ts_corr(rolling_sum(close, 5), rolling_sum(close, 20), 2)))
    return out


__alpha_meta_alpha_046 = {
    'id': 'alpha101_046',
    'nickname': 'Kakushadze Alpha #46',
    'theme': ['momentum'],
    'formula_latex': 'complex piecewise; see paper',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_046(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    delay = _delay
    make_one = _make_one
    where_ternary = _where_ternary
    x = ((delay(close, 20) - delay(close, 10)) / 10.0) - ((delay(close, 10) - close) / 10.0)
    one = make_one(close)
    out = where_ternary(0.25 < x, -1.0 * one, where_ternary(x < 0.0, one, -1.0 * (close - delay(close, 1))))
    return out


__alpha_meta_alpha_047 = {
    'id': 'alpha101_047',
    'nickname': 'Kakushadze Alpha #47',
    'theme': ['volume', 'momentum'],
    'formula_latex': '((rank(1/close)*volume/adv20) * (high*rank(high-close)/(sum(high,5)/5))) - rank(vwap-delay(vwap,5))',
    'columns_required': ['high', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': '',
}


def compute_alpha_047(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    make_one = _make_one
    t1 = safe_div(rank(safe_div(make_one(close), close)) * volume, adv20)
    t2 = safe_div(high * rank(high - close), rolling_sum(high, 5) / 5.0)
    out = t1 * t2 - rank(vwap - delay(vwap, 5))
    return out


__alpha_meta_alpha_048 = {
    'id': 'alpha101_048',
    'nickname': 'Kakushadze Alpha #48',
    'theme': ['momentum', 'volatility'],
    'formula_latex': 'indneutralize(...subindustry...) / sum((delta(close,1)/delay(close,1))^2, 250)',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 251,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_048(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    ind_neutralize = _ind_neutralize
    num = (ts_corr(delta(close, 1), delta(delay(close, 1), 1), 250) * delta(close, 1)) / close
    num = ind_neutralize(num, panel)
    denom = rolling_sum(safe_div(delta(close, 1), delay(close, 1)).pow(2), 250)
    out = safe_div(num, denom)
    return out


__alpha_meta_alpha_049 = {
    'id': 'alpha101_049',
    'nickname': 'Kakushadze Alpha #49',
    'theme': ['momentum'],
    'formula_latex': '(((delay(close,20)-delay(close,10))/10 - (delay(close,10)-close)/10) < -0.1) ? 1 : -1*(close-delay(close,1))',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_049(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    delay = _delay
    make_one = _make_one
    where_ternary = _where_ternary
    x = ((delay(close, 20) - delay(close, 10)) / 10.0) - ((delay(close, 10) - close) / 10.0)
    one = make_one(close)
    out = where_ternary(x < -0.1, one, -1.0 * (close - delay(close, 1)))
    return out


__alpha_meta_alpha_050 = {
    'id': 'alpha101_050',
    'nickname': 'Kakushadze Alpha #50',
    'theme': ['volume'],
    'formula_latex': '-1 * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 5)',
    'columns_required': ['volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_050(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    volume = panel["volume"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = -1.0 * ts_max(rank(ts_corr(rank(volume), rank(vwap), 5)), 5)
    return out


__alpha_meta_alpha_051 = {
    'id': 'alpha101_051',
    'nickname': 'Kakushadze Alpha #51',
    'theme': ['momentum'],
    'formula_latex': '(...< -0.05) ? 1 : -1*(close-delay(close,1))',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_051(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    delay = _delay
    make_one = _make_one
    where_ternary = _where_ternary
    x = ((delay(close, 20) - delay(close, 10)) / 10.0) - ((delay(close, 10) - close) / 10.0)
    one = make_one(close)
    out = where_ternary(x < -0.05, one, -1.0 * (close - delay(close, 1)))
    return out


__alpha_meta_alpha_052 = {
    'id': 'alpha101_052',
    'nickname': 'Kakushadze Alpha #52',
    'theme': ['momentum'],
    'formula_latex': '((-1*ts_min(low,5)+delay(ts_min(low,5),5)) * rank((sum(returns,240)-sum(returns,20))/220)) * ts_rank(volume,5)',
    'columns_required': ['low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 240,
    'notes': 'Very long lookback (>= ~100 bars); produces NaN warmup on short panels which may trigger the >95% NaN registry guard.',
}


def compute_alpha_052(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    low = panel["low"]
    volume = panel["volume"]

    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    out = ((-1.0 * ts_min(low, 5)) + delay(ts_min(low, 5), 5)) * rank((rolling_sum(returns, 240) - rolling_sum(returns, 20)) / 220.0) * ts_rank(volume, 5)
    return out


__alpha_meta_alpha_053 = {
    'id': 'alpha101_053',
    'nickname': 'Kakushadze Alpha #53',
    'theme': ['reversal'],
    'formula_latex': '-1 * delta(((close-low) - (high-close))/(close-low), 9)',
    'columns_required': ['high', 'low', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_053(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    x = safe_div(((close - low) - (high - close)), (close - low))
    out = -1.0 * delta(x, 9)
    return out


__alpha_meta_alpha_054 = {
    'id': 'alpha101_054',
    'nickname': 'Kakushadze Alpha #54',
    'theme': ['reversal'],
    'formula_latex': '-1 * ((low-close)*(open^5)) / ((low-high)*(close^5))',
    'columns_required': ['open', 'high', 'low', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_054(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    num = (low - close) * open_.pow(5)
    denom = (low - high) * close.pow(5)
    out = -1.0 * safe_div(num, denom)
    return out


__alpha_meta_alpha_055 = {
    'id': 'alpha101_055',
    'nickname': 'Kakushadze Alpha #55',
    'theme': ['volume', 'reversal'],
    'formula_latex': '-1 * correlation(rank((close-ts_min(low,12))/(ts_max(high,12)-ts_min(low,12))), rank(volume), 6)',
    'columns_required': ['high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 17,
    'notes': '',
}


def compute_alpha_055(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    x = safe_div(close - ts_min(low, 12), ts_max(high, 12) - ts_min(low, 12))
    out = -1.0 * ts_corr(rank(x), rank(volume), 6)
    return out


__alpha_meta_alpha_056 = {
    'id': 'alpha101_056',
    'nickname': 'Kakushadze Alpha #56',
    'theme': ['momentum'],
    'formula_latex': '0 - 1*(rank(sum(returns,10)/sum(sum(returns,2),3)) * rank((returns * cap)))  [cap unavailable -> 1]',
    'columns_required': ['close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization. Paper formula uses market 'cap' which is not part of the standard OHLCV panel; substituted by a constant 1.0 DataFrame. Result remains a valid factor but loses the cap-weighting term.",
}


def compute_alpha_056(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]


    returns = close.pct_change()
    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    make_one = _make_one
    # 'cap' (market cap) is not part of the standard panel; degrade to 1.0
    cap = make_one(close)
    num = rolling_sum(returns, 10)
    denom = rolling_sum(rolling_sum(returns, 2), 3)
    out = 0.0 - (rank(safe_div(num, denom)) * rank(returns * cap))
    return out


__alpha_meta_alpha_057 = {
    'id': 'alpha101_057',
    'nickname': 'Kakushadze Alpha #57',
    'theme': ['reversal'],
    'formula_latex': '0 - 1 * ((close-vwap) / decay_linear(rank(ts_argmax(close,30)), 2))',
    'columns_required': ['close', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 32,
    'notes': '',
}


def compute_alpha_057(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = 0.0 - safe_div((close - vwap), decay_linear(rank(ts_argmax(close, 30)), 2))
    return out


__alpha_meta_alpha_058 = {
    'id': 'alpha101_058',
    'nickname': 'Kakushadze Alpha #58',
    'theme': ['volume'],
    'formula_latex': '-1 * Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, sector), volume, 4), 8), 6)',
    'columns_required': ['volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_058(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    volume = panel["volume"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    out = -1.0 * ts_rank(decay_linear(ts_corr(ind_neutralize(vwap, panel), volume, 4), 8), 6)
    return out


__alpha_meta_alpha_059 = {
    'id': 'alpha101_059',
    'nickname': 'Kakushadze Alpha #59',
    'theme': ['volume'],
    'formula_latex': '-1 * Ts_Rank(decay_linear(correlation(IndNeutralize(vwap*0.728+vwap*0.272, industry), volume, 4), 16), 8)',
    'columns_required': ['volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 30,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_059(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    volume = panel["volume"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    x = vwap * 0.728317 + vwap * (1.0 - 0.728317)
    out = -1.0 * ts_rank(decay_linear(ts_corr(ind_neutralize(x, panel), volume, 4), 16), 8)
    return out


__alpha_meta_alpha_060 = {
    'id': 'alpha101_060',
    'nickname': 'Kakushadze Alpha #60',
    'theme': ['volume'],
    'formula_latex': '0 - (2*scale(rank((((close-low)-(high-close))/(high-low))*volume)) - scale(rank(ts_argmax(close,10))))',
    'columns_required': ['high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 10,
    'notes': '',
}


def compute_alpha_060(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    x = safe_div(((close - low) - (high - close)), (high - low)) * volume
    out = 0.0 - (2.0 * scale(rank(x)) - scale(rank(ts_argmax(close, 10))))
    return out


__alpha_meta_alpha_061 = {
    'id': 'alpha101_061',
    'nickname': 'Kakushadze Alpha #61',
    'theme': ['volume'],
    'formula_latex': 'rank(vwap - ts_min(vwap,16)) < rank(correlation(vwap, adv180, 18))',
    'columns_required': ['volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 197,
    'notes': '',
}


def compute_alpha_061(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv180 = ts_mean(volume, 180)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    lhs = rank(vwap - ts_min(vwap, 16))
    rhs = rank(ts_corr(vwap, adv180, 18))
    out = (lhs < rhs).astype(float)
    return out


__alpha_meta_alpha_062 = {
    'id': 'alpha101_062',
    'nickname': 'Kakushadze Alpha #62',
    'theme': ['volume'],
    'formula_latex': '(rank(correlation(vwap, sum(adv20,22), 10)) < rank(((rank(open)+rank(open)) < (rank((high+low)/2)+rank(high))))) * -1',
    'columns_required': ['open', 'high', 'low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 35,
    'notes': '',
}


def compute_alpha_062(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    lhs = rank(ts_corr(vwap, rolling_sum(adv20, 22), 10))
    inner = ((rank(open_) + rank(open_)) < (rank((high + low) / 2.0) + rank(high))).astype(float)
    rhs = rank(inner)
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_063 = {
    'id': 'alpha101_063',
    'nickname': 'Kakushadze Alpha #63',
    'theme': ['volume', 'momentum'],
    'formula_latex': '(rank(decay_linear(delta(IndNeutralize(close, industry), 2), 8)) - rank(decay_linear(correlation(0.318*vwap+0.682*open, sum(adv180,37), 14), 12))) * -1',
    'columns_required': ['open', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 204,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_063(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv180 = ts_mean(volume, 180)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    ind_neutralize = _ind_neutralize
    left = rank(decay_linear(delta(ind_neutralize(close, panel), 2), 8))
    mix = vwap * 0.318108 + open_ * (1.0 - 0.318108)
    right = rank(decay_linear(ts_corr(mix, rolling_sum(adv180, 37), 14), 12))
    out = (left - right) * -1.0
    return out


__alpha_meta_alpha_064 = {
    'id': 'alpha101_064',
    'nickname': 'Kakushadze Alpha #64',
    'theme': ['volume'],
    'formula_latex': '(rank(correlation(sum(0.178*open+0.822*low,13), sum(adv120,13), 17)) < rank(delta(0.178*((high+low)/2)+0.822*vwap, 4))) * -1',
    'columns_required': ['open', 'high', 'low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 136,
    'notes': '',
}


def compute_alpha_064(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv120 = ts_mean(volume, 120)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    a = open_ * 0.178404 + low * (1.0 - 0.178404)
    b = ((high + low) / 2.0) * 0.178404 + vwap * (1.0 - 0.178404)
    lhs = rank(ts_corr(rolling_sum(a, 13), rolling_sum(adv120, 13), 17))
    rhs = rank(delta(b, 4))
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_065 = {
    'id': 'alpha101_065',
    'nickname': 'Kakushadze Alpha #65',
    'theme': ['volume'],
    'formula_latex': '(rank(correlation(0.008*open+0.992*vwap, sum(adv60,9), 6)) < rank(open-ts_min(open,14))) * -1',
    'columns_required': ['open', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 65,
    'notes': '',
}


def compute_alpha_065(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv60 = ts_mean(volume, 60)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    mix = open_ * 0.00817205 + vwap * (1.0 - 0.00817205)
    lhs = rank(ts_corr(mix, rolling_sum(adv60, 9), 6))
    rhs = rank(open_ - ts_min(open_, 14))
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_066 = {
    'id': 'alpha101_066',
    'nickname': 'Kakushadze Alpha #66',
    'theme': ['momentum'],
    'formula_latex': '(rank(decay_linear(delta(vwap,4), 7)) + Ts_Rank(decay_linear(((0.966*low+0.034*low - vwap)/(open-(high+low)/2)), 11), 7)) * -1',
    'columns_required': ['open', 'high', 'low', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 18,
    'notes': '',
}


def compute_alpha_066(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    t1 = rank(decay_linear(delta(vwap, 4), 7))
    num = (low * 0.96633 + low * (1.0 - 0.96633)) - vwap
    denom = open_ - (high + low) / 2.0
    t2 = ts_rank(decay_linear(safe_div(num, denom), 11), 7)
    out = (t1 + t2) * -1.0
    return out


__alpha_meta_alpha_067 = {
    'id': 'alpha101_067',
    'nickname': 'Kakushadze Alpha #67',
    'theme': ['volume'],
    'formula_latex': '(rank(high-ts_min(high,2))^rank(correlation(IndNeutralize(vwap,sector), IndNeutralize(adv20,subindustry), 6))) * -1',
    'columns_required': ['high', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 25,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_067(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    lhs = rank(high - ts_min(high, 2))
    rhs = rank(ts_corr(ind_neutralize(vwap, panel), ind_neutralize(adv20, panel), 6))
    out = signed_power(lhs, 1.0) * signed_power(rhs, 1.0) * -1.0  # power = rank-rank (use signed_power for stability); paper uses '^' as power but with rank result use product as common impl
    out = (lhs * rhs) * -1.0
    return out


__alpha_meta_alpha_068 = {
    'id': 'alpha101_068',
    'nickname': 'Kakushadze Alpha #68',
    'theme': ['volume'],
    'formula_latex': '(Ts_Rank(correlation(rank(high), rank(adv15), 9), 14) < rank(delta(0.518*close+0.482*low, 1))) * -1',
    'columns_required': ['high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 36,
    'notes': '',
}


def compute_alpha_068(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv15 = ts_mean(volume, 15)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    lhs = ts_rank(ts_corr(rank(high), rank(adv15), 9), 14)
    mix = close * 0.518371 + low * (1.0 - 0.518371)
    rhs = rank(delta(mix, 1))
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_069 = {
    'id': 'alpha101_069',
    'nickname': 'Kakushadze Alpha #69',
    'theme': ['volume'],
    'formula_latex': '(rank(ts_max(delta(IndNeutralize(vwap, industry), 3), 5))^Ts_Rank(correlation(0.49*close+0.51*vwap, adv20, 5), 9)) * -1',
    'columns_required': ['close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 32,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_069(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    lhs = rank(ts_max(delta(ind_neutralize(vwap, panel), 3), 5))
    mix = close * 0.490655 + vwap * (1.0 - 0.490655)
    rhs = ts_rank(ts_corr(mix, adv20, 5), 9)
    out = (lhs * rhs) * -1.0
    return out


__alpha_meta_alpha_070 = {
    'id': 'alpha101_070',
    'nickname': 'Kakushadze Alpha #70',
    'theme': ['momentum', 'volume'],
    'formula_latex': '(rank(delta(vwap,1))^Ts_Rank(correlation(IndNeutralize(close,industry), adv50, 18), 18)) * -1',
    'columns_required': ['close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 84,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_070(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv5 = ts_mean(volume, 5)
    adv50 = ts_mean(volume, 50)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    lhs = rank(delta(vwap, 1))
    rhs = ts_rank(ts_corr(ind_neutralize(close, panel), adv50, 18), 18)
    out = (lhs * rhs) * -1.0
    return out


__alpha_meta_alpha_071 = {
    'id': 'alpha101_071',
    'nickname': 'Kakushadze Alpha #71',
    'theme': ['volume', 'reversal'],
    'formula_latex': 'max(Ts_Rank(decay_linear(correlation(Ts_Rank(close,3), Ts_Rank(adv180,12), 18), 4), 16), Ts_Rank(decay_linear((rank((low+open)-(2*vwap))^2, 16), 4))',
    'columns_required': ['open', 'low', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 226,
    'notes': '',
}


def compute_alpha_071(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv180 = ts_mean(volume, 180)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    a = ts_rank(decay_linear(ts_corr(ts_rank(close, 3), ts_rank(adv180, 12), 18), 4), 16)
    inner = signed_power(rank((low + open_) - (vwap + vwap)), 2.0)
    b = ts_rank(decay_linear(inner, 16), 4)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmax(arr_a, arr_b), index=close.index, columns=close.columns)
    return out


__alpha_meta_alpha_072 = {
    'id': 'alpha101_072',
    'nickname': 'Kakushadze Alpha #72',
    'theme': ['volume'],
    'formula_latex': 'rank(decay_linear(correlation((high+low)/2, adv40, 9), 10)) / rank(decay_linear(correlation(Ts_Rank(vwap,4), Ts_Rank(volume,19), 7), 3))',
    'columns_required': ['high', 'low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 57,
    'notes': '',
}


def compute_alpha_072(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv40 = ts_mean(volume, 40)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    num = rank(decay_linear(ts_corr((high + low) / 2.0, adv40, 9), 10))
    denom = rank(decay_linear(ts_corr(ts_rank(vwap, 4), ts_rank(volume, 19), 7), 3))
    out = safe_div(num, denom)
    return out


__alpha_meta_alpha_073 = {
    'id': 'alpha101_073',
    'nickname': 'Kakushadze Alpha #73',
    'theme': ['volume'],
    'formula_latex': 'max(rank(decay_linear(delta(vwap,5), 3)), Ts_Rank(decay_linear(-1*(delta(0.147*open+0.853*low,2)/(0.147*open+0.853*low)), 3), 17)) * -1',
    'columns_required': ['open', 'low', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 21,
    'notes': '',
}


def compute_alpha_073(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    low = panel["low"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    a = rank(decay_linear(delta(vwap, 5), 3))
    mix = open_ * 0.147155 + low * (1.0 - 0.147155)
    b_inner = safe_div(delta(mix, 2), mix) * -1.0
    b = ts_rank(decay_linear(b_inner, 3), 17)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmax(arr_a, arr_b), index=close.index, columns=close.columns) * -1.0
    return out


__alpha_meta_alpha_074 = {
    'id': 'alpha101_074',
    'nickname': 'Kakushadze Alpha #74',
    'theme': ['volume'],
    'formula_latex': '(rank(correlation(close, sum(adv30,37), 15)) < rank(correlation(rank(0.026*high+0.974*vwap), rank(volume), 11))) * -1',
    'columns_required': ['high', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 60,
    'notes': '',
}


def compute_alpha_074(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv30 = ts_mean(volume, 30)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    lhs = rank(ts_corr(close, rolling_sum(adv30, 37), 15))
    mix = high * 0.0261661 + vwap * (1.0 - 0.0261661)
    rhs = rank(ts_corr(rank(mix), rank(volume), 11))
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_075 = {
    'id': 'alpha101_075',
    'nickname': 'Kakushadze Alpha #75',
    'theme': ['volume'],
    'formula_latex': 'rank(correlation(vwap, volume, 4)) < rank(correlation(rank(low), rank(adv50), 12))',
    'columns_required': ['low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 61,
    'notes': '',
}


def compute_alpha_075(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv5 = ts_mean(volume, 5)
    adv50 = ts_mean(volume, 50)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    lhs = rank(ts_corr(vwap, volume, 4))
    rhs = rank(ts_corr(rank(low), rank(adv50), 12))
    out = (lhs < rhs).astype(float)
    return out


__alpha_meta_alpha_076 = {
    'id': 'alpha101_076',
    'nickname': 'Kakushadze Alpha #76',
    'theme': ['volume'],
    'formula_latex': 'max(rank(decay_linear(delta(vwap,1),12)), Ts_Rank(decay_linear(Ts_Rank(correlation(IndNeutralize(low, sector), adv81, 8), 20), 17), 19)) * -1',
    'columns_required': ['low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 141,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_076(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv81 = ts_mean(volume, 81)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    a = rank(decay_linear(delta(vwap, 1), 12))
    b = ts_rank(decay_linear(ts_rank(ts_corr(ind_neutralize(low, panel), adv81, 8), 20), 17), 19)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmax(arr_a, arr_b), index=close.index, columns=close.columns) * -1.0
    return out


__alpha_meta_alpha_077 = {
    'id': 'alpha101_077',
    'nickname': 'Kakushadze Alpha #77',
    'theme': ['volume'],
    'formula_latex': 'min(rank(decay_linear((high+low)/2 + high - (vwap+high), 20)), rank(decay_linear(correlation((high+low)/2, adv40, 3), 6)))',
    'columns_required': ['high', 'low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 47,
    'notes': '',
}


def compute_alpha_077(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv40 = ts_mean(volume, 40)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    a = rank(decay_linear(((high + low) / 2.0) + high - (vwap + high), 20))
    b = rank(decay_linear(ts_corr((high + low) / 2.0, adv40, 3), 6))
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmin(arr_a, arr_b), index=close.index, columns=close.columns)
    return out


__alpha_meta_alpha_078 = {
    'id': 'alpha101_078',
    'nickname': 'Kakushadze Alpha #78',
    'theme': ['volume'],
    'formula_latex': 'rank(correlation(sum(0.352*low+0.648*vwap, 20), sum(adv40,20), 7))^rank(correlation(rank(vwap), rank(volume), 6))',
    'columns_required': ['low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 46,
    'notes': '',
}


def compute_alpha_078(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv40 = ts_mean(volume, 40)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    mix = low * 0.352233 + vwap * (1.0 - 0.352233)
    lhs = rank(ts_corr(rolling_sum(mix, 20), rolling_sum(adv40, 20), 7))
    rhs = rank(ts_corr(rank(vwap), rank(volume), 6))
    out = lhs * rhs
    return out


__alpha_meta_alpha_079 = {
    'id': 'alpha101_079',
    'nickname': 'Kakushadze Alpha #79',
    'theme': ['volume', 'momentum'],
    'formula_latex': 'rank(delta(IndNeutralize(0.607*close+0.393*open, sector), 1)) < rank(correlation(Ts_Rank(vwap,4), Ts_Rank(adv150,9), 15))',
    'columns_required': ['open', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 172,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_079(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv15 = ts_mean(volume, 15)
    adv150 = ts_mean(volume, 150)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    mix = close * 0.60733 + open_ * (1.0 - 0.60733)
    lhs = rank(delta(ind_neutralize(mix, panel), 1))
    rhs = rank(ts_corr(ts_rank(vwap, 4), ts_rank(adv150, 9), 15))
    out = (lhs < rhs).astype(float)
    return out


__alpha_meta_alpha_080 = {
    'id': 'alpha101_080',
    'nickname': 'Kakushadze Alpha #80',
    'theme': ['momentum', 'volume'],
    'formula_latex': '(rank(Sign(delta(IndNeutralize(0.868*open+0.132*high, subindustry),4)))^Ts_Rank(correlation(high,adv10,5),6)) * -1',
    'columns_required': ['open', 'high', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 19,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_080(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    high = panel["high"]
    volume = panel["volume"]
    adv10 = ts_mean(volume, 10)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    mix = open_ * 0.868128 + high * (1.0 - 0.868128)
    lhs_inner = delta(ind_neutralize(mix, panel), 4)
    lhs = rank(pd.DataFrame(np.sign(lhs_inner.to_numpy(dtype=np.float64, na_value=np.nan)), index=close.index, columns=close.columns))
    rhs = ts_rank(ts_corr(high, adv10, 5), 6)
    out = (lhs * rhs) * -1.0
    return out


__alpha_meta_alpha_081 = {
    'id': 'alpha101_081',
    'nickname': 'Kakushadze Alpha #81',
    'theme': ['volume'],
    'formula_latex': '(rank(Log(product(rank((rank(correlation(vwap, sum(adv10,50), 8))^4)), 15))) < rank(correlation(rank(vwap), rank(volume), 5))) * -1',
    'columns_required': ['volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 70,
    'notes': '',
}


def compute_alpha_081(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv10 = ts_mean(volume, 10)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    rolling_prod = _rolling_prod
    inner = rank(ts_corr(vwap, rolling_sum(adv10, 50), 8))
    inner = signed_power(inner, 4.0)
    inner = rank(inner)
    prod = rolling_prod(inner, 15)
    lhs = rank(np.log(prod.where(prod > 0)))
    rhs = rank(ts_corr(rank(vwap), rank(volume), 5))
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_082 = {
    'id': 'alpha101_082',
    'nickname': 'Kakushadze Alpha #82',
    'theme': ['volume'],
    'formula_latex': 'min(rank(decay_linear(delta(open,1),15)), Ts_Rank(decay_linear(correlation(IndNeutralize(volume, sector), 0.634*open+0.366*open, 17), 7), 13)) * -1',
    'columns_required': ['open', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 35,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_082(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    volume = panel["volume"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    a = rank(decay_linear(delta(open_, 1), 15))
    mix = open_ * 0.634196 + open_ * (1.0 - 0.634196)
    b = ts_rank(decay_linear(ts_corr(ind_neutralize(volume, panel), mix, 17), 7), 13)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmin(arr_a, arr_b), index=close.index, columns=close.columns) * -1.0
    return out


__alpha_meta_alpha_083 = {
    'id': 'alpha101_083',
    'nickname': 'Kakushadze Alpha #83',
    'theme': ['volume', 'volatility'],
    'formula_latex': '(rank(delay((high-low)/(sum(close,5)/5), 2)) * rank(rank(volume))) / (((high-low)/(sum(close,5)/5)) / (vwap-close))',
    'columns_required': ['high', 'low', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 7,
    'notes': '',
}


def compute_alpha_083(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    delay = _delay
    rng_avg = safe_div((high - low), rolling_sum(close, 5) / 5.0)
    num = rank(delay(rng_avg, 2)) * rank(rank(volume))
    denom = safe_div(rng_avg, vwap - close)
    out = safe_div(num, denom)
    return out


__alpha_meta_alpha_084 = {
    'id': 'alpha101_084',
    'nickname': 'Kakushadze Alpha #84',
    'theme': ['momentum'],
    'formula_latex': 'SignedPower(Ts_Rank(vwap-ts_max(vwap,15), 21), delta(close,5))',
    'columns_required': ['close', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 35,
    'notes': "SignedPower with a delta(close,5) exponent can produce non-finite values when the exponent is large; non-finite outputs are clipped to NaN to satisfy the registry's no-inf invariant.",
}


def compute_alpha_084(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    vwap = panel["vwap"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    base = ts_rank(vwap - ts_max(vwap, 15), 21)
    exponent_df = delta(close, 5)
    base_arr = base.to_numpy(dtype=np.float64, na_value=np.nan)
    exp_arr = exponent_df.to_numpy(dtype=np.float64, na_value=np.nan)
    out_arr = np.sign(base_arr) * np.power(np.abs(base_arr), exp_arr)
    out_arr = np.where(np.isfinite(out_arr), out_arr, np.nan)
    out = pd.DataFrame(out_arr, index=close.index, columns=close.columns)
    return out


__alpha_meta_alpha_085 = {
    'id': 'alpha101_085',
    'nickname': 'Kakushadze Alpha #85',
    'theme': ['volume'],
    'formula_latex': 'rank(correlation(0.877*high+0.123*close, adv30, 10))^rank(correlation(Ts_Rank((high+low)/2,4), Ts_Rank(volume,10), 7))',
    'columns_required': ['high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 39,
    'notes': '',
}


def compute_alpha_085(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv30 = ts_mean(volume, 30)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    mix = high * 0.876703 + close * (1.0 - 0.876703)
    lhs = rank(ts_corr(mix, adv30, 10))
    rhs = rank(ts_corr(ts_rank((high + low) / 2.0, 4), ts_rank(volume, 10), 7))
    out = lhs * rhs
    return out


__alpha_meta_alpha_086 = {
    'id': 'alpha101_086',
    'nickname': 'Kakushadze Alpha #86',
    'theme': ['volume'],
    'formula_latex': '(Ts_Rank(correlation(close, sum(adv20,15), 6), 20) < rank((open+close) - (vwap+open))) * -1',
    'columns_required': ['open', 'close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 44,
    'notes': '',
}


def compute_alpha_086(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    lhs = ts_rank(ts_corr(close, rolling_sum(adv20, 15), 6), 20)
    rhs = rank((open_ + close) - (vwap + open_))
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_087 = {
    'id': 'alpha101_087',
    'nickname': 'Kakushadze Alpha #87',
    'theme': ['momentum'],
    'formula_latex': 'max(rank(decay_linear(delta(0.37*close+0.63*vwap, 2), 3)), Ts_Rank(decay_linear(abs(correlation(IndNeutralize(adv81, industry), close, 13)), 5), 14)) * -1',
    'columns_required': ['close', 'vwap', 'volume'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 110,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_087(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    vwap = panel["vwap"]
    volume = panel["volume"]
    adv81 = ts_mean(volume, 81)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    mix = close * 0.369701 + vwap * (1.0 - 0.369701)
    a = rank(decay_linear(delta(mix, 2), 3))
    b = ts_rank(decay_linear(ts_corr(ind_neutralize(adv81, panel), close, 13).abs(), 5), 14)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmax(arr_a, arr_b), index=close.index, columns=close.columns) * -1.0
    return out


__alpha_meta_alpha_088 = {
    'id': 'alpha101_088',
    'nickname': 'Kakushadze Alpha #88',
    'theme': ['volume'],
    'formula_latex': 'min(rank(decay_linear((rank(open)+rank(low))-(rank(high)+rank(close)),8)), Ts_Rank(decay_linear(correlation(Ts_Rank(close,8),Ts_Rank(adv60,20),8),7),3))',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 94,
    'notes': '',
}


def compute_alpha_088(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv60 = ts_mean(volume, 60)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    a = rank(decay_linear((rank(open_) + rank(low)) - (rank(high) + rank(close)), 8))
    b = ts_rank(decay_linear(ts_corr(ts_rank(close, 8), ts_rank(adv60, 20), 8), 7), 3)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmin(arr_a, arr_b), index=close.index, columns=close.columns)
    return out


__alpha_meta_alpha_089 = {
    'id': 'alpha101_089',
    'nickname': 'Kakushadze Alpha #89',
    'theme': ['volume', 'momentum'],
    'formula_latex': 'Ts_Rank(decay_linear(correlation(low, adv10, 7), 6), 4) - Ts_Rank(decay_linear(delta(IndNeutralize(vwap, industry),3),10),15)',
    'columns_required': ['low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 30,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_089(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv10 = ts_mean(volume, 10)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    mix = low * 0.967285 + low * (1.0 - 0.967285)
    a = ts_rank(decay_linear(ts_corr(mix, adv10, 7), 6), 4)
    b = ts_rank(decay_linear(delta(ind_neutralize(vwap, panel), 3), 10), 15)
    out = a - b
    return out


__alpha_meta_alpha_090 = {
    'id': 'alpha101_090',
    'nickname': 'Kakushadze Alpha #90',
    'theme': ['volume'],
    'formula_latex': '(rank(close-ts_max(close,5))^Ts_Rank(correlation(IndNeutralize(adv40, subindustry), low, 5), 3)) * -1',
    'columns_required': ['low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 46,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_090(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    low = panel["low"]
    volume = panel["volume"]
    adv40 = ts_mean(volume, 40)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    lhs = rank(close - ts_max(close, 5))
    rhs = ts_rank(ts_corr(ind_neutralize(adv40, panel), low, 5), 3)
    out = (lhs * rhs) * -1.0
    return out


__alpha_meta_alpha_091 = {
    'id': 'alpha101_091',
    'nickname': 'Kakushadze Alpha #91',
    'theme': ['volume'],
    'formula_latex': '(Ts_Rank(decay_linear(decay_linear(correlation(IndNeutralize(close, industry), volume, 10), 16), 4), 5) - rank(decay_linear(correlation(vwap, adv30, 4), 3))) * -1',
    'columns_required': ['close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 35,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_091(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv30 = ts_mean(volume, 30)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    a = ts_rank(decay_linear(decay_linear(ts_corr(ind_neutralize(close, panel), volume, 10), 16), 4), 5)
    b = rank(decay_linear(ts_corr(vwap, adv30, 4), 3))
    out = (a - b) * -1.0
    return out


__alpha_meta_alpha_092 = {
    'id': 'alpha101_092',
    'nickname': 'Kakushadze Alpha #92',
    'theme': ['volume'],
    'formula_latex': 'min(Ts_Rank(decay_linear(((high+low)/2 + close < low+open), 15), 19), Ts_Rank(decay_linear(correlation(rank(low), rank(adv30), 8), 7), 7))',
    'columns_required': ['open', 'high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 49,
    'notes': '',
}


def compute_alpha_092(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv30 = ts_mean(volume, 30)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    cond = (((high + low) / 2.0 + close) < (low + open_)).astype(float)
    a = ts_rank(decay_linear(cond, 15), 19)
    b = ts_rank(decay_linear(ts_corr(rank(low), rank(adv30), 8), 7), 7)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmin(arr_a, arr_b), index=close.index, columns=close.columns)
    return out


__alpha_meta_alpha_093 = {
    'id': 'alpha101_093',
    'nickname': 'Kakushadze Alpha #93',
    'theme': ['volume'],
    'formula_latex': 'Ts_Rank(decay_linear(correlation(IndNeutralize(vwap, industry), adv81, 17), 20), 8) / rank(decay_linear(delta(0.524*close+0.476*vwap, 3), 16))',
    'columns_required': ['close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 123,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_093(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv81 = ts_mean(volume, 81)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    a = ts_rank(decay_linear(ts_corr(ind_neutralize(vwap, panel), adv81, 17), 20), 8)
    mix = close * 0.524434 + vwap * (1.0 - 0.524434)
    b = rank(decay_linear(delta(mix, 3), 16))
    out = safe_div(a, b)
    return out


__alpha_meta_alpha_094 = {
    'id': 'alpha101_094',
    'nickname': 'Kakushadze Alpha #94',
    'theme': ['volume'],
    'formula_latex': '(rank(vwap-ts_min(vwap,12))^Ts_Rank(correlation(Ts_Rank(vwap,20), Ts_Rank(adv60,4), 18), 3)) * -1',
    'columns_required': ['volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 82,
    'notes': '',
}


def compute_alpha_094(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv60 = ts_mean(volume, 60)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    lhs = rank(vwap - ts_min(vwap, 12))
    rhs = ts_rank(ts_corr(ts_rank(vwap, 20), ts_rank(adv60, 4), 18), 3)
    out = (lhs * rhs) * -1.0
    return out


__alpha_meta_alpha_095 = {
    'id': 'alpha101_095',
    'nickname': 'Kakushadze Alpha #95',
    'theme': ['volume'],
    'formula_latex': 'rank(open-ts_min(open,13)) < Ts_Rank((rank(correlation(sum((high+low)/2,19), sum(adv40,19),13))^5), 12)',
    'columns_required': ['open', 'high', 'low', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 63,
    'notes': '',
}


def compute_alpha_095(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv40 = ts_mean(volume, 40)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    lhs = rank(open_ - ts_min(open_, 13))
    inner = rank(ts_corr(rolling_sum((high + low) / 2.0, 19), rolling_sum(adv40, 19), 13))
    inner = signed_power(inner, 5.0)
    rhs = ts_rank(inner, 12)
    out = (lhs < rhs).astype(float)
    return out


__alpha_meta_alpha_096 = {
    'id': 'alpha101_096',
    'nickname': 'Kakushadze Alpha #96',
    'theme': ['volume'],
    'formula_latex': 'max(Ts_Rank(decay_linear(correlation(rank(vwap), rank(volume), 4), 4), 8), Ts_Rank(decay_linear(Ts_ArgMax(correlation(Ts_Rank(close,7), Ts_Rank(adv60,4), 4), 13), 14), 13)) * -1',
    'columns_required': ['close', 'volume', 'vwap'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 103,
    'notes': '',
}


def compute_alpha_096(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv60 = ts_mean(volume, 60)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    a = ts_rank(decay_linear(ts_corr(rank(vwap), rank(volume), 4), 4), 8)
    b = ts_rank(decay_linear(ts_argmax(ts_corr(ts_rank(close, 7), ts_rank(adv60, 4), 4), 13), 14), 13)
    arr_a = a.to_numpy(dtype=np.float64, na_value=np.nan)
    arr_b = b.to_numpy(dtype=np.float64, na_value=np.nan)
    out = pd.DataFrame(np.fmax(arr_a, arr_b), index=close.index, columns=close.columns) * -1.0
    return out


__alpha_meta_alpha_097 = {
    'id': 'alpha101_097',
    'nickname': 'Kakushadze Alpha #97',
    'theme': ['volume'],
    'formula_latex': '(rank(decay_linear(delta(IndNeutralize(0.721*low+0.279*vwap, industry),3),20)) - Ts_Rank(decay_linear(Ts_Rank(correlation(Ts_Rank(low,8), Ts_Rank(adv60,17), 5), 19), 16),16)) * -1',
    'columns_required': ['low', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 128,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_097(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    low = panel["low"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv60 = ts_mean(volume, 60)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    mix = low * 0.721001 + vwap * (1.0 - 0.721001)
    a = rank(decay_linear(delta(ind_neutralize(mix, panel), 3), 20))
    b = ts_rank(decay_linear(ts_rank(ts_corr(ts_rank(low, 8), ts_rank(adv60, 17), 5), 19), 16), 16)
    out = (a - b) * -1.0
    return out


__alpha_meta_alpha_098 = {
    'id': 'alpha101_098',
    'nickname': 'Kakushadze Alpha #98',
    'theme': ['volume'],
    'formula_latex': 'rank(decay_linear(correlation(vwap, sum(adv5,26), 5), 7)) - rank(decay_linear(Ts_Rank(Ts_ArgMin(correlation(rank(open), rank(adv15), 21), 9), 7), 8))',
    'columns_required': ['open', 'volume', 'vwap', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 56,
    'notes': '',
}


def compute_alpha_098(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    open_ = panel["open"]
    volume = panel["volume"]
    vwap = panel["vwap"]
    adv5 = ts_mean(volume, 5)
    adv15 = ts_mean(volume, 15)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    a = rank(decay_linear(ts_corr(vwap, rolling_sum(adv5, 26), 5), 7))
    b = rank(decay_linear(ts_rank(ts_argmin(ts_corr(rank(open_), rank(adv15), 21), 9), 7), 8))
    out = a - b
    return out


__alpha_meta_alpha_099 = {
    'id': 'alpha101_099',
    'nickname': 'Kakushadze Alpha #99',
    'theme': ['volume'],
    'formula_latex': '(rank(correlation(sum((high+low)/2, 20), sum(adv60, 20), 9)) < rank(correlation(low, volume, 6))) * -1',
    'columns_required': ['high', 'low', 'volume', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 68,
    'notes': '',
}


def compute_alpha_099(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv60 = ts_mean(volume, 60)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    rolling_sum = _rolling_sum
    lhs = rank(ts_corr(rolling_sum((high + low) / 2.0, 20), rolling_sum(adv60, 20), 9))
    rhs = rank(ts_corr(low, volume, 6))
    out = (lhs < rhs).astype(float) * -1.0
    return out


__alpha_meta_alpha_100 = {
    'id': 'alpha101_100',
    'nickname': 'Kakushadze Alpha #100',
    'theme': ['volume', 'momentum'],
    'formula_latex': '0 - 1*((1.5*scale(IN(IN(rank(((close-low)-(high-close))/(high-low)*volume), subind), subind)) - scale(IN(correlation(close, rank(adv20), 5) - rank(ts_argmin(close,30)), subind))) * (volume/adv20))',
    'columns_required': ['high', 'low', 'close', 'volume'],
    'extras_required': [],
    'requires_sector': True,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 30,
    'notes': "Industry neutralization implemented via per-row sector group demean (panel['sector'] required). When sector tag is absent the registry rejects via SkipAlpha; the compute() also has a degraded global demean fallback. This is a partial approximation of the paper's IndClass.industry/subindustry/sector neutralization.",
}


def compute_alpha_100(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    high = panel["high"]
    low = panel["low"]
    volume = panel["volume"]
    adv20 = ts_mean(volume, 20)

    # Helper aliases (local closures keep the file standalone & purity-safe).
    ind_neutralize = _ind_neutralize
    money_flow = safe_div(((close - low) - (high - close)), (high - low)) * volume
    t1 = 1.5 * scale(ind_neutralize(ind_neutralize(rank(money_flow), panel), panel))
    t2 = scale(ind_neutralize(ts_corr(close, rank(adv20), 5) - rank(ts_argmin(close, 30)), panel))
    out = 0.0 - ((t1 - t2) * safe_div(volume, adv20))
    return out


__alpha_meta_alpha_101 = {
    'id': 'alpha101_101',
    'nickname': 'Kakushadze Alpha #101',
    'theme': ['reversal'],
    'formula_latex': '(close - open) / ((high - low) + 0.001)',
    'columns_required': ['open', 'high', 'low', 'close'],
    'extras_required': [],
    'requires_sector': False,
    'universe': ['equity_us'],
    'frequency': ['1D'],
    'decay_horizon': 5,
    'min_warmup_bars': 1,
    'notes': '',
}


def compute_alpha_101(panel: dict) -> pd.DataFrame:
    """Compute the alpha on the OHLCV+ panel and return a wide DataFrame."""
    close = panel["close"]
    open_ = panel["open"]
    high = panel["high"]
    low = panel["low"]


    # Helper aliases (local closures keep the file standalone & purity-safe).
    out = safe_div((close - open_), (high - low + 0.001))
    return out

def get_all_alpha101_factors() -> list:
    """Return list of (meta_dict, compute_fn) tuples for all WorldQuant 101 Alphas (Kakushadze 2015) factors."""
    return [
        (__alpha_meta_alpha_001, compute_alpha_001),
        (__alpha_meta_alpha_002, compute_alpha_002),
        (__alpha_meta_alpha_003, compute_alpha_003),
        (__alpha_meta_alpha_004, compute_alpha_004),
        (__alpha_meta_alpha_005, compute_alpha_005),
        (__alpha_meta_alpha_006, compute_alpha_006),
        (__alpha_meta_alpha_007, compute_alpha_007),
        (__alpha_meta_alpha_008, compute_alpha_008),
        (__alpha_meta_alpha_009, compute_alpha_009),
        (__alpha_meta_alpha_010, compute_alpha_010),
        (__alpha_meta_alpha_011, compute_alpha_011),
        (__alpha_meta_alpha_012, compute_alpha_012),
        (__alpha_meta_alpha_013, compute_alpha_013),
        (__alpha_meta_alpha_014, compute_alpha_014),
        (__alpha_meta_alpha_015, compute_alpha_015),
        (__alpha_meta_alpha_016, compute_alpha_016),
        (__alpha_meta_alpha_017, compute_alpha_017),
        (__alpha_meta_alpha_018, compute_alpha_018),
        (__alpha_meta_alpha_019, compute_alpha_019),
        (__alpha_meta_alpha_020, compute_alpha_020),
        (__alpha_meta_alpha_021, compute_alpha_021),
        (__alpha_meta_alpha_022, compute_alpha_022),
        (__alpha_meta_alpha_023, compute_alpha_023),
        (__alpha_meta_alpha_024, compute_alpha_024),
        (__alpha_meta_alpha_025, compute_alpha_025),
        (__alpha_meta_alpha_026, compute_alpha_026),
        (__alpha_meta_alpha_027, compute_alpha_027),
        (__alpha_meta_alpha_028, compute_alpha_028),
        (__alpha_meta_alpha_029, compute_alpha_029),
        (__alpha_meta_alpha_030, compute_alpha_030),
        (__alpha_meta_alpha_031, compute_alpha_031),
        (__alpha_meta_alpha_032, compute_alpha_032),
        (__alpha_meta_alpha_033, compute_alpha_033),
        (__alpha_meta_alpha_034, compute_alpha_034),
        (__alpha_meta_alpha_035, compute_alpha_035),
        (__alpha_meta_alpha_036, compute_alpha_036),
        (__alpha_meta_alpha_037, compute_alpha_037),
        (__alpha_meta_alpha_038, compute_alpha_038),
        (__alpha_meta_alpha_039, compute_alpha_039),
        (__alpha_meta_alpha_040, compute_alpha_040),
        (__alpha_meta_alpha_041, compute_alpha_041),
        (__alpha_meta_alpha_042, compute_alpha_042),
        (__alpha_meta_alpha_043, compute_alpha_043),
        (__alpha_meta_alpha_044, compute_alpha_044),
        (__alpha_meta_alpha_045, compute_alpha_045),
        (__alpha_meta_alpha_046, compute_alpha_046),
        (__alpha_meta_alpha_047, compute_alpha_047),
        (__alpha_meta_alpha_048, compute_alpha_048),
        (__alpha_meta_alpha_049, compute_alpha_049),
        (__alpha_meta_alpha_050, compute_alpha_050),
        (__alpha_meta_alpha_051, compute_alpha_051),
        (__alpha_meta_alpha_052, compute_alpha_052),
        (__alpha_meta_alpha_053, compute_alpha_053),
        (__alpha_meta_alpha_054, compute_alpha_054),
        (__alpha_meta_alpha_055, compute_alpha_055),
        (__alpha_meta_alpha_056, compute_alpha_056),
        (__alpha_meta_alpha_057, compute_alpha_057),
        (__alpha_meta_alpha_058, compute_alpha_058),
        (__alpha_meta_alpha_059, compute_alpha_059),
        (__alpha_meta_alpha_060, compute_alpha_060),
        (__alpha_meta_alpha_061, compute_alpha_061),
        (__alpha_meta_alpha_062, compute_alpha_062),
        (__alpha_meta_alpha_063, compute_alpha_063),
        (__alpha_meta_alpha_064, compute_alpha_064),
        (__alpha_meta_alpha_065, compute_alpha_065),
        (__alpha_meta_alpha_066, compute_alpha_066),
        (__alpha_meta_alpha_067, compute_alpha_067),
        (__alpha_meta_alpha_068, compute_alpha_068),
        (__alpha_meta_alpha_069, compute_alpha_069),
        (__alpha_meta_alpha_070, compute_alpha_070),
        (__alpha_meta_alpha_071, compute_alpha_071),
        (__alpha_meta_alpha_072, compute_alpha_072),
        (__alpha_meta_alpha_073, compute_alpha_073),
        (__alpha_meta_alpha_074, compute_alpha_074),
        (__alpha_meta_alpha_075, compute_alpha_075),
        (__alpha_meta_alpha_076, compute_alpha_076),
        (__alpha_meta_alpha_077, compute_alpha_077),
        (__alpha_meta_alpha_078, compute_alpha_078),
        (__alpha_meta_alpha_079, compute_alpha_079),
        (__alpha_meta_alpha_080, compute_alpha_080),
        (__alpha_meta_alpha_081, compute_alpha_081),
        (__alpha_meta_alpha_082, compute_alpha_082),
        (__alpha_meta_alpha_083, compute_alpha_083),
        (__alpha_meta_alpha_084, compute_alpha_084),
        (__alpha_meta_alpha_085, compute_alpha_085),
        (__alpha_meta_alpha_086, compute_alpha_086),
        (__alpha_meta_alpha_087, compute_alpha_087),
        (__alpha_meta_alpha_088, compute_alpha_088),
        (__alpha_meta_alpha_089, compute_alpha_089),
        (__alpha_meta_alpha_090, compute_alpha_090),
        (__alpha_meta_alpha_091, compute_alpha_091),
        (__alpha_meta_alpha_092, compute_alpha_092),
        (__alpha_meta_alpha_093, compute_alpha_093),
        (__alpha_meta_alpha_094, compute_alpha_094),
        (__alpha_meta_alpha_095, compute_alpha_095),
        (__alpha_meta_alpha_096, compute_alpha_096),
        (__alpha_meta_alpha_097, compute_alpha_097),
        (__alpha_meta_alpha_098, compute_alpha_098),
        (__alpha_meta_alpha_099, compute_alpha_099),
        (__alpha_meta_alpha_100, compute_alpha_100),
        (__alpha_meta_alpha_101, compute_alpha_101),
    ]
