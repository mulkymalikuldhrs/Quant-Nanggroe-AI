# Quant Nanggroe Dashboard

**Apple macOS Liquid Glass × Bloomberg Terminal × Quant Hedge Fund OS**

Production-grade frontend for the Quant Nanggroe autonomous hedge fund trading system. Built with Next.js 16, React 19, Tailwind CSS v4, and Zustand v5.

⚠️ **AUDIT NOTE (2026-07-30):** Scoring engine NOW WIRED (Session 7). Backend pipeline has 8 scorers active with FusionEngine. Dashboard still needs extraction from github2 branch per ADR-007.

---

## Design System

### Glassmorphism Architecture

The UI implements an Apple macOS-inspired "Liquid Glass" design language:

| Layer | CSS Class | Description |
|-------|-----------|-------------|
| Light Glass | `.glass-light` | `backdrop-filter: blur(24px)` with subtle border |
| Medium Glass | `.glass` | `backdrop-filter: blur(32px)` with 6% white bg |
| Strong Glass | `.glass-strong` | `backdrop-filter: blur(40px)` with 8% white bg |
| Double-Bezel | `.double-bezel` | Card with `::before` inner inset border stroke |
| Bloomberg Cell | `.bbg-cell` | Compact high-density data cell with light border |
| Noise Overlay | `.noise` | Subtle grain texture overlay for depth |

### Design Tokens

All colors, spacing, and animations are controlled via CSS custom properties:

```css
--color-brand-emerald: #10b981;
--color-brand-amber: #f59e0b;
--color-brand-purple: #8b5cf6;
--color-profit: #10b981;
--color-loss: #ef4444;
--color-bid: #10b981;
--color-ask: #ef4444;

--surface-card: rgba(255, 255, 255, 0.02);
--surface-hover: rgba(255, 255, 255, 0.04);
--border-default: rgba(255, 255, 255, 0.06);
--border-hover: rgba(255, 255, 255, 0.1);
```

### Typography

- **UI Text:** Inter (system font stack)
- **Data/Monospace:** JetBrains Mono or system monospace
- **Scale:** 10px (labels) → 11px (badges) → 12px (body) → 14px (emphasis) → 18-24px (headings)

---

## Architecture

```
dashboard/src/
├── app/                          ← Next.js App Router pages
│   ├── page.tsx                  ← Main dashboard (system health, live prices, quick nav)
│   ├── trading/page.tsx          ← Live multi-broker trading (MT5, Binance, IBKR, Paper)
│   ├── portfolio/page.tsx        ← Cross-broker portfolio aggregation
│   ├── agents/page.tsx           ← Agent council + LangGraph pipeline
│   ├── risk/page.tsx             ← Risk management (VaR, Kelly, parity, 9-checkpoint)
│   ├── strategies/page.tsx       ← Strategy lifecycle, schema, backtest adapters
│   ├── backtest/page.tsx         ← Backtesting engine interface
│   ├── market/page.tsx           ← Market data, sentiment, signals
│   ├── memory/page.tsx           ← Memory bus search/storage
│   ├── colony/page.tsx           ← Agent colony management
│   ├── factors/page.tsx          ← Alpha factor zoo explorer
│   ├── security/page.tsx         ← Security events & sandbox status
│   ├── channels/page.tsx         ← Notification channels
│   ├── tools/page.tsx            ← Tool registry & execution
│   └── settings/page.tsx         ← Full configuration UI (brokers, API keys, risk limits)
│
├── components/
│   ├── layout/                   ← AppLayout, Sidebar, Header (glassmorphism chrome)
│   ├── ui/                       ← Card, Button, Input, Select, Badge, Tabs, Switch, ScrollArea
│   ├── shared/                   ← StatusCard, ChartCard, DataTable, RiskGauge, ErrorBoundary,
│   │                               LoadingSkeleton, AgentCard, Sparkline
│   └── providers/                ← ThemeProvider (auto day/night)
│
└── lib/
    ├── api-client.ts             ← Typed API client with retry, dedup, timeout
    ├── websocket.ts              ← WebSocket hook with exponential backoff
    ├── store.ts                  ← Zustand store with granular loading/error states
    └── utils.ts                  ← Quant formatters (currency, percent, change, P&L color)
```

---

## Pages Overview

