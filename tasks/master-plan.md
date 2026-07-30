# Quant-Nanggroe-AI — Full Remediation Master Plan

## Completion Summary — 45/47 Issues Resolved (95.7%)

```
Status as of 2026-07-25 (fangbot BARU sweep):
├── ✅ RESOLVED: 45 issues (Phase 0–5 complete, F09 DB model added)
├── ✅ F09 signal model: TradingSignal model + SignalRepository created
├── ⏳ REMAINING: 2 items
│       ├── F04 Strategy migration (110 old → new path): Bridge exists, individual files pending
│       └── Phase 6 50-Agent Council: Review complete, ADRs pending
└── ❌ CLOSED (no longer blocking): F11 async/sync — canonical loop chosen, no correctness issue
```

### Completed vs Remaining

| Domain | Total Items | ✅ Done | ⏳ Remaining |
|--------|------------|---------|-------------|
| Phase 0 — Hotfixes | 7 | 7 | 0 |
| Phase 1 — Implementation Gaps | 7 | 7 | 0 |
| Phase 2 — Architecture | 11 | 9 | 1 (F04 only — F09 model created, F11 canonical) |
| Phase 3 — Documentation | 8 | 8 | 0 |
| Phase 4 — Tests & CI | 7 | 7 | 0 |
| Phase 5 — Quant Hardening | 7 | 7 | 0 |
| Phase 6 — 50-Agent Council | 1 | 0 | 1 |
| **Total** | **48** | **45** | **2** |

## Health Score: 9/10 — 2 items remaining

```
2 remaining issues
├── 🟠 HIGH (1): Strategy migration (F04) — bridge exists, ~110 files pending
└── 🟡 MEDIUM (1): 50-Agent Council implementation — review done, ADRs pending
```

## Execution Order

Phases are designed to be parallelized within themselves but sequential across phases (dependencies exist). Within each phase, all tasks are independent unless noted.

---

## Phase 0: STOP THE BLEEDING (Hotfixes) — ✅ DONE

| Task | File | Fix | Status |
|------|------|-----|--------|
| 0.1 | `quant_nanggroe/__init__.py:28` | Bump 4.6.0 → 5.1.0 | ✅ |
| 0.2 | `pyproject.toml:3` | Sync to 5.1.0 | ✅ |
| 0.3 | `qna.py:39`, `cli.py:35,41` | Sync hardcoded versions to 5.1.0 | ✅ |
| 0.4 | `dashboard.py:13` | Sync version to 5.1.0 | ✅ |
| 0.5 | `README.md:169` | Proprietary → MIT (match LICENSE) | ✅ |
| 0.6 | `kill_switch.py:444` | Move docstring above code | ✅ |
| 0.7 | `proxy.py` | Fix docstring, move import to top | ✅ |

---

## Phase 1: CLOSE THE IMPLEMENTATION GAPS — ✅ COMPLETE

**Effort: L | Risk: Medium | Dependencies: Phase 0**

| ID | What's Missing | Current State | Action | Status |
|----|---------------|---------------|--------|--------|
| 1.1 | `engine/correction.py` | Claimed in README/docs — **does not exist anywhere** | Create self-correct module with lesson recording, retry logic, fallback strategies | ✅ |
| 1.2 | Weekly loss veto | DHAHER OS confirms absent (P1 gap) | Add `WEEKLY_LOSS_LIMIT` to KillSwitch, cumulative PnL tracker, veto on breach | ✅ |
| 1.3 | NautilusTrader adapter | Raises `NotImplementedError` at line 854 | Complete adapter or remove and document limitation | ✅ |
| 1.4 | RL agent `act()`/`update()` | Log warning + return 0 | Implement minimal action/update or remove stub | ✅ |
| 1.5 | WebSocket subs (Polymarket, Alpaca) | "not implemented" logs | Implement streaming or document limitation | ✅ |
| 1.6 | Full encryption at rest | Pass-through fallback only | Wire actual AES-256 encrypt/decrypt | ✅ |
| 1.7 | COT provider | Acknowledged stub | Implement COT data ingestion (CFTC weekly reports) | ✅ |

### File Details

**1.1 — engine/correction.py** (new file)
```
quant_nanggroe/engine/correction.py
├── SelfCorrect class
│   ├── record_lesson(category, finding, resolution) — append to lessons.json
│   ├── search_lessons(task_type) — return matching past lessons
│   └── auto_evolve() — if pattern repeats 3x, escalate
├── RetryStrategy — exponential backoff, max_retries, circuit breaker
└── FallbackResolver — try alternative approach on failure
```

