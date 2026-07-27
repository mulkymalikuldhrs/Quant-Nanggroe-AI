"""SQLite persistence for backtest results — replaces in-memory-only storage."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from quant_nanggroe.qna_config import DATA_DIR

DB_PATH = DATA_DIR / "backtest_results.db"

def _get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    _init_db(db)
    return db

def _init_db(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            strategy_type TEXT,
            symbol TEXT,
            timeframe TEXT,
            start_date TEXT,
            end_date TEXT,
            parameters TEXT,
            metrics TEXT,
            equity_curve TEXT,
            trades TEXT,
            status TEXT DEFAULT 'completed',
            version INTEGER DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_backtest_strategy ON backtest_runs(strategy_name);
        CREATE INDEX IF NOT EXISTS idx_backtest_created ON backtest_runs(created_at);
    """)

def save_run(run_data: Dict[str, Any]) -> str:
    run_id = str(uuid.uuid4())[:8]
    db = _get_db()
    db.execute("""
        INSERT INTO backtest_runs (id, created_at, strategy_name, strategy_type, symbol,
            timeframe, start_date, end_date, parameters, metrics, equity_curve, trades)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        datetime.now(timezone.utc).isoformat(),
        run_data.get("strategy_name", "unknown"),
        run_data.get("strategy_type", ""),
        run_data.get("symbol", ""),
        run_data.get("timeframe", ""),
        run_data.get("start_date", ""),
        run_data.get("end_date", ""),
        json.dumps(run_data.get("parameters", {}), default=str),
        json.dumps(run_data.get("metrics", {}), default=str),
        json.dumps(run_data.get("equity_curve", []), default=str),
        json.dumps(run_data.get("trades", []), default=str),
    ))
    db.commit()
    return run_id

def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    db = _get_db()
    rows = db.execute(
        "SELECT id, created_at, strategy_name, strategy_type, symbol, metrics, status "
        "FROM backtest_runs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["metrics"] = json.loads(d["metrics"]) if isinstance(d["metrics"], str) else {}
        result.append(d)
    return result

def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    row = db.execute("SELECT * FROM backtest_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for field in ["parameters", "metrics", "equity_curve", "trades"]:
        if isinstance(d.get(field), str):
            d[field] = json.loads(d[field])
    return d

def delete_run(run_id: str) -> bool:
    db = _get_db()
    c = db.execute("DELETE FROM backtest_runs WHERE id = ?", (run_id,))
    db.commit()
    return c.rowcount > 0

def get_best_by_sharpe(min_trades: int = 10, limit: int = 20) -> List[Dict[str, Any]]:
    db = _get_db()
    rows = db.execute(
        "SELECT id, created_at, strategy_name, strategy_type, symbol, metrics "
        "FROM backtest_runs ORDER BY created_at DESC"
    ).fetchall()
    scored = []
    for r in rows:
        m = json.loads(r["metrics"]) if isinstance(r["metrics"], str) else {}
        sharpe = m.get("sharpe", m.get("sharpe_ratio", 0))
        trades = m.get("total_trades", m.get("num_trades", 0))
        if isinstance(sharpe, (int, float)) and trades >= min_trades:
            scored.append((sharpe, dict(r), m))
    scored.sort(key=lambda x: x[0], reverse=True)
    result = []
    for s, r, m in scored[:limit]:
        r["metrics"] = m
        result.append(r)
    return result
