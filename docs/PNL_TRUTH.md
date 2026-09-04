# PnL Truth — Single Canonical Store

**Canonical: `quant_nanggroe/data/qna_trade_journal.db`** (MT5 broker truth).
All realized-PnL reads (dashboard, scorecards, `state_writer` guard, audits)
must derive from this file. Nothing else is PnL truth.

Live-journal safety: the live file is **read-only** for analysis — copy to
`%TEMP%` first, never open it for writing. Verified 2026-09-04:
`qna_trade_journal.db` = 253952 bytes before and after (byte-identical).

## Per-store roles

| # | Store (writer) | File / table | Role | Writes on which event | Keys |
|---|---|---|---|---|---|
| 1 | `journal_sync.sync_mt5_deals` (+ `record_signal_context`, `link_signal_to_ticket`) | `qna_trade_journal.db` → `trades` (**canonical**), `signal_context` (intent) | **CANONICAL.** Broker-settled fills only. | MT5 `history_deals_get` grouped by `position_id`; open deal + close deal paired. `signal_context` rows written on buy/sell pipeline decision (`autonomous.py`), linked to ticket by symbol + entry-price match; `record_outcome` forwarded to evaluator per close. | `trades`: `ticket` UNIQUE (join key), `strategy`, `symbol`, `side`, `entry`, `sl`, `tp`, `confidence`, `open_time`, `close_time`, `exit_price`, `pnl`, `outcome`, `comment` (`magic=`), `close_reason`, `hit_type`. `signal_context`: `symbol`, `strategy`, `entry_price`, `sl`, `tp`, `confidence`, `atr`, `lot_size`, `timestamp`, `ticket`, `filled`, `pnl`, `outcome`, `hit_type` |
| 2 | `StrategyEvaluator.record_signal` / `record_outcome` | `data/strategy_eval.db` → `signal_outcomes` (eval ledger) | **VIEW** (derived). Auto-disable tracking only; never quoted as PnL. | `record_signal` on filled execution with broker ticket (`autonomous.py` `_make_decision` ticket resolution; ticket 0 = skip). `record_outcome` per MT5 close via `journal_sync`. Unmatched closes: `WARNING + ticket id`, no crash. Empty/whitespace/`None` strategy → `"ensemble"` fallback (same convention as `autonomous.py` `trigger_strategy` default, verified). | `strategy`, `symbol`, `ticket` (join key → `trades.ticket`), `entry_price`, `exit_price`, `pnl`, `outcome`, `opened_at`, `closed_at` |
| 3 | `TradeHistory.add_event` | `data/trade_history.db` → `trade_events` | **VIEW** (diagnostic log). Signal/candle diagnostics; never PnL truth. | Candle-close / signal events (`candle_scheduler.py`). `pnl` column here is informational only. | `symbol`, `timeframe`, `signal`, `confidence`, `traded`, `notified`, `regime`, `strategy`, `entry_price`, `sl`, `tp`, `pnl` (info only), `timestamp`. No ticket key — cannot join to canonical. |
| 4a | `live_engine` (`_open_position` / `_close_position` / `_partial_exit` / `_sync_broker_positions`) | `data/qna_live.db` → `positions`, `trades`, `signals`, `portfolio` | **DEPRECATED for PnL.** Legacy educational/paper loop ledger. Do not read for realized PnL; do not extend. | Position open after confirmed fill; close/partial inserts computed as `(exit-entry)*qty` locally (not broker-settled). | `symbol`, `side`, `entry_price`, `exit_price`, `quantity`, `entry_time`, `exit_time`, `pnl` (local calc), `strategy`. No ticket key — cannot join to canonical. |
| 4b | `account_ledger.record_account` / `increment_trade_count` | `data/account_ledger.json` | **VIEW** (account registry, not trades). Which MT5 accounts ever connected. | MT5 connect (`builder.py`); trade-count bump per fill. | `login` (key), `server`, `name`, `first_seen`, `last_seen`, `trades` (count only, no amounts) |
| — | `state_writer` (`state.json`, `pnl.csv`) | `paper_state/` | **VIEW** (dashboard snapshot). Guarded by canonical: `total_value` floored to journal `SUM(pnl)`; `assert_reconciled` fails open only on drift ≥ $1. | Engine snapshot writes. | `total_value`, `daily_pnl`, `weekly_pnl` (mirror, not source) |

## Join keys

- Cross-store trade join key: **`ticket`** (`trades.ticket` ⟷ `signal_outcomes.ticket` ⟷ `signal_context.ticket`).
- `trade_history.db` and `qna_live.db` carry **no ticket** → they cannot be joined to canonical and must never be used to confirm/deny a fill or a PnL figure.

## Rule for new code (exactly one)

- Realized PnL enters the system at **exactly one** place: `journal_sync.sync_mt5_deals` → `qna_trade_journal.db.trades`.
- Signal intent goes to **exactly one** intent path: `record_signal_context` (+ `StrategyEvaluator.record_signal` for the eval ledger).
- New code **MUST NOT** write `pnl` into `trade_history.db`, `qna_live.db`, `account_ledger.json`, or `paper_state/` as a source of truth. Those are views; writes there are display/diagnostic only.
- Fail-closed: unknown attribution stays `"unknown"` (never invent a strategy); empty strategy normalizes to `"ensemble"`; unmatched `record_outcome` warns with ticket id and never crashes.
