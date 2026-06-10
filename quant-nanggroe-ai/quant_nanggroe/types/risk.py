"""Risk types — VaR, CVaR, Drawdown, and Trading Constitution.

These types encode risk measurements and constraints used by the risk
management engine and the Trading Constitution (the set of hard rules
that can never be violated).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VaRMethod(str, Enum):
    """Value at Risk calculation method."""

    PARAMETRIC = "parametric"
    HISTORICAL = "historical"
    MONTE_CARLO = "monte_carlo"
    CVAR = "cvar"


class VaRResult(BaseModel):
    """Result of a Value at Risk calculation.

    Supports multiple methods: parametric (variance-covariance),
    historical (empirical), Monte Carlo simulation, and CVaR.
    """

    method: VaRMethod = Field(description="Calculation method used")
    confidence_level: float = Field(
        gt=0.0,
        lt=1.0,
        description="Confidence level (e.g., 0.95 for 95%)",
    )
    var: float = Field(description="Value at Risk — maximum expected loss")
    expected_shortfall: float = Field(
        description="CVaR — average loss beyond VaR threshold",
    )
    confidence_interval: tuple[float, float] = Field(
        description="Confidence interval (lower, upper)",
    )
    portfolio_value: Optional[float] = Field(
        default=None,
        description="Portfolio value used in calculation",
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"json_schema_extra": {
        "examples": [{
            "method": "parametric",
            "confidence_level": 0.95,
            "var": 0.0234,
            "expected_shortfall": 0.0312,
            "confidence_interval": [-0.04, 0.02],
        }]
    }}


class DrawdownResult(BaseModel):
    """Drawdown analysis result."""

    max_drawdown: float = Field(
        ge=0.0,
        le=1.0,
        description="Maximum drawdown as fraction of peak (0.0–1.0)",
    )
    max_drawdown_pct: float = Field(
        description="Maximum drawdown as percentage",
    )
    current_drawdown: float = Field(
        ge=0.0,
        le=1.0,
        description="Current drawdown from peak",
    )
    current_drawdown_pct: float = Field(description="Current drawdown as percentage")
    peak_value: float = Field(description="Peak portfolio value")
    trough_value: float = Field(description="Trough portfolio value at max drawdown")
    recovery_time_days: Optional[int] = Field(
        default=None,
        description="Days to recover from max drawdown (None if not yet recovered)",
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"json_schema_extra": {
        "examples": [{
            "max_drawdown": 0.15,
            "max_drawdown_pct": 15.0,
            "current_drawdown": 0.03,
            "current_drawdown_pct": 3.0,
            "peak_value": 100000.0,
            "trough_value": 85000.0,
        }]
    }}


class RiskMetrics(BaseModel):
    """Comprehensive risk metrics for a portfolio or position."""

    var_95: Optional[float] = Field(default=None, description="VaR at 95% confidence")
    var_99: Optional[float] = Field(default=None, description="VaR at 99% confidence")
    cvar_95: Optional[float] = Field(default=None, description="CVaR at 95% confidence")
    max_drawdown: float = Field(default=0.0, ge=0.0, description="Maximum drawdown fraction")
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(default=None, description="Sortino ratio")
    calmar_ratio: Optional[float] = Field(default=None, description="Calmar ratio")
    volatility: Optional[float] = Field(default=None, ge=0.0, description="Annualized volatility")
    beta: Optional[float] = Field(default=None, description="Beta relative to benchmark")
    correlation: Optional[float] = Field(default=None, ge=-1.0, le=1.0, description="Correlation")
    win_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Win rate 0.0–1.0")
    profit_factor: Optional[float] = Field(default=None, ge=0.0, description="Profit factor")
    expectancy: Optional[float] = Field(default=None, description="Expected value per trade")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"json_schema_extra": {
        "examples": [{
            "var_95": 0.0234,
            "var_99": 0.0389,
            "cvar_95": 0.0312,
            "max_drawdown": 0.15,
            "sharpe_ratio": 1.8,
            "sortino_ratio": 2.3,
            "volatility": 0.25,
            "win_rate": 0.62,
        }]
    }}


class TradingConstitution(BaseModel):
    """The Trading Constitution — inviolable hard rules.

    These rules can NEVER be overridden by any agent or strategy.
    They are the absolute guardrails of the system.

    Inspired by Quant-Nanggroe-AI's TradingConstitution and the
    Blueprint Final specification.
    """

    risk_greater_than_opportunity: bool = Field(
        default=True,
        description="Risk assessment must precede opportunity assessment",
    )
    regime_greater_than_strategy: bool = Field(
        default=True,
        description="Market regime must allow strategy execution",
    )
    structure_greater_than_indicator: bool = Field(
        default=True,
        description="Market structure overrides indicator signals",
    )
    invalidation_greater_than_rr: bool = Field(
        default=True,
        description="Invalidation logic overrides risk/reward calculations",
    )
    no_trade_is_valid_decision: bool = Field(
        default=True,
        description="Choosing not to trade is always valid",
    )
    max_leverage: float = Field(default=3.0, ge=1.0, description="Maximum allowed leverage")
    max_correlation: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Maximum correlation between positions",
    )
    max_exposure_per_asset: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Maximum portfolio exposure to a single asset",
    )
    daily_drawdown_limit: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Maximum daily drawdown limit (fraction)",
    )

    model_config = {"json_schema_extra": {
        "examples": [{
            "risk_greater_than_opportunity": True,
            "regime_greater_than_strategy": True,
            "structure_greater_than_indicator": True,
            "invalidation_greater_than_rr": True,
            "no_trade_is_valid_decision": True,
            "max_leverage": 3.0,
            "max_correlation": 0.7,
            "max_exposure_per_asset": 0.2,
            "daily_drawdown_limit": 0.05,
        }]
    }}
