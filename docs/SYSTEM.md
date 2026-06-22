# QNA System Documentation

## Overview

Quant Nanggroe AI (QNA) is a multi-agent quantitative trading framework with:

- LangGraph StateGraph orchestration (8 nodes, conditional edges)
- 15 trading strategies across 7 categories
- 11-agent council with LLM-based bull/bear + risk debates
- 9-checkpoint constitutional risk gate (deterministic, not negotiable)
- Paper exchange broker (902 lines, slippage + commission simulation)
- Alpaca integration for real trading
- FastAPI REST API (9 endpoints) + WebSocket with 30s heartbeat
- Next.js dashboard (15 pages via real API calls — zero mock data)
- Docker multi-stage build + docker-compose (3 services)
- Telegram bot integration (`qna_prod.py --telegram`)
- Auto Ω singularity kernel (8 consciousness layers)

## File-by-File Reference

### Core Package (`quant_nanggroe/`)

| File | Lines | Purpose |
|------|-------|---------|
| `api.py` | 778 | FastAPI app: 9 REST endpoints + WebSocket `/ws/trading` |
| `cli.py` | 813 | Click CLI: `qnai run/backtest/agents/portfolio/risk/serve/memory` |
| `qna_prod.py` | 439 | Production runner: 15-min autonomous cycle with Telegram |
| `live_engine.py` | 1199 | Legacy autonomous engine: 60s cycle, 5 inline strategies |
| `engine_production_bridge.py` | 535 | Production wiring: 6 components connecting real engines |
| `config/settings.py` | 178 | Pydantic v2 Settings: 33+ env vars with `QNAI_` prefix |

### Agent System (`quant_nanggroe/agents/`)

| File | Lines | Purpose |
|------|-------|---------|
| `graph.py` | 789 | LangGraph StateGraph: 8 nodes, conditional routing, singleton factory |
| `state.py` | — | AgentState TypedDict: complete shared state schema |
| `base.py` | — | BaseAgent ABC + multi-provider LLM factory (OpenAI/Anthropic/Google/Ollama/OpenRouter) |
| `registry.py` | — | AgentRegistry + AgentFactory: dynamic agent creation |
| `trader/tools.py` | 230 | 3 LangChain tools: `place_order`, `get_position`, `get_portfolio` — all wired to PaperBroker |
| `telegram_bot.py` | 190 | Telegram signal bot with `--telegram` flag |
| `bridges/risk_gate_bridge.py` | — | Deterministic 9-checkpoint gate bridge |
| `bridges/kelly_bridge.py` | — | Kelly position sizing bridge |
| `council/debate.py` | — | Bull/Bear researcher debate + 3-way risk debate |
| `council/voting.py` | — | Weighted voting with historical accuracy weights |

### Engine (`quant_nanggroe/engine/`)

| File | Lines | Purpose |
|------|-------|---------|
| `strategy/strategies/__init__.py` | 269 | 15 strategy factory + registry |
| `strategy/strategy_selector.py` | 356 | Regime→strategy compatibility matrix |
| `strategy/multi_timeframe.py` | 237 | HTF→MTF→LTF alignment |
| `risk/manager.py` | 673 | RiskManager: 5 position sizing methods |
| `risk/checks.py` | — | ConstitutionalRiskGuard: 9 mandatory checkpoints |
| `risk/kill_switch.py` | — | Auto-halt on limit breach |
| `risk/drawdown.py` | — | Maximum drawdown tracking |
| `risk/kelly/` | — | Full/Half/Quarter Kelly + Multi-asset |
| `regime/hmm_detector.py` | — | HMM 4-regime detection |
| `backtest/engine.py` | — | Walk-forward + Monte Carlo backtest |
| `data/cot_provider.py` | 263 | CFTC COT report fetcher + COTAnalyzer |
| `data/economic_calendar.py` | — | Econ calendar with impact scoring |
| `live/adaptive_integration.py` | 348 | AdaptiveSignalPipeline + RiskGate + DataFeedIntegrator |
| `smc/engine.py` | — | SMC orchestrator: 8-module analysis pipeline |
| `smc/market_structure.py` | — | BOS/CHOCH/CISD + HH/HL/LH/LL trend |
| `smc/poi.py` | — | FVG, Order Block, Breaker Block, Rejection Block |
| `smc/amdx.py` | — | AMDX cycle: Accumulation/Manipulation/Distribution/Extension |
| `smc/liquidity.py` | — | Liquidity Pool, Sweep, Inducement |
| `smc/killzone.py` | — | Session/Killzone/MacroTime timer (WIB) |
| `smc/ict_setups.py` | — | Silver Bullet, Turtle Soup, Venom |
| `smc/confluence.py` | — | 7-criteria entry checklist scorer |
| `smc/crt.py` | — | Candle Range Theory + MTF confirmation |

