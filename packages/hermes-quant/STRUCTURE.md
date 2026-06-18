# HERMES QUANT OPERATING SYSTEM - PROJECT STRUCTURE

## Directory Tree

```
hermes-quant-os/
├── AGENTS.md                          # Single Source of Truth & Operational Constitution
├── README.md                          # Quick Start Guide
├── CHANGELOG.md                       # Version History & Release Notes
├── PR.md                              # Pull Request Guide & Templates
├── STRUCTURE.md                       # This file - Project Structure
├── ARCHITECTURE.md                    # System Architecture Deep Dive
├── UPGRADE_PLAN.md                    # Autonomous Upgrade Roadmap
├── ALL.md                             # Comprehensive Combined Reference
├── requirements.txt                   # Python Dependencies
├── hermes.sh                          # Main Control Script (start/stop/restart/status/logs/health/install)
│
├── src/                               # Source Code
│   ├── hermes_quant.py                # Main Agent Controller (HermesQuantOS class)
│   ├── watchdog.py                    # Watchdog Daemon (10s check, exponential backoff)
│   │
│   └── tools/                         # Trading Tools (21 Agent Modules)
│       ├── __init__.py                # Package init
│       │
│       │   # ── L1: Data Layer ──────────────────────────────
│       ├── market_data_tool.py        # Market Data Agent: OHLCV, economic calendar, market overview
│       ├── chart_vision_tool.py       # Chart Vision Agent: Chart image analysis via vision LLM
│       │
│       │   # ── L2: Analysis Layer ──────────────────────────
│       ├── technical_analysis_tool.py # Technical Analyst: SMC (BOS/CHoCH/OB/FVG/sweeps), indicators
│       ├── macro_sentiment_tool.py    # Macro/Fundamental/Sentiment: Risk-on/off regime, economic context
│       ├── smc_agent_enhanced.py      # Enhanced SMC Agent: Order Blocks, FVG, Liquidity Sweeps + Neural Grounding
│       ├── news_sentinel.py           # News Sentinel: Macro impact scoring with logarithmic time decay
│       ├── market_state_engine.py     # Market Regime Engine: TRENDING/RANGE/RISK_OFF/PANIC/NO_TRADE detection
│       │
│       │   # ── L3: Decision Layer ──────────────────────────
│       ├── strategy_tool.py           # Strategy Agent: 3-scenario analysis, confluence scoring
│       ├── risk_officer_tool.py       # Risk Officer: FULL VETO, 9 checkpoints, lot sizing (HARDCODED limits)
│       ├── portfolio_tool.py          # Portfolio Manager: Allocation, position management
│       ├── decision_engine.py         # Decision Synthesis Engine: Decision Matrix → Entry/SL/TP1-3
│       ├── pressure_engine.py         # Pressure Normalization: BUY_PRESSURE / SELL_PRESSURE vectors (0.0-1.0)
│       ├── strategy_lifecycle.py      # Darwinian Strategy Lifecycle: Auto-KILL on negative expectancy
│       │
│       │   # ── L4: Execution Layer ─────────────────────────
│       ├── execution_tool.py          # Execution Agent: Paper/MT5/OANDA/Binance execution
│       ├── kill_switch_tool.py        # Kill Switch: Emergency halt, auto-trigger, manual reset
│       ├── autoswitch_engine.py       # Auto-Switch Engine: Seamless provider failover
│       │
│       │   # ── L5: Learning Layer ──────────────────────────
│       ├── journal_tool.py            # Journal Agent: Trade logging, PnL, performance stats
│       ├── auditor_research_tool.py   # Post-Trade Auditor + Research: Plan vs execution, edge decay
│       ├── audit_logger.py            # Audit Logger: Full trail from sensor to final decision
│       ├── backtest_engine.py         # Backtest Engine: Dynamic Spread, Slippage, Latency Simulation
│       └── math_engine.py             # Math Engine: Statistical analysis, probability calculations
│
├── scripts/                           # Infrastructure Scripts
│   ├── keeper.py                      # Cron-based health monitor (1-minute intervals)
│   ├── install_termux.sh             # Android Termux installer with Termux:Boot
│   └── install_server.sh             # Linux server installer with systemd
│
├── schemas/                           # Database Schemas
│   └── trading_journal.sql           # 7-table SQL schema for full audit trail
│
├── config/                            # Configuration Files
│   ├── hermes-quant.yaml             # Main system configuration
│   ├── system_prompt.py              # Trading-focused system prompt
│   └── .env                          # Environment variables (API keys, tokens)
│
├── docs/                              # Documentation
│   └── (supplementary docs)
│
├── data/                              # Runtime Data (generated)
│   ├── sessions.json                 # Session memory (conversation history, decisions, PnL)
│   └── memory_*.md                   # Markdown memory exports (last 10 retained)
│
├── logs/                              # Runtime Logs (generated)
│   ├── hermes_quant_YYYYMMDD.log    # Daily Hermes log
│   ├── watchdog_stdout.log          # Watchdog output log
│   ├── keeper_YYYYMMDD.log          # Keeper log
│   └── boot.log                     # On-boot startup log
│
└── .hermes/                           # Internal State (generated)
    └── health.json                   # Health status file (read by keeper/status)
```

