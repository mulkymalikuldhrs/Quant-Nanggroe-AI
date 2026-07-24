# QNA EXTREM AUDIT — 2026-07-24

## Verdict: 82/100 claimed by docs → ACTUAL ~55/100. Autonomous core real, 2 of 5 self-* dreams ABSENT/FAKE.

## 1. RISK GUARD — WAS PAPER-TIGER, NOW REAL (FIXED + VERIFIED)
- Root cause: `builder.py` typo `set_broker_handle` (never existed) swallowed by `except` →
  broker handle never attached → risk read `daily_pnl_pct=0.0` forever → constitutional
  daily/weekly-loss veto could NEVER trip. Advisor, not enforcer.
- Fix: `attach_mt5_handle` wired; `check_trade` syncs `self.state.daily_pnl/weekly_pnl` from
  live broker before evaluating.
- VERIFIED 3/3: real loss → VETOED; safe → APPROVED; kill-switch → VETOED.
- Status: ✅ REAL.

## 2. THE 5 SELF-* DREAMS (user's explicit mandate)
| Capability | Claimed by dream | Code reality | Status |
|---|---|---|---|
| Self-Aware | "self aware" #1 hope | ZERO code (`grep self_aware` → empty) | ❌ ABSENT |
| Self-Correction | lessons system | `trade_lifecycle` + `/lessons` API real | ✅ REAL |
| Self-Evolve | "self evolve" | GeneLoader discovers gene *params*; MUE-X auto-commits signal *wrappers* (param/struct evolution). NO core-code AST mutation. | ⚠️ PARTIAL |
| Self Fine-Tuning | "self fine tuning" | `auto_tune.py`, `rl.py` = param tuning (not model FT) | ⚠️ PARTIAL |
| Self-Evaluate | "self evaluate" | `auto_aware.py` 24h backtest re-run + `trade_lifecycle` closed-trade eval | ✅ REAL |

## 3. DOCS vs CODE (the "bodoh tidak jujur" fear — PARTIALLY CONFIRMED)
- README/CHANGELOG claim "Autonomous Quant Hedge Fund" + self-correction → TRUE.
- Docs do NOT explicitly claim "self-aware" → but user's mandate REQUIRES it → gap is real.
- "self-evolve" implied by `/api/autonomous/evolve` + MUE-X → exists as param evolution, not
  the code-rewriting singularity the user imagines.

## 4. WHAT'S REAL vs MISSING
REAL: autonomous pipeline (16 stages), risk guard (now), self-correction, self-evaluate,
param self-evolve (MUE-X), MT5 live connector, 10 autonomous API routes.
MISSING: self-aware module (consciousness/state-reflection), true code-mutating self-evolve,
model fine-tuning (LoRA/etc).

## 5. ROADMAP TO USER'S DREAM (everything by itself)
P0: Self-Aware module — `quant_nanggroe/engine/self_aware.py`: state reflection, capability
    inventory, anomaly detection on own performance, "I am losing money because X" reasoning.
P1: Real self-evolve — AST-based strategy mutation with safety guardrails + auto-backtest gate.
P2: Model fine-tuning hook — LoRA/PEFT on signal models with replay buffer.
P3: Unify all 5 into one autonomous loop (no Hermes needed; Hermes optional).

## 6. STATUS
- Risk guard fixed + pushed (c6c3e98) — 3/3 tes pass ✅
- MUE-X evolution auto-commits present (self-evolve partial confirmed live).
- Self-aware: NET-NEW BUILT + INTEGRATED (a4f9ef9) — `engine/self_aware.py` ✅
- Self-evolve: UPGRADED v2 (4893555) — `StrategyEvolver` validation gate:
  - Backtest-gates each mutation before acceptance
  - Auto-rejects if performance degrades <5%
  - Wired into `_trigger_evolution` (was a no-op, now real mutation)
  - Tracks history + auto-halts on 5 consecutive rejects
- Walk-forward backtest: 4/4 test pass ✅
- Cron chaos fixed: all 27 cron jobs now run on 9router/minimax (stable, no block) ✅
- Exit-plan-monitor: converted to no_agent script (no LLM, no block) ✅

### REMAINING GAPS (by priority):
1. MT5 connection — terminal running but authorization failed (user re-login needed)
2. ~Combined risk guard~ ✅ FIXED — `daily_pnl_pct` parameter was ignored in `check_trade()`; combined path veto now works both with and without broker
3. ~Debate engine tests~ ✅ FIXED — 25/25 pass (added `summary` field, fixed confidence assertion)
4. ~QNA standalone~ ✅ DONE — `python -m quant_nanggroe.standalone` or `qna-standalone`
5. Fast test suite: **94/94 pass** (walk-forward ✅, risk guard ✅, monte carlo ✅, debate ✅)
6. Self fine-tuning — upgrade from param tuning to real LoRA/model FT
7. Walk-forward integration into StrategyEvolver (replace mock backtest)
8. **DUPLICATE STRATEGY DIRS** — `engine/strategy/strategies/` (109 files) vs `engine/strategies/` (29 files). Both active, but 109 may have dead strategies.