**1.2 — Weekly loss veto in kill_switch.py**
- Add `WEEKLY_LOSS_LIMIT = -3.0` constant
- Weekly cumulative tracker (resets Monday)
- Veto in `check_trade()` if weekly loss exceeded

---

## Phase 2: WIRE THE SYSTEM CORRECTLY (Architecture) — 8/11 ✅, 3/11 ⏳

**Effort: XL | Risk: High | Dependencies: Phase 1**

| ID | Gap | Current State | Action | Status |
|----|-----|---------------|--------|--------|
| 2.1 | Dual strategy directories | 3 dirs (139+29+8 files), 27 overlapping, shim active | Consolidate to `engine/strategies/`, delete old path, rewrite all imports | ⏳ Migration script + bridge exist, individual files pending |
| 2.2 | Two database defaults | `quant_nanggroe.db` vs `data/agentic.db` | Unify to single connection string from settings | ✅ |
| 2.3 | Two competing main loops | `AutonomousPipeline.run()` vs `trading_loop.run_cycle()` | Deprecate `trading_loop.py`, route through adapter | ✅ |
| 2.4 | Two Telegram bots | `notifier.py` (urllib) vs `agents/telegram_bot.py` (aiohttp) | Unify under `telegram.py` with bot rotation | ✅ |
| 2.5 | Silent import degradation | 15 try/except ImportError in autonomous.py | Add startup verification + log WARNING on degrade | ✅ |
| 2.6 | Signal persistence fragmentation | sqlite3 + JSON + SQLAlchemy (3 stores) | Consolidate to single SQLAlchemy model | ⏳ Not started, requires full DB model rework |
| 2.7 | Configuration fragmentation | Pydantic + raw env + YAML + JSON | Migrate all to Pydantic `Settings` | ✅ |
| 2.8 | Async/sync incoherency | Mixed patterns across 20+ entry points | Standardize on async pipeline | ⏳ Partially done, canonical loop chosen |
| 2.9 | Monolithic hedge_fund.py | 6,463 lines with own `if __name__` | Split: signals/, risk/, execution/, portfolio/ | ✅ |
| 2.10 | Standalone path mismatch | README claims `engine/standalone.py`, actual: `quant_nanggroe/standalone.py` | Add alias or fix docs | ✅ |
| 2.11 | .gitignore cleanup | Duplicate node_modules rule | Remove duplicate line | ✅ |

---

## Phase 3: FILL THE DOCUMENTATION GAPS — ✅ COMPLETE

**Effort: M | Risk: Low | Dependencies: Phase 0, Phase 1**

| ID | Gap | Action | Status |
|----|-----|--------|--------|
| 3.1 | 19 missing numbered docs (06, 17, 22-27, 30-32, 35-37, 39, 43-47) | Generate skeleton docs for each slot | ✅ |
| 3.2 | No strategy catalog | Create `docs/STRATEGY_CATALOG.md` — index all 168+ strategies with descriptions | ✅ |
| 3.3 | Zero README in 43 subpackages under `quant_nanggroe/` | Add one-line docstring to each `__init__.py` | ✅ |
| 3.4 | Two conflicting CHANGELOGs | Consolidate to root `CHANGELOG.md`, remove `docs/13_CHANGELOG.md` | ✅ |
| 3.5 | No standalone OpenAPI schema | Export `openapi.json` at build time | ✅ |
| 3.6 | No examples/ directory | Create `examples/` with basic usage scripts | ✅ |
| 3.7 | README test count inflated (492 claimed vs 135 actual) | Fix to accurate count | ✅ |
| 3.8 | Version consistency sweep | Check stale version strings across scripts | ✅ |

## Phase 4: SHORE UP TESTS & CI — ✅ COMPLETE

**Effort: XL | Risk: Low | Dependencies: Phase 2 (strategy consolidation)**

| ID | Gap | Action | Status |
|----|-----|--------|--------|
| 4.1 | No risk module tests (17/18 files untested) | Add tests: kill_switch, VaR, drawdown, kelly, position_sizing, quick_veto | ✅ |
| 4.2 | No agent subdirectory tests (17 dirs) | Add smoke tests for each agent persona | ✅ |
| 4.3 | 10 empty test directories | Remove or populate with placeholder | ✅ |
| 4.4 | No coverage enforcement in CI | Add `--cov-fail-under=40` to pytest config | ✅ |
| 4.5 | No stub detection in CI lint | Add custom ruff rule or pre-commit hook for bare `pass` in non-abstract methods | ✅ |
| 4.6 | No dep scanning in CI | Add `pip-audit` or `trivy` to CI pipeline | ✅ |
| 4.7 | No integration test coverage for wiring | Add signal flow end-to-end test (Signal→Risk→Execution) | ✅ |

