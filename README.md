# Quant Nanggroe AI v8.0.10 — Autonomous Quant Hedge Fund

> **Autonomous Quantitative Hedge Fund — Institutional Grade**
> **Self-Aware · Self-Correct · Self-Evolve · Self-Fine-Tune · Self-Evaluate**
> *"Mesin uang autonomous, jalan tanpa Hermes, optionally assisted."* — Mulky Malikul Dhaher

---

## 🎯 What Is This?

QNA is a **fully autonomous quantitative hedge fund platform** that runs, evolves, and optimizes itself with zero human intervention. It's not a trading bot — it's a **living financial organism**.

### Core Capabilities

| Capability | Module | Status |
|---|---|---|
| **Self-Aware** | `engine/self_aware.py` | ✅ Reflects on every run |
| **Self-Correct** | `engine/correction.py` | ✅ Records + resolves errors |
| **Self-Evolve** | `engine/strategy/strategies/strategy_evolver.py` | ✅ Walk-forward validated mutations |
| **Self-Fine-Tune** | `engine/strategy/strategies/self_finetune.py` | ✅ Grid search + optimization |
| **Self-Evaluate** | `engine/strategy/strategies/strategy_evolver.py` | ✅ Accept/reject gate |
| **Auto-Registry** | `engine/registry.py` | ✅ Scans ENTIRE repo (800+ files) |
| **Candle Scheduler** | `engine/candle_scheduler.py` | ✅ Real-time M15/H1/H4/D1 candle-close watcher |

---

## 🚀 Quick Start

### 1. Install
```bash
git clone https://codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI
cd Quant-Nanggroe-AI
uv sync
```

### 2. Configure
```bash
cp .env.example .env
# Required vars: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, QNA_ADMIN_API_KEY
```

### 3. Run
```bash
# Full autonomous mode (real-time candle-close scheduler)
python qna.py daemon

# System tray (start/stop daemon, open dashboard — Windows)
python qna_tray.py

# API server
python qna.py api

# Dashboard
cd dashboard && npm run dev
```

---

## 📊 System Architecture

```
qna.py daemon / qna_tray.py
  → candle_scheduler.py:start_candle_scheduler()
    → _tick_loop() — monitors MT5 ticks every 1s
      → _check_all_closes() — detects candle close per symbol+TF
        → _run_analysis(symbol, tf)
          → pipeline.run() — full pipeline:
             data(stale-veto) → signal(aggregation) → risk(9-gate)
             → context gate(news blackout) → execute(duplicate-position
               gate + fill-status gate) → broker truth
             → Telegram notification on trade/signal
             → SQLite trade history (unlimited)
             → WebSocket push ("candles" channel) + dashboard live
  → auto_retrain.py (hourly Bayesian re-tune → decay guard)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `qna_tray.py` | Windows system tray: daemon control, dashboard links |
| `engine/candle_scheduler.py` | Real-time candle-close multi-TF scheduler |
| `engine/candle_events.py` | Thread→async event bus for WS candle pushes |
| `engine/agentic/autonomous.py` | Autonomous trading pipeline (timeframe-aware) |
| `engine/agentic/context_gate.py` | High-impact news blackout veto (±30 min) |
| `engine/execution/signal_aggregator.py` | ONE position per symbol, fixed 0.5% risk |
| `engine/risk/manager.py` | 9-checkpoint risk gate + kill switch |
| `engine/trade_history.py` | SQLite-backed unlimited trade history |
| `engine/strategy_allocation.py` | CPCV per-symbol admission |
| `engine/analytics/strategy_scorecard.py` | Per-strategy metrics |
| `engine/analytics/trade_awareness.py` | What/why/how/lesson per trade |
| `engine/risk/trailing_stop.py` | Breakeven ratchet + ATR trail |
| `engine/risk/trading_profile.py` | Scalp/day/swing SL-TP profiles |
| `engine/smc/native_smc.py` | OrderBlock/FVG/BOS/Sweep native |
| `engine/auto_retrain.py` | Autonomous Bayesian re-tune loop + decay guard |

---

## 🖥️ Dashboard

Next.js 16 + React 19 + Tailwind + Radix UI. 36 pages, 10 API routes.

| Page | Purpose |
|------|---------|
| `/` | Main dashboard |
| `/trading` | Live trading view |
| `/trading/history` | Unlimited trade history (SQLite) |
| `/candle-monitor` | Real-time candle close events |
| `/notifications` | Signal/trade notification feed |
| `/strategies` | Strategy management |
| `/risk` | Risk management |
| `/config` | Configuration center |
| `/export` | Data export (xlsx/pdf) |
| `/autonomous` | Autonomous pipeline status |

---

## 🧪 Tests

```bash
# Core regression (61 tests)
python -m pytest tests/test_engine/test_strategy_allocation.py tests/test_risk/test_trailing_stop_gate7.py tests/test_engine/test_analytics.py tests/test_engine/test_signal_aggregator.py tests/test_engine/test_ml.py tests/test_engine/test_candle_scheduler.py -q

# Dashboard build
cd dashboard && node node_modules/next/dist/bin/next build
```

---

## 📁 Project Structure

```
Quant-Nanggroe-AI/
├── qna.py                    # Entry point (daemon/api/status/backtest)
├── quant_nanggroe/           # Core Python package (800+ files)
│   ├── engine/               # Trading engine
│   │   ├── agentic/          # Autonomous pipeline
│   │   ├── candle_scheduler.py  # Real-time scheduler
│   │   ├── trade_history.py  # SQLite trade history
│   │   ├── risk/             # Risk management
│   │   ├── execution/        # Order execution
│   │   ├── analytics/        # Performance analytics
│   │   └── smc/              # Smart Money Concepts
│   ├── api/                  # FastAPI backend
│   └── connectors/           # MT5 broker
├── dashboard/                # Next.js 16 dashboard
│   └── src/app/              # 36 pages + 10 API routes
├── tests/                    # 183 test files
├── CANONICAL.md              # Single Source of Truth
└── config/                   # Configuration files
```

---

## 🔒 Security

- **Fail-closed JWT**: Refuses boot if secret is weak/default
- **REAL-ONLY mode**: No paper trading by default
- **Kill switch**: C5 cross-process shared state
- **API key auth**: All routes protected
- **Rate limiting**: 60 req/min per IP

---

## 📚 Documentation

- `CANONICAL.md` — Single Source of Truth (v8.0.10)
- `CHANGELOG.md` — Version history
- `AGENTS.md` — Agent configuration
- `CLAUDE.md` — Claude Code configuration

---

**Version:** v8.0.10 | **Status:** GREEN — LIVE on MT5 | **Broker:** ValetaxIntl-Live2 (Cent, .vxc)
