"""Qlib 158 Alpha Factors.

Implements 154 Qlib alpha factors from Microsoft Qlib.

Adapted from microsoft/qlib:qlib/contrib/data/handler.py (Apache-2.0).
Copyright (c) Microsoft Corporation.

Each factor uses the __alpha_meta__ + compute(panel) pattern.
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

# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 BETA10: formula = (\\mathrm{close}_t - \\mathrm{close}_{{t-10}}) / (10\\,\\mathrm{close})."""


__alpha_meta_beta10 = {
    'id': 'qlib158_beta10',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close}_t - \\\\mathrm{close}_{{t-10}}) / (10\\\\,\\\\mathrm{close})',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_beta10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 BETA10 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(delta(c, 10), c) / float(10)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 BETA20: formula = (\\mathrm{close}_t - \\mathrm{close}_{{t-20}}) / (20\\,\\mathrm{close})."""


__alpha_meta_beta20 = {
    'id': 'qlib158_beta20',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close}_t - \\\\mathrm{close}_{{t-20}}) / (20\\\\,\\\\mathrm{close})',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_beta20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 BETA20 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(delta(c, 20), c) / float(20)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 BETA30: formula = (\\mathrm{close}_t - \\mathrm{close}_{{t-30}}) / (30\\,\\mathrm{close})."""


__alpha_meta_beta30 = {
    'id': 'qlib158_beta30',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close}_t - \\\\mathrm{close}_{{t-30}}) / (30\\\\,\\\\mathrm{close})',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_beta30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 BETA30 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(delta(c, 30), c) / float(30)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 BETA5: formula = (\\mathrm{close}_t - \\mathrm{close}_{{t-5}}) / (5\\,\\mathrm{close})."""


__alpha_meta_beta5 = {
    'id': 'qlib158_beta5',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close}_t - \\\\mathrm{close}_{{t-5}}) / (5\\\\,\\\\mathrm{close})',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_beta5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 BETA5 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(delta(c, 5), c) / float(5)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 BETA60: formula = (\\mathrm{close}_t - \\mathrm{close}_{{t-60}}) / (60\\,\\mathrm{close})."""


__alpha_meta_beta60 = {
    'id': 'qlib158_beta60',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close}_t - \\\\mathrm{close}_{{t-60}}) / (60\\\\,\\\\mathrm{close})',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_beta60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 BETA60 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(delta(c, 60), c) / float(60)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTD10: formula = \\mathrm{CNTP}_10 - \\mathrm{CNTN}_10."""


__alpha_meta_cntd10 = {
    'id': 'qlib158_cntd10',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{CNTP}_10 - \\\\mathrm{CNTN}_10',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_cntd10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTD10 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    dn = (c < c.shift(1)).astype('float64')
    up_w = up.rolling(window=10, min_periods=10).mean()
    dn_w = dn.rolling(window=10, min_periods=10).mean()
    return up_w - dn_w


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTD20: formula = \\mathrm{CNTP}_20 - \\mathrm{CNTN}_20."""


__alpha_meta_cntd20 = {
    'id': 'qlib158_cntd20',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{CNTP}_20 - \\\\mathrm{CNTN}_20',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_cntd20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTD20 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    dn = (c < c.shift(1)).astype('float64')
    up_w = up.rolling(window=20, min_periods=20).mean()
    dn_w = dn.rolling(window=20, min_periods=20).mean()
    return up_w - dn_w


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTD30: formula = \\mathrm{CNTP}_30 - \\mathrm{CNTN}_30."""


__alpha_meta_cntd30 = {
    'id': 'qlib158_cntd30',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{CNTP}_30 - \\\\mathrm{CNTN}_30',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_cntd30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTD30 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    dn = (c < c.shift(1)).astype('float64')
    up_w = up.rolling(window=30, min_periods=30).mean()
    dn_w = dn.rolling(window=30, min_periods=30).mean()
    return up_w - dn_w


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTD5: formula = \\mathrm{CNTP}_5 - \\mathrm{CNTN}_5."""


__alpha_meta_cntd5 = {
    'id': 'qlib158_cntd5',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{CNTP}_5 - \\\\mathrm{CNTN}_5',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_cntd5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTD5 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    dn = (c < c.shift(1)).astype('float64')
    up_w = up.rolling(window=5, min_periods=5).mean()
    dn_w = dn.rolling(window=5, min_periods=5).mean()
    return up_w - dn_w


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTD60: formula = \\mathrm{CNTP}_60 - \\mathrm{CNTN}_60."""


__alpha_meta_cntd60 = {
    'id': 'qlib158_cntd60',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{CNTP}_60 - \\\\mathrm{CNTN}_60',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_cntd60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTD60 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    dn = (c < c.shift(1)).astype('float64')
    up_w = up.rolling(window=60, min_periods=60).mean()
    dn_w = dn.rolling(window=60, min_periods=60).mean()
    return up_w - dn_w


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTN10: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}<\\mathrm{close}_{{-1}}], 10)."""


__alpha_meta_cntn10 = {
    'id': 'qlib158_cntn10',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}<\\\\mathrm{close}_{{-1}}], 10)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_cntn10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTN10 on the supplied OHLCV panel."""
    c = panel['close']
    dn = (c < c.shift(1)).astype('float64')
    return dn.rolling(window=10, min_periods=10).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTN20: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}<\\mathrm{close}_{{-1}}], 20)."""


__alpha_meta_cntn20 = {
    'id': 'qlib158_cntn20',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}<\\\\mathrm{close}_{{-1}}], 20)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_cntn20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTN20 on the supplied OHLCV panel."""
    c = panel['close']
    dn = (c < c.shift(1)).astype('float64')
    return dn.rolling(window=20, min_periods=20).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTN30: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}<\\mathrm{close}_{{-1}}], 30)."""


__alpha_meta_cntn30 = {
    'id': 'qlib158_cntn30',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}<\\\\mathrm{close}_{{-1}}], 30)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_cntn30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTN30 on the supplied OHLCV panel."""
    c = panel['close']
    dn = (c < c.shift(1)).astype('float64')
    return dn.rolling(window=30, min_periods=30).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTN5: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}<\\mathrm{close}_{{-1}}], 5)."""


__alpha_meta_cntn5 = {
    'id': 'qlib158_cntn5',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}<\\\\mathrm{close}_{{-1}}], 5)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_cntn5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTN5 on the supplied OHLCV panel."""
    c = panel['close']
    dn = (c < c.shift(1)).astype('float64')
    return dn.rolling(window=5, min_periods=5).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTN60: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}<\\mathrm{close}_{{-1}}], 60)."""


__alpha_meta_cntn60 = {
    'id': 'qlib158_cntn60',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}<\\\\mathrm{close}_{{-1}}], 60)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_cntn60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTN60 on the supplied OHLCV panel."""
    c = panel['close']
    dn = (c < c.shift(1)).astype('float64')
    return dn.rolling(window=60, min_periods=60).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTP10: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}>\\mathrm{close}_{{-1}}], 10)."""


__alpha_meta_cntp10 = {
    'id': 'qlib158_cntp10',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}>\\\\mathrm{close}_{{-1}}], 10)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_cntp10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTP10 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    return up.rolling(window=10, min_periods=10).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTP20: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}>\\mathrm{close}_{{-1}}], 20)."""


__alpha_meta_cntp20 = {
    'id': 'qlib158_cntp20',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}>\\\\mathrm{close}_{{-1}}], 20)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_cntp20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTP20 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    return up.rolling(window=20, min_periods=20).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTP30: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}>\\mathrm{close}_{{-1}}], 30)."""


__alpha_meta_cntp30 = {
    'id': 'qlib158_cntp30',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}>\\\\mathrm{close}_{{-1}}], 30)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_cntp30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTP30 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    return up.rolling(window=30, min_periods=30).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTP5: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}>\\mathrm{close}_{{-1}}], 5)."""


__alpha_meta_cntp5 = {
    'id': 'qlib158_cntp5',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}>\\\\mathrm{close}_{{-1}}], 5)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_cntp5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTP5 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    return up.rolling(window=5, min_periods=5).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CNTP60: formula = \\mathrm{rolling\\_mean}(\\mathrm{1}[\\mathrm{close}>\\mathrm{close}_{{-1}}], 60)."""


__alpha_meta_cntp60 = {
    'id': 'qlib158_cntp60',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{rolling\\\\_mean}(\\\\mathrm{1}[\\\\mathrm{close}>\\\\mathrm{close}_{{-1}}], 60)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_cntp60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CNTP60 on the supplied OHLCV panel."""
    c = panel['close']
    up = (c > c.shift(1)).astype('float64')
    return up.rolling(window=60, min_periods=60).mean()


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORD10: formula = \\mathrm{ts\\_corr}(\\mathrm{close}/\\mathrm{close}_{{-1}}, \\log((\\mathrm{volume}+1)/(\\mathrm{volume}_{{-1}}+1)), 10)."""


__alpha_meta_cord10 = {
    'id': 'qlib158_cord10',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}/\\\\mathrm{close}_{{-1}}, \\\\log((\\\\mathrm{volume}+1)/(\\\\mathrm{volume}_{{-1}}+1)), 10)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_cord10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORD10 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    c_ret = safe_div(c, c.shift(1))
    v_ret = safe_div(v + 1.0, v.shift(1) + 1.0)
    logvr = np.log(v_ret)
    return ts_corr(c_ret, logvr, 10)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORD20: formula = \\mathrm{ts\\_corr}(\\mathrm{close}/\\mathrm{close}_{{-1}}, \\log((\\mathrm{volume}+1)/(\\mathrm{volume}_{{-1}}+1)), 20)."""


