# Sim Repo Merge Log

**Task ID:** 4-c  
**Date:** 2025-03-04  
**Agent:** Sim Merge Agent  
**Repo:** `/home/z/my-project/quant-nanggroe-ai/repos/sim/`

---

## Executive Summary

The sim repo is an AI coding/workflow automation platform (like Sim.ai / Copilot), NOT a trading platform. Of its 22 branches containing ~88,000+ unique lines, **only the Kalshi and Polymarket TypeScript tools are directly relevant** to the Quant-Nanggroe-AI trading platform. All other code (copilot, workflow UI, MCP storage, rate-limiter, AWS Lambda, Microsoft tools, etc.) is TypeScript infrastructure for the coding assistant and has no trading utility.

**Decision: MERGE selectively — only Kalshi + Polymarket tool APIs. Skip the entire sim codebase infrastructure.**

---

## Branch Evaluation (22 branches)

### All Branches Analyzed

| Branch | Lines Changed | Trading Relevant? | Action |
|--------|---------------|-------------------|--------|
| `feat/copilot-v3` | +24,177 | Only Kalshi/Polymarket tools | Skip infra, extract APIs |
| `improvement/workflow-blocks` | +25,252 | Only Kalshi/Polymarket tools | Skip (same tools as main) |
| `feat/aws-lambda` | +23,243 | No | Skip (Lambda deploy UI) |
| `feat/microsoft-tools` | +4,077 | No | Skip (Office/Teams integrations) |
| `feat/execution-filesystem` | +8,208 | No | Skip (file system executor) |
| `feat/files-support` | +7,986 | No | Skip (file upload UI) |
| `feat/copilot-autolayout` | — | No | Skip (AI layout) |
| `feat/copilot-billing-v1` | — | No | Skip (billing) |
| `feat/hunterio` | — | No | Skip (email finder tool) |
| `feat/redtail` | — | No | Skip (CRM integration) |
| `feat/text-to-workflow` | — | No | Skip (AI workflow gen) |
| `feat/xai` | — | No | Skip (X/Grok API) |
| `fix/copilot-env-vars` | — | No | Skip (env var fix) |
| `fix/start-webhook` | — | No | Skip (webhook fix) |
| `fix/temp-logs` | — | No | Skip (logging fix) |
| `fix/wand` | — | No | Skip (prompt wand fix) |
| `improvement/copilot` | — | No | Skip (copilot improvement) |
| `improvement/prompt-wand` | — | No | Skip (prompt UI) |
| `improvement/templates` | — | No | Skip (workflow templates) |
| `improvement/ui-ux` | — | No | Skip (UI/UX improvements) |
| `improvement/workflow-block` | — | No | Skip (workflow block UI) |
| `blog` | — | No | Skip (blog content) |
| `staging` | — | No | Skip (staging branch) |

### Key Finding

All 22 branches share the **same** Kalshi and Polymarket tools that already exist on the `main` branch. No branch has unique trading-relevant code beyond what's on main. The branches differ only in their non-trading features (copilot AI, workflow UI, marketplace, etc.).

---

## Trading-Relevant Code Extracted

### Source Files (TypeScript, on main branch)

**Kalshi Tools** (19 files in `apps/sim/tools/kalshi/`):
- `types.ts` — Type definitions, RSA-PSS auth, URL builders
- `index.ts` — Tool exports
- `amend_order.ts` — Amend existing order
- `cancel_order.ts` — Cancel an order
- `create_order.ts` — Create new order (limit/market, FOK/GTC/IOC)
- `get_balance.ts` — Account balance
- `get_candlesticks.ts` — OHLCV data
- `get_event.ts` / `get_events.ts` — Event queries
- `get_exchange_status.ts` — Exchange status
- `get_fills.ts` — Fill history
- `get_market.ts` / `get_markets.ts` — Market data
- `get_order.ts` / `get_orders.ts` — Order management
- `get_orderbook.ts` — Order book
- `get_positions.ts` — Position tracking
- `get_series_by_ticker.ts` — Series data
- `get_trades.ts` — Trade history

