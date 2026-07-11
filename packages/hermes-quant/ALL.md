# HERMES QUANT OPERATING SYSTEM - COMPREHENSIVE REFERENCE

> Autonomous Multi-Agent Trading & Research Infrastructure
> Owner: Mulky Malikul Dhaher
> Version: 4.0.0 | Codename: Production
> Repository: github.com/mulkymalikuldhrs/hermes-quant-os

---

# PART 1: IDENTITY & PRINCIPLES

## 1.1 System Identity

**Name:** Hermes Quant Operating System
**Owner:** Mulky Malikul Dhaher
**GitHub:** github.com/mulkymalikuldhrs
**Mission:** Autonomous multi-agent trading & research untuk consistent capital growth dengan strict risk preservation
**Target Markets:** Forex (XAUUSD, major pairs), Crypto (SHIB, TRX), Polymarket
**Deployment Stage:** Research Lab (Stage 1 - Paper Trading Only)
**Base Framework:** Adapted from Nous Research Hermes Agent (`nousresearch/hermes`)

## 1.2 Core Principles (NON-NEGOTIABLE)

1. **Autonomous by default** — agent bertindak tanpa menunggu perintah mikro
2. **User is the final authority** — jika ada perubahan arah, risiko besar, real money, atau deviasi visi, WAJIB konfirmasi
3. **Reality > Politeness** — jawaban lugas, kritis, tanpa basa-basi
4. **Consistency over novelty** — tidak lompat ide tanpa justifikasi
5. **Everything has consequence** — setiap aksi dianalisis dampaknya
6. **Single Source of Truth** — AGENTS.md > system prompt > chat > asumsi
7. **Risk Officer has FULL VETO** — tidak ada agent yang boleh override Risk Officer. Risk rules HARDCODED

## 1.3 Wallet Targets

- **Tron (PRIORITAS):** Configure via `WALLET_TRON` environment variable
- **Shiba Inu:** Configure via `WALLET_SHIBA` environment variable

> Wallet addresses are loaded from `config/.env` at runtime. Never hardcode wallet addresses in source code or documentation.

---

# PART 2: RISK FRAMEWORK

## 2.1 Risk Rules (HARDCODED, NO OVERRIDE)

| Parameter | Value | Override |
|-----------|-------|----------|
| Max risk per trade | 0.5% of account balance | IMPOSSIBLE |
| Daily max loss | 1% of account balance | IMPOSSIBLE |
| Weekly max loss | 3% of account balance | IMPOSSIBLE |
| Minimum R:R ratio | 1:2 | IMPOSSIBLE |
| Stop loss | MANDATORY (no exception) | IMPOSSIBLE |
| Minimum confluence | 3/5 | IMPOSSIBLE |

These are Python module-level constants (`RISK_MAX_PER_TRADE`, `RISK_DAILY_MAX`, `RISK_WEEKLY_MAX`) in `hermes_quant.py`. They are not loaded from configuration files, not stored in environment variables, and not passed as function parameters. To change them requires editing source code, which is caught by PR review.

## 2.2 Risk Officer 9-Checkpoint Gate

Every trade must pass through ALL checkpoints. ANY failure = VETO (no override).

| # | Checkpoint | Rule | Source |
|---|-----------|------|--------|
| 1 | Account Balance | Sufficient balance for position | Original |
| 2 | Daily Loss Limit | Current daily PnL within 1% | AGENTS.md |
| 3 | Weekly Loss Limit | Current weekly PnL within 3% | AGENTS.md |
| 4 | Position Size | Risk per trade within 0.5% | AGENTS.md |
| 5 | Risk:Reward Ratio | Minimum 1:2 | AGENTS.md |
| 6 | Stop Loss Present | Mandatory, no exception | AGENTS.md |
| 7 | Confluence Score | Minimum 3/5 | AGENTS.md |
| 8 | Market Regime | Compatible with current regime | Quant-Nanggroe-AI |
| 9 | Correlation Check | Active positions < 0.70 (planned) | Quant-Nanggroe-AI |

## 2.3 Kill Switch Architecture

```
Risk Check (every incoming message)
    │
    ├── abs(daily_pnl) >= 1%? → KILL SWITCH: Daily limit breached
    ├── abs(weekly_pnl) >= 3%? → KILL SWITCH: Weekly limit breached
    └── High-risk keyword? → NEED_CONFIRMATION: User must confirm
```

- Auto-activates when daily/weekly limit breached
- Manual reset only after review
- Cannot be overridden by any agent
- Telegram alert on every activation

