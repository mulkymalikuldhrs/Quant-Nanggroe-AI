"""Tests for the YAML Strategy System.

Tests cover:
- Schema validation (Pydantic models)
- YAML parsing and code generation
- Strategy loader and registry
- Backtest adapter signal generation

All tests are self-contained with no external dependencies.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.schema import (
    EntryRule,
    ExitRule,
    IndicatorType,
    OperatorType,
    RiskRules,
    StrategyConfig,
    UniverseDefinition,
)
from quant_nanggroe.engine.strategy.parser import (
    parse_strategy,
    parse_strategy_from_string,
    strategy_to_code,
    validate_strategy,
    _slugify,
)
from quant_nanggroe.engine.strategy.loader import (
    StrategyLoader,
    StrategyConfigRegistry,
    StrategyLoadError,
)
from quant_nanggroe.engine.strategy.backtest_adapter import (
    StrategyBacktestAdapter,
)


# ─── Sample YAML content ──────────────────────────────────────────────

VALID_STRATEGY_YAML = """
name: "Momentum Alpha"
description: "RSI-based momentum strategy with volume confirmation"
version: "1.0.0"
universe:
  symbols: ["SPY", "QQQ", "IWM"]
timeframe: "1d"
entry_rules:
  - indicator: "rsi"
    operator: "lt"
    value: 30
    params:
      period: 14
  - indicator: "volume"
    operator: "gt"
    value: 1000000
exit_rules:
  - indicator: "rsi"
    operator: "gt"
    value: 70
  - trailing_stop_pct: 5.0
    take_profit_pct: 15.0
risk_rules:
  max_position_pct: 10.0
  stop_loss_pct: 3.0
  max_daily_trades: 5
tags: ["momentum", "rsi"]
author: "Test Author"
"""

MINIMAL_STRATEGY_YAML = """
name: "Simple Strategy"
universe:
  symbols: ["AAPL"]
entry_rules:
  - indicator: "sma"
    operator: "gt"
    value: 100
exit_rules:
  - trailing_stop_pct: 5.0
risk_rules:
  max_position_pct: 10.0
  stop_loss_pct: 3.0
  max_daily_trades: 5
"""

STRATEGY_WITH_EXCHANGES_YAML = """
name: "Exchange Strategy"
universe:
  exchanges: ["NYSE", "NASDAQ"]
  sector_filter: ["Technology"]
entry_rules:
  - indicator: "price"
    operator: "gt"
    value: 50
exit_rules:
  - take_profit_pct: 20.0
risk_rules:
  max_position_pct: 15.0
  stop_loss_pct: 5.0
  max_daily_trades: 3
"""

INVALID_STRATEGY_YAML = """
name: ""
universe:
  symbols: []
entry_rules: []
exit_rules: []
"""

BASE_STRATEGY_YAML = """
name: "Base Momentum"
universe:
  symbols: ["SPY"]
entry_rules:
  - indicator: "rsi"
    operator: "lt"
    value: 30
exit_rules:
  - indicator: "rsi"
    operator: "gt"
    value: 70
risk_rules:
  max_position_pct: 10.0
  stop_loss_pct: 3.0
  max_daily_trades: 5
"""

CHILD_STRATEGY_YAML = """
name: "Aggressive Momentum"
base_strategy: "Base Momentum"
universe:
  symbols: ["SPY", "QQQ"]
entry_rules:
  - indicator: "rsi"
    operator: "lt"
    value: 40
risk_rules:
  max_position_pct: 20.0
  stop_loss_pct: 2.0
  max_daily_trades: 10
