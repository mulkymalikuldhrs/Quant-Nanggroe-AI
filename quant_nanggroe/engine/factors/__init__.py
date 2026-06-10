"""Alpha Factor Library for Quant-Nanggroe-AI.

Provides a comprehensive set of alpha factors ported from Vibe-Trading (452 factors),
including:
- WorldQuant 101 Alphas (alpha101) — 101 factors
- Guotai Junan 191 Alphas (gtja191) — 191 factors
- Qlib 158 Alpha Factors (qlib158) — 154 factors
- Academic Alpha Factors (academic) — 6 factors (Fama-French, Carhart)
- Technical Factors — 9 factors
- Fundamental Factors — 8 factors

Each factor follows the __alpha_meta__ + compute(panel) pattern from Vibe-Trading,
adapted to use Quant-Nanggroe-AI base.py operators. Factors are AST-pure
(no external API calls, no randomness, no lookahead bias).

Usage:
    from quant_nanggroe.engine.factors import FactorRegistry, get_default_registry

    registry = get_default_registry()
    print(registry.health())  # Show loaded factors by zoo/theme

    # List factors by category
    alpha101_ids = registry.list(zoo="alpha101")

    # Compute a factor
    panel = {"close": close_df, "open": open_df, ...}
    result = registry.compute("alpha101_001", panel)
"""

from quant_nanggroe.engine.factors.base import (
    AlphaFactor,
    FactorMeta,
    Market,
    cross_sectional_zscore,
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
    ts_product,
    ts_sum,
    delta,
    decay_linear,
    signed_power,
    safe_div,
    vwap,
)
from quant_nanggroe.engine.factors.registry import (
    FactorHandle,
    FactorRegistry,
    get_default_registry,
    reset_default_registry,
)
from quant_nanggroe.engine.factors.pipeline import FactorPipeline

__all__ = [
    # Base classes and types
    "AlphaFactor",
    "FactorMeta",
    "FactorHandle",
    "Market",
    # Registry
    "FactorRegistry",
    "get_default_registry",
    "reset_default_registry",
    # Pipeline
    "FactorPipeline",
    # Operators
    "cross_sectional_zscore",
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
    "ts_product",
    "ts_sum",
    "delta",
    "decay_linear",
    "signed_power",
    "safe_div",
    "vwap",
]