---

## File-by-File Breakdown

### Root Files

| File | Purpose | Size | Modified |
|------|---------|------|----------|
| `AGENTS.md` | Single Source of Truth - constitutional rules, risk parameters, agent taxonomy, trading framework | ~8KB | v3.0.0 |
| `README.md` | Quick start, architecture overview, commands, risk summary | ~2KB | v1.0.0 |
| `CHANGELOG.md` | Complete version history from v1.0.0 to current | ~8KB | v3.2.0 |
| `PR.md` | PR templates, review criteria, proposed PRs, workflow | ~6KB | v3.2.0 |
| `STRUCTURE.md` | This file - project structure documentation | ~5KB | v3.2.0 |
| `ARCHITECTURE.md` | Deep-dive architecture with data flow diagrams | ~10KB | v3.2.0 |
| `UPGRADE_PLAN.md` | Autonomous upgrade roadmap from Stage 1 to Full Autonomous | ~8KB | v3.2.0 |
| `ALL.md` | Comprehensive combined reference document | ~35KB | v3.2.0 |
| `requirements.txt` | Python dependencies: aiohttp, python-dotenv, yfinance, requests | ~100B | v1.0.0 |
| `hermes.sh` | Bash control script for all operations | ~10KB | v2.0.0 |

### Source Code (`src/`)

| File | Lines | Purpose | Layer | Source |
|------|-------|---------|-------|--------|
| `hermes_quant.py` | ~900 | Main agent loop, Telegram bot, tool orchestration, memory management | All | Original |
| `watchdog.py` | ~200 | Process monitor with exponential backoff, crash loop detection | Infra | v2.0.0 |

### Trading Tools (`src/tools/`)

