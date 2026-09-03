# DEAD API Triage (v8.1.0)

> SSOT: `CANONICAL.md`. Method: every backend route in `quant_nanggroe/api/routes/*.py`
> was grepped against `dashboard/src/**` (pages, components, lib, proxies).
> A route is DEAD when it has **zero dashboard callers**. Verified 2026-09-03.
> Deprecation only in this workstream — no router deleted, no import broken.

## ALIVE (have dashboard callers — KEEP, not deprecated)

| Router | Evidence of caller |
|--------|-------------------|
| `assistant.py` (`/api/assistant/chat`, `/chat_llm`) | `dashboard/src/components/assistant/assistant-widget.tsx:113,117` |
| `colony.py` (`/api/colony/list`, `/create`, `/{id}`, `/{id}/run`) | `dashboard/src/lib/api-client.ts:325-331` (colonyApi, used by `app/colony/page.tsx`) |
| `auth.py` (`POST /api/auth/token`) | `dashboard/src/lib/websocket.ts:88` — stays per spec |

## DEAD (zero dashboard callers — deprecated, keep-or-remove below)

| # | Backend routes | Full paths | Recommendation |
|---|---------------|------------|----------------|
| 1 | `agentic.py:43,86,123` — `POST /berkshire`, `POST /consensus`, `GET /agents` | `/api/agentic/*` | REMOVE — no callers; overlaps alive `/api/agents/*`. |
| 2 | `analytics.py:30,55,82` — `POST /metrics`, `POST /compare`, `GET /metrics-list` | `/api/analytics/*` | REMOVE — no callers; metrics covered by alive `/api/portfolio/performance`. |
| 3 | `fred.py:41,75,109` — `GET /series`, `GET /series/{id}`, `GET /search` | `/api/fred/*` | KEEP-if-macro-page-planned else REMOVE — wired to real FRED API, just unwired. |
| 4 | `sec_edgar.py:25,64,82,99,113,131` — `GET /filings`, `/company/{cik}`, `/search`, `/fundamentals/{cik}`, `/financials/{cik}`, `/health` | `/api/sec/edgar/*` | REMOVE — equity-only scope; QNA is FX/commodity per CANONICAL 15.8. |
| 5 | `options.py:58,72,85,156,188,247` — `GET /chain/{s}`, `GET /positions`, `POST /analyze`, `/vol-surface`, `/strategy`, `/strategy/named` | `/api/options/*` | REMOVE — no options trading in scope, no callers. |
| 6 | `personas.py:39,58,70,88` — `GET /list`, `/types`, `/{id}`, `POST /{id}/analyze` | `/api/personas/*` | REMOVE — agents page uses alive `/api/agents/*` instead. |
| 7 | `rl.py:29,90,122` — `POST /train`, `POST /inference`, `GET /agents` | `/api/rl/*` | REMOVE — numpy-only nets with no live market replay (see its own docstring). |
| 8 | `whatsapp.py:538,560,583,613,637` — `POST /webhook`, `/notify`, `/trade-alert`, `/risk-warning`, `GET /status` | `/api/whatsapp/*` | KEEP-if-bridge-planned else REMOVE — needs external WhatsApp bridge service. |
| 9 | `ensemble.py:36,105,118,132,145,153` — `POST /vote`, `GET /adapters`, `/risk/kelly`, `/risk/monte-carlo`, `/scanner/summary`, `/scanner/pairs` | `/api/ensemble/*` | REMOVE — consensus covered by alive `/api/council/*` + `/api/debate/*`. |
| 10 | `otto_proxy.py:7` — `{full_path:path}` catch-all | `/api/otto/*` | REMOVE — proxy to external `localhost:8765` service, no callers. |
| 11 | `signal_generator.py:82,98,108,171` — `GET /list`, `/active`, `POST /generate`, `/batch-generate` | `/api/signals/*` | REMOVE — superseded by alive `/api/market/signals` + `/api/backtest/*`. |
| 12 | `ecosystem.py:20,56,97,119` — `GET /status`, `/overview`, `/exchange/list`, `/security/events` | `/api/status`, `/api/overview`, `/api/exchange/list`, `/api/security/events` | REMOVE — no callers; also `/api/security/events` shadows the alive security router (ecosystem mounts first in `app.py:370` vs `391`). |
| 13 | `colony.py:129` — `GET /colony/status` only (rest of router alive) | `/api/colony/status` | REMOVE route — colony page never calls it; keep the router. |

## Client methods removed (zero callers, verified)

- `agentsApi.getDecisions` (`api-client.ts`) — no page called `/api/agents/decisions`; backend never had it.
- `portfolioApi.getRiskParity` (`api-client.ts`) — `app/portfolio/page.tsx` uses summary/performance/equity-curve/risk only.

## Correction (2026-09-04, coordinator verification)

- `engine/data/cot_provider.py` is **LIVE — do NOT archive.** It has 4 real importers:
  `engine/strategies/cot_strategy.py:39`, `engine/live/adaptive_integration.py:439,471`,
  `engine/fundamental/cot.py:24` (now archived, import moved with it),
  `tests/test_cot_provider_contract.py:14`. The WS-F "safe to archive" verdict
  was wrong for this file (it correctly identified `engine/fundamental/cot.py` only).
- `engine/fundamental/cot.py` (COTParser, zero external importers) → archived to
  `archive/cot_parser_2026-09-04.py`; removed from `engine/fundamental/__init__.py`
  imports/`__all__`. Canonical COT path: `engine/cot/cot_analyzer.py` (analysis) +
  `engine/risk/cot_position_guard.py` (live pipeline via `autonomous.py:2292-2295`) +
  `engine/data/cot_provider.py` (compat shim).
