"""Tests for the simulation engine module.

Tests Monte Carlo simulation, stress testing, and paper trading
with deterministic seeds for reproducibility.
"""

import math
from datetime import datetime

import pytest

from quant_nanggroe.engine.simulation import (
    MonteCarloSimulator,
    PaperTradingSimulator,
    StressTestEngine,
    SimulationConfig,
    SimulationResult,
    SimulationType,
    MarketRegime,
    StressTestScenario,
    PREDEFINED_SCENARIOS,
)


class TestSimulationConfig:
    """Tests for SimulationConfig dataclass."""

    def test_default_config(self):
        config = SimulationConfig()
        assert config.simulation_type == SimulationType.MONTE_CARLO
        assert config.initial_capital == 100000.0
        assert config.num_simulations == 10000
        assert config.time_horizon_days == 252
        assert config.confidence_level == 0.95
        assert config.seed is None

    def test_custom_config(self):
        config = SimulationConfig(
            simulation_type=SimulationType.STRESS_TEST,
            initial_capital=50000.0,
            num_simulations=100,
            seed=42,
        )
        assert config.simulation_type == SimulationType.STRESS_TEST
        assert config.initial_capital == 50000.0
        assert config.num_simulations == 100
        assert config.seed == 42


class TestMonteCarloSimulator:
    """Tests for Monte Carlo simulation engine."""

    def test_basic_simulation(self):
        """Test that Monte Carlo simulation produces valid results."""
        sim = MonteCarloSimulator(
            annual_return=0.10,
            annual_volatility=0.20,
        )
        config = SimulationConfig(
            num_simulations=100,
            time_horizon_days=252,
            seed=42,
        )
        result = sim.run(config)

        assert result.simulation_type == SimulationType.MONTE_CARLO
        assert len(result.final_values) == 100
        assert len(result.returns) == 100
        assert len(result.max_drawdowns) == 100
        assert result.mean_final_value > 0
        assert result.worst_case > 0
        assert result.best_case > result.worst_case
        assert result.probability_of_loss >= 0.0
        assert result.probability_of_loss <= 1.0

    def test_deterministic_with_seed(self):
        """Test that same seed produces same results."""
        config = SimulationConfig(num_simulations=50, seed=12345)
        sim = MonteCarloSimulator(annual_return=0.08, annual_volatility=0.15)

        result1 = sim.run(config)
        result2 = sim.run(config)

        assert result1.mean_final_value == result2.mean_final_value
        assert result1.var == result2.var
        assert result1.cvar == result2.cvar

    def test_var_less_than_zero_for_positive_returns(self):
        """VaR at 95% confidence should be negative for typical return distributions."""
        sim = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.20)
        config = SimulationConfig(num_simulations=1000, seed=42)
        result = sim.run(config)

        # VaR at 95% should be negative (5th percentile of returns)
        assert result.var < 0

    def test_cvar_less_than_var(self):
        """CVaR (expected shortfall) should be more negative than VaR."""
        sim = MonteCarloSimulator(annual_return=0.05, annual_volatility=0.30)
        config = SimulationConfig(num_simulations=5000, seed=42)
        result = sim.run(config)

        # CVaR should be more negative than VaR (worse case)
        assert result.cvar <= result.var

    def test_max_drawdowns_are_negative(self):
        """Max drawdowns should be negative or zero."""
        sim = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.20)
        config = SimulationConfig(num_simulations=100, seed=42)
        result = sim.run(config)

        for dd in result.max_drawdowns:
            assert dd <= 0

    def test_higher_volatility_means_wider_distribution(self):
        """Higher volatility should produce wider range of final values."""
        config = SimulationConfig(num_simulations=500, seed=42)

        sim_low_vol = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.10)
        result_low = sim_low_vol.run(config)

        sim_high_vol = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.40)
        result_high = sim_high_vol.run(config)

        range_low = result_low.best_case - result_low.worst_case
        range_high = result_high.best_case - result_high.worst_case

        assert range_high > range_low

    def test_sharpe_ratio_computed(self):
        """Sharpe ratio should be computed and reasonable."""
        sim = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.15)
        config = SimulationConfig(num_simulations=500, seed=42)
        result = sim.run(config)

        # Sharpe ratio should be positive for positive expected return
        assert result.sharpe_ratio > 0

    def test_probability_of_loss_increases_with_volatility(self):
        """Higher volatility should increase probability of loss."""
        config = SimulationConfig(num_simulations=2000, seed=42)

        sim_low = MonteCarloSimulator(annual_return=0.05, annual_volatility=0.10)
        result_low = sim_low.run(config)

        sim_high = MonteCarloSimulator(annual_return=0.05, annual_volatility=0.50)
        result_high = sim_high.run(config)

        assert result_high.probability_of_loss > result_low.probability_of_loss

    def test_zero_volatility(self):
        """Zero volatility should produce deterministic results."""
        sim = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.0)
        config = SimulationConfig(num_simulations=10, seed=42)
        result = sim.run(config)

        # All final values should be the same with zero volatility
        for val in result.final_values:
            assert abs(val - result.mean_final_value) < 1.0