### Exchange (`quant_nanggroe/exchange/`)

| File | Lines | Purpose |
|------|-------|---------|
| `paper_broker.py` | 902 | Full paper broker: slippage, commission, position tracking, synthetic orderbook |
| `alpaca_broker.py` | 1032 | Alpaca REST + WebSocket: paper/live trading |
| `factory.py` | — | Exchange factory with 8 CCXT exchanges |
| `manager.py` | — | Exchange manager |
| `base/` | — | ExchangeInterface, ExchangeConfig, ExchangeState base classes |

### API + Dashboard (`dashboard/src/lib/`)

| File | Lines | Purpose |
|------|-------|---------|
| `api-client.ts` | 177 | TypeScript API client: 5 endpoint groups, all typed interfaces |
| `store.ts` | 119 | Zustand store: async actions, loading/error state per resource |
| `websocket.ts` | 134 | WebSocket hook: exponential backoff (up to 30s), 20 retry limit |

### Scripts (`scripts/`)

| File | Lines | Purpose |
|------|-------|---------|
| `start_alpaca_paper.sh` | — | Start API with Alpaca paper broker |
| `activate-trading.sh` | — | Activate live trading engine |
| `qna-heartbeat.sh` | — | Cron health check |
| `test_data_fallback.py` | — | Data fallback + circuit breaker tests |

### Infrastructure

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: builder → qna user → healthcheck |
| `docker-compose.yml` | 3 services: api, worker, redis |
| `.env.template` | 33 environment variables documented |
| `nginx/` | Nginx reverse proxy config |
| `monitoring/` | Grafana + Prometheus dashboards |

## Data Flow

### Trading Pipeline (API via `POST /api/v1/trade`)

```
POST /api/v1/trade
  │
  ├──→ TradingGraph.run() (LangGraph, 8 nodes)
  │     │
  │     1. market_analysis → Researcher + Macro + Crypto + Forex agents
  │     2. signal_generation → Strategist agent (deep LLM)
  │     3. risk_assessment → LLM risk agent (qualitative)
  │     4. deterministic_risk_gate → 9-checkpoint HARD GATE
  │       ├── APPROVED/MODIFIED → continue
  │       ├── REJECTED → HALT
  │       ├── low confidence → council_debate
  │       └── kill switch → emergency_exit (close all)
  │     5. kelly_sizing → KellyBridge (position sizing)
  │     6. portfolio_optimization → Portfolio agent
  │     7. execution_decision → Trader agent
  │     8. order_execution → Execution agent
  │     9. reflection → CouncilDebate (post-trade)
  │
  └──→ Fallback: ProductionStrategyRunner (no LLM)
        └──→ RegimeAwareExecution → RiskEnforcer → SyncPaperBroker
```

### Production Runner (`qna_prod.py`)

```
15-min cycle:
  1. Fetch 1h OHLCV via CryptoProvider
  2. SMC engine analysis (market structure, POI, ICT setups, killzone)
  3. ATR-based stop loss (2×ATR)
  4. Position sizing (constitutional cap)
  5. ConstitutionalRiskGuard (9 checkpoints)
  6. Build signal with SMC context
  7. Telegram notification (if --telegram flag)
  8. Persist to SQLite (signals + cycles tables)
```

### Live Engine (`live_engine.py`)

