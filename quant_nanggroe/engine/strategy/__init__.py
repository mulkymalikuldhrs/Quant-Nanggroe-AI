"""Legacy strategy engine package — most modules removed in path consolidation.

Only ``strategies`` sub-package remains as a backward-compat shim
(``quant_nanggroe.engine.strategy.strategies``). All strategy logic lives
in ``quant_nanggroe.engine.strategies``.
"""

# Backward-compat: anything that was imported from this package before
# cleanup will get the strategies shim.
from . import strategies  # noqa: F401