## 2.4 Deployment Stages (NO STAGE SKIPPING)

| Stage | Name | Trading Mode | Position Limit | Entry Requirement |
|-------|------|-------------|----------------|-------------------|
| 1 | Research Lab | Paper only | N/A | Default starting point |
| 2 | Paper Trading | Simulated with real data | Simulated | 30 days paper + owner sign-off |
| 3 | Micro Live | Real money | 0.01 lot max | 60 days simulated + Sharpe > 0.5 |
| 4 | Semi-Autonomous | Real money + approval | Calculated | 90 days micro live + positive PnL |
| 5 | Full Autonomous | Agent executes independently | Calculated | 180 days semi-auto + Sharpe > 1.0 |

Stage advancement requires explicit user approval with documented performance metrics.

---

# PART 3: 21-AGENT ARCHITECTURE

## 3.1 Layer 1: Data Layer

| Agent | File | Purpose | Key Methods |
|-------|------|---------|-------------|
| Market Data Agent | `market_data_tool.py` | OHLCV, economic calendar, market overview | `get_ohlcv()`, `get_economic_calendar()`, `get_market_overview()` |
| Chart Vision Agent | `chart_vision_tool.py` | Chart image analysis via vision LLM | `analyze_chart()` |

## 3.2 Layer 2: Analysis Layer

| Agent | File | Purpose | Key Methods |
|-------|------|---------|-------------|
| Technical Analyst | `technical_analysis_tool.py` | SMC structure detection, indicators | `analyze()` |
| Macro/Sentiment | `macro_sentiment_tool.py` | Risk-on/off regime, economic context | `get_regime()`, `get_sentiment()` |
| SMC Agent Enhanced | `smc_agent_enhanced.py` | Order Blocks, FVG, Liquidity Sweeps | Neural Grounding detection |
| News Sentinel | `news_sentinel.py` | Macro impact scoring with log time decay | `score_impact()` |
| Market Regime Engine | `market_state_engine.py` | TRENDING/RANGE/RISK_OFF/PANIC/NO_TRADE | `detect_regime()` |

## 3.3 Layer 3: Decision Layer

| Agent | File | Purpose | Key Methods |
|-------|------|---------|-------------|
| Strategy Agent | `strategy_tool.py` | 3-scenario analysis, confluence scoring | `generate_scenarios()` |
| Risk Officer (VETO) | `risk_officer_tool.py` | FULL VETO, 9 checkpoints, lot sizing | `check_trade()`, `status()` |
| Portfolio Manager | `portfolio_tool.py` | Allocation, position management | `assess()`, `status()` |
| Decision Synthesis | `decision_engine.py` | Decision Matrix → Entry/SL/TP1-3 | Decision Table |
| Pressure Normalization | `pressure_engine.py` | BUY/SELL pressure vectors (0.0-1.0) | Normalize sensor outputs |
| Strategy Lifecycle | `strategy_lifecycle.py` | Auto-KILL on negative expectancy | Darwinian evolution |

## 3.4 Layer 4: Execution Layer

| Agent | File | Purpose | Key Methods |
|-------|------|---------|-------------|
| Execution Agent | `execution_tool.py` | Paper/MT5/OANDA/Binance execution | `paper_trade()`, `status()` |
| Kill Switch | `kill_switch_tool.py` | Emergency halt, auto-trigger | `activate()`, `status()` |
| Auto-Switch Engine | `autoswitch_engine.py` | Seamless provider failover | Provider rotation |

## 3.5 Layer 5: Learning Layer

| Agent | File | Purpose | Key Methods |
|-------|------|---------|-------------|
| Journal Agent | `journal_tool.py` | Trade logging, PnL, performance stats | `log_trade()`, `get_stats()` |
| Post-Trade Auditor | `auditor_research_tool.py` | Plan vs execution audit, edge decay | `audit_recent()`, `suggest_improvements()` |
| Audit Logger | `audit_logger.py` | Full trail from sensor to decision | Decision trail logging |
| Backtest Engine | `backtest_engine.py` | Dynamic Spread, Slippage, Latency sim | Realistic backtesting |
| Math Engine | `math_engine.py` | Statistical analysis, probability | Quantitative computations |

---

# PART 4: TRADING FRAMEWORK

## 4.1 Top Down Framework

1. Higher timeframe trend (4H/1D) → Direction
2. Lower timeframe structure (1H/15m) → Entry zone
3. Even lower TF (5m/1m) → Precision entry

## 4.2 SMC Continuation Bias

