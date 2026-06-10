"""Alpha Factor Library for Quant-Nanggroe-AI.

Provides a comprehensive set of alpha factors extracted from Vibe-Trading (452 factors),
including WorldQuant 101 Alphas, GTJA 191 Alphas, Barra Risk Model factors,
technical factors, and fundamental factors.

Each factor inherits from AlphaFactor base class and implements a pure compute() method
with AST-pure semantics (no external API calls, no randomness, no lookahead bias).

Factor categories:
    - alpha101: WorldQuant 101 Formulaic Alphas (Kakushadze 2015)
    - gtja191: Guotai Junan 191 Alphas (Chinese A-share market)
    - barra: MSCI Barra Risk Model factors
    - technical: Standard technical analysis factors
    - fundamental: Fundamental analysis factors
"""

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    FactorMeta,
    Market,
    decay_linear,
    delay,
    delta,
    rank,
    safe_div,
    scale,
    signed_power,
    ts_argmax,
    ts_argmin,
    ts_corr,
    ts_cov,
    ts_kurtosis,
    ts_max,
    ts_mean,
    ts_median,
    ts_min,
    ts_product,
    ts_rank,
    ts_skewness,
    ts_std,
    ts_sum,
    vwap,
)
from quant_nanggroe.engine.factors.registry import FactorRegistry, FactorCategory, get_default_registry, reset_default_registry
from quant_nanggroe.engine.factors.pipeline import (
    CombineMethod,
    FactorPipeline,
    MissingDataMethod,
    NeutralizationMethod,
    OutlierMethod,
)

__all__ = [
    # Base
    "AlphaFactor",
    "FactorMeta",
    "Market",
    # Operators
    "rank",
    "scale",
    "ts_rank",
    "ts_corr",
    "ts_cov",
    "ts_mean",
    "ts_median",
    "ts_std",
    "ts_sum",
    "ts_product",
    "ts_skewness",
    "ts_kurtosis",
    "ts_max",
    "ts_min",
    "ts_argmax",
    "ts_argmin",
    "delta",
    "delay",
    "decay_linear",
    "signed_power",
    "safe_div",
    "vwap",
    # Registry
    "FactorRegistry",
    "FactorCategory",
    "get_default_registry",
    "reset_default_registry",
    # Pipeline
    "FactorPipeline",
    "CombineMethod",
    "OutlierMethod",
    "MissingDataMethod",
    "NeutralizationMethod",
]
