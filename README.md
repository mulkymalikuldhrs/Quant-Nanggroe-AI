# Quant-Nanggroe-AI v4.6.0 — Autonomous Quant Hedge Fund

> **X·Y·Z Pipeline: 15 stages, 15 components wired, 72/100 production-ready.**
> **"Isi saldo dan mulai autonomous trading."** — Mulky Malikul Dhaher

## Dashboard UI

```
http://localhost:3000/pipeline  → 15-stage pipeline status + config panels
http://localhost:3000/qna-status → QNA system health
http://localhost:3000/trading    → Live trading controls
http://localhost:3000/portfolio  → Portfolio view
http://localhost:3000/strategies → Strategy management
http://localhost:3000/risk       → Risk dashboard
http://localhost:3000/agents     → AI agent status
http://localhost:3000/settings   → System config
```

## 3 Langkah Mulai Trading

### 1. Setup Akun MT5
```bash
copy config\mt5_accounts.yaml.example config\mt5_accounts.yaml
# Edit config\mt5_accounts.yaml — isi login, server
```

### 2. Set Password
```bash
set VALETAX_PASSWORD=password_mt5_anda
```

### 3. Start Backend + Dashboard
```bash
# Terminal 1: Backend API
launch.bat
# → http://localhost:8000/docs

# Terminal 2: Dashboard UI
cd dashboard && npm run dev
# → http://localhost:3000/pipeline
```

> **Butuh demo MT5?** Buka MT5 → File → Open Account → Demo.   
> **Untuk live trading:** Set `QNA_LIVE_TRADING=1` di `start_trading.bat`

## X·Y·Z Pipeline — 15 Stages

```
[1]  Data Fetch     [2]  Regime Detection     [3]  AIHF Bridge
[4]  HF Bridge       [5]  Strategy+Genes       [6]  RegimeFilter
[7]  Ensemble Vote   [8]  Council Debate       [9]  Risk Check
[10] Final Decider   [11] Execution (MT5)      [12] Strategy Logger
[13] PnL Evaluator   [14] Evolve & Repeat      [15] Hedge Fund Bridge
```

### Full Pipeline Flow

```
POST /api/autonomous/pipeline/run {"symbol":"BTC-USD"}
  → AutonomousPipeline.run() [1,180 lines, 15 components]

    STEP 1 - DATA:
      _fetch_data(symbol)       → yfinance / DataProviderManager (retry x3)

    STEP 2 - REGIME:
      MarketRegimeDetector()    → HMM: trending/ranging/volatile/crisis

    STEP 3 - AI SIGNALS:
      AIHF Bridge               → 20 agents vote → consensus override (< 0.6)
      HedgeFund Bridge          → 10 core providers → weighted vote [NEW]

    STEP 4 - STRATEGIES:
      discover_strategies()     → 28 canonical + 34 MUE-X genes
      GeneLoader                → MUE-X evolved strategies
      RegimeFilter              → Filter by regime compat (min 0.35)

    STEP 5 - ENSEMBLE:
      _ensemble_signal()        → Regime-weighted voting
      AIHF override             → If AIHF stronger, override signal
      HedgeFund override        → If HF stronger, override signal

    STEP 6 - COUNCIL:
      convene_council()         → Multi-agent debate (if confidence < threshold)

    STEP 7 - RISK:
      _check_risk()             → KillSwitch → RiskManager 9-gate → ATR sizing

    STEP 8 - FINAL DECIDER:
      FinalDecider.decide()     → Kelly + SL/TP + portfolio + regime → VETO

    STEP 9 - EXECUTION:
      _make_decision()          → PaperBroker (default) / MT5 live

    STEP 10 - LOGGING:
      StrategyLogger            → EVERY triggered strategy logged
      PnLEvaluator              → Closed-PnL → win rate / Sharpe / drawdown
      needs_fine_tune()         → Trigger fine-tune if bad

    STEP 11 - EVOLVE:
      SelfCorrection            → Lessons recorded → auto-improve
      Repeat                    → Autonomous loop
```

## Arsitektur (842 .py files)