```
60s cycle:
  1. Kill switch check
  2. Fetch prices (every cycle)
  3. Fetch klines (1m every 3 cycles, 15m every 6, 4h every 15)
  4. COT data (every 20 cycles)
  5. Economic calendar (every 10 cycles)
  6. Adaptive pipeline signals (15 strategies, regime-based, MTF-aligned)
  7. Inline strategy fallback (5 strategies)
  8. NP strategies (TSMOM, TrendFollow)
  9. Production bridge strategies
  10. Auto-backtest (every 100 cycles)
  11. Position updates + rebalance
  12. SQLite persistence
  13. Telegram heartbeat (every 10 cycles)
```

### Dashboard → API Flow

```
Browser → Next.js (port 3000)
  ├── api-client.ts → apiRequest<T>() → fetch(`http://localhost:8000/api/v1/...`)
  │     ├── GET  /api/v1/health         → Dashboard health indicator
  │     ├── GET  /api/v1/portfolio      → Portfolio + positions table
  │     ├── GET  /api/v1/agents         → Agent council graph
  │     ├── POST /api/v1/trade          → Execute pipeline
  │     ├── POST /api/v1/backtest       → Run backtest
  │     └── GET  /api/v1/risk/{symbol}  → Risk assessment
  │
  └── websocket.ts → ws://localhost:8000/ws/trading
        ├── trade_update (live trade notifications)
        ├── risk_alert (risk breach alerts)
        ├── position_change (position updates)
        └── heartbeat (30s keepalive)
```

## API Endpoints

| Method | Path | Description | Response Model |
|--------|------|-------------|----------------|
| GET | `/` | API info | name, version, docs |
| GET | `/api/v1/health` | Health check | uptime, components |
| POST | `/api/v1/trade` | Execute trading pipeline | TradeResponse |
| GET | `/api/v1/portfolio` | Portfolio status | PortfolioResponse |
| GET | `/api/v1/agents` | List agents | AgentListResponse |
| POST | `/api/v1/backtest` | Run backtest | BacktestResponse |
| GET | `/api/v1/risk/{symbol}` | Risk assessment | RiskCheckResponse |
| WS | `/ws/trading` | Real-time streaming | JSON messages |

## Environment Variables

All 33+ vars in `.env.template` with `QNAI_` prefix. Key groups:

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `QNAI_ALPACA_API_KEY` | For live | — | Alpaca API key |
| `QNAI_ALPACA_API_SECRET` | For live | — | Alpaca secret |
| `QNAI_OPENAI_API_KEY` | For LLM | — | OpenAI key |
| `QNAI_ANTHROPIC_API_KEY` | Optional | — | Anthropic key |
| `QNAI_NVIDIA_API_KEY` | For NVIDIA | — | NVIDIA NIM key |
| `QNAI_DATABASE_URL` | No | `sqlite:///quant_nanggroe.db` | DB connection |
| `QNAI_DEBUG` | No | `False` | Debug mode |
| `QNAI_RISK_MAX_PER_TRADE` | No | 0.5 | Max % risk per trade |
| `QNAI_RISK_MAX_DAILY_LOSS` | No | 1.0 | Max daily loss % |
| `QNAI_RISK_MAX_WEEKLY_LOSS` | No | 3.0 | Max weekly loss % |
| `QNAI_RISK_MAX_DRAWDOWN` | No | 10.0 | Max drawdown % |
| `TELEGRAM_BOT_TOKEN` | For Telegram | — | Telegram bot token |
| `TELEGRAM_CHAT_ID` | For Telegram | — | Telegram chat ID |

## Strategy Registry

15 strategies in 7 categories:

| Strategy | Category | Asset Classes | Walk-Forward |
|----------|----------|---------------|:---:|
| MeanReversion | mean_reversion | stocks, forex, crypto | ❌ |
| Momentum | momentum | stocks, forex, crypto, futures | ❌ |
| PairsTrading | pairs_trading | stocks, crypto | ❌ |
| VolatilityArbitrage | volatility | stocks, futures, options | ❌ |
| StatisticalArbitrage | statistical_arbitrage | stocks, crypto | ❌ |
| MarketMaking | market_making | crypto, forex | ❌ |
| RegimeBased | regime_detection | stocks, forex, crypto | ❌ |
| CryptoSpecific | crypto | crypto | ❌ |
| SMC | pattern | crypto, forex, stocks | ❌0/60 |
| ICT | pattern | crypto, forex, stocks | 6/60 fold |
| Support/Resistance | supply_demand | crypto, forex, stocks | ❌ |
| Supply/Demand | supply_demand | crypto, forex, stocks | ❌ |
| Wyckoff | wyckoff | crypto, stocks, futures | ❌0/60 |
| COT | cot | futures, forex | ❌ |
| Fundamental | fundamental | forex, stocks, futures, crypto | ❌ |

