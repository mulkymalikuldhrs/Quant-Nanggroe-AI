"""Skill system for the AI-MultiColony harness.

Implements Markdown-based skill definitions with dynamic loading,
skill registry, and execution context management.

Skills are defined as Markdown documents with structured frontmatter
that specifies the skill's name, description, parameters, and
execution template.  They can be loaded from files or defined
programmatically.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Models ───────────────────────────────────────────────────────────────────


class SkillParameter(BaseModel):
    """A parameter definition for a skill."""
    model_config = ConfigDict(frozen=False)

    name: str = ""
    type: str = "string"  # string, int, float, bool, list, dict
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    choices: Optional[List[str]] = None


class SkillDefinition(BaseModel):
    """A skill definition with metadata and execution template."""
    model_config = ConfigDict(frozen=False)

    skill_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    category: str = "general"  # research, analysis, code, data, communication
    tags: List[str] = Field(default_factory=list)
    parameters: List[SkillParameter] = Field(default_factory=list)
    template: str = ""  # Execution template (Markdown or prompt template)
    author: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    enabled: bool = True

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """Validate provided parameters against the skill definition.

        Returns
        -------
        list[str]
            List of validation errors (empty if valid).
        """
        errors: List[str] = []
        param_map = {p.name: p for p in self.parameters}

        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in params:
                if param.default is None:
                    errors.append(f"Missing required parameter: {param.name}")

        # Check parameter types
        for key, value in params.items():
            param_def = param_map.get(key)
            if param_def is None:
                errors.append(f"Unknown parameter: {key}")
                continue

            expected_type = param_def.type
            type_map = {
                "string": str,
                "int": int,
                "float": (int, float),
                "bool": bool,
                "list": list,
                "dict": dict,
            }
            expected = type_map.get(expected_type)
            if expected and not isinstance(value, expected):
                errors.append(
                    f"Parameter '{key}' expected type {expected_type}, got {type(value).__name__}"
                )

            # Check choices
            if param_def.choices and value not in param_def.choices:
                errors.append(
                    f"Parameter '{key}' must be one of {param_def.choices}, got {value}"
                )

        return errors


class SkillExecution(BaseModel):
    """Record of a skill execution."""
    model_config = ConfigDict(frozen=False)

    execution_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    skill_id: str = ""
    skill_name: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0


# ── Markdown parsing ────────────────────────────────────────────────────────


class SkillParser:
    """Parse Markdown-based skill definitions.

    Expected format::

        ---
        name: Research Market
        description: Research market conditions
        version: 1.0.0
        category: research
        tags: [market, research, analysis]
        parameters:
          - name: symbol
            type: string
            required: true
          - name: timeframe
            type: string
            required: false
            default: 1d
        ---

        ## Instructions

        Analyze the market for {{symbol}} over {{timeframe}}.
    """

    @staticmethod
    def parse(markdown: str) -> SkillDefinition:
        """Parse a Markdown skill definition.

        Parameters
        ----------
        markdown:
            Markdown string with frontmatter.

        Returns
        -------
        SkillDefinition
            Parsed skill definition.
        """
        # Extract frontmatter
        frontmatter: Dict[str, Any] = {}
        template = markdown

        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", markdown, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            template = fm_match.group(2)

            for line in fm_text.strip().split("\n"):
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()

                # Handle list values
                if value.startswith("[") and value.endswith("]"):
                    items = [i.strip().strip("'\"") for i in value[1:-1].split(",")]
                    frontmatter[key] = items
                elif value.lower() == "true":
                    frontmatter[key] = True
                elif value.lower() == "false":
                    frontmatter[key] = False
                else:
                    frontmatter[key] = value

        # Parse parameters from frontmatter
        parameters: List[SkillParameter] = []
        param_section = re.search(
            r"parameters:\s*\n((?:\s+-\s+.*\n)*)", markdown,
        )
        if param_section:
            param_text = param_section.group(1)
            current_param: Dict[str, Any] = {}
            for line in param_text.strip().split("\n"):
                line = line.strip().lstrip("- ")
                if not line:
                    continue
                if ":" not in line:
                    continue
                pkey, _, pval = line.partition(":")
                pkey = pkey.strip()
                pval = pval.strip()

                if pkey == "name":
                    if current_param:
                        parameters.append(SkillParameter(**current_param))
                    current_param = {"name": pval}
                elif pkey == "type":
                    current_param["type"] = pval
                elif pkey == "required":
                    current_param["required"] = pval.lower() == "true"
                elif pkey == "default":
                    current_param["default"] = pval
                elif pkey == "description":
                    current_param["description"] = pval
                elif pkey == "choices":
                    if pval.startswith("[") and pval.endswith("]"):
                        current_param["choices"] = [
                            i.strip().strip("'\"") for i in pval[1:-1].split(",")
                        ]

            if current_param:
                parameters.append(SkillParameter(**current_param))

        return SkillDefinition(
            name=frontmatter.get("name", "unnamed"),
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            category=frontmatter.get("category", "general"),
            tags=frontmatter.get("tags", []),
            parameters=parameters,
            template=template.strip(),
            author=frontmatter.get("author", ""),
        )

    @staticmethod
    def render_template(template: str, params: Dict[str, Any]) -> str:
        """Render a skill template with parameter substitution.

        Replaces ``{{param_name}}`` placeholders with parameter values.
        """
        result = template
        for key, value in params.items():
            result = result.replace("{{" + key + "}}", str(value))
        # Remove any unsubstituted placeholders
        result = re.sub(r"\{\{\w+\}\}", "", result)
        return result


# ── Skill Registry ──────────────────────────────────────────────────────────


class SkillRegistry:
    """Registry for skill definitions with dynamic loading and execution.

    Supports programmatic registration, Markdown parsing, template
    rendering, and execution tracking.

    Usage::

        registry = SkillRegistry()
        registry.register(skill_def)
        result = await registry.execute("research_market", {"symbol": "AAPL"})
    """

    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
        self._executions: List[SkillExecution] = []
        self._action_map: Dict[str, Callable] = {}

    # ── Registration ────────────────────────────────────────────────────

    def register(self, skill: SkillDefinition, action: Optional[Callable] = None) -> None:
        """Register a skill definition.

        Parameters
        ----------
        skill:
            SkillDefinition to register.
        action:
            Optional callable to execute when the skill is invoked.
        """
        self._skills[skill.name] = skill
        if action is not None:
            self._action_map[skill.name] = action
        logger.info("Registered skill: %s (%s)", skill.name, skill.skill_id)

    def register_from_markdown(self, markdown: str, action: Optional[Callable] = None) -> SkillDefinition:
        """Parse and register a skill from Markdown.

        Parameters
        ----------
        markdown:
            Markdown skill definition.
        action:
            Optional execution callable.

        Returns
        -------
        SkillDefinition
            The parsed and registered skill.
        """
        skill = SkillParser.parse(markdown)
        self.register(skill, action)
        return skill

    def unregister(self, name: str) -> bool:
        """Unregister a skill by name."""
        if name in self._skills:
            del self._skills[name]
            self._action_map.pop(name, None)
            return True
        return False

    def get(self, name: str) -> Optional[SkillDefinition]:
        """Look up a skill by name."""
        return self._skills.get(name)

    # ── Execution ───────────────────────────────────────────────────────

    async def execute(self, name: str, params: Optional[Dict[str, Any]] = None) -> SkillExecution:
        """Execute a registered skill.

        Parameters
        ----------
        name:
            Skill name.
        params:
            Parameters to pass to the skill.

        Returns
        -------
        SkillExecution
            Execution record with result or error.
        """
        params = params or {}
        execution = SkillExecution(
            skill_name=name,
            parameters=params,
            status="running",
            started_at=datetime.now(timezone.utc),
        )

        skill = self._skills.get(name)
        if skill is None:
            execution.status = "failed"
            execution.error = f"Skill '{name}' not found"
            execution.completed_at = datetime.now(timezone.utc)
            self._executions.append(execution)
            return execution

        execution.skill_id = skill.skill_id

        # Validate parameters
        errors = skill.validate_params(params)
        if errors:
            execution.status = "failed"
            execution.error = f"Parameter validation failed: {'; '.join(errors)}"
            execution.completed_at = datetime.now(timezone.utc)
            self._executions.append(execution)
            return execution

        # Execute
        start_time = datetime.now(timezone.utc)
        try:
            action = self._action_map.get(name)
            if action is not None:
                import asyncio
                if asyncio.iscoroutinefunction(action):
                    result = await action(params)
                else:
                    result = action(params)
            else:
                # Render template
                result = SkillParser.render_template(skill.template, params)

            execution.status = "completed"
            execution.result = result
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
        finally:
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at and execution.completed_at:
                delta = execution.completed_at - execution.started_at
                execution.duration_ms = delta.total_seconds() * 1000

        self._executions.append(execution)
        return execution

    # ── Query ───────────────────────────────────────────────────────────

    def list_skills(self, category: Optional[str] = None) -> List[SkillDefinition]:
        """List all registered skills, optionally filtered by category."""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    def find_by_tag(self, tag: str) -> List[SkillDefinition]:
        """Find skills by tag."""
        return [s for s in self._skills.values() if tag in s.tags]

    @property
    def skill_count(self) -> int:
        return len(self._skills)

    @property
    def execution_history(self) -> List[SkillExecution]:
        return list(self._executions)

    @property
    def stats(self) -> Dict[str, Any]:
        """Registry statistics."""
        total = len(self._executions)
        completed = sum(1 for e in self._executions if e.status == "completed")
        failed = sum(1 for e in self._executions if e.status == "failed")
        return {
            "skill_count": self.skill_count,
            "total_executions": total,
            "completed_executions": completed,
            "failed_executions": failed,
            "success_rate": completed / max(1, total),
        }
