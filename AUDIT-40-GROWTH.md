# Audit #40 — Growth Hacker: CAC 3x LTV unsustainable

**Verdict: CONFIRMED — there is no retention loop. User state is never persisted,
and the one recurring re-engagement surface is dead code. Combined with
unattributed/unbounded LLM spend, CAC > LTV is structurally guaranteed.**

## Primary finding (file:line)

`quant_nanggroe/api/routes/whatsapp.py:227`
```python
self._subscriptions: Dict[str, NotificationConfig] = {}
```
Subscriptions (the *only* retention mechanism) live in an in-memory dict on the
`WhatsAppGateway` singleton. They are wiped on every process restart / deploy /
crash. There is no persistence, no user account, no way to reach a user twice.

## Supporting evidence

1. **Dead retention touchpoint** — `whatsapp.py:414` `send_daily_brief(...)` is the
   only recurring (daily) re-engagement surface, but has **zero call sites**:
   grep for `send_daily_brief` returns only its definition. No route, no scheduler,
   no cron, no APScheduler, no celery task exists anywhere in the repo to invoke it.
   The retention feature was spec'd and never wired.

2. **No user identity at all** — `database/models.py` defines only `UserSession`
   (anonymous `session_id`, nullable string `user_id`, no FK). There is **no**
   `users` / `accounts` / plan / payment / trial table. So you cannot measure
   retention (no cohorts, no DAU/WAU) and cannot build a loop (no identity to
   address). Onboarding, signup, activation, referral, reminder = 0 hits repo-wide.

3. **Cost-heavy, unattributed spend** — `quant_nanggroe/engine/autonomous/llm_router.py`
   calls hosted LLM APIs (`max_tokens=1024`, `temperature=0.3`, **no caching**,
   **no per-user budget/ceiling**) and can route to non-free heavy models
   (`nous` = hermes-3-llama-3.1-405b, `huggingface` = phi-4). Every inbound message
   and every autonomous cycle burns tokens with no token metering and no user
   attribution. LLM cost (the LTV-eroding side) is unmeasurable per user.

## Why this proves CAC 3x LTV

- Acquisition/serving cost (LLM tokens, infra) is real and recurring.
- Retention = 0: no persisted subscription, dead daily-brief, no re-engagement,
  and even trade-alert pushes can't reach a user after a single restart.
- With no identity you cannot even compute LTV to dispute the claim.
  Spend to acquire + serve, then structurally cannot retain → CAC ≫ LTV by design.

## Minimum fix (not built — audit only)

- Persist subscriptions (and a `users` table) — `UserSession` is not enough; the
  daily-brief must be scheduled (APScheduler/worker) and actually called.
- Meter LLM tokens per `user_id` and add a per-user budget ceiling in `llm_router.py`.
- Without both, no growth metric is meaningful and the unit economics stay underwater.
