# Journal Expectancy — Real MT5 Journal Read

- **Date:** 2026-09-04
- **Source file:** `quant_nanggroe/data/qna_trade_journal.db` (245,760 bytes, mtime 1788393511.8015585)
- **Access:** read-only — every query ran against a temp copy (`shutil.copyfile` → `sqlite3` `mode=ro` URI). Live file never opened for write.
- **Row counts:** `trades` = 429, `signal_context` = 511
- **Window:** `MIN(open_time)` = 1784541369.0, `MAX(open_time)` = 1788391834.0 (≈ 2026-09-02)

## Schema (exact, from `sqlite_master`)

```sql
CREATE TABLE trades (
    ticket INTEGER PRIMARY KEY,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry REAL NOT NULL,
    sl REAL,
    tp REAL,
    confidence REAL,
    open_time REAL NOT NULL,
    close_time REAL,
    exit_price REAL,
    pnl REAL,
    outcome TEXT,  -- 'win' | 'loss' | 'open'
    comment TEXT,
    hypothesis TEXT, setup_ctx TEXT, close_reason TEXT, hit_type TEXT,
    market_ctx TEXT, tf_category TEXT);

CREATE TABLE signal_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    strategy TEXT DEFAULT 'unknown',
    entry_price REAL DEFAULT 0.0,
    sl REAL DEFAULT 0.0,
    tp REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.0,
    atr REAL DEFAULT 0.0,
    lot_size REAL DEFAULT 0.01,
    timestamp TEXT NOT NULL,
    ticket INTEGER,
    filled INTEGER DEFAULT 0,
    pnl REAL DEFAULT 0.0,
    outcome TEXT DEFAULT '',
    hit_type TEXT DEFAULT '');
```

## Exact SQL used

```sql
-- close_time presence
SELECT COUNT(*) FROM trades WHERE close_time IS NULL;      -- 105
SELECT COUNT(*) FROM trades WHERE close_time IS NOT NULL;  -- 324
-- closed-trade expectancy
SELECT COUNT(*), ROUND(AVG(pnl),4), ROUND(SUM(pnl),2)
  FROM trades WHERE close_time IS NOT NULL;                -- 324 | 5.0477 | 1635.47
-- confidence buckets on closed trades
SELECT COUNT(*), ROUND(AVG(pnl),4), ROUND(SUM(pnl),2) FROM trades
 WHERE close_time IS NOT NULL AND (confidence IS NULL OR confidence < 0.30);
SELECT COUNT(*), ROUND(AVG(pnl),4), ROUND(SUM(pnl),2) FROM trades
 WHERE close_time IS NOT NULL AND confidence >= 0.30 AND confidence < 0.50;
SELECT COUNT(*), ROUND(AVG(pnl),4), ROUND(SUM(pnl),2) FROM trades
 WHERE close_time IS NOT NULL AND confidence >= 0.50;
-- per-strategy on closed trades
SELECT strategy, COUNT(*), ROUND(AVG(pnl),4), ROUND(SUM(pnl),2)
  FROM trades WHERE close_time IS NOT NULL GROUP BY strategy ORDER BY 2 DESC;
-- attribution / linkage diagnostics
SELECT strategy, COUNT(*) FROM trades GROUP BY strategy ORDER BY 2 DESC;
SELECT strategy, COUNT(*) FROM signal_context GROUP BY strategy ORDER BY 2 DESC;
SELECT COUNT(*) FROM signal_context WHERE filled=1;        -- 0
SELECT COUNT(*) FROM signal_context WHERE ticket IS NOT NULL; -- 0
SELECT COUNT(*) FROM trades WHERE confidence=0.0;          -- 289
SELECT outcome, COUNT(*) FROM trades GROUP BY outcome;
```

## Results

### Close distribution — 324 of 429 rows actually closed

| close_time | n |
|---|---|
| NOT NULL (closed) | 324 |
| NULL (open) | 105 (ensemble 88, unknown 16, pipeline 1) |

Closed-trade expectancy: **n=324, AVG(pnl)=5.0477, SUM(pnl)=1635.47**.

### Expectancy per confidence bucket (closed trades only)

| bucket | COUNT | AVG(pnl) | SUM(pnl) |
|---|---|---|---|
| lo (< 0.30) | 185 | 8.9146 | 1649.20 |
| mid (0.30–0.50) | 0 | NULL | NULL |
| hi (≥ 0.50) | 139 | -0.0988 | -13.73 |

### Expectancy per strategy (closed trades only)

| strategy | COUNT | AVG(pnl) | SUM(pnl) |
|---|---|---|---|
| ensemble | 179 | 2.5244 | 451.87 |
| unknown | 113 | 10.6777 | 1206.58 |
| smc | 22 | -0.7291 | -16.04 |
| aroon | 8 | -1.4275 | -11.42 |
| day | 1 | 4.4800 | 4.48 |
| probe | 1 | 0.0000 | 0.00 |