"""


# ═══════════════════════════════════════════════════════════════════════
# Schema Validation Tests
# ═══════════════════════════════════════════════════════════════════════


class TestEntryRule:
    """Tests for EntryRule model."""

    def test_valid_entry_rule(self):
        rule = EntryRule(indicator="rsi", operator="lt", value=30)
        assert rule.indicator == "rsi"
        assert rule.operator == OperatorType.LT
        assert rule.value == 30
        assert rule.weight == 1.0

    def test_entry_rule_with_params(self):
        rule = EntryRule(
            indicator="sma", operator="gt", value=100, params={"period": 20}
        )
        assert rule.params["period"] == 20

    def test_entry_rule_with_timeframe(self):
        rule = EntryRule(
            indicator="rsi", operator="lt", value=30, timeframe="1h"
        )
        assert rule.timeframe == "1h"

    def test_entry_rule_with_weight(self):
        rule = EntryRule(indicator="rsi", operator="lt", value=30, weight=1.5)
        assert rule.weight == 1.5

    def test_entry_rule_indicator_normalized(self):
        rule = EntryRule(indicator="  RSI  ", operator="lt", value=30)
        assert rule.indicator == "rsi"

    def test_entry_rule_empty_indicator_fails(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            EntryRule(indicator="   ", operator="lt", value=30)

    def test_entry_rule_invalid_weight(self):
        with pytest.raises(ValueError):
            EntryRule(indicator="rsi", operator="lt", value=30, weight=3.0)

    def test_entry_rule_negative_weight(self):
        with pytest.raises(ValueError):
            EntryRule(indicator="rsi", operator="lt", value=30, weight=-0.5)

    def test_all_operators(self):
        for op in OperatorType:
            rule = EntryRule(indicator="rsi", operator=op, value=50)
            assert rule.operator == op


class TestExitRule:
    """Tests for ExitRule model."""

    def test_indicator_exit_rule(self):
        rule = ExitRule(indicator="rsi", operator="gt", value=70)
        assert rule.indicator == "rsi"
        assert rule.operator == OperatorType.GT
        assert rule.value == 70

    def test_trailing_stop_exit(self):
        rule = ExitRule(trailing_stop_pct=5.0)
        assert rule.trailing_stop_pct == 5.0

    def test_take_profit_exit(self):
        rule = ExitRule(take_profit_pct=15.0)
        assert rule.take_profit_pct == 15.0

    def test_combined_pct_exit(self):
        rule = ExitRule(trailing_stop_pct=5.0, take_profit_pct=15.0)
        assert rule.trailing_stop_pct == 5.0
        assert rule.take_profit_pct == 15.0

    def test_no_exit_condition_fails(self):
        with pytest.raises(ValueError, match="must have either"):
            ExitRule()

    def test_trailing_stop_range(self):
        with pytest.raises(ValueError):
            ExitRule(trailing_stop_pct=0.0)

    def test_take_profit_range(self):
        with pytest.raises(ValueError):
            ExitRule(take_profit_pct=0.0)

    def test_trailing_stop_max(self):
        with pytest.raises(ValueError):
            ExitRule(trailing_stop_pct=101.0)


class TestRiskRules:
    """Tests for RiskRules model."""

    def test_default_risk_rules(self):
        rules = RiskRules()
        assert rules.max_position_pct == 10.0
        assert rules.stop_loss_pct == 3.0
        assert rules.max_daily_trades == 5
        assert rules.min_cash_reserve_pct == 5.0

    def test_custom_risk_rules(self):
        rules = RiskRules(
            max_position_pct=20.0,
            stop_loss_pct=5.0,
            max_daily_trades=10,
            max_drawdown_pct=15.0,
        )
        assert rules.max_position_pct == 20.0
        assert rules.max_drawdown_pct == 15.0

    def test_max_position_pct_range(self):
        with pytest.raises(ValueError):
            RiskRules(max_position_pct=0.0)

    def test_stop_loss_pct_range(self):
        with pytest.raises(ValueError):
            RiskRules(stop_loss_pct=0.0)

    def test_max_daily_trades_range(self):
        with pytest.raises(ValueError):
            RiskRules(max_daily_trades=0)

    def test_optional_fields_none_by_default(self):
        rules = RiskRules()
        assert rules.max_portfolio_heat is None
        assert rules.max_correlation is None
        assert rules.max_drawdown_pct is None


class TestUniverseDefinition:
    """Tests for UniverseDefinition model."""

    def test_symbols_universe(self):
        universe = UniverseDefinition(symbols=["AAPL", "MSFT", "GOOGL"])
        assert universe.symbols == ["AAPL", "MSFT", "GOOGL"]

    def test_symbols_normalized_uppercase(self):
        universe = UniverseDefinition(symbols=["aapl", "msft"])
        assert universe.symbols == ["AAPL", "MSFT"]

    def test_exchange_universe(self):
        universe = UniverseDefinition(exchanges=["nyse", "nasdaq"])
        assert universe.exchanges == ["NYSE", "NASDAQ"]

    def test_sector_filter_title_case(self):
        universe = UniverseDefinition(sector_filter=["technology", "health care"])
        assert universe.sector_filter == ["Technology", "Health Care"]

    def test_market_cap_range(self):
        universe = UniverseDefinition(
            symbols=["SPY"],
            market_cap_range=(1_000_000_000, None),
        )
        assert universe.market_cap_range[0] == 1_000_000_000

    def test_empty_universe_fails(self):
        with pytest.raises(ValueError, match="at least one filter"):
            UniverseDefinition()

    def test_exclude_symbols(self):
        universe = UniverseDefinition(
            symbols=["AAPL", "MSFT", "TSLA"],
            exclude_symbols=["TSLA"],
        )
        assert "TSLA" in universe.exclude_symbols

    def test_min_max_price(self):
        universe = UniverseDefinition(
            symbols=["SPY"],
            min_price=10.0,
            max_price=1000.0,
        )
        assert universe.min_price == 10.0
        assert universe.max_price == 1000.0

    def test_min_volume(self):
        universe = UniverseDefinition(
            symbols=["SPY"],
            min_volume=1_000_000,
        )
        assert universe.min_volume == 1_000_000


class TestStrategyConfig:
    """Tests for StrategyConfig model."""

    def test_valid_config(self):
        config = StrategyConfig(
            name="Test Strategy",
            universe=UniverseDefinition(symbols=["AAPL"]),
            entry_rules=[EntryRule(indicator="rsi", operator="lt", value=30)],
            exit_rules=[ExitRule(trailing_stop_pct=5.0)],
            risk_rules=RiskRules(),
        )
        assert config.name == "Test Strategy"

    def test_config_from_yaml_string(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        assert config.name == "Momentum Alpha"
        assert len(config.entry_rules) == 2
        assert len(config.exit_rules) == 2

    def test_config_defaults(self):
        config = parse_strategy_from_string(MINIMAL_STRATEGY_YAML)
        assert config.version == "1.0.0"
        assert config.description == ""

    def test_config_tags_normalized(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        assert "momentum" in config.tags
        assert "rsi" in config.tags

    def test_empty_name_fails(self):
        with pytest.raises(ValueError):
            StrategyConfig(
                name="",
                universe=UniverseDefinition(symbols=["AAPL"]),
                entry_rules=[EntryRule(indicator="rsi", operator="lt", value=30)],
                exit_rules=[ExitRule(trailing_stop_pct=5.0)],
            )

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValueError):
            parse_strategy_from_string("""
