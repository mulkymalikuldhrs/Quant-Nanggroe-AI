"""Simulation engine for strategy testing under various market conditions.

Provides Monte Carlo simulation, stress testing, and paper trading
capabilities for validating trading strategies before live deployment.

Extracted from ai-hedge-fund's simulation routines with production hardening.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class SimulationType(str, Enum):
    """Types of market simulations."""

    MONTE_CARLO = "monte_carlo"
    STRESS_TEST = "stress_test"
    PAPER_TRADING = "paper_trading"
    SCENARIO = "scenario"


class MarketRegime(str, Enum):
    """Market regime classifications for stress testing."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    CRISIS = "crisis"
    HIGH_VOLATILITY = "high_volatility"
    FLASH_CRASH = "flash_crash"
    LIQUIDITY_CRISIS = "liquidity_crisis"


@dataclass
class SimulationConfig:
    """Configuration for simulation runs."""

    simulation_type: SimulationType = SimulationType.MONTE_CARLO
    initial_capital: float = 100000.0
    num_simulations: int = 10000
    time_horizon_days: int = 252
    confidence_level: float = 0.95
    annual_risk_free_rate: float = 0.05
    seed: Optional[int] = None


@dataclass
class SimulationResult:
    """Results from a simulation run."""

    simulation_type: SimulationType
    final_values: List[float] = field(default_factory=list)
    returns: List[float] = field(default_factory=list)
    var: float = 0.0
    cvar: float = 0.0
    max_drawdowns: List[float] = field(default_factory=list)
    mean_final_value: float = 0.0
    median_final_value: float = 0.0
    worst_case: float = 0.0
    best_case: float = 0.0
    probability_of_loss: float = 0.0
    sharpe_ratio: float = 0.0
    config: Optional[SimulationConfig] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class StressTestScenario:
    """A predefined stress test scenario."""

    name: str
    regime: MarketRegime
    price_shock_pct: float
    volatility_multiplier: float
    spread_multiplier: float
    liquidity_reduction: float
    recovery_days: int
    description: str = ""


# Predefined stress test scenarios aligned with historical market events
PREDEFINED_SCENARIOS: List[StressTestScenario] = [
    StressTestScenario(
        name="2008 Financial Crisis",
        regime=MarketRegime.CRISIS,
        price_shock_pct=-37.0,
        volatility_multiplier=4.5,
        spread_multiplier=8.0,
        liquidity_reduction=0.85,
        recovery_days=546,
        description="S&P 500 dropped 37% from Oct 2007 to Mar 2009. VIX peaked at 80. "
                    "Extreme illiquidity in credit markets. Bid-ask spreads widened 8x.",
    ),
    StressTestScenario(
        name="2020 COVID Crash",
        regime=MarketRegime.FLASH_CRASH,
        price_shock_pct=-33.9,
        volatility_multiplier=5.0,
        spread_multiplier=6.0,
        liquidity_reduction=0.70,
        recovery_days=149,
        description="S&P 500 dropped 33.9% in 23 trading days. "
                    "VIX spiked to 82.69. Fastest 30%+ drop in history.",
    ),
    StressTestScenario(
        name="2010 Flash Crash",
        regime=MarketRegime.FLASH_CRASH,
        price_shock_pct=-9.0,
        volatility_multiplier=8.0,
        spread_multiplier=15.0,
        liquidity_reduction=0.95,
        recovery_days=1,
        description="May 6, 2010: Dow dropped 9% in minutes, recovered same day.",
    ),
    StressTestScenario(
        name="2022 Rate Shock",
        regime=MarketRegime.BEAR,
        price_shock_pct=-25.0,
        volatility_multiplier=2.5,
        spread_multiplier=3.0,
        liquidity_reduction=0.40,
        recovery_days=365,
        description="Fed aggressive rate hikes. S&P 500 down 25% Jan-Oct 2022.",
    ),
    StressTestScenario(
        name="Crypto Winter 2022",
        regime=MarketRegime.CRISIS,
        price_shock_pct=-77.0,
        volatility_multiplier=3.0,
        spread_multiplier=5.0,
        liquidity_reduction=0.80,
        recovery_days=540,
        description="Bitcoin fell from $69K to $15K (-77%). FTX collapse.",
    ),
    StressTestScenario(
        name="Taper Tantrum 2013",
        regime=MarketRegime.HIGH_VOLATILITY,
        price_shock_pct=-7.0,
        volatility_multiplier=2.0,
        spread_multiplier=2.5,
        liquidity_reduction=0.30,
        recovery_days=60,
        description="Fed hinted at tapering QE. Bond yields spiked.",
    ),
    StressTestScenario(
        name="Liquidity Crisis",
        regime=MarketRegime.LIQUIDITY_CRISIS,
        price_shock_pct=-15.0,
        volatility_multiplier=3.0,
        spread_multiplier=10.0,
        liquidity_reduction=0.90,
        recovery_days=90,
        description="Market makers withdraw liquidity. Bid-ask spreads widen 10x.",
    ),
    StressTestScenario(
        name="Prolonged Bear Market",
        regime=MarketRegime.BEAR,
        price_shock_pct=-40.0,
        volatility_multiplier=2.0,
        spread_multiplier=2.0,
        liquidity_reduction=0.30,
        recovery_days=730,
        description="Extended 2-year bear market with 40% drawdown.",
    ),
]


