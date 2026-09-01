"""Legacy shim — re-exports from canonical core.scoring path.

Preserves backward-compat for `from quant_nanggroe.engine.volatility_scorer import VolatilityScorer`.
Canonical implementation lives in `quant_nanggroe.core.scoring.volatility_scorer`.
"""
from quant_nanggroe.core.scoring.volatility_scorer import *  # noqa: F401,F403
from quant_nanggroe.core.scoring.volatility_scorer import VolatilityScorer  # noqa: F401
