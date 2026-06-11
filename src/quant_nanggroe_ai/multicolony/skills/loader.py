"""Dynamic skill loader for the Multi-Colony Ecosystem.

This module provides functionality to dynamically load skills from
Python modules, YAML configuration files, and plugin directories.

The skill loader discovers skill definitions, instantiates them,
and registers them with the SkillRegistry.
"""

from __future__ import annotations

import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

from quant_nanggroe_ai.multicolony.skills.registry import SkillMetadata, SkillRegistry

logger = structlog.get_logger(__name__)


class SkillDefinition(BaseModel):
    """A skill definition loaded from a configuration source.

    Attributes:
        name: Skill name.
        module_path: Python module path (e.g., 'my_package.skills.code_review').
        function_name: Name of the function within the module.
        description: Skill description.
        version: Semantic version.
        category: Skill category.
        tags: Tags for filtering.
        required_tools: Tools required by this skill.
        input_schema: JSON Schema for inputs.
        output_schema: JSON Schema for outputs.
        author: Skill author.
        enabled: Whether the skill should be loaded.
    """

    name: str
    module_path: str
    function_name: str = "execute"
    description: str = ""
    version: str = "0.1.0"
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    author: str = "system"
    enabled: bool = True


class LoaderResult(BaseModel):
    """Result of a skill loading operation.

    Attributes:
        definition: The skill definition that was loaded.
        success: Whether loading succeeded.
        error_message: Error details if loading failed.
        skill_id: ID of the registered skill (if successful).
    """

    definition: SkillDefinition
    success: bool = True
    error_message: str | None = None
    skill_id: str | None = None


class SkillLoader:
    """Dynamically loads and registers skills from various sources.

    The skill loader can import skill functions from Python modules,
    scan directories for skill plugins, and register them with the
    SkillRegistry.

    Example::

        loader = SkillLoader(registry)
        results = loader.load_from_module("my_package.skills")
        results = loader.load_from_directory("/path/to/skills")
    """

    def __init__(self, registry: SkillRegistry) -> None:
        """Initialize the skill loader.

        Args:
            registry: The skill registry to register loaded skills with.
        """
        self._registry = registry
        self._loaded_modules: set[str] = set()
        self._log = logger.bind(component="skill_loader")

    def load_from_module(
        self,
        module_path: str,
        function_name: str = "execute",
        name: str | None = None,
        description: str = "",
        category: str = "general",
        tags: list[str] | None = None,
    ) -> LoaderResult:
        """Load a skill from a Python module.

        Args:
            module_path: Dotted Python module path.
            function_name: Name of the skill function in the module.
            name: Override skill name (defaults to module's last part).
            description: Skill description.
            category: Skill category.
            tags: Tags for filtering.

        Returns:
            A loader result indicating success or failure.
        """
        definition = SkillDefinition(
            name=name or module_path.rsplit(".", 1)[-1],
            module_path=module_path,
            function_name=function_name,
            description=description,
            category=category,
            tags=tags or [],
        )

        try:
            fn = self._import_function(
                module_path,
                function_name,
            )

            if fn is None:
                return LoaderResult(
                    definition=definition,
                    success=False,
                    error_message=f"Function '{function_name}' not found in '{module_path}'.",
                )

            metadata = self._registry.register(
                name=definition.name,
                fn=fn,
                description=definition.description,
                version=definition.version,
                category=definition.category,
                tags=definition.tags,
                required_tools=definition.required_tools,
                input_schema=definition.input_schema,
                output_schema=definition.output_schema,
                author=definition.author,
            )

            self._loaded_modules.add(module_path)
            self._log.info(
                "skill_loaded_from_module",
                module_path=module_path,
                name=definition.name,
            )

            return LoaderResult(
                definition=definition,
                success=True,
                skill_id=metadata.skill_id,
            )

        except Exception as exc:
            self._log.error(
                "skill_load_failed",
                module_path=module_path,
                error=str(exc),
            )
            return LoaderResult(
                definition=definition,
                success=False,
                error_message=str(exc),
            )

    def load_from_definitions(
        self,
        definitions: list[SkillDefinition],
    ) -> list[LoaderResult]:
        """Load multiple skills from skill definitions.

        Args:
            definitions: List of skill definitions to load.

        Returns:
            A list of loader results.
        """
        results = []
        for definition in definitions:
            if not definition.enabled:
                self._log.info(
                    "skill_skipped_disabled",
                    name=definition.name,
                )
                continue

            try:
                fn = self._import_function(
                    definition.module_path,
                    definition.function_name,
                )

                if fn is None:
                    results.append(LoaderResult(
                        definition=definition,
                        success=False,
                        error_message=(
                            f"Function '{definition.function_name}' not found "
                            f"in '{definition.module_path}'."
                        ),
                    ))
                    continue

                metadata = self._registry.register(
                    name=definition.name,
                    fn=fn,
                    description=definition.description,
                    version=definition.version,
                    category=definition.category,
                    tags=definition.tags,
                    required_tools=definition.required_tools,
                    input_schema=definition.input_schema,
                    output_schema=definition.output_schema,
                    author=definition.author,
                )

                results.append(LoaderResult(
                    definition=definition,
                    success=True,
                    skill_id=metadata.skill_id,
                ))

            except Exception as exc:
                results.append(LoaderResult(
                    definition=definition,
                    success=False,
                    error_message=str(exc),
                ))

        return results

    def load_from_directory(
        self,
        directory: str | Path,
        function_name: str = "execute",
        category: str = "general",
    ) -> list[LoaderResult]:
        """Load skills from all Python files in a directory.

        Scans the directory for Python files and attempts to load
        the specified function from each as a skill.

        Args:
            directory: Path to the skills directory.
            function_name: Name of the skill function to look for.
            category: Default category for discovered skills.

        Returns:
            A list of loader results.
        """
        directory = Path(directory)
        if not directory.is_dir():
            self._log.warning("skills_directory_not_found", path=str(directory))
            return []

        results = []
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem
            skill_name = module_name.replace("_", " ").title().replace(" ", "")

            # Build module path from directory
            module_path = self._build_module_path(directory, py_file)

            result = self.load_from_module(
                module_path=module_path,
                function_name=function_name,
                name=skill_name,
                category=category,
            )
            results.append(result)

        self._log.info(
            "skills_loaded_from_directory",
            directory=str(directory),
            total=len(results),
            successful=sum(1 for r in results if r.success),
        )

        return results

    def _import_function(
        self,
        module_path: str,
        function_name: str,
    ) -> Callable | None:
        """Import a function from a module path.

        Args:
            module_path: Dotted Python module path.
            function_name: Name of the function to import.

        Returns:
            The imported function, or None if not found.
        """
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            self._log.warning("module_import_failed", module_path=module_path)
            return None

        fn = getattr(module, function_name, None)
        if fn is None or not callable(fn):
            return None

        return fn

    def _build_module_path(self, directory: Path, py_file: Path) -> str:
        """Build a Python module path from a directory and file.

        Args:
            directory: The directory containing the file.
            py_file: The Python file.

        Returns:
            A dotted module path string.
        """
        # Try to find the package root
        parts = []
        current = py_file.parent
        while current != current.parent:
            init_file = current / "__init__.py"
            if init_file.exists():
                parts.insert(0, current.name)
                current = current.parent
            else:
                break

        parts.append(py_file.stem)
        return ".".join(parts)