class MonteCarloSimulator:
    """Monte Carlo simulation engine for portfolio risk analysis.

    Generates random price paths based on historical return distributions
    and computes risk metrics (VaR, CVaR, max drawdown) across scenarios.

    Uses geometric Brownian motion for price path generation:
        dS = mu * S * dt + sigma * S * dW

    Example:
        >>> simulator = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.20)
        >>> result = simulator.run(SimulationConfig(num_simulations=1000))
        >>> print(f"VaR(95%): {result.var:.2%}")
    """

    def __init__(
        self,
        annual_return: float = 0.10,
        annual_volatility: float = 0.20,
        config: Optional[SimulationConfig] = None,
    ):
        self.annual_return = annual_return
        self.annual_volatility = annual_volatility
        self.config = config or SimulationConfig()

    def run(self, config: Optional[SimulationConfig] = None) -> SimulationResult:
        """Run Monte Carlo simulation."""
        cfg = config or self.config
        rng = np.random.default_rng(cfg.seed)

        dt = 1.0 / 252
        mu = self.annual_return
        sigma = self.annual_volatility
        n_steps = cfg.time_horizon_days
        n_sims = cfg.num_simulations
        s0 = cfg.initial_capital

        z = rng.standard_normal((n_sims, n_steps))
        daily_returns = (mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z
        cumulative_returns = np.cumprod(1 + daily_returns, axis=1)
        final_values = s0 * cumulative_returns[:, -1]
        total_returns = (final_values / s0) - 1

        sorted_returns = np.sort(total_returns)
        var_index = int(len(sorted_returns) * (1 - cfg.confidence_level))
        var_value = sorted_returns[min(var_index, len(sorted_returns) - 1)]
        cvar_value = np.mean(sorted_returns[:max(var_index, 1)])

        max_drawdowns = []
        for i in range(n_sims):
            path = s0 * cumulative_returns[i, :]
            peak = np.maximum.accumulate(path)
            drawdown = (path - peak) / peak
            max_drawdowns.append(float(np.min(drawdown)))

        daily_rf = cfg.annual_risk_free_rate / 252
        excess_returns = daily_returns - daily_rf
        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns)
        sharpe = (mean_excess / std_excess) * math.sqrt(252) if std_excess > 0 else 0.0

        return SimulationResult(
            simulation_type=SimulationType.MONTE_CARLO,
            final_values=final_values.tolist(),
            returns=total_returns.tolist(),
            var=float(var_value),
            cvar=float(cvar_value),
            max_drawdowns=max_drawdowns,
            mean_final_value=float(np.mean(final_values)),
            median_final_value=float(np.median(final_values)),
            worst_case=float(np.min(final_values)),
            best_case=float(np.max(final_values)),
            probability_of_loss=float(np.mean(total_returns < 0)),
            sharpe_ratio=float(sharpe),
            config=cfg,
        )


