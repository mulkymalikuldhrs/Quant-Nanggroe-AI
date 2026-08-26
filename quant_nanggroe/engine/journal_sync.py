"""MT5 -> Journal Sync - closes the feedback loop."""
from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("QNA.JournalSync")
_JOURNAL_DB = Path(__file__).resolve().parents[1] / "data" / "qna_trade_journal.db"
_LAST_SYNC_KEY = "last_sync_ts"
_DEAL_TYPE_BUY = 0
_DEAL_ENTRY_IN = 0
_DEAL_ENTRY_OUT = 1
_DEAL_ENTRY_INOUT = 2
_DEAL_ENTRY_OUT_BY = 3

_MAGIC_MAP = {888888: "ensemble"}
_KNOWN = [
    "aroon", "smc", "ensemble", "amdx", "kaufman", "mean_rev",
    "multi_timeframe", "trend_follow", "momentum", "scalp",
    "day", "swing", "trailing_stop", "ict", "algebra",
]


def _get_db() -> Path:
    p = Path(__file__).resolve().parents[1] / "data" / "qna_trade_journal.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _ensure_schema(db_path):
    con = sqlite3.connect(str(db_path))
    con.execute(
        "CREATE TABLE IF NOT EXISTS _sync_meta"
        " (key TEXT PRIMARY KEY, value TEXT)")
    con.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket INTEGER UNIQUE,
            strategy TEXT DEFAULT 'unknown',
            symbol TEXT NOT NULL,
            side TEXT DEFAULT 'buy',
            entry REAL DEFAULT 0.0,
            sl REAL,
            tp REAL,
            confidence REAL DEFAULT 0.0,
            open_time INTEGER,
            close_time INTEGER,
            exit_price REAL DEFAULT 0.0,
            pnl REAL DEFAULT 0.0,
            outcome TEXT DEFAULT 'breakeven',
            comment TEXT DEFAULT '',
            hypothesis TEXT DEFAULT '',
            setup_ctx TEXT DEFAULT '',
            close_reason TEXT DEFAULT '',
            hit_type TEXT DEFAULT '',
            market_ctx TEXT DEFAULT '',
            tf_category TEXT DEFAULT 'intraday'
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_trades_ticket ON trades(ticket)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time)")
    # Signal context: stores sl/tp/confidence from pipeline, linked to deals via ticket
    con.execute("""
        CREATE TABLE IF NOT EXISTS signal_context (
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
            hit_type TEXT DEFAULT ''
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_sigctx_symbol ON signal_context(symbol)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_sigctx_ticket ON signal_context(ticket)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_sigctx_timestamp ON signal_context(timestamp)")
    con.commit()
    con.close()


def record_signal_context(symbol: str, strategy: str, entry_price: float,
                          sl: float, tp: float, confidence: float,
                          atr: float = 0.0, lot_size: float = 0.01) -> None:
    """Record signal context (sl/tp/confidence) for later linking to MT5 deals."""
    try:
        con = sqlite3.connect(str(_get_db()))
        con.execute(
            """INSERT INTO signal_context
               (symbol, strategy, entry_price, sl, tp, confidence, atr, lot_size, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (symbol, strategy, entry_price, sl, tp, confidence, atr, lot_size,
             datetime.now(timezone.utc).isoformat()))
        con.commit()
        con.close()
    except Exception as exc:
        logger.warning("record_signal_context failed: %s", exc)


def link_signal_to_ticket(symbol: str, entry_price: float, ticket: int,
                          tolerance: float = 0.001) -> bool:
    """Link an unfilled signal_context to an MT5 deal ticket by symbol+price match."""
    try:
        con = sqlite3.connect(str(_get_db()))
        row = con.execute(
            """SELECT id FROM signal_context
               WHERE symbol=? AND ticket IS NULL
                 AND ABS(entry_price - ?) < ?
               ORDER BY timestamp DESC LIMIT 1""",
            (symbol, entry_price, tolerance)).fetchone()
        if row:
            con.execute("UPDATE signal_context SET ticket=? WHERE id=?", (ticket, row[0]))
            con.commit()
            con.close()
            return True
        con.close()
    except Exception:
        pass
    return False


def get_signal_context_by_ticket(ticket: int) -> dict | None:
    """Retrieve signal context for a given MT5 ticket."""
    try:
        con = sqlite3.connect(str(_get_db()))
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT * FROM signal_context WHERE ticket=?", (ticket,)).fetchone()
        con.close()
        return dict(row) if row else None
    except Exception:
        return None


def _read_last_sync(con):
    try:
        r = con.execute(
            "SELECT value FROM _sync_meta WHERE key=?",
            (_LAST_SYNC_KEY,)).fetchone()
        return float(r[0]) if r else 0.0
    except Exception:
        return 0.0


def _write_last_sync(con, ts):
    con.execute(
        "INSERT OR REPLACE INTO _sync_meta VALUES (?,?)",
        (_LAST_SYNC_KEY, str(ts)))
    con.commit()


def _classify_outcome(pnl):
    if pnl > 0:
        return "win"
    if pnl < 0:
        return "loss"
    return "breakeven"


def _detect_hit_type(close_reason, pnl):
    cr = close_reason.lower()
    if "take_profit" in cr or "[tp]" in cr:
        return "tp"
    if "stop_loss" in cr or "[sl]" in cr:
        return "sl"
    if "trailing" in cr:
        return "trail"
    if pnl > 0:
        return "tp"
    if pnl < 0:
        return "sl"
    return "unknown"


def _attribute_strategy(magic, comment, symbol):
    if magic in _MAGIC_MAP:
        return _MAGIC_MAP[magic]
    if comment and len(comment) > 2:
        c = comment.strip().lower()
        for k in _KNOWN:
            if k in c:
                return k
    try:
        from quant_nanggroe.engine.strategy_allocation import (
            admitted_for_symbol,
        )
        admitted = admitted_for_symbol(symbol)
        if admitted and len(admitted) == 1:
            return admitted[0]
    except Exception:
        pass
    return "unknown"



def sync_mt5_deals(backfill_days: int = 0, deals=None) -> Dict[str, Any]:
    """Pull closed deals from active MT5 terminal into the trade journal.

    v8.0.11 FIX: Accept optional ``deals`` parameter to avoid calling
    MT5 C-API from daemon threads (not thread-safe). Caller in
    CandleScheduler's asyncio loop fetches deals on the main thread
    and passes them here.

    Args:
        backfill_days: If >0, override last-sync and look back this many days.
        deals: Pre-fetched MT5 deal objects. If None, fetch via mt5 module.
    """
    db_path = _get_db()
    _ensure_schema(db_path)

    if deals is None:
        try:
            import MetaTrader5 as mt5
        except ImportError:
            logger.error("MetaTrader5 lib missing - cannot sync")
            return {"synced": 0, "inserted": 0, "updated": 0, "total_pnl": 0.0,
                    "errors": ["MetaTrader5 not installed"]}

        if not mt5.initialize():
            err = mt5.last_error()
            logger.error("MT5 initialize failed: %s", err)
            return {"synced": 0, "inserted": 0, "updated": 0, "total_pnl": 0.0,
                    "errors": [f"MT5 init failed: {err}"]}
        acct = mt5.account_info()
        if acct:
            logger.info("Journal sync on account %s (%s)", acct.login, acct.server)

        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row

        now = time.time()
        last_sync = _read_last_sync(con)
        if backfill_days > 0:
            from_dt = datetime.now(timezone.utc) - timedelta(days=backfill_days)
        elif last_sync > 0:
            from_dt = datetime.fromtimestamp(last_sync, tz=timezone.utc) - timedelta(hours=1)
        else:
            from_dt = datetime.now(timezone.utc) - timedelta(days=365)

        to_dt = datetime.now(timezone.utc)

        try:
            deals = mt5.history_deals_get(from_dt, to_dt)
        except Exception as e:
            logger.error("history_deals_get failed: %s", e)
            con.close()
            return {"synced": 0, "inserted": 0, "updated": 0, "total_pnl": 0.0,
                    "errors": [str(e)]}

        if not deals:
            logger.info("No new MT5 deals found (%s to %s)", from_dt.date(), to_dt.date())
            _write_last_sync(con, now)
            con.close()
            return {"synced": 0, "inserted": 0, "updated": 0, "total_pnl": 0.0,
                    "errors": []}
    else:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        now = time.time()
        logger.info("Journal sync using %d pre-fetched deals", len(deals))

    # Group by position_id: pair open+close
    position_map = {}
    for d in deals:
        pid = getattr(d, "position_id", 0) or getattr(d, "order", 0)
        if pid:
            position_map.setdefault(pid, []).append(d)

    inserted = 0
    updated = 0
    total_pnl = 0.0
    errors = []

    for pid, pos_deals in position_map.items():
        try:
            opens = [d for d in pos_deals if d.entry == _DEAL_ENTRY_IN]
            closes = [d for d in pos_deals if d.entry in (_DEAL_ENTRY_OUT, _DEAL_ENTRY_INOUT, _DEAL_ENTRY_OUT_BY)]
            if not opens:
                continue
            open_deal = opens[0]
            close_deal = closes[-1] if closes else None

            ticket = close_deal.ticket if close_deal else open_deal.ticket
            symbol = open_deal.symbol
            side = "buy" if open_deal.type == _DEAL_TYPE_BUY else "sell"
            entry_price = open_deal.price
            open_ts = open_deal.time
            magic = getattr(open_deal, "magic", 888888)
            comment = getattr(open_deal, "comment", "") or ""

            if close_deal:
                exit_price = close_deal.price
                close_ts = close_deal.time
                pnl = (getattr(close_deal, "profit", 0.0)
                       + getattr(close_deal, "commission", 0.0)
                       + getattr(close_deal, "swap", 0.0))
                close_reason = getattr(close_deal, "comment", "") or ""
            else:
                exit_price = 0.0
                close_ts = None
                pnl = 0.0
                close_reason = ""

            total_pnl += pnl
            outcome = _classify_outcome(pnl)
            hit_type = _detect_hit_type(close_reason, pnl) if close_deal else ""
            strategy = _attribute_strategy(magic, comment, symbol)

            existing = con.execute(
                "SELECT ticket, pnl FROM trades WHERE ticket=?", (ticket,)
            ).fetchone()

            # Look up signal context (sl/tp/confidence) from pipeline
            sig_ctx = None
            try:
                sig_row = con.execute(
                    """SELECT sl, tp, confidence, atr, lot_size FROM signal_context
                       WHERE symbol=? AND ticket IS NULL
                         AND ABS(entry_price - ?) < 0.002
                       ORDER BY timestamp DESC LIMIT 1""",
                    (symbol, entry_price)).fetchone()
                if sig_row:
                    sig_ctx = {"sl": sig_row[0], "tp": sig_row[1],
                               "confidence": sig_row[2], "atr": sig_row[3],
                               "lot_size": sig_row[4]}
                    # Link ticket back to signal context
                    con.execute(
                        "UPDATE signal_context SET ticket=?, filled=1, pnl=?, outcome=?, hit_type=? WHERE rowid=?",
                        (ticket, pnl, outcome, hit_type, sig_row.rowid if hasattr(sig_row, 'rowid') else None))
            except Exception:
                pass

            _sl = sig_ctx["sl"] if sig_ctx else None
            _tp = sig_ctx["tp"] if sig_ctx else None
            _conf = sig_ctx["confidence"] if sig_ctx else 0.0

            if existing:
                if existing["pnl"] is None or existing["pnl"] == 0.0:
                    con.execute(
                        """UPDATE trades SET close_time=?, exit_price=?,
                           pnl=?, outcome=?, close_reason=?, hit_type=?,
                           sl=?, tp=?, confidence=?
                           WHERE ticket=?""",
                        (close_ts, exit_price, pnl, outcome, close_reason, hit_type,
                         _sl, _tp, _conf, ticket))
                    updated += 1
            else:
                con.execute(
                    """INSERT INTO trades (ticket, strategy, symbol, side, entry,
                       sl, tp, confidence, open_time, close_time, exit_price,
                       pnl, outcome, comment, hypothesis, setup_ctx,
                       close_reason, hit_type, market_ctx, tf_category)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ticket, strategy, symbol, side, entry_price,
                     _sl, _tp, _conf, open_ts, close_ts, exit_price,
                     pnl, outcome, comment, f"magic={magic}", "",
                     close_reason, hit_type, "", "intraday"))
                inserted += 1

        except Exception as exc:
            errors.append(f"deal {pid}: {exc}")
            logger.warning("Deal %s sync error: %s", pid, exc)

    _write_last_sync(con, now)
    con.commit()

    # summary stats
    total_count = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    net_pnl = con.execute("SELECT ROUND(SUM(pnl),2) FROM trades").fetchone()[0]
    con.close()

    result = {
        "synced": len(position_map),
        "inserted": inserted,
        "updated": updated,
        "total_pnl": round(total_pnl, 2),
        "journal_total_trades": total_count,
        "journal_net_pnl": round(net_pnl, 2),
        "errors": errors,
    }
    logger.info(
        "Journal sync: %d positions, +%d new, ~%d updated, "
        "session PnL=%.2f, journal total=%d trades PnL=%.2f",
        len(position_map), inserted, updated, total_pnl, total_count, net_pnl,
    )
    return result


def get_journal_stats() -> Dict[str, Any]:
    """Quick journal health check for dashboard /health endpoint."""
    db_path = _get_db()
    if not db_path.exists():
        return {"exists": False}
    con = sqlite3.connect(str(db_path))
    try:
        total = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        net_pnl = con.execute("SELECT ROUND(SUM(pnl),2) FROM trades").fetchone()[0]
        wins = con.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0").fetchone()[0]
        losses = con.execute("SELECT COUNT(*) FROM trades WHERE pnl < 0").fetchone()[0]
        unknown_attr = con.execute(
            "SELECT COUNT(*) FROM trades WHERE strategy IN ('unknown','ensemble')").fetchone()[0]
        last_sync = _read_last_sync(con)
        return {
            "exists": True, "total_trades": total, "net_pnl": round(net_pnl, 2),
            "wins": wins, "losses": losses,
            "win_rate": round(wins / max(total, 1), 4),
            "unknown_attribution": unknown_attr,
            "last_sync_ts": last_sync,
        }
    finally:
        con.close()


async def async_sync_mt5_deals(backfill_days: int = 0) -> Dict[str, Any]:
    """Async wrapper: fetch deals via broker's MT5 handle (thread-safe),
    then pass to sync_mt5_deals for DB persistence.

    v8.0.11: Runs inside CandleScheduler's asyncio event loop where MT5
    is already initialized on the scheduler thread.
    """
    try:
        from datetime import datetime as _dt, timezone as _tz, timedelta as _td
        import MetaTrader5 as _mt5
        now = _dt.now(_tz.utc)
        from_dt = (now - _td(days=backfill_days)) if backfill_days > 0 else (now - _td(days=365))
        deals = _mt5.history_deals_get(from_dt, now)
        if deals is None:
            deals = []
    except Exception as exc:
        logger.error("async_sync: MT5 fetch failed: %s", exc)
        return {"synced": 0, "inserted": 0, "updated": 0, "total_pnl": 0.0,
                "errors": [str(exc)]}

    return sync_mt5_deals(backfill_days=backfill_days, deals=deals)
