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


---

> **SSOT:** `CANONICAL.md` v8.1.4 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