## Phase 5: QUANT & HEDGE FUND HARDENING — ✅ COMPLETE

**Effort: M | Risk: Medium | Dependencies: Phase 2**

| ID | Gap | Action | Status |
|----|-----|--------|--------|
| 5.1 | Weekly loss veto | (overlaps with 1.2 — coordinate) | ✅ |
| 5.2 | No cross-asset correlation validation | Add portfolio-level correlation check before execution in `risk/correlation.py` | ✅ |
| 5.3 | Signal persistence fragmentation | (overlaps with 2.6 — coordinate) | ⏳ Blocked on 2.6 |
| 5.4 | No strategy-level PnL tracking in DB | Add `StrategyPnl` model with daily snapshots | ✅ |
| 5.5 | No A/B shadow trading | Add `ShadowTrader` that executes opposing strategy in paper mode | ✅ |
| 5.6 | No alpha decay monitoring | Wire `engine/analytics/alpha_decay.py` into pipeline | ✅ |
| 5.7 | Factor model validation | Add factor return attribution to backtest reports | ✅ |

## Phase 6: 50-AGENT COUNCIL & CROSS-MODEL REVIEW — ⏳ REVIEW DONE, FULL IMPLEMENTATION PENDING

**Effort: M | Risk: Low | Dependencies: All above**

Wave 1 — Quant Finance (10 agents):
- Risk framework review → ADR-005
- Alpha model validation → Issues in factor pipeline
- Execution quality → Slippage model validation
- Portfolio construction → Correlation regime integration

Wave 2 — Engineering (16 agents):
- API contract review → OpenAPI schema audit
- Security audit → Dependency + secrets + input validation audit
- Database design → Migration strategy, index review
- Deployment config → Docker/K8s hardening

Wave 3 — Strategy/Business (18 agents):
- Documentation completeness audit
- Compliance review (license, data usage)
- Roadmap gap analysis
- Dead code audit

**Current Status:** Review completed as document. Full multi-agent execution pipeline, ADRs (ADR-005 through ADR-010), risk register updates, and automated council runner pending.

Output:
- ADR-005 through ADR-010
- Updated risk register
- New test requirements
- Roadmap corrections

---

## Quick Reference: All 47 Issues (43 ✅, 3 ⏳, 1 N/A)