| File | Layer | Agent Name | Key Methods | Source Repo |
|------|-------|------------|-------------|-------------|
| `market_data_tool.py` | L1 | Market Data Agent | `get_ohlcv()`, `get_economic_calendar()`, `get_market_overview()` | Original |
| `chart_vision_tool.py` | L1 | Chart Vision Agent | `analyze_chart()` | Original |
| `technical_analysis_tool.py` | L2 | Technical Analyst | `analyze()`, SMC detection | Original |
| `macro_sentiment_tool.py` | L2 | Macro/Sentiment | `get_regime()`, `get_sentiment()` | Original |
| `smc_agent_enhanced.py` | L2 | SMC Enhanced | Order Block, FVG, Liquidity Sweep | Quant-Nanggroe-AI |
| `news_sentinel.py` | L2 | News Sentinel | `score_impact()`, time decay | Quant-Nanggroe-AI |
| `market_state_engine.py` | L2 | Market Regime Engine | `detect_regime()`, NO_TRADE gate | Quant-Nanggroe-AI |
| `strategy_tool.py` | L3 | Strategy Agent | `generate_scenarios()`, confluence | Original |
| `risk_officer_tool.py` | L3 | Risk Officer (VETO) | `check_trade()`, 9 checkpoints | Original |
| `portfolio_tool.py` | L3 | Portfolio Manager | `assess()`, `status()` | Original |
| `decision_engine.py` | L3 | Decision Synthesis | Decision Matrix, Entry/SL/TP | Quant-Nanggroe-AI |
| `pressure_engine.py` | L3 | Pressure Normalization | BUY/SELL pressure vectors | Quant-Nanggroe-AI |
| `strategy_lifecycle.py` | L3 | Strategy Lifecycle | Auto-KILL, expectancy tracking | Quant-Nanggroe-AI |
| `execution_tool.py` | L4 | Execution Agent | `paper_trade()`, `status()` | Original |
| `kill_switch_tool.py` | L4 | Kill Switch | `activate()`, `status()`, auto-trigger | Original |
| `autoswitch_engine.py` | L4 | Auto-Switch Engine | Provider failover | Quant-Nanggroe-AI |
| `journal_tool.py` | L5 | Journal Agent | `log_trade()`, `get_stats()` | Original |
| `auditor_research_tool.py` | L5 | Auditor + Research | `audit_recent()`, `suggest_improvements()` | Original |
| `audit_logger.py` | L5 | Audit Logger | Full decision trail | Quant-Nanggroe-AI |
| `backtest_engine.py` | L5 | Backtest Engine | Spread, Slippage, Latency sim | Quant-Nanggroe-AI |
| `math_engine.py` | L5 | Math Engine | Statistical computations | Quant-Nanggroe-AI |

### Infrastructure Scripts (`scripts/`)

| File | Purpose | Trigger |
|------|---------|---------|
| `keeper.py` | Lightweight health check: verifies Hermes PID, checks health.json, restarts if needed | Cron (1-min) |
| `install_termux.sh` | Installs Python deps, creates Termux:Boot entry, sets up data/logs directories | Manual |
| `install_server.sh` | Installs Python deps, creates systemd service, enables on-boot | Manual (sudo) |

### Database Schema (`schemas/`)

| Table | Purpose |
|-------|---------|
| `trades` | Full trade records with entry/exit/SL/TP |
| `trade_audit` | Plan vs execution comparison |
| `risk_decisions` | Risk Officer approvals/rejections |
| `kill_switch_events` | Kill switch activation log |
| `strategy_performance` | Strategy metrics and lifecycle |
| `market_regime_log` | Market regime transitions |
| `agent_decisions` | All agent decision trails |

### Configuration (`config/`)

| File | Purpose |
|------|---------|
| `hermes-quant.yaml` | System configuration: model names, intervals, limits |
| `system_prompt.py` | AGENTS.md-aligned system prompt for LLM |
| `.env` | API keys (NVIDIA, Groq, OpenCode, Telegram), chat ID, model names |

---

## Source Repository Map

| Hermes Component | Source Repository | Version | Adaptation Notes |
|------------------|-------------------|---------|------------------|
| Core agent loop | `nousresearch/hermes` | latest | Adapted from Hermes Agent; added trading tools, Telegram bot, risk framework |
| 10 tools (v3.1) | `mulkymalikuldhrs/Quant-Nanggroe-AI` | v15.2.0 | Ported from TypeScript services to Python tools; adapted Deterministic Agent Execution |
| Alpha factors | `mulkymalikuldhrs/Vibe-Trading` | v0.1.8 | 452 alphas (qlib158, alpha101, gtja191, academic) - planned integration (PR-004) |
| Swarm pipeline | `mulkymalikuldhrs/AutoHedge` | latest | Director/Quant/Risk/Execution pipeline - planned integration (PR-005) |
| Colony framework | `mulkymalikuldhrs/AI-MultiColony-Ecosystem` | v8.0.0 | Agent registry, lifecycle management concepts - architecture reference |

---

**Document maintained by Mulky Malikul Dhaher**
**Repository: github.com/mulkymalikuldhrs/hermes-quant-os**
