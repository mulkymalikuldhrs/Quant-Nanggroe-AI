"""Academic Alpha Factors (Fama-French, Carhart).

Implements 6 academic alpha factors based on classic asset pricing models.

Fama-French 3-factor model (1993):
- MKT_RF: Market factor (21-day return z-score)
- SMB: Size factor (inverse dollar-volume z-score)
- HML: Value factor (inverse 252-day return z-score)

Fama-French 5-factor model (2015):
- RMW: Profitability factor (inverse volatility z-score)
- CMA: Investment factor (inverse volume growth z-score)

Carhart 4-factor model (1997):
- CARHART_MOM: Momentum factor (12m-1m return z-score)

All factors use price-based proxies when fundamental data is unavailable.
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

def _cross_sectional_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Per-row z-score: (x - row_mean) / row_std; zero/NaN std rows -> NaN."""
    mean = df.mean(axis=1, skipna=True)
    std = df.std(axis=1, ddof=1, skipna=True)
    centered = df.sub(mean, axis=0)
    result = centered.div(std.where(std > 0), axis=0)
    return result.replace([np.inf, -np.inf], np.nan)


def _cross_sectional_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Per-row z-score: (x - row_mean) / row_std; zero/NaN std rows -> NaN."""
    mean = df.mean(axis=1, skipna=True)
    std = df.std(axis=1, ddof=1, skipna=True)
    centered = df.sub(mean, axis=0)
    result = centered.div(std.where(std > 0), axis=0)
    return result.replace([np.inf, -np.inf], np.nan)



__alpha_meta_carhart_mom = {
    'id': 'academic_carhart_mom',
    'nickname': 'Carhart 1997 momentum — 12m-1m return',
    'theme': ['momentum'],
    'formula_latex': r'\mathrm{zscore}_{x}\bigl((\mathrm{close}_t - \mathrm{close}_{t-252})/\mathrm{close}_{t-252} - (\mathrm{close}_t - \mathrm{close}_{t-21})/\mathrm{close}_{t-21}\bigr)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 252,
    'notes': (
        'Carhart (1997) UMD momentum factor. 12-month return minus 1-month return, '
        'cross-sectional z-score per date for long-short ranking. Top z-scores = '
        'winners. Constructed directly from prices, so this matches the original '
        'definition modulo the z-score wrapper. Canonical 252d window; declared '
        'decay_horizon=60 due to registry schema cap (le=60); real signal horizon=252.'
    ),
}


def compute_carhart_mom(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return 252-day minus 21-day return z-score (Carhart UMD).

    Uses canonical (252, 21) windows without silent shrink on short panels.
    Short panels produce all-NaN; the registry surfaces this as >95% NaN
    (RegistryError) rather than returning a misleading shrunk-window value.
    """
    close = panel['close']
    ret_long = safe_div(delta(close, 252), close.shift(252))
    ret_short = safe_div(delta(close, 21), close.shift(21))
    return _cross_sectional_zscore(ret_long - ret_short)


__alpha_meta_cma = {
    'id': 'academic_cma',
    'nickname': '[PRICE PROXY] FF2015 CMA — investment via inverse volume growth',
    'theme': ['quality'],
    'formula_latex': r'\mathrm{zscore}_{x}\bigl(-\Delta_{60}\log(\mathrm{ts\_mean}(\mathrm{volume},\,60) + 1)\bigr)',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 120,
    'notes': (
        '[PRICE PROXY] for the Fama-French (2015) CMA (Conservative Minus '
        'Aggressive) investment factor. The original definition uses total-asset '
        'growth from fundamental data; here we use the negative 60-day change in '
        'log average volume as an activity-growth proxy, then cross-sectional '
        'z-score per date for long-short ranking. Top z-scores = volume contraction '
        '(conservative / low-growth proxy).'
    ),
}