All-rows strategy mix (429): ensemble 267, **unknown 129 (30.1%)**, smc 22, aroon 8, day 1, pipeline 1, probe 1. No empty-string strategies anywhere (0 rows).

Outcome column: breakeven 104, loss 244, open 1, win 80. `pnl`: NULL 1, zero 244, nonzero 184.

## Caveats (read before quoting any number)

1. **Confidence column is effectively binary, not a real bucket signal.** All 185 "lo" closed rows have `confidence = 0.0` (the sync default when no `signal_context` link exists). The mid bucket is empty by construction: pipeline confidences that do link are ≥ 0.50, unlinked rows are 0.0. Do not read "lo beats hi" as a finding — it compares unlinked-default rows vs linked rows.
2. **Signal→ticket linkage never fired.** All 511 `signal_context` rows are `strategy='ensemble'`, `ticket IS NULL`, `filled=0`, `outcome=''`. The `link_signal_to_ticket` / ticket-update path in `journal_sync.py` wrote nothing, so trade-row `sl/tp/confidence` fall back to NULL/0.0.
3. **Unknown attribution (129/429 = 30.1%; 113/324 = 34.9% of closed) comes from the MT5-sync attribution layer**, `_attribute_strategy` in `quant_nanggroe/engine/journal_sync.py:188-205` (magic not mapped, no comment keyword, no single admitted strategy) — NOT from the `record_signal` path, whose caller already defaults to `"ensemble"` (`autonomous.py:1245-1247`). The `record_signal`/`record_signal_context` callee-side `"ensemble"` fallback added with this doc only closes the residual empty/None/whitespace hole; it cannot re-attribute the historical 129.
4. **PnL is net of costs.** `sync_mt5_deals` stores `profit + commission + swap` per close deal.
5. **Source is MT5 fills history** (live/Valetax account deals synced into the journal), not paper telemetry. One `pipeline` row is still `outcome='open'` with NULL pnl/`close_time`.

## Store reconcile (docs only — no ledger logic changed)

| store | trades | explanation |
|---|---|---|
| `quant_nanggroe/data/qna_trade_journal.db` → `trades` | 429 (324 closed) | MT5 fill history synced via `sync_mt5_deals` — the fills ledger of record. |
| `data/trade_history.db` → `trade_events` (`traded=1`) | 90 flags, all with `entry_price=0`, `pnl=0`, `SUM(pnl)=0.0` | Pipeline telemetry intents (`buy` 497 / `sell` 233 / `hold` 1286 of 2016 events), never wired to fill prices — intent log, not fills. |
| `data/qna_live.db` → `trades` / portfolio | 0 / balance 10000.0 flat, `signals` 0 | Virgin store on an unused path — nothing writes live positions there. |
| `quant_nanggroe/data/account_ledger.json` | 0 trades (logins 211098748, 372044706) | Login registry only (`first_seen`/`last_seen`); the `trades` counter is never incremented by any writer. |

Divergences are wiring gaps (telemetry vs fills vs unused store vs un-incremented counter), not conflicting truths: the journal is the only store holding broker-confirmed fills.

## Addendum 2026-09-04 — B1 chain repaired + bucket finding (v8.1.4)

**Chain autopsy (why `signal_outcomes` had 0 rows despite live fills):**
1. BREAK-A (entry): `_make_decision` resolved ticket from broker positions on ONE poll — position often not yet visible post-fill → ticket 0 → `if _ticket:` gate skipped `record_signal`. Fixed: retry 3×1s + loud warning (`autonomous.py` B1 block).
2. BREAK-B (linkage): back-link `UPDATE ... WHERE rowid=?` passed `sig_row.rowid`, but the SELECT listed only 5 columns and `sqlite3.Row` exposes no `.rowid` → `hasattr` False → `None` → matched nothing (569/569 NULL). Fixed: `SELECT rowid, ...` + `sig_row[0]` (`journal_sync.py`).
3. BREAK-C (close join): `record_outcome` matched only the close-deal ticket, while entries carry the *position* ticket. Fixed: also close by `position_id` (`journal_sync.py`, both call sites, fail-soft).

**Bucket expectancy, closed journal trades only (`outcome IN ('win','loss')`, n=373):**

| Bucket | COUNT | AVG(pnl) | SUM(pnl) |
|---|---|---|---|
| lo (conf < 0.30) | 234 | +7.14 | +1670.93 |
| mid (0.30–0.50) | 0 | n/a | n/a |
| hi (conf ≥ 0.50) | 139 | −0.10 | −13.73 |

Reading (honest, not a signal): low-confidence flow is net-positive (+1671 over 234 closes) while high-confidence flow is flat — the OPPOSITE of what a confidence gate assumes. Caveats: period/cohort effects unmeasured; costs ARE included (profit+commission+swap); mid bucket empty (n=0). Implication: do NOT raise the committee floor on theory — the data says the edge, if any, lives in the lo bucket. Re-query after 100+ new ticket-matched closes before any threshold action.