| Page | Route | Features |
|------|-------|----------|
| **Dashboard** | `/` | System health, live prices (WebSocket), metric cards, quick nav |
| **Trading** | `/trading` | Multi-broker accounts, order entry, positions, live balance, cross-broker aggregation |
| **Portfolio** | `/portfolio` | Cross-broker P&L, equity curve, allocation donut, Kelly sizing, ATR calculator |
| **Agents** | `/agents` | Agent council grid, run pipeline, agent graph visualization, kill switch |
| **Risk** | `/risk` | VaR/CVaR gauges, 9-checkpoint gate, Kelly parameters, risk parity, drawdown analysis |
| **Strategies** | `/strategies` | Strategy list, schema editor, loader/parser, backtest adapter config |
| **Backtest** | `/backtest` | Backtest runner, results viewer, equity/drawdown curves, Monte Carlo |
| **Market** | `/market` | Real-time prices, sentiment analysis, sector breakdown, trading signals |
| **Memory** | `/memory` | Memory search/filter, store memory, type-colored cards |
| **Factors** | `/factors` | Alpha factor zoo explorer, IC/returns, factor pipeline builder, correlation heatmap |
| **Settings** | `/settings` | API keys, broker credentials (MT4/MT5/cTrader), exchange configs, LLM keys, risk limits, agent models, system toggles |
| **OrderFlow** | `/orderflow` | Bookmap-style visualization — heatmap, trade bubbles, DOM ladder, CVD, VWAP (shared with SahamEngineAI) |
| **TradeBobby** | Sidebar panels | Macro Pulse, COT Positioning, Crypto Pulse, Setup Tracker, Agent Brief (daemon API connected) |

---

## Production Features

### Real-Time WebSocket
- Auto-connect to `/api/ws/stream` with 4 channels: `price`, `regime`, `risk`, `portfolio`
- Exponential backoff reconnection (1s → 30s with jitter)
- Connection state tracking with `LIVE` / `RECONNECTING` / `OFFLINE` indicator
- Auto-subscribe on connect, store updates via callbacks

### API Client
- Retry logic: up to 3 retries with exponential backoff (500ms → 5s)
- Request deduplication for concurrent GET requests
- 30-second timeout with AbortController
- Non-retryable status codes: 400, 401, 403, 404, 405, 422, 429
- `ApiError` class with `retryable` flag
- 30+ typed endpoints across 8 API modules

### State Management
- Granular per-endpoint loading/error tracking
- Real-time data integration from WebSocket
- Notification system with 50-message cap
- Aggregate `refreshAll()` for parallel data refresh
- Auto-refresh every 30 seconds

### Error Handling
- React `ErrorBoundary` wrapping each page
- `ErrorDisplay` component with retry button
- Granular error banners per data source
- Graceful fallback to mock data when backend unavailable

### Auto Day/Night Theme
- 3 modes: `system` (follows OS), `dark`, `light`
- `localStorage` persistence
- System preference listener with real-time switching
- Flash prevention (hidden until mounted)
- Smooth transition between modes

---

## Quick Start

```bash
# Install dependencies
npm install

# Development server (port 3000)
npm run dev

# Production build
npm run build

# Start production server
npm start
```

Requires the Quant Nanggroe Python backend running on port 8000:

```bash
python qna.py api
```

### Running Daemons (for TradeBobby panels)

```bash
# From the project root
cd quant_nanggroe/daemons
python -c "from macro_pulse import MacroPulseDaemon; MacroPulseDaemon().run_once()"
python -c "from crypto_pulse import CryptoPulseDaemon; CryptoPulseDaemon().run_sync()"
python -c "from cot_fetcher import COTFetcherDaemon; COTFetcherDaemon().run_once()"
python -c "from news_scanner import NewsScannerDaemon; NewsScannerDaemon().run_once()"
```

---

## Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16 | App Router, SSR/SSG |
| React | 19 | UI components |
| Tailwind CSS | 4 | Utility-first styling |
| Zustand | 5 | State management |
| Recharts | 2 | Charts (area, line, pie) |
| Lucide React | latest | Icons |
| clsx + tailwind-merge | latest | Class management |