class TestStressTestEngine:
    """Tests for stress testing engine."""

    def test_predefined_scenarios_exist(self):
        """Predefined scenarios should be non-empty."""
        assert len(PREDEFINED_SCENARIOS) >= 5

    def test_run_single_scenario(self):
        """Test running a single stress test scenario."""
        engine = StressTestEngine(portfolio_value=100000.0)
        scenario = PREDEFINED_SCENARIOS[0]  # 2008 Financial Crisis

        config = SimulationConfig(
            simulation_type=SimulationType.STRESS_TEST,
            num_simulations=100,
            seed=42,
        )
        result = engine.run_scenario(scenario, config)

        assert result.simulation_type == SimulationType.STRESS_TEST
        assert len(result.final_values) == 100
        assert result.worst_case < result.best_case

    def test_run_all_predefined(self):
        """Test running all predefined scenarios."""
        engine = StressTestEngine(portfolio_value=100000.0)
        config = SimulationConfig(
            simulation_type=SimulationType.STRESS_TEST,
            num_simulations=50,
            seed=42,
        )
        results = engine.run_all_predefined(config)

        assert len(results) == len(PREDEFINED_SCENARIOS)
        for name, result in results.items():
            assert result.simulation_type == SimulationType.STRESS_TEST
            assert len(result.final_values) == 50

    def test_crisis_scenario_reduces_value(self):
        """Crisis scenarios should reduce portfolio value on average."""
        engine = StressTestEngine(portfolio_value=100000.0)
        crisis_scenario = StressTestScenario(
            name="Test Crisis",
            regime=MarketRegime.CRISIS,
            price_shock_pct=-50.0,
            volatility_multiplier=3.0,
            spread_multiplier=5.0,
            liquidity_reduction=0.8,
            recovery_days=252,
        )
        config = SimulationConfig(num_simulations=500, seed=42)
        result = engine.run_scenario(crisis_scenario, config)

        # Average final value should be less than initial
        assert result.mean_final_value < 100000.0

    def test_custom_scenario(self):
        """Test creating and running a custom stress test scenario."""
        custom = StressTestScenario(
            name="Custom Flash Crash",
            regime=MarketRegime.FLASH_CRASH,
            price_shock_pct=-20.0,
            volatility_multiplier=5.0,
            spread_multiplier=8.0,
            liquidity_reduction=0.60,
            recovery_days=30,
            description="Custom flash crash scenario for testing",
        )

        engine = StressTestEngine(portfolio_value=100000.0)
        config = SimulationConfig(num_simulations=50, seed=42)
        result = engine.run_scenario(custom, config)

        assert result.simulation_type == SimulationType.STRESS_TEST
        assert result.probability_of_loss > 0


