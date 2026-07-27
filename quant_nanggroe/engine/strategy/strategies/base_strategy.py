"""Legacy shim for BaseStrategy.

Provides a module-level ``BaseStrategy`` alias for backward compatibility.
"""

# Re-export the alias defined in the package ``__init__``.
from quant_nanggroe.engine.strategy.strategies import BaseStrategy  # noqa: F401