---

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws/stream
```

---

© Dhaher Labs / Quant Nanggroe Hedge Fund


---

## 🎯 100/100/100 Roadmap — Dari OpenCode Audit (2026-07-30)

### Target Matrix: 3 Dimensi

| Score | Arti | Target | Estimasi Waktu |
|-------|------|--------|---------------|
| **A 100** | Bisa dinikmati — evolution jalan, error kedengeran, dashboard meaningful | ✅ Pipeline sehat, evolution beneran belajar, error gak silent | **1 hari** |
| **B 100** | Quant-grade — single source of truth, statistical rigor, no data corruption | ✅ Weight governance, signal/registry dedup, test coverage >80% | **3-4 hari** |
| **C 100** | Institutional — zero silent fail, audit trail, multi-account, SLA | ✅ Paper=production, alerting, replay, 80% coverage, multi-broker | **2-4 minggu** |
| **Total** | **300/300** | **Fully autonomous quant nation** | **~6 minggu** |

### Detail Gap per Score (Dari Audit 8 Task Agent)

#### A 100 — Enjoyable & Reliable

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| A1 | **Evolution loop dead** — 4 wiring bugs di `main.py:847-854` | scan_strategy→scan_all, evaluate() pake list | **2 jam** |
| A2 | **Silent error 20+ titik** — semua `log.debug()` | Upgrade ke `log.error` + propagate | **1 jam** |
| A3 | **`np` undefined** — StressVaR selalu throw NameError | `import numpy as np` di main.py | **5 menit** |
| A4 | **`get_valid_pairs` missing** — always throws AttributeError | Fix import atau remove dead call | **15 menit** |
| A5 | **Dashboard build stale + color config gak ada** | Rebuild + color picker | **2 jam** |
| A6 | **PnL attribution gak ada** — dashboard gak tampilin evolution journal | Wire dashboard API ke journal SQLite | **1 jam** |
| | **Total A fix** | | **~6 jam** |

#### B 100 — Quant-Grade

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| B1 | **WeightEvolver vs WeightUpdater fight** — beda data source, beda formula, gak sync | Eliminate satu. Rekomendasi: WeightEvolver (circuit breaker) | **3 jam** |
| B2 | **Weight total 1.03 + 2 scorers missing dari evolver** | Tambah CryptoScorer & NewsScorer ke DEFAULT, normalize | **30 menit** |
| B3 | **8 Signal classes, 3 field name conflicts** — signal_type vs direction vs side vs bias | Pilih canonical (`types/signals.py`), delete sisanya | **2 jam** |
| B4 | **3 registries gak sync** — StrategyRegistry vs AutoRegistry vs WalkForwardRegistry | StrategyRegistry = canonical, AutoRegistry delete for strategies | **2 jam** |
| B5 | **4/10 scorers untested** — Crypto, News, Positioning, Confluence | Tambah test class + mock external APIs | **3 jam** |
| B6 | **6/8 evolution modules untested** — config, handler, scanner, disabler, updater, evolver | Tambah test class | **4 jam** |
| | **Total B fix** | | **~14.5 jam** |

#### C 100 — Institutional/Hedge Fund

| # | Gap | Fix | Estimasi |
|---|-----|-----|----------|
| C1 | **Paper mode = dead risk** — PnL hardcoded 0.0, balance 1000 | Simulasi PnL real dari MT5/fallback | **2 jam** |
| C2 | **RiskLimits class unwired** — `limits.py:48` can_trade() zero callers | Wire ke `_pipeline_risk_check` | **1 jam** |
| C3 | **Audit trail write-only** — evolution journal nulis tapi gak dibaca | Dashboard timeline + PnL attribution | **4 jam** |
| C4 | **No alert system** — error silent total | Telegram alert on subsystem fail | **3 jam** |
| C5 | **Test coverage rendah** — estimasi 20-30% | Target 80%. Prioritaskan risk + scoring + evolution + pipeline | **3-4 hari** |
| C6 | **Multi-account MT5** — single session, gak bisa multi-broker | Multi-process architecture | **1 minggu** |
| C7 | **~15K lines dead code** — 10 REST clients, 453 alphas, RL stub, live_engine.py | Hapus/archive file terverifikasi | **3 jam** |
| C8 | **Data quality framework** — gak ada SLA monitoring, staleness detection | Data health check + status endpoint + dashboard | **2 hari** |
| | **Total C fix** | | **~6-10 hari** |

### Timeline Eksekusi

```
Hari 1:     A1 + A2 + A3 + A4 + B1 + B2          → Score A ~90, B ~60
Hari 2-3:   B3 + B4 + B5 + B6 + A5 + A6          → Score A 100, B ~90
Minggu 2:   C1 + C2 + C3 + C7 + C8               → Score C ~70
Minggu 3-4: C4 + C5 + C6                         → Score C ~90
Minggu 5-6: Last mile hardening                  → Score C 100
```

### Keputusan Arsitektur yang Perlu Diambil Mulky

| Keputusan | Opsi A | Opsi B | Rekomendasi |
|-----------|--------|--------|-------------|
| **Weight tuner** | WeightEvolver (circuit breaker, normalized) | WeightUpdater (Bayesian, SQLite) | **WeightEvolver** — safety circuit breaker |
| **Registry main** | StrategyRegistry (decorator-driven) | AutoRegistry (scan semua subclass) | **StrategyRegistry** — explicit > implicit |
| **Signal canonical** | `types/signals.py` (20 fields, BaseModel) | `pipeline/signal.py` (8 fields, dataclass) | **`types/signals.py`** — Pydantic validation |
| **Alerts** | Telegram | Email | **Telegram** — sudah ada bot |
| **Multi-account MT5** | Multi-process (1 per broker) | Docker containers | **Multi-process** — 16GB RAM cukup |

### Catatan Realistis

Estimasi 6 minggu tapi bisa molor karena:
1. **Testing time** — tiap perubahan perlu ruff + mypy + pytest. Kena typo = backtrack
2. **Refactor domino effect** — signal dedup → 8 file berubah → 5 file impor patah → fix lagi
3. **Mental energy** — baca 83 strategy files, 24 risk files, 20 provider files buat mastiin gak ada yang kehapus

**Realistis: 6-8 minggu** untuk 300/300.