__alpha_meta_cord20 = {
    'id': 'qlib158_cord20',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}/\\\\mathrm{close}_{{-1}}, \\\\log((\\\\mathrm{volume}+1)/(\\\\mathrm{volume}_{{-1}}+1)), 20)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_cord20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORD20 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    c_ret = safe_div(c, c.shift(1))
    v_ret = safe_div(v + 1.0, v.shift(1) + 1.0)
    logvr = np.log(v_ret)
    return ts_corr(c_ret, logvr, 20)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORD30: formula = \\mathrm{ts\\_corr}(\\mathrm{close}/\\mathrm{close}_{{-1}}, \\log((\\mathrm{volume}+1)/(\\mathrm{volume}_{{-1}}+1)), 30)."""


__alpha_meta_cord30 = {
    'id': 'qlib158_cord30',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}/\\\\mathrm{close}_{{-1}}, \\\\log((\\\\mathrm{volume}+1)/(\\\\mathrm{volume}_{{-1}}+1)), 30)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_cord30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORD30 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    c_ret = safe_div(c, c.shift(1))
    v_ret = safe_div(v + 1.0, v.shift(1) + 1.0)
    logvr = np.log(v_ret)
    return ts_corr(c_ret, logvr, 30)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORD5: formula = \\mathrm{ts\\_corr}(\\mathrm{close}/\\mathrm{close}_{{-1}}, \\log((\\mathrm{volume}+1)/(\\mathrm{volume}_{{-1}}+1)), 5)."""


__alpha_meta_cord5 = {
    'id': 'qlib158_cord5',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}/\\\\mathrm{close}_{{-1}}, \\\\log((\\\\mathrm{volume}+1)/(\\\\mathrm{volume}_{{-1}}+1)), 5)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_cord5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORD5 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    c_ret = safe_div(c, c.shift(1))
    v_ret = safe_div(v + 1.0, v.shift(1) + 1.0)
    logvr = np.log(v_ret)
    return ts_corr(c_ret, logvr, 5)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORD60: formula = \\mathrm{ts\\_corr}(\\mathrm{close}/\\mathrm{close}_{{-1}}, \\log((\\mathrm{volume}+1)/(\\mathrm{volume}_{{-1}}+1)), 60)."""


__alpha_meta_cord60 = {
    'id': 'qlib158_cord60',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}/\\\\mathrm{close}_{{-1}}, \\\\log((\\\\mathrm{volume}+1)/(\\\\mathrm{volume}_{{-1}}+1)), 60)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_cord60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORD60 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    c_ret = safe_div(c, c.shift(1))
    v_ret = safe_div(v + 1.0, v.shift(1) + 1.0)
    logvr = np.log(v_ret)
    return ts_corr(c_ret, logvr, 60)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORR10: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, \\log(\\mathrm{volume}+1), 10)."""


__alpha_meta_corr10 = {
    'id': 'qlib158_corr10',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, \\\\log(\\\\mathrm{volume}+1), 10)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_corr10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORR10 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    logv = np.log1p(v)
    return ts_corr(c, logv, 10)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORR20: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, \\log(\\mathrm{volume}+1), 20)."""


__alpha_meta_corr20 = {
    'id': 'qlib158_corr20',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, \\\\log(\\\\mathrm{volume}+1), 20)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_corr20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORR20 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    logv = np.log1p(v)
    return ts_corr(c, logv, 20)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORR30: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, \\log(\\mathrm{volume}+1), 30)."""


__alpha_meta_corr30 = {
    'id': 'qlib158_corr30',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, \\\\log(\\\\mathrm{volume}+1), 30)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_corr30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORR30 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    logv = np.log1p(v)
    return ts_corr(c, logv, 30)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORR5: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, \\log(\\mathrm{volume}+1), 5)."""


__alpha_meta_corr5 = {
    'id': 'qlib158_corr5',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, \\\\log(\\\\mathrm{volume}+1), 5)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_corr5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORR5 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    logv = np.log1p(v)
    return ts_corr(c, logv, 5)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 CORR60: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, \\log(\\mathrm{volume}+1), 60)."""


