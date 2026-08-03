# FINDINGS — TRADE ATTRIBUTION AUDIT (QNA)

**Audit date:** 2026-08-02 (while live loop was running, login 372044706, balance 1128.21)
**Scope:** signal → fusion → verdict → order → trade journal, for both live entry points
  - `quant_nanggroe/autonomous_cycle.py` (60s loop → `PurifiedEngine`) — **the path that owns the 3 live Valetax positions** (GBPUSD.vx BUY, BTCUSD.vx SELL/BUY; symbols list at autonomous_cycle.py:85)
  - `qna.py live` → `quant_nanggroe/live_engine.py` (LiveEngine → production bridge)
**Method:** code inspection (source of truth), live DB inspection, live log inspection. `.md` files not trusted.

---

## 1. VERIFIED OK (Yang Sudah Benar)

| # | Item | Evidence (file:line) |
|---|------|----------------------|
| V1 | Strategy identity is carried on every signal object produced by the registry | autonomous_cycle.py:209-234 (`Signal(..., strategy=name, confidence=...)`) |
| V2 | MT5 order **comment** carries the strategy for orders sent via PurifiedEngine | engine_production_bridge_purified.py:337 `comment=f"{sig.strategy}:{sig.symbol}"` |
| V3 | TradeJournal SQLite schema exists with a `strategy` + `confidence` column | trade_journal.py:46-61 (columns: `ticket, strategy, symbol, side, entry, sl, tp, confidence, open_time, close_time, exit_price, pnl, outcome, comment`) |
| V4 | `record_open()` is called after every filled order in the autonomous loop | autonomous_cycle.py:744-758 |
| V5 | Opposing buy+sell for the same symbol are conflict-resolved (highest confidence wins) | trade_journal.py:151-180 (`resolve_conflicts`), wired at autonomous_cycle.py:740 |
| V6 | Risk gate + KillSwitch are fail-closed in the autonomous loop | engine_production_bridge_purified.py:236-252, 316-319; autonomous_cycle.py:667-672, 690-694 |
| V7 | LiveEngine records signals → `signals` table and open positions → `positions` table with `strategy` | live_engine.py:907-914, 748-752 |

---

## 2. GAPS (Celah / Kekurangan)

### 🔴 CRITICAL

