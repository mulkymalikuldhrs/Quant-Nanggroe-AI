"""YAML Strategy System for Quant Nanggroe AI.

Provides a declarative strategy definition system where trading strategies
are defined in YAML files, validated with Pydantic models, and converted
to executable signal generators for the backtest engine.

Components:
- schema: Pydantic models for strategy YAML validation
- parser: YAML strategy parser and code generator
- loader: Strategy loader, registry, and hot-reload
- backtest_adapter: Connect strategies to backtest engine
- templates: Pre-built strategy templates (YAML files)
"""

from __future__ import annotations

from quant_nanggroe.engine.strategy.schema import (
    EntryRule,
    ExitRule,
    IndicatorType,
    OperatorType,
    RiskRules,
    StrategyConfig,
    TimeFrameType,
    UniverseDefinition,
)
from quant_nanggroe.engine.strategy.parser import (
    parse_strategy,
    parse_strategy_from_string,
    validate_strategy,
    strategy_to_code,
)
from quant_nanggroe.engine.strategy.loader import (
    StrategyLoader,
    StrategyRegistry,
    StrategyWatcher,
    StrategyLoadError,
)
from quant_nanggroe.engine.strategy.backtest_adapter import StrategyBacktestAdapter
from quant_nanggroe.engine.strategy.regime_strategy import RegimeAdaptiveStrategy
from quant_nanggroe.engine.strategy.registry import (
    StrategyRegistry,
    StrategyMetadata,
    WalkForwardResult,
)

__all__ = [
    # Schema
    "EntryRule",
    "ExitRule",
    "IndicatorType",
    "OperatorType",
    "RiskRules",
    "StrategyConfig",
    "TimeFrameType",
    "UniverseDefinition",
    # Parser
    "parse_strategy",
    "parse_strategy_from_string",
    "validate_strategy",
    "strategy_to_code",
    # Loader
    "StrategyLoader",
    "StrategyRegistry",
    "StrategyWatcher",
    "StrategyLoadError",
    # Adapter
    "StrategyBacktestAdapter",
    # Regime-adaptive
    "RegimeAdaptiveStrategy",
    # Registry
    "StrategyRegistry",
    "StrategyMetadata",
    "WalkForwardResult",
]