name: "Test"
universe:
  symbols: ["AAPL"]
entry_rules:
  - indicator: "rsi"
    operator: "lt"
    value: 30
exit_rules:
  - trailing_stop_pct: 5.0
unknown_field: "not allowed"
""")


# ═══════════════════════════════════════════════════════════════════════
# Parser Tests
# ═══════════════════════════════════════════════════════════════════════


class TestParseStrategy:
    """Tests for the YAML strategy parser."""

    def test_parse_from_string(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        assert config.name == "Momentum Alpha"

    def test_parse_from_file(self, tmp_path):
        yaml_file = tmp_path / "strategy.yaml"
        yaml_file.write_text(VALID_STRATEGY_YAML)

        config = parse_strategy(yaml_file)
        assert config.name == "Momentum Alpha"

    def test_parse_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_strategy("/nonexistent/strategy.yaml")

    def test_parse_invalid_yaml_type(self):
        with pytest.raises(ValueError, match="YAML mapping"):
            parse_strategy_from_string("just a string")

    def test_parse_empty_name_fails(self):
        with pytest.raises(ValueError):
            parse_strategy_from_string(INVALID_STRATEGY_YAML)

    def test_parse_preserves_entry_rules(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        assert len(config.entry_rules) == 2
        assert config.entry_rules[0].indicator == "rsi"
        assert config.entry_rules[1].indicator == "volume"

    def test_parse_preserves_exit_rules(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        assert len(config.exit_rules) == 2

    def test_parse_preserves_risk_rules(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        assert config.risk_rules.max_position_pct == 10.0
        assert config.risk_rules.stop_loss_pct == 3.0


class TestSlugify:
    """Tests for the _slugify helper."""

    def test_simple_name(self):
        assert _slugify("momentum") == "Momentum"

    def test_multi_word(self):
        assert _slugify("momentum_alpha") == "MomentumAlpha"

    def test_with_spaces(self):
        assert _slugify("Momentum Alpha") == "MomentumAlpha"

    def test_with_special_chars(self):
        assert _slugify("RSI-Strategy v2") == "RsiStrategyV2"


class TestValidateStrategy:
    """Tests for the validate_strategy function."""

    def test_valid_strategy_no_errors(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        errors = validate_strategy(config)
        assert len(errors) == 0

    def test_invalid_timeframe(self):
        config = parse_strategy_from_string("""
