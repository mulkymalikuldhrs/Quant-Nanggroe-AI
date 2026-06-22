"""Strategy registry and factory for Quant Nanggroe AI.

Provides a central registry for all strategy implementations and
a factory function for creating strategy instances by name.

All strategies extend BaseStrategy and implement generate_signal(),
required_columns(), and warmup_period().

Usage::

    from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies

    # List available strategies
    names = list_strategies()

    # Create a strategy by name
    strategy = create_strategy("MeanReversion", params={"lookback": 30})

    # Generate a signal
    signal = strategy.generate_signal(data)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.engine.strategy.strategies.mean_reversion import MeanReversionStrategy
from quant_nanggroe.engine.strategy.strategies.momentum import MomentumStrategy
from quant_nanggroe.engine.strategy.strategies.pairs_trading import PairsTradingStrategy
from quant_nanggroe.engine.strategy.strategies.volatility_arbitrage import (
    VolatilityArbitrageStrategy,
    GARCH11,
)
from quant_nanggroe.engine.strategy.strategies.statistical_arbitrage import (
    StatisticalArbitrageStrategy,
)
from quant_nanggroe.engine.strategy.strategies.market_making import MarketMakingStrategy
from quant_nanggroe.engine.strategy.strategies.regime_based import RegimeBasedStrategy
from quant_nanggroe.engine.strategy.strategies.crypto_specific import CryptoSpecificStrategy
from quant_nanggroe.engine.strategy.strategies.smc_strategy import SMCStrategy
from quant_nanggroe.engine.strategy.strategies.ict_strategy import ICTStrategy
from quant_nanggroe.engine.strategy.strategies.support_resistance_strategy import (
    SupportResistanceStrategy,
)
from quant_nanggroe.engine.strategy.strategies.supply_demand_strategy import (
    SupplyDemandStrategy,
)
from quant_nanggroe.engine.strategy.strategies.wyckoff_strategy import WyckoffStrategy
from quant_nanggroe.engine.strategy.strategies.cot_strategy import COTStrategy
from quant_nanggroe.engine.strategy.strategies.fundamental_strategy import FundamentalStrategy


# Strategy class registry: name -> class
_STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "MeanReversion": MeanReversionStrategy,
    "Momentum": MomentumStrategy,
    "PairsTrading": PairsTradingStrategy,
    "VolatilityArbitrage": VolatilityArbitrageStrategy,
    "StatisticalArbitrage": StatisticalArbitrageStrategy,
    "MarketMaking": MarketMakingStrategy,
    "RegimeBased": RegimeBasedStrategy,
    "CryptoSpecific": CryptoSpecificStrategy,
    "SMC": SMCStrategy,
    "ICT": ICTStrategy,
    "S/R": SupportResistanceStrategy,
    "SnD": SupplyDemandStrategy,
    "Wyckoff": WyckoffStrategy,
    "COT": COTStrategy,
    "Fundamental": FundamentalStrategy,
}

# Strategy metadata for discovery
_STRATEGY_METADATA: Dict[str, Dict] = {
    "MeanReversion": {
        "description": "Bollinger Bands + Z-score + Ornstein-Uhlenbeck mean reversion",
        "asset_classes": ["stocks", "forex", "crypto"],
        "timeframes": ["1h", "4h", "1d"],
        "category": "mean_reversion",
    },
    "Momentum": {
        "description": "Time-series / dual / MA crossover / MACD momentum",
        "asset_classes": ["stocks", "forex", "crypto", "futures"],
        "timeframes": ["1h", "4h", "1d", "1w"],
        "category": "momentum",
    },
    "PairsTrading": {
        "description": "Cointegration-based pairs trading with Kalman filter",
        "asset_classes": ["stocks", "crypto"],
        "timeframes": ["1h", "4h", "1d"],
        "category": "pairs_trading",
    },
    "VolatilityArbitrage": {
        "description": "GARCH volatility forecasting + variance risk premium",
        "asset_classes": ["stocks", "futures", "options"],
        "timeframes": ["1d", "1w"],
        "category": "volatility",
    },
    "StatisticalArbitrage": {
        "description": "PCA factor model + residual mean reversion + Kalman filter",
        "asset_classes": ["stocks", "crypto"],
        "timeframes": ["1h", "4h", "1d"],
        "category": "statistical_arbitrage",
    },
    "MarketMaking": {
        "description": "Avellaneda-Stoikov optimal quotes + inventory management",
        "asset_classes": ["crypto", "forex"],
        "timeframes": ["1m", "5m", "15m"],
        "category": "market_making",
    },
    "RegimeBased": {
        "description": "HMM regime detection + strategy switching",
        "asset_classes": ["stocks", "forex", "crypto"],
        "timeframes": ["1h", "4h", "1d"],
        "category": "regime_detection",
    },
    "CryptoSpecific": {
        "description": "Funding rate arb / liquidation cascade / on-chain / DEX arb / MEV",
        "asset_classes": ["crypto"],
        "timeframes": ["5m", "15m", "1h", "4h", "1d"],
        "category": "crypto",
    },
    "SMC": {
        "description": "Smart Money Concept: order blocks, liquidity sweeps, FVG, market structure shifts",
        "asset_classes": ["crypto", "forex", "stocks"],
        "timeframes": ["5m", "15m", "1h", "4h", "1d"],
        "category": "pattern",
    },
    "ICT": {
        "description": "Inner Circle Trader: displacement, FVG, OTE retracement, kill zones, order blocks",
        "asset_classes": ["crypto", "forex", "stocks"],
        "timeframes": ["5m", "15m", "1h", "4h", "1d"],
        "category": "pattern",
    },
    "S/R": {
        "description": "Dynamic Support & Resistance: swing pivots, zone clustering, bounce/breakout detection",
        "asset_classes": ["crypto", "forex", "stocks", "futures"],
        "timeframes": ["15m", "1h", "4h", "1d"],
        "category": "supply_demand",
    },
    "SnD": {
        "description": "Supply & Demand zones: institutional zone detection, strength scoring, zone touches",
        "asset_classes": ["crypto", "forex", "stocks"],
        "timeframes": ["15m", "1h", "4h", "1d"],
        "category": "supply_demand",
    },
    "Wyckoff": {
        "description": "Wyckoff Method: accumulation/distribution phases, SC, AR, ST, Spring, UT detection",
        "asset_classes": ["crypto", "stocks", "futures"],
        "timeframes": ["1h", "4h", "1d", "1w"],
        "category": "wyckoff",
    },
    "COT": {
        "description": "Commitment of Traders: speculator positioning, COT index, commercial divergence, extreme readings",
        "asset_classes": ["futures", "forex"],
        "timeframes": ["1d", "1w"],
        "category": "cot",
    },
    "Fundamental": {
        "description": "Fundamental analysis: economic calendar, macro data, sentiment, central bank policy, event-driven",
        "asset_classes": ["forex", "stocks", "futures", "crypto"],
        "timeframes": ["1h", "4h", "1d", "1w"],
        "category": "fundamental",
    },
}


def create_strategy(
    name: str, params: Optional[Dict] = None
) -> BaseStrategy:
    """Create a strategy instance by name.

    Args:
        name: Strategy name (must be in the registry).
        params: Optional strategy parameters.

    Returns:
        Instantiated BaseStrategy subclass.

    Raises:
        ValueError: If the strategy name is not registered.
    """
    if name not in _STRATEGY_REGISTRY:
        available = ", ".join(sorted(_STRATEGY_REGISTRY.keys()))
        raise ValueError(
            f"Unknown strategy '{name}'. Available: {available}"
        )

    strategy_cls = _STRATEGY_REGISTRY[name]
    return strategy_cls(params=params)


def list_strategies() -> List[str]:
    """List all registered strategy names.

    Returns:
        Sorted list of strategy names.
    """
    return sorted(_STRATEGY_REGISTRY.keys())


def get_strategy_metadata(name: str) -> Dict:
    """Get metadata for a registered strategy.

    Args:
        name: Strategy name.

    Returns:
        Dict with description, asset_classes, timeframes, category.

    Raises:
        ValueError: If the strategy name is not registered.
    """
    if name not in _STRATEGY_METADATA:
        raise ValueError(f"Unknown strategy '{name}'")
    return _STRATEGY_METADATA[name]


def register_strategy(
    name: str,
    strategy_cls: Type[BaseStrategy],
    metadata: Optional[Dict] = None,
) -> None:
    """Register a new strategy class.

    Args:
        name: Strategy name for the registry.
        strategy_cls: Strategy class (must extend BaseStrategy).
        metadata: Optional metadata dict.

    Raises:
        TypeError: If strategy_cls does not extend BaseStrategy.
    """
    if not issubclass(strategy_cls, BaseStrategy):
        raise TypeError(
            f"Strategy class must extend BaseStrategy, got {strategy_cls}"
        )

    _STRATEGY_REGISTRY[name] = strategy_cls
    if metadata:
        _STRATEGY_METADATA[name] = metadata


__all__ = [
    # Base
    "BaseStrategy",
    # Strategies
    "MeanReversionStrategy",
    "MomentumStrategy",
    "PairsTradingStrategy",
    "VolatilityArbitrageStrategy",
    "GARCH11",
    "StatisticalArbitrageStrategy",
    "MarketMakingStrategy",
    "RegimeBasedStrategy",
    "CryptoSpecificStrategy",
    "SMCStrategy",
    "ICTStrategy",
    "SupportResistanceStrategy",
    "SupplyDemandStrategy",
    "WyckoffStrategy",
    "COTStrategy",
    "FundamentalStrategy",
    # Registry functions
    "create_strategy",
    "list_strategies",
    "get_strategy_metadata",
    "register_strategy",
]
