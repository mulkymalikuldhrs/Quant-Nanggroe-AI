# OPTIMIZATION_REPORT — Quant-Nanggroe-AI (dashboard / API / factors / dead code)

> Profile: `fangbot` · Mode: FANG (Focus-Analyze-Navigate-Grow) · Ponytail: full (non-destructive only)
> Scope: dashboard bundle, API latency, dead code (`island_scan_report.md`), factor bloat.
> **No destructive changes applied.** All measurements taken read-only or via temporary, reverted config. Build artifact `.next` is gitignored.

---

## 0. TL;DR (before → after)

| Area | Before | After (if fixes applied) | Status |
|------|---------|---------------------------|--------|
| Production dashboard build | **BROKEN** — `next build` fails | compiles + deploys | 🔴 blocker |
| `.next` dev cache on disk | **600 MB** (`dev/`) | 0 (not committed) | 🟢 easy |
| Client static JS (first-load) | **~2.1 MB** (388 KB biggest chunk ×2) | ~1.4 MB (-33%) | 🟡 medium |
| API `live_engine` portfolio reads | **8 sequential queries** (= N+1) | 1 batched query | 🟡 medium |
| `audit_log` query | **unbounded** (`LIMIT 10000`) | paginated / indexed | 🟡 medium |
| Dead-code report usability | **"2/639 reachable" (false)** | real orphan set | 🟡 medium |
| Factor count auto-registered | **466** (UI caps at 50) | lazy-load by zoo | 🟡 medium |

> "After" = projected from the recommended fix, **not yet measured live** (non-destructive pass). Numbers marked 🟢 are verifiable now.

---

## 1. Dashboard bundle size

### Method
- No `.next` production build existed. Ran `npx next build` (Next 16.2.9, Turbopack) in `dashboard/`.
- **The build FAILED** (see §1.1). A clean production bundle could not be produced as-is.
- `du -sh node_modules` timed out (huge dep tree: 403 pkgs in `dashboard/node_modules`). Not a runtime cost — node_modules is never shipped.

### Measured (from the partial/last successful compile)
| Metric | Value |
|---------|-------|
| Client `static/chunks` total | **2.1 MB** (`du -sh .next/static/chunks`) |
| Largest single chunk | **388 KB** × 2 (`0k30ej8iepuiy.js`, `0067j8__2rd3f.js`) |
| Prerendered routes (`.html` emitted) | **15** of 19 attempted |
| `.next/server` (SSR) | 17 MB |
| `.next/dev` (stray dev cache) | **600 MB** (must never ship) |

### 1.1 🔴 BLOCKER — production build is broken
`next build` fails on **two** independent faults in `dashboard/src/app/trading/page.tsx`:
1. **Type error**: `Cannot find name 'setAccounts'` (line 105) — `setAccounts` is called but never declared in the component.
2. **Runtime prerender error**: `ReferenceError: accounts is not defined` — `accounts` is referenced but never declared.

Neither is caught by `next dev` (dev tolerates it), so CI/deploy would ship a broken build or fail the pipeline. **Fix before any perf work matters.**

### 1.2 Quick wins (non-destructive to apply later)
- Delete `dashboard/.next/dev` (600 MB) — it is a dev cache, gitignored, regenerated on `next dev`.
- The two 388 KB chunks are likely `recharts` (v3) + `framer-motion` (dashboard) / `lightweight-charts`. Both dashboards pull chart libs. **Shared-chart strategy + `dynamic()` import of heavy chart pages** would cut first-load ~33%.
- Both `dashboard/` and root `src/app` are separate Next apps. Root `src/app` appears to be a stale duplicate SPA (no API routes, pure components). Confirm which is canonical; delete the other to halve maintenance + confusion.

---

## 2. API latency (N+1 / full table scan)

The FastAPI backend lives in `quant_nanggroe/api/` (32 route files, wired in `qna.py:235`). It uses **in-memory engines + raw SQL cursors** (sqlite), not an ORM — so classic ORM N+1 isn't present, but **sequential-key-lookup N+1** and **unbounded scans** are.

### 2.1 🟡 `live_engine.py` — 8 sequential single-key reads (= N+1)
`quant_nanggroe/live_engine.py` reads portfolio/engine_state with one `SELECT … WHERE key=?` per field:
```
SELECT value FROM portfolio WHERE key='total_trades'   (line 384)
SELECT value FROM portfolio WHERE key='winning_trades' (line 386)
SELECT value FROM engine_state WHERE key='cycle_count'  (line 531)
SELECT value FROM engine_state WHERE key='total_errors'  (line 535)
… + 4 more (8 total)
```
Every stats call = 8 round-trips. **Fix**: `SELECT key, value FROM portfolio` once, build a dict. One query, zero N+1.

### 2.2 🟡 `security/audit.py` — unbounded scan
- `SELECT * FROM audit_log` (line 329) — full table dump, no `WHERE`, no `LIMIT`.
- `await self.query(start_date=start, end_date=end, limit=10000)` (line 421) — `LIMIT 10000` is a de-facto full scan on a hot path.

**Fix**: `WHERE ts BETWEEN ? AND ? ORDER BY ts DESC LIMIT 100 OFFSET ?` + ensure index on `(ts)`.

### 2.3 🟡 `security/audit.py` / `live_engine.py` — `SELECT *`
`SELECT * FROM audit_log` and `SELECT * FROM strategy_stats` (live_engine:371) pull every column. Fine for small tables, but `audit_log` grows unbounded → becomes a scan. Select explicit columns + add indexes on filter columns.

