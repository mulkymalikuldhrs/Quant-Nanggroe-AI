# HERMES QUANT OPERATING SYSTEM - CHANGELOG

All notable changes to Hermes Quant OS are documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

---

## [4.1.0] - 2026-03-05

### Fixed
- Replaced placeholder comment in `market_data_tool.py` with clear "not configured" status
- Verified all 21 tools have proper routing (no dead tools)

### Changed
- Minor documentation cleanup

---

## [4.0.0] - 2026-05-25 - PRODUCTION READY: Critical Security & State Fixes

### Fixed - CRITICAL (P0 Blockers)
- **Exposed API keys**: Created `.env.example` template with placeholders, added `.gitignore` to prevent credential leaks. All API keys in `.env` must be rotated immediately.
- **Risk Officer PnL completely broken**: `ExecutionTool` was creating fresh `RiskOfficerTool()` instances on every trade, meaning daily/weekly loss limits were NEVER enforced. Fixed by introducing `SharedState` singleton with shared tool instances.
- **Dual PnL desync**: `HermesQuantOS` and `RiskOfficerTool` tracked PnL independently and were never synchronized. Fixed: `RiskOfficerTool` is now the single source of truth, accessed via `SharedState.risk_officer`.
- **No data persistence**: All trading state (PnL, trades, kill switch, strategies) was lost on restart. Fixed: implemented SQLite persistence via `shared_state.py` using `schemas/trading_journal.sql`. State is restored on startup.
- **Telegram HTML stripped**: `send_telegram_message()` was stripping all HTML tags, making all formatted messages appear as plain text. Fixed: now uses `"parse_mode": "HTML"` in Telegram API payload with automatic fallback to plain text if HTML parsing fails.

### Fixed - HIGH (P1 Critical)
- **10 dead tools with no routing**: 10 of 21 tools (pressure_engine, decision_engine, market_state, news_sentinel, strategy_lifecycle, math_engine, backtest, autoswitch, smc_enhanced, audit) had zero routing in `process_with_tools()`. Fixed: added full routing for all 21 tools.
- **Tool count inconsistency**: Docstring said "13 Agents", system prompt said "11 tools", status showed "X/11". Fixed: all references now consistently say "21 agents across 5 layers".

### Added
- `src/tools/shared_state.py` — SharedState singleton with SQLite persistence, shared tool instances, state restore on startup
- `config/.env.example` — Template with placeholder values (no real keys)
- `.gitignore` — Prevents committing .env, __pycache__, .db files, logs, PID files

### Changed
- `execution_tool.py` — Now uses `SharedState.risk_officer` instead of creating fresh instances; logs trades to SQLite; auto-persists PnL after close
- `hermes_quant.py` — Uses SharedState for shared tool instances; PnL reads from RiskOfficer (single source); 21-tool routing; HTML Telegram messages; removed unused `import random`; moved `import re` to top level
- `requirements.txt` — Added `pandas>=2.0.0` (needed by yfinance)
- `config/.env` — Fixed hardcoded paths (now optional, defaults to relative); updated version to 4.0.0

---

## [3.2.0] - 2026-05-25 - Documentation & Autonomous Upgrade Planning

### Added
- `CHANGELOG.md` - Complete version history and release notes
- `PR.md` - Pull Request templates and contribution guidelines
- `STRUCTURE.md` - Full project structure documentation with file-by-file breakdown
- `ARCHITECTURE.md` - Deep-dive system architecture referencing all source repos
- `UPGRADE_PLAN.md` - Autonomous upgrade roadmap from Stage 1 to Full Autonomous
- `ALL.md` - Comprehensive combined reference document
- `docs/` directory for supplementary documentation

### Changed
- Consolidated reference architecture from `Quant-Nanggroe-AI`, `AI-MultiColony-Ecosystem`, `Vibe-Trading`, and `AutoHedge` into unified documentation
- Mapped all 21 active tools against 5-layer agent taxonomy

---

## [3.1.0] - 2026-05-24 - Cross-Repo Integration Upgrade

### Added - Quant-Nanggroe-AI Integration (10 new tools)
- `pressure_engine.py` - Pressure Normalization Engine converting multi-agent sensor outputs into BUY_PRESSURE / SELL_PRESSURE vectors (0.0-1.0)
- `decision_engine.py` - Decision Synthesis Engine with Decision Matrix for compressed execution outputs (Entry, SL, TP1-TP3)
- `market_state_engine.py` - Market Regime Engine detecting TRENDING_UP, TRENDING_DOWN, RANGE_BOUND, RISK_OFF, PANIC, NO_TRADE states
- `news_sentinel.py` - News Sentinel with logarithmic time decay and event classification for macro impact scoring
- `strategy_lifecycle.py` - Darwinian Strategy Lifecycle Manager that auto-KILLs strategies with negative expectancy over 20 trades
- `math_engine.py` - Mathematical computation engine for statistical analysis and probability calculations
- `backtest_engine.py` - Backtesting engine with Dynamic Spread, Variable Slippage, and 100-500ms Latency Simulation
- `autoswitch_engine.py` - Auto-Switch Engine for seamless provider failover across NVIDIA/Groq/OpenCode
- `smc_agent_enhanced.py` - Enhanced SMC Agent with Order Block, FVG, Liquidity Sweep detection and Contextual Neural Grounding
- `audit_logger.py` - Comprehensive Audit Logger with full trail from sensor to final decision

### Changed
- Agent count expanded from 13 to 21 active tools
- Tool initialization in `hermes_quant.py` updated to load all 21 tools
- System prompt updated to reference all 21 tools

