"""Strategy registry and factory for Quant Nanggroe AI.

Provides a central registry for all 16 strategy implementations and
a factory function for creating strategy instances by name.

All strategies extend BaseStrategy and implement generate_signal(),
required_columns(), and warmup_period().

Registered strategies:
  Statistical / Mean-Reversion:
    - MeanReversion       — Z-score / Bollinger / OU mean reversion
    - PairsTrading        — Cointegration-based pairs trading
    - StatisticalArbitrage — PCA factor model residual reversion
    - VolatilityArbitrage — GARCH/EWMA vol-ratio z-score

  Momentum / Trend:
    - Momentum            — TS / dual / MA crossover / MACD
    - TrendFollow         — Dual MA + ADX + trailing ATR

  Market Structure:
    - MarketMaking        — Avellaneda-Stoikov optimal quoting
    - RegimeBased         — HMM regime detection + switching

  Crypto:
    - CryptoSpecific      — Funding arb / cascade / on-chain / DEX arb / MEV

  Price Action:
    - Wyckoff             — Accumulation/distribution phases
    - SupportResistance   — S/R swing points and zone clusters
    - SupplyDemand        — Institutional supply/demand zones
    - SMC                 — Order blocks, liquidity, FVG, market structure
    - ICT                 — Displacement, OTE, FVG, kill zones

  Fundamental / Sentiment:
    - Fundamental         — Economic calendar, macro surprises
    - COT                 — Commitment of Traders extremes

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

from quant_nanggroe.engine.strategy.registry import StrategyRegistry
from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.engine.strategy.strategies.crypto_specific import CryptoSpecificStrategy
from quant_nanggroe.engine.strategy.strategies.market_making import MarketMakingStrategy
from quant_nanggroe.engine.strategy.strategies.mean_reversion import MeanReversionStrategy
from quant_nanggroe.engine.strategy.strategies.momentum import MomentumStrategy
from quant_nanggroe.engine.strategy.strategies.pairs_trading import PairsTradingStrategy
from quant_nanggroe.engine.strategy.strategies.regime_based import RegimeBasedStrategy
from quant_nanggroe.engine.strategy.strategies.statistical_arbitrage import (
    StatisticalArbitrageStrategy,
)
from quant_nanggroe.engine.strategy.strategies.volatility_arbitrage import (
    VolatilityArbitrageStrategy,
)
from quant_nanggroe.engine.strategy.strategies.trend_follow import TrendFollowStrategy
from quant_nanggroe.engine.strategy.strategies.wyckoff_strategy import WyckoffStrategy
from quant_nanggroe.engine.strategy.strategies.support_resistance_strategy import (
    SupportResistanceStrategy,
)
from quant_nanggroe.engine.strategy.strategies.supply_demand_strategy import SupplyDemandStrategy
from quant_nanggroe.engine.strategy.strategies.smc_strategy import SMCStrategy
from quant_nanggroe.engine.strategy.strategies.ict_strategy import ICTStrategy
from quant_nanggroe.engine.strategy.strategies.fundamental_strategy import FundamentalStrategy
from quant_nanggroe.engine.strategy.strategies.cot_strategy import COTStrategy

# Global registry instance for all strategies
STRATEGY_REGISTRY: StrategyRegistry = StrategyRegistry()


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
    "TrendFollow": TrendFollowStrategy,
    "Wyckoff": WyckoffStrategy,
    "SupportResistance": SupportResistanceStrategy,
    "SupplyDemand": SupplyDemandStrategy,
    "SMC": SMCStrategy,
    "ICT": ICTStrategy,
    "Fundamental": FundamentalStrategy,
    "COT": COTStrategy,
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
    "TrendFollow": {
        "description": "Dual MA crossover + ADX trend confirmation + trailing ATR stop",
        "asset_classes": ["stocks", "forex", "crypto", "futures"],
        "timeframes": ["1d", "4h", "1w"],
        "category": "trend_following",
    },
    "Wyckoff": {
        "description": "Wyckoff accumulation/distribution phase detection (PS, SC, AR, ST, spring, upthrust)",
        "asset_classes": ["stocks", "crypto", "futures"],
        "timeframes": ["1h", "4h", "1d"],
        "category": "price_action",
    },
    "SupportResistance": {
        "description": "S/R level detection via swing points, zone clustering, bounce/breakout signals",
        "asset_classes": ["stocks", "forex", "crypto", "futures"],
        "timeframes": ["15m", "1h", "4h", "1d"],
        "category": "price_action",
    },
    "SupplyDemand": {
        "description": "Institutional supply/demand zone detection with strength scoring and volume confirmation",
        "asset_classes": ["stocks", "forex", "crypto", "futures"],
        "timeframes": ["15m", "1h", "4h", "1d"],
        "category": "price_action",
    },
    "SMC": {
        "description": "Smart Money Concepts: order blocks, liquidity sweeps, fair value gaps, market structure",
        "asset_classes": ["stocks", "forex", "crypto"],
        "timeframes": ["15m", "1h", "4h", "1d"],
        "category": "price_action",
    },
    "ICT": {
        "description": "Inner Circle Trader: displacement, FVG, optimal trade entry, order blocks, kill zones",
        "asset_classes": ["forex", "crypto"],
        "timeframes": ["15m", "1h", "4h"],
        "category": "price_action",
    },
    "Fundamental": {
        "description": "Economic calendar events, macro data surprises, central bank policy, sentiment analysis",
        "asset_classes": ["forex", "stocks", "futures"],
        "timeframes": ["1d", "1w"],
        "category": "fundamental",
    },
    "COT": {
        "description": "Commitment of Traders positioning extremes and divergence trading",
        "asset_classes": ["futures"],
        "timeframes": ["1w"],
        "category": "sentiment",
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


# --- auto-register all strategies with the StrategyRegistry ---
for _name, _meta in _STRATEGY_METADATA.items():
    tf = _meta.get("timeframes", [""])
    STRATEGY_REGISTRY.register(
        name=_name,
        description=_meta.get("description", ""),
        asset_classes=_meta.get("asset_classes", []),
        timeframe=tf[0] if tf else "",
        status="active",
    )

__all__ = [
    # Base
    "BaseStrategy",
    # Strategies
    "MeanReversionStrategy",
    "MomentumStrategy",
    "PairsTradingStrategy",
    "VolatilityArbitrageStrategy",
    "StatisticalArbitrageStrategy",
    "MarketMakingStrategy",
    "RegimeBasedStrategy",
    "CryptoSpecificStrategy",
    "TrendFollowStrategy",
    "WyckoffStrategy",
    "SupportResistanceStrategy",
    "SupplyDemandStrategy",
    "SMCStrategy",
    "ICTStrategy",
    "FundamentalStrategy",
    "COTStrategy",
    # Registry functions
    "create_strategy",
    "list_strategies",
    "get_strategy_metadata",
    "register_strategy",
    "STRATEGY_REGISTRY",
]
