"""Self-evolution organism package for AI-MultiColony.

Implements the autonomous organism lifecycle:
Sense → Decision → Factory → Growth → Evolve

The organism can detect problems, decide on actions, build solutions,
grow their adoption, and evolve its own behaviour over time – all
safeguarded by an immune system.

Modules
-------
sense     – Problem scanning engine (RSS, APIs, trend detection)
decision  – Decision scoring with configurable criteria
factory   – Solution builder (code generation, service creation)
immune    – Safety system (loop detection, iteration limits, kill switches)
growth    – Growth and marketing engine
lifecycle – Full lifecycle orchestrator
"""

from .sense import (
    SenseEngine,
    Signal,
    SignalType,
    SignalSeverity,
    SignalSource,
    ScanResult,
    SignalScanner,
    RSSScanner,
    APIScanner,
    TrendScanner,
)
from .decision import (
    DecisionEngine,
    DecisionScore,
    DecisionStatus,
    DecisionConfig,
    ScoringCriterion,
    CriterionCategory,
    DEFAULT_CRITERIA,
)
from .factory import (
    SolutionFactory,
    BuildRequest,
    BuildResult,
    BuildArtifact,
    ArtifactType,
    BuildStatus,
    CODE_TEMPLATES,
)
from .immune import (
    ImmuneSystem,
    ImmuneConfig,
    ThreatAlert,
    ThreatLevel,
    ThreatType,
    ImmuneAction,
)
from .growth import (
    GrowthEngine,
    GrowthMetrics,
    GrowthStage,
    PromotionRecord,
    PromotionChannel,
    FeedbackEntry,
)
from .lifecycle import (
    LifecycleOrchestrator,
    LifecyclePhase,
    OrganismStatus,
    OrganismConfig,
    CycleResult,
)

__all__ = [
    # Sense
    "SenseEngine",
    "Signal",
    "SignalType",
    "SignalSeverity",
    "SignalSource",
    "ScanResult",
    "SignalScanner",
    "RSSScanner",
    "APIScanner",
    "TrendScanner",
    # Decision
    "DecisionEngine",
    "DecisionScore",
    "DecisionStatus",
    "DecisionConfig",
    "ScoringCriterion",
    "CriterionCategory",
    "DEFAULT_CRITERIA",
    # Factory
    "SolutionFactory",
    "BuildRequest",
    "BuildResult",
    "BuildArtifact",
    "ArtifactType",
    "BuildStatus",
    "CODE_TEMPLATES",
    # Immune
    "ImmuneSystem",
    "ImmuneConfig",
    "ThreatAlert",
    "ThreatLevel",
    "ThreatType",
    "ImmuneAction",
    # Growth
    "GrowthEngine",
    "GrowthMetrics",
    "GrowthStage",
    "PromotionRecord",
    "PromotionChannel",
    "FeedbackEntry",
    # Lifecycle
    "LifecycleOrchestrator",
    "LifecyclePhase",
    "OrganismStatus",
    "OrganismConfig",
    "CycleResult",
]
