# QNA FINAL-PHASE PROMPTS — end of development phase

> Status at writing: v8.1.3 + follow-ups (`471e251e`), daemon ALIVE, 5/5 remotes synced.
> Purpose: copy-paste prompts below into subagents to finish development.
> Rule for ALL prompts: no commits (coordinator commits); end with exactly one line:
> `result: <headline>` OR `needs input: <ask>` OR `failed: <reason>`.
> Global rules: fail-closed preserved; defaults unchanged unless stated; minimal diffs;
> docs follow code (file:line evidence); PYTHONPATH="" for python; Windows paths.

## Phase-close definition (DONE = all true)

- [ ] P0 battery green: test_risk + agentic + vector + strategy + cpcv-writer + kill-switch (currently 256+8xf + deltas)
- [ ] `tsc --noEmit --skipLibCheck` clean + `next build` 40/40 routes
- [ ] `ruff check .` + `mypy quant_nanggroe/ --ignore-missing-imports` clean (CI parity)
- [ ] Zero `Math.random`-as-data, zero bare `risk_reward=`, zero dead UI wrappers
- [ ] Versions agree ×4: pyproject + qna.py + pkg `__init__` + CANONICAL footer
- [ ] CHANGELOG + CANONICAL § cover HEAD commit (no drift)
- [ ] Daemon alive + scheduler events fresh (<15 min) + kill-switch state documented
- [ ] NO-GO sizing still standing OR overturned by measured evidence (never by opinion)
- [ ] Release tag `v8.x.x` pushed to all 5 remotes

Out of scope for dev-close (needs live time, not code): 100+ closed live trades proof,
committee threshold data-tuning, veto/Kelly/voter DELETION (parity+markers suffice),
WinRate-gated promotion (needs analyzer+re-run cycle + live fills).

---

## PROMPT 1 — closer-ci-green (make CI fully green)

```
WRITE MODE — repo D:\repositories\Quant-Nanggroe-AI-worktree. No commits.
Baseline: .github/workflows/ci.yml runs ruff + mypy --ignore-missing-imports + gitleaks +
pytest tests/ quant_nanggroe/tests/ --cov-fail-under=60 -x + tsc (setup-node + npm ci).
Known debt: tests/test_qna_units.py has 40 `except ImportError` guards (soft-pass pattern);
dashboard vitest/build excluded by comment (slow).

TASKS:
1. Run ruff check . and fix ALL findings in files WE own (quant_nanggroe/engine/risk/*,
   api/routes/risk_config.py, dashboard settings/vector pages excluded — ruff is py-only).
   For pre-existing violations in untouched legacy files: fix only if trivially safe,
   else list them (file:line + rule code) in your result. Do NOT reformat whole files.
2. Run mypy quant_nanggroe/engine/risk/manager.py quant_nanggroe/engine/risk/checks.py
   quant_nanggroe/api/routes/risk_config.py --ignore-missing-imports; fix only new-type
   errors introduced by recent work (metadata_overrides, evaluate params, threshold
   resolver); list pre-existing ones, don't boil the ocean.
3. tests/test_qna_units.py: count the 40 guards, categorize what each guards
   (missing optional dep vs drifted API). For guards hiding DRIFTED internal APIs
   (imports from quant_nanggroe.* that fail), convert up to 5 to real passing tests
   against current API or mark the guarded block with # DRIFT: <expected module>.
   For missing-optional-dep guards (torch/chromadb/CCXT/redis): leave, just count.
4. Do NOT touch: thresholds, execution, sizing, live paths, versions.
VERIFY: ruff clean on touched files; mypy clean on the 3 files; pytest
  tests/test_qna_units.py -q (same-or-better pass count, zero new failures).
```

## PROMPT 2 — closer-scripts (finish the 16 kept candidates)

```
WRITE MODE — repo D:\repositories\Quant-Nanggroe-AI-worktree. No commits.
Baseline: archive/scripts_rot_2026-09-05/README.md lists 16 kept candidates as
needs-manual-review (shim-importable or live-referenced). scripts/ still ~112 files.

TASKS (per file, decide KEEP / QUARANTINE / FIX-IMPORT):
1. For each of the 16: grep importers across quant_nanggroe/, tests/, qna.py,
   dashboard/src, .github/workflows. If zero live importers AND stale singular-tree
   import (engine.strategy.strategies / backtest_adapter / regime_strategy): git mv to
   archive/scripts_rot_2026-09-05/ + one README line (filename + stale import + file:line).
2. If importable via shim or referenced by tests/CI: FIX the import to the canonical
   path (engine/strategies/, engine/backtest/) when the target API matches; if the API
   drifted, QUARANTINE instead with reason. Never rewrite script logic.
3. Hardcoded machine paths (D:\..., C:\..., /tmp/, /root/): replace with
   Path(__file__).resolve().parent.parent-anchored paths ONLY where the intent is
   obvious; else list them (file:line) for manual review.
4. Do NOT touch: run_cpcv_validation.py, run_walkforward.py, qna_autonomous_cycle.py,
   anything CI/tests import, docs/_attic, session.md, .env.
VERIFY: git status shows moves only (R) + README; py_compile edited files; grep
  confirms no live references to quarantined basenames.
```

