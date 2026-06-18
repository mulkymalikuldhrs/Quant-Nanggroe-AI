# HERMES QUANT OPERATING SYSTEM - ARCHITECTURE

## 1. System Overview

Hermes Quant Operating System is an autonomous multi-agent trading and research infrastructure designed for consistent capital growth with strict risk preservation. The system operates on the principle that trading decisions must be deterministic, data-grounded, and subject to absolute risk constraints that no agent can override.

The architecture draws from four key reference repositories maintained by the owner (Mulky Malikul Dhaher), synthesizing their strongest patterns into a unified trading system:

- **Quant-Nanggroe-AI** (v15.2.0): Deterministic Agent Execution, Pressure Normalization, Market Regime Engine, Darwinian Strategy Evolution
- **AI-MultiColony-Ecosystem** (v8.0.0): Unified Agent Registry, multi-agent lifecycle management, colony coordination
- **Vibe-Trading** (v0.1.8): 450+ pre-built quant alphas, alpha purity enforcement, factor analysis
- **AutoHedge**: Swarm pipeline (Director -> Quant -> Risk -> Execution), venue-specific integration

The foundational agent framework is adapted from **Nous Research Hermes Agent** (`nousresearch/hermes`), extended with trading-specific tools, constitutional risk rules, and auto-restart infrastructure.

---

## 2. 5-Layer Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HERMES QUANT OS                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  L5: LEARNING LAYER                                      │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │ Journal  │  │ Post-Trade   │  │ Research /       │   │   │
│  │  │ Agent    │  │ Auditor      │  │ Improvement      │   │   │
│  │  └──────────┘  └──────────────┘  └──────────────────┘   │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │ Audit    │  │ Backtest     │  │ Math Engine      │   │   │
│  │  │ Logger   │  │ Engine       │  │                  │   │   │
│  │  └──────────┘  └──────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  L4: EXECUTION LAYER                                     │   │
│  │  ┌──────────────────┐  ┌────────────────────────────┐   │   │
│  │  │ Execution Agent  │  │ Kill Switch (EMERGENCY)    │   │   │
│  │  │ Paper/MT5/OANDA  │  │ Auto-trigger on limit      │   │   │
│  │  │ /Binance         │  │ breach                     │   │   │
│  │  └──────────────────┘  └────────────────────────────┘   │   │
│  │  ┌──────────────────┐                                    │   │
│  │  │ Auto-Switch      │                                    │   │
│  │  │ Engine           │                                    │   │
│  │  └──────────────────┘                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  L3: DECISION LAYER                                      │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │ Strategy │  │ Risk Officer │  │ Portfolio        │   │   │
│  │  │ Agent    │  │ (FULL VETO)  │  │ Manager          │   │   │
│  │  └──────────┘  └──────────────┘  └──────────────────┘   │   │
│  │  ┌──────────────────┐  ┌────────────────────────────┐   │   │
│  │  │ Decision         │  │ Pressure Normalization     │   │   │
│  │  │ Synthesis Engine │  │ Engine                     │   │   │
│  │  └──────────────────┘  └────────────────────────────┘   │   │
│  │  ┌──────────────────┐                                    │   │
│  │  │ Strategy         │                                    │   │
│  │  │ Lifecycle Mgr    │                                    │   │
│  │  └──────────────────┘                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  L2: ANALYSIS LAYER                                      │   │
│  │  ┌──────────────────┐  ┌────────────────────────────┐   │   │
│  │  │ Technical        │  │ Macro / Sentiment          │   │   │
│  │  │ Analyst          │  │                            │   │   │
│  │  └──────────────────┘  └────────────────────────────┘   │   │
│  │  ┌──────────────────┐  ┌────────────────────────────┐   │   │
│  │  │ SMC Agent        │  │ News Sentinel              │   │   │
│  │  │ Enhanced         │  │ (Log Decay)                │   │   │
│  │  └──────────────────┘  └────────────────────────────┘   │   │
│  │  ┌──────────────────┐                                    │   │
│  │  │ Market Regime    │                                    │   │
│  │  │ Engine           │                                    │   │
│  │  └──────────────────┘                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  L1: DATA LAYER                                          │   │
│  │  ┌──────────────────┐  ┌────────────────────────────┐   │   │
│  │  │ Market Data      │  │ Chart Vision               │   │   │
│  │  │ Agent            │  │ Agent                      │   │   │
│  │  └──────────────────┘  └────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CONSTITUTIONAL GUARD (AGENTS.md)                        │   │
│  │  Risk Rules: 0.5%/trade | 1%/day | 3%/week              │   │
│  │  Risk Officer: FULL VETO (no override)                   │   │
│  │  Kill Switch: Auto-trigger on breach                     │   │
│  │  Deployment Stage Gate: Requires performance metrics      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow Architecture

