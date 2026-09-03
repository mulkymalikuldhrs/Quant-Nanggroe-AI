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


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/train")
async def train_agent(req: TrainRequest) -> dict[str, Any]:
    """Train a DRL agent on synthetic episodes. Returns real loss metrics.

    ponytail: the engine RL agents are numpy-only policy nets. We run a short
    supervised warmup over random rollouts so the response reflects an actual
    update step (real loss), not a fabricated success. No live market replay
    exists for RL, so no historical P&L is claimed.
    """
    try:
        import numpy as np

        from quant_nanggroe.engine.rl import create_agent
        from quant_nanggroe.engine.rl.agents import Experience, RLState

        agent = create_agent(
            name=req.agent_type,
            state_dim=10,
            action_dim=3,
        )

        rng = np.random.default_rng(42)
        losses: list[float] = []
        for _ in range(req.episodes):
            state = RLState.from_random(state_dim=10)
            action = agent.act(state)
            # ponytail: shaped reward to give the update a gradient to chase.
            reward = float(rng.random() - 0.5) - (0.1 if action == 0 else 0.0)
            next_state = RLState.from_random(state_dim=10)
            exp = Experience(
                state=state.to_array(),
                action=action,
                reward=reward,
                next_state=next_state.to_array(),
                done=False,
            )
            metrics = agent.update([exp])
            if metrics:
                # ponytail: agents report different loss-key names
                # (ppo: policy_loss+value_loss, dqn: q_loss) — sum *_loss.
                step_loss = sum(v for k, v in metrics.items() if k.endswith("_loss"))
                losses.append(float(step_loss))

        avg_loss = round(float(np.mean(losses)), 6) if losses else None
        return {
            "status": "success",
            "symbol": req.symbol,
            "agent_type": req.agent_type,
            "episodes": req.episodes,
            "state_dim": 10,
            "action_dim": 3,
            "avg_loss": avg_loss,
            "module": "rl",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except (ValueError, ImportError) as e:
        raise HTTPException(status_code=400, detail=f"RL agent unavailable: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/inference")
async def get_inference(req: InferenceRequest) -> dict[str, Any]:
    """Get RL agent inference for current market state."""
    try:
        from quant_nanggroe.engine.rl import create_agent
        from quant_nanggroe.engine.rl.agents import RLState

        agent = create_agent(
            name=req.agent_type,
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


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
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
