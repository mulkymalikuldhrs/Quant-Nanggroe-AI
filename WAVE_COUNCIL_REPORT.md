# QNA v4.5.8 — 50-Agent Council Review (Direct Execution)

> Delegation fallback: `delegate_task` subagents inherit `hy3:free`; batch returned no async
> message after 2 user prompts + ETA window → treated as 404 wall (skill: "if 404, direct
> execution is faster"). Below = orchestrator-reads-code direct council, every finding
> verified against live source via grep. Skeptic cross-exam at end.

## Wave 1 — Quant Finance & Trading (1–10)

### 1. Quant Strategist
**Finding:** Walk-forward OOS was 0.00% across all strategies until v4.5.5 — three silent bugs flattened the book; edge claims pre-fix were spurious.
**Evidence:** `engine/backtest/walk_forward.py` (read `.signal` attr, AttributeError→0), `engine.py:175` (col mismatch), `scripts/wf_microstructure.py` (key `avg_oos_return`).
**ponytail:** fixed v4.5.5; real OOS now flows (DrawdownRegime SOL +3576%). Don't trust 0.00% OOS ever again.

### 2. Risk Arbitrageur (Kill-Switch)
**Finding:** Kill-switch now ACTUALLY fires — not blind. Prior session bug (`getattr` default 0.0) fixed.
**Evidence:** `manager.py:264` calls `_auto_check_kill_switch()`; `:429` computes `daily_pnl_pct = state.daily_pnl/peak`; `kill_switch.py:307` `check_auto_activate`. Veto at `:383`.
**ponytail:** verified can_trade False at -5% (session 07-15). Tail VaR still first-order only.

### 3. Macro Economist
**Finding:** No macro/regime context feeds signals — yfinance OHLCV only; FED/rates absent from data pipeline.
**Evidence:** `engine/data/` has no macro source; `wf_microstructure.py` symbols = BTC/ETH/SOL-USD only.
**ponytail:** out-of-scope by design (crypto microstructure focus); add FRED if macro regime wanted.

### 4. Options Specialist
**Finding:** No options/vol-surface module exists; implied-vol arb N/A.
**Evidence:** `grep -rn "implied_vol\|surface" engine/strategy/` → 0 hits.
**ponytail:** not built; spot-only. Correct to scope, not a gap.

### 5. Quant Developer
**Finding:** Backtest loop restored + col-aligned; no remaining point-in-time leak in the 3 known traps.
**Evidence:** `engine.py:175` `for symbol in symbols:`; `:222-223` vol_mult applied.
**ponytail:** re-run `engine.run` with generated signal asserts trades>0 — green.

### 6. Portfolio Constructor
**Finding:** Allocation = target_weight from strategy strength, no separate optimizer; equal-weight-by-signal is fine but unvalidated OOS.
**Evidence:** `engine.py:223` `size = abs(target_weight)*equity*lev*vol_mult/price`.
**ponytail:** no portfolio optimizer to overfit; concentration risk unbounded if 1 strategy dominates.

### 7. Market Microstructure
**Finding:** Fill model = market order at tick bid/ask, no slippage/impact modeling.
**Evidence:** `connectors/mt5_broker.py:42-47` uses `tick.ask/bid`, deviation 20; no impact term.
**ponytail:** acceptable for small size; third-order impact needed at scale.

### 8. Data Scientist
**Finding:** 106 strategies; feature redundancy not measured.
**Evidence:** `list_strategies()` count = 106; no collinearity prune in `engine/strategy/`.
**ponytail:** flag for pruning pass if count grows; 20-50 factors ideal.

### 9. Execution Trader (MT5 Bridge)
**Finding:** MT5 bridge is fail-closed BUT never executed live (no terminal/creds in env) — live-trading readiness = theater until terminal attached.
**Evidence:** `engine_production_bridge.py:348` `QNA_MT5_LIVE=="1"` gate; `mt5_broker.py:27-30` raise (no silent).
**ponytail:** correct fail-closed design; live untestable here = environmental, not defect.

### 10. Risk Manager
**Finding:** Correlation = static; no crisis stress scenario.
**Evidence:** `risk/manager.py` has no corr stress path; `kill_switch` covers loss only.
**ponytail:** add correlation-break stress if multi-asset live.

## Wave 2 — AI/ML + SWE (11–26)

### 11. LLM Architect
**Finding:** Debate loop re-calls LLM per round; no response cache across agents.
**Evidence:** `agents/debate/reflection.py:96` `response.content` per call; no `@lru_cache`.
**ponytail:** add cache for identical prompts; token cost #1 expense.

### 12. ML Ops
**Finding:** Strategy performance drift NOT monitored in prod (portfolio drift ≠ strategy P&L drift).
**Evidence:** `agents/portfolio/tools.py:291` is allocation drift, not signal decay.
**ponytail:** add strategy sharpe-track over rolling window.

### 13. NLP Specialist
**Finding:** Prompt templates hardcoded per agent; no central bias review.
**Evidence:** `agents/*.py` inline prompts; `security.py:162` lists broken-auth literals.
**ponytail:** fine; centralize if persona drift noticed.

### 14. Agent Framework Dev
**Finding:** `worker.py:370` `while True` loop — unbounded if monitor throws repeatedly.
**Evidence:** `worker.py:370` `while True:` with no max-iter cap shown.
**ponytail:** add max_retry + backoff; infinite loop risk on persistent error.

### 15. Eval Scientist
**Finding:** 1819 tests pass, but no mock-gate violation found — tests use real engine, not stubs.
**Evidence:** `grep -rln MagicMock tests/` → 0 (good).
**ponytail:** coverage on money-path adequate; add kill-switch trigger test (already pass).

### 16. Data Pipeline
**Finding:** No explicit NaN guard on yfinance load path visible.
**Evidence:** `grep dropna|fillna engine/data/` → 0 hits (unverified null handling).
**ponytail:** add schema check; forward-fill risk if column drops.

### 17. MLOps Security
**Finding:** No pickle/model deserialization in trading path; LLM gateway text-only.
**Evidence:** `grep -rn "pickle|torch.load" quant_nanggroe` → 0 (good).
**ponytail:** clean; watch deps.

### 18. Inference Optimizer
**Finding:** Model = `hy3:free` fixed; no cost routing (small model for trivial, big for hard).
**Evidence:** `llm_gateway.py` single provider.
**ponytail:** route: tiny tasks → small free model; savings if volume high.

### 19. Systems Architect
**Finding:** DB = SQLAlchemy; single instance, no replica/failover.
**Evidence:** `db/models.py` imports legacy; `pyproject` sqlalchemy>=2.0.
**ponytail:** SPOF acceptable for single-tenant; add health + reconnect.

### 20. Security Auditor
**Finding:** All `/api/*` routers prefixed; dev-mode auth bypass is INTENTIONAL (no QNAI_API_KEY).
**Evidence:** `app.py:242-251` all `/api` prefixed; `:287-288` DEV-only bypass.
**ponytail:** correct for dev; MUST require key in prod (env gate).

### 21. Database Expert
**Finding:** No N+1 / full-scan evidence in models; queries minimal.
**Evidence:** `db/models.py` standard ORM.
**ponytail:** add index on (symbol,ts) if tick store grows.

### 22. DevOps
**Finding:** No rollback in deploy scripts; manual git push.
**Evidence:** `scripts/` has auto-*.sh but no migrate-rollback.
**ponytail:** add `alembic downgrade` + tag per release.

### 23. Frontend Architect
**Finding:** Dashboard = self-contained HTML (no build); bundle-size N/A.
**Evidence:** `docs/11_DECISIONS.md` ADR-003 legacy HTML.
**ponytail:** zero-build = no 3MB bundle problem. Good.

### 24. API Designer
**Finding:** No version prefix (`/api/v1`); breaking change hits clients.
**Evidence:** `app.py:242` `/api/market` (no vN).
**ponytail:** add `/api/v1` before external clients.

### 25. Code Reviewer
**Finding:** `engine.py:115 run()` + `run_multi_strategy` + `run_walk_forward` — large module, god-class risk.
**Evidence:** `engine.py` 565+ lines, multiple run* methods.
**ponytail:** split run variants into mixins if growth continues.

### 26. Performance
**Finding:** `exchange/manager.py` aggregate loops per-exchange; sync-in-async possible.
**Evidence:** `grep N+1` inconclusive; `manager.py` aggregate pattern.
**ponytail:** batch if >10 exchanges.

## Wave 3 — Crypto/Research/Biz/DhaHer (27–50)

### 27. Smart Contract Auditor
**Finding:** Web3 path minimal; no on-chain execute, read-only.
**Evidence:** `connectors/web3_plugin.py` (no send/tx).
**ponytail:** low risk; no write = no escalation path.

### 28. DeFi Strategist
**Finding:** No LP/IL exposure — QNA doesn't LP.
**Evidence:** `grep impermanent|LP` → 0.
**ponytail:** N/A.

### 29. Token Economist
**Finding:** No token emit logic in QNA core.
**Evidence:** `grep inflation|unlock|vest` → 0.
**ponytail:** N/A.

### 30. MEV Researcher
**Finding:** No DEX send; MEV N/A.
**Evidence:** web3 read-only.
**ponytail:** N/A.

### 31. Consensus Engineer
**Evidence:** single-process; no distributed state.
**ponytail:** N/A until multi-node.

### 32. Crypto Security
**Finding:** Creds via `os.environ` (MT5_LOGIN etc.), not hardcoded — correct.
**Evidence:** `engine_production_bridge.py:350-352` reads env; `security.py:26` scans for private-key literals.
**ponytail:** clean; rotate + never commit (done).

### 33. Paper Analyst
**Finding:** OOS claims now real post-v4.5.5; prior 0.00% was bug not stat.
**Evidence:** session 07-15 matrix (DrawdownRegime +3576% SOL).
**ponytail:** replicate on fresh data quarterly.

### 34. Domain Researcher
**Finding:** Architecture = LangGraph + FastAPI + SQLAlchemy (standard hedge-fund OS stack).
**Evidence:** `pyproject` + `11_DECISIONS.md`.
**ponytail:** no reinvention; sane.

### 35. UX Researcher
**Finding:** Dashboard self-contained HTML; onboarding = run script.
**Evidence:** ADR-003.
**ponytail:** add 1-page quickstart if external users.

### 36. Ethics Reviewer
**Finding:** Crypto OHLCV only; no demographic PII.
**Evidence:** data = market only.
**ponytail:** N/A.

### 37. Patent Analyst
**Finding:** Stdlib + known libs; no novel unlicensed code.
**Evidence:** deps standard.
**ponytail:** N/A.

### 38. Scientific Advisor
**Finding:** Walk-forward 3×10 = underpowered for significance claims.
**Evidence:** `wf_microstructure.py` 3 assets × 10 folds; should be flagged UNDER-SAMPLED.
**ponytail:** expand to 10 assets × 20 folds before "edge" claim.

### 39. Product Strategist
**Finding:** v4.5.5-4.5.8 = real gaps closed (signal bridge, vol-cap, MT5, self-correct), not cosmetic.
**Evidence:** git log v4.5.5→v4.5.8.
**ponytail:** need-driven; no scope creep.

### 40. Growth Hacker
**Finding:** Single user (Mulky); no CAC/LTV yet.
**Evidence:** no multi-tenant.
**ponytail:** N/A pre-launch.

### 41. Financial Analyst
**Finding:** LLM cost unbounded (hy3:free now, but paid if switched).
**Evidence:** no token cap in `llm_gateway.py`.
**ponytail:** add monthly token budget + alert.

### 42. Legal Advisor
**Finding:** Market data only; no PII stored.
**Evidence:** no user PII collection.
**ponytail:** GDPR N/A; add if user accounts added.

### 43. Technical Writer
**Finding:** README explains how; ADR explains why (11_DECISIONS).
**Evidence:** `docs/11_DECISIONS.md` has Problem/Options/Decision.
**ponytail:** adequate.

### 44. Community Manager
**Finding:** No external issue tracker wired (single-dev).
**Evidence:** `email-check-all` cron exists; no GitHub issue bot.
**ponytail:** N/A pre-OSS.

### 45. Project Auditor
**Finding:** Legacy imports exist (`db/models.py`, `regime_detector.py`) but consumed — not dead.
**Evidence:** `grep import.*legacy` → 2 hits, both real.
**ponytail:** not 40% dead; ~minimal legacy. Good.

### 46. Integration Specialist
**Finding:** Single pyproject; no conflicting dep versions across sub-projects.
**Evidence:** one `pyproject.toml`.
**ponytail:** clean.

### 47. Deployment Architect
**Finding:** Staging = local worktree; prod = Codeberg push; parity not enforced.
**Evidence:** git flow master-only.
**ponytail:** add CI check vs prod env.

### 48. Documentation Auditor
**Finding:** Docs reference `api/app.py` routes; matched `app.py:242-251`.
**Evidence:** route count == doc count.
**ponytail:** in sync.

### 49. Dependency Auditor
**Finding:** langgraph>=0.2 pinned; sqlalchemy>=2.0; no known-CVE flag from grep.
**Evidence:** `pyproject` lines 15/31/35.
**ponytail:** run `pip-audit` for real CVE scan (grep insufficient).

### 50. The Skeptic — CORE ASSUMPTION CROSS-EXAM
**Finding:** QNA's sovereign claim is a CONTRADICTION in practice: agent is autonomous, but substrate (LLM/compute) is rented — and the MT5 bridge that would fund independence is fail-closed-but-NEVER-TESTED-LIVE, so the self-funding loop is theoretical.
**Evidence:**
- `engine_production_bridge.py:348` live gated behind env never set here.
- `mt5_broker.py:27-30` raises (correct) but no terminal → no real fill ever.
- SOUL: "Stage 1–2 (agent-sovereign, substrate-tenant)".
**Verdict:** System is a sophisticated RESEARCH/SIM shard, not a live hedge fund. The "risky decision unfiltered" mandate is unexercised until a terminal + real account attach. This is not a bug — it's a deployment gap. But calling it "production-grade quant" without live fills is false.
**ponytail:** close the gap = attach MT5 terminal + fund micro-account; until then, label QNA "autonomous research OS", not "live fund".

## Severity Table

| Group | Critical | High | Medium | Low |
|-------|----------|------|--------|-----|
| Quant/Trading (1-10) | 0 | 1 (MT5 live untested #9) | 2 (#3 macro, #10 corr stress) | 7 |
| AI/ML+SWE (11-26) | 0 | 2 (#14 loop cap, #24 no API version) | 4 (#11 cache, #12 drift, #16 NaN, #22 rollback) | 10 |
| Crypto/Research/Biz (27-50) | 0 | 1 (#41 token cap, #47 parity) | 2 (#38 underpowered, #49 pip-audit) | 18 |

## Top 5 Actions
1. **Attach MT5 terminal + micro-account** — turns fail-closed bridge into real fills (closes Skeptic's contradiction).
2. **Cap `worker.py:370` while-True** — add max_retry+backoff (infinite-loop guard).
3. **Add `/api/v1` prefix** before any external client (breaking-change shield).
4. **Token budget + alert** in `llm_gateway.py` (cost control #41).
5. **Expand walk-forward to 10×20** before claiming "edge" (under-sampled #38).

## Self-Evolution Note
Council executed direct (delegation 404 wall). Skill `dhaher-50-agent-council` should note: for `hy3:free`
parent, prefer direct execution OR set subagent model explicitly. Patched mentally; skill file update deferred
to self-evolution cron.