### 3.1 Trading Decision Pipeline

```
Market Data (L1)
    │
    ├── OHLCV Data (yfinance/MT5/OANDA/Binance)
    ├── Chart Images (for Vision LLM)
    │
    ▼
Analysis (L2)
    │
    ├── Market Regime Engine ──→ TRENDING / RANGE / RISK_OFF / PANIC / NO_TRADE
    │                            │
    │                            └── If NO_TRADE → STOP (Kill Switch)
    │
    ├── Technical Analyst ──→ SMC Structure (BOS/CHoCH/OB/FVG/Sweeps)
    ├── SMC Agent Enhanced ──→ Order Blocks + Liquidity Zones
    ├── Macro/Sentiment ──→ Risk-on/off + Economic Context
    ├── News Sentinel ──→ Impact Score (with Log Time Decay)
    │
    ▼
Pressure Normalization (L3 sub-process)
    │
    ├── Convert all L2 outputs to numerical vectors
    ├── BUY_PRESSURE: 0.0 - 1.0
    ├── SELL_PRESSURE: 0.0 - 1.0
    │
    ▼
Decision (L3)
    │
    ├── Strategy Agent ──→ 3 Scenarios (Bullish/Bearish/Neutral)
    │                        Each with: Entry, SL, TP, R:R
    │
    ├── Confluence Scoring ──→ Minimum 3/5 required
    │   1. Trend alignment with HTF
    │   2. BOS confirmation
    │   3. Order Block presence
    │   4. RSI not overbought/oversold against
    │   5. EMA alignment
    │
    ├── Risk Officer ──→ 9 Checkpoint Review
    │   1. Account balance check
    │   2. Daily loss limit (1%)
    │   3. Weekly loss limit (3%)
    │   4. Position size check (0.5% max risk)
    │   5. Risk:Reward ratio (min 1:2)
    │   6. Stop loss present (mandatory)
    │   7. Confluence score (min 3/5)
    │   8. Market regime compatibility
    │   9. Correlation check (planned: <0.70)
    │
    │   ──→ VETO = Trade BLOCKED (no override possible)
    │   ──→ APPROVE = Trade proceeds to execution
    │
    ├── Decision Synthesis Engine ──→ Compressed Output: Entry, SL, TP1-3
    ├── Portfolio Manager ──→ Allocation check
    ├── Strategy Lifecycle ──→ Strategy health check
    │
    ▼
Execution (L4)
    │
    ├── Execution Agent ──→ Paper/MT5/OANDA/Binance
    │   ├── Paper mode (current: Research Lab)
    │   ├── Risk approval gate
    │   └── Order placement
    │
    ├── Kill Switch Monitor ──→ Auto-trigger if limits breached
    │
    ▼
Learning (L5)
    │
    ├── Journal Agent ──→ Log trade with full details
    ├── Post-Trade Auditor ──→ Compare plan vs execution
    ├── Research/Improvement ──→ Detect edge decay, suggest refinements
    ├── Audit Logger ──→ Full trail from sensor to decision
    ├── Backtest Engine ──→ Validate with realistic conditions
    └── Math Engine ──→ Statistical analysis of results
```

### 3.2 Message Flow (Telegram Interface)

```
User (Telegram)
    │
    ▼
Telegram Bot API (polling, 3s interval)
    │
    ▼
HermesQuantOS.process_telegram_update()
    │
    ├── Filter: chat_id must match TELEGRAM_CHAT_ID
    ├── Dedup: message_id tracking (last 100)
    │
    ├── Command? (/start, /status, /market, etc.)
    │   └── handle_command() ──→ Direct tool call ──→ Telegram response
    │
    ├── Tool Call? ([TOOL:name]args[/TOOL])
    │   └── process_with_tools() ──→ Tool execution ──→ Telegram response
    │
    └── Free Text?
        ├── decision_framework() check
        │   ├── BLOCKED (risk limits) ──→ Kill switch message
        │   ├── NEED_CONFIRMATION (high risk) ──→ Confirmation request
        │   └── PROCEED ──→ LLM generation
        │
        └── generate_response()
            ├── Try NVIDIA (Nemotron 70B)
            ├── Try Groq (Llama 3.1 8B / 3.3 70B)
            ├── Try OpenCode
            └── All failed ──→ Degraded mode message
```

---

## 4. Infrastructure Architecture