**Polymarket Tools** (19 files in `apps/sim/tools/polymarket/`):
- `types.ts` — Type definitions, 3 API endpoints (Gamma, CLOB, Data)
- `index.ts` — Tool exports
- `get_event.ts` / `get_events.ts` — Event queries (Gamma API)
- `get_last_trade_price.ts` — Last trade price (CLOB)
- `get_market.ts` / `get_markets.ts` — Market data (Gamma)
- `get_midpoint.ts` — Midpoint price (CLOB)
- `get_orderbook.ts` — Order book (CLOB)
- `get_positions.ts` — Positions (Data API)
- `get_price.ts` — Price query (CLOB)
- `get_price_history.ts` — Historical prices
- `get_series.ts` / `get_series_by_id.ts` — Series data
- `get_spread.ts` — Bid-ask spread (CLOB)
- `get_tags.ts` — Tag/categories (Gamma)
- `get_tick_size.ts` — Minimum tick size (CLOB)
- `get_trades.ts` — Trade history (Data API)
- `search.ts` — Search markets/events (Gamma)

**Block Definitions** (UI configs, NOT merged):
- `apps/sim/blocks/blocks/kalshi.ts` — 676 lines, UI block config for workflow editor
- `apps/sim/blocks/blocks/polymarket.ts` — 432 lines, UI block config for workflow editor

---

## Merged Code

### 1. NEW: Kalshi Broker (`execution/kalshi.py`)

**File:** `src/quant_nanggroe_ai/execution/kalshi.py`  
**Lines:** 1,272  
**Source:** Adapted from 19 TypeScript files in `apps/sim/tools/kalshi/`

**Key Adaptations (TypeScript → Python):**
- All type interfaces → Pydantic models (KalshiMarket, KalshiOrder, KalshiPosition, etc.)
- `crypto.sign()` RSA-PSS → `cryptography` package `private_key.sign()` with PSS padding
- `fetch()` → `httpx.AsyncClient` with retry logic
- `buildKalshiAuthHeaders()` → `_build_auth_headers()` with timestamp + RSA-PSS signature
- `normalizePemKey()` → `_normalize_pem_key()` preserving the PEM normalization logic
- `handleKalshiError()` → exception-based error handling with logging
- All 17 Kalshi API operations implemented as async methods

**Methods:**
| Method | API | Auth Required |
|--------|-----|---------------|
| `get_markets()` | GET /markets | No |
| `get_market()` | GET /markets/{ticker} | No |
| `get_events()` | GET /events | No |
| `get_event()` | GET /events/{ticker} | No |
| `get_series_by_ticker()` | GET /series/{ticker} | No |
| `get_exchange_status()` | GET /exchange/status | No |
| `get_orderbook()` | GET /markets/{ticker}/orderbook | No |
| `get_trades()` | GET /trades | No |
| `get_candlesticks()` | GET /markets/candlesticks | No |
| `get_balance()` | GET /portfolio/balance | Yes |
| `get_positions()` | GET /portfolio/positions | Yes |
| `get_orders()` | GET /portfolio/orders | Yes |
| `get_order()` | GET /portfolio/orders/{id} | Yes |
| `get_fills()` | GET /portfolio/fills | Yes |
| `create_order()` | POST /portfolio/orders | Yes |
| `cancel_order()` | DELETE /portfolio/orders/{id} | Yes |
| `amend_order()` | POST /portfolio/orders/{id}/amend | Yes |

**Models:** 12 Pydantic models (KalshiMarket, KalshiEvent, KalshiSeries, KalshiBalance, KalshiPosition, KalshiOrder, KalshiOrderbook, KalshiOrderbookLevel, KalshiTrade, KalshiCandlestick, KalshiFill, KalshiExchangeStatus)

### 2. ENHANCED: Polymarket Broker (`execution/polymarket.py`)

**File:** `src/quant_nanggroe_ai/execution/polymarket.py`  
**Lines:** 1,456 (was 667, added ~789 lines)  
**Source:** Enhanced with features from 19 TypeScript files in `apps/sim/tools/polymarket/`

**New Models Added:**
- `PolymarketEvent` — Event with nested markets
- `PolymarketTag` — Tag/category
- `PolymarketSeries` — Series of related events
- `PolymarketOrderbookEntry` — Single orderbook level
- `PolymarketOrderbook` — Full orderbook with bids/asks
- `PolymarketPriceHistoryEntry` — Price history data point
- `PolymarketSearchResult` — Search results container
- `PolymarketSpread` — Bid-ask spread
- `PolymarketTradeRecord` — Trade from Data API

