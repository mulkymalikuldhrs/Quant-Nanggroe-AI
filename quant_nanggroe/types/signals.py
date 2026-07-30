"""Signal types for Quant Nanggroe AI.

SINGLE SOURCE OF TRUTH for all signal models across the codebase.

Trading signals are the primary output of analyst and strategist agents.
Each signal carries type, confidence, and supporting evidence.

Canonical — all non-canonical Signal classes across the codebase should
migrate to import from here. See QNA_AGENT_STATE.md for migration status.

Unified field set aggregated from:
  - quant_nanggroe/types/signals.py       (original canonical)
  - quant_nanggroe/pipeline/signal.py     (side, strategy, reason)
  - quant_nanggroe/pipeline/execution.py  (PipelineSignal)
  - quant_nanggroe/agents/state.py        (direction, action, entry_price, indicators, risk_reward_ratio)
  - quant_nanggroe/engine/strategies/base.py (StrategySignal)
  - quant_nanggroe/engine/agentic/voting.py  (bias)
  - quant_nanggroe/engine/agentic/final_decider.py (regime_compatibility)
  - quant_nanggroe/engine/agentic_trading.py   (role)
  - quant_nanggroe/engine/live/adaptive_integration.py (LiveSignal)
  - quant_nanggroe/engine/ml/signal_generator.py (MLSignal)
  - quant_nanggroe/engine/models/signal_generator.py (TradingSignal)
  - quant_nanggroe/core/scoring/fusion_engine.py (ScoredSignal)
  - quant_nanggroe/engine/portfolio/confluence_scorer.py (ConfluenceSignal)
  - quant_nanggroe/engine/kelly/backtest_integration.py (KellySignal)
  - quant_nanggroe/engine_production_bridge.py / _purified.py (Signal)
  - quant_nanggroe/agents/aihf_bridge.py (AIHFSignal)
  - quant_nanggroe/agents/gold_trader.py (GoldSignal)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Trading signal direction."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    EXIT_ALL = "exit_all"


class SignalStrength(str, Enum):
    """Signal confidence/strength classification."""
    WEAK = "weak"          # confidence < 0.3
    MODERATE = "moderate"   # 0.3 <= confidence < 0.6
    STRONG = "strong"       # 0.6 <= confidence < 0.8
    VERY_STRONG = "very_strong"  # confidence >= 0.8


class Signal(BaseModel):
    """
    A trading signal produced by an agent.

    CANONICAL — single source of truth.
    All non-canonical Signal classes should migrate to import this class.

    Signals carry direction, confidence, target price levels,
    and supporting evidence for downstream consumption by the
    risk and execution agents.
    """
    # --- Core identity ---
    id: Optional[str] = None
    symbol: str = Field(..., min_length=1)
    signal_type: SignalType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Signal confidence 0.0-1.0")

    # --- Legacy alias fields (bridges to non-canonical callers) ---
    side: Optional[str] = Field(None, description="Alias for signal_type (\"buy\"/\"sell\"/\"hold\") — legacy, prefer signal_type")
    direction: Optional[str] = Field(None, description="Alias for signal_type — legacy, prefer signal_type")
    bias: Optional[str] = Field(None, description="Alias for signal_type (\"buy\"/\"sell\"/\"neutral\") — legacy, prefer signal_type")
    action: Optional[str] = Field(None, description="Alias for signal_type — legacy, prefer signal_type")

    # --- Strength / classification ---
    strength: Optional[SignalStrength] = None
    composite_score: Optional[float] = Field(None, description="Composite score from FusionEngine")  # fusion_engine.py
    weight: float = Field(1.0, description="Signal weight for voting/aggregation")  # confluence_scorer + debate
    override_aggregator: bool = Field(False, description="Bypass aggregator voting")  # fusion_engine.py

    # --- Price levels ---
    price: Optional[float] = Field(None, gt=0, description="Current price when signal generated")
    entry_price: Optional[float] = Field(None, gt=0, description="Suggested entry price")  # agents/state.py, strategies/base.py
    target_price: Optional[float] = Field(None, gt=0, description="Target price for the signal")
    stop_loss: Optional[float] = Field(None, gt=0, description="Suggested stop-loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Suggested take-profit price")
    risk_reward_ratio: Optional[float] = Field(None, description="Risk:Reward ratio")  # agents/state.py, strategies/base.py

    # --- Context ---
    timeframe: Optional[str] = None
    regime: Optional[str] = Field(None, description="Market regime context")  # kelly/backtest_integration.py
    regime_compatibility: Optional[float] = Field(None, description="Regime compatibility score (0-1)")  # final_decider.py

    # --- Provenance ---
    source_agent: str = Field(..., description="Agent that produced this signal")
    source_agents: List[str] = Field(default_factory=list, description="All contributing agents")  # agents/state.py
    source_strategy: Optional[str] = None
    role: Optional[str] = Field(None, description="Agent role that produced this signal")  # agentic_trading.py
    model_name: Optional[str] = Field(None, description="ML model name")  # ml/signal_generator.py

    # --- Reasoning / evidence ---
    reasoning: str = Field(default="", description="Human-readable reasoning")
    evidence: Dict = Field(default_factory=dict, description="Supporting data/evidence")
    factors: List[str] = Field(default_factory=list, description="Contributing factors")
    indicators: Dict[str, Any] = Field(default_factory=dict, description="Supporting indicator values")  # agents/state.py, strategies/base.py
    features_used: List[str] = Field(default_factory=list, description="ML features used")  # ml/signal_generator.py

    # --- Position sizing / ML ---
    suggested_size: Optional[float] = Field(None, description="Suggested position size as fraction")  # models/signal_generator.py
    models_agree: bool = Field(True, description="All ML models agreed on direction")  # models/signal_generator.py
    conviction: Optional[float] = Field(None, description="Conviction score (0-1)")  # kelly/backtest_integration.py

    # --- Timestamps ---
    timestamp: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # --- Extensibility ---
    metadata: Dict = Field(default_factory=dict)
    details: List[tuple[str, Any]] = Field(default_factory=list, description="Scorer-level details from FusionEngine")  # fusion_engine.py

    model_config = {"from_attributes": True}

    def compute_strength(self) -> SignalStrength:
        """Classify signal strength based on confidence."""
        if self.confidence >= 0.8:
            return SignalStrength.VERY_STRONG
        elif self.confidence >= 0.6:
            return SignalStrength.STRONG
        elif self.confidence >= 0.3:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
