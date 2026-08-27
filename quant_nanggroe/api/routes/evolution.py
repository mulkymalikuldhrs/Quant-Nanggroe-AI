"""Evolution API endpoint — serve evolution loop data to dashboard."""
from fastapi import APIRouter, Query

from quant_nanggroe.engine.evolution.evolution_config import EvolutionConfig
from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal

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


@router.post("/config")
def update_config(key: str, value: str):
    config = EvolutionConfig()
    config.set(key, value)
    return {"success": True}