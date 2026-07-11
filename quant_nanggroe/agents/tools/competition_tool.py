"""Competition Tool — Agent Competition, Leaderboard & A/B Testing.

Provides agent registration, leaderboard tracking, A/B experiment
framework, signal quality scoring, and team mission matching.

Features
--------
* Agent registration and leaderboard
* A/B experiment framework for strategy comparison
* Signal quality scoring with Sharpe, accuracy, and consistency metrics
* Team mission and matching
* LangChain @tool function for agent consumption

References
----------
AI-Trader service/server competition and team mission architecture
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentTier(str, Enum):
    """Agent performance tier."""
    ELITE = "ELITE"
    EXPERT = "EXPERT"
    ADVANCED = "ADVANCED"
    INTERMEDIATE = "INTERMEDIATE"
    NOVICE = "NOVICE"


class ExperimentStatus(str, Enum):
    """A/B experiment status."""
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MissionStatus(str, Enum):
    """Team mission status."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AgentProfile(BaseModel):
    """Registered agent profile."""
    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field("", description="Agent display name")
    description: str = Field("", description="Agent description")
    tier: AgentTier = Field(AgentTier.NOVICE, description="Performance tier")
    total_signals: int = Field(0, description="Total signals generated")
    correct_signals: int = Field(0, description="Correct signal count")
    accuracy: float = Field(0.0, description="Signal accuracy (0-1)")
    sharpe_ratio: float = Field(0.0, description="Risk-adjusted performance")
    total_pnl: float = Field(0.0, description="Total P&L")
    max_drawdown: float = Field(0.0, description="Maximum drawdown")
    consistency_score: float = Field(0.0, description="Consistency score (0-1)")
    overall_score: float = Field(0.0, description="Composite score (0-100)")
    registered_at: str = Field("")
    last_active: str = Field("")


class SignalQualityScore(BaseModel):
    """Signal quality assessment."""
    signal_id: str = Field("", description="Signal identifier")
    agent_id: str = Field("", description="Agent that generated the signal")
    symbol: str = Field("", description="Trading symbol")
    direction: str = Field("", description="Signal direction")
    entry_price: float = Field(0.0, description="Suggested entry price")
    target_price: float = Field(0.0, description="Suggested target price")
    stop_loss: float = Field(0.0, description="Suggested stop loss")
    accuracy_score: float = Field(0.0, description="Signal accuracy score (0-1)")
    risk_adjusted_score: float = Field(0.0, description="Risk-adjusted score (0-1)")
    consistency_score: float = Field(0.0, description="Consistency with track record (0-1)")
    composite_score: float = Field(0.0, description="Composite quality score (0-100)")
    timestamp: str = Field("")


class Experiment(BaseModel):
    """A/B experiment for comparing strategies."""
    experiment_id: str = Field(..., description="Unique experiment ID")
    name: str = Field("", description="Experiment name")
    description: str = Field("", description="Experiment description")
    variant_a: str = Field("", description="Strategy A identifier")
    variant_b: str = Field("", description="Strategy B identifier")
    status: ExperimentStatus = Field(ExperimentStatus.DRAFT)
    start_time: Optional[str] = Field(None)
    end_time: Optional[str] = Field(None)
    variant_a_signals: int = Field(0)
    variant_b_signals: int = Field(0)
    variant_a_pnl: float = Field(0.0)
    variant_b_pnl: float = Field(0.0)
    variant_a_accuracy: float = Field(0.0)
    variant_b_accuracy: float = Field(0.0)
    winner: Optional[str] = Field(None)
    statistical_significance: float = Field(0.0, description="P-value or confidence")
    created_at: str = Field("")