**Walk-forward result: 0 strategies have universal predictive power on daily data across all folds.**

## Risk System

### 9-Checkpoint Constitutional Risk Gate (non-negotiable)

1. Risk per trade ≤ 0.5%
2. Daily loss < 1.0%
3. Weekly loss < 3.0%
4. Risk:Reward ≥ 1:2
5. Stop loss exists and valid
6. Valid entry price > 0
7. Valid direction (BUY/SELL/LONG/SHORT)
8. Not overtrading (≤ 5 trades/day)
9. Correlated positions ≤ 3

### Kill Switch

- Activates when daily PnL < -2% OR weekly PnL < -5%
- When active: ALL trades blocked, existing positions get emergency exit
- Manual toggle via dashboard + CLI

### Position Sizing

- Kelly Criterion (Full/Half/Quarter Kelly)
- ATR-based stop distance (2×ATR)
- Constitutional cap: max 10% of portfolio per position
- Max leverage: 3.0×
- Max drawdown: 15%

## State of the System — Session 3b (22 June 2026)

### What Changed

| Scope | Change | Verification |
|-------|--------|:---:|
| WS1 | 180 combo walk-forward validation | 0 universal alpha |
| WS2 | Dashboard wired to real API, mock-data.ts deleted | Syntax OK |
| WS3 | Alpaca script + Dockerfile + docker-compose + .env | Syntax OK |
| WS4 | api.py real PaperBroker, cli.py real pipeline, trader tools no mock | Syntax OK |
| WS5 | 0 mock/simulated data across all 19 files | Syntax OK |
| WS6 | Hardcoded paths → auto-detection in 4 scripts | Syntax OK |

### What's Still Blocked

- **No validated alpha**: 0/4 coins pass walk-forward on any strategy
- **npm install**: Times out in Termux — dashboard deps can't be installed
- **Docker daemon**: Unavailable in Termux
- **Alpaca keys**: Not found in credentials.md
- **0 real trades, $0 P&L**: QNA has never executed a single real trade
- **Pydantic v1/v2**: `field_validator` vs `root_validator` incompatibility in some modules

## Deployment

### Local Development

```bash
export PYTHONPATH=/path/to/Quant-Nanggroe-AI-worktree

# API only
python3 -m uvicorn quant_nanggroe.api:app --host 0.0.0.0 --port 8000

# CLI
python3 -m quant_nanggroe.cli run --symbols BTC/USDT --provider openai

# Production (autonomous)
python3 -m quant_nanggroe.qna_prod --telegram --symbols BTC-USD

# Live engine (legacy)
python3 quant_nanggroe/live_engine.py start
```

### Docker

```bash
# Build
docker compose build

# Start
docker compose up -d

# Services
#   api: FastAPI on port 8000
#   worker: celery worker
#   redis: Redis cache
```

## Critical Context

- **ZERO validated alpha**: SMC (13/60 fold pass), ICT (6/60), Wyckoff (0/60), MACD (0/4 coins). Original "Sharpe 1.57" was 92-candle in-sample curve-fitting.
- **Dashboard 100% real**: api-client.ts (177 lines, 5 endpoint groups), store.ts (119 lines, async Zustand), websocket.ts (134 lines, exponential backoff 20 retries). Zero mock references.
- **Docker ready**: Multi-stage (builder→non-root qna), healthcheck, 3 services. Needs daemon + keys.
- **Path auto-detection**: All scripts use `SCRIPT_DIR` relative resolution. Clone anywhere.
- **Auto Ω operating system**: 8 consciousness layers active for all sessions.
- **0 real trades executed**: Paper infrastructure exists but untested.
