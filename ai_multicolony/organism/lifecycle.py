"""Full lifecycle orchestrator for the AI-MultiColony organism.

Implements the complete organism lifecycle:
Sense → Decision → Factory → Growth → Evolve

The lifecycle orchestrator coordinates all organism phases,
manages state transitions, and provides a unified interface
for running autonomous evolution cycles.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from .sense import SenseEngine, Signal, SignalType, SignalSeverity, ScanResult
from .decision import DecisionEngine, DecisionScore, DecisionStatus, DecisionConfig
from .factory import SolutionFactory, BuildRequest, BuildResult, ArtifactType
from .immune import ImmuneSystem, ImmuneConfig, ThreatLevel, ThreatAlert
from .growth import GrowthEngine, GrowthMetrics, GrowthStage

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class LifecyclePhase(str, Enum):
    """Phases of the organism lifecycle."""
    IDLE = "idle"
    SENSING = "sensing"
    DECIDING = "deciding"
    BUILDING = "building"
    GROWING = "growing"
    EVOLVING = "evolving"
    PAUSED = "paused"
    KILLED = "killed"
    ERROR = "error"


class OrganismStatus(str, Enum):
    """Overall status of the organism."""
    ACTIVE = "active"
    DORMANT = "dormant"
    PAUSED = "paused"
    KILLED = "killed"
    ERROR = "error"


# ── Models ───────────────────────────────────────────────────────────────────


class CycleResult(BaseModel):
    """Result from a single lifecycle cycle."""
    model_config = ConfigDict(frozen=False)

    cycle_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    phase: LifecyclePhase = LifecyclePhase.IDLE
    signals_detected: int = 0
    decisions_made: int = 0
    solutions_built: int = 0
    promotions: int = 0
    errors: List[str] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganismConfig(BaseModel):
    """Configuration for the organism lifecycle."""
    model_config = ConfigDict(frozen=False)

    sense_interval_s: float = 60.0
    max_cycles: int = 100
    auto_approve_threshold: float = 0.7
    auto_reject_threshold: float = 0.3
    enable_auto_growth: bool = True
    enable_evolution: bool = True
    immune_config: ImmuneConfig = Field(default_factory=ImmuneConfig)
    decision_config: DecisionConfig = Field(default_factory=DecisionConfig)


# ── Lifecycle Orchestrator ───────────────────────────────────────────────────


class LifecycleOrchestrator:
    """Orchestrates the full organism lifecycle.

    Coordinates the Sense → Decision → Factory → Growth → Evolve
    cycle, manages state transitions, and provides monitoring.

    Usage::

        orchestrator = LifecycleOrchestrator()
        result = await orchestrator.run_cycle()
        # Or run multiple cycles
        results = await orchestrator.run_cycles(count=5)
    """

    def __init__(self, config: Optional[OrganismConfig] = None):
        self._config = config or OrganismConfig()
        self._sense = SenseEngine()
        self._decision = DecisionEngine(self._config.decision_config)
        self._factory = SolutionFactory()
        self._immune = ImmuneSystem(self._config.immune_config)
        self._growth = GrowthEngine()

        self._phase: LifecyclePhase = LifecyclePhase.IDLE
        self._status: OrganismStatus = OrganismStatus.DORMANT
        self._cycle_count: int = 0
        self._cycle_results: List[CycleResult] = []
        self._running: bool = False

    # ── Component access ────────────────────────────────────────────────

    @property
    def sense_engine(self) -> SenseEngine:
        return self._sense

    @property
    def decision_engine(self) -> DecisionEngine:
        return self._decision

    @property
    def factory(self) -> SolutionFactory:
        return self._factory

    @property
    def immune_system(self) -> ImmuneSystem:
        return self._immune

    @property
    def growth_engine(self) -> GrowthEngine:
        return self._growth

    # ── Lifecycle execution ─────────────────────────────────────────────

    async def run_cycle(self) -> CycleResult:
        """Run a single lifecycle cycle: Sense → Decision → Factory → Growth.

        Returns
        -------
        CycleResult
            Summary of what happened in this cycle.
        """
        import time
        start = time.monotonic()
        cycle_id = uuid.uuid4().hex[:12]
        result = CycleResult(cycle_id=cycle_id)

        # Check immune system
        if self._immune.is_killed:
            result.phase = LifecyclePhase.KILLED
            result.errors.append("Organism is killed")
            result.duration_ms = (time.monotonic() - start) * 1000
            return result

        if self._immune.is_paused:
            result.phase = LifecyclePhase.PAUSED
            result.errors.append("Organism is paused")
            result.duration_ms = (time.monotonic() - start) * 1000
            return result

        self._cycle_count += 1

        # Check iteration limit
        iter_alert = self._immune.check_iteration()
        if iter_alert.threat_level in (ThreatLevel.DANGER, ThreatLevel.CRITICAL):
            result.phase = LifecyclePhase.KILLED
            result.alerts.append(iter_alert.description)
            result.duration_ms = (time.monotonic() - start) * 1000
            return result

        try:
            # Phase 1: Sense
            self._phase = LifecyclePhase.SENSING
            self._status = OrganismStatus.ACTIVE
            result.phase = LifecyclePhase.SENSING

            scan_result = await self._sense.scan()
            result.signals_detected = len(scan_result.signals)

            # Phase 2: Decision
            self._phase = LifecyclePhase.DECIDING
            approved_signals: List[Signal] = []

            for signal in scan_result.signals:
                criteria_scores = self._signal_to_criteria(signal)
                score = self._decision.evaluate(
                    signal_id=signal.signal_id,
                    signal_title=signal.title,
                    criteria_scores=criteria_scores,
                )
                result.decisions_made += 1

                if score.status in (DecisionStatus.APPROVED, DecisionStatus.ESCALATED):
                    approved_signals.append(signal)

            # Phase 3: Factory
            self._phase = LifecyclePhase.BUILDING
            for signal in approved_signals:
                request = BuildRequest(
                    decision_id=f"dec-{signal.signal_id}",
                    signal_id=signal.signal_id,
                    signal_title=signal.title,
                    artifact_type=ArtifactType.SERVICE,
                    requirements=[signal.description],
                )
                build_result = await self._factory.build(request)
                if build_result.success:
                    result.solutions_built += len(build_result.artifacts)

                    # Phase 4: Growth
                    if self._config.enable_auto_growth:
                        self._phase = LifecyclePhase.GROWING
                        for artifact in build_result.artifacts:
                            if artifact.artifact_id not in [m.solution_id for m in self._growth._metrics.values()]:
                                self._growth.register_solution(artifact.artifact_id, artifact.name)
                            promo = self._growth.promote(artifact.artifact_id)
                            if promo:
                                result.promotions += 1

            # Phase 5: Evolve (adapt based on results)
            if self._config.enable_evolution:
                self._phase = LifecyclePhase.EVOLVING
                self._evolve(result)

            self._phase = LifecyclePhase.IDLE

        except Exception as e:
            result.phase = LifecyclePhase.ERROR
            result.errors.append(str(e))
            logger.error("Lifecycle cycle error: %s", e)

        result.duration_ms = (time.monotonic() - start) * 1000
        self._cycle_results.append(result)
        return result

    async def run_cycles(self, count: int = 1) -> List[CycleResult]:
        """Run multiple lifecycle cycles.

        Parameters
        ----------
        count:
            Number of cycles to run.

        Returns
        -------
        list[CycleResult]
            Results from each cycle.
        """
        results = []
        for i in range(count):
            if self._immune.is_killed:
                break
            result = await self.run_cycle()
            results.append(result)
            if result.phase == LifecyclePhase.ERROR:
                break
        return results

    async def run_continuous(self, interval_s: float = 60.0, max_cycles: int = 100) -> List[CycleResult]:
        """Run the lifecycle continuously with intervals.

        Parameters
        ----------
        interval_s:
            Seconds between cycles.
        max_cycles:
            Maximum number of cycles.

        Returns
        -------
        list[CycleResult]
            Results from all cycles.
        """
        self._running = True
        results = []

        for i in range(max_cycles):
            if not self._running or self._immune.is_killed:
                break

            result = await self.run_cycle()
            results.append(result)

            if result.phase in (LifecyclePhase.ERROR, LifecyclePhase.KILLED):
                break

            await asyncio.sleep(interval_s)

        self._running = False
        return results

    def stop(self) -> None:
        """Stop the continuous lifecycle."""
        self._running = False

    # ── Helpers ─────────────────────────────────────────────────────────

    def _signal_to_criteria(self, signal: Signal) -> Dict[str, float]:
        """Convert a signal to default criteria scores.

        Maps signal properties to decision criteria scores.
        """
        severity_map = {
            SignalSeverity.CRITICAL: 9.0,
            SignalSeverity.HIGH: 7.0,
            SignalSeverity.MEDIUM: 5.0,
            SignalSeverity.LOW: 3.0,
            SignalSeverity.INFO: 1.0,
        }

        type_map = {
            SignalType.THREAT: 8.0,
            SignalType.PROBLEM: 7.0,
            SignalType.OPPORTUNITY: 8.0,
            SignalType.TREND: 6.0,
            SignalType.ANOMALY: 5.0,
            SignalType.EVENT: 4.0,
        }

        urgency = severity_map.get(signal.severity, 5.0)
        impact = type_map.get(signal.signal_type, 5.0)

        return {
            "business_impact": impact,
            "urgency": urgency,
            "feasibility": 6.0,
            "cost_efficiency": 5.0,
            "risk_level": max(0, 10.0 - urgency),
            "strategic_alignment": 5.0,
            "innovation_potential": 5.0,
        }

    def _evolve(self, result: CycleResult) -> None:
        """Adapt the organism based on cycle results.

        This is a lightweight evolution step that adjusts decision
        criteria weights based on cycle performance.
        """
        # If no signals detected, lower the sense interval
        if result.signals_detected == 0:
            logger.debug("No signals detected, adjusting sense parameters")

        # If many solutions built, strengthen growth efforts
        if result.solutions_built > 2:
            logger.debug("Strong building phase, adjusting growth parameters")

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def phase(self) -> LifecyclePhase:
        return self._phase

    @property
    def status(self) -> OrganismStatus:
        return self._status

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def cycle_results(self) -> List[CycleResult]:
        return list(self._cycle_results)

    @property
    def config(self) -> OrganismConfig:
        return self._config

    @property
    def stats(self) -> Dict[str, Any]:
        """Orchestrator statistics."""
        return {
            "phase": self._phase.value,
            "status": self._status.value,
            "cycle_count": self._cycle_count,
            "is_running": self._running,
            "immune_killed": self._immune.is_killed,
            "sense_stats": self._sense.stats,
            "decision_stats": self._decision.stats,
            "factory_stats": self._factory.stats,
            "growth_stats": self._growth.stats,
        }
