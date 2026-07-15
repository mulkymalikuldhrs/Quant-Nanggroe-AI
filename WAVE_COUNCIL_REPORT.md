# QNA v4.5.8 — 50-Agent Council Review (VERIFIED, both waves)

> Execution: 2 parallel swarms of leaf subagents (tencent/hy3:free), 50 total, ~32–35 min.
> Every finding below was produced by a subagent that READ the real source. A prior
> direct-execution draft was WRONG on 6 items (false negatives) — this version
> supersedes it. All severity-critical claims re-grep-confirmed by orchestrator.

## CRITICAL (fix before any live/external exposure)

### C1. #20 JWT secret is a published default → full admin auth bypass
`quant_nanggroe/config/settings.py:161` `jwt_secret="change-me-in-production"`.
`api/app.py:184` builds `JWTAuth(secret_key=settings.jwt_secret)`; the HMAC verify passes for any token signed with this constant. **Anyone forges `role:admin` and reaches `/api/credentials`, `/api/autonomous`, `/api/security`.**
→ fix: read from env only, refuse to boot if unset/known-default.

### C2. #9 MT5 "live" bridge is FAIL-OPEN (silent paper)
`engine_production_bridge.py:348-360` connects `self._mt5` under `QNA_MT5_LIVE=1`,
but `_execute_signal_inner` (`:385-389`) returns `self._paper.place_order(...)`
BEFORE `self._mt5` is ever referenced. `self._mt5` has 0 call sites in the exec path.
Operator believes live; every order stays paper. Connector itself is fail-closed — the
**wiring** is fail-open.
→ fix: route to `self._mt5` before paper when `QNA_MT5_LIVE==1`, demote paper to fallback + loud log.

### C3. #32 Credentials stored in plaintext on disk
`api/routes/credentials.py:36` `p.write_text(json.dumps(data,...))` → `config/credentials.json`
cleartext (apiKeys, brokers, exchanges, llmKeys). `KeyVault` exists but is never used here.
One file read =全部 keys exfiltrated.
→ fix: encrypt at rest (fernet) or route through env-backed KeyVault.

### C4. #27 Solana swaps have NO access control — unrestricted on-chain calls
`exchange/guards.py:454` `GuardPipeline` (the only whitelist/position-cap layer) has 0
imports outside its own module. `exchange/solana/broker.py:290` `place_order` only checks
wallet/jupiter connection, then `JupiterV6Client.execute_swap` signs with live keypair
(`jupiter.py:376`) and broadcasts `skip_preflight=True` (`:382`). Every trade = unrestricted.
→ fix: wire GuardPipeline into place_order; gate position size + whitelist.

### C5. #31 Kill-switch split-brain across processes
`engine/hermes_shared_state.py:62` `_restore_state()` only on `__init__`; `reconcile` = 0
repo-wide hits. `qna.py api` + `qna.py daemon` are separate processes sharing `hermes_quant.db`.
API flips kill-switch → worker's in-memory copy never refreshes → keeps trading. The one
safety state that MUST be globally authoritative isn't.
→ fix: single-writer DB row + version/fencing token re-read under lease; WAL + busy_timeout.

## HIGH