## PROMPT 3 — closer-docs (final consistency sweep)

```
WRITE MODE — markdown + version files only, repo D:\repositories\Quant-Nanggroe-AI-worktree.
No commits.
Baseline: CANONICAL SSOT + CHANGELOG + §15.x sections; 80-file footer convention;
known items: session.md 206KB+ append-only, QNA_FULL_CONTEXT dated snapshot (by design),
WAR_PLAN archived banner, AGENT_STATE fixed once.

TASKS:
1. Consistency sweep: versions agree ×4 (pyproject/qna.py/pkg/CANONICAL footer);
   strategy counts (84 live files / 80 decorated / 59 archive) stated identically
   everywhere they appear (grep "83 strategies\|84 strategies\|80.*decorat" and unify
   to the verified numbers with file:line citations); test counts in CANONICAL vs
   actual `def test_` grep counts (report deltas, fix where stale).
2. Fresh overclaim hunt: read the NEWEST CANONICAL section + newest CHANGELOG entry;
   spot-check 6 verifiable claims against code; mark VERIFIED/PARTIAL/OVERCLAIM;
   fix PARTIAL/OVERCLAIM on the spot (docs follow code).
3. session.md: do NOT edit. Propose rotation (not execution): report size/lines and
   draft a 5-line rotation policy (rename to session-YYYY-MM-DD.md + fresh session.md)
   as a RECOMMENDATION in your result for the owner.
4. QNA_AGENT_STATE.md: re-verify version/skills/phase lines vs current code; fix drift.
5. Do NOT touch: docs/_attic, archive, lessons.json, .env, any code.
VERIFY: every edited claim cites file:line you personally read; version strings match.
```

## PROMPT 4 — closer-deadcode (GATED — do not run until live proof exists)

```
WRITE MODE — repo D:\repositories\Quant-Nanggroe-AI-worktree. No commits.
GATE: run this prompt ONLY after 100+ closed live trades with ticket-matched outcomes
exist in quant_nanggroe/data/qna_trade_journal.db AND per-bucket expectancy is computed.
If the gate is not met, reply `needs input: live-proof gate not met (closed=X)` and stop.

TASKS (only past gate):
1. Veto: delete GovernanceVetoGuard + QuickVetoBridge ONLY IF parity tests prove
   RiskManager+ConstitutionalRiskGuard cover every veto scenario for 30 live days
   with zero missed vetoes. Keep limits.py (persistent weekly tracker) regardless.
2. Kelly: unify on risk/kelly.py; archive kelly/ dupes + sizing.py + position_sizing.py
   ONLY IF position-size outputs match to 6 decimals on 1000 sampled inputs (write the
   comparison test first, then delete).
3. Voters: keep VoteChamber; archive council/ensemble/voting ONLY IF no live caller
   remains (grep) and committee tests stay green.
4. After each deletion: full P0 battery + tsc + build. Any red = revert that deletion.
VERIFY: battery green; grep zero references to deleted module paths; commit message
  lists every deleted file + proof location.
```

## PROMPT 5 — keeper-monitor (daemon liveness + weekly evidence)

```
READ-WRITE MODE (may restart daemon) — repo D:\repositories\Quant-Nanggroe-AI-worktree.
No commits except docs/KEEPER_LOG.md append (create if absent; force-add note for
coordinator since docs/ is gitignored).

TASKS (weekly, or on demand):
1. Liveness: PID file (data/daemons/qna_daemon.pid) alive? scheduler last_event fresh
   (<15 min)? kill-switch state? MT5 terminal process present? Daemon parent/child tree
   sane (one parent, no duplicates)? Report each with evidence.
2. If daemon DOWN and kill-switch inactive and MT5 present: restart via
   `start "QNA-Daemon" /b .venv\Scripts\python.exe qna.py daemon` from repo root,
   fix stale PID file to the live parent PID, verify fresh scheduler events within
   ~10 min. If kill-switch ACTIVE: do NOT restart trading — report state + reason.
3. Evidence: count new ticket-matched outcomes in journal (entries with ticket != 0
   AND matched close); count strategy='unknown' share (must shrink over time);
   report per-strategy closed counts.
4. Append one dated entry to docs/KEEPER_LOG.md: liveness table + evidence counts +
   verdict (HEALTHY/HALTED/DEGRADED) + one-line next action.
5. Never: change thresholds, delete code, touch .env, trade manually.
VERIFY: scheduler mtime fresh after restart; journal file byte-size grown (or explain why not).
```

## PROMPT 6 — closer-ledger (single PnL truth)

