"""Compatibility shim for CryptoSpecificStrategy.

Provides legacy interface expected by older test suite:
- Constructor accepts `params` dict and optional `name`.
- `name` defaults to "CryptoSpecific".
- Exposes `mode`, `entry_threshold`, and other attributes from the underlying
  strategy.
- Implements `required_columns()` and `warmup_period()` methods.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

import pandas as pd

from quant_nanggroe.engine.strategies.base import StrategyParameters
from quant_nanggroe.engine.strategies.crypto_specific import CryptoSpecificStrategy as _BaseCryptoSpecific

class CryptoSpecificStrategy(_BaseCryptoSpecific):
    """Legacy wrapper exposing older API expectations."""

    def __init__(self, name: str = "CryptoSpecific", params: Optional[Dict[str, Any]] = None):
        # The underlying class expects a StrategyParameters instance.
        super().__init__(parameters=StrategyParameters(params or {}))
        # Override name to match legacy tests.
        self.name = name
        # Keep a copy of raw params for compatibility (tests may inspect .params)
        self.params = params or {}

    # Legacy methods expected by tests.
    def required_columns(self):
        mode = getattr(self, "mode", "")
        if mode == "funding_rate_arb":
            return [self.funding_rate_column]
        if mode == "liquidation_cascade":
            return ["close", "volume"]
        if mode == "on_chain":
            return ["exchange_inflow", "exchange_outflow"]
        if mode == "dex_arb":
            return ["dex_price", "cex_price"]
        if mode == "mev_aware":
            return ["solana_tip", "priority_fee"]
        return []

    def warmup_period(self):
        # The strategy needs lookback + 10 rows for signal generation.
        return self.lookback + 10