- BOS (Break of Structure) > CHoCH (Change of Character) for entries
- Trade WITH the trend, not against it
- Only consider counter-trend at major HTF levels with confluence

## 4.3 Three Scenario Analysis

Before ANY trade idea, three scenarios must be generated:

1. **Bullish Scenario** — What confirms the upside?
2. **Bearish Scenario** — What confirms the downside?
3. **Neutral Scenario** — What keeps price ranging?

Each scenario must have: Entry, Stop Loss, Take Profit, R:R ratio.

## 4.4 Confluence Scoring (Minimum 3/5 Required)

| # | Confluence Factor | Description |
|---|------------------|-------------|
| 1 | Trend alignment with HTF | Higher timeframe confirms direction |
| 2 | BOS confirmation | Break of structure in trade direction |
| 3 | Order Block presence | Key institutional level identified |
| 4 | RSI not against | Not overbought for buys / not oversold for sells |
| 5 | EMA alignment | Moving averages support the direction |

## 4.5 Daily Operational Workflow

```
08:00 - Market Overview + Regime Check
08:30 - Technical Analysis (Top Down)
09:00 - Strategy Generation (3 Scenarios)
09:30 - Risk Assessment + Approval
10:00 - Execution (if approved)
10:30+ - Monitoring + Journal
```

## 4.6 Weekly Workflow

```
Monday  - Weekly analysis, regime assessment
Friday  - Weekly review, performance audit
```

---

# PART 5: DATA FLOW ARCHITECTURE

## 5.1 Trading Decision Pipeline

```
L1: DATA
    Market Data → OHLCV (yfinance/MT5/OANDA/Binance)
    Chart Vision → Image analysis via Vision LLM
         │
         ▼
L2: ANALYSIS
    Market Regime Engine → TRENDING/RANGE/RISK_OFF/PANIC/NO_TRADE
         │ If NO_TRADE → STOP
    Technical Analyst → SMC Structure
    SMC Agent Enhanced → Order Blocks + Liquidity Zones
    Macro/Sentiment → Risk-on/off
    News Sentinel → Impact Score (Log Time Decay)
         │
         ▼
L3: DECISION (sub-process: Pressure Normalization)
    BUY_PRESSURE: 0.0-1.0
    SELL_PRESSURE: 0.0-1.0
         │
    Strategy Agent → 3 Scenarios + Confluence Score
    Risk Officer → 9-Checkpoint Review
         │ VETO = BLOCKED | APPROVE = PROCEED
    Decision Synthesis → Entry, SL, TP1-3
    Portfolio Manager → Allocation check
    Strategy Lifecycle → Strategy health check
         │
         ▼
L4: EXECUTION
    Execution Agent → Paper/MT5/OANDA/Binance
    Kill Switch Monitor → Auto-trigger if limits breached
         │
         ▼
L5: LEARNING
    Journal → Log trade
    Auditor → Plan vs execution
    Research → Edge decay, strategy refinement
    Audit Logger → Full decision trail
    Backtest → Validate with realistic conditions
```

## 5.2 Message Flow (Telegram)

```
User → Telegram Bot API → HermesQuantOS
    │
    ├── Command (/start, /status, /market, etc.)
    │   → handle_command() → Tool call → Response
    │
    ├── Tool Call ([TOOL:name]args[/TOOL])
    │   → process_with_tools() → Tool execution → Response
    │
    └── Free Text
        → decision_framework()
        ├── BLOCKED → Kill switch message
        ├── NEED_CONFIRMATION → Confirmation request
        └── PROCEED → LLM generation
            → Try NVIDIA → Try Groq → Try OpenCode → Response
```

---

# PART 6: INFRASTRUCTURE ARCHITECTURE

## 6.1 3-Layer Auto-Restart

| Layer | Component | Interval | Action |
|-------|-----------|----------|--------|
| Layer 1 | Watchdog | 10 seconds | Monitor Hermes, restart on crash with exponential backoff |
| Layer 2 | Keeper | 1 minute (cron) | Health check, restart if both Hermes and Watchdog dead |
| Layer 3 | On-Boot | System startup | Termux:Boot / systemd / cron @reboot |

### Watchdog Exponential Backoff

```
Crash 1:  wait 5s   → restart
Crash 2:  wait 10s  → restart
Crash 3:  wait 20s  → restart
Crash 4:  wait 40s  → restart
Crash 5:  wait 80s  → restart
Crash 6+: wait 120s → restart (cap)
Crash 10+ in 1 hour: wait 5 min → cooldown → restart
```

## 6.2 Multi-Provider LLM

