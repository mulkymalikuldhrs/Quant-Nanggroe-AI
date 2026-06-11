"""L4: Procedural memory for the Multi-Colony Ecosystem.

This module implements procedural memory (Layer 4) for skill extraction
and optimization, with DSPy integration for programmatic skill refinement.

Procedural memory stores learned procedures and skills that agents have
acquired through experience, enabling skill extraction from successful
task executions and optimization over time.

Memory Hierarchy:
    L1: Working memory (immediate context)
    L2: Episodic memory (event sequences)
    L3: Semantic memory (facts and knowledge)
    L4: Procedural memory (this module - skills and procedures)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ProcedureStatus(str, Enum):
    """Status of a stored procedure."""

    DRAFT = "draft"
    TESTED = "tested"
    OPTIMIZED = "optimized"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class Procedure(BaseModel):
    """A procedure stored in procedural memory.

    A procedure represents a learned sequence of steps that accomplishes
    a specific task, extracted from agent experiences.

    Attributes:
        procedure_id: Unique identifier for the procedure.
        name: Human-readable name for the procedure.
        description: What the procedure accomplishes.
        steps: Ordered list of steps in the procedure.
        inputs: Expected input parameters.
        outputs: Expected output format.
        preconditions: Conditions that must be true before execution.
        postconditions: Conditions that will be true after execution.
        status: Current procedure status.
        success_rate: Fraction of successful executions (0.0-1.0).
        execution_count: Number of times the procedure has been executed.
        avg_execution_time_ms: Average execution time.
        source_episodes: Episode IDs from which this was extracted.
        version: Procedure version number.
        parent_procedure_id: ID of the parent procedure (for optimization chains).
        dspy_signature: DSPy signature for programmatic optimization.
        tags: Tags for categorization.
        metadata: Additional metadata.
        created_at: When the procedure was created.
        updated_at: When the procedure was last updated.
    """

    procedure_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    status: ProcedureStatus = ProcedureStatus.DRAFT
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_count: int = 0
    avg_execution_time_ms: float = 0.0
    source_episodes: list[str] = Field(default_factory=list)
    version: int = 1
    parent_procedure_id: str | None = None
    dspy_signature: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExtractionResult(BaseModel):
    """Result of a skill extraction operation.

    Attributes:
        procedure_id: ID of the extracted procedure.
        source_episode_ids: Episode IDs used for extraction.
        steps_extracted: Number of steps extracted.
        confidence: Extraction confidence score (0.0-1.0).
        suggestions: Improvement suggestions for the procedure.
    """

    procedure_id: str
    source_episode_ids: list[str]
    steps_extracted: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    suggestions: list[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    """Result of a procedure optimization operation.

    Attributes:
        original_procedure_id: ID of the original procedure.
        optimized_procedure_id: ID of the optimized procedure.
        improvement_score: Improvement in success rate (0.0-1.0).
        changes: Description of changes made.
        steps_before: Number of steps before optimization.
        steps_after: Number of steps after optimization.
    """

    original_procedure_id: str
    optimized_procedure_id: str
    improvement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    changes: list[str] = Field(default_factory=list)
    steps_before: int = 0
    steps_after: int = 0


class ProceduralMemory:
    """L4 Procedural memory with DSPy integration for skill optimization.

    This class manages procedural memory for agents, providing methods
    to extract skills from successful task executions and optimize
    procedures over time.

    Note:
        DSPy integration is stubbed. In production, this would use
        the DSPy library for programmatic prompt optimization.

    Example::

        memory = ProceduralMemory(agent_id="agent-1")
        result = await memory.extract_skill(
            name="code_review",
            episode_ids=["ep-1", "ep-2", "ep-3"],
        )
        opt_result = await memory.optimize_skill(result.procedure_id)
    """

    def __init__(
        self,
        agent_id: str = "",
        colony_id: str = "",
    ) -> None:
        """Initialize procedural memory.

        Args:
            agent_id: ID of the agent this memory belongs to.
            colony_id: ID of the colony.
        """
        self._agent_id = agent_id
        self._colony_id = colony_id
        self._procedures: dict[str, Procedure] = {}
        self._dspy_optimizer: Any = None  # Stub for DSPy optimizer
        self._log = logger.bind(
            agent_id=agent_id,
            component="procedural_memory",
        )

    @property
    def procedure_count(self) -> int:
        """Number of stored procedures."""
        return len(self._procedures)

    async def extract_skill(
        self,
        name: str,
        episode_ids: list[str] | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ) -> ExtractionResult:
        """Extract a skill/procedure from successful task executions.

        This method analyzes past task executions (episodes) and
        extracts a reusable procedure.

        Args:
            name: Name for the extracted procedure.
            episode_ids: IDs of source episodes to extract from.
            description: Description of the procedure.
            tags: Tags for categorization.

        Returns:
            The extraction result with the new procedure ID.
        """
        # Stub: In production, would use DSPy/LM to analyze episodes
        # and extract structured steps

        # Generate placeholder steps
        steps = [
            {"step": 1, "action": "analyze_input", "description": "Analyze the input parameters"},
            {"step": 2, "action": "plan_execution", "description": "Plan the execution strategy"},
            {"step": 3, "action": "execute_steps", "description": "Execute the planned steps"},
            {"step": 4, "action": "verify_output", "description": "Verify the output meets requirements"},
        ]

        procedure = Procedure(
            name=name,
            description=description or f"Extracted procedure: {name}",
            steps=steps,
            inputs={"task_input": "any"},
            outputs={"task_output": "any"},
            status=ProcedureStatus.DRAFT,
            source_episodes=episode_ids or [],
            tags=tags or [],
        )

        self._procedures[procedure.procedure_id] = procedure

        result = ExtractionResult(
            procedure_id=procedure.procedure_id,
            source_episode_ids=episode_ids or [],
            steps_extracted=len(steps),
            confidence=0.7,  # Placeholder confidence
            suggestions=[
                "Test the extracted procedure on similar tasks",
                "Consider adding error handling steps",
            ],
        )

        self._log.info(
            "skill_extracted",
            procedure_id=procedure.procedure_id,
            name=name,
            steps=len(steps),
        )

        return result

    async def optimize_skill(
        self,
        procedure_id: str,
        optimization_rounds: int = 3,
    ) -> OptimizationResult:
        """Optimize a procedure using DSPy-style optimization.

        This method iteratively refines a procedure to improve its
        success rate and efficiency.

        Args:
            procedure_id: ID of the procedure to optimize.
            optimization_rounds: Number of optimization iterations.

        Returns:
            The optimization result.

        Raises:
            ProcedureNotFoundError: If the procedure is not found.
        """
        if procedure_id not in self._procedures:
            raise ProcedureNotFoundError(f"Procedure {procedure_id} not found.")

        original = self._procedures[procedure_id]
        steps_before = len(original.steps)

        # Stub: In production, would use DSPy optimizer
        # For now, simulate optimization by creating an improved version

        optimized_steps = list(original.steps)
        # Simulate optimization: remove redundant steps, improve descriptions
        for step in optimized_steps:
            step["optimized"] = True

        optimized = Procedure(
            name=f"{original.name}_v{original.version + 1}",
            description=original.description + " (optimized)",
            steps=optimized_steps,
            inputs=dict(original.inputs),
            outputs=dict(original.outputs),
            preconditions=list(original.preconditions),
            postconditions=list(original.postconditions),
            status=ProcedureStatus.OPTIMIZED,
            success_rate=min(original.success_rate + 0.1, 1.0),
            parent_procedure_id=original.procedure_id,
            version=original.version + 1,
            tags=list(original.tags),
            metadata={"optimization_rounds": optimization_rounds},
        )

        self._procedures[optimized.procedure_id] = optimized

        result = OptimizationResult(
            original_procedure_id=procedure_id,
            optimized_procedure_id=optimized.procedure_id,
            improvement_score=0.1,  # Simulated improvement
            changes=[
                f"Optimized over {optimization_rounds} rounds",
                "Improved step descriptions",
                "Increased success rate estimate",
            ],
            steps_before=steps_before,
            steps_after=len(optimized_steps),
        )

        self._log.info(
            "skill_optimized",
            original_id=procedure_id,
            optimized_id=optimized.procedure_id,
            improvement=result.improvement_score,
        )

        return result

    async def get_procedure(self, procedure_id: str) -> Procedure:
        """Get a specific procedure by ID.

        Args:
            procedure_id: ID of the procedure.

        Returns:
            The procedure.

        Raises:
            ProcedureNotFoundError: If the procedure is not found.
        """
        if procedure_id not in self._procedures:
            raise ProcedureNotFoundError(f"Procedure {procedure_id} not found.")
        return self._procedures[procedure_id]

    async def list_procedures(
        self,
        status: ProcedureStatus | None = None,
        tags: list[str] | None = None,
    ) -> list[Procedure]:
        """List procedures with optional filtering.

        Args:
            status: Filter by status.
            tags: Filter by tags.

        Returns:
            A list of matching procedures.
        """
        procedures = list(self._procedures.values())

        if status is not None:
            procedures = [p for p in procedures if p.status == status]

        if tags is not None:
            procedures = [
                p for p in procedures
                if all(t in p.tags for t in tags)
            ]

        return procedures

    async def update_procedure_status(
        self,
        procedure_id: str,
        status: ProcedureStatus,
    ) -> Procedure:
        """Update a procedure's status.

        Args:
            procedure_id: ID of the procedure.
            status: New status.

        Returns:
            The updated procedure.

        Raises:
            ProcedureNotFoundError: If the procedure is not found.
        """
        if procedure_id not in self._procedures:
            raise ProcedureNotFoundError(f"Procedure {procedure_id} not found.")

        procedure = self._procedures[procedure_id]
        procedure.status = status
        procedure.updated_at = datetime.now(timezone.utc)

        self._log.info(
            "procedure_status_updated",
            procedure_id=procedure_id,
            new_status=status.value,
        )

        return procedure

    async def record_execution(
        self,
        procedure_id: str,
        success: bool,
        execution_time_ms: float = 0.0,
    ) -> None:
        """Record a procedure execution for tracking success rate.

        Args:
            procedure_id: ID of the procedure that was executed.
            success: Whether the execution succeeded.
            execution_time_ms: Execution time in milliseconds.

        Raises:
            ProcedureNotFoundError: If the procedure is not found.
        """
        if procedure_id not in self._procedures:
            raise ProcedureNotFoundError(f"Procedure {procedure_id} not found.")

        procedure = self._procedures[procedure_id]
        procedure.execution_count += 1

        # Update running success rate
        if procedure.execution_count == 1:
            procedure.success_rate = 1.0 if success else 0.0
        else:
            old_total = (procedure.execution_count - 1) * procedure.success_rate
            procedure.success_rate = (old_total + (1.0 if success else 0.0)) / procedure.execution_count

        # Update average execution time
        if procedure.execution_count == 1:
            procedure.avg_execution_time_ms = execution_time_ms
        else:
            old_avg = procedure.avg_execution_time_ms
            procedure.avg_execution_time_ms = (
                (old_avg * (procedure.execution_count - 1) + execution_time_ms)
                / procedure.execution_count
            )

        procedure.updated_at = datetime.now(timezone.utc)

    async def delete_procedure(self, procedure_id: str) -> None:
        """Delete a procedure from memory.

        Args:
            procedure_id: ID of the procedure to delete.

        Raises:
            ProcedureNotFoundError: If the procedure is not found.
        """
        if procedure_id not in self._procedures:
            raise ProcedureNotFoundError(f"Procedure {procedure_id} not found.")

        del self._procedures[procedure_id]
        self._log.info("procedure_deleted", procedure_id=procedure_id)

    def clear(self) -> None:
        """Clear all procedures from memory."""
        self._procedures.clear()
        self._log.info("procedural_memory_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics.

        Returns:
            A dictionary of memory statistics.
        """
        status_counts: dict[str, int] = {}
        for proc in self._procedures.values():
            status_counts[proc.status.value] = status_counts.get(proc.status.value, 0) + 1

        avg_success = (
            sum(p.success_rate for p in self._procedures.values()) / len(self._procedures)
            if self._procedures
            else 0.0
        )

        return {
            "agent_id": self._agent_id,
            "procedure_count": self.procedure_count,
            "status_counts": status_counts,
            "avg_success_rate": round(avg_success, 3),
        }


class ProcedureNotFoundError(Exception):
    """Raised when a procedure is not found in procedural memory."""
