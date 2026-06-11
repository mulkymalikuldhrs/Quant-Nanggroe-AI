"""Colony management for AI-MultiColony.

Provides colony lifecycle, hand-based agent grouping, task scheduling,
and agent-to-agent communication.
"""

from .manager import Colony, ColonyManager, SCALE_PRESETS
from .hands import (
    Hand,
    HandManager,
    SecurityHand,
    CodeHand,
    ResearchHand,
    BrowserHand,
    VoiceHand,
    ComputeHand,
    IntegrationHand,
    HAND_DESCRIPTIONS,
    HAND_DEFAULTS,
)
from .scheduler import TaskScheduler
from .a2a import A2ACoordinator

__all__ = [
    # Manager
    "Colony",
    "ColonyManager",
    "SCALE_PRESETS",
    # Hands
    "Hand",
    "HandManager",
    "SecurityHand",
    "CodeHand",
    "ResearchHand",
    "BrowserHand",
    "VoiceHand",
    "ComputeHand",
    "IntegrationHand",
    "HAND_DESCRIPTIONS",
    "HAND_DEFAULTS",
    # Scheduler
    "TaskScheduler",
    # A2A
    "A2ACoordinator",
]
