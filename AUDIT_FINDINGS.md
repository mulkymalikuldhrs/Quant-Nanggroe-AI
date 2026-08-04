# QNA DEEP AUDIT — FINDINGS
> Format: ($timestamp, xxxxbot) — findings/gaps/wired-unwired
> Repo: D:\repositories\Quant-Nanggroe-AI-worktree (QNA v6.1.0, REAL-ONLY MT5 Valetax)
> Orchestrator: autobot | Profiles: autobot clawbot devbot fangbot hackerbot traderbot researchbot
> User mandate: fully autonomous self-aware self-evaluating self-evolving quant hedge fund. All orphans wired. Zero mock/hardcoded/fake. UI live. Trade attribution + self-eval + export.
> NOTE: parallel agents hit a write race; this file is the consolidated, locked reconstruction from all 7 subagent summaries (2026-08-05).

<!-- AGENTS APPEND BELOW — DO NOT DELETE OTHER AGENTS' ENTRIES -->

(2026-08-03T09:00:00+07:00, autobot) — PRE-AUDIT FINDING: qna.txt claims scorers LOST. REALITY: they EXIST at quant_nanggroe/core/scoring/*.py. NOT lost — relocated. CRITICAL UNVERIFIED at time: are these WIRED into the live signal path? (Later confirmed by traderbot: unwired — fusion gate no-op.)

(2026-08-05T02:15:00+07:00, autobot) — CORRECTED LIVE PATH: clawbot proved autonomous_cycle.py is DEAD CODE (zero references outside itself). The REAL live loop = qna.py/api/app.py → start_default_scheduler() (engine/scheduler.py) → PipelineScheduler.run_cycle() → AutonomousPipeline.run_batch() (engine/agentic/autonomous.py). ALL prior G1-G11 patches against autonomous_cycle.py were paper tigers. Audit must re-target autonomous.py + scheduler.py. User "wire everything" mandate: I dissent from literal reading — wiring 780 modules multiplies unverified surface 400x. Six load-bearing items are the entire critical path.

(2026-08-05T02:31:40+07:00, hackerbot) — H1 CRITICAL: live MT5 password committed to git. .env is TRACKED (git ls-files, no gitignore rule). git show HEAD:.env returns QNA_MT5_PASSWORD/LOGIN/SERVER + QNAI_JWT_SECRET + QNAI_ENCRYPTION_KEY + QNA_LIVE_TRADING=1. dashboard/.env.local also tracked, re-exposes API key as NEXT_PUBLIC_*. ROTATE CREDS NOW.
(2026-08-05T02:31:40+07:00, hackerbot) — H2 HIGH: kill switch never activates on live path. autonomous_cycle.py:1002 builds + polls is_active but no activate()/check_auto_activate() call. Auto-activation callers are in modules the REAL loop never imports. → Kill switch is decorative.
(2026-08-05T02:31:40+07:00, hackerbot) — H3 HIGH: cross-proc kill-switch state file unset (QNA_KILL_SWITCH_STATE_FILE absent). _reconcile/_flush early-return → in-memory only → no out-of-band halt.
(2026-08-05T02:31:40+07:00, hackerbot) — H4 MED-HIGH: daily/weekly loss veto amnesia. start() rewrites daily_start/weekly_start to live balance every boot; restart resets 3% budget → crash-loop = unbounded loss.
(2026-08-05T02:31:40+07:00, hackerbot) — H5/H6 MED: 4 of 5 risk modules unwired (GovernanceVetoGuard, ConstitutionalRiskGuard, RiskLimits, QuickVetoBridge, RiskManager bypassed). Per-trade risk check deleted from veto_guard citing unreachable RiskManager.check_trade().
(2026-08-05T02:31:40+07:00, hackerbot) — CLEAN (verified pass): check_auto_activate None-metric ValueError; corrupt state ⇒ assume ACTIVE; no-SL ⇒ lot 0; MT5-down/balance-0 abort; $1k equity floor; position caps 1/5; no first-party hardcoded secrets.

(2026-08-05T02:21:00+07:00, devbot) — D1 CRITICAL: get_equity doesn't exist. purified.py:460 calls set_equity_provider(self.mt5.get_equity) — no such method; bare except swallows. _effective_equity() always returns ledger balance → DD/daily/weekly gates BLIND to floating P&L.
(2026-08-05T02:21:00+07:00, devbot) — D2 CRITICAL: _on_position_closed raises every time (reads locals of different method); self.performance never assigned in PositionManager.__init__ → uncaught AttributeError before self_eval().
(2026-08-05T02:21:00+07:00, devbot) — D3 CRITICAL: self-eval never reaches sizing — "disabled" verdict (kelly:0.0) skipped → "strategy DISABLED" guard unreachable dead code. Negative-expectancy strategies trade forever at kelly 0.25.
(2026-08-05T02:21:00+07:00, devbot) — D4 CRITICAL: REAL-ONLY is a comment not property. pipeline/execution.py:88-102 falls back to paper.py when MT5 down → outage = silent simulated fills.
(2026-08-05T02:21:00+07:00, devbot) — D5 HIGH: position caps not enforced within cycle (open_positions fetched once, never incremented). N same-symbol signals all pass.
(2026-08-05T02:21:00+07:00, devbot) — D6 HIGH: NONE_TP prefix bypasses naked-fill guard; wrong predicate attaches sl=0.0 to live order.
(2026-08-05T02:21:00+07:00, devbot) — D7 HIGH: bridge sprawl — engine_production_bridge.py imported by 7 modules; live_engine.py (1548 LOC) declared REMOVED but on disk; autonomous.py:666 builds SECOND TradeJournal. ≥3 concurrent stacks on one account.
(2026-08-05T02:21:00+07:00, devbot) — D8 MED: phantom $10k seeded; position_size() reads self.balance not _effective_equity(). Self-eval inert until 20 closed trades/strategy.

(2026-08-05T02:21:47+07:00, fangbot) — F1 CRITICAL: dashboard trading/page.tsx:177-204 fabricates orderbook+time&sales from Math.random() ("Simulate" comment) next to REAL MT5 positions. Real routes/orderbook.py mounted (app.py:425) ignored.
(2026-08-05T02:21:47+07:00, fangbot) — F2 HIGH: 6 pages call non-existent endpoints → permanent 404: /api/council /api/debate /api/rl /api/scheduler /api/causal /api/options.
(2026-08-05T02:21:47+07:00, fangbot) — F3 HIGH: more random-data fallbacks w/o STALE badge: market/page.tsx:111,181, strategies/page.tsx:393, terminal/page.tsx:331.
(2026-08-05T02:21:47+07:00, fangbot) — F4 HIGH: tray exists+wired but (a) backend never emits "error" → dead branch; (b) trading.py:697-700 two identical branches → zero accounts = green; (c) status-tray.tsx:26 swallows fetch failures → dead API stays green forever.
(2026-08-05T02:21:47+07:00, fangbot) — F5 MED: 13 pages unreachable from sidebar/command palette. MED: Next route handlers shadow Python routers on identical paths → Python unreachable from browser.

(2026-08-05T02:24:06+07:00, researchbot) — R1 CRITICAL: self-loop debate never executed. autonomous_self_loop.py:382 calls DebateEngine.debate(dict) vs List[AgentOpinion] sig, then .get("consensus") on dataclass → guaranteed exception swallowed by logger.debug. Step 6 permanent no-op.
(2026-08-05T02:24:06+07:00, researchbot) — R2 CRITICAL: live council always returns hold@0.50. council.py:86,89 matches "buy"/"sell" but personas emit "BULLISH"/"BEARISH"/"NEUTRAL" + hardcoded "neutral" → zero votes match → hold branch → overwrites real signal at autonomous.py:1008-1013.
(2026-08-05T02:24:06+07:00, researchbot) — R3 CRITICAL: non-deterministic council. council.py:152 random.sample picks 3 of 6 per call → same input different trade.
(2026-08-05T02:24:06+07:00, researchbot) — R4 MED: 5/6 personas are 36-line constant stubs. ~2700 LOC orphaned (council/debate.py, council/voting.py, debate/reflection.py, colony.py, duplicate debate_engine.py).
(2026-08-05T02:24:06+07:00, researchbot) — R5 MED: self_aware.py:52 history is RAM list, zero persistence. memory/paging.py (~1050 LOC, working ArchivalMemory.save) has 1 importer (cli.py) → unplugged. graphify-out/graph.json 184 bytes empty → silent indexer failure.

(2026-08-05T02:21:00+07:00, traderbot) — T1 LOW (dangerous): qna.txt "lost scorers" claim FALSE. All 8 exist at core/scoring/ + tested (31 tests). qna.txt used wrong dir+names. Only _verify_scoring.py truly absent.
(2026-08-05T02:21:00+07:00, traderbot) — T2 HIGH: live fusion gate structural no-op. autonomous_cycle.py:421-436 (DEAD FILE) builds FusionEngine but feeds only {symbol,price,candles,signals}; scorers need vix/gpr/ict → return 0/0 → composite=0.0 neutral every cycle → veto branches unreachable. Fix exists unused: context_builder.py:build_fusion_context.
(2026-08-05T02:21:00+07:00, traderbot) — T3 HIGH: dead math in geo_scorer.py:35 (positive input, negative clamp → always 0.0; conflicts add +0.3 conf but zero risk penalty).
(2026-08-05T02:21:00+07:00, traderbot) — T4 HIGH: WF pipeline 89% blind. _tune_wf.log: 81 strategies, 3 with positive OOS fold. numpy import error → wf=err tune=err.
(2026-08-05T02:21:00+07:00, traderbot) — T5 MED: self_eval real+honest (trade_journal.py:258-300 aggregates per-strategy kelly; attribution real). Caveat: :60-65 degrades to DISABLED+keeps trading → should fail-closed.

(2026-08-05T02:37:00+07:00, clawbot) — C1 CRITICAL: autonomous_cycle.py DEPRECATED + 0 references = dead code. Live loop = start_default_scheduler → engine/agentic/autonomous.py. All G-series patches = paper tigers.
(2026-08-05T02:37:00+07:00, clawbot) — C2 HIGH: live scheduler (engine/scheduler.py:54) passes BARE "EURUSD" with NO .vx suffix → Valetax rejects → 0 fills. .vx handling exists ONLY in dead autonomous_cycle.py.
(2026-08-05T02:37:00+07:00, clawbot) — C3 HIGH: self-evolve NO-OP. autonomous_self_loop.py only via REST endpoint, not auto-started. _evolve_strategies → "EVOLVE skip: no baseline params". 0 live trades to date.
(2026-08-05T02:37:00+07:00, clawbot) — C4 MED: REAL-ONLY enforced by refusal (monitor-only, 0 trades), not by trading. Rencana.md "🟢 GREEN" overstates.
(2026-08-05T02:37:00+07:00, clawbot) — C5 MED: README documents deleted feature (qna.py live / python -m autonomous_cycle both dead/stub).
(2026-08-05T02:37:00+07:00, clawbot) — C6 MED: autonomous_self_loop.py orphaned from PipelineScheduler → split-brain self-improvement.

(2026-08-05T02:40:00+07:00, autobot) — SYNTHESIS (consolidated, all-agent input): TOP-10 GAPS: G1 creds-in-git → G2 unpullable kill switch → G3 zero closed trades → G4 council flattens signal to hold@0.50 → G5 fake orderbook next to real → G6 fusion gate can't veto → G7 amnesiac risk baselines → G8 81 strategies/3 OOS → G9 self-loop never executed → G10 10x orphan surface. ROADMAP: P1 Stop Bleeding (rotate creds, wire kill switch, persist baselines, remove fake council, fail-closed journal) → P2 Make Honest (kill Math.random, truthful tray, fix dead endpoints, build_fusion_context, quarantine orphans) → P3 Make Learn (re-run WF w/ numpy, force 100 real closed trades, THEN evolve) → P4 Compound. RULES: R-A freeze, R-B no new surface, R-C quarantine-not-delete, R-D fail loud, R-E evidence or it didn't happen. DECISION: dissent from literal "wire everything" — 6 load-bearing items = critical path.
