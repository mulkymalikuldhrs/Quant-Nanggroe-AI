"""
Agent State Definitions for Quant Nanggroe AI Trading Framework.

Defines all Pydantic models and TypedDict classes used for agent state
management within the LangGraph trading graph. These models represent
the shared state that flows between agents during the trading pipeline.

Constitutional risk limits are HARDCODED and CANNOT be overridden.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated, TypedDict

from quant_nanggroe.engine.risk.constants import (
    CONFIDENCE_THRESHOLD as _ENGINE_CONFIDENCE_THRESHOLD,
)
from quant_nanggroe.engine.risk.constants import (
    KILL_SWITCH_DAILY_PNL as _ENGINE_KILL_SWITCH_DAILY_PNL,
)
from quant_nanggroe.engine.risk.constants import (
    KILL_SWITCH_WEEKLY_PNL as _ENGINE_KILL_SWITCH_WEEKLY_PNL,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_CORRELATED_POSITIONS as _ENGINE_MAX_CORRELATED_POSITIONS,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_DAILY_LOSS as _ENGINE_MAX_DAILY_LOSS,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_DAILY_TRADES as _ENGINE_MAX_DAILY_TRADES,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_DRAWDOWN_PCT as _ENGINE_MAX_DRAWDOWN_PCT,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_LEVERAGE as _ENGINE_MAX_LEVERAGE,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_POSITION_SIZE_PCT as _ENGINE_MAX_POSITION_SIZE_PCT,
)

# =============================================================================
# CONSTITUTIONAL RISK LIMITS — Single Source of Truth
# =============================================================================
# All constants are imported from engine/risk/constants.py to avoid duplication.
# These values are immutable and cannot be changed at runtime.
# A runtime assertion below ensures the values stay in sync.
# =============================================================================
from quant_nanggroe.engine.risk.constants import (
    MAX_RISK_PER_TRADE as _ENGINE_MAX_RISK_PER_TRADE,
)
from quant_nanggroe.engine.risk.constants import (
    MAX_WEEKLY_LOSS as _ENGINE_MAX_WEEKLY_LOSS,
)
from quant_nanggroe.engine.risk.constants import (
    MIN_RISK_REWARD as _ENGINE_MIN_RISK_REWARD,
)

# Re-export with the names expected by the agent layer
MAX_RISK_PER_TRADE: float = _ENGINE_MAX_RISK_PER_TRADE
MAX_DAILY_LOSS: float = _ENGINE_MAX_DAILY_LOSS
MAX_WEEKLY_LOSS: float = _ENGINE_MAX_WEEKLY_LOSS
MIN_RISK_REWARD: float = _ENGINE_MIN_RISK_REWARD
MAX_CORRELATED_POSITIONS: int = _ENGINE_MAX_CORRELATED_POSITIONS
MAX_POSITION_SIZE_PCT: float = _ENGINE_MAX_POSITION_SIZE_PCT
MAX_LEVERAGE: float = _ENGINE_MAX_LEVERAGE
MAX_DRAWDOWN_PCT: float = _ENGINE_MAX_DRAWDOWN_PCT
MAX_TRADES_PER_DAY: int = _ENGINE_MAX_DAILY_TRADES  # Alias for backward compat
CONFIDENCE_THRESHOLD: float = _ENGINE_CONFIDENCE_THRESHOLD
KILL_SWITCH_DAILY_PNL: float = _ENGINE_KILL_SWITCH_DAILY_PNL
KILL_SWITCH_WEEKLY_PNL: float = _ENGINE_KILL_SWITCH_WEEKLY_PNL

# =============================================================================
# RUNTIME ASSERTION: Ensure engine constants and agent constants match
# =============================================================================
# These assertions verify that the values imported from engine/risk/constants.py
# match the previously hardcoded values in this file. If someone changes the
# engine constants without updating the expected values here, this will fail.
# =============================================================================
_assertion_checks = [
    ("MAX_RISK_PER_TRADE", _ENGINE_MAX_RISK_PER_TRADE, 0.005),
    ("MAX_DAILY_LOSS", _ENGINE_MAX_DAILY_LOSS, 0.01),
    ("MAX_WEEKLY_LOSS", _ENGINE_MAX_WEEKLY_LOSS, 0.03),
    ("MIN_RISK_REWARD", _ENGINE_MIN_RISK_REWARD, 2.0),
    ("MAX_CORRELATED_POSITIONS", _ENGINE_MAX_CORRELATED_POSITIONS, 3),
    ("MAX_POSITION_SIZE_PCT", _ENGINE_MAX_POSITION_SIZE_PCT, 0.10),
    ("MAX_LEVERAGE", _ENGINE_MAX_LEVERAGE, 3.0),
    ("MAX_DRAWDOWN_PCT", _ENGINE_MAX_DRAWDOWN_PCT, 0.10),
    ("MAX_DAILY_TRADES", _ENGINE_MAX_DAILY_TRADES, 5),
    ("CONFIDENCE_THRESHOLD", _ENGINE_CONFIDENCE_THRESHOLD, 0.65),
    # Kill switch thresholds are EARLY WARNING — they trigger BEFORE constitutional hard limits
    # KILL_SWITCH_DAILY: -0.8% (before 1% hard limit) | KILL_SWITCH_WEEKLY: -2.5% (before 3% hard limit)
    ("KILL_SWITCH_DAILY_PNL", _ENGINE_KILL_SWITCH_DAILY_PNL, -0.008),
    ("KILL_SWITCH_WEEKLY_PNL", _ENGINE_KILL_SWITCH_WEEKLY_PNL, -0.025),
]
for _name, _imported_val, _expected_val in _assertion_checks:
    assert _imported_val == _expected_val, (
        f"CONSTANT MISMATCH: engine/risk/constants.py {_name}={_imported_val} "
        f"!= expected {_expected_val}. Update this assertion if the change is intentional."
    )


# =============================================================================
# Enumerations
# =============================================================================

class TradeAction(str, Enum):
    """Possible trade actions."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"


