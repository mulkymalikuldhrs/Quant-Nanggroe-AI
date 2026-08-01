"""Evolution API endpoint — serve evolution loop data to dashboard."""
from fastapi import APIRouter, Query
from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal
from quant_nanggroe.engine.evolution.evolution_config import EvolutionConfig

router = APIRouter(prefix="/api/evolution", tags=["evolution"])


@router.get("/status")
def get_evolution_status():
    journal = EvolutionJournal()
    stats = journal.get_summary_stats()
    return {"success": True, "data": stats}


@router.get("/strategies")
def get_strategy_performance(limit: int = Query(50, ge=1, le=500)):
    journal = EvolutionJournal()
    snapshots = journal.get_latest_snapshots(limit)
    return {"success": True, "data": snapshots}


@router.get("/trades")
def get_recent_trades(limit: int = Query(20, ge=1, le=500)):
    journal = EvolutionJournal()
    trades = journal.all_trades(limit)
    return {"success": True, "data": trades}


@router.get("/config")
def get_config():
    config = EvolutionConfig()
    return {"success": True, "data": config.data}


@router.get("/timeline")
def get_evolution_timeline(limit: int = Query(500, ge=1, le=5000)):
    """PnL attribution timeline.

    Reads the append-only evolution journal (closed_trades table) and
    returns the realized PnL per trade in chronological order so the
    dashboard can render an evolution PnL attribution timeline.
    """
    journal = EvolutionJournal()
    cur = journal._conn.execute(
        "SELECT id, timestamp, symbol, strategy, direction, pnl, pnl_pct, hold_hours "
        "FROM closed_trades ORDER BY id ASC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    timeline = [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "symbol": r["symbol"],
            "strategy": r["strategy"],
            "direction": r["direction"],
            "pnl": r["pnl"],
            "pnl_pct": r["pnl_pct"],
            "hold_hours": r["hold_hours"],
        }
        for r in rows
    ]
    return {"success": True, "data": timeline}


@router.post("/config")
def update_config(key: str, value: str):
    config = EvolutionConfig()
    config.set(key, value)
    return {"success": True}