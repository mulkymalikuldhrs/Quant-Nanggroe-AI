"""Archive Strategies — Fixed/replacement strategies for production use.

These are corrected versions of strategies that had issues in the main registry.
They are registered with 'archive_' prefix to avoid name conflicts.
"""

from quant_nanggroe.engine.strategies.archive.msnr_fixed import MSNRStrategyFixed
from quant_nanggroe.engine.strategies.archive.smc_fixed import SMCStrategyFixed
from quant_nanggroe.engine.strategies.archive.quarterly_fixed import QuarterlyTheoryStrategyFixed

__all__ = [
    "MSNRStrategyFixed",
    "SMCStrategyFixed",
    "QuarterlyTheoryStrategyFixed",
]