class SignalDirection(str, Enum):
    """Signal direction types."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RiskVerdict(str, Enum):
    """Risk assessment verdicts."""
    APPROVED = "APPROVED"
    VETOED = "VETOED"
    CONDITIONAL = "CONDITIONAL"
    KILL_SWITCH = "KILL_SWITCH"


class MarketRegime(str, Enum):
    """Macro market regime types."""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    TRANSITIONING = "TRANSITIONING"
    CRISIS = "CRISIS"
    RECOVERY = "RECOVERY"


class AgentRole(str, Enum):
    """Agent role types."""
    RESEARCHER = "researcher"
    TRADER = "trader"
    STRATEGIST = "strategist"
    RISK = "risk"
    PORTFOLIO = "portfolio"
    EXECUTION = "execution"
    MACRO = "macro"
    CRYPTO = "crypto"
    FOREX = "forex"
    COUNCIL = "council"
    SMC = "smc"
    DEBATE = "debate"
    GEOPOLITICS = "geopolitics"
    PERSONAS = "personas"
    PERSONA = "persona"  # Alias for individual persona agents
    COMPLIANCE = "compliance"


# =============================================================================
# Core Data Models
# =============================================================================

class MarketData(BaseModel):
    """Market data for a single symbol."""
    model_config = ConfigDict(extra="allow")

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTCUSDT)")
    price: float = Field(0.0, description="Current price")
    open: float = Field(0.0, description="Opening price")
    high: float = Field(0.0, description="High price")
    low: float = Field(0.0, description="Low price")
    close: float = Field(0.0, description="Closing price")
    volume: float = Field(0.0, description="Trading volume")
    change_pct: float = Field(0.0, description="Percentage change")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")
    bid: Optional[float] = Field(None, description="Bid price")
    ask: Optional[float] = Field(None, description="Ask price")
    vwap: Optional[float] = Field(None, description="Volume-weighted average price")


class Signal(BaseModel):
    """A trading signal generated by the Strategist agent."""
    model_config = ConfigDict(extra="allow")

    symbol: str = Field(..., description="Trading symbol")
    direction: SignalDirection = Field(..., description="Signal direction")
    action: TradeAction = Field(..., description="Recommended trade action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Signal confidence (0-1)")
    entry_price: Optional[float] = Field(None, description="Suggested entry price")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    timeframe: str = Field("1D", description="Signal timeframe")
    source_agents: List[str] = Field(default_factory=list, description="Agents contributing to signal")
    reasoning: str = Field("", description="Detailed reasoning for the signal")
    timestamp: datetime = Field(default_factory=datetime.now, description="Signal generation time")
    indicators: Dict[str, Any] = Field(default_factory=dict, description="Supporting indicator values")
    risk_reward_ratio: Optional[float] = Field(None, description="Risk:Reward ratio")


class Decision(BaseModel):
    """A final trading decision made by the Trader agent."""
    model_config = ConfigDict(extra="allow")

    symbol: str = Field(..., description="Trading symbol")
    action: TradeAction = Field(..., description="Trade action to execute")
    quantity: float = Field(0.0, description="Number of shares/contracts")
    entry_price: Optional[float] = Field(None, description="Entry price")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Decision confidence")
    risk_reward_ratio: Optional[float] = Field(None, description="Risk:Reward ratio")
    reasoning: str = Field("", description="Decision reasoning")
    timestamp: datetime = Field(default_factory=datetime.now, description="Decision time")
    position_size_pct: float = Field(0.0, description="Position size as % of portfolio")


class RiskCheckpoint(BaseModel):
    """A single risk checkpoint result."""
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Checkpoint name")
    value: str = Field(..., description="Current value")
    limit: str = Field(..., description="Constitutional limit")
    passed: bool = Field(..., description="Whether the checkpoint passed")
    details: str = Field("", description="Additional details")


class RiskAssessment(BaseModel):
    """Complete risk assessment with 9-checkpoint gate."""
    model_config = ConfigDict(extra="allow")

    verdict: RiskVerdict = Field(RiskVerdict.VETOED, description="Overall risk verdict")
    checkpoints: List[RiskCheckpoint] = Field(default_factory=list, description="9 risk checkpoints")
    var_95: Optional[float] = Field(None, description="Value at Risk (95% confidence)")
    var_99: Optional[float] = Field(None, description="Value at Risk (99% confidence)")
    cvar_95: Optional[float] = Field(None, description="Conditional VaR (95%)")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown percentage")
    kelly_fraction: Optional[float] = Field(None, description="Kelly criterion fraction")
    position_sizing_approved: bool = Field(False, description="Position sizing passed risk check")
    correlation_risk: Optional[float] = Field(None, description="Portfolio correlation risk")
    kill_switch_active: bool = Field(False, description="Whether kill switch is active")
    daily_pnl_pct: float = Field(0.0, description="Daily PnL percentage")
    weekly_pnl_pct: float = Field(0.0, description="Weekly PnL percentage")
    trade_count_today: int = Field(0, description="Number of trades today")
    timestamp: datetime = Field(default_factory=datetime.now, description="Assessment time")
    override_possible: bool = Field(False, description="Constitutional limits cannot be overridden")


class PortfolioState(BaseModel):
    """Current portfolio state."""
    model_config = ConfigDict(extra="allow")

    total_value: float = Field(0.0, description="Total portfolio value")
    cash: float = Field(0.0, description="Available cash")
    positions: Dict[str, PositionInfo] = Field(default_factory=dict, description="Current positions by symbol")
    unrealized_pnl: float = Field(0.0, description="Unrealized profit/loss")
    realized_pnl: float = Field(0.0, description="Realized profit/loss")
    daily_pnl: float = Field(0.0, description="Daily profit/loss")
    weekly_pnl: float = Field(0.0, description="Weekly profit/loss")
    allocation: Dict[str, float] = Field(default_factory=dict, description="Asset allocation by symbol")
    risk_budget_used: float = Field(0.0, description="Risk budget used percentage")
    open_orders: List[Dict[str, Any]] = Field(default_factory=list, description="Open orders")


class PositionInfo(BaseModel):
    """Information about a single position."""
    model_config = ConfigDict(extra="allow")

    symbol: str = Field(..., description="Trading symbol")
    quantity: float = Field(0.0, description="Position quantity")
    entry_price: float = Field(0.0, description="Average entry price")
    current_price: float = Field(0.0, description="Current market price")
    unrealized_pnl: float = Field(0.0, description="Unrealized PnL")
    direction: str = Field("LONG", description="LONG or SHORT")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    timestamp: datetime = Field(default_factory=datetime.now, description="Position open time")


class AgentOutput(BaseModel):
    """Output from a single agent execution."""
    model_config = ConfigDict(extra="allow")

    agent_name: str = Field(..., description="Name of the agent")
    agent_role: AgentRole = Field(..., description="Role of the agent")
    content: str = Field("", description="Agent's text output/reasoning")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured output data")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Agent's confidence")
    success: bool = Field(True, description="Whether agent execution succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Output timestamp")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Tool calls made")


class DebateState(TypedDict):
    """State for the bull/bear debate mechanism."""
    bull_history: Annotated[str, "Bull argument history"]
    bear_history: Annotated[str, "Bear argument history"]
    history: Annotated[str, "Full conversation history"]
    current_response: Annotated[str, "Latest response"]
    judge_decision: Annotated[str, "Final judge decision"]
    count: Annotated[int, "Number of debate rounds"]


class RiskDebateState(TypedDict):
    """State for the risk debate mechanism (conservative/neutral/aggressive)."""
    conservative_history: Annotated[str, "Conservative debater history"]
    neutral_history: Annotated[str, "Neutral debater history"]
    aggressive_history: Annotated[str, "Aggressive debater history"]
    history: Annotated[str, "Full conversation history"]
    latest_speaker: Annotated[str, "Last debater who spoke"]
    current_conservative_response: Annotated[str, "Latest conservative response"]
    current_neutral_response: Annotated[str, "Latest neutral response"]
    current_aggressive_response: Annotated[str, "Latest aggressive response"]
    judge_decision: Annotated[str, "Risk judge's final decision"]
    count: Annotated[int, "Number of debate rounds"]


class VoteResult(BaseModel):
    """Result of a council vote."""
    model_config = ConfigDict(extra="allow")

    voter: str = Field(..., description="Voter agent name")
    vote: TradeAction = Field(..., description="Vote cast")
    weight: float = Field(1.0, description="Voter's weight based on historical accuracy")
    reasoning: str = Field("", description="Voter's reasoning")
    confidence: float = Field(0.0, description="Voter's confidence")


class CouncilResult(BaseModel):
    """Result of a council debate and vote."""
    model_config = ConfigDict(extra="allow")

    final_decision: TradeAction = Field(TradeAction.HOLD, description="Final council decision")
    debate_summary: str = Field("", description="Summary of the debate")
    votes: List[VoteResult] = Field(default_factory=list, description="Individual votes")
    weighted_score: Dict[str, float] = Field(default_factory=dict, description="Weighted scores per action")
    consensus_level: float = Field(0.0, description="How much agreement (0-1)")
    requires_human_review: bool = Field(False, description="Whether human review is needed")


# =============================================================================
# Main Agent State (used by LangGraph StateGraph)
# =============================================================================

class AgentState(TypedDict):
    """
    Main agent state that flows through the LangGraph trading graph.

    This is the shared state that all agents read from and write to
    during the trading pipeline execution.
    """
    # Core identification
    symbols: Annotated[List[str], "List of trading symbols to analyze"]
    trade_date: Annotated[str, "Current trading date (YYYY-MM-DD)"]

    # Market data
    market_data: Annotated[Dict[str, Any], "Market data by symbol -> MarketData dict"]

    # Agent outputs from analysis phase
    research_output: Annotated[str, "Research agent output"]
    macro_output: Annotated[str, "Macro agent output"]
    crypto_output: Annotated[str, "Crypto agent output"]
    forex_output: Annotated[str, "Forex agent output"]

    # Signal generation
    signals: Annotated[List[Dict[str, Any]], "Generated trading signals"]
    strategist_output: Annotated[str, "Strategist agent output"]

    # Risk assessment (LLM-based qualitative analysis)
    risk_assessment: Annotated[Dict[str, Any], "Risk assessment results"]
    risk_verdict: Annotated[str, "Risk verdict: APPROVED/VETOED/KILL_SWITCH"]

    # Deterministic risk gate (HARD GATE — final authority)
    deterministic_risk_verdict: Annotated[str, "Deterministic risk gate verdict: APPROVED/REJECTED/MODIFIED/KILL_SWITCH"]
    deterministic_risk_results: Annotated[List[Dict[str, Any]], "Per-trade deterministic gate results"]
    deterministic_risk_timestamp: Annotated[str, "Timestamp of deterministic gate evaluation"]

    # Kelly position sizing (deterministic)
    kelly_results: Annotated[List[Dict[str, Any]], "Kelly criterion position sizing results"]

    # Portfolio
    portfolio_state: Annotated[Dict[str, Any], "Current portfolio state"]
    portfolio_output: Annotated[str, "Portfolio agent output"]

    # Trading decision
    decisions: Annotated[List[Dict[str, Any]], "Final trading decisions"]
    trader_output: Annotated[str, "Trader agent output"]

    # Execution
    execution_output: Annotated[str, "Execution agent output"]
    orders_placed: Annotated[List[Dict[str, Any]], "Orders placed"]

    # Council / Debate
    debate_state: Annotated[Dict[str, Any], "Current debate state"]
    council_result: Annotated[Dict[str, Any], "Council voting result"]

    # All agent outputs collected
    agent_outputs: Annotated[Dict[str, Any], "All agent outputs by name"]

    # Control flow
    iteration: Annotated[int, "Current iteration count"]
    confidence: Annotated[float, "Overall confidence in the decision"]
    kill_switch_active: Annotated[bool, "Whether kill switch is active"]
    should_halt: Annotated[bool, "Whether to halt the pipeline"]

    # Metadata
    metadata: Annotated[Dict[str, Any], "Additional metadata"]
    sender: Annotated[str, "Agent that last sent a message"]


def create_initial_state(symbols: List[str], trade_date: str) -> Dict[str, Any]:
    """
    Create the initial AgentState for a new trading pipeline run.

    Args:
        symbols: List of trading symbols to analyze
        trade_date: Current trading date string (YYYY-MM-DD)

    Returns:
        Initial AgentState dictionary with default values
    """
    return {
        "symbols": symbols,
        "trade_date": trade_date,
        "market_data": {},
        "research_output": "",
        "macro_output": "",
        "crypto_output": "",
        "forex_output": "",
        "signals": [],
        "strategist_output": "",
        "risk_assessment": {},
        "risk_verdict": RiskVerdict.VETOED.value,
        "deterministic_risk_verdict": "REJECTED",
        "deterministic_risk_results": [],
        "deterministic_risk_timestamp": "",
        "kelly_results": [],
        "portfolio_state": {},
        "portfolio_output": "",
        "decisions": [],
        "trader_output": "",
        "execution_output": "",
        "orders_placed": [],
        "debate_state": {
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "current_response": "",
            "judge_decision": "",
            "count": 0,
        },
        "council_result": {},
        "agent_outputs": {},
        "iteration": 0,
        "confidence": 0.0,
        "kill_switch_active": False,
        "should_halt": False,
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "constitutional_limits": {
                "max_risk_per_trade": MAX_RISK_PER_TRADE,
                "max_daily_loss": MAX_DAILY_LOSS,
                "max_weekly_loss": MAX_WEEKLY_LOSS,
                "min_risk_reward": MIN_RISK_REWARD,
                "max_correlated_positions": MAX_CORRELATED_POSITIONS,
                "max_position_size_pct": MAX_POSITION_SIZE_PCT,
                "max_leverage": MAX_LEVERAGE,
                "max_drawdown_pct": MAX_DRAWDOWN_PCT,
                "max_trades_per_day": MAX_TRADES_PER_DAY,
                "override_possible": False,
            },
        },
        "sender": "system",
    }
