"""
QNA Hedge Fund — SQLite Trade Journal & Production Launcher.

Menggantikan CSV logging dengan SQLite untuk:
- Per-strategy P&L tracking
- Trade history queryable
- Daily/weekly/monthly aggregation
- Position management
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("E:/trading/data/qna_journal.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,        -- open_buy, open_sell, close_buy, close_sell, paper_buy, paper_sell
    volume REAL NOT NULL,
    price REAL NOT NULL,
    sl REAL,
    tp REAL,
    atr REAL,
    confidence REAL DEFAULT 0.5,
    signal TEXT,                 -- JSON: list of provider sources
    pnl REAL DEFAULT 0,
    pnl_pips REAL DEFAULT 0,
    balance_before REAL,
    balance_after REAL,
    strategy TEXT DEFAULT 'qna_hedge_fund',
    mode TEXT DEFAULT 'paper',   -- paper, demo, real
    exit_time TEXT,
    exit_price REAL,
    exit_reason TEXT,
    tags TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS daily_summary (
    date TEXT PRIMARY KEY,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    total_pnl_pips REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    sharpe_ratio REAL DEFAULT 0,
    max_dd REAL DEFAULT 0,
    balance_start REAL,
    balance_end REAL,
    best_trade REAL DEFAULT 0,
    worst_trade REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS signals_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    symbol TEXT NOT NULL,
    providers TEXT,               -- JSON array
    buy_conf REAL DEFAULT 0,
    sell_conf REAL DEFAULT 0,
    total_conf REAL DEFAULT 0,
    decision TEXT,               -- buy/sell/neutral
    dxy TEXT,
    executed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def get_db() -> sqlite3.Connection:
    """Get database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if not exist."""
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"✅ Journal database ready: {DB_PATH}")


def log_trade(
    symbol: str,
    action: str,
    volume: float,
    price: float,
    sl: float = None,
    tp: float = None,
    atr: float = 0.001,
    confidence: float = 0.5,
    signal: list = None,
    balance: float = 1000,
    mode: str = "paper",
    strategy: str = "qna_hedge_fund",
) -> int:
    """Log a trade to SQLite journal."""
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO trades 
           (time, symbol, action, volume, price, sl, tp, atr, confidence, signal, balance_before, mode, strategy)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now().isoformat(),
            symbol,
            action,
            volume,
            price,
            sl,
            tp,
            atr,
            confidence,
            json.dumps(signal or []),
            balance,
            mode,
            strategy,
        ),
    )
    conn.commit()
    trade_id = cursor.lastrowid
    conn.close()
    return trade_id


def get_recent_trades(limit: int = 20) -> list:
    """Get recent trades for reporting."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_pnl(date: str = None) -> dict:
    """Get daily P&L summary."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    row = conn.execute(
        """SELECT 
            COUNT(*) as trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
            SUM(pnl) as total_pnl
           FROM trades 
           WHERE date(time) = ? AND mode != 'paper'""",
        (date,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {"trades": 0, "wins": 0, "losses": 0, "total_pnl": 0}


def run_daily_summary():
    """Auto-generate daily summary."""
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Aggregate today
    conn.execute("""
        INSERT OR REPLACE INTO daily_summary (date, total_trades, winning_trades, losing_trades, total_pnl)
        SELECT 
            date(time) as d,
            COUNT(*),
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END),
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END),
            SUM(pnl)
        FROM trades 
        WHERE date(time) = ?
        GROUP BY d
    """, (today,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    init_db()
    
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        rows = get_recent_trades(10)
        print(f"\n{'='*60}")
        print(f"  QNA HEDGE FUND — JOURNAL")
        print(f"  Database: {DB_PATH}")
        print(f"{'='*60}")
        for r in rows:
            print(f"  {r['action']:12s} {r['symbol']:8s} {r['volume']:.2f} lot @ {r['price']:.5f} | PnL=${r['pnl']:.2f} | {r['mode']}")
