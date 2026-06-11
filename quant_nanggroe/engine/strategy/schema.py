"""Pydantic models for YAML strategy validation.

Defines the schema for declarative trading strategies stored in YAML files.
All models use Pydantic v2 with strict validation.

Strategy YAML structure::

    name: "Momentum Alpha"
    description: "Cross-sectional momentum with volatility filter"
    universe:
      symbols: ["SPY", "QQQ", "IWM"]
      exchanges: ["NYSE", "NASDAQ"]
      market_cap_range: [1_000_000_000, null]
      sector_filter: ["Technology", "Healthcare"]
    timeframe: "1d"
    entry_rules:
      - indicator: "rsi"
        operator: "lt"
        value: 30
        timeframe: "1d"
      - indicator: "volume"
        operator: "gt"
        value: 1.5
        timeframe: "1d"
    exit_rules:
      - indicator: "rsi"
        operator: "gt"
        value: 70
        trailing_stop_pct: 5.0
        take_profit_pct: 15.0
    risk_rules:
      max_position_pct: 10.0
      stop_loss_pct: 3.0
      max_daily_trades: 5
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


class IndicatorType(str, Enum):
    """Supported technical indicators for strategy rules."""

    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"
    SMA = "sma"
    EMA = "ema"
    VOLUME = "volume"
    ATR = "atr"
    STOCHASTIC = "stochastic"
    ADX = "adx"
    OBV = "obv"
    VWAP = "vwap"
    FACTOR = "factor"
    PRICE = "price"
    CUSTOM = "custom"


class OperatorType(str, Enum):
    """Comparison operators for rule evaluation."""

    GT = "gt"           # greater than
    GTE = "gte"         # greater than or equal
    LT = "lt"           # less than
    LTE = "lte"         # less than or equal
    EQ = "eq"           # equal
    NEQ = "neq"         # not equal
    CROSS_ABOVE = "cross_above"   # signal crosses above threshold
    CROSS_BELOW = "cross_below"   # signal crosses below threshold


class TimeFrameType(str, Enum):
    """Supported timeframe strings for strategy rules."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MO1 = "1M"


class EntryRule(BaseModel):
    """A single entry condition for a trading strategy.

    Each entry rule specifies an indicator, comparison operator,
    threshold value, and optional timeframe for multi-timeframe strategies.
    All entry rules are evaluated with AND logic (all must be true).
    """

    indicator: str = Field(
        ...,
        description="Indicator name (e.g., 'rsi', 'sma_20', 'volume_ratio')",
        min_length=1,
    )
    operator: OperatorType = Field(
        ...,
        description="Comparison operator",
    )
    value: float = Field(
        ...,
        description="Threshold value to compare against",
    )
    timeframe: Optional[str] = Field(
        None,
        description="Timeframe for this rule (for multi-timeframe strategies)",
    )
    params: dict = Field(
        default_factory=dict,
        description="Additional parameters for indicator computation (e.g., {'period': 14})",
    )
    weight: float = Field(
        default=1.0,
        description="Weight of this rule in signal scoring (0.0-2.0)",
        ge=0.0,
        le=2.0,
    )

    @field_validator("indicator")
    @classmethod
    def indicator_must_be_valid(cls, v: str) -> str:
        """Validate indicator name is non-empty and lowercase."""
        if not v.strip():
            raise ValueError("Indicator name cannot be empty or whitespace")
        return v.strip().lower()


class ExitRule(BaseModel):
    """A single exit condition for a trading strategy.

    Exit rules can be indicator-based (same as entry rules) or
    percentage-based (trailing stop, take profit).
    """

    indicator: Optional[str] = Field(
        None,
        description="Indicator name for indicator-based exits",
        min_length=1,
    )
    operator: Optional[OperatorType] = Field(
        None,
        description="Comparison operator for indicator-based exits",
    )
    value: Optional[float] = Field(
        None,
        description="Threshold value for indicator-based exits",
    )
    trailing_stop_pct: Optional[float] = Field(
        None,
        description="Trailing stop percentage (e.g., 5.0 = 5% trailing stop)",
        gt=0.0,
        le=100.0,
    )
    take_profit_pct: Optional[float] = Field(
        None,
        description="Take profit percentage (e.g., 15.0 = 15% take profit)",
        gt=0.0,
        le=1000.0,
    )
    timeframe: Optional[str] = Field(
        None,
        description="Timeframe for this rule (for multi-timeframe strategies)",
    )
    params: dict = Field(
        default_factory=dict,
        description="Additional parameters for indicator computation",
    )

    @model_validator(mode="after")
    def must_have_exit_condition(self) -> "ExitRule":
        """Validate that at least one exit condition is specified."""
        has_indicator_exit = self.indicator is not None and self.operator is not None
        has_pct_exit = self.trailing_stop_pct is not None or self.take_profit_pct is not None
        if not has_indicator_exit and not has_pct_exit:
            raise ValueError(
                "ExitRule must have either an indicator-based condition "
                "(indicator + operator + value) or a percentage-based exit "
                "(trailing_stop_pct and/or take_profit_pct)"
            )
        return self


