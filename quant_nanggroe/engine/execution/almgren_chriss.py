"""
Almgren-Chriss Optimal Execution Model
Implements the classic Almgren-Chriss framework for optimal trade execution
with linear market impact and temporary + permanent impact costs.

Reference: Almgren & Chriss (2001), "Optimal Execution of Portfolio Transactions"
Journal of Risk, 3(2), 5-39.

Extended with:
- Adaptive execution schedules (VWAP, TWAP, Implementation Shortfall)
- Volume profile integration
- Real-time market data updates
- Multi-asset execution
"""
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionParams:
    """Almgren-Chriss model parameters"""
    total_shares: float          # Total shares to execute
    shares_per_period: float     # Natural trading volume per period
    volatility: float            # Annualized volatility
    spread: float                # Bid-ask spread (as fraction)
    alpha: float                 # Drift (expected return)
    eta: float                   # Temporary impact coefficient (default: 2.5e-7)
    lambda_: float               # Risk aversion coefficient
    gamma: float                 # Permanent impact coefficient
    sigma: float                 # Daily volatility
    T: int                       # Number of trading periods
    start_price: float           # Current price

    @classmethod
    def from_market_data(cls, shares: float, avg_daily_volume: float,
                          price: float, volatility: float = 0.2,
                          spread: float = 0.001, risk_aversion: float = 1e-6,
                          days: int = 5, periods_per_day: int = 13) -> 'ExecutionParams':
        """Create params from market data"""
        total_periods = days * periods_per_day
        period_vol = volatility / np.sqrt(252 * periods_per_day)

        # Impact coefficients (simplified)
        eta = 2.5e-7 * (shares / avg_daily_volume) ** 0.5
        gamma = 1e-7

        return cls(
            total_shares=shares,
            shares_per_period=avg_daily_volume / periods_per_day,
            volatility=period_vol,
            spread=spread,
            alpha=0.0,
            eta=eta,
            lambda_=risk_aversion,
            gamma=gamma,
            sigma=period_vol,
            T=total_periods,
            start_price=price,
        )


@dataclass
class TradeSchedule:
    """An execution schedule"""
    periods: List[int]            # Time periods (0 to T)
    holdings: np.ndarray          # Shares remaining at each period
    trade_sizes: np.ndarray       # Shares traded at each period
    prices: np.ndarray            # Expected execution prices
    costs: np.ndarray             # Execution costs
    total_cost: float             # Total implementation shortfall

    @property
    def avg_price(self) -> float:
        """Volume-weighted average execution price"""
        total_traded = np.sum(self.trade_sizes)
        if total_traded == 0:
            return 0.0
        return float(np.sum(self.trade_sizes * self.prices) / total_traded)

    @property
    def implementation_shortfall(self) -> float:
        """Implementation shortfall vs arrival price"""
        return float(self.total_cost)


@dataclass
class ExecutionResult:
    schedule: TradeSchedule
    params: ExecutionParams
    strategy: str
    total_cost: float
    avg_price: float
    market_impact: float           # Total market impact cost
    timing_risk: float             # Timing/price risk cost
    slippage: float                # Realized slippage
    metrics: Dict[str, float] = field(default_factory=dict)