**New Methods Added:**
| Method | API Source | Description |
|--------|-----------|-------------|
| `get_events()` | Gamma API | List events with filters |
| `get_event()` | Gamma API | Get event by ID or slug |
| `get_orderbook()` | CLOB API | Order book for a token |
| `get_price()` | CLOB API | Price for token/side |
| `get_midpoint()` | CLOB API | Midpoint price |
| `get_last_trade_price()` | CLOB API | Last trade price |
| `get_spread()` | CLOB API | Bid-ask spread |
| `get_tick_size()` | CLOB API | Minimum tick size |
| `get_price_history()` | Gamma API | Historical price data |
| `get_tags()` | Gamma API | Available tags/categories |
| `get_series()` | Gamma API | Available series |
| `get_series_by_id()` | Gamma API | Series by ID |
| `search()` | Gamma API | Search markets/events |
| `get_trades()` | Data API | Trade history by wallet |
| `get_data_positions()` | Data API | Positions by wallet address |

**New Constants:** `DATA_URL = "https://data-api.polymarket.com"` (3rd API endpoint)

**New Helper Methods:** `_parse_market_from_gamma()`, `_parse_event()`, `_parse_series()`

### 3. UPDATED: Execution Package (`execution/__init__.py`)

- Added `KalshiBroker` import and export
- Added `"kalshi"` to `BrokerFactory._REGISTRY`
- Updated `BrokerType` union to include `KalshiBroker`
- Updated docstring with Kalshi broker type

---

## NOT Merged (and Why)

| Code | Reason |
|------|--------|
| Copilot v3 (191 commits, +24K lines) | AI chat assistant — not trading |
| Workflow blocks UI (+25K lines) | Visual workflow builder — not trading |
| AWS Lambda (+23K lines) | Serverless deployment — not trading |
| Microsoft tools (+4K lines) | Office/Teams integration — not trading |
| Execution filesystem (+8K lines) | File-based executor — not trading |
| Files support (+8K lines) | File upload UI — not trading |
| Rate-limiter storage factory | TypeScript pattern — not portable |
| MCP storage factory | TypeScript MCP protocol — not portable |
| Logging factory | TypeScript logging — not portable |
| Kalshi/Polymarket block configs | React UI blocks — not Python |
| Testing factories | TypeScript test helpers — not portable |
| Marketplace UI | React components — not portable |
| Hunter.io / Redtail / xAI tools | Non-trading integrations |
| CI/CD workflows | GitHub Actions — not Python |

---

## Dependency Requirements

### New dependency for Kalshi RSA-PSS authentication:
```
cryptography>=41.0.0
```

This is required for `KalshiBroker._generate_signature()` which uses RSA-PSS with SHA256. The broker gracefully degrades if not installed (logs warning, returns empty signature).

### Existing dependencies used:
- `httpx` — HTTP client (already in project)
- `pydantic` — Data models (already in project)

---

## Verification

- [x] `kalshi.py` — Python syntax check passed (ast.parse)
- [x] `polymarket.py` — Python syntax check passed (ast.parse)
- [x] `execution/__init__.py` — Python syntax check passed (ast.parse)
- [x] All new methods have docstrings with "Adapted from sim repo" attribution
- [x] All import paths use `quant_nanggroe_ai` package prefix
- [x] No TypeScript code copied directly — all converted to Python async patterns
- [x] Pydantic models replace TypeScript interfaces
- [x] httpx.AsyncClient replaces fetch()
- [x] Exception-based error handling replaces throw patterns

---

## Files Changed Summary

| File | Action | Lines |
|------|--------|-------|
| `src/quant_nanggroe_ai/execution/kalshi.py` | CREATED | 1,272 |
| `src/quant_nanggroe_ai/execution/polymarket.py` | ENHANCED | 1,456 (+789) |
| `src/quant_nanggroe_ai/execution/__init__.py` | UPDATED | +6 |
| **Total** | | **~2,067 net new lines** |
