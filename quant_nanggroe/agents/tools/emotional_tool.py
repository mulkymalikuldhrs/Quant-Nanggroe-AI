"""Emotional Tool — Emotional Intelligence & Gamified Discipline.

Provides mood tracking, discipline score calculation, gamified
enforcement (streaks, penalties), and emotional lockout integration
with the existing risk module.

Features
--------
* Mood tracking and logging
* Discipline score calculation
* Gamified enforcement (streaks, penalties, badges)
* Emotional lockout integration with existing risk module
* LangChain @tool function for agent consumption

References
----------
Trading-Plan-AI-Interactive Emotion Logic & Gamification documentation
"""

from __future__ import annotations

import json
import logging
import time
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

class MoodType(str, Enum):
    """Trader mood classification."""
    FOCUSED = "FOCUSED"
    CALM = "CALM"
    NEUTRAL = "NEUTRAL"
    CONFIDENT = "CONFIDENT"
    ANXIOUS = "ANXIOUS"
    FOMO = "FOMO"
    GREEDY = "GREEDY"
    REVENGE = "REVENGE"
    PANICKED = "PANICKED"
    FATIGUED = "FATIGUED"
    EUPHORIC = "EUPHORIC"
    BORED = "BORED"


class MoodCategory(str, Enum):
    """Mood category (positive/negative/neutral)."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class DisciplineAction(str, Enum):
    """Discipline enforcement actions."""
    NONE = "NONE"
    WARNING = "WARNING"
    COOLDOWN = "COOLDOWN"
    SOFT_LOCKOUT = "SOFT_LOCKOUT"
    HARD_LOCKOUT = "HARD_LOCKOUT"


class BadgeType(str, Enum):
    """Gamification badge types."""
    IRON_DISCIPLINE = "IRON_DISCIPLINE"
    STREAK_MASTER = "STREAK_MASTER"
    RISK_GUARDIAN = "RISK_GUARDIAN"
    ZEN_TRADER = "ZEN_TRADER"
    CONSISTENCY_KING = "CONSISTENCY_KING"
    FIVE_DAY_STREAK = "FIVE_DAY_STREAK"
    TEN_DAY_STREAK = "TEN_DAY_STREAK"
    THIRTY_DAY_STREAK = "THIRTY_DAY_STREAK"
    VIOLATION_FREE_WEEK = "VIOLATION_FREE_WEEK"
    VIOLATION_FREE_MONTH = "VIOLATION_FREE_MONTH"


# ---------------------------------------------------------------------------
# Mood classification
# ---------------------------------------------------------------------------

_MOOD_CATEGORIES: Dict[MoodType, MoodCategory] = {
    MoodType.FOCUSED: MoodCategory.POSITIVE,
    MoodType.CALM: MoodCategory.POSITIVE,
    MoodType.NEUTRAL: MoodCategory.NEUTRAL,
    MoodType.CONFIDENT: MoodCategory.POSITIVE,
    MoodType.ANXIOUS: MoodCategory.NEGATIVE,
    MoodType.FOMO: MoodCategory.NEGATIVE,
    MoodType.GREEDY: MoodCategory.NEGATIVE,
    MoodType.REVENGE: MoodCategory.NEGATIVE,
    MoodType.PANICKED: MoodCategory.NEGATIVE,
    MoodType.FATIGUED: MoodCategory.NEGATIVE,
    MoodType.EUPHORIC: MoodCategory.NEGATIVE,  # Overconfidence is dangerous
    MoodType.BORED: MoodCategory.NEGATIVE,  # Leads to overtrading
}

_MOOD_SCORES: Dict[MoodType, float] = {
    MoodType.FOCUSED: 1.0,
    MoodType.CALM: 0.8,
    MoodType.NEUTRAL: 0.5,
    MoodType.CONFIDENT: 0.7,
    MoodType.ANXIOUS: -0.5,
    MoodType.FOMO: -0.8,
    MoodType.GREEDY: -0.7,
    MoodType.REVENGE: -1.0,
    MoodType.PANICKED: -0.9,
    MoodType.FATIGUED: -0.4,
    MoodType.EUPHORIC: -0.6,
    MoodType.BORED: -0.3,
}

_LOCKOUT_THRESHOLDS = {
    3: DisciplineAction.SOFT_LOCKOUT,
    5: DisciplineAction.HARD_LOCKOUT,
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class MoodEntry(BaseModel):
    """Mood log entry."""
    entry_id: str = Field("", description="Entry identifier")
    mood: MoodType = Field(..., description="Mood type")
    category: MoodCategory = Field(MoodCategory.NEUTRAL)
    score: float = Field(0.0, description="Mood score (-1 to +1)")
    context: str = Field("", description="Context for the mood")
    symbol: Optional[str] = Field(None, description="Associated symbol")
    trade_id: Optional[str] = Field(None, description="Associated trade ID")
    timestamp: str = Field("")


class DisciplineScore(BaseModel):
    """Discipline score calculation result."""
    trader_id: str = Field(..., description="Trader identifier")
    overall_score: float = Field(0.0, description="Overall discipline score (0-100)")
    mood_score: float = Field(0.0, description="Mood discipline component (0-100)")
    streak_score: float = Field(0.0, description="Streak discipline component (0-100)")
    violation_score: float = Field(0.0, description="Violation penalty component (0-100)")
    current_streak: int = Field(0, description="Current positive mood streak")
    longest_streak: int = Field(0, description="Longest positive mood streak")
    consecutive_violations: int = Field(0, description="Consecutive negative moods")
    action: DisciplineAction = Field(DisciplineAction.NONE)
    badges: List[BadgeType] = Field(default_factory=list)
    lockout_active: bool = Field(False, description="Whether emotional lockout is active")
    lockout_reason: Optional[str] = Field(None)
    timestamp: str = Field("")


class StreakRecord(BaseModel):
    """Streak tracking record."""
    trader_id: str = Field(...)
    current_streak: int = Field(0)
    longest_streak: int = Field(0)
    last_positive_at: Optional[str] = Field(None)
    last_violation_at: Optional[str] = Field(None)
    consecutive_violations: int = Field(0)
    total_positive_entries: int = Field(0)
    total_negative_entries: int = Field(0)
    total_entries: int = Field(0)


class EmotionalLockoutState(BaseModel):
    """Emotional lockout state."""
    active: bool = Field(False)
    action: DisciplineAction = Field(DisciplineAction.NONE)
    started_at: Optional[str] = Field(None)
    duration_minutes: int = Field(0)
    reason: str = Field("")
    exercises: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Emotional Tool
# ---------------------------------------------------------------------------

class EmotionalTool:
    """Emotional intelligence and gamified discipline tool for agent consumption.

    Provides mood tracking, discipline scoring, gamified enforcement
    with streaks and penalties, and emotional lockout integration
    with the existing risk module.

    Usage::

        tool = EmotionalTool()
        entry = await tool.log_mood("trader1", MoodType.FOCUSED)
        score = await tool.get_discipline_score("trader1")
        lockout = await tool.check_lockout("trader1")
    """

    def __init__(self) -> None:
        self._mood_history: Dict[str, List[MoodEntry]] = {}
        self._streaks: Dict[str, StreakRecord] = {}
        self._lockouts: Dict[str, EmotionalLockoutState] = {}
        self._badges: Dict[str, List[BadgeType]] = {}

    async def log_mood(
        self,
        trader_id: str,
        mood: MoodType,
        context: str = "",
        symbol: Optional[str] = None,
        trade_id: Optional[str] = None,
    ) -> MoodEntry:
        """Log a mood entry for a trader.

        Args:
            trader_id: Trader identifier.
            mood: Mood type.
            context: Context for the mood.
            symbol: Associated trading symbol.
            trade_id: Associated trade ID.

        Returns:
            MoodEntry record.
        """
        category = _MOOD_CATEGORIES.get(mood, MoodCategory.NEUTRAL)
        score = _MOOD_SCORES.get(mood, 0.0)

        entry = MoodEntry(
            entry_id=f"mood_{int(time.time() * 1000)}",
            mood=mood,
            category=category,
            score=score,
            context=context,
            symbol=symbol,
            trade_id=trade_id,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

        if trader_id not in self._mood_history:
            self._mood_history[trader_id] = []
        self._mood_history[trader_id].append(entry)

        # Update streak
        await self._update_streak(trader_id, category)

        # Check for lockout
        await self.check_lockout(trader_id)

        # Check for badges
        await self._check_badges(trader_id)

        logger.info("Logged mood for %s: %s (score=%.2f)", trader_id, mood.value, score)
        return entry

    async def get_discipline_score(self, trader_id: str) -> DisciplineScore:
        """Calculate discipline score for a trader.

        Args:
            trader_id: Trader identifier.

        Returns:
            DisciplineScore with comprehensive discipline metrics.
        """
        history = self._mood_history.get(trader_id, [])
        streak = self._streaks.get(trader_id, StreakRecord(trader_id=trader_id))
        badges = self._badges.get(trader_id, [])

        # Mood score (recent entries weighted more)
        mood_score = 50.0
        if history:
            recent = history[-20:]  # Last 20 entries
            weights = [1.0 - (i / len(recent)) * 0.5 for i in range(len(recent))]
            weighted_sum = sum(e.score * w for e, w in zip(recent, weights))
            total_weight = sum(weights)
            avg_score = weighted_sum / total_weight if total_weight > 0 else 0.0
            mood_score = 50 + avg_score * 50  # Scale to 0-100

        # Streak score
        streak_score = min(streak.current_streak * 5, 100) if streak.current_streak > 0 else 0.0

        # Violation score
        violation_penalty = streak.consecutive_violations * 15
        violation_score = max(0, 100 - violation_penalty)

        # Overall score
        overall = mood_score * 0.4 + streak_score * 0.3 + violation_score * 0.3

        # Determine action
        action = DisciplineAction.NONE
        if streak.consecutive_violations >= 5:
            action = DisciplineAction.HARD_LOCKOUT
        elif streak.consecutive_violations >= 3:
            action = DisciplineAction.SOFT_LOCKOUT
        elif streak.consecutive_violations >= 2:
            action = DisciplineAction.COOLDOWN
        elif streak.consecutive_violations >= 1:
            action = DisciplineAction.WARNING

        return DisciplineScore(
            trader_id=trader_id,
            overall_score=round(overall, 2),
            mood_score=round(mood_score, 2),
            streak_score=round(streak_score, 2),
            violation_score=round(violation_score, 2),
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            consecutive_violations=streak.consecutive_violations,
            action=action,
            badges=badges,
            lockout_active=action in (DisciplineAction.SOFT_LOCKOUT, DisciplineAction.HARD_LOCKOUT),
            lockout_reason=self._get_lockout_reason(streak.consecutive_violations),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    async def check_lockout(self, trader_id: str) -> EmotionalLockoutState:
        """Check if emotional lockout should be active.

        Args:
            trader_id: Trader identifier.

        Returns:
            EmotionalLockoutState with lockout status.
        """
        streak = self._streaks.get(trader_id, StreakRecord(trader_id=trader_id))
        consecutive = streak.consecutive_violations

        # Determine action based on consecutive violations
        action = DisciplineAction.NONE
        duration = 0
        for threshold, act in sorted(_LOCKOUT_THRESHOLDS.items()):
            if consecutive >= threshold:
                action = act
                duration = threshold * 15  # Minutes

        if action == DisciplineAction.NONE and consecutive >= 2:
            action = DisciplineAction.COOLDOWN
            duration = 15
        elif action == DisciplineAction.NONE and consecutive >= 1:
            action = DisciplineAction.WARNING
            duration = 0

        # Create/update lockout state
        lockout = EmotionalLockoutState(
            active=action in (DisciplineAction.SOFT_LOCKOUT, DisciplineAction.HARD_LOCKOUT),
            action=action,
            started_at=datetime.now(tz=timezone.utc).isoformat() if action != DisciplineAction.NONE else None,
            duration_minutes=duration,
            reason=self._get_lockout_reason(consecutive),
            exercises=self._get_reflective_exercises(consecutive),
        )

        self._lockouts[trader_id] = lockout
        return lockout

    async def get_mood_history(
        self,
        trader_id: str,
        limit: int = 50,
    ) -> List[MoodEntry]:
        """Get mood history for a trader.

        Args:
            trader_id: Trader identifier.
            limit: Maximum entries.

        Returns:
            List of MoodEntry records.
        """
        history = self._mood_history.get(trader_id, [])
        return history[-limit:]

    # ----- Internal helpers -----

    async def _update_streak(self, trader_id: str, category: MoodCategory) -> None:
        """Update streak record for a trader."""
        if trader_id not in self._streaks:
            self._streaks[trader_id] = StreakRecord(trader_id=trader_id)

        streak = self._streaks[trader_id]
        streak.total_entries += 1

        if category == MoodCategory.POSITIVE:
            streak.current_streak += 1
            streak.consecutive_violations = 0
            streak.total_positive_entries += 1
            streak.last_positive_at = datetime.now(tz=timezone.utc).isoformat()
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        elif category == MoodCategory.NEGATIVE:
            streak.current_streak = 0
            streak.consecutive_violations += 1
            streak.total_negative_entries += 1
            streak.last_violation_at = datetime.now(tz=timezone.utc).isoformat()

    async def _check_badges(self, trader_id: str) -> None:
        """Check and award badges for gamification."""
        if trader_id not in self._badges:
            self._badges[trader_id] = []

        streak = self._streaks.get(trader_id, StreakRecord(trader_id=trader_id))
        current_badges = set(b.value for b in self._badges[trader_id])

        new_badges = []

        if streak.current_streak >= 5 and BadgeType.FIVE_DAY_STREAK.value not in current_badges:
            new_badges.append(BadgeType.FIVE_DAY_STREAK)
        if streak.current_streak >= 10 and BadgeType.TEN_DAY_STREAK.value not in current_badges:
            new_badges.append(BadgeType.TEN_DAY_STREAK)
        if streak.current_streak >= 30 and BadgeType.THIRTY_DAY_STREAK.value not in current_badges:
            new_badges.append(BadgeType.THIRTY_DAY_STREAK)
        if streak.longest_streak >= 10 and BadgeType.STREAK_MASTER.value not in current_badges:
            new_badges.append(BadgeType.STREAK_MASTER)
        if streak.total_positive_entries >= 50 and streak.total_negative_entries < 10:
            if BadgeType.ZEN_TRADER.value not in current_badges:
                new_badges.append(BadgeType.ZEN_TRADER)

        self._badges[trader_id].extend(new_badges)

        for badge in new_badges:
            logger.info("Badge awarded to %s: %s", trader_id, badge.value)

    @staticmethod
    def _get_lockout_reason(consecutive_violations: int) -> str:
        """Get lockout reason message."""
        if consecutive_violations >= 5:
            return (
                f"HARD LOCKOUT: {consecutive_violations} consecutive emotional violations. "
                "Mandatory cooling-off period. No trading allowed."
            )
        elif consecutive_violations >= 3:
            return (
                f"SOFT LOCKOUT: {consecutive_violations} consecutive emotional violations. "
                "Take a break before your next trade."
            )
        elif consecutive_violations >= 1:
            return (
                f"WARNING: {consecutive_violations} consecutive negative mood entries. "
                "Consider pausing before trading."
            )
        return ""

    @staticmethod
    def _get_reflective_exercises(consecutive_violations: int) -> List[str]:
        """Get reflective exercises for lockout recovery."""
        if consecutive_violations < 2:
            return []

        exercises = [
            "Journal: What triggered this emotional state?",
            "Breathe: 4-7-8 breathing exercise (4 sec inhale, 7 hold, 8 exhale)",
            "Review: Check your trading plan - does this trade fit your rules?",
        ]

        if consecutive_violations >= 3:
            exercises.extend([
                "Step away: Take a 15-minute walk without screens",
                "Gratitude: Write 3 things going well in your trading",
                "Perspective: Is this trade worth the emotional capital?",
            ])

        if consecutive_violations >= 5:
            exercises.extend([
                "Full reset: End trading for the day",
                "Reflect: Write a letter to your future trading self",
                "Support: Discuss your state with a mentor or peer",
            ])

        return exercises


# ---------------------------------------------------------------------------
# Singleton and LangChain @tool
# ---------------------------------------------------------------------------

_default_emotional: EmotionalTool | None = None


def _get_default_emotional() -> EmotionalTool:
    global _default_emotional
    if _default_emotional is None:
        _default_emotional = EmotionalTool()
    return _default_emotional


@tool
async def check_emotional_state(mood: str) -> str:
    """Check emotional state and discipline score for the current trader.

    Logs the trader's mood, calculates discipline score, checks for
    lockout conditions, and provides gamified feedback including
    streaks, badges, and reflective exercises.

    Args:
        mood: Current mood from: FOCUSED, CALM, NEUTRAL, CONFIDENT,
              ANXIOUS, FOMO, GREEDY, REVENGE, PANICKED, FATIGUED,
              EUPHORIC, BORED

    Returns:
        JSON string with discipline score, streak info, lockout status,
        badges, and recommended exercises if lockout is active.
    """
    try:
        et = _get_default_emotional()
        mood_enum = MoodType(mood.upper())
        entry = await et.log_mood("default_trader", mood_enum)
        score = await et.get_discipline_score("default_trader")
        return json.dumps({
            "mood_entry": entry.model_dump(),
            "discipline_score": score.model_dump(),
        }, indent=2, default=str)
    except ValueError:
        return json.dumps({"error": f"Invalid mood: {mood}. Use: {', '.join(m.value for m in MoodType)}"})
    except Exception as exc:
        logger.error("check_emotional_state tool error: %s", exc)
        return json.dumps({"error": f"Emotional check failed: {exc}"})


__all__ = [
    "EmotionalTool",
    "MoodType",
    "MoodCategory",
    "DisciplineAction",
    "BadgeType",
    "MoodEntry",
    "DisciplineScore",
    "StreakRecord",
    "EmotionalLockoutState",
    "check_emotional_state",
]
