# Quant-Nanggroe-AI v4.3.4 — Autonomous Quant Hedge Fund

> **"Isi saldo dan mulai autonomous trading."** — Mulky Malikul Dhaher

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

### 3. Start
```bash
launch.bat
# → http://localhost:8000/docs
# → POST /api/autonomous/pipeline/run {"symbol": "BTC-USD"}
```

> **Butuh demo MT5?** Buka MT5 → File → Open Account → Demo.   
> **Untuk live trading:** Set `QNA_LIVE_TRADING=1` di `start_trading.bat`

## Arsitektur

```
quant_nanggroe/
├── api/            → FastAPI (140 routes, auth middleware, scheduler)
│   ├── app.py      → create_app() factory + scheduler lifecycle
│   ├── middleware.py → Auth (localhost→ADMIN), CORS, RateLimit
│   └── routes/     → trading, autonomous, scheduler, backtest, etc.
├── engine/
│   ├── agentic/    → AutonomousPipeline (data→signal→risk→execute)
│   ├── scheduler.py→ PipelineScheduler (auto-trigger every N min)
│   ├── execution/  → ExecutionManager (guards→kill switch→risk→broker)
│   │   ├── manager.py   → execute_order() with full safety pipeline
│   │   ├── builder.py   → build_execution_manager() (paper default, MT5 opt-in)
│   │   └── brokers/     → PaperBroker, MT5ExecutionBroker (async adapter)
│   ├── risk/       → KillSwitch, RiskManager, VaR, Kelly, PositionSizing
│   ├── backtest/   → WalkForwardAnalyzer, PSR/DSR, Monte Carlo
│   └── strategy/   → 106+ strategies (regime-based selection)
├── exchange/       → ExchangeManager, CCXT broker, PaperExchangeBroker
├── connectors/     → MT5Broker, broker_base (sync adapter)
├── config/         → settings, mt5_accounts.yaml
└── agents/         → LangChain tools, debate, personas
```

## Alur Autonomous Trading

```
POST /api/autonomous/pipeline/run {"symbol":"BTC-USD"}
  → AutonomousPipeline.run_cycle()
    1. _fetch_data(symbols)        → yfinance (retry x3)
    2. _generate_signals(data)     → regime-based strategy selection → Signal[]
    3. _risk_check(signals)        → Kill switch → RiskManager 9-gate → passed signals
    4. _execute(passed_signals)    → ExecutionManager:
        a. Guard pipeline (cooldown / max position / whitelist)
        b. Kill switch check → BLOCK if daily/weekly/drawdown breached
        c. RiskManager veto → BLOCK if constitutional limits exceeded
        d. Broker submit → PaperBroker (default) or MT5 (live)
    5. Log results → return {signals, trades, errors}

Scheduler (auto-start when QNA_SCHEDULER_ENABLED=1):
  POST /api/scheduler/start {"interval_minutes": 15}
  → PipelineScheduler runs batch cycle every N minutes
  → Covers: BTC-USD, ETH-USD, SOL-USD, EURUSD, USDJPY
```

## Keamanan

- **Localhost auto-ADMIN** — `127.0.0.1` / `::1` / `localhost` → skip auth
- **Fail-closed** — tanpa `QNAI_JWT_SECRET` → RuntimeError
- **Kill switch ENFORCED** — `execute_order()` hard-block, bukan warning
- **RiskManager ENFORCED** — veto tidak bisa di-override
- **Paper default** — `QNA_LIVE_TRADING=1` diperlukan untuk MT5 live

## Konfigurasi

| Env Var | Default | Fungsi |
|---------|---------|--------|
| `VALETAX_PASSWORD` | — | Password MT5 (via expandvars) |
| `QNA_LIVE_TRADING` | `0` | `1` = aktifkan MT5 live |
| `QNAI_API_KEY` | — | API key untuk auth dari luar |
| `QNAI_JWT_SECRET` | — | JWT signing key |
| `QNAI_ALLOW_INSECURE_DEV` | `false` | `true` = bypass auth |

## Status: ✅ AUTONOMOUS TRADING OPERATIONAL

421 tests pass. Pipeline end-to-end verified (117 strategies). Scheduler wired. Kill switch enforced. Paper default.

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
