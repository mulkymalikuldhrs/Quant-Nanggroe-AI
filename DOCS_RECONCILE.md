# DOCS_RECONCILE.md — Docs vs Code Reconciliation

**Scope:** `docs/02_ARCHITECTURE.md`, `docs/04_API.md`, `CLAUDE.md`
vs actual code in `quant_nanggroe/api/routes/*.py` and `quant_nanggroe/engine/*`.
**Date:** 2026-07-15 · **Profile:** autobot · **Method:** ponytail (full).

## TL;DR — the big one

The docs describe the API as served under **`/api/v1/*`**. The actually-served app
(`quant_nanggroe/api/app.py`, launched by `qna.py api`) mounts every router under
**`/api/*`** — `grep -c "/api/v1" quant_nanggroe/api/app.py` → **0**. The dashboard
client (`dashboard/src/lib/api-client.ts`) also calls `/api/*`. So the documented
"API prefix mismatch" (backend `/api/v1/*` vs client `/api/*`) **does not exist** —
it was invented. The only code still using `/api/v1/*` is the **dead** module
`quant_nanggroe/api.py` (v0.2.0), which is not the server that runs.

## Stale / wrong claims found and fixed

| # | Doc | Claim (wrong) | Reality | Fix |
|---|-----|---------------|---------|-----|
| 1 | 02_ARCH, 04_API | API served at `/api/v1/*`; "prefix mismatch" tracked | Served at `/api/*`; no mismatch | Rewrote prefixes to `/api/*`; struck the mismatch constraint |
| 2 | 02_ARCH | "29 route modules in `api/routes/` … mounted in `api/app.py`" | 30 modules in `quant_nanggroe/api/routes/`; mounted in `quant_nanggroe/api/app.py` | Corrected path + count to 30 |
| 3 | 02_ARCH | Engine table: **`engine/trading/`** = Order execution | `engine/trading/` does **not exist**; real module is **`engine/execution/`** (`base.py`, `order.py`, `manager.py`) | Repointed to `engine/execution/` |
| 4 | 02_ARCH | Strategies = **106** | 107 strategy files in `engine/strategy/strategies/` | → 107 |
| 5 | 02_ARCH, 04_API | Version **v4.5.0** | Actual `__version__` = **4.3.4** (qna.py, `quant_nanggroe/__init__.py`) | → v4.3.4 |
| 6 | 04_API | Route #1 `_data.py` → `/api/data` (system health) | `_data.py` has **0 routes**, is **not imported** in `app.py`; it only holds synthetic stub data for other routes | Marked "(not mounted)"; pointed to `/health` |
| 7 | 04_API | Autonomous module prefix `/api/v1` | Real prefix is `/api/autonomous` (and its 10 routes) | → `/api/autonomous` |
| 8 | 04_API | Rate limit "per-IP 100/min, per-key 1000/min, `X-RateLimit-*` headers" | `RateLimitMiddleware` = per-IP only, **60/min**, in-memory; **no** per-key limit, **no** rate-limit headers | Corrected to 60/min, per-IP only, no headers |
| 9 | 04_API | "All endpoints return `{"success","data","error"}` envelope" | Only **3 of 31** route modules use that envelope; most return plain dicts/Pydantic | Rewrote as "Response Shape" note |

## Verified CORRECT (no change needed)

- **CLAUDE.md** — references `48_REPOSITORY_AUDIT.md`, `02_ARCHITECTURE.md`, `04_API.md`,
  `12_TASKS.md`; all four files exist. No stale pointers.
- **Exchange layer** — `quant_nanggroe/exchange/` exists with `base.py` + broker impls.
- **`providers/`** — exists (`coingecko`, `finnhub`, `macro`, `proxy`, …). ARCH table is
  roughly accurate (note: `twelvedata.py` not present; `openbb` lives under `data/providers`).
- **Security** — `quant_nanggroe/security/` exists with `auth.py`, `encryption.py`,
  `keyvault.py`, etc. Auth roles (admin/trader/viewer) match `security/auth.py`.
- **Dashboard stack** — Next.js 16 / React 19 / Tailwind v4 / Prisma v6 all match `package.json`.
- **WebSocket** — `/ws`-mounted `ws.py` exposes a `/stream` websocket (client uses
  `ws://host:8000/api/ws/stream` — this is the one real `/api/ws` divergence, cosmetic, not documented as broken).

## Module inventory (ground truth)

**Route modules (`quant_nanggroe/api/routes/`): 30 files.**
`_data`, `agentic`, `agents`, `analytics`, `autonomous`(10), `backtest`, `brokers`,
`channels`, `colony`, `council`, `credentials`, `debate`, `ecosystem`, `fred`,
`geopolitics`, `market`, `memory`, `monitor`, `options`, `personas`, `portfolio`,
`rl`, `sec_edgar`, `signal_generator`, `strategies`, `strategy`, `trading`, `whatsapp`,
`wiring_compat`, `ws`.

**Engine subdirs (`quant_nanggroe/engine/`):** agentic, analysis, analytics, api, autonomous,
backtest (17), colony, core, data (7), execution (6), factors (10), fundamental, integration,
kelly (9), live, ml, models, nvidia_nim, options, pattern_recorder, portfolio, regime (7),
risk (18), rl, screener (10), shadow, simulation, smc, strategy (9 + strategies/107),
stress_testing, visualization.

## Action items (not doc bugs, but real gaps)

1. **Delete or archive `quant_nanggroe/api.py`** — dead v0.2.0 app using `/api/v1/*`; it is
   the sole source of the phantom prefix and confuses readers. `quant_nanggroe/cli.py` still
   calls `http://localhost:8000/api/v1/portfolio` → would 404 against the live server.
2. **`engine/simulation/` is empty** (only `__init__.py`) — ARCH lists a simulation layer;
   confirm intentional or drop from mental model.
3. **`twelvedata.py`** named in ARCH provider table is absent (only `data/providers` has a
   finnhub/openbb set). Confirm or remove.

## Files modified

- `docs/02_ARCHITECTURE.md` — paths, counts, prefixes, version, constraints #1/#2.
- `docs/04_API.md` — version, all `/api/v1/*` → `/api/*`, `_data.py` entry, autonomous
  prefix, rate-limit values, response-envelope note, prefix-mismatch note.

## Verification

```bash
grep -rc "/api/v1" quant_nanggroe/api/app.py            # 0 — live app clean
grep -rl "v4.5.0" docs/02_ARCHITECTURE.md docs/04_API.md # (none after fix)
ls quant_nanggroe/engine/trading 2>&1                    # No such file (now points to execution/)
python -c "import quant_nanggroe,sys; print(quant_nanggroe.__version__)"  # 4.3.4
```
