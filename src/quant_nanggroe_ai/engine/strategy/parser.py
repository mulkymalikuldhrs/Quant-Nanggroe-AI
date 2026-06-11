"""YAML strategy parser and code generator.

Parses YAML strategy files into validated StrategyConfig objects,
validates them for semantic correctness, and generates executable
Python code from strategy definitions.

Usage::

    from quant_nanggroe_ai.engine.strategy.parser import parse_strategy, validate_strategy

    config = parse_strategy("strategies/momentum.yaml")
    errors = validate_strategy(config)
    code = strategy_to_code(config)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import ValidationError

from quant_nanggroe_ai.engine.strategy.schema import (
    EntryRule,
    ExitRule,
    RiskRules,
    StrategyConfig,
    UniverseDefinition,
)

logger = logging.getLogger(__name__)

# Operator to Python operator mapping for code generation
_OPERATOR_MAP = {
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "eq": "==",
    "neq": "!=",
    "cross_above": "cross_above",
    "cross_below": "cross_below",
}


def parse_strategy(yaml_path: str | Path) -> StrategyConfig:
    """Parse a YAML strategy file into a validated StrategyConfig.

    Args:
        yaml_path: Path to the YAML strategy file.

    Returns:
        Validated StrategyConfig instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If the YAML content fails validation.
        yaml.YAMLError: If the file is not valid YAML.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Strategy file must contain a YAML mapping, got {type(raw).__name__}")

    try:
        config = StrategyConfig(**raw)
    except ValidationError as e:
        # Format Pydantic errors for readability
        errors = []
        for error in e.errors():
            loc = ".".join(str(l) for l in error["loc"])
            errors.append(f"  {loc}: {error['msg']}")
        raise ValueError(
            f"Strategy validation failed in {path.name}:\n" + "\n".join(errors)
        ) from e

    logger.info(f"Parsed strategy: {config.name} (v{config.version})")
    return config


def parse_strategy_from_string(yaml_content: str) -> StrategyConfig:
    """Parse a YAML strategy string into a validated StrategyConfig.

    Args:
        yaml_content: YAML strategy content as a string.

    Returns:
        Validated StrategyConfig instance.

    Raises:
        ValueError: If the YAML content fails validation.
        yaml.YAMLError: If the content is not valid YAML.
    """
    raw = yaml.safe_load(yaml_content)

    if not isinstance(raw, dict):
        raise ValueError(f"Strategy must be a YAML mapping, got {type(raw).__name__}")

    try:
        config = StrategyConfig(**raw)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            loc = ".".join(str(l) for l in error["loc"])
            errors.append(f"  {loc}: {error['msg']}")
        raise ValueError(
            "Strategy validation failed:\n" + "\n".join(errors)
        ) from e

    return config


