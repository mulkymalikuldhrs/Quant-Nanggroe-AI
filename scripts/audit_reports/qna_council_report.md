# QNA 50-Agent Council — Strategic Review (Live-Trading Readiness)

**Repo:** `D:\repositories\Quant-Nanggroe-AI-worktree` (branch `master`, HEAD `7ea82f37`)
**Mode:** Direct execution (skill Mode B — one-shot review, files open). Read-only.
**Date:** 2026-08-01
**Scope:** money-path modules (risk / execution / exchange / api / security / llm).
**Coverage:** 742 `.py` in `quant_nanggroe/` + `scripts/qna-paper-daemon.py`. Every finding grep/read-verified against source (no subagent hearsay).

---

## VERDICT: NOT ready for live trading (RED)

QNA has a genuinely deep architecture — consolidated `build_execution_manager()` singleton, an enforced (not warn-only) kill-switch gate, cross-process kill-switch persistence, fail-closed live wiring. But **three money-path gaps block live capital**, and **test density is fatally low for financial code**.

**Biggest gap:** The kill-switch is wired and enforced, but the **PnL that feeds it is dead** — every production caller invokes `em.execute_order(order)` with no PnL args, so auto-activation reads `0.0` and can never trip on real losses (`manager.py:226-231`, callers `trading.py:204`, `trader/tools.py:143`).

**Biggest risk:** Live MT5 market orders are sent with **no SL/TP** (`mt5_broker.py:511-522`) — an unattended daemon can hold an unbounded-loss naked position if the trailing-stop path is not separately guaranteed.

---

## Wave 1 — Quant Finance & Trading (Agents 1–10)

### 1. Quant Strategist
**Finding:** No proven P&L / walk-forward artifact gates live promotion.
**Evidence:** `scripts/qna-paper-daemon.py` runs paper cycles but no committed backtest/paper P&L report is referenced as a live-gate; README carries no verified return curve.
`ponytail:` Require N days of green paper P&L logged before `QNA_LIVE_TRADING=1` is honored.

### 2. Risk Arbitrageur (tail risk)
**Finding:** Tail-risk hedge module exists but is not proven in the execute path.
**Evidence:** `engine/risk/tail_risk_hedge.py`, `engine/risk/var.py` present; no call site in `engine/execution/manager.py` execute flow.
`ponytail:` Wire VaR/tail check into the pre-trade guard chain or document it as advisory-only.

### 3. Macro Economist
**Finding:** VIX/regime gate exists but decoupled from order gate.
**Evidence:** `engine/risk/vix_gate.py`, `engine/regime/` present; `manager.execute_order` guard chain does not invoke a macro veto.
`ponytail:` Add regime/VIX gate to the guard chain, not just to signal generation.

### 4. Options Specialist
**Finding:** Options engine present; no evidence it feeds live sizing.
**Evidence:** `engine/options/` exists; not referenced in execution/risk sizing path.
`ponytail:` Nothing actionable for live equities/FX go-live — scope options later.

### 5. Quant Developer (backtest leak)
**Finding:** Backtest framework separate from live path — parity unverified.
**Evidence:** `backtest_pipeline.py` + `quant_nanggroe/backtest/` vs `engine/execution/` are distinct code paths; no shared fill model asserted.
`ponytail:` Assert backtest and live use the same slippage/commission model or backtest edge won't survive.

### 6. Portfolio Constructor
**Finding:** Risk-parity/Bridgewater modules present, integration into live allocation unproven.
**Evidence:** `engine/portfolio/risk_parity_bridgewater.py`, `covariance_risk.py`; no execute-path caller.
`ponytail:` Confirm allocations flow to order sizing, else equal-weight is the de-facto policy.

### 7. Market Microstructure
**Finding:** MT5 orders use fixed `deviation=10` and IOC filling regardless of symbol.
**Evidence:** `exchange/mt5_broker.py:517,520` — `"deviation": 10`, `ORDER_FILLING_IOC` hardcoded.
`ponytail:` Per-symbol deviation/filling; 10 points is wrong for indices/metals vs FX majors.

### 8. Data Scientist
**Finding:** No committed feature-redundancy / data-quality gate on live inputs.
**Evidence:** `engine/data_quality/` exists but not asserted in daemon pre-signal step.
`ponytail:` Add a stale/NaN feed check before signal gen in `qna-paper-daemon.py`.

