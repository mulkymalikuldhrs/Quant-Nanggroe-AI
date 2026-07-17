# Quant-Nanggroe-AI v4.5.0 — Autonomous Quant Hedge Fund

> **"Isi saldo dan mulai autonomous trading."** — Mulky Malikul Dhaher

## Satu Perintah untuk Mulai

```bash
set VALETAX_PASSWORD=your_mt5_password
set QNA_LIVE_TRADING=1
python run_server.py
# → http://localhost:8000/docs
# → POST /api/autonomous/pipeline/run {"symbol": "BTC-USD"}
```

Atau jalankan `start_trading.bat` (isi password di `config/mt5_accounts.yaml`).

## Arsitektur

```
quant_nanggroe/
├── api/            → FastAPI (137 routes, 30+ routers, auth middleware)
│   ├── app.py      → create_app() factory
│   ├── middleware.py → Auth (localhost→ADMIN), CORS, RateLimit
│   └── routes/     → trading, backtest, autonomous, options, etc.
├── engine/
│   ├── autonomous/ → AutonomousPipeline (data→signal→risk→execute)
│   ├── execution/  → ExecutionManager (guards→kill switch→risk→broker)
│   │   ├── manager.py   → execute_order() with full safety pipeline
│   │   ├── builder.py   → build_execution_manager() (paper default, MT5 opt-in)
│   │   └── brokers/     → PaperBroker, MT5ExecutionBroker (async adapter)
│   ├── risk/       → KillSwitch, RiskManager, VaR, Kelly, PositionSizing
│   ├── backtest/   → WalkForwardAnalyzer, PSR/DSR, Monte Carlo
│   └── strategy/   → 106 strategies (KEEP/DROP graded)
├── connectors/     → MT5Broker, broker_base.BrokerConnector (sync)
├── exchange/       → ExchangeManager, MT5Broker (ExchangeInterface)
├── config/         → settings, mt5_accounts.yaml, credentials
└── agents/         → LangChain tools, debate, personas
```

## Alur Autonomous Trading

```
POST /api/autonomous/pipeline/run {"symbol":"BTC-USD"}
  → AutonomousPipeline.run_cycle()
    1. _fetch_data(symbols)        → MT5 → yfinance (failover)
    2. _generate_signals(data)     → KEEP strategies → Signal[]
    3. _risk_check(signals)        → Kill switch → passed signals
    4. _execute(passed_signals)    → ExecutionManager:
        a. Guard pipeline (cooldown / max position / whitelist)
        b. Kill switch check → BLOCK if daily/weekly/drawdown breached
        c. RiskManager veto → BLOCK if constitutional limits exceeded
        d. Broker submit → PaperBroker (default) or MT5 (live)
    5. Log results → return {signals, trades, errors}
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

## Status: ✅ SIAP TRADING

409 engine tests pass. Pipeline syntax fixed. Safety enforced. Cron tiap 15 menit.
