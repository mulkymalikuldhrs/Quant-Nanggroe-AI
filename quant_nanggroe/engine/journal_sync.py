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
    con.commit()
    con.close()


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



def sync_mt5_deals(backfill_days: int = 0) -> Dict[str, Any]:
    """Pull closed deals from active MT5 terminal into the trade journal."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        logger.error("MetaTrader5 lib missing - cannot sync")
        return {"synced": 0, "inserted": 0, "updated": 0, "total_pnl": 0.0,
                "errors": ["MetaTrader5 not installed"]}

    # Initialize MT5 — attach to already-logged-in terminal session
    if not mt5.initialize():
        err = mt5.last_error()
        logger.error("MT5 initialize failed: %s", err)
        return {"synced": 0, "inserted": 0, "updated": 0, "total_pnl": 0.0,
                "errors": [f"MT5 init failed: {err}"]}
    acct = mt5.account_info()
    if acct:
        logger.info("Journal sync on account %s (%s)", acct.login, acct.server)

    db_path = _get_db()
    _ensure_schema(db_path)
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

            if existing:
                if existing["pnl"] is None or existing["pnl"] == 0.0:
                    con.execute(
                        """UPDATE trades SET close_time=?, exit_price=?,
                           pnl=?, outcome=?, close_reason=?, hit_type=?
                           WHERE ticket=?""",
                        (close_ts, exit_price, pnl, outcome, close_reason, hit_type, ticket))
                    updated += 1
            else:
                con.execute(
                    """INSERT INTO trades (ticket, strategy, symbol, side, entry,
                       sl, tp, confidence, open_time, close_time, exit_price,
                       pnl, outcome, comment, hypothesis, setup_ctx,
                       close_reason, hit_type, market_ctx, tf_category)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ticket, strategy, symbol, side, entry_price,
                     None, None, 0.0, open_ts, close_ts, exit_price,
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
