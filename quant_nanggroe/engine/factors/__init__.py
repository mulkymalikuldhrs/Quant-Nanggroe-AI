"""Alpha Factor Library for Quant-Nanggroe-AI.

Provides a comprehensive set of alpha factors extracted from Vibe-Trading (452 factors),
including WorldQuant 101 Alphas, GTJA 191 Alphas, technical factors, and fundamental factors.

Each factor inherits from AlphaFactor base class and implements a pure compute() method
with AST-pure semantics (no external API calls, no randomness, no lookahead bias).
"""

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    Market,
    rank,
    scale,
    ts_rank,
    ts_corr,
    ts_cov,
    ts_mean,
    ts_std,
    ts_max,
    ts_min,
    ts_argmax,
    ts_argmin,
    delta,
    decay_linear,
    signed_power,
    safe_div,
    vwap,
)
from quant_nanggroe.engine.factors.registry import FactorRegistry
from quant_nanggroe.engine.factors.pipeline import FactorPipeline

__all__ = [
    "AlphaFactor",
    "Market",
    "FactorRegistry",
    "FactorPipeline",
    "rank",
    "scale",
    "ts_rank",
    "ts_corr",
    "ts_cov",
    "ts_mean",
    "ts_std",
    "ts_max",
    "ts_min",
    "ts_argmax",
    "ts_argmin",
    "delta",
    "decay_linear",
    "signed_power",
    "safe_div",
    "vwap",
]