### 2.4 Not a problem (verified)
- The API routes use in-memory backtest engines (`BacktestEngine`, `ExecutionManager`) — no per-request DB round-trips there. Latency risk is concentrated in `live_engine` stats + `audit_log`, above.

---

## 3. Dead code (`island_scan_report.md`)

### 3.1 🔴 The report's headline metric is WRONG
`island_scan_report.md` claims:
> Modules scanned: 639 · Reachable from entry points: **2**

This is **false**. Verification:
- `grep -rl "import quant_nanggroe" --include=*.py .` → **495 files import the package.**
- `quant_nanggroe.api` is listed ORPHAN but `qna.py:235` does `from quant_nanggroe.api.app import create_app`. It is the actual API server.
- `quant_nanggroe.engine.factors.registry` is listed ORPHAN but is imported by `quant_nanggroe/mcp/tools.py`.

The scanner's "entry points: 6 / reachable: 2" logic is broken (likely it only treated a handful of scripts as roots and missed `qna.py` + the FastAPI app + dashboard's API client as consumers). **520 "ORPHAN" lines are therefore untrustworthy as a deletion list.**

### 3.2 What IS real
The repo genuinely carries large **unused/aspirational surface area** (the orphans cluster around `agents/*`, `exchange/*`, `debate/*`, `personas/*` — many are scaffolded agent modules not wired into the running engine). But the scan can't tell you *which* are safe to delete. **Do not bulk-delete from this report.**

### 3.3 Recommended fix (non-destructive)
1. Re-run the scan with **correct roots**: `qna.py`, `quant_nanggroe/api/app.py`, `dashboard/src/**` (TS consumers), `tests/`. Use `vulture`/`pyflakes` + `madge` (circular/orphan) instead of the custom scanner.
2. Produce a **vetted** orphan list (confirmed zero importers across the real root set) before any deletion.
3. Quarantine (move to `attic/`) for one release cycle, don't `rm`.

---

## 4. Factor bloat (>50 factors?)

**Yes — massively.** `quant_nanggroe/engine/factors/registry.py:_register_builtin_factors()` auto-loads:

| Zoo | File | Factors | LOC |
|------|------|---------:|----:|
| Alpha101 | `alpha101.py` | **101** | 3,316 |
| GTJA191 | `gtja191.py` | **191** | 5,543 |
| Qlib158 | `qlib158.py` | **158** | 4,063 |
| Academic | `academic.py` | 6 | 247 |
| Fundamental (class) | `fundamental.py` | 8 | 295 |
| Technical (class) | `technical.py` | 2 | 349 |
| **Total** | | **466** | **~15.5k** |

- **456** factors are auto-registered on every `FactorRegistry()` init (Alpha101+GTJA191+Qlib158+Academic).
- **Every** `get_all_*_factors()` call instantiates all factors eagerly. Importing the registry → 456 object constructions at startup.
- The dashboard `factors/page.tsx` **hard-caps display at 50** (`.slice(0, 50)`) — the UI literally cannot show its own factor count. It also ships **mock data** (14 hardcoded factors) because the live API `/api/backtest/factors` only returns **5** factor stubs.

### 4.1 Fix (non-destructive)
- **Lazy-load by zoo**: don't auto-register all 456. Register on demand: `registry.load_zoo("gtja191")` when a strategy requests it. Cuts cold-start + memory.
- **Don't instantiate at import**: `get_all_*_factors()` should return metadata/factories, not live `AlphaFactor` objects, until actually computed.
- **Cap the registry surface**: most strategies use <20 factors. Make the default registry ~20 curated factors; exotic zoos opt-in.
- **Fix the UI contract**: either raise the 50-cap (virtualized list) or paginate; and wire the live endpoint to return the real zoo counts instead of 5 stubs + 14 mocks.

---

## 5. Recommended actions (priority order)

1. 🔴 **Fix `dashboard/src/app/trading/page.tsx`** (declare `accounts`/`setAccounts`). Unblocks `next build` → deploy. *Destructive? No — add 1–2 lines.*
2. 🟢 **Delete `dashboard/.next/dev`** (600 MB) and add a CI guard that fails if `.next` is committed.
3. 🟡 **Batch `live_engine` portfolio reads** (8 → 1 query). *No schema change.*
4. 🟡 **Bound + index `audit_log`** queries. Add `CREATE INDEX` migration.
5. 🟡 **Lazy-load factor zoos** (466 → ~20 default). Biggest single memory/startup win in the Python side.
6. 🟡 **Re-run dead-code scan with correct roots**; quarantine, don't delete.
7. 🟡 **Dedupe the two Next apps** (root `src/app` vs `dashboard/`).
8. 🟡 **Code-split chart libs** via `next/dynamic` to cut 2.1 MB → ~1.4 MB first load.

---

## 6. Verification notes (reproducibility)
- Build: `cd dashboard && NEXT_TELEMETRY_DISABLED=1 npx next build` → fails at `trading/page.tsx`.
- Factor count: `grep -cE "^def |^class "` over `engine/factors/{alpha101,gtja191,qlib158,fundamental,academic,technical}.py` + registry `function_modules` list (`registry.py:237`).
- N+1: `grep -nE "SELECT value FROM (portfolio|engine_state) WHERE key=" quant_nanggroe/live_engine.py` → 8 hits.
- Dead-code refutation: `grep -rl "import quant_nanggroe" --include=*.py . | wc -l` → 495.

## 7. What I did NOT change
- `next.config.ts`: temporarily set `typescript.ignoreBuildErrors` for measurement only, then **restored from backup** (`git diff dashboard/next.config.ts` is empty).
- `src/app/trading`: moved out and back for a clean build attempt; **byte-identical** to original.
- No files deleted. No `git commit`. `.next/` is gitignored.
