"""AutoRegistry — Self-discovering component registry for QNA.

No manual __all__, no explicit imports needed. Any file placed in a monitored
directory is automatically discovered, imported, and registered.

Supports: strategies, agents, exchanges, providers, indicators, genes.

Usage:
    from quant_nanggroe.engine.registry import AutoRegistry
    
    # Auto-discover all strategies
    registry = AutoRegistry()
    registry.discover_all()
    
    # Get a strategy by name
    strat = registry.get("WyckoffStrategy")
    
    # List all registered
    registry.list_registered()
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Registry ────────────────────────────────────────────────────────


class AutoRegistry:
    """Self-discovering registry for QNA components.

    Scans directories for .py files, auto-imports them, and registers
    any class that matches a given base class or naming convention.
    """

    def __init__(self):
        self._registry: dict[str, type] = {}
        self._modules: dict[str, str] = {}  # module path per name

    # ── Discovery ───────────────────────────────────────────────────

    def discover_from_dir(
        self,
        directory: str | Path,
        base_class: Optional[type] = None,
        name_suffix: str = "",
        recursive: bool = True,
    ) -> int:
        """Scan a directory and auto-register matching classes.

        Args:
            directory: Path to scan for .py files.
            base_class: If set, only classes inheriting from this are registered.
            name_suffix: Only register classes whose name ends with this suffix.
            recursive: If True, scan subdirectories too.

        Returns:
            Number of newly registered classes.
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            logger.warning("Directory not found: %s", directory)
            return 0

        count = 0
        pattern = "**/*.py" if recursive else "*.py"
        for py_file in sorted(dir_path.glob(pattern)):
            if py_file.name == "__init__.py":
                continue

            mod_name = py_file.stem
            # Skip already-registered
            if mod_name in self._registry:
                continue

            try:
                spec = importlib.util.spec_from_file_location(mod_name, py_file)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except Exception as e:
                logger.debug("Skipping %s: %s", py_file.name, e)
                continue

            # Find matching classes in this module
            for obj_name, obj in inspect.getmembers(mod, inspect.isclass):
                if obj.__module__ != mod.__name__:
                    continue  # imported class, not defined here
                if name_suffix and not obj_name.endswith(name_suffix):
                    continue
                if base_class is not None and not issubclass(obj, base_class):
                    continue
                # Skip base/abstract classes
                if inspect.isabstract(obj):
                    continue
                if base_class is not None and obj_name == base_class.__name__:
                    continue

                # Register
                key = obj_name.lower()
                self._registry[key] = obj
                self._modules[key] = str(py_file)
                count += 1
                logger.debug("Registered: %s -> %s", obj_name, py_file)

        if count:
            logger.info("Discovered %d new components in %s", count, directory)
        return count

    def discover_package(
        self,
        package_name: str,
        base_class: Optional[type] = None,
        name_suffix: str = "",
    ) -> int:
        """Scan an installed Python package by name.

        Useful for registering components from installed packages.
        """
        count = 0
        try:
            pkg = importlib.import_module(package_name)
        except ImportError:
            logger.warning("Package not found: %s", package_name)
            return 0

        pkg_path = Path(getattr(pkg, "__path__", str(pkg.__file__ or ""))[0])
        return self.discover_from_dir(pkg_path, base_class, name_suffix)

    def discover_all(
        self,
        strategy_dirs: Optional[list[str | Path]] = None,
        base_class: Optional[type] = None,
        name_suffix: str = "",
    ) -> dict[str, int]:
        """Run discovery across multiple directories.

        Args:
            strategy_dirs: List of directories to scan. If None, uses defaults.
            base_class: Optional base class filter.
            name_suffix: Optional name suffix filter.

        Returns:
            Dict mapping directory -> number of discoveries.
        """
        if strategy_dirs is None:
            strategy_dirs = self._default_dirs()

        results: dict[str, int] = {}
        for d in strategy_dirs:
            n = self.discover_from_dir(d, base_class, name_suffix)
            results[str(d)] = n
        return results

    # ── Access ──────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[type]:
        """Get a registered component by name (case-insensitive)."""
        return self._registry.get(name.lower())

    def get_all(self) -> dict[str, type]:
        """Get all registered components."""
        return dict(self._registry)

    def get_by_module(self, name: str) -> Optional[str]:
        """Get the file path where a component was found."""
        return self._modules.get(name.lower())

    def list_registered(self) -> list[str]:
        """List all registered component names."""
        return sorted(self._registry.keys())

    def count(self) -> int:
        return len(self._registry)

    # ── Internal helpers ────────────────────────────────────────────

    def _default_dirs(self) -> list[Path]:
        """Return the default search paths for QNA components."""
        base = Path(__file__).resolve().parent.parent
        dirs = [
            base / "engine" / "strategies",
            base / "engine" / "strategy" / "strategies",
            base / "agents",
            base / "exchange",
            base / "providers",
            base / "indicators",
            base / "memory",
        ]
        return [d for d in dirs if d.is_dir()]

    def status(self) -> dict[str, Any]:
        """Report registry status."""
        return {
            "total_registered": self.count(),
            "components": sorted(k for k in self._registry),
            "modules": dict(self._modules),
        }