class RiskRules(BaseModel):
    """Risk management rules for a trading strategy.

    These rules are enforced as hard limits during backtesting and
    live trading. They cannot be overridden by agent decisions.
    """

    max_position_pct: float = Field(
        default=10.0,
        description="Maximum position size as percentage of portfolio",
        gt=0.0,
        le=100.0,
    )
    stop_loss_pct: float = Field(
        default=3.0,
        description="Default stop-loss percentage from entry price",
        gt=0.0,
        le=50.0,
    )
    max_daily_trades: int = Field(
        default=5,
        description="Maximum number of trades per day",
        ge=1,
        le=100,
    )
    max_portfolio_heat: Optional[float] = Field(
        None,
        description="Maximum portfolio heat (sum of position risks as % of capital)",
        gt=0.0,
        le=100.0,
    )
    max_correlation: Optional[float] = Field(
        None,
        description="Maximum pairwise correlation between positions",
        gt=0.0,
        le=1.0,
    )
    max_drawdown_pct: Optional[float] = Field(
        None,
        description="Maximum drawdown percentage before strategy halt",
        gt=0.0,
        le=100.0,
    )
    min_cash_reserve_pct: float = Field(
        default=5.0,
        description="Minimum cash reserve as percentage of portfolio",
        ge=0.0,
        le=50.0,
    )


class UniverseDefinition(BaseModel):
    """Defines the trading universe for a strategy.

    A universe can be specified as:
    - Explicit symbol list
    - Exchange-based filtering
    - Market cap range filtering
    - Sector/industry filtering

    Multiple filters are combined with AND logic.
    """

    symbols: List[str] = Field(
        default_factory=list,
        description="Explicit list of symbols to trade",
    )
    exchanges: List[str] = Field(
        default_factory=list,
        description="Exchange filters (e.g., ['NYSE', 'NASDAQ'])",
    )
    market_cap_range: Optional[Tuple[Optional[float], Optional[float]]] = Field(
        None,
        description="Market cap range as [min, max] in USD. None = no limit.",
    )
    sector_filter: List[str] = Field(
        default_factory=list,
        description="Sector filters (e.g., ['Technology', 'Healthcare'])",
    )
    exclude_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols to exclude from the universe",
    )
    min_price: Optional[float] = Field(
        None,
        description="Minimum price filter",
        gt=0.0,
    )
    max_price: Optional[float] = Field(
        None,
        description="Maximum price filter",
        gt=0.0,
    )
    min_volume: Optional[float] = Field(
        None,
        description="Minimum average daily volume filter",
        gt=0.0,
    )

    @field_validator("symbols")
    @classmethod
    def symbols_must_be_uppercase(cls, v: List[str]) -> List[str]:
        """Normalize symbols to uppercase."""
        return [s.strip().upper() for s in v if s.strip()]

    @field_validator("exchanges")
    @classmethod
    def exchanges_must_be_uppercase(cls, v: List[str]) -> List[str]:
        """Normalize exchange names to uppercase."""
        return [e.strip().upper() for e in v if e.strip()]

    @field_validator("sector_filter")
    @classmethod
    def sectors_must_be_title_case(cls, v: List[str]) -> List[str]:
        """Normalize sector names to title case."""
        return [s.strip().title() for s in v if s.strip()]

    @model_validator(mode="after")
    def must_have_at_least_one_filter(self) -> "UniverseDefinition":
        """Validate that at least one universe filter is specified."""
        has_any = (
            len(self.symbols) > 0
            or len(self.exchanges) > 0
            or self.market_cap_range is not None
            or len(self.sector_filter) > 0
        )
        if not has_any:
            raise ValueError(
                "UniverseDefinition must specify at least one filter: "
                "symbols, exchanges, market_cap_range, or sector_filter"
            )
        return self


class StrategyConfig(BaseModel):
    """Complete strategy configuration loaded from YAML.

    This is the top-level model that validates an entire strategy definition.
    It includes entry rules, exit rules, risk rules, and universe definition.
    """

    name: str = Field(
        ...,
        description="Strategy name (must be unique)",
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        default="",
        description="Human-readable strategy description",
        max_length=2000,
    )
    version: str = Field(
        default="1.0.0",
        description="Strategy version (semver)",
    )
    universe: UniverseDefinition = Field(
        ...,
        description="Trading universe definition",
    )
    timeframe: str = Field(
        default="1d",
        description="Primary strategy timeframe",
    )
    entry_rules: List[EntryRule] = Field(
        default_factory=list,
        description="Entry conditions (AND logic)",
        min_length=1,
    )
    exit_rules: List[ExitRule] = Field(
        default_factory=list,
        description="Exit conditions (OR logic — any triggers exit)",
        min_length=1,
    )
    risk_rules: RiskRules = Field(
        default_factory=RiskRules,
        description="Risk management rules",
    )
    base_strategy: Optional[str] = Field(
        None,
        description="Name of base strategy to inherit from (for strategy inheritance)",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Strategy tags for categorization",
    )
    author: Optional[str] = Field(
        None,
        description="Strategy author",
    )
    created_at: Optional[str] = Field(
        None,
        description="Creation date (ISO 8601)",
    )
    updated_at: Optional[str] = Field(
        None,
        description="Last update date (ISO 8601)",
    )

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v: str) -> str:
        """Validate strategy name."""
        v = v.strip()
        if not v:
            raise ValueError("Strategy name cannot be empty")
        if len(v) > 100:
            raise ValueError("Strategy name must be <= 100 characters")
        return v

    @field_validator("tags")
    @classmethod
    def tags_must_be_lowercase(cls, v: List[str]) -> List[str]:
        """Normalize tags to lowercase."""
        return [t.strip().lower() for t in v if t.strip()]

    model_config = {"extra": "forbid"}