__alpha_meta_corr60 = {
    'id': 'qlib158_corr60',
    'theme': ['volume', 'microstructure'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, \\\\log(\\\\mathrm{volume}+1), 60)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_corr60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 CORR60 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    logv = np.log1p(v)
    return ts_corr(c, logv, 60)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMAX10: formula = \\mathrm{ts\\_argmax}(\\mathrm{high}, 10) / 10."""


__alpha_meta_imax10 = {
    'id': 'qlib158_imax10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 10) / 10',
    'columns_required': ['high'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_imax10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMAX10 on the supplied OHLCV panel."""
    h = panel['high']
    return ts_argmax(h, 10) / float(10)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMAX20: formula = \\mathrm{ts\\_argmax}(\\mathrm{high}, 20) / 20."""


__alpha_meta_imax20 = {
    'id': 'qlib158_imax20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 20) / 20',
    'columns_required': ['high'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_imax20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMAX20 on the supplied OHLCV panel."""
    h = panel['high']
    return ts_argmax(h, 20) / float(20)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMAX30: formula = \\mathrm{ts\\_argmax}(\\mathrm{high}, 30) / 30."""


__alpha_meta_imax30 = {
    'id': 'qlib158_imax30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 30) / 30',
    'columns_required': ['high'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_imax30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMAX30 on the supplied OHLCV panel."""
    h = panel['high']
    return ts_argmax(h, 30) / float(30)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMAX5: formula = \\mathrm{ts\\_argmax}(\\mathrm{high}, 5) / 5."""


__alpha_meta_imax5 = {
    'id': 'qlib158_imax5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 5) / 5',
    'columns_required': ['high'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_imax5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMAX5 on the supplied OHLCV panel."""
    h = panel['high']
    return ts_argmax(h, 5) / float(5)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMAX60: formula = \\mathrm{ts\\_argmax}(\\mathrm{high}, 60) / 60."""


__alpha_meta_imax60 = {
    'id': 'qlib158_imax60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 60) / 60',
    'columns_required': ['high'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_imax60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMAX60 on the supplied OHLCV panel."""
    h = panel['high']
    return ts_argmax(h, 60) / float(60)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMIN10: formula = \\mathrm{ts\\_argmin}(\\mathrm{low}, 10) / 10."""


__alpha_meta_imin10 = {
    'id': 'qlib158_imin10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 10) / 10',
    'columns_required': ['low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_imin10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMIN10 on the supplied OHLCV panel."""
    lo = panel['low']
    return ts_argmin(lo, 10) / float(10)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMIN20: formula = \\mathrm{ts\\_argmin}(\\mathrm{low}, 20) / 20."""


__alpha_meta_imin20 = {
    'id': 'qlib158_imin20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 20) / 20',
    'columns_required': ['low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_imin20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMIN20 on the supplied OHLCV panel."""
    lo = panel['low']
    return ts_argmin(lo, 20) / float(20)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMIN30: formula = \\mathrm{ts\\_argmin}(\\mathrm{low}, 30) / 30."""


__alpha_meta_imin30 = {
    'id': 'qlib158_imin30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 30) / 30',
    'columns_required': ['low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_imin30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMIN30 on the supplied OHLCV panel."""
    lo = panel['low']
    return ts_argmin(lo, 30) / float(30)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMIN5: formula = \\mathrm{ts\\_argmin}(\\mathrm{low}, 5) / 5."""


__alpha_meta_imin5 = {
    'id': 'qlib158_imin5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 5) / 5',
    'columns_required': ['low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_imin5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMIN5 on the supplied OHLCV panel."""
    lo = panel['low']
    return ts_argmin(lo, 5) / float(5)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMIN60: formula = \\mathrm{ts\\_argmin}(\\mathrm{low}, 60) / 60."""


__alpha_meta_imin60 = {
    'id': 'qlib158_imin60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 60) / 60',
    'columns_required': ['low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_imin60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMIN60 on the supplied OHLCV panel."""
    lo = panel['low']
    return ts_argmin(lo, 60) / float(60)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMXD10: formula = (\\mathrm{ts\\_argmax}(\\mathrm{high}, 10) - \\mathrm{ts\\_argmin}(\\mathrm{low}, 10)) / 10."""


__alpha_meta_imxd10 = {
    'id': 'qlib158_imxd10',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 10) - \\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 10)) / 10',
    'columns_required': ['high', 'low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_imxd10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMXD10 on the supplied OHLCV panel."""
    h = panel['high']
    lo = panel['low']
    return (ts_argmax(h, 10) - ts_argmin(lo, 10)) / float(10)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMXD20: formula = (\\mathrm{ts\\_argmax}(\\mathrm{high}, 20) - \\mathrm{ts\\_argmin}(\\mathrm{low}, 20)) / 20."""


__alpha_meta_imxd20 = {
    'id': 'qlib158_imxd20',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 20) - \\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 20)) / 20',
    'columns_required': ['high', 'low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_imxd20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMXD20 on the supplied OHLCV panel."""
    h = panel['high']
    lo = panel['low']
    return (ts_argmax(h, 20) - ts_argmin(lo, 20)) / float(20)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMXD30: formula = (\\mathrm{ts\\_argmax}(\\mathrm{high}, 30) - \\mathrm{ts\\_argmin}(\\mathrm{low}, 30)) / 30."""


__alpha_meta_imxd30 = {
    'id': 'qlib158_imxd30',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 30) - \\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 30)) / 30',
    'columns_required': ['high', 'low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_imxd30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMXD30 on the supplied OHLCV panel."""
    h = panel['high']
    lo = panel['low']
    return (ts_argmax(h, 30) - ts_argmin(lo, 30)) / float(30)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMXD5: formula = (\\mathrm{ts\\_argmax}(\\mathrm{high}, 5) - \\mathrm{ts\\_argmin}(\\mathrm{low}, 5)) / 5."""


__alpha_meta_imxd5 = {
    'id': 'qlib158_imxd5',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 5) - \\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 5)) / 5',
    'columns_required': ['high', 'low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_imxd5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMXD5 on the supplied OHLCV panel."""
    h = panel['high']
    lo = panel['low']
    return (ts_argmax(h, 5) - ts_argmin(lo, 5)) / float(5)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 IMXD60: formula = (\\mathrm{ts\\_argmax}(\\mathrm{high}, 60) - \\mathrm{ts\\_argmin}(\\mathrm{low}, 60)) / 60."""


__alpha_meta_imxd60 = {
    'id': 'qlib158_imxd60',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{ts\\\\_argmax}(\\\\mathrm{high}, 60) - \\\\mathrm{ts\\\\_argmin}(\\\\mathrm{low}, 60)) / 60',
    'columns_required': ['high', 'low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_imxd60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 IMXD60 on the supplied OHLCV panel."""
    h = panel['high']
    lo = panel['low']
    return (ts_argmax(h, 60) - ts_argmin(lo, 60)) / float(60)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KLEN: formula = (\\mathrm{high} - \\mathrm{low}) / \\mathrm{open}."""


__alpha_meta_klen = {
    'id': 'qlib158_klen',
    'theme': ['microstructure'],
    'formula_latex': '(\\\\mathrm{high} - \\\\mathrm{low}) / \\\\mathrm{open}',
    'columns_required': ['open', 'high', 'low'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_klen(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KLEN on the supplied OHLCV panel."""
    o = panel['open']
    h = panel['high']
    lo = panel['low']
    return safe_div(h - lo, o)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KLOW: formula = (\\min(\\mathrm{open}, \\mathrm{close}) - \\mathrm{low}) / \\mathrm{open}."""


__alpha_meta_klow = {
    'id': 'qlib158_klow',
    'theme': ['microstructure'],
    'formula_latex': '(\\\\min(\\\\mathrm{open}, \\\\mathrm{close}) - \\\\mathrm{low}) / \\\\mathrm{open}',
    'columns_required': ['open', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_klow(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KLOW on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    lo = panel['low']
    lower = o.where(o <= c, c)
    return safe_div(lower - lo, o)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KLOW2: formula = (\\min(\\mathrm{open}, \\mathrm{close}) - \\mathrm{low}) / (\\mathrm{high} - \\mathrm{low})."""


__alpha_meta_klow2 = {
    'id': 'qlib158_klow2',
    'theme': ['microstructure'],
    'formula_latex': '(\\\\min(\\\\mathrm{open}, \\\\mathrm{close}) - \\\\mathrm{low}) / (\\\\mathrm{high} - \\\\mathrm{low})',
    'columns_required': ['open', 'high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_klow2(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KLOW2 on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    lower = o.where(o <= c, c)
    return safe_div(lower - lo, h - lo)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KMID: formula = (\\mathrm{close} - \\mathrm{open}) / \\mathrm{open}."""


__alpha_meta_kmid = {
    'id': 'qlib158_kmid',
    'theme': ['microstructure'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{open}) / \\\\mathrm{open}',
    'columns_required': ['open', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_kmid(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KMID on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    return safe_div(c - o, o)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KMID2: formula = (\\mathrm{close} - \\mathrm{open}) / (\\mathrm{high} - \\mathrm{low})."""


__alpha_meta_kmid2 = {
    'id': 'qlib158_kmid2',
    'theme': ['microstructure'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{open}) / (\\\\mathrm{high} - \\\\mathrm{low})',
    'columns_required': ['open', 'high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_kmid2(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KMID2 on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    return safe_div(c - o, h - lo)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KSFT: formula = (2\\,\\mathrm{close} - \\mathrm{high} - \\mathrm{low}) / \\mathrm{open}."""


__alpha_meta_ksft = {
    'id': 'qlib158_ksft',
    'theme': ['microstructure'],
    'formula_latex': '(2\\\\,\\\\mathrm{close} - \\\\mathrm{high} - \\\\mathrm{low}) / \\\\mathrm{open}',
    'columns_required': ['open', 'high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_ksft(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KSFT on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    return safe_div(2.0 * c - h - lo, o)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KSFT2: formula = (2\\,\\mathrm{close} - \\mathrm{high} - \\mathrm{low}) / (\\mathrm{high} - \\mathrm{low})."""


__alpha_meta_ksft2 = {
    'id': 'qlib158_ksft2',
    'theme': ['microstructure'],
    'formula_latex': '(2\\\\,\\\\mathrm{close} - \\\\mathrm{high} - \\\\mathrm{low}) / (\\\\mathrm{high} - \\\\mathrm{low})',
    'columns_required': ['open', 'high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_ksft2(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KSFT2 on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    return safe_div(2.0 * c - h - lo, h - lo)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KUP: formula = (\\mathrm{high} - \\max(\\mathrm{open}, \\mathrm{close})) / \\mathrm{open}."""


__alpha_meta_kup = {
    'id': 'qlib158_kup',
    'theme': ['microstructure'],
    'formula_latex': '(\\\\mathrm{high} - \\\\max(\\\\mathrm{open}, \\\\mathrm{close})) / \\\\mathrm{open}',
    'columns_required': ['open', 'high', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_kup(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KUP on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    h = panel['high']
    upper = o.where(o >= c, c)
    return safe_div(h - upper, o)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 KUP2: formula = (\\mathrm{high} - \\max(\\mathrm{open}, \\mathrm{close})) / (\\mathrm{high} - \\mathrm{low})."""


__alpha_meta_kup2 = {
    'id': 'qlib158_kup2',
    'theme': ['microstructure'],
    'formula_latex': '(\\\\mathrm{high} - \\\\max(\\\\mathrm{open}, \\\\mathrm{close})) / (\\\\mathrm{high} - \\\\mathrm{low})',
    'columns_required': ['open', 'high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 1,
    'min_warmup_bars': 1,
}


def compute_kup2(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 KUP2 on the supplied OHLCV panel."""
    o = panel['open']
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    upper = o.where(o >= c, c)
    return safe_div(h - upper, h - lo)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MA10: formula = \\mathrm{ts\\_mean}(\\mathrm{close}, 10) / \\mathrm{close}."""


__alpha_meta_ma10 = {
    'id': 'qlib158_ma10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 10) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_ma10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MA10 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_mean(c, 10), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MA20: formula = \\mathrm{ts\\_mean}(\\mathrm{close}, 20) / \\mathrm{close}."""


__alpha_meta_ma20 = {
    'id': 'qlib158_ma20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 20) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_ma20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MA20 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_mean(c, 20), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MA30: formula = \\mathrm{ts\\_mean}(\\mathrm{close}, 30) / \\mathrm{close}."""


__alpha_meta_ma30 = {
    'id': 'qlib158_ma30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 30) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_ma30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MA30 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_mean(c, 30), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MA5: formula = \\mathrm{ts\\_mean}(\\mathrm{close}, 5) / \\mathrm{close}."""


__alpha_meta_ma5 = {
    'id': 'qlib158_ma5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 5) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_ma5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MA5 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_mean(c, 5), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MA60: formula = \\mathrm{ts\\_mean}(\\mathrm{close}, 60) / \\mathrm{close}."""


__alpha_meta_ma60 = {
    'id': 'qlib158_ma60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 60) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_ma60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MA60 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_mean(c, 60), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MAX10: formula = \\mathrm{ts\\_max}(\\mathrm{high}, 10) / \\mathrm{close}."""


__alpha_meta_max10 = {
    'id': 'qlib158_max10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 10) / \\\\mathrm{close}',
    'columns_required': ['high', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_max10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MAX10 on the supplied OHLCV panel."""
    h = panel['high']
    c = panel['close']
    return safe_div(ts_max(h, 10), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MAX20: formula = \\mathrm{ts\\_max}(\\mathrm{high}, 20) / \\mathrm{close}."""


__alpha_meta_max20 = {
    'id': 'qlib158_max20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 20) / \\\\mathrm{close}',
    'columns_required': ['high', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_max20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MAX20 on the supplied OHLCV panel."""
    h = panel['high']
    c = panel['close']
    return safe_div(ts_max(h, 20), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MAX30: formula = \\mathrm{ts\\_max}(\\mathrm{high}, 30) / \\mathrm{close}."""


__alpha_meta_max30 = {
    'id': 'qlib158_max30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 30) / \\\\mathrm{close}',
    'columns_required': ['high', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_max30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MAX30 on the supplied OHLCV panel."""
    h = panel['high']
    c = panel['close']
    return safe_div(ts_max(h, 30), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MAX5: formula = \\mathrm{ts\\_max}(\\mathrm{high}, 5) / \\mathrm{close}."""


__alpha_meta_max5 = {
    'id': 'qlib158_max5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 5) / \\\\mathrm{close}',
    'columns_required': ['high', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_max5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MAX5 on the supplied OHLCV panel."""
    h = panel['high']
    c = panel['close']
    return safe_div(ts_max(h, 5), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MAX60: formula = \\mathrm{ts\\_max}(\\mathrm{high}, 60) / \\mathrm{close}."""


__alpha_meta_max60 = {
    'id': 'qlib158_max60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 60) / \\\\mathrm{close}',
    'columns_required': ['high', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_max60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MAX60 on the supplied OHLCV panel."""
    h = panel['high']
    c = panel['close']
    return safe_div(ts_max(h, 60), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MIN10: formula = \\mathrm{ts\\_min}(\\mathrm{low}, 10) / \\mathrm{close}."""


__alpha_meta_min10 = {
    'id': 'qlib158_min10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 10) / \\\\mathrm{close}',
    'columns_required': ['low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_min10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MIN10 on the supplied OHLCV panel."""
    lo = panel['low']
    c = panel['close']
    return safe_div(ts_min(lo, 10), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MIN20: formula = \\mathrm{ts\\_min}(\\mathrm{low}, 20) / \\mathrm{close}."""


__alpha_meta_min20 = {
    'id': 'qlib158_min20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 20) / \\\\mathrm{close}',
    'columns_required': ['low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_min20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MIN20 on the supplied OHLCV panel."""
    lo = panel['low']
    c = panel['close']
    return safe_div(ts_min(lo, 20), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MIN30: formula = \\mathrm{ts\\_min}(\\mathrm{low}, 30) / \\mathrm{close}."""


__alpha_meta_min30 = {
    'id': 'qlib158_min30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 30) / \\\\mathrm{close}',
    'columns_required': ['low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_min30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MIN30 on the supplied OHLCV panel."""
    lo = panel['low']
    c = panel['close']
    return safe_div(ts_min(lo, 30), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MIN5: formula = \\mathrm{ts\\_min}(\\mathrm{low}, 5) / \\mathrm{close}."""


__alpha_meta_min5 = {
    'id': 'qlib158_min5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 5) / \\\\mathrm{close}',
    'columns_required': ['low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_min5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MIN5 on the supplied OHLCV panel."""
    lo = panel['low']
    c = panel['close']
    return safe_div(ts_min(lo, 5), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 MIN60: formula = \\mathrm{ts\\_min}(\\mathrm{low}, 60) / \\mathrm{close}."""


__alpha_meta_min60 = {
    'id': 'qlib158_min60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 60) / \\\\mathrm{close}',
    'columns_required': ['low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_min60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 MIN60 on the supplied OHLCV panel."""
    lo = panel['low']
    c = panel['close']
    return safe_div(ts_min(lo, 60), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLD10: formula = \\mathrm{quantile}_{{0.2}}(\\mathrm{close}, 10) / \\mathrm{close}."""


__alpha_meta_qtld10 = {
    'id': 'qlib158_qtld10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.2}}(\\\\mathrm{close}, 10) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_qtld10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLD10 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=10, min_periods=10).quantile(0.2)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLD20: formula = \\mathrm{quantile}_{{0.2}}(\\mathrm{close}, 20) / \\mathrm{close}."""


__alpha_meta_qtld20 = {
    'id': 'qlib158_qtld20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.2}}(\\\\mathrm{close}, 20) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_qtld20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLD20 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=20, min_periods=20).quantile(0.2)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLD30: formula = \\mathrm{quantile}_{{0.2}}(\\mathrm{close}, 30) / \\mathrm{close}."""


__alpha_meta_qtld30 = {
    'id': 'qlib158_qtld30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.2}}(\\\\mathrm{close}, 30) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_qtld30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLD30 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=30, min_periods=30).quantile(0.2)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLD5: formula = \\mathrm{quantile}_{{0.2}}(\\mathrm{close}, 5) / \\mathrm{close}."""


__alpha_meta_qtld5 = {
    'id': 'qlib158_qtld5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.2}}(\\\\mathrm{close}, 5) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_qtld5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLD5 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=5, min_periods=5).quantile(0.2)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLD60: formula = \\mathrm{quantile}_{{0.2}}(\\mathrm{close}, 60) / \\mathrm{close}."""


__alpha_meta_qtld60 = {
    'id': 'qlib158_qtld60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.2}}(\\\\mathrm{close}, 60) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_qtld60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLD60 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=60, min_periods=60).quantile(0.2)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLU10: formula = \\mathrm{quantile}_{{0.8}}(\\mathrm{close}, 10) / \\mathrm{close}."""


__alpha_meta_qtlu10 = {
    'id': 'qlib158_qtlu10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.8}}(\\\\mathrm{close}, 10) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_qtlu10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLU10 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=10, min_periods=10).quantile(0.8)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLU20: formula = \\mathrm{quantile}_{{0.8}}(\\mathrm{close}, 20) / \\mathrm{close}."""


__alpha_meta_qtlu20 = {
    'id': 'qlib158_qtlu20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.8}}(\\\\mathrm{close}, 20) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_qtlu20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLU20 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=20, min_periods=20).quantile(0.8)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLU30: formula = \\mathrm{quantile}_{{0.8}}(\\mathrm{close}, 30) / \\mathrm{close}."""


__alpha_meta_qtlu30 = {
    'id': 'qlib158_qtlu30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.8}}(\\\\mathrm{close}, 30) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_qtlu30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLU30 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=30, min_periods=30).quantile(0.8)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLU5: formula = \\mathrm{quantile}_{{0.8}}(\\mathrm{close}, 5) / \\mathrm{close}."""


__alpha_meta_qtlu5 = {
    'id': 'qlib158_qtlu5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.8}}(\\\\mathrm{close}, 5) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_qtlu5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLU5 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=5, min_periods=5).quantile(0.8)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 QTLU60: formula = \\mathrm{quantile}_{{0.8}}(\\mathrm{close}, 60) / \\mathrm{close}."""


__alpha_meta_qtlu60 = {
    'id': 'qlib158_qtlu60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{quantile}_{{0.8}}(\\\\mathrm{close}, 60) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_qtlu60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 QTLU60 on the supplied OHLCV panel."""
    c = panel['close']
    q = c.rolling(window=60, min_periods=60).quantile(0.8)
    return safe_div(q, c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RANK10: formula = \\mathrm{ts\\_rank}(\\mathrm{close}, 10)."""


__alpha_meta_rank10 = {
    'id': 'qlib158_rank10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_rank}(\\\\mathrm{close}, 10)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_rank10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RANK10 on the supplied OHLCV panel."""
    c = panel['close']
    return ts_rank(c, 10)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RANK20: formula = \\mathrm{ts\\_rank}(\\mathrm{close}, 20)."""


__alpha_meta_rank20 = {
    'id': 'qlib158_rank20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_rank}(\\\\mathrm{close}, 20)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_rank20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RANK20 on the supplied OHLCV panel."""
    c = panel['close']
    return ts_rank(c, 20)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RANK30: formula = \\mathrm{ts\\_rank}(\\mathrm{close}, 30)."""


__alpha_meta_rank30 = {
    'id': 'qlib158_rank30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_rank}(\\\\mathrm{close}, 30)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_rank30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RANK30 on the supplied OHLCV panel."""
    c = panel['close']
    return ts_rank(c, 30)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RANK5: formula = \\mathrm{ts\\_rank}(\\mathrm{close}, 5)."""


__alpha_meta_rank5 = {
    'id': 'qlib158_rank5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_rank}(\\\\mathrm{close}, 5)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_rank5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RANK5 on the supplied OHLCV panel."""
    c = panel['close']
    return ts_rank(c, 5)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RANK60: formula = \\mathrm{ts\\_rank}(\\mathrm{close}, 60)."""


__alpha_meta_rank60 = {
    'id': 'qlib158_rank60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_rank}(\\\\mathrm{close}, 60)',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_rank60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RANK60 on the supplied OHLCV panel."""
    c = panel['close']
    return ts_rank(c, 60)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RESI10: formula = (\\mathrm{close} - \\mathrm{ts\\_mean}(\\mathrm{close}, 10)) / \\mathrm{close}."""


__alpha_meta_resi10 = {
    'id': 'qlib158_resi10',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 10)) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_resi10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RESI10 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c - ts_mean(c, 10), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RESI20: formula = (\\mathrm{close} - \\mathrm{ts\\_mean}(\\mathrm{close}, 20)) / \\mathrm{close}."""


__alpha_meta_resi20 = {
    'id': 'qlib158_resi20',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 20)) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_resi20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RESI20 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c - ts_mean(c, 20), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RESI30: formula = (\\mathrm{close} - \\mathrm{ts\\_mean}(\\mathrm{close}, 30)) / \\mathrm{close}."""


__alpha_meta_resi30 = {
    'id': 'qlib158_resi30',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 30)) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_resi30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RESI30 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c - ts_mean(c, 30), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RESI5: formula = (\\mathrm{close} - \\mathrm{ts\\_mean}(\\mathrm{close}, 5)) / \\mathrm{close}."""


__alpha_meta_resi5 = {
    'id': 'qlib158_resi5',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 5)) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_resi5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RESI5 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c - ts_mean(c, 5), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RESI60: formula = (\\mathrm{close} - \\mathrm{ts\\_mean}(\\mathrm{close}, 60)) / \\mathrm{close}."""


__alpha_meta_resi60 = {
    'id': 'qlib158_resi60',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_mean}(\\\\mathrm{close}, 60)) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_resi60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RESI60 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c - ts_mean(c, 60), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 ROC10: formula = \\mathrm{close}_t / \\mathrm{close}_{{t-10}} - 1."""


__alpha_meta_roc10 = {
    'id': 'qlib158_roc10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{close}_t / \\\\mathrm{close}_{{t-10}} - 1',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_roc10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 ROC10 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c, c.shift(10)) - 1.0


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 ROC20: formula = \\mathrm{close}_t / \\mathrm{close}_{{t-20}} - 1."""


__alpha_meta_roc20 = {
    'id': 'qlib158_roc20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{close}_t / \\\\mathrm{close}_{{t-20}} - 1',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_roc20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 ROC20 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c, c.shift(20)) - 1.0


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 ROC30: formula = \\mathrm{close}_t / \\mathrm{close}_{{t-30}} - 1."""


__alpha_meta_roc30 = {
    'id': 'qlib158_roc30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{close}_t / \\\\mathrm{close}_{{t-30}} - 1',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_roc30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 ROC30 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c, c.shift(30)) - 1.0


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 ROC5: formula = \\mathrm{close}_t / \\mathrm{close}_{{t-5}} - 1."""


__alpha_meta_roc5 = {
    'id': 'qlib158_roc5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{close}_t / \\\\mathrm{close}_{{t-5}} - 1',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_roc5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 ROC5 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c, c.shift(5)) - 1.0


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 ROC60: formula = \\mathrm{close}_t / \\mathrm{close}_{{t-60}} - 1."""


__alpha_meta_roc60 = {
    'id': 'qlib158_roc60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{close}_t / \\\\mathrm{close}_{{t-60}} - 1',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_roc60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 ROC60 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(c, c.shift(60)) - 1.0


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSQR10: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, t, 10)^2."""


__alpha_meta_rsqr10 = {
    'id': 'qlib158_rsqr10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, t, 10)^2',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_rsqr10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSQR10 on the supplied OHLCV panel."""
    c = panel['close']
    t_arr = np.arange(len(c.index), dtype=np.float64)
    t_df = pd.DataFrame(np.broadcast_to(t_arr[:, None], c.shape).copy(), index=c.index, columns=c.columns)
    corr = ts_corr(c, t_df, 10)
    return corr * corr


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSQR20: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, t, 20)^2."""


__alpha_meta_rsqr20 = {
    'id': 'qlib158_rsqr20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, t, 20)^2',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_rsqr20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSQR20 on the supplied OHLCV panel."""
    c = panel['close']
    t_arr = np.arange(len(c.index), dtype=np.float64)
    t_df = pd.DataFrame(np.broadcast_to(t_arr[:, None], c.shape).copy(), index=c.index, columns=c.columns)
    corr = ts_corr(c, t_df, 20)
    return corr * corr


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSQR30: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, t, 30)^2."""


__alpha_meta_rsqr30 = {
    'id': 'qlib158_rsqr30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, t, 30)^2',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_rsqr30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSQR30 on the supplied OHLCV panel."""
    c = panel['close']
    t_arr = np.arange(len(c.index), dtype=np.float64)
    t_df = pd.DataFrame(np.broadcast_to(t_arr[:, None], c.shape).copy(), index=c.index, columns=c.columns)
    corr = ts_corr(c, t_df, 30)
    return corr * corr


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSQR5: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, t, 5)^2."""


__alpha_meta_rsqr5 = {
    'id': 'qlib158_rsqr5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, t, 5)^2',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_rsqr5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSQR5 on the supplied OHLCV panel."""
    c = panel['close']
    t_arr = np.arange(len(c.index), dtype=np.float64)
    t_df = pd.DataFrame(np.broadcast_to(t_arr[:, None], c.shape).copy(), index=c.index, columns=c.columns)
    corr = ts_corr(c, t_df, 5)
    return corr * corr


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSQR60: formula = \\mathrm{ts\\_corr}(\\mathrm{close}, t, 60)^2."""


__alpha_meta_rsqr60 = {
    'id': 'qlib158_rsqr60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_corr}(\\\\mathrm{close}, t, 60)^2',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_rsqr60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSQR60 on the supplied OHLCV panel."""
    c = panel['close']
    t_arr = np.arange(len(c.index), dtype=np.float64)
    t_df = pd.DataFrame(np.broadcast_to(t_arr[:, None], c.shape).copy(), index=c.index, columns=c.columns)
    corr = ts_corr(c, t_df, 60)
    return corr * corr


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSV10: formula = (\\mathrm{close} - \\mathrm{ts\\_min}(\\mathrm{low}, 10)) / (\\mathrm{ts\\_max}(\\mathrm{high}, 10) - \\mathrm{ts\\_min}(\\mathrm{low}, 10))."""


__alpha_meta_rsv10 = {
    'id': 'qlib158_rsv10',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 10)) / (\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 10) - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 10))',
    'columns_required': ['high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_rsv10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSV10 on the supplied OHLCV panel."""
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    hh = ts_max(h, 10)
    ll = ts_min(lo, 10)
    return safe_div(c - ll, hh - ll)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSV20: formula = (\\mathrm{close} - \\mathrm{ts\\_min}(\\mathrm{low}, 20)) / (\\mathrm{ts\\_max}(\\mathrm{high}, 20) - \\mathrm{ts\\_min}(\\mathrm{low}, 20))."""


__alpha_meta_rsv20 = {
    'id': 'qlib158_rsv20',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 20)) / (\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 20) - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 20))',
    'columns_required': ['high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_rsv20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSV20 on the supplied OHLCV panel."""
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    hh = ts_max(h, 20)
    ll = ts_min(lo, 20)
    return safe_div(c - ll, hh - ll)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSV30: formula = (\\mathrm{close} - \\mathrm{ts\\_min}(\\mathrm{low}, 30)) / (\\mathrm{ts\\_max}(\\mathrm{high}, 30) - \\mathrm{ts\\_min}(\\mathrm{low}, 30))."""


__alpha_meta_rsv30 = {
    'id': 'qlib158_rsv30',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 30)) / (\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 30) - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 30))',
    'columns_required': ['high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_rsv30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSV30 on the supplied OHLCV panel."""
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    hh = ts_max(h, 30)
    ll = ts_min(lo, 30)
    return safe_div(c - ll, hh - ll)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSV5: formula = (\\mathrm{close} - \\mathrm{ts\\_min}(\\mathrm{low}, 5)) / (\\mathrm{ts\\_max}(\\mathrm{high}, 5) - \\mathrm{ts\\_min}(\\mathrm{low}, 5))."""


__alpha_meta_rsv5 = {
    'id': 'qlib158_rsv5',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 5)) / (\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 5) - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 5))',
    'columns_required': ['high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_rsv5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSV5 on the supplied OHLCV panel."""
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    hh = ts_max(h, 5)
    ll = ts_min(lo, 5)
    return safe_div(c - ll, hh - ll)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 RSV60: formula = (\\mathrm{close} - \\mathrm{ts\\_min}(\\mathrm{low}, 60)) / (\\mathrm{ts\\_max}(\\mathrm{high}, 60) - \\mathrm{ts\\_min}(\\mathrm{low}, 60))."""


__alpha_meta_rsv60 = {
    'id': 'qlib158_rsv60',
    'theme': ['momentum'],
    'formula_latex': '(\\\\mathrm{close} - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 60)) / (\\\\mathrm{ts\\\\_max}(\\\\mathrm{high}, 60) - \\\\mathrm{ts\\\\_min}(\\\\mathrm{low}, 60))',
    'columns_required': ['high', 'low', 'close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_rsv60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 RSV60 on the supplied OHLCV panel."""
    c = panel['close']
    h = panel['high']
    lo = panel['low']
    hh = ts_max(h, 60)
    ll = ts_min(lo, 60)
    return safe_div(c - ll, hh - ll)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 STD10: formula = \\mathrm{ts\\_std}(\\mathrm{close}, 10) / \\mathrm{close}."""


__alpha_meta_std10 = {
    'id': 'qlib158_std10',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{close}, 10) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_std10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 STD10 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_std(c, 10), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 STD20: formula = \\mathrm{ts\\_std}(\\mathrm{close}, 20) / \\mathrm{close}."""


__alpha_meta_std20 = {
    'id': 'qlib158_std20',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{close}, 20) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_std20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 STD20 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_std(c, 20), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 STD30: formula = \\mathrm{ts\\_std}(\\mathrm{close}, 30) / \\mathrm{close}."""


__alpha_meta_std30 = {
    'id': 'qlib158_std30',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{close}, 30) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_std30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 STD30 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_std(c, 30), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 STD5: formula = \\mathrm{ts\\_std}(\\mathrm{close}, 5) / \\mathrm{close}."""


__alpha_meta_std5 = {
    'id': 'qlib158_std5',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{close}, 5) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_std5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 STD5 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_std(c, 5), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 STD60: formula = \\mathrm{ts\\_std}(\\mathrm{close}, 60) / \\mathrm{close}."""


__alpha_meta_std60 = {
    'id': 'qlib158_std60',
    'theme': ['momentum'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{close}, 60) / \\\\mathrm{close}',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_std60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 STD60 on the supplied OHLCV panel."""
    c = panel['close']
    return safe_div(ts_std(c, 60), c)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMD10: formula = \\mathrm{SUMP}_w - \\mathrm{SUMN}_w."""


__alpha_meta_sumd10 = {
    'id': 'qlib158_sumd10',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{SUMP}_w - \\\\mathrm{SUMN}_w',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_sumd10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMD10 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=10, min_periods=10).sum()
    num_n = neg.rolling(window=10, min_periods=10).sum()
    den = absd.rolling(window=10, min_periods=10).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMD20: formula = \\mathrm{SUMP}_w - \\mathrm{SUMN}_w."""


__alpha_meta_sumd20 = {
    'id': 'qlib158_sumd20',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{SUMP}_w - \\\\mathrm{SUMN}_w',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_sumd20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMD20 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=20, min_periods=20).sum()
    num_n = neg.rolling(window=20, min_periods=20).sum()
    den = absd.rolling(window=20, min_periods=20).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMD30: formula = \\mathrm{SUMP}_w - \\mathrm{SUMN}_w."""


__alpha_meta_sumd30 = {
    'id': 'qlib158_sumd30',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{SUMP}_w - \\\\mathrm{SUMN}_w',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_sumd30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMD30 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=30, min_periods=30).sum()
    num_n = neg.rolling(window=30, min_periods=30).sum()
    den = absd.rolling(window=30, min_periods=30).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMD5: formula = \\mathrm{SUMP}_w - \\mathrm{SUMN}_w."""


__alpha_meta_sumd5 = {
    'id': 'qlib158_sumd5',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{SUMP}_w - \\\\mathrm{SUMN}_w',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_sumd5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMD5 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=5, min_periods=5).sum()
    num_n = neg.rolling(window=5, min_periods=5).sum()
    den = absd.rolling(window=5, min_periods=5).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMD60: formula = \\mathrm{SUMP}_w - \\mathrm{SUMN}_w."""


__alpha_meta_sumd60 = {
    'id': 'qlib158_sumd60',
    'theme': ['reversal'],
    'formula_latex': '\\\\mathrm{SUMP}_w - \\\\mathrm{SUMN}_w',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_sumd60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMD60 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=60, min_periods=60).sum()
    num_n = neg.rolling(window=60, min_periods=60).sum()
    den = absd.rolling(window=60, min_periods=60).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMN10: formula = \\sum \\max(-\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sumn10 = {
    'id': 'qlib158_sumn10',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_sumn10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMN10 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=10, min_periods=10).sum()
    den = absd.rolling(window=10, min_periods=10).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMN20: formula = \\sum \\max(-\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sumn20 = {
    'id': 'qlib158_sumn20',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_sumn20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMN20 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=20, min_periods=20).sum()
    den = absd.rolling(window=20, min_periods=20).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMN30: formula = \\sum \\max(-\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sumn30 = {
    'id': 'qlib158_sumn30',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_sumn30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMN30 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=30, min_periods=30).sum()
    den = absd.rolling(window=30, min_periods=30).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMN5: formula = \\sum \\max(-\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sumn5 = {
    'id': 'qlib158_sumn5',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_sumn5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMN5 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=5, min_periods=5).sum()
    den = absd.rolling(window=5, min_periods=5).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMN60: formula = \\sum \\max(-\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sumn60 = {
    'id': 'qlib158_sumn60',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_sumn60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMN60 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=60, min_periods=60).sum()
    den = absd.rolling(window=60, min_periods=60).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMP10: formula = \\sum \\max(\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sump10 = {
    'id': 'qlib158_sump10',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_sump10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMP10 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=10, min_periods=10).sum()
    den = absd.rolling(window=10, min_periods=10).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMP20: formula = \\sum \\max(\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sump20 = {
    'id': 'qlib158_sump20',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_sump20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMP20 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=20, min_periods=20).sum()
    den = absd.rolling(window=20, min_periods=20).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMP30: formula = \\sum \\max(\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sump30 = {
    'id': 'qlib158_sump30',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_sump30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMP30 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=30, min_periods=30).sum()
    den = absd.rolling(window=30, min_periods=30).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMP5: formula = \\sum \\max(\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sump5 = {
    'id': 'qlib158_sump5',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_sump5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMP5 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=5, min_periods=5).sum()
    den = absd.rolling(window=5, min_periods=5).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 SUMP60: formula = \\sum \\max(\\Delta\\mathrm{close}, 0) / \\sum |\\Delta\\mathrm{close}|."""


__alpha_meta_sump60 = {
    'id': 'qlib158_sump60',
    'theme': ['reversal'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta\\\\mathrm{close}, 0) / \\\\sum |\\\\Delta\\\\mathrm{close}|',
    'columns_required': ['close'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_sump60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 SUMP60 on the supplied OHLCV panel."""
    c = panel['close']
    diff = c - c.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=60, min_periods=60).sum()
    den = absd.rolling(window=60, min_periods=60).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VMA10: formula = \\mathrm{ts\\_mean}(\\mathrm{volume}, 10) / \\mathrm{volume}."""


__alpha_meta_vma10 = {
    'id': 'qlib158_vma10',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{volume}, 10) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_vma10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VMA10 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_mean(v, 10), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VMA20: formula = \\mathrm{ts\\_mean}(\\mathrm{volume}, 20) / \\mathrm{volume}."""


__alpha_meta_vma20 = {
    'id': 'qlib158_vma20',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{volume}, 20) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_vma20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VMA20 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_mean(v, 20), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VMA30: formula = \\mathrm{ts\\_mean}(\\mathrm{volume}, 30) / \\mathrm{volume}."""


__alpha_meta_vma30 = {
    'id': 'qlib158_vma30',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{volume}, 30) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_vma30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VMA30 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_mean(v, 30), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VMA5: formula = \\mathrm{ts\\_mean}(\\mathrm{volume}, 5) / \\mathrm{volume}."""


__alpha_meta_vma5 = {
    'id': 'qlib158_vma5',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{volume}, 5) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_vma5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VMA5 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_mean(v, 5), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VMA60: formula = \\mathrm{ts\\_mean}(\\mathrm{volume}, 60) / \\mathrm{volume}."""


__alpha_meta_vma60 = {
    'id': 'qlib158_vma60',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_mean}(\\\\mathrm{volume}, 60) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_vma60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VMA60 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_mean(v, 60), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSTD10: formula = \\mathrm{ts\\_std}(\\mathrm{volume}, 10) / \\mathrm{volume}."""


__alpha_meta_vstd10 = {
    'id': 'qlib158_vstd10',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{volume}, 10) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_vstd10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSTD10 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_std(v, 10), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSTD20: formula = \\mathrm{ts\\_std}(\\mathrm{volume}, 20) / \\mathrm{volume}."""


__alpha_meta_vstd20 = {
    'id': 'qlib158_vstd20',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{volume}, 20) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_vstd20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSTD20 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_std(v, 20), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSTD30: formula = \\mathrm{ts\\_std}(\\mathrm{volume}, 30) / \\mathrm{volume}."""


__alpha_meta_vstd30 = {
    'id': 'qlib158_vstd30',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{volume}, 30) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_vstd30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSTD30 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_std(v, 30), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSTD5: formula = \\mathrm{ts\\_std}(\\mathrm{volume}, 5) / \\mathrm{volume}."""


__alpha_meta_vstd5 = {
    'id': 'qlib158_vstd5',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{volume}, 5) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_vstd5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSTD5 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_std(v, 5), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSTD60: formula = \\mathrm{ts\\_std}(\\mathrm{volume}, 60) / \\mathrm{volume}."""


__alpha_meta_vstd60 = {
    'id': 'qlib158_vstd60',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{volume}, 60) / \\\\mathrm{volume}',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_vstd60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSTD60 on the supplied OHLCV panel."""
    v = panel['volume']
    return safe_div(ts_std(v, 60), v + 1e-12)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMD10: formula = \\mathrm{VSUMP}_w - \\mathrm{VSUMN}_w."""


__alpha_meta_vsumd10 = {
    'id': 'qlib158_vsumd10',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{VSUMP}_w - \\\\mathrm{VSUMN}_w',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_vsumd10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMD10 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=10, min_periods=10).sum()
    num_n = neg.rolling(window=10, min_periods=10).sum()
    den = absd.rolling(window=10, min_periods=10).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMD20: formula = \\mathrm{VSUMP}_w - \\mathrm{VSUMN}_w."""


__alpha_meta_vsumd20 = {
    'id': 'qlib158_vsumd20',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{VSUMP}_w - \\\\mathrm{VSUMN}_w',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_vsumd20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMD20 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=20, min_periods=20).sum()
    num_n = neg.rolling(window=20, min_periods=20).sum()
    den = absd.rolling(window=20, min_periods=20).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMD30: formula = \\mathrm{VSUMP}_w - \\mathrm{VSUMN}_w."""


__alpha_meta_vsumd30 = {
    'id': 'qlib158_vsumd30',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{VSUMP}_w - \\\\mathrm{VSUMN}_w',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_vsumd30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMD30 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=30, min_periods=30).sum()
    num_n = neg.rolling(window=30, min_periods=30).sum()
    den = absd.rolling(window=30, min_periods=30).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMD5: formula = \\mathrm{VSUMP}_w - \\mathrm{VSUMN}_w."""


__alpha_meta_vsumd5 = {
    'id': 'qlib158_vsumd5',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{VSUMP}_w - \\\\mathrm{VSUMN}_w',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_vsumd5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMD5 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=5, min_periods=5).sum()
    num_n = neg.rolling(window=5, min_periods=5).sum()
    den = absd.rolling(window=5, min_periods=5).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMD60: formula = \\mathrm{VSUMP}_w - \\mathrm{VSUMN}_w."""


__alpha_meta_vsumd60 = {
    'id': 'qlib158_vsumd60',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{VSUMP}_w - \\\\mathrm{VSUMN}_w',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_vsumd60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMD60 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num_p = pos.rolling(window=60, min_periods=60).sum()
    num_n = neg.rolling(window=60, min_periods=60).sum()
    den = absd.rolling(window=60, min_periods=60).sum()
    return safe_div(num_p - num_n, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMN10: formula = \\sum \\max(-\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsumn10 = {
    'id': 'qlib158_vsumn10',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_vsumn10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMN10 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=10, min_periods=10).sum()
    den = absd.rolling(window=10, min_periods=10).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMN20: formula = \\sum \\max(-\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsumn20 = {
    'id': 'qlib158_vsumn20',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_vsumn20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMN20 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=20, min_periods=20).sum()
    den = absd.rolling(window=20, min_periods=20).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMN30: formula = \\sum \\max(-\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsumn30 = {
    'id': 'qlib158_vsumn30',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_vsumn30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMN30 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=30, min_periods=30).sum()
    den = absd.rolling(window=30, min_periods=30).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMN5: formula = \\sum \\max(-\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsumn5 = {
    'id': 'qlib158_vsumn5',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_vsumn5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMN5 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=5, min_periods=5).sum()
    den = absd.rolling(window=5, min_periods=5).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMN60: formula = \\sum \\max(-\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsumn60 = {
    'id': 'qlib158_vsumn60',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(-\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_vsumn60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMN60 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    neg = (-diff).where(diff < 0, 0.0)
    absd = diff.abs()
    num = neg.rolling(window=60, min_periods=60).sum()
    den = absd.rolling(window=60, min_periods=60).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMP10: formula = \\sum \\max(\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsump10 = {
    'id': 'qlib158_vsump10',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_vsump10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMP10 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=10, min_periods=10).sum()
    den = absd.rolling(window=10, min_periods=10).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMP20: formula = \\sum \\max(\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsump20 = {
    'id': 'qlib158_vsump20',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_vsump20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMP20 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=20, min_periods=20).sum()
    den = absd.rolling(window=20, min_periods=20).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMP30: formula = \\sum \\max(\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsump30 = {
    'id': 'qlib158_vsump30',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_vsump30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMP30 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=30, min_periods=30).sum()
    den = absd.rolling(window=30, min_periods=30).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMP5: formula = \\sum \\max(\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsump5 = {
    'id': 'qlib158_vsump5',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_vsump5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMP5 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=5, min_periods=5).sum()
    den = absd.rolling(window=5, min_periods=5).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 VSUMP60: formula = \\sum \\max(\\Delta v, 0) / \\sum |\\Delta v|."""


__alpha_meta_vsump60 = {
    'id': 'qlib158_vsump60',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\sum \\\\max(\\\\Delta v, 0) / \\\\sum |\\\\Delta v|',
    'columns_required': ['volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_vsump60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 VSUMP60 on the supplied OHLCV panel."""
    v = panel['volume']
    diff = v - v.shift(1)
    pos = diff.where(diff > 0, 0.0)
    absd = diff.abs()
    num = pos.rolling(window=60, min_periods=60).sum()
    den = absd.rolling(window=60, min_periods=60).sum()
    return safe_div(num, den)


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 WVMA10: formula = \\mathrm{ts\\_std}(\\mathrm{ret}\\cdot v, 10) / \\mathrm{ts\\_mean}(|\\mathrm{ret}|\\cdot v, 10)."""


__alpha_meta_wvma10 = {
    'id': 'qlib158_wvma10',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{ret}\\\\cdot v, 10) / \\\\mathrm{ts\\\\_mean}(|\\\\mathrm{ret}|\\\\cdot v, 10)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 10,
    'min_warmup_bars': 10,
}


def compute_wvma10(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 WVMA10 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    ret = safe_div(c, c.shift(1)) - 1.0
    rv = ret * v
    arv = ret.abs() * v
    return safe_div(ts_std(rv, 10), ts_mean(arv, 10))


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 WVMA20: formula = \\mathrm{ts\\_std}(\\mathrm{ret}\\cdot v, 20) / \\mathrm{ts\\_mean}(|\\mathrm{ret}|\\cdot v, 20)."""


__alpha_meta_wvma20 = {
    'id': 'qlib158_wvma20',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{ret}\\\\cdot v, 20) / \\\\mathrm{ts\\\\_mean}(|\\\\mathrm{ret}|\\\\cdot v, 20)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 20,
    'min_warmup_bars': 20,
}


def compute_wvma20(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 WVMA20 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    ret = safe_div(c, c.shift(1)) - 1.0
    rv = ret * v
    arv = ret.abs() * v
    return safe_div(ts_std(rv, 20), ts_mean(arv, 20))


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 WVMA30: formula = \\mathrm{ts\\_std}(\\mathrm{ret}\\cdot v, 30) / \\mathrm{ts\\_mean}(|\\mathrm{ret}|\\cdot v, 30)."""


__alpha_meta_wvma30 = {
    'id': 'qlib158_wvma30',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{ret}\\\\cdot v, 30) / \\\\mathrm{ts\\\\_mean}(|\\\\mathrm{ret}|\\\\cdot v, 30)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 30,
    'min_warmup_bars': 30,
}


def compute_wvma30(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 WVMA30 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    ret = safe_div(c, c.shift(1)) - 1.0
    rv = ret * v
    arv = ret.abs() * v
    return safe_div(ts_std(rv, 30), ts_mean(arv, 30))


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 WVMA5: formula = \\mathrm{ts\\_std}(\\mathrm{ret}\\cdot v, 5) / \\mathrm{ts\\_mean}(|\\mathrm{ret}|\\cdot v, 5)."""


__alpha_meta_wvma5 = {
    'id': 'qlib158_wvma5',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{ret}\\\\cdot v, 5) / \\\\mathrm{ts\\\\_mean}(|\\\\mathrm{ret}|\\\\cdot v, 5)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 5,
    'min_warmup_bars': 5,
}


def compute_wvma5(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 WVMA5 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    ret = safe_div(c, c.shift(1)) - 1.0
    rv = ret * v
    arv = ret.abs() * v
    return safe_div(ts_std(rv, 5), ts_mean(arv, 5))


# Adapted from microsoft/qlib@d5379c520f66a39953bad76234a7019a72796fd0:qlib/contrib/data/handler.py
# (Apache-2.0). Copyright (c) Microsoft Corporation.
"""qlib158 WVMA60: formula = \\mathrm{ts\\_std}(\\mathrm{ret}\\cdot v, 60) / \\mathrm{ts\\_mean}(|\\mathrm{ret}|\\cdot v, 60)."""


__alpha_meta_wvma60 = {
    'id': 'qlib158_wvma60',
    'theme': ['volume', 'volatility'],
    'formula_latex': '\\\\mathrm{ts\\\\_std}(\\\\mathrm{ret}\\\\cdot v, 60) / \\\\mathrm{ts\\\\_mean}(|\\\\mathrm{ret}|\\\\cdot v, 60)',
    'columns_required': ['close', 'volume'],
    'universe': ['equity_us', 'equity_cn', 'equity_hk'],
    'frequency': ['1d'],
    'decay_horizon': 60,
    'min_warmup_bars': 60,
}


def compute_wvma60(panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return qlib158 WVMA60 on the supplied OHLCV panel."""
    c = panel['close']
    v = panel['volume']
    ret = safe_div(c, c.shift(1)) - 1.0
    rv = ret * v
    arv = ret.abs() * v
    return safe_div(ts_std(rv, 60), ts_mean(arv, 60))

def get_all_qlib158_factors() -> list:
    """Return list of (meta_dict, compute_fn) tuples for all Qlib 158 Alpha Factors factors."""
    return [
        (__alpha_meta_beta10, compute_beta10),
        (__alpha_meta_beta20, compute_beta20),
        (__alpha_meta_beta30, compute_beta30),
        (__alpha_meta_beta5, compute_beta5),
        (__alpha_meta_beta60, compute_beta60),
        (__alpha_meta_cntd10, compute_cntd10),
        (__alpha_meta_cntd20, compute_cntd20),
        (__alpha_meta_cntd30, compute_cntd30),
        (__alpha_meta_cntd5, compute_cntd5),
        (__alpha_meta_cntd60, compute_cntd60),
        (__alpha_meta_cntn10, compute_cntn10),
        (__alpha_meta_cntn20, compute_cntn20),
        (__alpha_meta_cntn30, compute_cntn30),
        (__alpha_meta_cntn5, compute_cntn5),
        (__alpha_meta_cntn60, compute_cntn60),
        (__alpha_meta_cntp10, compute_cntp10),
        (__alpha_meta_cntp20, compute_cntp20),
        (__alpha_meta_cntp30, compute_cntp30),
        (__alpha_meta_cntp5, compute_cntp5),
        (__alpha_meta_cntp60, compute_cntp60),
        (__alpha_meta_cord10, compute_cord10),
        (__alpha_meta_cord20, compute_cord20),
        (__alpha_meta_cord30, compute_cord30),
        (__alpha_meta_cord5, compute_cord5),
        (__alpha_meta_cord60, compute_cord60),
        (__alpha_meta_corr10, compute_corr10),
        (__alpha_meta_corr20, compute_corr20),
        (__alpha_meta_corr30, compute_corr30),
        (__alpha_meta_corr5, compute_corr5),
        (__alpha_meta_corr60, compute_corr60),
        (__alpha_meta_imax10, compute_imax10),
        (__alpha_meta_imax20, compute_imax20),
        (__alpha_meta_imax30, compute_imax30),
        (__alpha_meta_imax5, compute_imax5),
        (__alpha_meta_imax60, compute_imax60),
        (__alpha_meta_imin10, compute_imin10),
        (__alpha_meta_imin20, compute_imin20),
        (__alpha_meta_imin30, compute_imin30),
        (__alpha_meta_imin5, compute_imin5),
        (__alpha_meta_imin60, compute_imin60),
        (__alpha_meta_imxd10, compute_imxd10),
        (__alpha_meta_imxd20, compute_imxd20),
        (__alpha_meta_imxd30, compute_imxd30),
        (__alpha_meta_imxd5, compute_imxd5),
        (__alpha_meta_imxd60, compute_imxd60),
        (__alpha_meta_klen, compute_klen),
        (__alpha_meta_klow, compute_klow),
        (__alpha_meta_klow2, compute_klow2),
        (__alpha_meta_kmid, compute_kmid),
        (__alpha_meta_kmid2, compute_kmid2),
        (__alpha_meta_ksft, compute_ksft),
        (__alpha_meta_ksft2, compute_ksft2),
        (__alpha_meta_kup, compute_kup),
        (__alpha_meta_kup2, compute_kup2),
        (__alpha_meta_ma10, compute_ma10),
        (__alpha_meta_ma20, compute_ma20),
        (__alpha_meta_ma30, compute_ma30),
        (__alpha_meta_ma5, compute_ma5),
        (__alpha_meta_ma60, compute_ma60),
        (__alpha_meta_max10, compute_max10),
        (__alpha_meta_max20, compute_max20),
        (__alpha_meta_max30, compute_max30),
        (__alpha_meta_max5, compute_max5),
        (__alpha_meta_max60, compute_max60),
        (__alpha_meta_min10, compute_min10),
        (__alpha_meta_min20, compute_min20),
        (__alpha_meta_min30, compute_min30),
        (__alpha_meta_min5, compute_min5),
        (__alpha_meta_min60, compute_min60),
        (__alpha_meta_qtld10, compute_qtld10),
        (__alpha_meta_qtld20, compute_qtld20),
        (__alpha_meta_qtld30, compute_qtld30),
        (__alpha_meta_qtld5, compute_qtld5),
        (__alpha_meta_qtld60, compute_qtld60),
        (__alpha_meta_qtlu10, compute_qtlu10),
        (__alpha_meta_qtlu20, compute_qtlu20),
        (__alpha_meta_qtlu30, compute_qtlu30),
        (__alpha_meta_qtlu5, compute_qtlu5),
        (__alpha_meta_qtlu60, compute_qtlu60),
        (__alpha_meta_rank10, compute_rank10),
        (__alpha_meta_rank20, compute_rank20),
        (__alpha_meta_rank30, compute_rank30),
        (__alpha_meta_rank5, compute_rank5),
        (__alpha_meta_rank60, compute_rank60),
        (__alpha_meta_resi10, compute_resi10),
        (__alpha_meta_resi20, compute_resi20),
        (__alpha_meta_resi30, compute_resi30),
        (__alpha_meta_resi5, compute_resi5),
        (__alpha_meta_resi60, compute_resi60),
        (__alpha_meta_roc10, compute_roc10),
        (__alpha_meta_roc20, compute_roc20),
        (__alpha_meta_roc30, compute_roc30),
        (__alpha_meta_roc5, compute_roc5),
        (__alpha_meta_roc60, compute_roc60),
        (__alpha_meta_rsqr10, compute_rsqr10),
        (__alpha_meta_rsqr20, compute_rsqr20),
        (__alpha_meta_rsqr30, compute_rsqr30),
        (__alpha_meta_rsqr5, compute_rsqr5),
        (__alpha_meta_rsqr60, compute_rsqr60),
        (__alpha_meta_rsv10, compute_rsv10),
        (__alpha_meta_rsv20, compute_rsv20),
        (__alpha_meta_rsv30, compute_rsv30),
        (__alpha_meta_rsv5, compute_rsv5),
        (__alpha_meta_rsv60, compute_rsv60),
        (__alpha_meta_std10, compute_std10),
        (__alpha_meta_std20, compute_std20),
        (__alpha_meta_std30, compute_std30),
        (__alpha_meta_std5, compute_std5),
        (__alpha_meta_std60, compute_std60),
        (__alpha_meta_sumd10, compute_sumd10),
        (__alpha_meta_sumd20, compute_sumd20),
        (__alpha_meta_sumd30, compute_sumd30),
        (__alpha_meta_sumd5, compute_sumd5),
        (__alpha_meta_sumd60, compute_sumd60),
        (__alpha_meta_sumn10, compute_sumn10),
        (__alpha_meta_sumn20, compute_sumn20),
        (__alpha_meta_sumn30, compute_sumn30),
        (__alpha_meta_sumn5, compute_sumn5),
        (__alpha_meta_sumn60, compute_sumn60),
        (__alpha_meta_sump10, compute_sump10),
        (__alpha_meta_sump20, compute_sump20),
        (__alpha_meta_sump30, compute_sump30),
        (__alpha_meta_sump5, compute_sump5),
        (__alpha_meta_sump60, compute_sump60),
        (__alpha_meta_vma10, compute_vma10),
        (__alpha_meta_vma20, compute_vma20),
        (__alpha_meta_vma30, compute_vma30),
        (__alpha_meta_vma5, compute_vma5),
        (__alpha_meta_vma60, compute_vma60),
        (__alpha_meta_vstd10, compute_vstd10),
        (__alpha_meta_vstd20, compute_vstd20),
        (__alpha_meta_vstd30, compute_vstd30),
        (__alpha_meta_vstd5, compute_vstd5),
        (__alpha_meta_vstd60, compute_vstd60),
        (__alpha_meta_vsumd10, compute_vsumd10),
        (__alpha_meta_vsumd20, compute_vsumd20),
        (__alpha_meta_vsumd30, compute_vsumd30),
        (__alpha_meta_vsumd5, compute_vsumd5),
        (__alpha_meta_vsumd60, compute_vsumd60),
        (__alpha_meta_vsumn10, compute_vsumn10),
        (__alpha_meta_vsumn20, compute_vsumn20),
        (__alpha_meta_vsumn30, compute_vsumn30),
        (__alpha_meta_vsumn5, compute_vsumn5),
        (__alpha_meta_vsumn60, compute_vsumn60),
        (__alpha_meta_vsump10, compute_vsump10),
        (__alpha_meta_vsump20, compute_vsump20),
        (__alpha_meta_vsump30, compute_vsump30),
        (__alpha_meta_vsump5, compute_vsump5),
        (__alpha_meta_vsump60, compute_vsump60),
        (__alpha_meta_wvma10, compute_wvma10),
        (__alpha_meta_wvma20, compute_wvma20),
        (__alpha_meta_wvma30, compute_wvma30),
        (__alpha_meta_wvma5, compute_wvma5),
        (__alpha_meta_wvma60, compute_wvma60),
    ]