```
quant_nanggroe/
├── api/            → FastAPI (140 routes, auth middleware, scheduler)
│   ├── app.py      → create_app() factory + scheduler lifecycle
│   ├── middleware.py → Auth (localhost→ADMIN), CORS, RateLimit
│   └── routes/     → trading, autonomous, scheduler, backtest, etc.
├── engine/
│   ├── agentic/    → AutonomousPipeline (1,180 lines) — ALL 15 stages wired
│   │   ├── autonomous.py    → MAIN ORCHESTRATOR
│   │   ├── final_decider.py → One Final Veto (483 lines)
│   │   ├── council.py       → Multi-agent debate
│   │   └── ensemble.py      → EnsembleVoter
│   ├── analytics/
│   │   ├── strategy_logger.py  → Every triggered strategy logged (306L)
│   │   └── pnl_evaluator.py    → Closed-PnL evaluation + fine-tune (231L)
│   ├── regime/
│   │   └── strategy_filter.py  → RegimeFilter (282L)
│   ├── strategies/
│   │   └── gene_loader.py      → MUE-X gene evolution (415L)
│   ├── scheduler.py→ PipelineScheduler (auto-trigger every N min)
│   ├── execution/  → ExecutionManager, PaperBroker, MT5 broker
│   ├── risk/       → KillSwitch, RiskManager, VaR, Kelly, PositionSizing
│   ├── backtest/   → WalkForwardAnalyzer, PSR/DSR, Monte Carlo
│   └── strategy/   → 106+ strategies (regime-based selection)
├── agents/
│   ├── aihf_bridge.py          → 20 AI agents (305L)
│   ├── hedge_fund_bridge.py    → 10 HF providers adapter (216L) [NEW]
│   ├── tools/                  → Technical, debate, compliance
│   └── personas/               → AI personas
├── exchange/       → ExchangeManager, CCXT broker, PaperExchangeBroker
├── data/           → Providers (yahoo, binance, finnhub, polygon, etc)
├── config/         → settings, mt5_accounts.yaml
├── security/       → Auth, encryption, credentials
└── mcp/            → Model Context Protocol server

dashboard/          → Next.js 16, 17 routes, 36 components, Tailwind v4
  └── pipeline/     → Pipeline UI with all 15 stages configurable [NEW]
```

## Semua Komponen Pipeline (15 WIRED)

| # | Komponen | File | Lines | Status |
|---|----------|------|-------|--------|
| 1 | **AutonomousPipeline** | `engine/agentic/autonomous.py` | 1,180 | ✅ Orchestrator |
| 2 | **FinalDecider** | `engine/agentic/final_decider.py` | 483 | ✅ Final Veto |
| 3 | **StrategyLogger** | `engine/analytics/strategy_logger.py` | 306 | ✅ Attribution |
| 4 | **PnLEvaluator** | `engine/analytics/pnl_evaluator.py` | 231 | ✅ Closed-PnL Eval |
| 5 | **RegimeFilter** | `engine/regime/strategy_filter.py` | 282 | ✅ Regime Gate |
| 6 | **GeneLoader** | `engine/strategies/gene_loader.py` | 415 | ✅ Gene Evolution |
| 7 | **AIHF Bridge** | `agents/aihf_bridge.py` | 305 | ✅ AI Signals |
| 8 | **HF Bridge** | `agents/hedge_fund_bridge.py` | 216 | ✅ **NEW** |
| 9 | **RiskManager** | `engine/risk/manager.py` | 500+ | ✅ 9-Gate Risk |
| 10 | **KillSwitch** | `engine/risk/kill_switch.py` | 100 | ✅ Emergency |
| 11 | **CooldownGuard** | `engine/execution/cooldown.py` | 50 | ✅ Cooldown |
| 12 | **Council** | `engine/agentic/council.py` | — | ✅ Debate |
| 13 | **Ensemble** | `engine/agentic/ensemble.py` | — | ✅ Voting |
| 14 | **DataFreshness** | `engine/analytics/data_freshness.py` | 50 | ✅ Freshness |
| 15 | **CrashRecovery** | `engine/state/recovery.py` | 100 | ✅ Recovery |

## External Signal Adapters — E: Drive Repos (4 WIRED)

Seven adapters bridge external signal providers into the `SignalVotingSystem`.
Four are direct E: drive repo integrations; three are built-in.

| Adapter | Source | Integration | Signal Sources |
|---------|--------|-------------|----------------|
| **AIHFAdapter** | `E:/ai-hedge-fund` | `src.main.run_hedge_fund()` — 15-investor multi-agent debate | `decisions[].action` (buy/hold/sell) + `confidence` (0-100 scaled to 0-1) |
| **HiddenRegimeAdapter** | `E:/hidden-regime` | `hidden_regime_mcp.tools.detect_regime()` → `create_financial_pipeline()` HMM | `current_regime` (bullish→BUY, bearish→SELL, crisis→SELL) + `confidence` (0-1) |
| **TradingAgentsAdapter** | `E:/tradingagents` | `tradingagents.graph.trading_graph.TradingAgentsGraph.propagate()` | 5-tier rating (Buy→BUY, Overweight→BUY, Hold→NEUTRAL, Underweight→SELL, Sell→SELL) + paid-LLM cost-guard |
| **AITraderAdapter** | `E:/AI-Trader` | HTTP → `GET /api/signals/feed` + `GET /api/trending`; SQLite → `clawtrader.db` signals table | Signal feed actions (buy/sell/short) + trending direction/score |
| **LangAlphaAdapter** | `E:/LangAlpha` | `mcp_servers.yf_analysis_mcp_server` + `fundamentals_mcp_server` + `macro_mcp_server` | Weighted vote: analyst consensus (strongBuy/buy/sell/strongSell) + PE/PB valuation + market risk premium |
| **WyckoffAdapter** | Built-in QNA | `engine.strategies.wyckoff.WyckoffStrategy.generate_signal()` | VSA-based BUY/SELL with 0.65 default confidence |
| **MultiTimeframeAdapter** | Built-in QNA | `engine.strategy.multi_timeframe.MultiTimeframeAnalyzer.analyze()` | MTF direction (bullish→BUY, bearish→SELL) + confidence |

