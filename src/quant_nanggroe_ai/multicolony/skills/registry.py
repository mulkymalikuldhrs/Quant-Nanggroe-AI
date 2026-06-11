"""Skill registry for the Multi-Colony Ecosystem.

This module provides a registry for managing skills that agents can
use within colonies. Skills are reusable capabilities that can be
registered, loaded, and executed on demand.

A skill is a named, versioned capability with defined inputs/outputs
that can be dynamically discovered and invoked by agents.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class SkillStatus(str, Enum):
    """Status of a registered skill."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    ERROR = "error"


class SkillMetadata(BaseModel):
    """Metadata for a registered skill.

    Attributes:
        skill_id: Unique identifier for the skill.
        name: Human-readable name.
        description: What the skill does.
        version: Semantic version string.
        category: Skill category (e.g., 'coding', 'analysis').
        tags: Tags for search and filtering.
        status: Current skill status.
        required_tools: Tools required by this skill.
        input_schema: JSON Schema for skill inputs.
        output_schema: JSON Schema for skill outputs.
        author: Who created the skill.
        created_at: When the skill was registered.
        updated_at: When the skill was last updated.
        execution_count: Number of times the skill has been executed.
        avg_execution_time_ms: Average execution time in milliseconds.
        error_count: Number of execution errors.
    """

    skill_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    version: str = "0.1.0"
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    status: SkillStatus = SkillStatus.ACTIVE
    required_tools: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    author: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_count: int = 0
    avg_execution_time_ms: float = 0.0
    error_count: int = 0