### 4.1 3-Layer Auto-Restart

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: ON-BOOT                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Termux:Boot  │  │ systemd      │  │ cron @reboot     │  │
│  │ (Android)    │  │ (Linux)      │  │ (Fallback)       │  │
│  │ sleep 10     │  │ After=network│  │ sleep 30         │  │
│  │ → hermes.sh  │  │ → hermes.sh  │  │ → hermes.sh      │  │
│  │   start      │  │   start      │  │   start          │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: KEEPER (Cron, 1-minute interval)                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Check hermes.pid exists and process is alive     │    │
│  │ 2. Check watchdog.pid exists and process is alive   │    │
│  │ 3. Read .hermes/health.json                         │    │
│  │ 4. If Hermes dead AND Watchdog dead → restart both  │    │
│  │ 5. Log to logs/keeper_YYYYMMDD.log                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: WATCHDOG (10-second interval)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Check if Hermes process is alive (every 10s)     │    │
│  │ 2. If dead → restart with exponential backoff        │    │
│  │    Delay: 5s → 10s → 20s → 40s → 80s → 120s (cap) │    │
│  │ 3. Crash loop detection: max 10 restarts/hour       │    │
│  │    If exceeded → 5-minute cooldown                  │    │
│  │ 4. Telegram alert on every crash/restart            │    │
│  │ 5. Update .hermes/health.json                       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  HERMES QUANT OS (Main Process)                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ - Telegram bot polling (3s interval)                │    │
│  │ - Tool orchestration (21 tools)                     │    │
│  │ - Multi-provider LLM (NVIDIA → Groq → OpenCode)    │    │
│  │ - Session memory (JSON + Markdown)                  │    │
│  │ - Risk framework (hardcoded limits)                 │    │
│  │ - Signal handling (SIGINT, SIGTERM)                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Multi-Provider LLM Architecture

```
generate_response(prompt)
    │
    ├── Provider Priority Queue:
    │
    │   1. NVIDIA API
    │      ├── Model: meta/llama-3.1-nemotron-70b-instruct
    │      ├── Endpoint: https://integrate.api.nvidia.com/v1
    │      └── 1 key (NVIDIA_API_KEY)
    │
    │   2. Groq API (round-robin, up to 6 keys)
    │      ├── Models: llama-3.1-8b-instant, llama-3.3-70b-versatile
    │      ├── Endpoint: https://api.groq.com/openai/v1
    │      └── Key rotation: groq_key_index % len(GROQ_API_KEYS)
    │
    │   3. OpenCode API (round-robin, up to 2 keys)
    │      ├── Model: opencode
    │      ├── Endpoint: https://api.opencode.ai/v1
    │      └── Key rotation: opencode_key_index % len(OPENCODE_API_KEYS)
    │
    └── Failure Handling:
        ├── Try next provider on any error
        ├── Log warning with error details
        └── Return degraded mode message if all fail
```

---

## 5. Risk Architecture (Constitutional Guard)

The risk system is architecturally independent from the LLM reasoning layer. Risk decisions are made by deterministic Python code with hardcoded constants, not by the LLM. This prevents any form of "reasoning around" safety rules.

### 5.1 Risk Rules (Immutable Constants)

```python
RISK_MAX_PER_TRADE = 0.005     # 0.5% - NO OVERRIDE
RISK_DAILY_MAX = 0.01          # 1%   - NO OVERRIDE
RISK_WEEKLY_MAX = 0.03         # 3%   - NO OVERRIDE
```

These are Python module-level constants in `hermes_quant.py`. They are not loaded from configuration files, not stored in environment variables, and not passed as function parameters. To change them requires editing the source code directly, which would be caught by PR review.

### 5.2 Kill Switch Architecture

```
Risk Check (every incoming message)
    │
    ├── abs(daily_pnl) >= RISK_DAILY_MAX (1%)?
    │   └── YES → BLOCKED: "Kill Switch AKTIF - Daily Limit"
    │            Trading halted for the day
    │            No override possible
    │
    ├── abs(weekly_pnl) >= RISK_WEEKLY_MAX (3%)?
    │   └── YES → BLOCKED: "Kill Switch AKTIF - Weekly Limit"
    │            Trading halted for the week
    │            No override possible
    │
    └── High-risk keyword detected?
        ├── 'execute trade', 'open position', 'place order'
        ├── 'buy now', 'sell now', 'market order'
        ├── 'real money', 'live trade'
        ├── 'override risk', 'skip risk'
        └── YES → NEED_CONFIRMATION: User must explicitly confirm
```

### 5.3 Risk Officer 9-Checkpoint Gate

Every trade must pass through the Risk Officer's 9 checkpoints before execution. The Risk Officer has FULL VETO authority - if any checkpoint fails, the trade is rejected and no other agent can override this decision.

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
| 9 | Correlation Check | Active positions correlation < 0.70 (planned) | Quant-Nanggroe-AI |