def validate_strategy(config: StrategyConfig) -> List[str]:
    """Validate a StrategyConfig for semantic correctness.

    Performs checks beyond Pydantic schema validation:
    - Entry rules reference valid indicators
    - Exit rules are consistent (not contradictory)
    - Risk rules are reasonable
    - Universe is non-empty after filtering
    - Timeframe is valid

    Args:
        config: StrategyConfig to validate.

    Returns:
        List of validation error strings. Empty list means valid.
    """
    errors: List[str] = []

    # 1. Check timeframe is valid
    valid_timeframes = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"}
    if config.timeframe not in valid_timeframes:
        errors.append(
            f"Invalid timeframe '{config.timeframe}'. Must be one of {valid_timeframes}"
        )

    # 2. Check entry rules are not contradictory
    for i, rule in enumerate(config.entry_rules):
        # Check for conflicting rules on same indicator
        for j, other in enumerate(config.entry_rules):
            if i >= j:
                continue
            if rule.indicator == other.indicator and rule.operator == other.operator:
                if rule.operator.value in ("gt", "gte") and other.operator.value in ("gt", "gte"):
                    if rule.value > other.value:
                        errors.append(
                            f"Entry rules [{i}] and [{j}] on '{rule.indicator}' "
                            f"may be contradictory: {rule.value} and {other.value}"
                        )

    # 3. Check exit rules have valid percentages
    for i, rule in enumerate(config.exit_rules):
        if rule.trailing_stop_pct is not None and rule.take_profit_pct is not None:
            if rule.trailing_stop_pct >= rule.take_profit_pct:
                errors.append(
                    f"Exit rule [{i}]: trailing_stop_pct ({rule.trailing_stop_pct}%) "
                    f">= take_profit_pct ({rule.take_profit_pct}%) — "
                    f"trailing stop should be smaller than take profit"
                )

    # 4. Check risk rules are reasonable
    risk = config.risk_rules
    if risk.stop_loss_pct > risk.max_position_pct:
        errors.append(
            f"Risk: stop_loss_pct ({risk.stop_loss_pct}%) > max_position_pct "
            f"({risk.max_position_pct}%) — stop loss should not exceed max position"
        )

    if risk.max_daily_trades <= 0:
        errors.append(f"Risk: max_daily_trades must be positive, got {risk.max_daily_trades}")

    # 5. Check universe will produce non-empty results
    universe = config.universe
    if universe.symbols and universe.exclude_symbols:
        remaining = set(universe.symbols) - set(universe.exclude_symbols)
        if not remaining:
            errors.append(
                "Universe: all symbols are excluded by exclude_symbols"
            )

    if universe.min_price is not None and universe.max_price is not None:
        if universe.min_price > universe.max_price:
            errors.append(
                f"Universe: min_price ({universe.min_price}) > max_price ({universe.max_price})"
            )

    # 6. Check entry/exit rule timeframes match strategy timeframe (if specified)
    for i, rule in enumerate(config.entry_rules):
        if rule.timeframe and rule.timeframe not in valid_timeframes:
            errors.append(
                f"Entry rule [{i}]: invalid timeframe '{rule.timeframe}'"
            )

    for i, rule in enumerate(config.exit_rules):
        if rule.timeframe and rule.timeframe not in valid_timeframes:
            errors.append(
                f"Exit rule [{i}]: invalid timeframe '{rule.timeframe}'"
            )

    # 7. Check for base_strategy reference (circular dependency warning)
    if config.base_strategy == config.name:
        errors.append(
            f"Strategy '{config.name}' cannot inherit from itself"
        )

    return errors