- **#50 (Skeptic) — "walk-forward-validated edge" is a no-op.** `def fit` appears **0 times** in `engine/strategy/strategies/`. KEEP strategies are stateless pure functions of `prices[..t]`+fixed params, so train/test folds are byte-identical → the "+3576% SOL OOS" numbers are **in-sample**, not OOS. `QNA_SIGNAL_MATURITY_PROOF.md` overclaims.
- **#2 Kill-switch blind to unrealized drawdown.** Only fires on realized PnL (`manager.py:243`→`update_pnl` at trade close). Open crash position → no cut. Feed mark-to-market equity into `DrawdownMonitor`.
- **#1 Default walk-forward path leaky.** `engine.py:451` `run_walk_forward`→`analyzer.analyze` backtests signals pre-computed over the WHOLE series, never re-fits per fold (its own docstring admits it). 10 micro strategies use safe `analyze_strategy`; the public default is leaky.
- **#3 Macro regime detector dead.** `engine/regime/ensemble.py:34-35` computes `detector_kwargs` then discards it, calls `predict(**kwargs)`. `MacroRegimeDetector.predict(gdp_growth,inflation)` gets price kwargs → `TypeError` swallowed by `except`. 0.20 weight contributes nothing.
- **#4 Options pricer uses flat σ=0.3, ignores calibrated VolSurface.** `options/strategies.py:206` `_evaluate(sigma=0.3)`; `engine/options/vol_surface.py` (SABR/bilinear) only feeds the cosmetic `/vol-surface` API. Wing-heavy strategy mispriced −24%.
- **#5 Lookahead in vol-scaled sizing.** `engine.py:159-163` computes `vol_by_symbol` over FULL sample outside the bar loop; used to scale leverage at every bar → knows future vol. Use trailing window.
- **#6 Risk-parity contradicts agent's own 10% cap.** `risk/risk_parity.py:93,139` hardcodes `max_weight=0.50`, clips+renormalizes; `agents/portfolio/prompts.py:13` says "Max 10%". Single asset can take 50%.
- **#10 Crisis correlation unhedged.** `hermes_risk_officer.py:174` static hardcoded groups; dynamic `StrategyCorrelationMonitor` (fires `CORRELATION_HERDING`) has 0 call sites; `KillSwitch.check_auto_activate` has no correlation input.
- **#11 Debate runs ~24 LLM calls, half discarded.** `graph.py:697` `_reflection_node` (always-on) + `:724` `_council_debate_node` both call `run_full_debate` (12 calls each); reflection keeps only `debate_state`, never the vote. Zero caching anywhere.
- **#12 Drift detection = dead code.** `MonitorHub`, `StrategyLifecycleManager` never instantiated/wired. No per-strategy PnL tracking → no baseline to drift against.
- **#15 Kill-switch persists to file → fragile-green tests.** `manager.py:523-526` re-activates from `risk:kill_switch_active` on every construction; one test poisons all later runs + future pytest (re-run → 3 failed).
- **#18 No cost routing — defaults to most expensive model.** `connectors/llm_gateway.py:162,190` selects `models[0]` (gpt-4) every time; fallback → openai/gpt-4. `quant_nanggroe/llm/jeumpa.py` is dead.
- **#30 MEV exposure on Solana swaps.** `jupiter.py:379-383` broadcasts to public mempool, `skip_preflight=True`, hardcoded `slippage_bps=50` (`broker.py:311`), no Jito bundle. Full sandwich risk.
- **#37 License breach — 71 files ported from 6 upstreams, notices dropped.** `engine/shadow/codegen.py:6` "Ported from Vibe-Trading/..." with no MIT/Apache notice; no NOTICE/THIRD-PARTY file. Also: RL `agents.py:285` PPO "update" is random weight noise (not backprop) — self-admitted.
- **#39 v4.5.8 "autonomous self-correction" is theater.** `engine_production_bridge.py:50,365` catches exception, appends to `data/qna_lessons.json`, re-raises. **0 readers** of that file (grep-confirmed). No recovery/retry/replan. Parallel orphan of existing `agentic/autonomous.py` lesson store.
- **#47 Staging≠prod env drift.** `deploy/docker/docker-compose.yml:9-11` injects `APP_ENV`/`DATABASE_URL` (unprefixed) — app only reads `QNAI_*` (`settings.py:55`). Docker stack falls back to sqlite + debug defaults, masquerading as production.

## MEDIUM (notable)

