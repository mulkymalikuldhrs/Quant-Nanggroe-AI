# Task: NVIDIA NIM Integration + Replace Mock Data in API Routes

## Summary of Changes

### TASK 1: NVIDIA NIM Model Integration

#### File: `quant_nanggroe/engine/llm_router.py`
1. **Added `NVIDIA = "nvidia"` to `LLMProvider` enum** — NVIDIA is now the 5th provider option (between Google and Local)
2. **Added default model mappings** for NVIDIA in `_DEFAULT_MODELS`:
   - `deep_thinking`: `meta/llama-3.1-405b-instruct`
   - `standard`: `meta/llama-3.1-70b-instruct`
   - `quick`: `meta/llama-3.1-8b-instruct`
3. **Added cost estimates** for NVIDIA in `_COST_PER_1K`: `{"input": 0.002, "output": 0.006}`
4. **Added `_call_nvidia` static method** — Uses ChatOpenAI with `base_url` set to `https://integrate.api.nvidia.com/v1` (OpenAI-compatible API). Handles messages, token counting, and ImportError gracefully.
5. **Added NVIDIA case** in `_call_provider` dispatch method
6. **Updated docstring** to reflect the new 5-provider failover chain

#### File: `quant_nanggroe/config/settings.py`
1. **Added `nvidia_api_key: Optional[str] = None`** — Loaded from `QNAI_NVIDIA_API_KEY` env var
2. **Added `nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"`** — Default NVIDIA NIM base URL

---

### TASK 2: Replace Mock/Dummy Data in API Routes

#### File: `quant_nanggroe/api/routes/market.py`
- **`get_price()`**: Now uses `ExchangeManager.get_ticker()` to fetch real price data from exchange providers, returning `ticker.last_price` and `ticker.timestamp`. Falls back to `price=None` if no exchange is connected.
- **`get_ohlcv()`**: Now uses `ExchangeManager.get_ohlcv()` to fetch real OHLCV data, mapping string timeframes to the internal `TimeFrame` enum. Converts internal `OHLCV` model objects to `OHLCVCandle` schema objects.
- **`get_pressure()`**: Now computes real buy/sell pressure from `ExchangeManager.get_orderbook()`, summing bid/ask volumes and normalizing to 0-1 scale. Falls back to the `PressureNormalizationEngine`'s cached result when the order book is unavailable.

#### File: `quant_nanggroe/api/routes/trading.py`
- **`place_order()`**: Now submits orders through the `ExecutionManager` guard pipeline. Builds `Order` objects from the request, routes through cooldown/max-position/whitelist guards, and returns FILLED/REJECTED/ERROR status based on the result.
- **`get_positions()`**: Now queries real positions from `ExchangeManager.get_aggregated_portfolio()`, mapping internal `Position` objects to `PositionResponse` schema.
- **`get_trade_history()`**: Now retrieves the execution audit log from `ExecutionManager.get_audit_log()` and fills from `FillTracker`, combining both into sorted `TradeHistoryItem` records.

#### File: `quant_nanggroe/api/routes/agents.py`
- **`run_agent()`**: Now invokes the actual `TradingGraph.run()`, extracting agent trace, decision action, risk verdict, and strategy signal from the graph's output state.
- **`get_agent_status()`**: Now queries the actual `AgentRegistry.list_agents()` and `AgentRegistry.list_roles()` to build a real list of registered agents with their roles.

#### File: `quant_nanggroe/api/routes/backtest.py`
- **In-memory storage** now backed by real `BacktestEngine` execution
- **`submit_backtest()`**: Queues a backtest and runs it asynchronously via `run_in_executor`. Uses `YFinanceLoader` to fetch real price data and `BacktestEngine` to run a proper SMA crossover simulation with realistic execution (slippage, commission, position sizing).
- Results include real metrics: `total_return`, `sharpe_ratio`, `max_drawdown`, `win_rate`, `profit_factor`, `avg_trade_pnl`, and equity curve.

#### File: `quant_nanggroe/api/routes/portfolio.py`
- **`get_portfolio_summary()`**: Now queries `ExchangeManager.get_aggregated_portfolio()` for real positions and portfolio value, combined with RiskManager status.
- **`get_portfolio_risk()`**: Now computes VaR/CVaR using the `VaRCalculator` from `engine.risk.var` if daily returns are available from the RiskManager.
- **`run_stress_test()`**: Implements real stress testing with 6 historical scenarios (2008 Financial Crisis, 2020 COVID Crash, 2010 Flash Crash, 2013 Taper Tantrum, 100bps Rate Shock, 2022 Crypto Winter). Applies multi-factor shocks (equity drawdown, volatility spike, credit spread widening, liquidity dry-up) per position with Monte Carlo simulation for tail risk estimation (P95/P99 losses).