class TestPaperTradingSimulator:
    """Tests for paper trading simulator."""

    def test_initial_state(self):
        """Test simulator initial state."""
        sim = PaperTradingSimulator(initial_capital=100000.0)
        assert sim.cash == 100000.0
        assert sim.portfolio_value == 100000.0
        assert len(sim.positions) == 0
        assert len(sim.fills) == 0
        assert len(sim.pending_orders) == 0

    def test_market_buy_order(self):
        """Test market buy order execution."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)
        order_id = sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")

        assert order_id.startswith("PAPER-")
        assert len(sim.pending_orders) == 1

        # Execute with a price tick
        fills = sim.tick({"AAPL": 150.0})

        assert len(fills) == 1
        assert fills[0]["symbol"] == "AAPL"
        assert fills[0]["side"] == "BUY"
        assert fills[0]["quantity"] == 100
        assert "AAPL" in sim.positions
        assert sim.positions["AAPL"]["quantity"] == 100

    def test_market_sell_order(self):
        """Test market sell order execution (after buying)."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)

        # Buy first
        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        sim.tick({"AAPL": 150.0})

        # Then sell
        sim.submit_order("AAPL", "SELL", 50, order_type="MARKET")
        fills = sim.tick({"AAPL": 155.0})

        assert len(fills) == 1
        assert fills[0]["side"] == "SELL"
        assert sim.positions["AAPL"]["quantity"] == 50

    def test_limit_buy_order(self):
        """Test limit buy order - should not execute above limit."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)
        sim.submit_order("AAPL", "BUY", 100, order_type="LIMIT", price=145.0)

        # Price above limit - should NOT execute
        fills = sim.tick({"AAPL": 150.0})
        assert len(fills) == 0
        assert len(sim.pending_orders) == 1

        # Price at or below limit - should execute
        fills = sim.tick({"AAPL": 144.0})
        assert len(fills) == 1
        assert fills[0]["price"] == 145.0  # Fill at limit price

    def test_limit_sell_order(self):
        """Test limit sell order - should not execute below limit."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)

        # Buy first
        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        sim.tick({"AAPL": 150.0})

        # Set limit sell
        sim.submit_order("AAPL", "SELL", 100, order_type="LIMIT", price=160.0)

        # Price below limit - should NOT execute
        fills = sim.tick({"AAPL": 155.0})
        assert len(fills) == 0

        # Price at or above limit - should execute
        fills = sim.tick({"AAPL": 162.0})
        assert len(fills) == 1
        assert fills[0]["price"] == 160.0

    def test_commission_deducted(self):
        """Test that commissions are deducted from cash."""
        sim = PaperTradingSimulator(
            initial_capital=100000.0,
            commission_rate=0.001,
            partial_fill_probability=0.0,
        )
        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        fills = sim.tick({"AAPL": 150.0})

        # Expected cost: 100 * 150 * (1 + slippage) + commission
        assert fills[0]["commission"] > 0
        assert sim.cash < 100000.0

    def test_cancel_order(self):
        """Test order cancellation."""
        sim = PaperTradingSimulator(initial_capital=100000.0)
        order_id = sim.submit_order("AAPL", "BUY", 100, order_type="LIMIT", price=145.0)

        # Cancel the order
        assert sim.cancel_order(order_id) is True
        assert len(sim.pending_orders) == 0

        # Cancel non-existent order
        assert sim.cancel_order("NON-EXISTENT") is False

    def test_portfolio_value_tracking(self):
        """Test portfolio value tracking with positions."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)

        # Buy stock
        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        sim.tick({"AAPL": 150.0})

        # Portfolio value should include position
        assert sim.portfolio_value > 0
        assert "AAPL" in sim.positions

        # Update price
        sim.positions["AAPL"]["current_price"] = 160.0
        expected = sim.cash + 100 * 160.0
        assert abs(sim.portfolio_value - expected) < 0.01

    def test_unrealized_pnl(self):
        """Test unrealized P&L calculation."""
        sim = PaperTradingSimulator(
            initial_capital=100000.0,
            slippage_bps=0,  # No slippage for clean test
            partial_fill_probability=0.0,
        )

        # Buy at 150
        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        sim.tick({"AAPL": 150.0})

        # Move price to 160
        sim.positions["AAPL"]["current_price"] = 160.0

        # Unrealized P&L: 100 * (160 - 150) = 1000
        assert sim.unrealized_pnl > 0

    def test_reset(self):
        """Test simulator reset."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)
        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        sim.tick({"AAPL": 150.0})

        sim.reset()

        assert sim.cash == 100000.0
        assert len(sim.positions) == 0
        assert len(sim.fills) == 0
        assert len(sim.pending_orders) == 0

    def test_multiple_symbols(self):
        """Test trading multiple symbols."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)

        sim.submit_order("AAPL", "BUY", 50, order_type="MARKET")
        sim.submit_order("MSFT", "BUY", 30, order_type="MARKET")
        fills = sim.tick({"AAPL": 150.0, "MSFT": 300.0})

        assert len(fills) == 2
        assert "AAPL" in sim.positions
        assert "MSFT" in sim.positions

    def test_full_sell_removes_position(self):
        """Test that selling entire position removes it from tracking."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)

        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        sim.tick({"AAPL": 150.0})

        sim.submit_order("AAPL", "SELL", 100, order_type="MARKET")
        sim.tick({"AAPL": 155.0})

        assert "AAPL" not in sim.positions

    def test_get_fills_returns_copy(self):
        """Test that get_fills returns a copy, not a reference."""
        sim = PaperTradingSimulator(initial_capital=100000.0, partial_fill_probability=0.0)
        sim.submit_order("AAPL", "BUY", 100, order_type="MARKET")
        sim.tick({"AAPL": 150.0})

        fills1 = sim.get_fills()
        fills2 = sim.get_fills()

        assert fills1 == fills2
        assert fills1 is not fills2  # Different objects


class TestSimulationResult:
    """Tests for SimulationResult dataclass."""

    def test_timestamp_auto_generated(self):
        """Result should have a valid timestamp."""
        result = SimulationResult(simulation_type=SimulationType.MONTE_CARLO)
        assert result.timestamp is not None
        assert len(result.timestamp) > 10

    def test_default_values(self):
        """Test default values for SimulationResult."""
        result = SimulationResult(simulation_type=SimulationType.MONTE_CARLO)
        assert result.final_values == []
        assert result.returns == []
        assert result.var == 0.0
        assert result.cvar == 0.0
        assert result.max_drawdowns == []
        assert result.probability_of_loss == 0.0