class SkillExecution(BaseModel):
    """Record of a skill execution.

    Attributes:
        execution_id: Unique identifier for this execution.
        skill_id: ID of the skill that was executed.
        agent_id: ID of the agent that executed the skill.
        inputs: The inputs provided to the skill.
        outputs: The outputs produced by the skill.
        success: Whether the execution succeeded.
        error_message: Error details if execution failed.
        execution_time_ms: Execution time in milliseconds.
        timestamp: When the execution occurred.
    """

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str
    agent_id: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: Any = None
    success: bool = True
    error_message: str | None = None
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SkillRegistry:
    """Registry for managing and executing skills.

    The skill registry allows skills to be registered with metadata and
    execution functions, then discovered and invoked by agents.

    Example::

        registry = SkillRegistry()

        # Register a skill
        registry.register(
            name="code_review",
            fn=review_code,
            description="Reviews code for quality and issues",
            category="coding",
        )

        # List available skills
        skills = registry.list_skills()

        # Execute a skill
        result = await registry.execute("code_review", inputs={"code": "..."})
    """

    def __init__(self) -> None:
        """Initialize the skill registry."""
        self._skills: dict[str, SkillMetadata] = {}
        self._functions: dict[str, Callable] = {}
        self._execution_history: list[SkillExecution] = []
        self._log = logger.bind(component="skill_registry")

    def register(
        self,
        name: str,
        fn: Callable,
        description: str = "",
        version: str = "0.1.0",
        category: str = "general",
        tags: list[str] | None = None,
        required_tools: list[str] | None = None,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        author: str = "system",
        skill_id: str | None = None,
    ) -> SkillMetadata:
        """Register a new skill.

        Args:
            name: Human-readable skill name (must be unique).
            fn: The skill execution function (sync or async).
            description: What the skill does.
            version: Semantic version string.
            category: Skill category.
            tags: Tags for search and filtering.
            required_tools: Tools required by this skill.
            input_schema: JSON Schema for inputs.
            output_schema: JSON Schema for outputs.
            author: Skill author.
            skill_id: Optional custom skill ID.

        Returns:
            The registered skill metadata.

        Raises:
            SkillAlreadyRegisteredError: If a skill with the same name exists.
        """
        # Check for duplicate name
        for existing in self._skills.values():
            if existing.name == name:
                raise SkillAlreadyRegisteredError(
                    f"Skill '{name}' is already registered."
                )

        metadata = SkillMetadata(
            skill_id=skill_id or str(uuid.uuid4()),
            name=name,
            description=description,
            version=version,
            category=category,
            tags=tags or [],
            required_tools=required_tools or [],
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            author=author,
        )

        self._skills[metadata.skill_id] = metadata
        self._functions[metadata.skill_id] = fn

        self._log.info(
            "skill_registered",
            skill_id=metadata.skill_id,
            name=name,
            category=category,
        )

        return metadata

    def unregister(self, skill_id: str) -> None:
        """Unregister a skill.

        Args:
            skill_id: ID of the skill to unregister.

        Raises:
            SkillNotFoundError: If the skill is not found.
        """
        if skill_id not in self._skills:
            raise SkillNotFoundError(f"Skill {skill_id} not found.")

        metadata = self._skills.pop(skill_id)
        self._functions.pop(skill_id, None)

        self._log.info(
            "skill_unregistered",
            skill_id=skill_id,
            name=metadata.name,
        )

    def load(self, skill_id: str) -> SkillMetadata:
        """Load a skill's metadata by ID.

        Args:
            skill_id: ID of the skill to load.

        Returns:
            The skill metadata.

        Raises:
            SkillNotFoundError: If the skill is not found.
        """
        if skill_id not in self._skills:
            raise SkillNotFoundError(f"Skill {skill_id} not found.")
        return self._skills[skill_id]

    def load_by_name(self, name: str) -> SkillMetadata:
        """Load a skill's metadata by name.

        Args:
            name: Name of the skill to load.

        Returns:
            The skill metadata.

        Raises:
            SkillNotFoundError: If the skill is not found.
        """
        for metadata in self._skills.values():
            if metadata.name == name:
                return metadata
        raise SkillNotFoundError(f"Skill '{name}' not found.")

    async def execute(
        self,
        skill_id_or_name: str,
        inputs: dict[str, Any] | None = None,
        agent_id: str | None = None,
    ) -> SkillExecution:
        """Execute a skill by ID or name.

        Args:
            skill_id_or_name: Skill ID or name to execute.
            inputs: Input parameters for the skill.
            agent_id: ID of the executing agent.

        Returns:
            A skill execution record.

        Raises:
            SkillNotFoundError: If the skill is not found.
            SkillExecutionError: If the skill execution fails.
        """
        # Resolve skill by ID or name
        metadata = self._resolve_skill(skill_id_or_name)
        if metadata is None:
            raise SkillNotFoundError(
                f"Skill '{skill_id_or_name}' not found."
            )

        fn = self._functions.get(metadata.skill_id)
        if fn is None:
            raise SkillExecutionError(
                f"No execution function for skill '{metadata.name}'."
            )

        if metadata.status == SkillStatus.DISABLED:
            raise SkillExecutionError(
                f"Skill '{metadata.name}' is disabled."
            )

        execution = SkillExecution(
            skill_id=metadata.skill_id,
            agent_id=agent_id,
            inputs=inputs or {},
        )

        import time

        start_time = time.monotonic()

        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(**(inputs or {}))
            else:
                result = fn(**(inputs or {}))

            execution.outputs = result
            execution.success = True

        except Exception as exc:
            execution.success = False
            execution.error_message = str(exc)
            metadata.error_count += 1

            self._log.error(
                "skill_execution_failed",
                skill_id=metadata.skill_id,
                name=metadata.name,
                error=str(exc),
            )
            raise SkillExecutionError(
                f"Skill '{metadata.name}' execution failed: {exc}"
            ) from exc

        finally:
            execution.execution_time_ms = (time.monotonic() - start_time) * 1000
            metadata.execution_count += 1

            # Update average execution time
            if metadata.execution_count > 0:
                metadata.avg_execution_time_ms = (
                    (metadata.avg_execution_time_ms * (metadata.execution_count - 1))
                    + execution.execution_time_ms
                ) / metadata.execution_count

            metadata.updated_at = datetime.now(timezone.utc)
            self._execution_history.append(execution)

        self._log.info(
            "skill_executed",
            skill_id=metadata.skill_id,
            name=metadata.name,
            execution_time_ms=execution.execution_time_ms,
        )

        return execution

    def list_skills(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        status: SkillStatus | None = None,
    ) -> list[SkillMetadata]:
        """List registered skills with optional filtering.

        Args:
            category: Filter by category.
            tags: Filter by tags (skills must have ALL specified tags).
            status: Filter by status.

        Returns:
            A list of matching skill metadata objects.
        """
        skills = list(self._skills.values())

        if category is not None:
            skills = [s for s in skills if s.category == category]

        if tags is not None:
            skills = [
                s for s in skills if all(t in s.tags for t in tags)
            ]

        if status is not None:
            skills = [s for s in skills if s.status == status]

        return skills

    def search_skills(self, query: str) -> list[SkillMetadata]:
        """Search skills by name, description, or tags.

        Args:
            query: Search query string.

        Returns:
            A list of matching skill metadata objects.
        """
        query_lower = query.lower()
        results = []

        for skill in self._skills.values():
            searchable = " ".join([
                skill.name,
                skill.description,
                " ".join(skill.tags),
                skill.category,
            ]).lower()

            if query_lower in searchable:
                results.append(skill)

        return results

    def get_execution_history(
        self,
        skill_id: str | None = None,
        agent_id: str | None = None,
        limit: int | None = None,
    ) -> list[SkillExecution]:
        """Get skill execution history.

        Args:
            skill_id: Filter by skill ID.
            agent_id: Filter by agent ID.
            limit: Maximum number of records to return.

        Returns:
            A list of skill execution records.
        """
        history = list(reversed(self._execution_history))

        if skill_id is not None:
            history = [h for h in history if h.skill_id == skill_id]
        if agent_id is not None:
            history = [h for h in history if h.agent_id == agent_id]
        if limit is not None:
            history = history[:limit]

        return history

    def _resolve_skill(self, skill_id_or_name: str) -> SkillMetadata | None:
        """Resolve a skill by ID or name.

        Args:
            skill_id_or_name: Skill ID or name.

        Returns:
            The skill metadata, or None if not found.
        """
        # Try by ID first
        if skill_id_or_name in self._skills:
            return self._skills[skill_id_or_name]

        # Try by name
        for metadata in self._skills.values():
            if metadata.name == skill_id_or_name:
                return metadata

        return None


class SkillAlreadyRegisteredError(Exception):
    """Raised when attempting to register a duplicate skill."""


class SkillNotFoundError(Exception):
    """Raised when a skill is not found in the registry."""


class SkillExecutionError(Exception):
    """Raised when a skill execution fails."""
