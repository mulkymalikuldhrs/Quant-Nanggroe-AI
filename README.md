# Quant Nanggroe AI — Autonomous Quant Hedge Fund

> **Autonomous Quantitative Hedge Fund — Institutional Grade**
> **Self-Aware · Self-Correct · Self-Evolve · Self-Fine-Tune · Self-Evaluate**
> *"Mesin uang autonomous, jalan tanpa Hermes, optionally assisted."* — Mulky Malikul Dhaher

---

## What Is This?

QNA is a **fully autonomous quantitative hedge fund platform** that runs, evolves, and optimizes itself with zero human intervention. It's not a trading bot — it's a **living financial organism**.

### Core Capabilities

| Capability | Module | Status |
|---|---|---|
| **Self-Aware** | `engine/autonomous_self_loop.py` | Reflects on every run |
| **Self-Correct** | `engine/agentic/autonomous.py` (SelfCorrection) | Records + resolves errors |
| **Self-Evolve** | `engine/auto_retrain.py` | Walk-forward validated mutations + decay guard |
| **Self-Fine-Tune** | `engine/auto_retrain.py` | Bayesian parameter optimization |
| **Self-Evaluate** | `engine/agentic/strategy_evaluator.py` | Auto-disable bad performers |
| **Auto-Registry** | `engine/registry.py` | Scans entire repo, 212 strategies registered |
| **Candle Scheduler** | `engine/candle_scheduler.py` | Real-time M15/H1/H4/D1 candle-close watcher |
| **Committee Voting** | `engine/agentic/committee/` | 5 specialist agents per pair + RiskAgent VETO |
| **Causal Engine** | `engine/causal_engine.py` | COT, SMT, macro weather, DCC correlations |
| **Trade Journal** | `engine/journal_sync.py` | MT5 deal sync → SQLite → evaluator feedback loop |

---

## Quick Start

### 1. Install
```bash
git clone https://codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI
cd Quant-Nanggroe-AI
uv sync
```

### 2. Configure
```bash
cp .env.example .env
# Required: QNAI_JWT_SECRET, QNA_ADMIN_API_KEY, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
```

### 3. Run
```bash
python qna.py daemon        # Full autonomous mode (candle scheduler + agents)
python qna.py api           # FastAPI :8000
python qna_tray.py          # Windows tray (daemon control + dashboard)
cd dashboard && pnpm install && pnpm dev   # Next.js dashboard :3000
```

---

## External Dependencies

All external dependencies are bundled inside `quant_nanggroe/external/`:

| Package | Path | Purpose |
|---------|------|---------|
| **Kronos** | `external/kronos/` | Financial foundation model (AAAI 2026) — OHLCV forecast |
| **MUE-X** | `external/mue_x/` | Evolution engine — 992 evolved strategy genes |
| **hidden-regime** | `external/hidden_regime/` | Regime detection — trend/range/crisis classification |
| **backtesting.py** | `external/backtesting/` | Walk-forward backtest engine |
| **OrderFlowMap** | `external/orderflow_map/` | Orderflow visualization |
| **smart-money-concepts** | `external/smc/` | SMC/ICT indicator library |

These are loaded via relative paths from `quant_nanggroe/` — no hardcoded `E:\` for Kronos/mue_x/hidden_regime. `quant_nanggroe/engine/execution/account_discovery.py:49` still scans `E:\Program Files\MetaTrader 5` to auto-detect the live terminal (functional, documented).

---

## System Architecture

```
qna.py daemon
  -> candle_scheduler.py:start_candle_scheduler()
    -> _tick_loop() — monitors MT5 ticks every 1s
      -> _check_all_closes() — detects candle close per symbol+TF
        -> _run_analysis(symbol, tf)
          -> pipeline.run() — full pipeline:
             data(stale-veto) -> signal(aggregation + CPCV allocation)
             -> committee(5-agent vote + RiskAgent VETO)
             -> risk(9-gate + kill switch + trailing stop)
             -> context gate(news blackout) -> execute(duplicate-position gate)
             -> broker truth -> journal_sync -> strategy_evaluator
             -> Telegram notification -> WebSocket push -> dashboard live
  -> auto_retrain.py (12h Bayesian re-tune + decay guard)
  -> strategy_evaluator (auto-disable on low Sharpe/win-rate)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `qna.py` | Entry point (daemon/api/status/backtest) |
