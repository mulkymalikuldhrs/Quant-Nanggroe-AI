"""
Autonomous Self-Loop API Routes
Exposes self-loop control and monitoring endpoints
"""
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])

# Global orchestrator instance
_orchestrator = None


def get_orchestrator():
    """Lazy-load the orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        from quant_nanggroe.engine.autonomous_self_loop import AutonomousSelfLoopOrchestrator
        _orchestrator = AutonomousSelfLoopOrchestrator()
    return _orchestrator


class StartRequest(BaseModel):
    evaluation_interval_minutes: int = 30
    evolution_interval_hours: int = 6
    validation_interval_hours: int = 12
    min_trades_for_evaluation: int = 10
    max_strategies_to_evolve: int = 5
    capital_allocation_pct: float = 0.8


@router.post("/start")
async def start_autonomous_loop(request: StartRequest) -> Dict[str, Any]:
    """Start the autonomous self-loop"""
    try:
        orchestrator = get_orchestrator()
        
        # Update configuration
        orchestrator.evaluation_interval = __import__("datetime").timedelta(
            minutes=request.evaluation_interval_minutes
        )
        orchestrator.evolution_interval = __import__("datetime").timedelta(
            hours=request.evolution_interval_hours
        )
        orchestrator.validation_interval = __import__("datetime").timedelta(
            hours=request.validation_interval_hours
        )
        orchestrator.min_trades = request.min_trades_for_evaluation
        orchestrator.max_evolve = request.max_strategies_to_evolve
        orchestrator.capital_pct = request.capital_allocation_pct
        
        # Start the loop
        await orchestrator.start()
        
        return {
            "status": "started",
            "message": "Autonomous self-loop started successfully",
            "config": {
                "evaluation_interval_minutes": request.evaluation_interval_minutes,
                "evolution_interval_hours": request.evolution_interval_hours,
                "validation_interval_hours": request.validation_interval_hours,
                "min_trades_for_evaluation": request.min_trades_for_evaluation,
                "max_strategies_to_evolve": request.max_strategies_to_evolve,
                "capital_allocation_pct": request.capital_allocation_pct,
            }
        }
    except Exception as e:
        logger.error(f"Failed to start autonomous loop: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_autonomous_loop() -> Dict[str, Any]:
    """Stop the autonomous self-loop"""
    try:
        orchestrator = get_orchestrator()
        await orchestrator.stop()
        return {
            "status": "stopped",
            "message": "Autonomous self-loop stopped successfully"
        }
    except Exception as e:
        logger.error(f"Failed to stop autonomous loop: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_autonomous_status() -> Dict[str, Any]:
    """Get current autonomous self-loop status"""
    try:
        orchestrator = get_orchestrator()
        return orchestrator.get_status()
    except Exception as e:
        logger.error(f"Failed to get autonomous status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/self-awareness")
async def get_self_awareness() -> Dict[str, Any]:
    """Get self-awareness reflection"""
    try:
        orchestrator = get_orchestrator()
        reflection = orchestrator.get_self_awareness()
        if reflection:
            return {
                "reflection": reflection,
                "timestamp": reflection.get("timestamp"),
            }
        else:
            return {
                "reflection": None,
                "message": "Self-awareness module not available"
            }
    except Exception as e:
        logger.error(f"Failed to get self-awareness: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate")
async def trigger_evaluation() -> Dict[str, Any]:
    """Manually trigger performance evaluation"""
    try:
        orchestrator = get_orchestrator()
        await orchestrator._evaluate_performance()
        return {
            "status": "evaluated",
            "message": "Performance evaluation triggered successfully"
        }
    except Exception as e:
        logger.error(f"Failed to trigger evaluation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolve")
async def trigger_evolution() -> Dict[str, Any]:
    """Manually trigger strategy evolution"""
    try:
        orchestrator = get_orchestrator()
        await orchestrator._evolve_strategies()
        return {
            "status": "evolved",
            "message": "Strategy evolution triggered successfully"
        }
    except Exception as e:
        logger.error(f"Failed to trigger evolution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def trigger_validation() -> Dict[str, Any]:
    """Manually trigger strategy validation"""
    try:
        orchestrator = get_orchestrator()
        await orchestrator._validate_strategies()
        return {
            "status": "validated",
            "message": "Strategy validation triggered successfully"
        }
    except Exception as e:
        logger.error(f"Failed to trigger validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reallocate")
async def trigger_reallocation() -> Dict[str, Any]:
    """Manually trigger capital reallocation"""
    try:
        orchestrator = get_orchestrator()
        await orchestrator._reallocate_capital()
        return {
            "status": "reallocated",
            "message": "Capital reallocation triggered successfully"
        }
    except Exception as e:
        logger.error(f"Failed to trigger reallocation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
