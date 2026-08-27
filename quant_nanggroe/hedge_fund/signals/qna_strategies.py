"""MUE-X evolved signal providers — dynamic discovery from external/mue_x.

Replaces 760-line hand-coded wrapper list with auto-discovery.
All 992 evolved providers loaded on demand via MueXSignalProvider factory.
"""

import os
import sys as _sys
from pathlib import Path
from typing import Optional

from quant_nanggroe.engine.causal.models import CausalContext
from quant_nanggroe.hedge_fund.signals.core import apply_causal_bias
from quant_nanggroe.hedge_fund.utils.config import log
from quant_nanggroe.hedge_fund.utils.data import get_historical_mt5

_MUE_X_DIR = Path(os.environ.get("MUE_X_STRATEGIES_DIR", str(Path(__file__).resolve().parent.parent.parent / 'external' / 'mue_x' / 'genes' / 'qna_strategies')))

class MueXSignalProvider:
    """Lazy-loading signal provider for a single MUE-X evolved strategy module."""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.strategy_name = f"qna_{module_name}"

    def __call__(self, symbol="EURUSD", ctx: Optional[CausalContext] = None):
        try:
            _sys.path.insert(0, str(_MUE_X_DIR))
            mod = __import__(self.module_name, fromlist=["generate_signal"])
            df = get_historical_mt5(symbol, count=100)
            if df is None or len(df) < 50:
                return {"bias": "neutral", "confidence": 0, "source": self.strategy_name}
            result = mod.generate_signal(df)
            if result is None or len(result) < 2:
                return {"bias": "neutral", "confidence": 0, "source": self.strategy_name}
            last = result.iloc[-1]
            entry = last.get("entry", 0)
            if entry == 1:
                return apply_causal_bias({"bias": "buy", "confidence": 0.55, "source": self.strategy_name}, symbol, ctx=ctx)
            if entry == -1:
                return apply_causal_bias({"bias": "sell", "confidence": 0.55, "source": self.strategy_name}, symbol, ctx=ctx)
        except Exception as e:
            log.debug("MUE-X %s err: %s", self.strategy_name, e)
        return {"bias": "neutral", "confidence": 0, "source": self.strategy_name}


def _discover_muex_providers() -> dict[str, MueXSignalProvider]:
    """Auto-discover all .py files in the MUE-X strategies directory."""
    providers: dict[str, MueXSignalProvider] = {}
    if not _MUE_X_DIR.is_dir():
        log.warning("MUE-X strategies dir not found: %s", _MUE_X_DIR)
        return providers
    for fpath in sorted(_MUE_X_DIR.glob("qna_*_mut_*.py")):
        mod_name = fpath.stem
        providers[mod_name] = MueXSignalProvider(mod_name)
    log.info("Discovered %d MUE-X evolved providers from %s", len(providers), _MUE_X_DIR)
    return providers


MUE_X_PROVIDERS = _discover_muex_providers()
