"""YAML Strategy System for Quant Nanggroe AI.

Provides a declarative strategy definition system where trading strategies
are defined in YAML files, validated with Pydantic models, and converted
to executable signal generators for the backtest engine.

Components:
- schema: Pydantic models for strategy YAML validation
- parser: YAML strategy parser and code generator
- loader: Strategy loader, registry, and hot-reload
- backtest_adapter: Connect strategies to backtest engine
"""

from __future__ import annotations

from quant_nanggroe_ai.engine.strategy.schema import (
    EntryRule,
    ExitRule,
    RiskRules,
    StrategyConfig,
    UniverseDefinition,
)
from quant_nanggroe_ai.engine.strategy.parser import (
    parse_strategy,
    validate_strategy,
    strategy_to_code,
)
from quant_nanggroe_ai.engine.strategy.loader import StrategyLoader, StrategyRegistry
from quant_nanggroe_ai.engine.strategy.backtest_adapter import StrategyBacktestAdapter

__all__ = [
    # Schema
    "EntryRule",
    "ExitRule",
    "RiskRules",
    "StrategyConfig",
    "UniverseDefinition",
    # Parser
    "parse_strategy",
    "validate_strategy",
    "strategy_to_code",
    # Loader
    "StrategyLoader",
    "StrategyRegistry",
    # Adapter
    "StrategyBacktestAdapter",
]