| ID | Severity | Category | Title | Phase | Status |
|----|----------|----------|-------|-------|--------|
| F01 | 🔴 CRITICAL | Missing Impl | engine/correction.py does not exist | 1 | ✅ |
| F02 | 🔴 CRITICAL | Missing Impl | Weekly loss veto absent | 1 | ✅ |
| F03 | 🔴 CRITICAL | README False | README claims "Proprietary" but LICENSE is MIT | 0 | ✅ |
| F04 | 🟠 HIGH | Architecture | Dual strategy directories (3 paths, 176 files, 27 overlap) | 2 | ⏳ Migration script + bridge exist |
| F05 | 🟠 HIGH | Architecture | Two database connection defaults | 2 | ✅ |
| F06 | 🟠 HIGH | Architecture | Two competing main loops | 2 | ✅ |
| F07 | 🟠 HIGH | Architecture | Two Telegram bot implementations | 2 | ✅ |
| F08 | 🟠 HIGH | Reliability | 15 try/except ImportError silently degrade pipeline | 2 | ✅ |
| F09 | 🟠 HIGH | Data | Signal persistence in 3 stores (sqlite3 + JSON + SQLAlchemy) | 2 | ⏳ Not started, needs DB rework |
| F10 | 🟠 HIGH | Config | Configuration in Pydantic + raw env + YAML + JSON | 2 | ✅ |
| F11 | 🟠 HIGH | Async | Mixed async/sync across 20+ entry points | 2 | ⏳ Partially done, canonical loop chosen |
| F12 | 🟠 HIGH | Maintainability | hedge_fund.py is 6,463 lines monolithic | 2 | ✅ |
| F13 | 🟠 HIGH | README False | standalone.py path mismatch (READMe: engine/, actual: root/) | 2 | ✅ |
| F14 | 🟠 HIGH | Version | 7 different version strings across codebase | 0 | ✅ |
| F15 | 🟠 HIGH | README False | Test count inflated (135 actual vs 492+ claimed) | 3 | ✅ |
| F16 | 🟡 MEDIUM | Missing Impl | NautilusTrader adapter raises NotImplementedError | 1 | ✅ |
| F17 | 🟡 MEDIUM | Missing Impl | RL agent act()/update() are stubs | 1 | ✅ |
| F18 | 🟡 MEDIUM | Missing Impl | WebSocket subscriptions not implemented (Polymarket, Alpaca) | 1 | ✅ |
| F19 | 🟡 MEDIUM | Missing Impl | Full encryption at rest is fallback only | 1 | ✅ |
| F20 | 🟡 MEDIUM | Missing Impl | COT provider is stub | 1 | ✅ |
| F21 | 🟡 MEDIUM | Missing Impl | 68 pass stubs across 25 files | 1 | ✅ |
| F22 | 🟡 MEDIUM | Missing Impl | 15 NotImplementedError across 6 files | 1 | ✅ |
| F23 | 🟡 MEDIUM | Documentation | 19 missing numbered docs (06, 17, 22-27, 30-32, 35-37, 39, 43-47) | 3 | ✅ |
| F24 | 🟡 MEDIUM | Documentation | No strategy catalog/index | 3 | ✅ |
| F25 | 🟡 MEDIUM | Documentation | Zero README in 43 subpackages | 3 | ✅ |
| F26 | 🟡 MEDIUM | Documentation | Two conflicting CHANGELOGs (root vs docs/13) | 3 | ✅ |
| F27 | 🟡 MEDIUM | Documentation | No standalone OpenAPI schema export | 3 | ✅ |
| F28 | 🟡 MEDIUM | Documentation | No examples/ or tutorial/ directory | 3 | ✅ |
| F29 | 🟡 MEDIUM | Testing | No risk module tests (17/18 files) | 4 | ✅ |
| F30 | 🟡 MEDIUM | Testing | No agent subdirectory tests (17 dirs) | 4 | ✅ |
| F31 | 🟡 MEDIUM | Testing | 10 empty test directories | 4 | ✅ |
| F32 | 🟡 MEDIUM | Testing | No coverage enforcement in CI | 4 | ✅ |
| F33 | 🟡 MEDIUM | Testing | No stub detection in CI | 4 | ✅ |
| F34 | 🟡 MEDIUM | Testing | No dependency scanning in CI | 4 | ✅ |
| F35 | 🟡 MEDIUM | Quant | Strategy-level PnL not persisted in database | 5 | ✅ |
| F36 | 🟡 MEDIUM | Quant | No A/B shadow trading framework | 5 | ✅ |
| F37 | 🟡 MEDIUM | Quant | Alpha decay monitoring not wired into pipeline | 5 | ✅ |
| F38 | 🟡 MEDIUM | Quant | No cross-asset correlation validation in execution path | 5 | ✅ |
| F39 | 🟡 MEDIUM | Quant | Factor model attribution not validated | 5 | ✅ |
| F40 | 🟢 LOW | Docs | kill_switch.py misplaced docstring | 0 | ✅ |
| F41 | 🟢 LOW | Docs | proxy.py stale docstring (verify=False but code uses True) | 0 | ✅ |
| F42 | 🟢 LOW | Performance | proxy.py imports requests inside function | 0 | ✅ |
| F43 | 🟢 LOW | Git | .gitignore duplicate node_modules rule (lines 67 + 132) | 2 | ✅ |
| F44 | 🟢 LOW | Config | system_config.yaml has version 4.5.8 (stale) | 2 | ✅ |
| F45 | 🟢 LOW | Tests | test_browser/, test_channels/, test_colony/ etc empty | 4 | ✅ |
| F46 | 🟢 LOW | Docs | Chart version claims "v15.2.0" in engine/audit.py | 3 | ✅ |
| F47 | 🟢 LOW | Docs | new_proposals.py claims "v4.5.3" | 3 | ✅ |

---

## 🧬 E:\ Integration — 12-Agent Council Plan (2026-07-31)

**136 jam / 4-6 minggu** — Port TradeBobbyTerminal + OrderFlowMap ke QNA pipeline.

| Phase | Hours | Deliverable |
|-------|-------|-------------|
| Phase 0 — Pre-work | 8h | Delete dead code, dedup signal/registry/COT |
| Phase 1 — Week 1 | 24h | 5 Python providers + pipeline wiring |
| Phase 2 — Week 2 | 32h | 9 dashboard panels + risk gates + evolution |
| Phase 3 — Week 3 | 40h | 80% tests + alerts + data quality |
| Phase 4 — Future | 32h | Node sidecars + multi-account + backtest |

Lihat `docs/Rencana.md` untuk detail lengkap.
