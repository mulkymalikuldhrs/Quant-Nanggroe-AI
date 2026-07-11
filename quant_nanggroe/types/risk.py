"""Risk types for Quant Nanggroe AI.

Defines risk assessment, VaR, CVaR, drawdown, and position sizing structures.
These types enforce the constitutional risk limits that cannot be overridden.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk severity classification."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    BREACH = "breach"  # Constitutional limit breached


class RiskAssessment(BaseModel):
    """
    Complete risk assessment produced by the Risk Agent.

    Contains the outcome of all 9 constitutional risk checkpoints.
    Any checkpoint failure results in a VETO (trade blocked).
    """
    symbol: str
    risk_level: RiskLevel = RiskLevel.LOW
    approved: bool = True
    veto: bool = False
    veto_reason: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Constitutional Check Results
    check_per_trade_risk: bool = True
    check_daily_loss: bool = True
    check_weekly_loss: bool = True
    check_max_drawdown: bool = True
    check_correlation: bool = True
    check_concentration: bool = True
    check_liquidity: bool = True
    check_volatility: bool = True
    check_market_hours: bool = True

    # Risk Metrics
    per_trade_risk_pct: float = 0.0
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    portfolio_var: Optional[float] = None
    portfolio_cvar: Optional[float] = None
    position_concentration_pct: float = 0.0
    avg_correlation: Optional[float] = None

    # Sizing
    suggested_position_size: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None

    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class VaRResult(BaseModel):
    """
    Value at Risk calculation result.

    Supports parametric (variance-covariance), historical, and Monte Carlo methods.
    CVaR (Expected Shortfall) is always computed alongside VaR.
    """
    var_value: float = Field(..., description="Value at Risk in currency units")
    cvar_value: float = Field(..., description="Conditional VaR (Expected Shortfall)")
    confidence_level: float = Field(..., ge=0.9, le=0.99)
    time_horizon: int = Field(..., ge=1, description="Time horizon in days")
    method: str = Field(..., description="Calculation method (parametric/historical/monte_carlo)")
    portfolio_value: float = Field(..., gt=0)
    var_pct: float = Field(..., ge=0, description="VaR as percentage of portfolio")
    cvar_pct: float = Field(..., ge=0, description="CVaR as percentage of portfolio")
    timestamp: datetime = Field(default_factory=datetime.now)
    simulation_count: Optional[int] = None

    model_config = {"from_attributes": True}


class DrawdownResult(BaseModel):
    """
    Drawdown analysis result.

    Tracks maximum drawdown, current drawdown, and recovery metrics.
    """
    current_drawdown: float = Field(..., ge=0, description="Current drawdown percentage")
    max_drawdown: float = Field(..., ge=0, description="Maximum drawdown percentage")
    peak_value: float = Field(..., gt=0, description="Portfolio peak value")
    trough_value: Optional[float] = None
    current_value: float = Field(..., gt=0)
    recovery_time_days: Optional[int] = None
    underwater_duration_days: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"from_attributes": True}


class PositionSizingResult(BaseModel):
    """
    Position sizing calculation result.

    Supports Kelly Criterion, fixed-fractional, and risk-parity methods.
    """
    symbol: str
    position_size: float = Field(..., ge=0, description="Position size in base currency")
    position_value: float = Field(..., ge=0, description="Position value in quote currency")
    risk_amount: float = Field(..., ge=0, description="Amount risked on this position")
    risk_pct: float = Field(..., ge=0, le=5.0, description="Risk as percentage of portfolio")
    method: str = Field(..., description="Sizing method (kelly/fixed_fractional/risk_parity)")
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    risk_reward_ratio: Optional[float] = None
    kelly_fraction: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"from_attributes": True}