| `qna_tray.py` | Windows system tray: daemon control, dashboard links |
| `engine/candle_scheduler.py` | Real-time candle-close multi-TF scheduler |
| `engine/candle_events.py` | Thread->async event bus for WS candle pushes |
| `engine/agentic/autonomous.py` | Autonomous trading pipeline (2596 lines) |
| `engine/agentic/context_gate.py` | High-impact news blackout veto (+-30 min) |
| `engine/agentic/committee/` | 5-agent specialist voting + RiskAgent VETO |
| `engine/agentic/strategy_evaluator.py` | Auto-disable bad performers (Sharpe/winstreak) |
| `engine/execution/manager.py` | Guard pipeline -> kill switch -> risk veto -> fill-status |
| `engine/execution/signal_aggregator.py` | ONE position per symbol, fixed 0.5% risk |
| `engine/risk/` | 9-checkpoint risk gate, trailing stop, trading profiles |
| `engine/trade_history.py` | SQLite-backed unlimited trade history |
| `engine/journal_sync.py` | MT5 deal sync -> trade journal -> evaluator feedback |
| `engine/strategy_allocation.py` | CPCV per-symbol admission (fail-open unvalidated, fail-closed proven-bad) |
| `engine/auto_retrain.py` | Autonomous Bayesian re-tune loop + decay guard |
| `engine/causal_engine.py` | COT, SMT, macro weather, DCC, regime detection |
| `engine/data_pipeline.py` | Finnhub news, CFTC COT, sentiment cache |
| `engine/smc/` | Native SMC: OrderBlock/FVG/BOS/Sweep |

---

## Dashboard

Next.js 16.2.9 + React 19 + Tailwind 4 + Zustand 5 + Recharts 3 + lightweight-charts 5. **39 pages**, 10 API routes, proxied to FastAPI :8000.

| Page | Purpose |
|------|---------|
| `/` | Main dashboard |
| `/trading` | Live trading view |
| `/trading/history` | Unlimited trade history |
| `/candle-monitor` | Real-time candle close events |
| `/committee` | Per-pair agent voting + risk veto + debate |
| `/evaluator` | Strategy evaluator + pipeline health + auto-disable |
| `/data-pipeline` | Causal engine, COT, SMT, macro weather |
| `/strategies` | Strategy management |
| `/risk` | Risk management |
| `/orderflow` | Live order book (Binance L2 data) |
| `/config` | Configuration center |
| `/export` | Data export |
| `/autonomous` | Autonomous pipeline status |
| `/memory` | Agent memory + knowledge graph |
| `/portfolio` | Portfolio overview |
| `/evolution` | Strategy evolution status |

---

## Tests

```bash
# Core regression (21 tests)
set PYTHONPATH= && python -m pytest tests/test_engine/test_strategy_allocation.py tests/test_risk/test_trailing_stop_gate7.py tests/test_engine/test_signal_aggregator.py -q

# Dashboard build
cd dashboard && npx next build

# Lint
ruff check .

# Type check
mypy quant_nanggroe/ --ignore-missing-imports
```

---

## Project Structure

```
Quant-Nanggroe-AI/
├── qna.py                    # Entry point (daemon/api/status/backtest)
├── quant_nanggroe/           # Core Python package (800+ files)
│   ├── engine/               # Trading engine
│   │   ├── agentic/          # Autonomous pipeline + committee + evaluator
│   │   ├── candle_scheduler.py  # Real-time scheduler
│   │   ├── trade_history.py  # SQLite trade history
│   │   ├── journal_sync.py   # MT5 deal sync -> journal -> evaluator
│   │   ├── risk/             # Risk management (9 gates + kill switch)
│   │   ├── execution/        # Order execution + signal aggregation
│   │   ├── analytics/        # Performance analytics + scorecard
│   │   ├── causal_engine.py  # COT/SMT/macro/regime
│   │   ├── auto_retrain.py   # Bayesian re-tune + decay guard
│   │   └── smc/              # Smart Money Concepts
│   ├── api/                  # FastAPI backend (52 routes)
│   └── connectors/           # MT5 broker
├── dashboard/                # Next.js 16 dashboard (39 pages)
│   └── src/app/              # Pages + API routes
├── tests/                    # 228 test files
├── CANONICAL.md              # Single Source of Truth
├── CHANGELOG.md              # Version history
└── config/                   # Configuration files
```

---

## Security

- **Fail-closed JWT**: Refuses boot if secret is weak/default
- **REAL-ONLY mode**: No paper trading by default (QNA_ALLOW_PAPER=1 required)
- **Kill switch**: C5 cross-process shared state (L1 auto-expire, L2/L3 manual reset)
- **API key auth**: All routes protected
- **Rate limiting**: 60 req/min per IP
- **CPCV allocation**: Fail-open for unvalidated strategies, fail-closed for proven-bad

---

## Documentation

- `CANONICAL.md` — Single Source of Truth
- `CHANGELOG.md` — Version history
- `AGENTS.md` — Agent configuration
- `CLAUDE.md` — Claude Code configuration

---

**Status:** LIVE on MT5 — CANONICAL v8.0.21 | **Broker:** ValetaxIntl-Live2 (login 372044706 QNA, BAL $1,445) | **Account:** QNA | **Weekly:** 0 WIB | **Probe:** 0/32 | **CPCV:** 207 | **Launcher:** `launch.bat` (single, WIB) | **Risk:** `engine/execution/manager.py` WIB weekly/PNL guard — see `CANONICAL.md` SSOT

---

> **SSOT:** `CANONICAL.md` v8.0.21 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

---

> **SSOT:** `CANONICAL.md` v8.0.21 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live