class AlmgrenChriss:
    """
    Full Almgren-Chriss optimal execution implementation.

    Strategies:
    - TWAP: Time-Weighted Average Price (uniform execution)
    - VWAP: Volume-Weighted Average Price (volume profile)
    - IS: Implementation Shortfall (Almgren-Chriss optimal)
    - Adaptive: Real-time adaptive schedule
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def twap(self, params: ExecutionParams) -> ExecutionResult:
        """TWAP: Uniform execution across all periods"""
        trade_size = params.total_shares / params.T
        holdings = params.total_shares - np.cumsum(np.full(params.T, trade_size))
        holdings = np.insert(holdings, 0, params.total_shares)[:-1]

        return self._compute_schedule(
            params=params,
            trade_sizes=np.full(params.T, trade_size),
            holdings=holdings,
            strategy="TWAP",
        )

    def vwap(self, params: ExecutionParams,
              volume_profile: Optional[np.ndarray] = None) -> ExecutionResult:
        """VWAP: Execution proportional to expected volume"""
        if volume_profile is None:
            volume_profile = np.ones(params.T) / params.T
        else:
            volume_profile = np.asarray(volume_profile, dtype=float)
            volume_profile = volume_profile / np.sum(volume_profile)

        trade_sizes = params.total_shares * volume_profile
        holdings = params.total_shares - np.cumsum(trade_sizes)
        holdings = np.insert(holdings, 0, params.total_shares)[:params.T]

        return self._compute_schedule(
            params=params,
            trade_sizes=trade_sizes,
            holdings=holdings,
            strategy="VWAP",
        )

    def implementation_shortfall(self, params: ExecutionParams) -> ExecutionResult:
        """Almgren-Chriss optimal Implementation Shortfall execution"""
        T, X = params.T, params.total_shares
        eta, lam, sigma, gamma = params.eta, params.lambda_, params.sigma, params.gamma
        spread = params.spread

        # Optimal trajectory
        kappa = np.sqrt(lam * sigma ** 2 / eta)

        if kappa * T < 1e-10:
            # Zero risk aversion -> TWAP
            return self.twap(params)

        # Almgren-Chriss optimal holdings trajectory
        t = np.arange(T + 1)
        numerator = np.sinh(kappa * (T - t))
        denominator = np.sinh(kappa * T)
        holdings = X * numerator / denominator

        trade_sizes = -np.diff(holdings)
        holdings = holdings[:-1]

        return self._compute_schedule(
            params=params,
            trade_sizes=trade_sizes,
            holdings=holdings,
            strategy="IS",
        )

    def adaptive(self, params: ExecutionParams,
                  price_updates: Optional[np.ndarray] = None,
                  volume_updates: Optional[np.ndarray] = None) -> ExecutionResult:
        """Adaptive execution schedule that re-optimizes"""
        if price_updates is not None:
            # Adjust schedule based on observed prices
            # Simplified: recompute IS with remaining shares
            remaining_shares = params.total_shares
            remaining_periods = params.T
            total_shares_executed = 0
            trade_sizes = np.zeros(params.T)

            for i in range(params.T):
                if remaining_periods <= 1:
                    trade_sizes[i] = remaining_shares
                else:
                    # Re-optimize for remaining
                    adj_params = ExecutionParams(
                        total_shares=remaining_shares,
                        shares_per_period=params.shares_per_period,
                        volatility=params.volatility,
                        spread=params.spread,
                        alpha=params.alpha,
                        eta=params.eta,
                        lambda_=params.lambda_,
                        gamma=params.gamma,
                        sigma=params.sigma,
                        T=remaining_periods,
                        start_price=price_updates[i] if i < len(price_updates) else params.start_price,
                    )
                    kappa = np.sqrt(params.lambda_ * params.sigma ** 2 / params.eta)
                    t = 1
                    trade_size = adj_params.total_shares * (
                        1 - np.sinh(kappa * (remaining_periods - 1)) / np.sinh(kappa * remaining_periods)
                    )
                    trade_sizes[i] = max(0, trade_size)

                total_shares_executed += trade_sizes[i]
                remaining_shares -= trade_sizes[i]
                remaining_periods -= 1

            holdings = params.total_shares - np.cumsum(trade_sizes)
            holdings = np.insert(holdings, 0, params.total_shares)[:params.T]

            return self._compute_schedule(
                params=params,
                trade_sizes=trade_sizes,
                holdings=holdings,
                strategy="Adaptive",
            )

        return self.implementation_shortfall(params)

    def _compute_schedule(self, params: ExecutionParams,
                           trade_sizes: np.ndarray,
                           holdings: np.ndarray,
                           strategy: str) -> ExecutionResult:
        """Compute execution costs for a given trade schedule"""
        T = len(trade_sizes)
        S0 = params.start_price
        sigma = params.sigma
        eta = params.eta
        gamma = params.gamma
        alpha = params.alpha

        prices = np.zeros(T)
        costs = np.zeros(T)

        for i in range(T):
            # Permanent impact from all trades so far
            perm_impact = gamma * (params.total_shares - holdings[i] if i < len(holdings) else 0)

            # Temporary impact from current trade
            trade_rate = trade_sizes[i] / params.shares_per_period
            temp_impact = eta * trade_sizes[i] * trade_rate

            # Expected price with drift and impact
            drift = alpha * i * S0
            prices[i] = S0 + drift + perm_impact - temp_impact

            # Cost = shares * (price impact + spread)
            costs[i] = trade_sizes[i] * (temp_impact + params.spread * S0)

        total_cost = float(np.sum(costs))

        # Market impact cost (permanent + temporary)
        market_impact = float(np.sum(trade_sizes * (eta * trade_sizes / params.shares_per_period + gamma * holdings)))

        # Timing risk (volatility cost)
        timing_risk = float(alpha * S0 * np.sum(trade_sizes * np.arange(T)))

        # Slippage
        slippage = float(np.sum(trade_sizes) * S0 - np.sum(trade_sizes * prices))

        schedule = TradeSchedule(
            periods=list(range(T)),
            holdings=holdings,
            trade_sizes=trade_sizes,
            prices=prices,
            costs=costs,
            total_cost=total_cost,
        )

        return ExecutionResult(
            schedule=schedule,
            params=params,
            strategy=strategy,
            total_cost=total_cost,
            avg_price=schedule.avg_price,
            market_impact=market_impact,
            timing_risk=timing_risk,
            slippage=slippage,
            metrics={
                "total_shares": params.total_shares,
                "avg_price": schedule.avg_price,
                "total_cost": total_cost,
                "cost_per_share": total_cost / max(params.total_shares, 1),
                "bps_cost": total_cost / (params.total_shares * S0) * 10000,
                "market_impact_bps": market_impact / (params.total_shares * S0) * 10000,
                "timing_risk_bps": timing_risk / (params.total_shares * S0) * 10000,
            },
        )

    def compare_strategies(self, params: ExecutionParams,
                            volume_profile: Optional[np.ndarray] = None) -> Dict[str, ExecutionResult]:
        """Compare all execution strategies"""
        return {
            "TWAP": self.twap(params),
            "VWAP": self.vwap(params, volume_profile),
            "IS": self.implementation_shortfall(params),
        }


class ExecutionSimulator:
    """
    Simulates execution of trade schedules with random price paths.
    Used to test robustness of execution strategies.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.rng = np.random.default_rng(self.config.get("seed", 42))

    def simulate(self, schedule: TradeSchedule, params: ExecutionParams,
                   n_simulations: int = 1000) -> Dict[str, Any]:
        """Simulate execution with random price paths"""
        S0 = params.start_price
        sigma = params.sigma

        final_costs = []
        final_prices = []

        for _ in range(n_simulations):
            price_path = S0 * np.exp(np.cumsum(self.rng.normal(0, sigma, len(schedule.trade_sizes))))

            sim_cost = np.sum(schedule.trade_sizes * (price_path - S0))
            final_costs.append(sim_cost)
            final_prices.append(price_path[-1])

        final_costs = np.array(final_costs)

        return {
            "expected_cost": float(np.mean(final_costs)),
            "cost_std": float(np.std(final_costs)),
            "var_95": float(np.percentile(final_costs, 5)),
            "var_99": float(np.percentile(final_costs, 1)),
            "max_cost": float(np.max(final_costs)),
            "min_cost": float(np.min(final_costs)),
            "expected_final_price": float(np.mean(final_prices)),
        }


# Convenience function
def optimal_execution_schedule(shares: float, price: float,
                                 avg_daily_volume: float, days: int = 5,
                                 risk_aversion: float = 1e-6,
                                 strategy: str = "IS") -> TradeSchedule:
    """One-liner to get optimal execution schedule"""
    params = ExecutionParams.from_market_data(
        shares=shares, avg_daily_volume=avg_daily_volume,
        price=price, days=days, risk_aversion=risk_aversion,
    )
    model = AlmgrenChriss()

    strategies = {
        "TWAP": model.twap,
        "VWAP": model.vwap,
        "IS": model.implementation_shortfall,
        "Adaptive": model.adaptive,
    }

    executor = strategies.get(strategy, model.implementation_shortfall)
    result = executor(params)
    return result.schedule