class TeamMission(BaseModel):
    """Team mission for collaborative trading."""
    mission_id: str = Field(..., description="Unique mission ID")
    name: str = Field("", description="Mission name")
    description: str = Field("", description="Mission description")
    target_symbols: List[str] = Field(default_factory=list)
    status: MissionStatus = Field(MissionStatus.OPEN)
    teams: List[Dict[str, Any]] = Field(default_factory=list)
    leaderboard: List[Dict[str, Any]] = Field(default_factory=list)
    reward_pool: float = Field(0.0, description="Reward pool amount")
    created_at: str = Field("")


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""
    rank: int = Field(0)
    agent_id: str = Field("")
    name: str = Field("")
    tier: AgentTier = Field(AgentTier.NOVICE)
    overall_score: float = Field(0.0)
    accuracy: float = Field(0.0)
    sharpe_ratio: float = Field(0.0)
    total_pnl: float = Field(0.0)


# ---------------------------------------------------------------------------
# Competition Tool
# ---------------------------------------------------------------------------

class CompetitionTool:
    """Agent competition and scoring tool for agent consumption.

    Provides agent registration, leaderboard, A/B experiments,
    signal quality scoring, and team mission management.

    Usage::

        tool = CompetitionTool()
        agent = await tool.register_agent("my-strategy", "My Strategy")
        score = await tool.score_signal("agent1", "AAPL", "BUY", 150.0)
        lb = await tool.get_leaderboard()
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentProfile] = {}
        self._experiments: Dict[str, Experiment] = {}
        self._missions: Dict[str, TeamMission] = {}
        self._signals: List[SignalQualityScore] = []

    # ----- Agent Registration -----

    async def register_agent(
        self,
        agent_id: str,
        name: str = "",
        description: str = "",
    ) -> AgentProfile:
        """Register a new agent in the competition.

        Args:
            agent_id: Unique agent identifier.
            name: Display name.
            description: Agent description.

        Returns:
            AgentProfile for the registered agent.
        """
        if agent_id in self._agents:
            return self._agents[agent_id]

        profile = AgentProfile(
            agent_id=agent_id,
            name=name or agent_id,
            description=description,
            tier=AgentTier.NOVICE,
            registered_at=datetime.now(tz=timezone.utc).isoformat(),
            last_active=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._agents[agent_id] = profile
        logger.info("Registered agent: %s", agent_id)
        return profile

    async def update_agent_performance(
        self,
        agent_id: str,
        signal_correct: bool,
        pnl: float = 0.0,
    ) -> AgentProfile:
        """Update agent performance after a signal resolves.

        Args:
            agent_id: Agent identifier.
            signal_correct: Whether the signal was correct.
            pnl: P&L from this signal.

        Returns:
            Updated AgentProfile.
        """
        if agent_id not in self._agents:
            await self.register_agent(agent_id)

        profile = self._agents[agent_id]
        profile.total_signals += 1
        if signal_correct:
            profile.correct_signals += 1
        profile.total_pnl += pnl
        profile.accuracy = profile.correct_signals / profile.total_signals if profile.total_signals > 0 else 0.0

        # Update tier
        if profile.total_signals >= 50:
            if profile.accuracy >= 0.7 and profile.sharpe_ratio >= 2.0:
                profile.tier = AgentTier.ELITE
            elif profile.accuracy >= 0.6 and profile.sharpe_ratio >= 1.5:
                profile.tier = AgentTier.EXPERT
            elif profile.accuracy >= 0.55:
                profile.tier = AgentTier.ADVANCED
            else:
                profile.tier = AgentTier.INTERMEDIATE
        elif profile.total_signals >= 20:
            profile.tier = AgentTier.INTERMEDIATE

        # Calculate overall score
        profile.overall_score = self._calculate_overall_score(profile)
        profile.last_active = datetime.now(tz=timezone.utc).isoformat()

        return profile

    # ----- Signal Quality Scoring -----

    async def score_signal(
        self,
        agent_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        target_price: float = 0.0,
        stop_loss: float = 0.0,
    ) -> SignalQualityScore:
        """Score a trading signal for quality assessment.

        Args:
            agent_id: Agent generating the signal.
            symbol: Trading symbol.
            direction: BUY or SELL.
            entry_price: Suggested entry price.
            target_price: Suggested target price.
            stop_loss: Suggested stop loss.

        Returns:
            SignalQualityScore with quality metrics.
        """
        profile = self._agents.get(agent_id)
        accuracy_score = profile.accuracy if profile else 0.5
        consistency_score = profile.consistency_score if profile else 0.5

        # Risk-adjusted score based on target/stop distance
        risk_adjusted = 0.5
        if entry_price > 0 and stop_loss > 0 and target_price > 0:
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price - entry_price)
            if risk > 0:
                rr_ratio = reward / risk
                risk_adjusted = min(rr_ratio / 3.0, 1.0)

        composite = (
            accuracy_score * 0.4
            + risk_adjusted * 0.35
            + consistency_score * 0.25
        ) * 100

        signal = SignalQualityScore(
            signal_id=str(uuid.uuid4()),
            agent_id=agent_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            accuracy_score=round(accuracy_score, 4),
            risk_adjusted_score=round(risk_adjusted, 4),
            consistency_score=round(consistency_score, 4),
            composite_score=round(composite, 2),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

        self._signals.append(signal)
        return signal

    # ----- Leaderboard -----

    async def get_leaderboard(
        self,
        limit: int = 20,
        tier: Optional[AgentTier] = None,
    ) -> List[LeaderboardEntry]:
        """Get the agent leaderboard.

        Args:
            limit: Maximum entries to return.
            tier: Filter by tier (optional).

        Returns:
            List of LeaderboardEntry sorted by overall score.
        """
        agents = list(self._agents.values())
        if tier:
            agents = [a for a in agents if a.tier == tier]

        agents.sort(key=lambda a: a.overall_score, reverse=True)

        entries = []
        for i, profile in enumerate(agents[:limit]):
            entries.append(LeaderboardEntry(
                rank=i + 1,
                agent_id=profile.agent_id,
                name=profile.name,
                tier=profile.tier,
                overall_score=round(profile.overall_score, 2),
                accuracy=round(profile.accuracy, 4),
                sharpe_ratio=round(profile.sharpe_ratio, 4),
                total_pnl=round(profile.total_pnl, 2),
            ))

        return entries

    # ----- A/B Experiments -----

    async def create_experiment(
        self,
        name: str,
        variant_a: str,
        variant_b: str,
        description: str = "",
    ) -> Experiment:
        """Create an A/B experiment for comparing strategies.

        Args:
            name: Experiment name.
            variant_a: Strategy A identifier.
            variant_b: Strategy B identifier.
            description: Experiment description.

        Returns:
            Experiment instance.
        """
        experiment = Experiment(
            experiment_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            variant_a=variant_a,
            variant_b=variant_b,
            status=ExperimentStatus.DRAFT,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._experiments[experiment.experiment_id] = experiment
        return experiment

    async def start_experiment(self, experiment_id: str) -> Experiment:
        """Start an A/B experiment.

        Args:
            experiment_id: Experiment identifier.

        Returns:
            Updated Experiment.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found")
        exp.status = ExperimentStatus.RUNNING
        exp.start_time = datetime.now(tz=timezone.utc).isoformat()
        return exp

    async def record_experiment_result(
        self,
        experiment_id: str,
        variant: str,
        signal_correct: bool,
        pnl: float = 0.0,
    ) -> Experiment:
        """Record a result for an A/B experiment.

        Args:
            experiment_id: Experiment identifier.
            variant: "a" or "b".
            signal_correct: Whether signal was correct.
            pnl: P&L from signal.

        Returns:
            Updated Experiment.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found")

        if variant.lower() == "a":
            exp.variant_a_signals += 1
            exp.variant_a_pnl += pnl
            if signal_correct:
                exp.variant_a_accuracy = (
                    (exp.variant_a_accuracy * (exp.variant_a_signals - 1) + 1.0)
                    / exp.variant_a_signals
                )
            else:
                exp.variant_a_accuracy = (
                    exp.variant_a_accuracy * (exp.variant_a_signals - 1)
                    / exp.variant_a_signals
                )
        elif variant.lower() == "b":
            exp.variant_b_signals += 1
            exp.variant_b_pnl += pnl
            if signal_correct:
                exp.variant_b_accuracy = (
                    (exp.variant_b_accuracy * (exp.variant_b_signals - 1) + 1.0)
                    / exp.variant_b_signals
                )
            else:
                exp.variant_b_accuracy = (
                    exp.variant_b_accuracy * (exp.variant_b_signals - 1)
                    / exp.variant_b_signals
                )

        return exp

    # ----- Team Missions -----

    async def create_mission(
        self,
        name: str,
        target_symbols: Optional[List[str]] = None,
        description: str = "",
        reward_pool: float = 0.0,
    ) -> TeamMission:
        """Create a team mission.

        Args:
            name: Mission name.
            target_symbols: Symbols to trade.
            description: Mission description.
            reward_pool: Reward pool amount.

        Returns:
            TeamMission instance.
        """
        mission = TeamMission(
            mission_id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            target_symbols=target_symbols or [],
            status=MissionStatus.OPEN,
            reward_pool=reward_pool,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._missions[mission.mission_id] = mission
        return mission

    async def join_mission(
        self,
        mission_id: str,
        agent_id: str,
        team_name: str = "",
    ) -> TeamMission:
        """Join a team mission.

        Args:
            mission_id: Mission identifier.
            agent_id: Agent joining.
            team_name: Optional team name.

        Returns:
            Updated TeamMission.
        """
        mission = self._missions.get(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        mission.teams.append({
            "agent_id": agent_id,
            "team_name": team_name or f"team_{agent_id}",
            "joined_at": datetime.now(tz=timezone.utc).isoformat(),
        })

        if mission.status == MissionStatus.OPEN:
            mission.status = MissionStatus.IN_PROGRESS

        return mission

    # ----- Internal helpers -----

    @staticmethod
    def _calculate_overall_score(profile: AgentProfile) -> float:
        """Calculate composite overall score for an agent."""
        accuracy_component = profile.accuracy * 40  # 0-40 points
        sharpe_component = min(max(profile.sharpe_ratio, 0) / 3.0, 1.0) * 30  # 0-30 points
        consistency_component = profile.consistency_score * 20  # 0-20 points
        pnl_component = min(max(profile.total_pnl, 0) / 10000, 1.0) * 10  # 0-10 points

        return round(
            accuracy_component + sharpe_component + consistency_component + pnl_component,
            2,
        )


# ---------------------------------------------------------------------------
# Singleton and LangChain @tool
# ---------------------------------------------------------------------------

_default_competition: CompetitionTool | None = None


def _get_default_competition() -> CompetitionTool:
    global _default_competition
    if _default_competition is None:
        _default_competition = CompetitionTool()
    return _default_competition


@tool
async def get_leaderboard(limit: int = 10) -> str:
    """Get the agent competition leaderboard.

    Returns the top agents ranked by overall score, including accuracy,
    Sharpe ratio, and total P&L.

    Args:
        limit: Maximum number of entries to return (default 10)

    Returns:
        JSON string with leaderboard entries.
    """
    try:
        comp = _get_default_competition()
        entries = await comp.get_leaderboard(limit=limit)
        return json.dumps(
            [e.model_dump() for e in entries],
            indent=2,
            default=str,
        )
    except Exception as exc:
        logger.error("get_leaderboard tool error: %s", exc)
        return json.dumps({"error": f"Leaderboard failed: {exc}"})


__all__ = [
    "CompetitionTool",
    "AgentTier",
    "ExperimentStatus",
    "MissionStatus",
    "AgentProfile",
    "SignalQualityScore",
    "Experiment",
    "TeamMission",
    "LeaderboardEntry",
    "get_leaderboard",
]