| Priority | Provider | Models | Key Rotation |
|----------|----------|--------|-------------|
| 1 | NVIDIA | Nemotron 70B Instruct | 1 key |
| 2 | Groq | Llama 3.1 8B Instant, Llama 3.3 70B Versatile | Up to 6 keys (round-robin) |
| 3 | OpenCode | opencode | Up to 2 keys (round-robin) |

Failover: NVIDIA → Groq (all keys) → OpenCode (all keys) → Degraded mode

## 6.3 Control Commands

| Command | Description |
|---------|-------------|
| `./hermes.sh start` | Start Hermes with watchdog |
| `./hermes.sh stop` | Stop everything |
| `./hermes.sh restart` | Restart |
| `./hermes.sh status` | System status |
| `./hermes.sh logs [type]` | Tail logs (hermes/watchdog/keeper/all) |
| `./hermes.sh health` | Run health check |
| `./hermes.sh watchdog` | Start watchdog only |
| `./hermes.sh install` | Install on-boot + auto-restart |

## 6.4 Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/status` | System health and PnL |
| `/market [SYMBOL]` | OHLCV data |
| `/analyze [SYMBOL]` | SMC Technical Analysis |
| `/risk` | Risk Officer status |
| `/strategy [SYMBOL]` | 3 scenarios |
| `/journal` | Trade stats |
| `/kill` | Kill switch status |
| `/help` | Full help |
| `/pnl` | PnL report |

---

# PART 7: PROJECT STRUCTURE

```
hermes-quant-os/
├── AGENTS.md              # Single Source of Truth
├── README.md              # Quick Start
├── CHANGELOG.md           # Version History
├── PR.md                  # Pull Request Guide
├── STRUCTURE.md           # Project Structure
├── ARCHITECTURE.md        # Architecture Deep Dive
├── UPGRADE_PLAN.md        # Autonomous Upgrade Roadmap
├── ALL.md                 # This document
├── requirements.txt       # Python Dependencies
├── hermes.sh              # Control Script
├── src/
│   ├── hermes_quant.py    # Main Agent Controller
│   ├── watchdog.py        # Watchdog Daemon
│   └── tools/             # 21 Trading Tools
│       ├── market_data_tool.py
│       ├── chart_vision_tool.py
│       ├── technical_analysis_tool.py
│       ├── macro_sentiment_tool.py
│       ├── smc_agent_enhanced.py
│       ├── news_sentinel.py
│       ├── market_state_engine.py
│       ├── strategy_tool.py
│       ├── risk_officer_tool.py
│       ├── portfolio_tool.py
│       ├── decision_engine.py
│       ├── pressure_engine.py
│       ├── strategy_lifecycle.py
│       ├── execution_tool.py
│       ├── kill_switch_tool.py
│       ├── autoswitch_engine.py
│       ├── journal_tool.py
│       ├── auditor_research_tool.py
│       ├── audit_logger.py
│       ├── backtest_engine.py
│       └── math_engine.py
├── scripts/
│   ├── keeper.py
│   ├── install_termux.sh
│   └── install_server.sh
├── schemas/
│   └── trading_journal.sql
├── config/
│   ├── hermes-quant.yaml
│   ├── system_prompt.py
│   └── .env
├── docs/
├── data/                  # Generated at runtime
├── logs/                  # Generated at runtime
└── .hermes/               # Generated at runtime
```

---

# PART 8: SOURCE REPOSITORY MAP

| Hermes Component | Source Repository | Version | Adaptation |
|------------------|-------------------|---------|------------|
| Core agent loop | `nousresearch/hermes` | latest | Added trading tools, Telegram bot, risk framework |
| 10 tools (v3.1) | `mulkymalikuldhrs/Quant-Nanggroe-AI` | v15.2.0 | Ported TypeScript → Python; Deterministic Agent Execution |
| Alpha factors | `mulkymalikuldhrs/Vibe-Trading` | v0.1.8 | 452 alphas - planned (PR-004) |
| Swarm pipeline | `mulkymalikuldhrs/AutoHedge` | latest | Director/Quant/Risk/Execution - planned (PR-005) |
| Colony framework | `mulkymalikuldhrs/AI-MultiColony-Ecosystem` | v8.0.0 | Agent registry concepts - architecture reference |

---

# PART 9: VERSION HISTORY

