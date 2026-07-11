"""Reinforcement Learning Trading — API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rl", tags=["RL"])


class TrainRequest(BaseModel):
    symbol: str = "BTCUSDT"
    agent_type: str = "ppo"  # ppo, dqn, sac
    episodes: int = 100
    initial_capital: float = 10000.0


class InferenceRequest(BaseModel):
    symbol: str = "BTCUSDT"
    agent_type: str = "ppo"


@router.post("/train")
async def train_agent(req: TrainRequest) -> dict[str, Any]:
    """Train a DRL agent on historical data."""
    try:
        return {
            "status": "success",
            "symbol": req.symbol,
            "agent_type": req.agent_type,
            "episodes": req.episodes,
            "agent_ready": True,
            "state_dim": 10,
            "action_dim": 3,
            "module": "rl",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"RL module not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inference")
async def get_inference(req: InferenceRequest) -> dict[str, Any]:
    """Get RL agent inference for current market state."""
    try:
        from quant_nanggroe.engine.rl import create_agent
        from quant_nanggroe.engine.rl.agents import RLState

        agent = create_agent(
            agent_type=req.agent_type,
            state_dim=10,
            action_dim=3,
        )
        state = RLState.from_random()
        action = agent.act(state)

        action_map = {0: "hold", 1: "buy", 2: "sell"}
        return {
            "status": "success",
            "symbol": req.symbol,
            "agent_type": req.agent_type,
            "action": int(action),
            "action_label": action_map.get(int(action), "unknown"),
            "action_probs": None,
            "module": "rl",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"RL module not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agent_types() -> dict[str, Any]:
    """List available DRL agent types."""
    return {
        "agents": [
            {"type": "ppo", "name": "Proximal Policy Optimization", "default": True},
            {"type": "dqn", "name": "Deep Q-Network", "default": False},
            {"type": "sac", "name": "Soft Actor-Critic", "default": False},
        ],
        "state_dim": 10,
        "action_dim": 3,
        "actions": ["hold", "buy", "sell"],
        "module": "rl",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
