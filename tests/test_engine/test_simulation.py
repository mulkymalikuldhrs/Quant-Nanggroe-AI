"""Tests for the simulation engine module.

Tests Monte Carlo simulation, stress testing, and paper trading
with deterministic seeds for reproducibility.
"""

import math
from datetime import datetime

import pytest

from quant_nanggroe.engine.simulation import (
    MonteCarloSimulator,
)


@pytest.mark.skip(reason="removed in df4c21f — needs rewrite")
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
    """Tests for Monte Carlo simulation engine using new API.

    The MonteCarloSimulator now operates on actual trade/return data
    via simulate_trade_shuffle, simulate_parametric, etc.
    """

    def test_basic_trade_shuffle(self):
        """Basic trade shuffle simulation produces valid results."""
        trades_pnl = [100.0, -50.0, 200.0, -30.0, 150.0] * 20  # 100 trades
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100000.0)

        assert result.num_simulations == 100
        assert result.metric_name == "total_return"
        assert result.mean_value != 0.0
        assert result.median_value != 0.0
        assert 0.0 <= result.probability_of_loss <= 1.0

    def test_deterministic_with_seed(self):
        """Same seed produces same results."""
        trades_pnl = [100.0, -50.0, 200.0] * 10
        sim = MonteCarloSimulator(num_simulations=50, random_seed=12345)
        result1 = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100000.0)
        result2 = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100000.0)

        assert result1.mean_value == result2.mean_value
        assert result1.p5 == result2.p5
        assert result1.p95 == result2.p95
        assert result1.probability_of_loss == result2.probability_of_loss

    def test_percentile_order(self):
        """Percentiles are correctly ordered: p5 <= p25 <= median <= p75 <= p95."""
        trades_pnl = [100.0, -50.0, 200.0, -30.0, 150.0] * 20
        sim = MonteCarloSimulator(num_simulations=200, random_seed=42)
        result = sim.simulate_trade_shuffle(trades_pnl, initial_capital=100000.0)

        assert result.p5 <= result.p25
        assert result.p25 <= result.median_value
        assert result.median_value <= result.p75
        assert result.p75 <= result.p95

    def test_probability_of_loss_increases_with_volatility(self):
        """Higher volatility should increase probability of loss."""
        import pandas as pd

        sim = MonteCarloSimulator(num_simulations=200, random_seed=42)

        # Low volatility returns
        returns_low = pd.Series([0.005, -0.003, 0.004] * 50)
        result_low = sim.simulate_parametric(returns_low, initial_capital=100000.0)

        # High volatility returns
        returns_high = pd.Series([0.05, -0.08, 0.06, -0.10, 0.03] * 30)
        result_high = sim.simulate_parametric(returns_high, initial_capital=100000.0)

        assert result_high.probability_of_loss > result_low.probability_of_loss

    def test_higher_volatility_wider_distribution(self):
        """Higher volatility produces wider distribution of results."""
        import pandas as pd

        sim = MonteCarloSimulator(num_simulations=200, random_seed=42)

        # Low volatility returns
        returns_low = pd.Series([0.001] * 200)
        result_low = sim.simulate_parametric(returns_low, initial_capital=100000.0)

        # High volatility returns
        returns_high = pd.Series([0.01, -0.01, 0.02, -0.02, 0.005] * 40)
        result_high = sim.simulate_parametric(returns_high, initial_capital=100000.0)

        range_low = result_low.p95 - result_low.p5
        range_high = result_high.p95 - result_high.p5

        assert range_high > range_low

    def test_parametric_normal(self):
        """Parametric simulation with normal distribution works."""
        import pandas as pd

        returns = pd.Series([0.001, -0.002, 0.003, -0.001, 0.002] * 50)
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = sim.simulate_parametric(returns, initial_capital=100000.0)

        assert result.num_simulations == 100
        assert result.metric_name == "total_return"
        assert result.mean_value != 0.0

    def test_bootstrap_resampling(self):
        """Bootstrap resampling produces valid results."""
        import pandas as pd

        returns = pd.Series([0.001, -0.002, 0.003, -0.001, 0.002] * 50)
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = sim.simulate_bootstrap(returns, initial_capital=100000.0)

        assert result.num_simulations == 100
        assert result.mean_value != 0.0

    def test_empty_trades_returns_empty_result(self):
        """Empty trades list returns an empty result (no simulation)."""
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = sim.simulate_trade_shuffle([], initial_capital=100000.0)

        assert result.num_simulations == 0
        assert result.probability_of_loss == 1.0

    def test_constant_returns_deterministic(self):
        """Constant returns (zero std) produce deterministic results."""
        import pandas as pd

        returns = pd.Series([0.001] * 100)
        sim = MonteCarloSimulator(num_simulations=100, random_seed=42)
        result = sim.simulate_parametric(returns, initial_capital=100000.0)

        # With zero volatility all simulations produce identical results
        assert result.mean_value == pytest.approx(result.median_value, rel=1e-10)


@pytest.mark.skip(reason="removed in df4c21f — needs rewrite")
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


@pytest.mark.skip(reason="removed in df4c21f — needs rewrite for PaperBroker API")
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


@pytest.mark.skip(reason="removed in df4c21f — needs rewrite")
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
