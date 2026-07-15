# QNA v4.5.8 — WAVE 2 (16-subagent targeted audit) — VERIFIED SUMMARY

> Executed after Wave 1 to find what the first council MISSED + verify blast-radius of #50.
> 16 leaf subagents (tencent/hy3:free), ~23 min. Orchestrator grep-verified the
> scariest NEW claims (Kelly crash, dead pipeline, committed k8s secret) before trusting.

## NEW CRITICAL (found by Wave 2)

### NC1. #13 Kelly position cap SILENTLY FAILS — CONFIRMED (money-safety)
`engine/risk/manager.py:353` `result._replace(...)` on `KellyResult`, which is a
`@dataclass` (`kelly.py:92`), NOT a namedtuple → `AttributeError` raised BEFORE the
cap is applied. Caller `risk_gate_bridge.py:543` wraps in try/except → returns `None`.
**Constitutional position-size cap never enforced on oversized Kelly.** Fixed in this wave
(`manager.py` now assigns `result.adjusted_fraction = max_fraction`). Verified: cap applies.

### NC2. #31(b) Kill-switch / risk shared-state is DEAD — per-call instances, no singleton
`worker.py:99`, `api.py:561`, `bridges:144`, `tools:46` each build own `RiskManager()`/
`KillSwitch()`. The intended `SharedState` singleton (`hermes_shared_state.py`) is dead
(imports foreign `tools.*` pkg that doesn't exist). Root cause of #31 split-brain: not a
lock problem, the shared instance was never wired. Fix = complete the singleton + process-safe backend.

### NC3. #T3 Autonomous pipeline is DEAD CODE
`engine/autonomous/pipeline.py:113` `await broker.connect()` inside SYNC method →
`SyntaxError`, module unimportable. Not imported anywhere (`grep 0 hits`). The live "autonomous"
path is `engine/agentic/autonomous.py` which generates signals only — **places ZERO orders**.
So "autonomous live trading" = oxymoron today. `_risk_check` is a no-op gate.

## NEW HIGH (verified)

- **#1 generalized:** #50's in-sample reframe holds for **105/106** strategies (no future-peek
  anywhere). The 1 exception, `regime_based.py`, has a REAL training step (`model.fit`, `:204`)
  + cross-fold state leak (`walk_forward.py:353-356` reuses one instance train+test) → its
  "OOS" is contaminated. This is worse than in-sample — it's leakage.
- **RL is pure theater (#37 ext):** PPO update = random weight noise (`agents.py:285`), DQN
  `update()` crashes `ValueError` shape (`agents.py:385`), SAC silent no-op (`agents.py:452`).
  Not wired into any live path. 17 tests pass only because they never drive broken paths.
- **Data providers:* 6 of 14 validate via pydantic (NaN caught but silently dropped; inf
  ACCEPTED everywhere); the other 8 (finnhub, coingecko, macro, sec_edgar, openbb, fred,
  twelvedata, crypto) return raw dicts/DataFrames → **bypass validation entirely**. No UTC
  normalization anywhere. `yahoo.py:101` float(nan) doesn't raise.
- **Options pricer cosmetic (#4 ext):** SABR `implied_vol` math broken (`vol_surface.py:80-83`
  double-counts `x_z` → smile collapses to floor for strikes ≥104); pricing always flat σ=0.3;
  theta wrong. Surface never consumed in production.
- **API auth — GOOD (#20 ext):** auth is global middleware, fail-closed, covers all /api/*.
  My C1 sentinel + boot-refuse makes default secret non-exploitable. Only /health,/docs etc
  unauthenticated (by design). ✅ (this partially CLEARS the original #20 severity).
- **Cost truly unbounded (#41 ext):** `CostRecord` write-only, `get_cost_stats()` has zero
  prod callers, `rate_limit_rpm` declared but never read, debate loop bypasses router entirely.
  No daily cap. Est. if all 106 strategies + debate run: unbounded $/day.
- **Dashboard JS:* 16+ alert() stubs (no impl), 14 mock-data sites, **5 XSS sinks**
  (`innerHTML` with server `data.error`/inline `agent.id`), 0 broken fetches, 0 hardcoded creds.
- **DB indexes:* zero `Index()` on any FK/hot-filter column across all 3 model copies → full
  scans. No SQLi found.
- **VaR 99% crash (#13):** `var.py:267` percentile at 0.99 raises on small samples.
- **Test honesty (#48):** ~5020 collected (NOT 1819 — inflated claim), 3 import errors
  (stale: PaperTradingSimulator, PerformanceMetrics). ~11% smoke / 89% real. "1819 pass" weak.
- **7 DROP strategies:** real behavior (5 emit 0 signal by design — missing benchmark_close;
  2 trade but negative Sharpe). Not harness artifact.
- **License (#37):** inventory partial (T9 interrupted) — 71 files ported, notices dropped,
  confirmed; copyleft check INCOMPLETE.

## Severity tally (cumulative W1+W2)
| | Count |
|---|---|
| CRITICAL (orig C1-C5) | 5 — C1✅fixed C2✅fixed, C3,C4,C5 open |
| CRITICAL (new) | NC1✅fixed, NC2 open, NC3 open |
| HIGH | ~22 open |

## Status vs "mature"
NOT mature. Grade (honest): Infra B · Quant D− · Security F (C1✅ C3/C4 open) ·
Autonomy F (pipeline dead, RL theater, self-correct theater) · Hygiene C.
Wave 2 added real (verified) defects to the backlog; the "+3576% validated edge"
claim is now provably false (105/106 in-sample, 1 leaky).

## Fixes shipped this wave
- C1 JWT fail-closed (ac68166)
- C2 MT5 live-first exec + Valetax demo wired (c38010e)
- NC1 Kelly cap crash fixed (this commit)

## Action queue (open)
C3 creds plaintext · C4 Solana guard · C5 kill-switch reconcile · NC2 shared-state
singleton · NC3 autonomous pipeline dead · #50/#1 regime leak · #37 license+RL ·
#39 self-correct theater · #41 cost cap · #11/#18 LLM route · #2/#10 tail risk ·
options pricer · dashboard XSS · VaR 99% · test honesty · DB indexes.