### Reference
- Sourced from `github.com/mulkymalikuldhrs/Quant-Nanggroe-AI` v15.2.0 Deterministic Agent Execution framework

---

## [3.0.0] - 2026-05-23 - AGENTS.md Constitutional Framework

### Added
- `AGENTS.md` - Single Source of Truth and Operational Constitution with 9 sections
- Core Principles (NON-NEGOTIABLE): Autonomous by default, User is final authority, Reality > Politeness, Consistency over novelty, Everything has consequence, Single Source of Truth, Risk Officer FULL VETO
- Hardcoded risk rules: 0.5% per trade, 1% daily, 3% weekly
- 5 Deployment Stages: Research Lab, Paper Trading, Micro Live, Semi-Autonomous, Full Autonomous
- Top Down Framework with SMC Continuation Bias
- 3-Scenario Analysis requirement (Bullish/Bearish/Neutral) before any trade idea
- Confluence Scoring system (minimum 3/5 required)
- Kill Switch with auto-activation on risk limit breach
- Wallet targets: Tron (PRIORITAS), Shiba Inu
- Communication protocol for trade signals

### Changed
- System prompt rewritten to enforce AGENTS.md principles
- Decision framework updated with high-risk keyword detection and kill switch logic
- All trading tools aligned to constitutional risk rules

---

## [2.0.0] - 2026-05-22 - Auto-Restart & On-Boot Infrastructure

### Added
- `src/watchdog.py` - Watchdog daemon monitoring Hermes every 10 seconds with exponential backoff (5s to 120s cap)
- `scripts/keeper.py` - Cron-based lightweight health monitor running every 1 minute
- `hermes.sh` - Main control script with start/stop/restart/status/logs/health/watchdog/install commands
- `scripts/install_termux.sh` - Android Termux installer with Termux:Boot integration
- `scripts/install_server.sh` - Linux server installer with systemd service
- 3-Layer Auto-Restart: Watchdog (10s) + Keeper (1min cron) + On-Boot (Termux/systemd/cron)
- Crash loop detection: max 10 restarts per hour, then 5-minute cooldown
- Telegram alerts on every crash/restart event
- Health status file at `.hermes/health.json`
- PID file management for process tracking
- Graceful shutdown with SIGINT/SIGTERM handling
- Log rotation with 7-day retention

### Changed
- Hermes main agent now runs under watchdog supervision by default
- Fallback mode: if watchdog fails to start, Hermes runs directly without protection

---

## [1.1.0] - 2026-05-21 - Multi-Provider LLM Support

### Added
- NVIDIA API integration (Nemotron 70B via integrate.api.nvidia.com)
- Groq API multi-key rotation (up to 6 keys with round-robin)
- OpenCode API integration (2 keys with round-robin)
- Automatic provider failover: NVIDIA -> Groq -> OpenCode
- Provider status tracking and logging

### Changed
- Response generation now tries multiple providers before failing
- Provider rotation on API errors
- Degraded mode message when all providers fail

---

## [1.0.0] - 2026-05-20 - Initial Release (Hermes Agent Adaptation)

### Added
- Core agent adapted from Nous Research Hermes Agent (`github.com/nousresearch/hermes`)
- `src/hermes_quant.py` - Main agent loop with Telegram bot interface
- `src/tools/market_data_tool.py` - OHLCV data via yfinance, economic calendar, market overview
- `src/tools/chart_vision_tool.py` - Chart image analysis via vision LLM
- `src/tools/technical_analysis_tool.py` - SMC structure detection (BOS/CHoCH/OB/FVG/sweeps), indicators
- `src/tools/macro_sentiment_tool.py` - Risk-on/off regime detection, sentiment analysis, fundamental data
- `src/tools/strategy_tool.py` - 3-scenario generator (bullish/bearish/neutral) with confluence scoring
- `src/tools/risk_officer_tool.py` - FULL VETO authority, 9 checkpoints, lot sizing with hardcoded limits
- `src/tools/portfolio_tool.py` - Portfolio assessment, allocation suggestions
- `src/tools/execution_tool.py` - Paper/MT5/OANDA/Binance execution with risk approval gate
- `src/tools/kill_switch_tool.py` - Emergency halt, auto-trigger monitoring, manual reset
- `src/tools/journal_tool.py` - Trade logging, PnL calculation, performance stats
- `src/tools/auditor_research_tool.py` - Trade audit (plan vs execution), edge decay detection, strategy refinement
- `schemas/trading_journal.sql` - 7-table SQL schema for full audit trail
- `config/hermes-quant.yaml` - System configuration
- `config/system_prompt.py` - Trading-focused system prompt
- `requirements.txt` - Python dependencies
- `README.md` - Quick start guide
- Telegram bot commands: /start, /status, /market, /analyze, /risk, /strategy, /journal, /kill, /help, /pnl
- Tool call format: `[TOOL:tool_name]arg1|arg2[/TOOL]`
- Session memory in JSON + Markdown with auto-cleanup (last 10 files)
- Conversation history with 100-item rolling window
- Decision logging with full audit trail

### Reference
- Base agent: `github.com/NousResearch/hermes-agent` (⭐165k)
- Inspiration: `github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem`
- Inspiration: `github.com/mulkymalikuldhrs/Quant-Nanggroe-AI`
- Inspiration: `github.com/mulkymalikuldhrs/Vibe-Trading`
- Inspiration: `github.com/mulkymalikuldhrs/AutoHedge`

---

## Version Summary

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

**Maintained by Mulky Malikul Dhaher**
**Repository: github.com/mulkymalikuldhrs/HermesQuantOS**
