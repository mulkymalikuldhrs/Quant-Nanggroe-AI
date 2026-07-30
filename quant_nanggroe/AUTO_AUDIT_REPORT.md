# QNA Autonomous Engineering Audit Report v2.0
## TL;DR
85% wired; critical gaps: MT5 symbol disabled, missing signal_vote, cron-doctor safety failure.

## Critical Blockers
1. MT5 trade_mode=4 (DISABLED) blocks ALL orders — modify order_send_auto_sltp to block on 0 or 4.
2. Missing signal_vote import — remove import; aggregate() works.
3. Path conflicts causing false positives — verify file:line via grep before reporting.
4. Cron-doctor auto-reverts models — update prompt to be read-only.
5. Fail-closed guardrail degraded — ensure all risk limits VETO execution.

## Top 5 Actions (Imperative, One Line Each)
1. Fix MT5 trade mode check — block all orders when trade_mode in (0,4).
2. Remove dead import — delete signal_vote line from hedge_fund_mtf.py.
3. Enforce file:line verification in council findings — grep first.
4. Harden cron-doctor prompt to "DO NOT modify any cron job settings".
5. Activate fail-closed guardrails — ensure all risk limits VETO execution.

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