### Signal Flow

```
fetch_all_signals(symbol="BTC-USD")
  → iterates ALL_ADAPTERS (7 registered)
  → each adapter.fetch_signal(symbol) → Signal | None
  → SignalVotingSystem.aggregate(signals) → VoteResult (final_bias, confidence)
  → TradingAgentsValidator.evaluate(primary, symbol) → confirm|contradict|abstain
  → EnsembleVoter merges into AutonomousPipeline signal
```

### Configuration

| Env Var | Affects | Default | Purpose |
|---------|---------|---------|---------|
| `AI_TRADER_BASE_URL` | AITraderAdapter | `http://localhost:8080` | AI-Trader API endpoint |
| `QNA_ALLOW_PAID_LLM` | TradingAgentsAdapter | (unset) | `1` to bypass paid-LLM cost-guard |
| `QNAI_ENCRYPTION_KEY` | EncryptedStore | (unset) | Fernet AES-256 key for security |

## Keamanan

- **Localhost auto-ADMIN** — `127.0.0.1` / `::1` / `localhost` → skip auth
- **Fail-closed** — tanpa `QNAI_JWT_SECRET` → RuntimeError
- **Kill switch ENFORCED** — `execute_order()` hard-block, bukan warning
- **RiskManager ENFORCED** — veto tidak bisa di-override
- **Paper default** — `QNA_LIVE_TRADING=1` diperlukan untuk MT5 live
- **HF Bridge logging suppressed** — hedge_fund.py `basicConfig()` prevented from overriding root logger

## Konfigurasi

| Env Var | Default | Fungsi |
|---------|---------|--------|
| `VALETAX_PASSWORD` | — | Password MT5 (via expandvars) |
| `QNA_LIVE_TRADING` | `0` | `1` = aktifkan MT5 live |
| `QNAI_API_KEY` | — | API key untuk auth dari luar |
| `QNAI_JWT_SECRET` | — | JWT signing key |
| `QNAI_ALLOW_INSECURE_DEV` | `false` | `true` = bypass auth |
| `PAPER_TRADE` | `true` | `false` = real MT5 execution |

## Status: ✅ PIPELINE OPERATIONAL — 78/100

| Criteria | Score |
|----------|-------|
| Pipeline stages wired | 15/15 (100%) |
| API stubs implemented | 3/3 (100%) — colony, memory, security-tools |
| E: drive signal adapters | 4/4 (100%) — ai-hedge-fund, hidden-regime, AI-Trader, LangAlpha |
| External adapter paths | 6 repositories on `E:` verified — ai-hedge-fund, hidden-regime, tradingagents, AI-Trader, LangAlpha, trading |
| Dashboard UI routes | 17 routes + pipeline |
| .md docs consolidated | 44 active + 32 archived = 78 total |
| hedge_fund.py integration | ✅ Merged via bridge adapter |
| Production readiness | **78/100** |

## Dashboard UI Endpoints

| Route | Description |
|-------|-------------|
| `/` | Main dashboard |
| `/pipeline` | **15-stage pipeline status + config panels [NEW]** |
| `/trading` | Live trading controls |
| `/portfolio` | Portfolio view |
| `/brokers` | Broker management |
| `/risk` | Risk dashboard |
| `/market` | Market data |
| `/agents` | AI agent status |
| `/backtest` | Backtest engine |
| `/strategies` | Strategy management |
| `/factors` | Alpha factors |
| `/memory` | System memory |
| `/colony` | Colony management |
| `/qna-status` | QNA system health |
| `/security` | Security settings |
| `/tools` | Tools |
| `/channels` | Channels |
| `/settings` | System config |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/autonomous/pipeline/run` | POST | Run pipeline for one symbol |
| `/api/autonomous/pipeline/batch` | POST | Run pipeline for multiple symbols |
| `/api/scheduler/status` | GET | Check scheduler status |
| `/api/scheduler/start` | POST | Start autonomous scheduler |
| `/api/scheduler/stop` | POST | Stop autonomous scheduler |
| `/api/scheduler/cycle` | POST | Manually trigger one cycle |
| `/health` | GET | Health check |