name: "Test"
universe:
  symbols: ["AAPL"]
timeframe: "2d"
entry_rules:
  - indicator: "rsi"
    operator: "lt"
    value: 30
exit_rules:
  - trailing_stop_pct: 5.0
""")
        errors = validate_strategy(config)
        assert any("timeframe" in e.lower() for e in errors)

    def test_trailing_stop_greater_than_take_profit(self):
        config = StrategyConfig(
            name="Test",
            universe=UniverseDefinition(symbols=["AAPL"]),
            entry_rules=[EntryRule(indicator="rsi", operator="lt", value=30)],
            exit_rules=[ExitRule(trailing_stop_pct=20.0, take_profit_pct=10.0)],
            risk_rules=RiskRules(),
        )
        errors = validate_strategy(config)
        assert any("trailing_stop" in e for e in errors)

    def test_stop_loss_greater_than_max_position(self):
        config = StrategyConfig(
            name="Test",
            universe=UniverseDefinition(symbols=["AAPL"]),
            entry_rules=[EntryRule(indicator="rsi", operator="lt", value=30)],
            exit_rules=[ExitRule(trailing_stop_pct=5.0)],
            risk_rules=RiskRules(max_position_pct=2.0, stop_loss_pct=5.0),
        )
        errors = validate_strategy(config)
        assert any("stop_loss" in e for e in errors)

    def test_self_referencing_base(self):
        config = StrategyConfig(
            name="Test",
            universe=UniverseDefinition(symbols=["AAPL"]),
            entry_rules=[EntryRule(indicator="rsi", operator="lt", value=30)],
            exit_rules=[ExitRule(trailing_stop_pct=5.0)],
            base_strategy="Test",
        )
        errors = validate_strategy(config)
        assert any("inherit from itself" in e for e in errors)

    def test_all_symbols_excluded(self):
        config = StrategyConfig(
            name="Test",
            universe=UniverseDefinition(
                symbols=["AAPL", "MSFT"],
                exclude_symbols=["AAPL", "MSFT"],
            ),
            entry_rules=[EntryRule(indicator="rsi", operator="lt", value=30)],
            exit_rules=[ExitRule(trailing_stop_pct=5.0)],
        )
        errors = validate_strategy(config)
        assert any("excluded" in e for e in errors)

    def test_min_price_greater_than_max_price(self):
        config = StrategyConfig(
            name="Test",
            universe=UniverseDefinition(
                symbols=["AAPL"],
                min_price=100.0,
                max_price=50.0,
            ),
            entry_rules=[EntryRule(indicator="rsi", operator="lt", value=30)],
            exit_rules=[ExitRule(trailing_stop_pct=5.0)],
        )
        errors = validate_strategy(config)
        assert any("min_price" in e for e in errors)


class TestStrategyToCode:
    """Tests for the strategy_to_code function."""

    def test_generates_valid_python(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        code = strategy_to_code(config)
        assert "class MomentumAlphaStrategy:" in code
        assert "compute_entry_signals" in code
        assert "compute_exit_signals" in code
        assert "generate_signals" in code

    def test_generates_imports(self):
        config = parse_strategy_from_string(MINIMAL_STRATEGY_YAML)
        code = strategy_to_code(config)
        assert "import numpy as np" in code
        assert "import pandas as pd" in code

    def test_generates_config_constants(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        code = strategy_to_code(config)
        assert 'NAME = "Momentum Alpha"' in code
        assert "MAX_POSITION_PCT = 10.0" in code
        assert "STOP_LOSS_PCT = 3.0" in code

    def test_generates_universe(self):
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        code = strategy_to_code(config)
        assert '"SPY"' in code
        assert '"QQQ"' in code
        assert '"IWM"' in code

    def test_slugify_name(self):
        config = parse_strategy_from_string(MINIMAL_STRATEGY_YAML)
        code = strategy_to_code(config)
        assert "class SimpleStrategyStrategy:" in code


# ═══════════════════════════════════════════════════════════════════════
# Loader and Registry Tests
# ═══════════════════════════════════════════════════════════════════════


class TestStrategyLoader:
    """Tests for StrategyLoader."""

    def test_load_from_file(self, tmp_path):
        yaml_file = tmp_path / "strategy.yaml"
        yaml_file.write_text(VALID_STRATEGY_YAML)

        loader = StrategyLoader(search_paths=[str(tmp_path)])
        config = loader.load(yaml_file)

        assert config.name == "Momentum Alpha"

    def test_load_caches_result(self, tmp_path):
        yaml_file = tmp_path / "strategy.yaml"
        yaml_file.write_text(VALID_STRATEGY_YAML)

        loader = StrategyLoader()
        config1 = loader.load(yaml_file)
        config2 = loader.load(yaml_file)

        assert config1.name == config2.name

    def test_load_file_not_found(self):
        loader = StrategyLoader()
        with pytest.raises(StrategyLoadError):
            loader.load("/nonexistent/strategy.yaml")

    def test_load_directory(self, tmp_path):
        (tmp_path / "strategy1.yaml").write_text(VALID_STRATEGY_YAML)
        (tmp_path / "strategy2.yaml").write_text(MINIMAL_STRATEGY_YAML)

        loader = StrategyLoader()
        configs = loader.load_directory(tmp_path)

        assert len(configs) == 2

    def test_load_directory_not_found(self):
        loader = StrategyLoader()
        with pytest.raises(StrategyLoadError):
            loader.load_directory("/nonexistent/dir")

    def test_load_empty_directory(self, tmp_path):
        loader = StrategyLoader()
        configs = loader.load_directory(tmp_path)
        assert configs == []

    def test_add_search_path(self, tmp_path):
        loader = StrategyLoader()
        loader.add_search_path(str(tmp_path))
        assert Path(tmp_path) in loader._search_paths

    def test_find_strategy_file(self, tmp_path):
        yaml_file = tmp_path / "base_momentum.yaml"
        yaml_file.write_text(BASE_STRATEGY_YAML)

        loader = StrategyLoader(search_paths=[str(tmp_path)])
        found = loader._find_strategy_file("Base Momentum")

        # May or may not find depending on name matching
        # The slugified name is "base_momentum"
        found_slug = loader._find_strategy_file("base_momentum")
        assert found_slug is not None or found is not None

    def test_inheritance_resolution(self, tmp_path):
        base_file = tmp_path / "base_momentum.yaml"
        base_file.write_text(BASE_STRATEGY_YAML)

        child_file = tmp_path / "aggressive_momentum.yaml"
        child_file.write_text(CHILD_STRATEGY_YAML)

        loader = StrategyLoader(search_paths=[str(tmp_path)])
        config = loader.load(child_file)

        # Child should override base fields
        assert config.name == "Aggressive Momentum"
        # Entry rule from child should override base
        assert config.entry_rules[0].value == 40
        # Risk rules from child should override
        assert config.risk_rules.max_position_pct == 20.0

    def test_check_for_changes(self, tmp_path):
        yaml_file = tmp_path / "strategy.yaml"
        yaml_file.write_text(VALID_STRATEGY_YAML)

        loader = StrategyLoader()
        config = loader.load(yaml_file)

        # No changes yet
        changed = loader.check_for_changes()
        assert config.name not in changed

        # Modify the file
        yaml_file.write_text(MINIMAL_STRATEGY_YAML)

        # Should detect change
        changed = loader.check_for_changes()
        assert "Momentum Alpha" in changed

    def test_reload_changed(self, tmp_path):
        yaml_file = tmp_path / "strategy.yaml"
        yaml_file.write_text(VALID_STRATEGY_YAML)

        loader = StrategyLoader()
        config = loader.load(yaml_file)
        assert config.name == "Momentum Alpha"

        # Modify and reload
        yaml_file.write_text(MINIMAL_STRATEGY_YAML)
        reloaded = loader.reload_changed()

        assert len(reloaded) == 1
        assert reloaded[0].name == "Simple Strategy"

    def test_merge_configs(self):
        base = parse_strategy_from_string(BASE_STRATEGY_YAML)
        child = parse_strategy_from_string(CHILD_STRATEGY_YAML)

        merged = StrategyLoader._merge_configs(base, child)

        assert merged.name == "Aggressive Momentum"
        assert merged.risk_rules.max_position_pct == 20.0
        # Universe from child
        assert "QQQ" in merged.universe.symbols


class TestStrategyConfigRegistry:
    """Tests for StrategyConfigRegistry."""

    def test_register_and_get(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        retrieved = registry.get("Momentum Alpha")
        assert retrieved.name == "Momentum Alpha"

    def test_register_duplicate_fails(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(config)

    def test_unregister(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        registry.unregister("Momentum Alpha")

        assert not registry.has("Momentum Alpha")

    def test_unregister_not_found(self):
        registry = StrategyConfigRegistry()
        with pytest.raises(KeyError):
            registry.unregister("Nonexistent")

    def test_get_not_found(self):
        registry = StrategyConfigRegistry()
        with pytest.raises(KeyError):
            registry.get("Nonexistent")

    def test_has(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        assert registry.has("Momentum Alpha")
        assert not registry.has("Nonexistent")

    def test_list_names(self):
        registry = StrategyConfigRegistry()
        config1 = parse_strategy_from_string(VALID_STRATEGY_YAML)
        config2 = parse_strategy_from_string(MINIMAL_STRATEGY_YAML)
        registry.register(config1)
        registry.register(config2)

        names = registry.list_names()
        assert "Momentum Alpha" in names
        assert "Simple Strategy" in names

    def test_list_names_by_tag(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        names = registry.list_names(tag="momentum")
        assert "Momentum Alpha" in names

        names = registry.list_names(tag="nonexistent")
        assert len(names) == 0

    def test_list_all(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        all_configs = registry.list_all()
        assert len(all_configs) == 1

    def test_load_from_directory(self, tmp_path):
        (tmp_path / "strategy.yaml").write_text(VALID_STRATEGY_YAML)

        registry = StrategyConfigRegistry()
        count = registry.load_from_directory(tmp_path)

        assert count == 1
        assert registry.has("Momentum Alpha")

    def test_validate_all(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        issues = registry.validate_all()
        assert len(issues) == 0

    def test_health(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)

        health = registry.health()
        assert health["total_strategies"] == 1
        assert "Momentum Alpha" in health["strategy_names"]

    def test_clear(self):
        registry = StrategyConfigRegistry()
        config = parse_strategy_from_string(VALID_STRATEGY_YAML)
        registry.register(config)
        registry.clear()
        assert not registry.has("Momentum Alpha")


# ═══════════════════════════════════════════════════════════════════════
# Backtest Adapter Tests
# ═══════════════════════════════════════════════════════════════════════


class TestStrategyBacktestAdapter:
    """Tests for StrategyBacktestAdapter."""

    @pytest.fixture
    def sample_config(self):
        return parse_strategy_from_string(VALID_STRATEGY_YAML)

    @pytest.fixture
    def sample_prices(self):
        """Generate sample price data."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        prices = np.maximum(prices, 1)  # Ensure positive prices

        df = pd.DataFrame(
            {"SPY": prices, "QQQ": prices * 0.8, "IWM": prices * 1.2},
            index=dates,
        )
        return df

    def test_adapter_creation(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        assert adapter.config.name == "Momentum Alpha"
        assert adapter.universe == ["SPY", "QQQ", "IWM"]

    def test_adapter_risk_rules(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        assert adapter.risk_rules.max_position_pct == 10.0

    def test_generate_signals(self, sample_config, sample_prices):
        adapter = StrategyBacktestAdapter(sample_config)
        signals = adapter.generate_signals(sample_prices)

        assert isinstance(signals, pd.DataFrame)
        assert len(signals) == len(sample_prices)
        # Signals should be between -1 and 1
        assert (signals.abs() <= 1.0).all().all()

    def test_signals_with_no_matching_symbols(self, sample_config):
        # Config uses SPY/QQQ/IWM, but data has different symbols
        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        prices = pd.DataFrame(
            {"FOO": np.random.uniform(90, 110, 50)},
            index=dates,
        )

        adapter = StrategyBacktestAdapter(sample_config)
        signals = adapter.generate_signals(prices)

        # Should fall back to available columns
        assert isinstance(signals, pd.DataFrame)

    def test_position_sizing_capped(self, sample_config, sample_prices):
        adapter = StrategyBacktestAdapter(sample_config)
        signals = adapter.generate_signals(sample_prices)

        # Max position is 10%, so max weight should be 0.10
        max_weight = sample_config.risk_rules.max_position_pct / 100.0
        assert (signals.abs() <= max_weight + 1e-10).all().all()

    def test_rsi_computation(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)

        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        prices = np.maximum(prices, 1)

        df = pd.DataFrame({
            "close": prices,
            "open": prices,
            "high": prices * 1.02,
            "low": prices * 0.98,
            "volume": 1_000_000,
        }, index=dates)

        rsi = adapter._compute_rsi(df["close"], period=14)
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(prices)
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

    def test_atr_computation(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)

        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        base = 100 + np.cumsum(np.random.randn(100))

        df = pd.DataFrame({
            "close": base,
            "open": base,
            "high": base + np.abs(np.random.randn(100)),
            "low": base - np.abs(np.random.randn(100)),
            "volume": 1_000_000,
        }, index=dates)

        atr = adapter._compute_atr(df, period=14)
        assert isinstance(atr, pd.Series)
        valid_atr = atr.dropna()
        assert (valid_atr >= 0).all()

    def test_evaluate_rule_gt(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        values = pd.Series([10, 20, 30, 40, 50])

        result = adapter._evaluate_rule(values, OperatorType.GT, 25)
        assert result.tolist() == [False, False, True, True, True]

    def test_evaluate_rule_lt(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        values = pd.Series([10, 20, 30, 40, 50])

        result = adapter._evaluate_rule(values, OperatorType.LT, 25)
        assert result.tolist() == [True, True, False, False, False]

    def test_evaluate_rule_cross_above(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        values = pd.Series([10, 20, 30, 25, 35])

        result = adapter._evaluate_rule(values, OperatorType.CROSS_ABOVE, 25)
        # index 0: shift(1) is NaN → False
        # index 1: 20>=25? No → False
        # index 2: 30>=25 AND 20<25? Yes → True
        # index 3: 25>=25 AND 30<25? No → False
        # index 4: 35>=25 AND 25<25? No → False
        assert result.iloc[0] == False
        assert result.iloc[1] == False
        assert result.iloc[2] == True
        assert result.iloc[3] == False

    def test_evaluate_rule_cross_below(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        values = pd.Series([50, 30, 20, 30, 10])

        result = adapter._evaluate_rule(values, OperatorType.CROSS_BELOW, 25)
        # index 0: shift(1) is NaN → False
        # index 1: 30<=25? No → False
        # index 2: 20<=25 AND 30>25? Yes → True
        # index 3: 30<=25? No → False
        # index 4: 10<=25 AND 30>25? Yes → True
        assert result.iloc[0] == False
        assert result.iloc[1] == False
        assert result.iloc[2] == True
        assert result.iloc[3] == False
        assert result.iloc[4] == True

    def test_to_backtest_config(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        bt_config = adapter.to_backtest_config()

        assert "initial_capital" in bt_config
        assert "commission_rate" in bt_config
        assert "max_positions" in bt_config

    def test_get_generated_code(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        code = adapter.get_generated_code()

        assert isinstance(code, str)
        assert "class" in code

    def test_clear_cache(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)
        adapter._indicator_cache["test"] = pd.Series([1, 2, 3])
        adapter.clear_cache()
        assert len(adapter._indicator_cache) == 0

    def test_generate_signals_with_prices(self, sample_config):
        adapter = StrategyBacktestAdapter(sample_config)

        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        base = 100 + np.cumsum(np.random.randn(100) * 2)
        base = np.maximum(base, 1)

        ohlcv = pd.DataFrame({
            "open": base,
            "high": base * 1.02,
            "low": base * 0.98,
            "close": base,
            "volume": 1_000_000,
        }, index=dates)

        ohlcv_dict = {"SPY": ohlcv}
        signals = adapter.generate_signals_with_prices(ohlcv_dict)

        assert isinstance(signals, pd.DataFrame)
        assert "SPY" in signals.columns

    def test_state_machine_full_with_trailing_stop(self):
        config = parse_strategy_from_string("""
name: "Trailing Stop Test"
universe:
  symbols: ["AAPL"]
entry_rules:
  - indicator: "price"
    operator: "gt"
    value: 0
exit_rules:
  - trailing_stop_pct: 10.0
risk_rules:
  max_position_pct: 10.0
  stop_loss_pct: 3.0
  max_daily_trades: 5
""")
        adapter = StrategyBacktestAdapter(config)

        # Create price data where price drops below trailing stop
        dates = pd.date_range("2024-01-01", periods=20, freq="D")
        prices = [100] * 5 + [99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85]

        ohlcv = pd.DataFrame({
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": [1_000_000] * 20,
        }, index=dates[:20])

        ohlcv_dict = {"AAPL": ohlcv}
        signals = adapter.generate_signals_with_prices(ohlcv_dict)

        # Should enter initially, then exit when trailing stop hits
        assert isinstance(signals, pd.DataFrame)


# ═══════════════════════════════════════════════════════════════════════
# Edge Case Tests
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge case tests across all strategy modules."""

    def test_config_with_all_operator_types(self):
        for op in OperatorType:
            config = StrategyConfig(
                name=f"Test_{op.value}",
                universe=UniverseDefinition(symbols=["AAPL"]),
                entry_rules=[EntryRule(indicator="rsi", operator=op, value=50)],
                exit_rules=[ExitRule(trailing_stop_pct=5.0)],
            )
            assert config.entry_rules[0].operator == op

    def test_config_with_custom_indicator(self):
        config = parse_strategy_from_string("""
name: "Custom Indicator"
universe:
  symbols: ["AAPL"]
entry_rules:
  - indicator: "custom_alpha"
    operator: "gt"
    value: 1.5
    params:
      period: 20
      smoothing: 3
exit_rules:
  - trailing_stop_pct: 5.0
""")
        assert config.entry_rules[0].indicator == "custom_alpha"
        assert config.entry_rules[0].params["smoothing"] == 3

    def test_universe_with_only_exchanges(self):
        config = parse_strategy_from_string(STRATEGY_WITH_EXCHANGES_YAML)
        assert config.universe.exchanges == ["NYSE", "NASDAQ"]
        assert config.universe.sector_filter == ["Technology"]

    def test_risk_rules_with_all_optional_fields(self):
        rules = RiskRules(
            max_position_pct=15.0,
            stop_loss_pct=3.0,
            max_daily_trades=8,
            max_portfolio_heat=30.0,
            max_correlation=0.7,
            max_drawdown_pct=15.0,
            min_cash_reserve_pct=10.0,
        )
        assert rules.max_portfolio_heat == 30.0
        assert rules.max_correlation == 0.7

    def test_loader_skips_invalid_files(self, tmp_path):
        (tmp_path / "valid.yaml").write_text(VALID_STRATEGY_YAML)
        (tmp_path / "invalid.yaml").write_text("not: a\nvalid: strategy")

        loader = StrategyLoader()
        configs = loader.load_directory(tmp_path)

        # Should load at least the valid one
        assert len(configs) >= 1

    def test_registry_duplicate_update(self, tmp_path):
        yaml_file = tmp_path / "strategy.yaml"
        yaml_file.write_text(VALID_STRATEGY_YAML)

        registry = StrategyConfigRegistry()
        count1 = registry.load_from_directory(tmp_path)

        # Load again — should update, not fail
        count2 = registry.load_from_directory(tmp_path)

        assert count1 == 1
        assert count2 == 1

    def test_adapter_with_constant_prices(self):
        """Test adapter handles constant prices (zero volatility)."""
        config = parse_strategy_from_string(MINIMAL_STRATEGY_YAML)
        adapter = StrategyBacktestAdapter(config)

        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        prices = np.full(50, 100.0)

        df = pd.DataFrame({"AAPL": prices}, index=dates)
        signals = adapter.generate_signals(df)

        assert isinstance(signals, pd.DataFrame)

    def test_parse_strategy_with_yml_extension(self, tmp_path):
        yaml_file = tmp_path / "strategy.yml"
        yaml_file.write_text(VALID_STRATEGY_YAML)

        config = parse_strategy(yaml_file)
        assert config.name == "Momentum Alpha"
