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