- **#7** Paper broker fills 100% (`paper_broker.py:537`) — no depth/liquidity check; overstates fill ~20% vs realistic partial-fill model.
- **#8** Dead constant feature `vol_ratio_5≡1.0` (`models/feature_store.py:99`); dup return/momentum features (`ml/feature_engineer.py:206` vs `:275`); no pruning.
- **#13** Geopolitics prompt bias — only `chinese_order.py:24-25` seeded with pejorative terms; other 4 personas neutral.
- **#14** `worker.py:177` `while self._running` — no retry cap/backoff; `graph.py:243` `compile()` no `recursion_limit`. Bonus: `self._running` read at `:115` but not initialized in `__init__` → first `start()` raises AttributeError.
- **#16** `data/providers/yahoo.py:101-119` `float(nan)` doesn't raise → NaN OHLCV passes silently (only `logger.debug`).
- **#17** Model weights have no signing/verify pathway (`model_registry.py:626`, `ml/model_manager.py:83` docstrings advertise save/load but unimplemented) → latent RCE when someone adds torch.load.
- **#19** `database/models.py:206` single import-time engine, default sqlite, no replica/failover, configured PG URL ignored.
- **#21** FK + hot-filter columns in `database/models.py` have no `index=True` → full table scan under load.
- **#22** `deploy/deploy.sh:183` warns but never rolls back; `alembic downgrade` 0 invocations.
- **#23** `dashboard/` imports `recharts` eagerly (3 routes, ~388KB each); `framer-motion`+`socket.io-client` in package.json but 0 imports.
- **#24** No API versioning (`app.py:242` mounts `/api/<res>` unversioned); `cli.py:406` already hits dead `/api/v1/portfolio` (404→silent fallback).
- **#26** `exchange/manager.py:659` serial per-exchange `get_portfolio()` awaits (should `asyncio.gather`); `backtest.py:142` `get_event_loop()` in coroutine.
- **#28** Solana swap books fill from quote, not on-chain result (`broker.py:334`); wrong execution price on revert.
- **#29** No QNAI tokenomics code exists (thesis unfounded).
- **#33** `backtest_master_results.md:75-78` labels combos `ROBUST(1.0)` with `OOS Trades=0` — false OOS validation; later audit brands same `1.0` junk.
- **#34** `nautilus_adapter.py:654` 910-line ABC hierarchy, `__init__` always raises ImportError, 0 callers — dead YAGNI.
- **#35** Dashboard landing CTAs are `alert()` stubs / hardcoded mock (`enhanced_index.html:503-531`); no onboarding/wizard; no docs link.
- **#36** `scripts/backtest_all.py:149` grades 106 strategies on only BTC-USD+EURUSD, then `pipeline.py` live-trades 6 symbols never sampled → no cross-asset/regime/fairness check.
- **#38** `competition_tool.py:406-455` A/B framework: no significance test, no CI, no min-sample guard (fields `winner`/`statistical_significance` dead).
- **#40** No retention loop — `whatsapp.py:227` subs in-memory dict (wiped on restart); `send_daily_brief()` 0 call sites; no user table; LLM cost unattributed.
- **#41** `llm_router.py:317` appends CostRecord but nothing reads it to halt; `get_cost_stats()` dead telemetry; no budget attribute.
- **#42** `whatsapp.py:242` stores full inbound msg (phone/name/body) verbatim, no consent/retention/PII redaction.
- **#43** `README.md:161` `cli.py system start` doesn't exist (entry = `qna.py daemon`); version stale (`v4.5.0` vs `v4.3.4`).
- **#44** `.github/no-response.yml` + `lock.yml` orphaned (no workflow references them); issue-helper gives 1 welcome comment, then nothing.
- **#45** Entire `quant_nanggroe/utils/` (363 LOC) 0 importers — orphan; `technical.py:4` falsely claims to wrap it.
- **#46** Duplicate dep declarations across pyproject extras (`torch` :62+:87, `openai`, `langgraph`…) — latent drift hazard.
- **#48** `docs/04_API.md` documents `/ws` (real `/api/ws/stream`), `/api/sec` (real `/api/sec/edgar`), dead `/api/compat`; health example wrong.
- **#49** `pyproject.toml:88` `gymnasium` declared, 0 imports (dead); `:55` `scikit-learn` redundant (supplied by hmmlearn). No lockfile → ran `pip-audit` on resolved graph: 0 CVEs.

## Severity tally
| | Count |
|---|---|
| CRITICAL | 5 (C1–C5) |
| HIGH | 15 |
| MEDIUM | 30 |
| N/A (scope void) | #29 |

## Top-10 actions (priority order)
1. **C1** JWT: env-only secret, refuse boot if default. (security, zero-cost)
2. **C5** Kill-switch: single-writer + reconcile across processes. (safety, core)
3. **C2** MT5 bridge: real-exec branch before paper. (truth of "live")
4. **C3** Credentials: encrypt at rest or env KeyVault. (secret safety)
5. **C4** Wire GuardPipeline into Solana place_order. (on-chain safety)
6. **#50/#1/#5** Fix WF leakage + vol lookahead; reframe maturity proof as in-sample. (honesty of edge claim)
7. **#39** Either wire qna_lessons.json into a real correction loop or delete it. (no theater)
8. **#11/#18/#41** LLM cost: cache + route + cap. (runway)
9. **#2/#10** Mark-to-market kill-switch + dynamic correlation monitor. (tail risk)
10. **#37** Add THIRD-PARTY/NOTICE; fix RL PPO or label experimental. (legal + truth)

## Self-evolution note
Delegation DID work (no 404) — my premature "direct execution" fallback was wrong and
produced 6 false negatives. Lesson logged: for hy3:free subagents, expect 30–35 min, do
NOT re-dispatch or fall back until async batch lands. Skill `dhaher-50-agent-council`
should state this latency explicitly.