---

## 6. Memory Architecture

### 6.1 Session Memory (JSON)

```json
{
    "history": [...],           // Last 100 conversations
    "decisions": [...],         // Last 50 agent decisions
    "daily_pnl": 0.0,          // Running daily PnL
    "weekly_pnl": 0.0,         // Running weekly PnL
    "last_update": "ISO-8601",
    "session_id": "YYYYMMDD_HHMMSS"
}
```

### 6.2 Markdown Memory

- Generated every 5 conversations
- Rolling window: last 10 files retained
- Contains: session metadata, PnL, recent conversations, decisions log

### 6.3 Health Status

```json
{
    "status": "running|stopped|crashed",
    "pid": 12345,
    "uptime_seconds": 86400,
    "restart_count": 3,
    "last_check": "ISO-8601"
}
```

---

## 7. Deployment Architecture

### 7.1 Current: Research Lab (Stage 1)

- Paper trading only
- No real money at risk
- All executions logged but not sent to brokers
- Full audit trail for strategy validation

### 7.2 Target Platforms

| Platform | Runtime | On-Boot | Status |
|----------|---------|---------|--------|
| Android (Termux) | Python 3.x in Termux | Termux:Boot plugin | Supported |
| Linux Server | Python 3.x | systemd service | Supported |
| Any (fallback) | Python 3.x | cron @reboot | Supported |
| VPS (planned) | Docker container | Docker restart policy | Planned |

### 7.3 Communication Channels

| Channel | Purpose | Direction |
|---------|---------|-----------|
| Telegram Bot | User commands, status updates, alerts | Bidirectional |
| Log Files | Debug, audit trail | Write-only |
| Health JSON | Process status for keeper | Write-only |
| Session JSON | Persistent memory across restarts | Read/Write |

---

## 8. Cross-Reference: Source Architecture Patterns

### 8.1 From Quant-Nanggroe-AI: Deterministic Agent Execution

The most significant architectural pattern adopted from Quant-Nanggroe-AI is the **Deterministic Agent Execution** framework. In this model, agents are forbidden from providing subjective opinions or "vibes-based" analysis. Instead, they output normalized numerical values (Pressure vectors 0.0-1.0) that are compiled by the Pressure Normalization Engine and fed into the Decision Synthesis Engine. This eliminates LLM hallucination from the decision pipeline.

Key patterns adopted:
- **Neural Grounding**: All reasoning anchored in raw numerical data from L1/L2 sources
- **Pressure-Based Output**: Agents output BUY_PRESSURE/SELL_PRESSURE instead of direct trade signals
- **Market Regime Gate**: NO_TRADE state halts the entire pipeline below it
- **Darwinian Strategy Evolution**: Auto-KILL strategies with negative expectancy
- **Reality Simulation**: Backtesting with Dynamic Spread, Variable Slippage, Latency

### 8.2 From AI-MultiColony-Ecosystem: Unified Agent Registry

The agent management pattern from AI-MultiColony-Ecosystem inspires the tool initialization structure in Hermes. While the current implementation uses a simple dictionary, the planned evolution will incorporate a proper agent registry with lifecycle management, metadata storage, and dynamic discovery.

Key patterns adopted:
- **Centralized Tool Dictionary**: All tools registered in `self.tools = {}`
- **Graceful Degradation**: Tool import wrapped in try/except with `TOOLS_AVAILABLE` flag
- **Lifecycle Tracking**: Session-based restart count and crash logging

### 8.3 From Vibe-Trading: Alpha Purity & Safety

The Alpha Zoo architecture from Vibe-Trading introduces rigorous safety patterns for quantitative code. When integrated (PR-004), these patterns will ensure that alpha factor computations are pure mathematical functions with no side effects.

Key patterns to adopt:
- **AST Allowlist Scan**: Reject alpha modules that import `os`, `sys`, `subprocess`, `socket`, etc.
- **Lookahead Bias Prevention**: Sentinel future-row injection tests
- **CI Grep Gates**: Reject `yaml.load()` without `safe_load`, trademark leaks, data leaks

### 8.4 From AutoHedge: Swarm Execution Pipeline

The AutoHedge architecture provides the template for a specialized multi-agent execution pipeline. When integrated (PR-005), it will add a Director/Quant/Risk/Execution chain specifically for crypto markets.

Key patterns to adopt:
- **Structured Output**: JSON-formatted recommendations for downstream systems
- **Swarm Pipeline**: Sequential agent handoff with defined contracts
- **Venue Abstraction**: Exchange-specific adapters behind common interface

---

**Document maintained by Mulky Malikul Dhaher**
**Repository: github.com/mulkymalikuldhrs/hermes-quant-os**