```
WRITE MODE — repo D:\repositories\Quant-Nanggroe-AI-worktree. No commits.
Baseline: three stores disagree (journal 429 rows telemetry-heavy, trade_events 90 flags
with zero prices, qna_live virgin 0 trades, ledger 0 trades). B1 ticket join now feeds
record_signal→record_outcome.

TASKS:
1. Read all four writers (journal_sync, trade_history, qna_live writer, ledger writer):
   who writes what, on which event (fill? close? MT5 sync?), with which keys.
2. Declare canonical: quant_nanggroe/data/qna_trade_journal.db (trades + signal_context
   joined by ticket). Write docs/PNL_TRUTH.md: per-store role (canonical vs view vs
   deprecated), join keys, and which stores new code must write to (exactly one).
3. Code (minimal, fail-closed): ensure EVERY record_signal call passes non-empty
   strategy (fallback "ensemble" already convention — verify all callers via grep
   record_signal, fix any passing empty/None); ensure record_outcome matches by ticket
   AND logs unmatched closes (warning with ticket id, no crash).
4. Add ≥3 tests on temp DBs (never touch live journal): ticket join round-trip,
   non-empty strategy enforced, unmatched close warns-but-survives.
5. Do NOT touch: risk, execution, sizing, thresholds, versions.
VERIFY: new tests pass; live journal byte-identical (record size before/after);
  py_compile touched files.
```

## PROMPT 7 — closer-release (tag + ship v8.x)

```
WRITE MODE (git allowed: tag + push tags only, no code edits) — repo
D:\repositories\Quant-Nanggroe-AI-worktree. No commits.
Preconditions (verify, abort with needs-input if any fail): working tree code-clean
(only runtime JSON may be dirty); P0 battery green (run it: test_risk + agentic +
vector + strategy + cpcv-writer + kill-switch); tsc clean; versions agree ×4;
CHANGELOG + CANONICAL cover HEAD (no drift).

TASKS:
1. Run the battery + tsc yourself and paste counts into result (do not trust prior claims).
2. Create annotated tag v<VERSION-from-qna.py> with message summarizing HEAD..last-tag
   (git log --oneline last-tag..HEAD, tags listed via git tag --list).
3. Push tag to all 5 remotes: codeberg, gh_dhaherlabs, gh_mulky, gh_mulky2, gitlab
   (remote names verified via git remote -v first; never invent URLs).
4. Verify each remote reports the new tag (git ls-remote --tags <remote> | grep version).
5. Report: tag name, commit hash, per-remote OK/FAIL.
RULES: tags only; if anything red, stop before tagging and report needs-input.
```

## PROMPT 8 — skeptic-round (re-grade quarterly or on demand)

```
RESEARCH ONLY — no writes. Repo D:\repositories\Quant-Nanggroe-AI-worktree.
Be the skeptic, not the cheerleader. File:line for every factual claim.

1. Recompute the ALPHA table from data/cpcv_registry.json (do not trust the doc):
   per-leg (avg, min, win_rate, trades). Is 0/10 still correct under min_sharpe>0?
   Any leg newly passing? Any sentinel legs?
2. Liveness: journal sizes, live DB counts, kill state, scheduler freshness, lessons
   growth. Traded since last audit? Fills broker-side only (note as unverifiable)?
3. Committee default vs measured bucket expectancy (docs/JOURNAL_EXPECTANCY.md if
   present): does data justify the current floor? Exact query + numbers.
4. One NEW structural concern from previously-unread code (pick: orderflow path,
   portfolio metrics, backtest costs, hedge_fund fallback, dashboard proxies).
5. GO/NO-GO on sizing with the single strongest reason. No hedging without numbers.
```

---

## Appendix: dev-close punchlist (owner checklist, updated 2026-09-04)

- [x] Risk truth (G1/G3/G10, UnboundLocalError, 80% buffer, schema)
- [x] API wiring (10 fixes, DEAD_API + markers)
- [x] Docs truth (§15.9 corrections, §15.13–15, footers, versions ×4)
- [x] Tests green (strategy 24/24, risk 169+8xf, parity, floor, P0, fill-ticket)
- [x] Lockfiles + CI (tsc step, both test paths)
- [x] Self-evolve READY (B1 ticket join, N1 metadata, journal expectancy doc)
- [x] Daemon resuscitated (alive + events flowing, PID fixed)
- [x] Gold experiment run + honestly rejected (win_rate 0.24–0.30, DD −0.47/−0.85)
- [ ] CI fully green incl. mypy/ruff zero-new (PROMPT 1)
- [ ] Scripts quarantine finished (PROMPT 2)
- [ ] Single PnL truth doc + unknown attribution → ~0% (PROMPT 6)
- [ ] Release tag v8.1.3 × 5 remotes (PROMPT 7)
- [ ] 100+ closed live trades proof (needs TIME, not code)
- [ ] Veto/Kelly/voter deletion (PROMPT 4, gated on live proof)
- [ ] Sizing (NO-GO until expectancy net-of-costs > 0 over ≥100 closes)