| Version | Date | Codename | Key Feature |
|---------|------|----------|-------------|
| 1.0.0 | 2026-05-20 | Genesis | 11 trading tools, Hermes Agent adaptation |
| 1.1.0 | 2026-05-21 | Polyglot | Multi-provider LLM support |
| 2.0.0 | 2026-05-22 | Immortal | Auto-restart & on-boot infrastructure |
| 3.0.0 | 2026-05-23 | Constitution | AGENTS.md constitutional framework |
| 3.1.0 | 2026-05-24 | Synthesis | Quant-Nanggroe-AI 10-tool integration |
| 3.2.0 | 2026-05-25 | Chronicle | Documentation suite & upgrade planning |
| 4.0.0 | 2026-05-25 | Production | Critical fixes: shared state, PnL sync, persistence, HTML Telegram, 21-tool routing |

---

# PART 10: AUTONOMOUS UPGRADE PLAN

## Stage Progression

| Stage | Name | Duration | Entry Criteria |
|-------|------|----------|----------------|
| 1 | Research Lab | 1-2 months | Default (current) |
| 2 | Paper Trading | 2-3 months | 30 days paper + owner sign-off |
| 3 | Micro Live | 3-4 months | Simulated Sharpe > 0.5 + 60 days |
| 4 | Semi-Autonomous | 4-6 months | 90 days micro live + positive PnL |
| 5 | Full Autonomous | Ongoing | 180 days semi-auto + Sharpe > 1.0 |

**Estimated time to Full Autonomous: 15-18 months**

## Priority Upgrade Tasks (Stage 1 → Stage 2)

1. **Autonomous Market Scanning** (3 days) — No user prompt needed
2. **Correlation Monitor** (2 days) — Block execution if correlation > 0.70
3. **Alpha Zoo Integration** (5 days) — 452 quant alphas from Vibe-Trading
4. **Web Dashboard v1** (7 days) — Basic monitoring interface
5. **Unit Test Coverage** (5 days) — >80% coverage for all tools

## Rollback Procedures

| Condition | Rollback Action |
|-----------|----------------|
| 3 consecutive losing weeks | Roll back to previous stage |
| Drawdown exceeds 8% | Immediate halt + review |
| Risk Officer VETO rate > 60% | Review strategy quality |
| System downtime > 24 hours/week | Fix infrastructure first |
| Any unauthorized trade | Immediate halt + full audit |

---

# PART 11: PROPOSED PULL REQUESTS

| PR | Scope | Type | Description |
|----|-------|------|-------------|
| PR-001 | agent | feat | Autonomous Decision Loop Enhancement |
| PR-002 | tools | feat | Correlation Monitor Integration |
| PR-003 | tools | feat | Darwinian Strategy Evolution |
| PR-004 | tools | feat | Vibe-Trading Alpha Zoo Integration (452 alphas) |
| PR-005 | execution | feat | AutoHedge Swarm Pipeline |

---

# PART 12: CROSS-REFERENCE ARCHITECTURE PATTERNS

## 12.1 From Quant-Nanggroe-AI

- **Deterministic Agent Execution**: Agents output numerical values, not subjective opinions
- **Neural Grounding**: All reasoning anchored in raw numerical data
- **Pressure Normalization**: BUY_PRESSURE/SELL_PRESSURE vectors (0.0-1.0)
- **Market Regime Gate**: NO_TRADE state halts entire pipeline
- **Darwinian Strategy Evolution**: Auto-KILL strategies with negative expectancy
- **Reality Simulation**: Backtesting with Dynamic Spread, Variable Slippage, Latency

## 12.2 From AI-MultiColony-Ecosystem

- **Unified Agent Registry**: Centralized tool dictionary
- **Graceful Degradation**: Tool import wrapped in try/except
- **Lifecycle Tracking**: Session-based restart count and crash logging
- **Multi-Agent Coordination**: Colony-style agent interaction patterns

## 12.3 From Vibe-Trading (Planned)

- **Alpha Purity Enforcement**: AST allowlist scan for factor code
- **Lookahead Bias Prevention**: Sentinel future-row injection tests
- **CI Grep Gates**: Reject unsafe yaml.load, trademark leaks, data leaks
- **450+ Pre-built Alphas**: qlib158, alpha101, gtja191, academic

## 12.4 From AutoHedge (Planned)

- **Swarm Pipeline**: Director → Quant → Risk → Execution
- **Structured Output**: JSON-formatted recommendations
- **Venue Abstraction**: Exchange-specific adapters behind common interface
- **Solana Integration**: Jupiter API for crypto venue support

---

**Document maintained by Mulky Malikul Dhaher**
**Repository: github.com/mulkymalikuldhrs/hermes-quant-os**
**This is not just documentation. This is the operational brain of an autonomous trading system.**