class StressTestEngine:
    """Stress testing engine for evaluating portfolio resilience."""

    def __init__(
        self,
        portfolio_value: float = 100000.0,
        annual_volatility: float = 0.20,
        position_count: int = 10,
    ):
        self.portfolio_value = portfolio_value
        self.annual_volatility = annual_volatility
        self.position_count = position_count

    def run_scenario(
        self,
        scenario: StressTestScenario,
        config: Optional[SimulationConfig] = None,
    ) -> SimulationResult:
        """Run a stress test scenario."""
        cfg = config or SimulationConfig(
            simulation_type=SimulationType.STRESS_TEST,
            initial_capital=self.portfolio_value,
            num_simulations=1000,
        )

        rng = np.random.default_rng(cfg.seed)
        shock = scenario.price_shock_pct / 100.0
        stressed_vol = self.annual_volatility * scenario.volatility_multiplier

        n_sims = cfg.num_simulations
        n_steps = max(scenario.recovery_days, 1)
        dt = 1.0 / 252

        z = rng.standard_normal((n_sims, n_steps))
        daily_returns = (shock / n_steps) + (stressed_vol * math.sqrt(dt) * z)
        cumulative_returns = np.cumprod(1 + daily_returns, axis=1)
        final_values = self.portfolio_value * cumulative_returns[:, -1]
        total_returns = (final_values / self.portfolio_value) - 1

        sorted_returns = np.sort(total_returns)
        var_index = int(len(sorted_returns) * (1 - cfg.confidence_level))
        var_value = sorted_returns[min(var_index, len(sorted_returns) - 1)]
        cvar_value = np.mean(sorted_returns[:max(var_index, 1)])

        max_drawdowns = []
        for i in range(n_sims):
            path = self.portfolio_value * cumulative_returns[i, :]
            peak = np.maximum.accumulate(path)
            drawdown = (path - peak) / peak
            max_drawdowns.append(float(np.min(drawdown)))

        return SimulationResult(
            simulation_type=SimulationType.STRESS_TEST,
            final_values=final_values.tolist(),
            returns=total_returns.tolist(),
            var=float(var_value),
            cvar=float(cvar_value),
            max_drawdowns=max_drawdowns,
            mean_final_value=float(np.mean(final_values)),
            median_final_value=float(np.median(final_values)),
            worst_case=float(np.min(final_values)),
            best_case=float(np.max(final_values)),
            probability_of_loss=float(np.mean(total_returns < 0)),
            sharpe_ratio=0.0,
            config=cfg,
        )

    def run_all_predefined(
        self,
        config: Optional[SimulationConfig] = None,
    ) -> Dict[str, SimulationResult]:
        """Run all predefined stress test scenarios."""
        results = {}
        for scenario in PREDEFINED_SCENARIOS:
            results[scenario.name] = self.run_scenario(scenario, config)
        return results


