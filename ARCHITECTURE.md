# Dhaher Labs — Ekosistem Uang Architecture v1.0
## Unified Trading Pipeline

```
┌──────────────────────────────────────────────────────────┐
│                    DHAHER ECOSYSTEM                        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  DATA LAYER          ANALYSIS LAYER     EXECUTION LAYER   │
│  ┌────────┐        ┌──────────────┐    ┌──────────────┐   │
│  │  MT5   │───────▶│  AIHF (15    │    │   MT5 Bridge │   │
│  │ (forex)│        │   agents)    │───▶│  (forex LIVE)│   │
│  └────────┘        └──────────────┘    └──────────────┘   │
│  ┌────────┐        ┌──────────────┐    ┌──────────────┐   │
│  │TV/MCP  │        │ Hidden-      │    │  Freqtrade   │   │
│  │(crypto)│───────▶│ Regime (HMM) │───▶│  (crypto)    │   │
│  └────────┘        └──────────────┘    └──────────────┘   │
│  ┌────────┐        ┌──────────────┐    ┌──────────────┐   │
│  │yfinance│        │  AgentQuant  │    │  Multi-Acct  │   │
│  │(stock) │───────▶│  (RL/exp)    │───▶│  (future)    │   │
│  └────────┘        └──────────────┘    └──────────────┘   │
│                                                           │
│  ORCHESTRATION: E:/trading/terminal.py                    │
│  MONITOR: Telegram @dhaherautobot                         │
│  MCP: Hermes (MT5, TV, hidden-regime)                    │
└──────────────────────────────────────────────────────────┘
```

## Active Status (18 Juli 2026)

| Layer | Komponen | Status | Pipe? | Catatan |
|-------|----------|--------|-------|---------|
| Data | MT5 (Valetax) | 🟢 LIVE | ✅ | $1,000, 1:2000, AT enabled |
| Data | TradingView MCP | 🟢 Active | ✅ | Signal scan |
| Data | Hidden-Regime/yfinance | 🟢 Server runs | ✅ | 3 tools: detect, stats, transition |
| Analysis | AIHF (15 agents) | 🟢 Ready | 🟡 | MCP server works, not wired to cron |
| Analysis | LangAlpha | 🟡 Cloned | 🟡 | Butuh uv sync (Python 3.12+) |
| Analysis | AgentQuant | 🟡 Valid | ❌ | Standalone experiments |
| Analysis | AI-Trader | 🟡 Node.js | ❌ | Not audited |
| Execution | MT5 Bridge (custom) | 🟢 LIVE | ✅ | Two-step init, ATR SL, trailing HH/LL |
| Execution | Freqtrade | 🔴 Broken | ❌ | Venv 95% kosong |
| Execution | Multi-account | 🟢 Framework | ✅ | terminal.py + accounts.json |
| Monitor | Terminal.py v3.1 | 🟢 All menu | ✅ | [1-9,g,x], Gastown [g], LangAlpha [8] |
| Monitor | Cron hedge-fund-runner | 🟢 Every 30min | ✅ | V2: ATR, trail, logger |
| Monitor | Trade logger CSV | 🟢 Active | ✅ | data/trades.csv |
| Orchestrator | Hermes MCP | 🟢 14 servers | ✅ | MT5, TV, hidden-regime, +11 |
| Orchestrator | Gastown (gt.exe) | 🟢 Binary | ✅ | terminal.py [g], rig/crew/bead |
| Safety | Risk Manager | 🟢 V2 | ✅ | ATR SL, max 1 pos, min balance |

## Cleanup Status

| Path | Action | Status |
|------|--------|--------|
| E:/tmp | 🗑️ Deleted | ✅ |
| E:/.npm-cache | 🗑️ Deleted | ✅ |
| E:/.ruff_cache | 🗑️ Deleted | ✅ |
| E:/SHIT | 🗑️ Deleted | ✅ |
| E:/nul | 🗑️ Deleted | ✅ |
| E:/gastown.zip (9B empty) | 🗑️ Deleted | ✅ |
| E:/beads.zip | 📦 Archived | ✅ |
| E:/archived/ | 🗃️ Contains career/ | Verified |
| E:/backups_/ | 🗃️ Contains 7 backups | Verified |

## Multi-Account Architecture (v1.0 Design)

```yaml
brokers:
  - id: valetax-demo
    type: mt5
    login: "372044706"
    server: "ValetaxIntl_Live-2"
    leverage: 1:2000
    balance: 1000
    status: active
  
  - id: broker2
    type: <mt5/ctrader/ibkr>
    login: "..."
    server: "..."
    status: future

pipeline:
  scan: tradingview → signal
  analyze: ai-hf + hidden-regime → entry/exit
  execute: mt5 (forex) + freqtrade (crypto)
  monitor: telegram + terminal
```

## Gastown Integration

Gastown (`E:/gastown_bin/gt.exe`) — multi-agent orchestrator (Go).
Diakses via `terminal.py [g]`.

Commands tersedia:
- `gt status` — status rig
- `gt crew list` — daftar crew
- `gt bead list` — daftar beads/work items

Gastown bisa orchestrate hedge fund agents (monitor, risk, evaluasi) sebagai crew.

## Trade Logger

Semua trade dicatat di `E:/trading/data/trades.csv`:

| Field | Description |
|-------|-------------|
| time | ISO timestamp |
| action | open_buy/open_sell/close/fail |
| symbol | EURUSD |
| volume | Lot size |
| price | Entry price |
| sl | Stop loss |
| tp | Take profit |
| atr | ATR value at entry |
| result | executed/closed/code=N |
| pnl | Profit/loss in USD |

Cron `hedge-fund-runner` tiap 30min membaca history deals dan update CSV.
Trailing stop: HH/LL break on M1 → SL geser ke entry price (zero-risk).
```

## Next Steps
1. ✅ MT5 bridge live
2. ✅ Hidden-regime MCP configured
3. ✅ Config restored
4. 🔲 AIHF & Freqtrade audit (swarm running)
5. 🔲 Fix terminal.py entry point
6. 🔲 Build monitor UI
7. 🔲 Multi-account registration framework
