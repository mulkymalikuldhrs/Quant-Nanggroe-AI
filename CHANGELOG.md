# Quant Nanggroe AI — Changelog

## v4.4.0 (Current — July 2026)

**1766/1766 tests pass (100%) — 106 strategies — 16 API routes — 5 brokers — 154 test files — 15 dashboard pages**

### ✅ Testing Milestone — Full Test Suite Pass
- **1766/1766 tests passing** across 154 test files (100% pass rate)
- Complete coverage: engine (backtest, risk, trading, strategy, execution), exchange connectors, API routes, agents, providers, core modules
- No skipped or xfailed tests — every test green across the board
- Test suite includes: unit tests, integration tests, regression tests

### 🏗️ 18 Strategy Modules
- 14 concrete strategies in `engine/strategy/strategies/`: mean_reversion, momentum, pairs_trading, trend_follow, statistical_arbitrage, supply_demand, support_resistance, ICT/SMC, Wyckoff, COT, regime_based, volatility_arbitrage, market_making, crypto_specific, fundamental
- 4 legacy strategies in `quant_nanggroe/strategies/`: pairs_trade, trend_follow, tsmom, xgboost_alpha
- Strategy registry with snake_case module names, CamelCase alias support via `create_strategy()`

### 🌐 30 API Routes
- Full FastAPI route suite in `quant_nanggroe/api/routes/`:
  - `_data.py`, `agentic.py`, `agents.py`, `analytics.py`, `backtest.py`, `brokers.py`
  - `channels.py`, `colony.py`, `council.py`, `credentials.py`, `debate.py`
  - `ecosystem.py`, `fred.py`, `geopolitics.py`, `market.py`, `memory.py`
  - `monitor.py`, `options.py`, `personas.py`, `portfolio.py`, `rl.py`
  - `sec_edgar.py`, `signal_generator.py`, `strategies.py`, `strategy.py`
  - `trading.py`, `whatsapp.py`, `wiring_compat.py`, `ws.py`

### 🔌 7 Broker Integrations
- **alpaca** — AlpacaBroker via `exchange/alpaca_broker.py`
- **ccxt** — CCXTBroker via `exchange/ccxt_broker.py`
- **ibkr** — IBKRBroker via `exchange/ibkr_broker.py`
- **mt5** — MT5Broker via `exchange/mt5_broker.py`
- **paper** — PaperExchangeBroker via `exchange/paper_broker.py` + PaperBroker via `engine/execution/brokers/paper.py`
- **polymarket** — PolymarketBroker via `exchange/polymarket_broker.py`
- **factory/manager** — BrokerFactory via `exchange/factory.py` + ExchangeBrokerAdapter in `api/routes/trading.py`

### 🐛 Recent Bug Fixes (2026-07-13)
- **pandas 3.0 freq alias** — `H` → `h` throughout (deprecated frequency string migration)
- **OHLCV requires symbol field** — Added missing `symbol` field validation in OHLCV data structures
- **toggle script CamelCase→snake_case** — Normalized toggle scripts to snake_case module naming
- **scripts/__init__.py lazy importer** — Fixed circular imports via lazy loading in scripts package
- **paper_broker BUY limit price logic** — Corrected limit price handling for BUY orders in paper broker
- **openbb_provider api_key passthrough** — Fixed API key forwarding in OpenBB data provider
- **Strategy registry normalize** — `list_strategies()` returns 16 snake_case names; `create_strategy()` handles CamelCase→snake_case mapping

### 🖥️ Dashboard & UI
- 15 Next.js App Router pages (main, trading, portfolio, agents, risk, strategies, backtest, market, memory, colony, factors, security, channels, tools, settings)
- Apple macOS Liquid Glass Design System with glassmorphism
- WebSocket real-time (4 channels: price, regime, risk, portfolio)
- API client with retry, dedup, timeout, 30+ typed endpoints
- Zustand store with granular loading/error states

### 🧪 154 Test Files
- 154 Python test files across `tests/` directory
- Full coverage for: engine, exchange, API, strategies, risk, backtest, execution, connectors