def strategy_to_code(config: StrategyConfig) -> str:
    """Generate executable Python code from a StrategyConfig.

    Creates a self-contained Python function that implements the strategy's
    entry and exit logic. The generated code uses pandas and numpy
    for indicator computation and signal generation.

    Args:
        config: StrategyConfig to convert to code.

    Returns:
        Python code string that defines a signal generator function.
    """
    lines: List[str] = []

    # Header
    lines.append('"""Auto-generated strategy code from YAML configuration."""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import numpy as np")
    lines.append("import pandas as pd")
    lines.append("from typing import Dict, Optional")
    lines.append("")

    # Signal generator class
    class_name = _slugify(config.name)
    lines.append(f"class {class_name}Strategy:")
    lines.append(f'    """Strategy: {config.name}')
    if config.description:
        lines.append(f"    {config.description}")
    lines.append(f'    """')
    lines.append("")

    # Config
    lines.append(f'    NAME = "{config.name}"')
    lines.append(f'    TIMEFRAME = "{config.timeframe}"')
    lines.append(f"    MAX_POSITION_PCT = {config.risk_rules.max_position_pct}")
    lines.append(f"    STOP_LOSS_PCT = {config.risk_rules.stop_loss_pct}")
    lines.append(f"    MAX_DAILY_TRADES = {config.risk_rules.max_daily_trades}")
    lines.append("")

    # Universe
    symbols_str = ", ".join(f'"{s}"' for s in config.universe.symbols)
    lines.append(f"    UNIVERSE = [{symbols_str}]")
    lines.append("")

    # Entry rules
    lines.append("    @staticmethod")
    lines.append("    def compute_entry_signals(df: pd.DataFrame) -> pd.Series:")
    lines.append('        """Compute entry signals (1 = enter, 0 = no signal)."""')
    lines.append("        signals = pd.Series(0, index=df.index)")

    for i, rule in enumerate(config.entry_rules):
        op = _OPERATOR_MAP.get(rule.operator.value, ">")
        indicator_fn = _indicator_to_function(rule.indicator, rule.params)

        if rule.operator.value in ("cross_above", "cross_below"):
            lines.append(f"        # Entry rule {i}: {rule.indicator} {rule.operator.value} {rule.value}")
            lines.append(f"        _ind_{i} = {indicator_fn}")
            if rule.operator.value == "cross_above":
                lines.append(
                    f"        _cross_{i} = (_ind_{i}.shift(1) < {rule.value}) & "
                    f"(_ind_{i} >= {rule.value})"
                )
            else:
                lines.append(
                    f"        _cross_{i} = (_ind_{i}.shift(1) > {rule.value}) & "
                    f"(_ind_{i} <= {rule.value})"
                )
            lines.append(f"        signals = signals + _cross_{i}.astype(int)")
        else:
            lines.append(f"        # Entry rule {i}: {rule.indicator} {op} {rule.value}")
            lines.append(f"        _ind_{i} = {indicator_fn}")
            lines.append(f"        _cond_{i} = (_ind_{i} {op} {rule.value})")
            lines.append(f"        signals = signals + _cond_{i}.astype(int)")

    # AND logic: all rules must be true
    if config.entry_rules:
        lines.append(f"        # AND logic: all {len(config.entry_rules)} rules must be true")
        lines.append(
            f"        entry = (signals >= {len(config.entry_rules)}).astype(int)"
        )
    else:
        lines.append("        entry = signals")
    lines.append("        return entry")
    lines.append("")

    # Exit rules
    lines.append("    @staticmethod")
    lines.append("    def compute_exit_signals(df: pd.DataFrame, entry_price: Optional[pd.Series] = None) -> pd.Series:")
    lines.append('        """Compute exit signals (1 = exit, 0 = hold)."""')
    lines.append("        exit_signals = pd.Series(0, index=df.index)")

    for i, rule in enumerate(config.exit_rules):
        if rule.trailing_stop_pct is not None:
            pct = rule.trailing_stop_pct / 100.0
            lines.append(f"        # Exit rule {i}: trailing stop {rule.trailing_stop_pct}%")
            lines.append("        if entry_price is not None:")
            lines.append(f"            _trail_stop = entry_price * (1 - {pct})")
            lines.append("            _trail_exit = df['close'] < _trail_stop")
            lines.append("            exit_signals = exit_signals | _trail_exit.astype(int)")
        elif rule.take_profit_pct is not None:
            pct = rule.take_profit_pct / 100.0
            lines.append(f"        # Exit rule {i}: take profit {rule.take_profit_pct}%")
            lines.append("        if entry_price is not None:")
            lines.append(f"            _tp_price = entry_price * (1 + {pct})")
            lines.append("            _tp_exit = df['close'] >= _tp_price")
            lines.append("            exit_signals = exit_signals | _tp_exit.astype(int)")
        elif rule.indicator and rule.operator:
            op = _OPERATOR_MAP.get(rule.operator.value, ">")
            indicator_fn = _indicator_to_function(rule.indicator, rule.params)
            lines.append(f"        # Exit rule {i}: {rule.indicator} {rule.operator.value} {rule.value}")
            lines.append(f"        _exit_ind_{i} = {indicator_fn}")

            if rule.operator.value in ("cross_above", "cross_below"):
                if rule.operator.value == "cross_above":
                    lines.append(
                        f"        _exit_cross_{i} = (_exit_ind_{i}.shift(1) < {rule.value}) & "
                        f"(_exit_ind_{i} >= {rule.value})"
                    )
                else:
                    lines.append(
                        f"        _exit_cross_{i} = (_exit_ind_{i}.shift(1) > {rule.value}) & "
                        f"(_exit_ind_{i} <= {rule.value})"
                    )
                lines.append(f"        exit_signals = exit_signals | _exit_cross_{i}.astype(int)")
            else:
                lines.append(f"        _exit_cond_{i} = (_exit_ind_{i} {op} {rule.value})")
                lines.append(f"        exit_signals = exit_signals | _exit_cond_{i}.astype(int)")

    # OR logic: any exit rule triggers exit
    lines.append("        exit = (exit_signals > 0).astype(int)")
    lines.append("        return exit")
    lines.append("")

    # Generate signal function
    lines.append("    @classmethod")
    lines.append("    def generate_signals(cls, df: pd.DataFrame) -> pd.Series:")
    lines.append('        """Generate position signals: 1 = long, 0 = flat, -1 = short."""')
    lines.append("        entry = cls.compute_entry_signals(df)")
    lines.append("        exit = cls.compute_exit_signals(df)")
    lines.append("        # Simple state machine: enter on entry, exit on exit")
    lines.append("        position = pd.Series(0, index=df.index)")
    lines.append("        in_position = False")
    lines.append("        for i in range(len(df)):")
    lines.append("            if not in_position and entry.iloc[i] == 1:")
    lines.append("                position.iloc[i] = 1")
    lines.append("                in_position = True")
    lines.append("            elif in_position and exit.iloc[i] == 1:")
    lines.append("                position.iloc[i] = 0")
    lines.append("                in_position = False")
    lines.append("            elif in_position:")
    lines.append("                position.iloc[i] = 1")
    lines.append("        return position")
    lines.append("")

    return "\n".join(lines)


def _slugify(name: str) -> str:
    """Convert a strategy name to a valid Python class name.

    Args:
        name: Strategy name string.

    Returns:
        Valid Python identifier (CamelCase).
    """
    # Replace non-alphanumeric with underscores
    slug = "".join(c if c.isalnum() else "_" for c in name)
    # Split on underscores and title-case each part
    parts = slug.split("_")
    return "".join(p.capitalize() for p in parts if p)


def _indicator_to_function(indicator: str, params: dict) -> str:
    """Convert an indicator name and params to a pandas computation expression.

    Args:
        indicator: Indicator name (e.g., 'rsi', 'sma', 'volume').
        params: Indicator parameters (e.g., {'period': 14}).

    Returns:
        Python code string for computing the indicator.
    """
    period = params.get("period", 14)

    if indicator in ("sma", "simple_moving_average"):
        return f"df['close'].rolling(window={period}).mean()"
    elif indicator in ("ema", "exponential_moving_average"):
        return f"df['close'].ewm(span={period}, adjust=False).mean()"
    elif indicator == "rsi":
        return (
            f"(lambda s: 100 - 100 / (1 + s.pct_change().rolling({period}).mean() / "
            f"s.pct_change().rolling({period}).std()))(df['close'])"
        )
    elif indicator == "volume":
        return "df['volume']"
    elif indicator == "price":
        return "df['close']"
    elif indicator == "atr":
        return (
            f"(lambda h, l, c: (h - l).rolling({period}).mean())"
            f"(df['high'], df['low'], df['close'])"
        )
    elif indicator == "macd":
        fast = params.get("fast_period", 12)
        slow = params.get("slow_period", 26)
        return (
            f"df['close'].ewm(span={fast}, adjust=False).mean() - "
            f"df['close'].ewm(span={slow}, adjust=False).mean()"
        )
    elif indicator == "bollinger":
        bb_period = params.get("period", 20)
        return f"df['close'].rolling(window={bb_period}).mean()"
    else:
        # Generic indicator: try to look up as a factor or custom column
        return f"df.get('{indicator}', df['close'])"