**G1. The trade journal is written to the WRONG PATH — and contains 0 rows. No trade has ever been attributed in the DB.**
- trade_journal.py:29-32 — `dirname(x3)` of `quant_nanggroe/trade_journal.py` resolves to `D:\repositories\` → DB path is `D:\repositories\data\qna_trade_journal.db` (verified by executing the path expression; file exists there, table `trades`, **0 rows**).
- The repo-local `data/qna_trade_journal.db` is a **0-byte file with no schema** (created 2026-08-02 01:38).
- Verified live at 08:30 while the loop was running (cycle #214): both DBs **0 rows**.
- Consequence: the entire self-eval / attribution feature (commit cec7e055 intent) has produced **zero persisted data**. There is no way to answer "which strategy produced this trade" from any DB.

**G2. Close-journaling is dead code — PositionManager is constructed with `journal=None`.**
- autonomous_cycle.py:659 creates `PositionManager(self.engine, self.market_data, self.journal)` **before** `self.journal = TradeJournal()` at line 665.
- `_on_position_closed()` early-returns `if not self.journal` (autonomous_cycle.py:413), so `record_close`, `self_eval()`, and Kelly-update (lines 430-439) **never run**.
- Consequence: no `close_time/exit_price/pnl/outcome` ever written; per-strategy win-rate/expectancy/Kelly are never computed from real PnL.

**G3. Unattributed execution path in LiveEngine: production-bridge orders execute on MT5 with NO DB record and NO broker comment.**
- live_engine.py:1162 — `exec_order = self.production["execution"].execute_signal(sig, ...)` fires a real MT5 order; the result is only consumed when `mode == "fallback"` (line 1164). In REAL-ONLY mode fills come back as `mode="mt5-live"` (engine_production_bridge.py:440) and are **silently discarded** — no `positions`, no `trades`, no `signals` row.
- The `Order` object sent to the broker has **no strategy field** and no comment (engine_production_bridge.py:426-433); `MT5Broker.place_order` builds the request with **no `comment`** (mt5_broker.py:80-93, magic fixed 888888). Broker-side deal history is therefore unattributable.
- SELL signals on this path open new SHORT positions with **no risk pre-check at all** — only BUY goes through `_can_open_new_position` (live_engine.py:1157-1161).

**G4. Positions already open at engine start are adopted silently and can never be attributed.**
- autonomous_cycle.py:399-409 — `update_positions()` adds every live MT5 ticket to `_seen_tickets` without calling `record_open`; on close, `get_open_trade(ticket)` returns None → `_on_position_closed` returns (lines 426-428). The 3 live positions were opened before the 04:03 run → **no attribution record exists for them today**.
- Same flaw in LiveEngine: `_sync_broker_positions` inserts broker positions with `strategy="mt5-sync"` (live_engine.py:698-722, line 718) — a placeholder, not a strategy.

**G5. No position-exists gate: the engine can open multiple stacked orders per symbol from multiple strategies.**
- `PurifiedEngine.cycle` executes **every** signal in the batch (engine_production_bridge_purified.py:311-346); `resolve_conflicts` only dedups *opposing* sides (trade_journal.py:167-179) — two strategies both saying BUY both execute.
- `MAX_POSITIONS_PER_SYMBOL=1`, `MAX_TOTAL_POSITIONS=5` are defined (autonomous_cycle.py:94-95) but **never referenced anywhere** (repo-wide grep: definitions only).
- With 81 strategies firing every 60 s this directly explains "trades look random / some buy some sell": successive cycles from different strategies open opposing or stacked positions.

### 🟠 MAJOR

**G6. HOLD (no trade) is never logged with reasons.**
- autonomous_cycle.py:202-203 silent return when candles < 50; strategy returning `None`/`hold` silently skipped (lines 211-212); empty signal list logs nothing (line 727 `if signals:`); risk vetoes only warn at bridge:318.
- live_engine.py:908-909 `if ls.side == "hold": continue` — no log.
- Live proof: `data/autonomous_loop.log` (967 lines, cycles #1-#214) contains **zero** signal lines — the loop gives no reason why nothing trades.
- Only the non-live `pipeline/signal.py:140-142` logs a hold reason.

**G7. Journal attribution is best-effort and can be WRONG.**
- autonomous_cycle.py:749-752 — filled ticket is matched back to a signal by `(symbol, side)` only; with multiple same-side signals, `next()` picks an arbitrary one; no match → `strategy="unknown"`, `confidence=0.0` (lines 751-752). No ticket↔signal linkage from the engine.
- Also `sl`/`tp` are journaled as **NULL**: `execute_order` result dict has no sl/tp (engine_production_bridge_purified.py:145-146) → autonomous_cycle.py:756-757.

**G8. RiskGuard runs on a phantom $10,000 balance — all risk decisions are computed on fake numbers.**
- autonomous_cycle.py:648 hardcodes `initial_balance=10000.0`; MT5 real balance (1128.21, logged at bridge:75-76) is never fed into `RiskGuard`.
- Live log every cycle: `Balance: $10000.00 | Trades: 0 | Wins: 0` while real equity ≈ $1122 with 3 open positions. Drawdown/daily/weekly-loss gates and Kelly sizing are therefore meaningless.
- `RiskGuard.update_pnl` (bridge:261-270) is never called by `cycle()`.

**G9. Kelly feedback is broken twice over.**
- Attribute mismatch: `PerformanceTracker` writes `self.risk_guard._kelly_cache` (autonomous_cycle.py:611) but `PurifiedEngine` reads `self.risk.kelly_cache` (bridge:322) — different dicts; and `PerformanceTracker.record_trade` is never called (grep: no callers).
- The `self_eval()`→kelly path (autonomous_cycle.py:433-439) is dead because of G2.

**G10. Misleading close logs: "closed" is logged even when the close FAILED.**
- autonomous_cycle.py:483-486 — `FULL TP: ... closed at 24.66R` logged unconditionally after `_close_position`; live log shows `Close failed retcode=10018 (Market closed)` **every cycle** for 4+ hours while the position stays open; `_partial_close` swallows order_send failures silently (lines 527-529). No "position still open" state tracking.

### 🟡 MINOR

**G11. Journal schema lacks factor contributions and risk-gate results.**
- trade_journal.py:46-61 — columns store only `strategy/confidence/comment`; no factor contributions, no risk-gate veto history, no fusion inputs.
- qna_live.db `signals` table has **no confidence column** (live_engine.py:136-141); `trades` table has strategy but no confidence/risk results (live_engine.py:123-129).

**G12. The "fusion" you believe runs (SignalFusion conf ≥ 0.65) is NOT on the live path.**
- `FusionEngine` (core/scoring/fusion_engine.py:17 `EXECUTION_CONFIDENCE_THRESHOLD=0.60`), council `DEBATE_THRESHOLD=0.65` (engine/agentic/council.py:26), and `DecisionEngine` (engine/decision.py:73, min 0.60) are used only by API/CLI/agent layers. Live "fusion" = `resolve_conflicts` only (trade_journal.py:151).
- LiveEngine's `RiskGate.check_signal` ignores `signal.confidence` entirely (engine/live/adaptive_integration.py:375-379) — sub-threshold signals can trade on the adaptive path.

**G13. Entry-point fragility: same file, different behavior by cwd.**
- autonomous_cycle.py:31-32 inserts only `repo/quant_nanggroe` into sys.path → `from quant_nanggroe.engine.strategies.registry import StrategyRegistry` fails when launched as `python quant_nanggroe/autonomous_cycle.py` → silent fallback to 4 built-in strategies (observed 2026-07-29 log: "registry not available — using built-in strategies"). The 2026-08-02 run loaded 81 strategies because the cwd differed. Registry availability must not depend on launch directory.

---

## 3. RECOMMENDED FIX (Rekomendasi Perbaikan)

1. **Fix DB path (G1):** `trade_journal.py:29-32` — use exactly two `dirname()` calls (repo root) or `REPO_ROOT = Path(__file__).resolve().parents[1]`. Add a startup assertion + a `journal_count` check that alerts if the file has no rows.
2. **Fix journal wiring (G2):** move `self.journal = TradeJournal()` BEFORE `PositionManager(...)` (autonomous_cycle.py:659 vs 665), or pass `self.journal` lazily.
3. **Close the attribution loop at the broker (G3, G7):** add `comment` (strategy + confidence) to `MT5Broker.place_order` request (mt5_broker.py:80-93) and a `strategy` field on `Order` (engine_production_bridge.py:426); journal the production-bridge fills in live_engine.py:1162-1173; pre-check SELL shorts with `_risk_gate`/`_can_open_new_position`; record ticket↔signal mapping at fill time instead of best-effort re-matching.
4. **Adopt-and-attribute existing positions (G4):** on startup, reconcile MT5 positions and insert `record_open(..., strategy=<comment-derived or "UNKNOWN" flagged>)`; never silently adopt.
5. **Enforce position caps (G5):** implement `MAX_POSITIONS_PER_SYMBOL` / `MAX_TOTAL_POSITIONS` in `PurifiedEngine.cycle` using `mt5.positions_get()` (or a broker positions check) before executing each signal; dedup same-side signals per symbol per cycle.
6. **Log HOLD with reasons (G6):** emit `HOLD <symbol> reason=<no_candles|no_signal|below_conf|risk_veto|position_open>` on every cycle with no trade, to file + DB (`hold_log` table).
7. **Sync real balance into RiskGuard (G8):** read `mt5.account_info().balance/equity` each cycle and update `RiskGuard`; call `update_pnl` from real deal history (MT5Broker.history_deals_get exists).
8. **Fix Kelly attr + wire self-eval (G9):** unify on `kelly_cache`; call `self_eval()` after each close.
9. **Honest close logs (G10):** only log `CLOSED` when `order_send.retcode == TRADE_RETCODE_DONE`; track open/close state per ticket; alert on repeated close failures.
10. **Extend journal schema (G11):** add `factor_contributions JSON`, `risk_gate JSON` (veto history), `fusion JSON`, `source_comment`, `mt5_magic`. Also add `confidence` to qna_live.db `signals` (live_engine.py:136-141).
11. **Make launch-context independent (G13):** insert `REPO_ROOT` (not just `repo/quant_nanggroe`) into sys.path at autonomous_cycle.py:32.

---

## Appendix — Live Evidence (2026-08-02)

- Loop started 04:03, login 372044706, `balance=1128.21` (data/autonomous_loop.log:23).
- 81 strategies loaded (log:98); `Min confidence: 0.6` (log:104).
- Cycles #1-#214: `Close failed for 20178543987 retcode=10018/10031` every cycle + unconditional `FULL TP: GBPUSD.vx ... closed at 24.66R` (log:431-489).
- `Balance: $10000.00 | Trades: 0 | Wins: 0` every cycle (phantom risk state).
- `D:\repositories\data\qna_trade_journal.db` — `trades` table, **0 rows**; repo `data/qna_trade_journal.db` — 0 bytes, no schema.
- `data/qna_live.db` — positions: 1 (paper-era BTCUSDT 'SMC' from 2026-07-25), trades: 0, signals: 0.
- `quant_nanggroe/audit.db` — audit_log: 0 rows.


<!-- CODE-TRUTH STATUS FOOTER — appended 2026-08-03 23:43:45 by autobot (QNA audit 2026-08-03) -->
<!-- Method: append-only. Source of truth = code, not prior .md claims. -->
## 🔍 CODE-TRUTH STATUS (2026-08-03 audit)
- **FusionEngine**: EXISTS — `quant_nanggroe/core/scoring/fusion_engine.py:27` (prior claim "false" RETRACTED).
- **API server**: EXISTS + startable — `quant_nanggroe/cli.py:603` uvicorn :8000; `launch.bat api`; 223 routes wired.
- **Dashboard**: UNWIRED only because server not started; UI code present (`dashboard/`, 261 tsx+ts).
- **Phantom-equity ($1M default)**: MITIGATED — P1b fail-CLOSED `_resolve_equity()` floor $1000 in `risk_gate_bridge.py` (ctor:145, evaluate:194, evaluate_from_state:449). Live path uses `evaluate_from_state` -> real MT5 equity.
- **Polars**: NOT imported anywhere (`import polars`=0) -> `engine/data/providers/yahoo_polars.py` genuinely MISSING (archive gap real).
- **Secrets**: 0 hardcoded (grep `sk-`/`AKIA`=0). `eval`/`pickle`: 0 live vulns (only security-linter strings).
- **ENV BLOCKER**: all venv numpy ABI broken (cp311 `.pyd` under cp312) -> runtime import unverified until `uv sync`. Patch syntax+logic verified standalone.
- **Archive upgrade**: 8/11 new modules ALREADY in code; 4 missing (quality.py, yahoo_polars.py, feature_engine.py, alerting/).
- **Audit trail**: `C:/Users/Hi/Desktop/QNA_AUDIT_DEBAT.txt` | inventory `QNA_FILE_INVENTORY.txt` | `QNA_EXTENSION_LEDGER.txt`.
<!-- END CODE-TRUTH FOOTER -->