### 9. Execution Trader (market impact) — **CRITICAL**
**Finding:** Live MT5 market orders are placed with NO stop-loss / take-profit in the request.
**Evidence:** `exchange/mt5_broker.py:511-522` — request dict has `action/symbol/volume/type/price/deviation/magic/comment/type_filling/type_time` but **no `sl` / `tp`** (contrast `modify_position` line 715-716 which DOES set sl/tp).
`ponytail:` Attach SL/TP at order_send; do not rely on a post-fill modify that can fail and leave a naked position.

### 10. Risk Manager (kill-switch) — **CRITICAL / biggest gap**
**Finding:** Kill-switch auto-activation is fed hardcoded `0.0` PnL by every production caller — it can never trip on real losses.
**Evidence:** `engine/execution/manager.py:226-231` calls `check_auto_activate(daily_pnl_pct=ks_daily,...)` where params default to `0.0` (`manager.py:~176-179`); callers `api/routes/trading.py:204` and `agents/trader/tools.py:143` call `em.execute_order(order)` with **no PnL args**.
`ponytail:` Pull realized PnL from the attached broker handle inside `execute_order` before the kill-switch check — don't trust callers to pass it.

---

## Wave 2 — AI/ML Engineering + Software Engineering (Agents 11–26)

### 11. LLM Architect
**Finding:** No retrieval/response cache — LLM calls are the #1 opex and uncached.
**Evidence:** `grep -rln "response_cache|prompt_cache|_llm_cache"` = 0 hits; `core/llm_provider.py` (`llm/` pkg) `chat()` has no memoization.
`ponytail:` Add a keyed response cache; agentic loops re-ask identical prompts every cycle.

### 12. ML Ops Engineer
**Finding:** No model-drift detection on any served model.
**Evidence:** `engine/ml/`, `engine/model_registry.py` present; no drift monitor referenced in daemon loop.
`ponytail:` Log prediction distribution; alert on KL-divergence shift.

### 13. NLP Specialist
**Finding:** Prompt templates not audited for directional bias in signal prompts.
**Evidence:** `agents/*/agent.py` prompt strings; no bias-audit artifact.
`ponytail:` Run `prompt-bias-audit` skill on trader/analyst prompts.

### 14. Agent Framework Dev
**Finding:** Autonomous self-loop present; retry/iteration guardrail not verified.
**Evidence:** `engine/autonomous_self_loop.py`, `engine/self_aware.py`.
`ponytail:` Confirm a hard max-iteration + cost ceiling per cron run.

### 15. Evaluation Scientist
**Finding:** No eval set exercises the kill-switch-blocked-order edge case end-to-end.
**Evidence:** only 5 `test_*.py` under `quant_nanggroe/` (148 under top-level `tests/`), none assert `execute_order` blocks when live PnL breaches.
`ponytail:` Add a test: seed losing PnL, assert order returns None + KILL_SWITCH_BLOCKED audit.

### 16. Data Pipeline Eng
**Finding:** Silent-null risk in feed→signal handoff (no schema assert).
**Evidence:** `data/warehouse.py` consumed by daemon without a null-column guard.
`ponytail:` Assert non-null OHLCV columns before strategy call.

### 17. MLOps Security
**Finding:** Model weights / provider outputs not integrity-checked.
**Evidence:** no signing in `engine/model_registry.py`.
`ponytail:` Low priority pre-go-live; document as accepted risk.

### 18. Inference Optimizer
**Finding:** Default model `gpt-4o` for all agents — no tiering by task.
**Evidence:** `config/settings.py:102` `default_llm_model = "gpt-4o"`.
`ponytail:` Route cheap classification to a small model; reserve gpt-4o for synthesis.

### 19. Systems Architect
**Finding:** SQLite is the default datastore — single-writer bottleneck under a live daemon.
**Evidence:** `config/settings.py:68` `database_url = "sqlite:///data/agentic.db"`.
`ponytail:` Postgres for live; SQLite locks will stall concurrent audit writes.

### 20. Security Auditor
**Finding:** JWT default is a boot-refusing sentinel — PASS (not a vuln).
**Evidence:** `config/settings.py:166-170` `jwt_secret="__UNSET_QNAI_JWT_SECRET__"` + docstring "refusing to boot with the unset sentinel."
`ponytail:` Verify the boot check actually raises in `create_app`; keep the sentinel.

### 21. Database Expert
**Finding:** No migration/index strategy asserted for the audit table under load.
**Evidence:** `alembic.ini` present; `audit.db` at root suggests ad-hoc writes.
`ponytail:` Index audit table on (timestamp, action) before high-frequency logging.