def compute_cma(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return inverse 60-day log-volume change z-score per stock.

    Uses the canonical 60-bar rolling mean + 60-bar delta windows without
    silent shrink on short panels. Short panels produce all-NaN; the
    registry surfaces this as >95% NaN (RegistryError) so the user sees
    "insufficient history" rather than a misleading shrunk-window value.
    """
    volume = panel['volume']
    log_avg_vol = np.log(ts_mean(volume, 60) + 1.0)
    growth = delta(log_avg_vol, 60)
    return _cross_sectional_zscore(-growth)


__alpha_meta_hml = {
    'id': 'academic_hml',
    'nickname': '[PRICE PROXY] FF1993 HML — value via inverse 252d return',
    'theme': ['value'],
    'formula_latex': r'\mathrm{zscore}_{x}\bigl(-(\mathrm{close}_t - \mathrm{close}_{t-252}) / \mathrm{close}_{t-252}\bigr)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 252,
    'notes': (
        '[PRICE PROXY] for the Fama-French (1993) HML (High Minus Low) value factor. '
        'The original definition uses book-to-market ratio from fundamental data; here '
        'we use the negative 252-day total return as a long-term reversal proxy, then '
        'cross-sectional z-score per date for long-short ranking. Top z-scores = '
        'long-term underperformers (deeper value). Canonical 252d window; declared '
        'decay_horizon=60 due to registry schema cap (le=60); real signal horizon=252.'
    ),
}


def compute_hml(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return inverse 252-day return cross-sectional z-score per stock.

    Uses the canonical 252-day window without silent shrink on short panels.
    Short panels produce an all-NaN result, which the registry surfaces as a
    >95% NaN error (RegistryError) so the user sees "insufficient history"
    instead of a misleading shrunk-window value.
    """
    close = panel['close']
    ret = safe_div(delta(close, 252), close.shift(252))
    return _cross_sectional_zscore(-ret)


__alpha_meta_mkt_rf = {
    'id': 'academic_mkt_rf',
    'nickname': '[PRICE PROXY] Market factor (Sharpe 1964) — 21d demeaned return',
    'theme': ['momentum'],
    'formula_latex': r'\mathrm{zscore}_{x}\bigl((\mathrm{close}_t - \mathrm{close}_{t-21}) / \mathrm{close}_{t-21}\bigr)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 21,
    'min_warmup_bars': 21,
    'notes': (
        '[PRICE PROXY] for the Sharpe (1964) / Fama-French market factor (MKT-RF). '
        'The original definition uses value-weighted market excess returns; here we '
        'use a 21-day per-stock total return and cross-sectional z-score per date '
        'for long-short ranking. Top z-scores = strong recent winners; bottom = losers.'
    ),
}


def compute_mkt_rf(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return 21-day return cross-sectional z-score per stock."""
    close = panel['close']
    ret = safe_div(delta(close, 21), close.shift(21))
    return _cross_sectional_zscore(ret)


__alpha_meta_rmw = {
    'id': 'academic_rmw',
    'nickname': '[PRICE PROXY] FF2015 RMW — quality via inverse 60d volatility',
    'theme': ['quality'],
    'formula_latex': r'\mathrm{zscore}_{x}\bigl(-\mathrm{ts\_std}((\mathrm{close}_t - \mathrm{close}_{t-1}) / \mathrm{close}_{t-1},\,60)\bigr)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
    'notes': (
        '[PRICE PROXY] for the Fama-French (2015) RMW (Robust Minus Weak) '
        'profitability factor. The original definition uses operating profitability '
        'from fundamental data; here we use the negative of 60-day return volatility '
        'as a low-vol-quality proxy, then cross-sectional z-score per date for '
        'long-short ranking. Top z-scores = lower vol (quality / robust).'
    ),
}


def compute_rmw(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return inverse 60-day return-volatility z-score per stock."""
    close = panel['close']
    ret_1d = safe_div(delta(close, 1), close.shift(1))
    vol_60 = ts_std(ret_1d, 60)
    return _cross_sectional_zscore(-vol_60)


__alpha_meta_smb = {
    'id': 'academic_smb',
    'nickname': '[PRICE PROXY] FF1993 SMB — small-minus-big via inverse dollar-volume',
    'theme': ['quality'],
    'formula_latex': r'\mathrm{zscore}_{x}\bigl(-\log(\mathrm{ts\_mean}(\mathrm{volume} \cdot \mathrm{close},\,60) + 1)\bigr)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
    'notes': (
        '[PRICE PROXY] for the Fama-French (1993) SMB (Small Minus Big) size factor. '
        'The original definition uses market capitalization from book equity data; here '
        'we use the negative log of 60-day average dollar volume (close * volume) as a '
        'liquidity-weighted size proxy, then cross-sectional z-score per date for '
        'long-short ranking. Top z-scores = smaller / less liquid names.'
    ),
}


def compute_smb(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return inverse log 60-day dollar-volume z-score per stock."""
    close = panel['close']
    volume = panel['volume']
    dollar_volume = volume * close
    avg = ts_mean(dollar_volume, 60)
    log_size = np.log(avg + 1.0)
    return _cross_sectional_zscore(-log_size)

def get_all_academic_factors() -> list:
    """Return list of (meta_dict, compute_fn) tuples for all Academic Alpha Factors (Fama-French, Carhart) factors."""
    return [
        (__alpha_meta_carhart_mom, compute_carhart_mom),
        (__alpha_meta_cma, compute_cma),
        (__alpha_meta_hml, compute_hml),
        (__alpha_meta_mkt_rf, compute_mkt_rf),
        (__alpha_meta_rmw, compute_rmw),
        (__alpha_meta_smb, compute_smb),
    ]
