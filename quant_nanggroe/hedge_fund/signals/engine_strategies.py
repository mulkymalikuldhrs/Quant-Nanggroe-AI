"""Engine strategy providers — wraps all @StrategyRegistry.register classes into aggregator-callable providers.

Each registered strategy gets wrapped as EngineStrategyProvider, a callable
matching the aggregator's provider signature: provider(symbol, ctx) -> dict.
Errors per strategy are caught — one failing strategy never crashes the pipeline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from quant_nanggroe.engine.strategies import StrategyRegistry
from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    StrategyParameters,
    StrategySignal,
)

if TYPE_CHECKING:
    from quant_nanggroe.engine.causal.models import CausalContext

log = logging.getLogger("qna.engine_strategies")


class EngineStrategyProvider:
    """Wraps a registered engine Strategy instance into a callable for the aggregator.

    Signature: provider(symbol="EURUSD", ctx=None) -> dict
    Matches the CORE_PROVIDERS convention so the aggregator's ThreadPoolExecutor
    can submit it identically.
    """

    def __init__(self, strategy) -> None:
        self._strategy = strategy
        self._name = strategy.name
        # Aggregator reads __name__ for logging via _provider_name().
        # "strat_" prefix separates engine strategies from external/core providers
        # in the correlation-bucket matcher.
        self.__name__ = f"strat_{self._name}"

    def __call__(
        self, symbol: str = "EURUSD", ctx: Optional["CausalContext"] = None
    ) -> dict:
        try:
            # Lazy imports — these trigger hedge_fund package init which requires
            # MT5 connection. Deferring avoids crashes in test/CI environments
            # where mt5 is not connected.
            from quant_nanggroe.hedge_fund.signals.core import apply_causal_bias
            from quant_nanggroe.hedge_fund.utils.config import log as hf_log
            from quant_nanggroe.hedge_fund.utils.data import get_historical_mt5

            df = get_historical_mt5(symbol, count=100)
            if df is None or len(df) < 30:
                return {"bias": "neutral", "confidence": 0, "source": self.__name__}

            sig: StrategySignal = self._strategy.generate_signal(
                df, symbol=symbol
            )
            if sig.direction == SignalDirection.BUY:
                return apply_causal_bias(
                    {"bias": "buy", "confidence": sig.confidence, "source": self.__name__},
                    symbol,
                    ctx=ctx,
                )
            if sig.direction == SignalDirection.SELL:
                return apply_causal_bias(
                    {
                        "bias": "sell",
                        "confidence": sig.confidence,
                        "source": self.__name__,
                    },
                    symbol,
                    ctx=ctx,
                )
        except Exception as exc:
            log.debug("EngineStrategy '%s' err: %s", self._name, exc)
        return {"bias": "neutral", "confidence": 0, "source": self.__name__}

    def __repr__(self) -> str:
        return f"EngineStrategyProvider({self._name})"


def _discover_engine_strategies() -> list[EngineStrategyProvider]:
    """Instantiate all registered strategies, wrap each as a provider."""
    providers: list[EngineStrategyProvider] = []
    registered = StrategyRegistry.list_strategies()
    for name in registered:
        try:
            # Use a bare StrategyParameters for strategies that accept it;
            # any strategy that raises here is simply skipped.
            instance = StrategyRegistry.create(name)
            if instance is None:
                continue
            providers.append(EngineStrategyProvider(instance))
        except Exception as exc:
            log.debug("EngineStrategy '%s' init failed: %s", name, exc)
    log.info(
        "WIRED %d/%d engine strategy providers", len(providers), len(registered)
    )
    return providers


# Module-level list — imported by registry.py and added to ALL_PROVIDERS.
ENGINE_STRATEGY_PROVIDERS = _discover_engine_strategies()
