# engine.simulation.__init__

## Class: 

Types of market simulations.

*Line: 24*

---

## Class: 

Market regime classifications for stress testing.

*Line: 33*

---

## Class: 

Configuration for simulation runs.

*Line: 46*

---

## Class: 

Results from a simulation run.

*Line: 59*

---

## Class: 

A predefined stress test scenario.

*Line: 79*

---

## Class: 

Monte Carlo simulation engine for portfolio risk analysis.

Generates random price paths based on historical return distributions
and computes risk metrics (VaR, CVaR, max drawdown) across scenarios.

Uses geometric Brownian motion for price path generation:
    dS = mu * S * dt + sigma * S * dW

Example:
    >>> simulator = MonteCarloSimulator(annual_return=0.10, annual_volatility=0.20)
    >>> result = simulator.run(SimulationConfig(num_simulations=1000))
    >>> print(f"VaR(95%): {result.var:.2%}")

**Methods:** __init__, run

*Line: 179*

---

## Class: 

Stress testing engine for evaluating portfolio resilience.

**Methods:** __init__, run_scenario, run_all_predefined

*Line: 257*

---

## Class: 

Paper trading simulator for strategy validation.

Simulates realistic order execution with slippage, commissions,
and partial fills.

Example:
    >>> sim = PaperTradingSimulator(initial_capital=100000)
    >>> order_id = sim.submit_order("AAPL", "BUY", 100, order_type="LIMIT", price=150.0)
    >>> sim.tick({"AAPL": 149.50})

**Methods:** __init__, portfolio_value, unrealized_pnl, submit_order, tick, get_fills, get_positions, cancel_order, reset

*Line: 335*

---

## Function: 

*Line: 194*

---

## Function: 

Run Monte Carlo simulation.

*Line: 204*

---

## Function: 

*Line: 260*

---

## Function: 

Run a stress test scenario.

*Line: 270*

---

## Function: 

Run all predefined stress test scenarios.

*Line: 324*

---

## Function: 

*Line: 347*

---

## Function: 

Total portfolio value (cash + positions at last known price).

*Line: 366*

---

## Function: 

Total unrealized P&L across all positions.

*Line: 375*

---

## Function: 

Submit an order to the paper trading simulator.

*Line: 382*

---

## Function: 

Process a price tick, executing eligible pending orders.

*Line: 414*

---

## Function: 

Get all fill records.

*Line: 517*

---

## Function: 

Get current positions.

*Line: 521*

---

## Function: 

Cancel a pending order.

*Line: 525*

---

## Function: 

Reset the simulator to initial state.

*Line: 533*

---

