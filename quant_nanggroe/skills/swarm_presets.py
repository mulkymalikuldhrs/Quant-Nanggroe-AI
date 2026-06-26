"""Vibe-Trading-inspired swarm preset configurations."""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class SwarmPreset:
    name: str
    description: str
    skills: List[str]
    config: Dict[str, Any] = field(default_factory=dict)


SWARM_PRESETS = {
    "momentum_scalper": SwarmPreset(
        name="Momentum Scalper",
        description="Fast momentum trading with RSI + volume confirmation",
        skills=["rsi_analysis", "volume_analysis", "risk_calculator"],
        config={"timeframe": "1m", "min_confidence": 0.7},
    ),
    "trend_follower": SwarmPreset(
        name="Trend Follower",
        description="Medium-term trend following with SMA + MACD",
        skills=["sma_crossover", "macd_analysis", "trend_analysis", "risk_calculator"],
        config={"timeframe": "1h", "min_confidence": 0.6},
    ),
    "mean_reversion": SwarmPreset(
        name="Mean Reversion",
        description="Mean reversion with Bollinger Bands + RSI",
        skills=["bollinger_bands", "rsi_analysis", "support_resistance", "risk_calculator"],
        config={"timeframe": "15m", "min_confidence": 0.8},
    ),
    "gold_strategy": SwarmPreset(
        name="Gold Strategy",
        description="XAUUSD specific with volatility + sentiment",
        skills=["volatility_analysis", "support_resistance", "sentiment_score"],
        config={"asset": "XAUUSD", "timeframe": "1h", "min_confidence": 0.65},
    ),
}


def get_preset(name: str) -> SwarmPreset:
    if name not in SWARM_PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(SWARM_PRESETS.keys())}")
    return SWARM_PRESETS[name]


def list_presets() -> List[str]:
    return list(SWARM_PRESETS.keys())