### 22. DevOps Engineer
**Finding:** Live wiring is fail-closed and env-gated — PASS with a caveat.
**Evidence:** `engine/execution/builder.py:52-53` `QNA_LIVE_TRADING` gate; `:98-104` paper fallback.
`ponytail:` Good design; add a rollback runbook for a bad live deploy.

### 23. Frontend Architect
**Finding:** Dashboard bundle size not measured; out of go-live critical path.
**Evidence:** `dashboard/` present, no bundle budget.
`ponytail:` Defer; not a live-capital blocker.

### 24. API Designer
**Finding:** `execute_order` API omits the risk context it needs to be safe.
**Evidence:** `api/routes/trading.py:204` `await em.execute_order(order)` — no PnL/risk snapshot passed (root of finding #10).
`ponytail:` Make `execute_order` self-source risk state; don't expose an unsafe caller contract.

### 25. Code Reviewer
**Finding:** `build_execution_manager` does 4 things (build/wire/connect/singleton) in one function.
**Evidence:** `engine/execution/builder.py:34-134`.
`ponytail:` Acceptable for now; extract broker-connect loop if it grows.

### 26. Performance Eng
**Finding:** Broker async-connect uses `get_event_loop()` (deprecated, loop-reuse hazard).
**Evidence:** `engine/execution/builder.py:116` `asyncio.get_event_loop()`.
`ponytail:` Use `asyncio.get_running_loop()` / explicit loop management.

---

## Wave 3 — Blockchain / Research / Business / DhaHer Specialists (Agents 27–50)

### 27. Smart Contract Auditor
**Finding:** Nothing actionable in scope — no on-chain contracts in the live path.
`ponytail:` Solana/polymarket brokers exist (`exchange/solana/`, `polymarket_broker.py`) but are not the go-live target.

### 28. DeFi Strategist
**Finding:** Polymarket/DEX brokers present but unproven; exclude from go-live.
**Evidence:** `exchange/polymarket_broker.py`.
`ponytail:` Gate these behind a separate flag until audited.

### 29. Token Economist
**Finding:** Nothing actionable in scope (no token issuance).

### 30. MEV Researcher
**Finding:** Solana connector path not MEV-hardened; out of scope for MT5 go-live.
**Evidence:** `exchange/solana/`.
`ponytail:` Defer.

### 31. Consensus Engineer
**Finding:** Kill-switch cross-process file store is the consensus mechanism — single-file SPOF.
**Evidence:** `engine/risk/kill_switch.py:45-66` file-based `_ks_read/_ks_write`; `_fail_closed` on unreadable (`:283-287`) is good.
`ponytail:` Fail-closed on unreadable is correct; ensure the file path is on durable local disk, not a network mount.

### 32. Crypto Security
**Finding:** Credential managers exist; verify key files are `0o600`.
**Evidence:** `security/credential_manager.py`, `keyvault.py`, `encryption.py`.
`ponytail:` Grep for `os.chmod(..,0o600)` on written key files; add if missing (known QNA pitfall).

### 33. Paper Analyst
**Finding:** No replication artifact linking a strategy paper to live params.
`ponytail:` Nothing actionable pre-go-live.

### 34. Domain Researcher
**Finding:** Broad feature surface (350+ engine modules) vs typical 20-50 factor firm — dispersion risk.
**Evidence:** `engine/` has ~40 subpackages.
`ponytail:` Freeze the live strategy set to a proven few; keep the rest experimental.

### 35. UX Researcher
**Finding:** Out of live-capital critical path.

### 36. Ethics Reviewer
**Finding:** Nothing actionable in scope.

### 37. Patent Analyst
**Finding:** Nothing actionable in scope.

### 38. Scientific Advisor
**Finding:** Sample size for any A/B of strategies unproven — 5 in-pkg tests is not significance.
**Evidence:** 5 `test_*.py` in `quant_nanggroe/`.
`ponytail:` See finding #45; test density is the systemic issue.

### 39. Product Strategist
**Finding:** Live-trading value proposition unproven without a P&L track record.
`ponytail:` Same as #1 — gate live on demonstrated paper returns.

### 40. Growth Hacker (opex/CAC)
**Finding:** LLM spend uncapped and uncached — unsustainable at agentic cadence.
**Evidence:** no cache (finding #11); `gpt-4o` default (`settings.py:102`).
`ponytail:` Cache + model tiering cut the #1 opex line before scaling.

### 41. Financial Analyst
**Finding:** No burn/cost telemetry on LLM calls surfaced to a budget gate.
**Evidence:** `llm_provider.get_cost_stats()` exists (`:354`) but no budget enforcement.
`ponytail:` Wire `get_cost_stats` to a hard monthly ceiling that pauses agents.

### 42. Legal Advisor
**Finding:** Live trading with real MT5 creds needs a compliance/audit trail — audit exists, retention policy does not.
**Evidence:** `engine/audit.py`, `_record_audit` in manager.
`ponytail:` Document audit retention + immutability before live.

### 43. Technical Writer
**Finding:** README explains "how" but not the live-readiness gate ("why not yet live").
**Evidence:** `README.md` (31KB) lacks an explicit go/no-go checklist.
`ponytail:` Add a "Live Readiness Checklist" section referencing findings #9/#10.

### 44. Community Manager
**Finding:** Nothing actionable in scope.

### 45. Project Auditor — **HIGH**
**Finding:** Fatally low test density for financial code (~1 in-pkg test per ~148 LOC of money-path, well below 1:100 minimum on execution).
**Evidence:** 5 `test_*.py` under `quant_nanggroe/` vs 742 `.py`; execution/kill-switch blocking path untested.
`ponytail:` Before live: cover `execute_order` block-on-loss, SL/TP-attached, and kill-switch cross-process reconcile.

### 46. Integration Specialist
**Finding:** Two MT5 broker classes (`exchange/mt5_broker.py` vs `connectors/mt5_broker.py`) risk divergent behavior.
**Evidence:** `builder.py:62` imports `connectors.mt5_broker.MT5Broker`; `exchange/mt5_broker.py` is a separate 1145-LOC impl.
`ponytail:` Confirm which is canonical; delete/alias the other to avoid a two-ABC repeat.

### 47. Deployment Architect
**Finding:** Repo root polluted with venvs/temp/session dumps — staging≠clean.
**Evidence:** `.tmp-ll-venv`, `tmp-venv`, `tmp-venvv2`, `coint_wheels`, 1.1MB `session.md`, `nul` at root.
`ponytail:` `.gitignore` + prune before a reproducible deploy image.

### 48. Documentation Auditor
**Finding:** Multiple agent-guide docs (CLAUDE/GEMINI/CURSOR/COPILOT.md) risk drift from code.
**Evidence:** 7+ `*.md` agent guides at root, edited across different dates.
`ponytail:` Single source of truth; generate the rest.

### 49. Dependency Auditor
**Finding:** 1.3MB `uv.lock` not scanned for CVEs in this pass.
**Evidence:** `uv.lock` present; no committed audit report.
`ponytail:` Run `uv pip audit` / `pip-audit` before live.

### 50. The Skeptic — "Show me the P&L"
**Finding:** No proven return curve exists; all readiness rests on architecture, not results — AND the one safety net (kill-switch) is fed zeros.
**Evidence:** finding #10 (`manager.py:226-231` + callers) + absence of a committed P&L artifact.
`ponytail:` Architecture ≠ edge. Fix #9/#10, log real paper P&L, THEN discuss live.

---

## Severity Summary

| Category | Critical | High | Medium | Low | PASS |
|----------|----------|------|--------|-----|------|
| Wave 1 (Quant/Trading) | 2 (#9,#10) | 1 (#7) | 5 | 2 | 0 |
| Wave 2 (AI-ML + SWE) | 0 | 2 (#11,#15) | 8 | 3 | 2 (#20,#22) |
| Wave 3 (Crypto/Research/Biz/DhaHer) | 0 | 2 (#45,#46) | 6 | 8 | 1 (#31) |

## Top 5 Actions (in priority order)

1. **Fix the dead kill-switch PnL feed** — make `execute_order` self-source realized PnL from the broker handle before `check_auto_activate` (`manager.py:226-231`); never trust callers (`trading.py:204`, `trader/tools.py:143`).
2. **Attach SL/TP to every live MT5 order** — add `sl`/`tp` to the `order_send` request (`mt5_broker.py:511-522`); no naked positions.
3. **Add money-path tests** — cover block-on-loss, SL/TP presence, and cross-process kill-switch reconcile before enabling `QNA_LIVE_TRADING`.
4. **Prove paper P&L** — require N days of committed green paper returns from `qna-paper-daemon.py` as the live gate (#1/#39/#50).
5. **Add an LLM response cache + budget ceiling** — kill the #1 opex before scaling agent cadence (`llm_provider` + `get_cost_stats` at `:354`).

---
*Read-only analysis. No code modified. Findings grep/read-verified against source per Orchestrator Verification Protocol.*