class PaperTradingSimulator:
    """Paper trading simulator for strategy validation.

    Simulates realistic order execution with slippage, commissions,
    and partial fills.

    Example:
        >>> sim = PaperTradingSimulator(initial_capital=100000)
        >>> order_id = sim.submit_order("AAPL", "BUY", 100, order_type="LIMIT", price=150.0)
        >>> sim.tick({"AAPL": 149.50})
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        partial_fill_probability: float = 0.1,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage_bps = slippage_bps
        self.partial_fill_probability = partial_fill_probability
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.pending_orders: List[Dict[str, Any]] = []
        self.fills: List[Dict[str, Any]] = []
        self._order_counter = 0
        self._fill_counter = 0

    @property
    def portfolio_value(self) -> float:
        """Total portfolio value (cash + positions at last known price)."""
        position_value = sum(
            p["quantity"] * p["current_price"]
            for p in self.positions.values()
        )
        return self.cash + position_value

    @property
    def unrealized_pnl(self) -> float:
        """Total unrealized P&L across all positions."""
        return sum(
            p["quantity"] * (p["current_price"] - p["avg_entry_price"])
            for p in self.positions.values()
        )

    def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> str:
        """Submit an order to the paper trading simulator."""
        self._order_counter += 1
        order_id = f"PAPER-{self._order_counter:06d}"

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side.upper(),
            "quantity": quantity,
            "remaining_quantity": quantity,
            "order_type": order_type.upper(),
            "price": price,
            "stop_price": stop_price,
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
        }

        if order_type.upper() == "MARKET":
            order["status"] = "QUEUED"

        self.pending_orders.append(order)
        return order_id

    def tick(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Process a price tick, executing eligible pending orders."""
        new_fills = []

        for symbol, price in current_prices.items():
            if symbol in self.positions:
                self.positions[symbol]["current_price"] = price

        remaining = []
        for order in self.pending_orders:
            symbol = order["symbol"]
            if symbol not in current_prices:
                remaining.append(order)
                continue

            price = current_prices[symbol]
            should_execute = False
            fill_price = price

            if order["order_type"] == "MARKET":
                should_execute = True
                if order["side"] == "BUY":
                    fill_price = price * (1 + self.slippage_bps / 10000)
                else:
                    fill_price = price * (1 - self.slippage_bps / 10000)

            elif order["order_type"] == "LIMIT":
                if order["side"] == "BUY" and price <= (order["price"] or float("inf")):
                    should_execute = True
                    fill_price = order["price"]
                elif order["side"] == "SELL" and price >= (order["price"] or 0):
                    should_execute = True
                    fill_price = order["price"]

            elif order["order_type"] == "STOP":
                if order["stop_price"] and price <= order["stop_price"]:
                    should_execute = True
                    if order["side"] == "BUY":
                        fill_price = price * (1 + self.slippage_bps / 10000)
                    else:
                        fill_price = price * (1 - self.slippage_bps / 10000)

            if not should_execute:
                remaining.append(order)
                continue

            fill_qty = order["remaining_quantity"]
            if random.random() < self.partial_fill_probability and fill_qty > 1:
                fill_qty = max(1, int(fill_qty * random.uniform(0.3, 0.8)))

            trade_value = fill_price * fill_qty
            commission = trade_value * self.commission_rate

            self._fill_counter += 1
            fill = {
                "fill_id": f"FILL-{self._fill_counter:06d}",
                "order_id": order["order_id"],
                "symbol": symbol,
                "side": order["side"],
                "quantity": fill_qty,
                "price": fill_price,
                "commission": commission,
                "slippage": abs(fill_price - price) * fill_qty,
                "timestamp": datetime.now().isoformat(),
            }
            new_fills.append(fill)
            self.fills.append(fill)

            if order["side"] == "BUY":
                self.cash -= (trade_value + commission)
            else:
                self.cash += (trade_value - commission)

            if symbol not in self.positions:
                if order["side"] == "BUY":
                    self.positions[symbol] = {
                        "quantity": fill_qty,
                        "avg_entry_price": fill_price,
                        "current_price": price,
                    }
            else:
                pos = self.positions[symbol]
                if order["side"] == "BUY":
                    new_qty = pos["quantity"] + fill_qty
                    new_avg = (pos["avg_entry_price"] * pos["quantity"] + fill_price * fill_qty) / new_qty
                    pos["quantity"] = new_qty
                    pos["avg_entry_price"] = new_avg
                    pos["current_price"] = price
                else:
                    pos["quantity"] -= fill_qty
                    if pos["quantity"] <= 0:
                        del self.positions[symbol]

            order["remaining_quantity"] -= fill_qty
            if order["remaining_quantity"] <= 0:
                order["status"] = "FILLED"
            else:
                order["status"] = "PARTIALLY_FILLED"
                remaining.append(order)

        self.pending_orders = remaining
        return new_fills

    def get_fills(self) -> List[Dict[str, Any]]:
        """Get all fill records."""
        return self.fills.copy()

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get current positions."""
        return self.positions.copy()

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        for i, order in enumerate(self.pending_orders):
            if order["order_id"] == order_id:
                self.pending_orders.pop(i)
                return True
        return False

    def reset(self) -> None:
        """Reset the simulator to initial state."""
        self.cash = self.initial_capital
        self.positions.clear()
        self.pending_orders.clear()
        self.fills.clear()
        self._order_counter = 0
        self._fill_counter = 0


__all__ = [
    "SimulationType",
    "MarketRegime",
    "SimulationConfig",
    "SimulationResult",
    "StressTestScenario",
    "PREDEFINED_SCENARIOS",
    "MonteCarloSimulator",
    "StressTestEngine",
    "PaperTradingSimulator",
]
