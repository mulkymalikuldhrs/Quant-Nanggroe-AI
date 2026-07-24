"""AutoRegistry — Fully autonomous component registry for QNA.

No manual __all__, no explicit imports, no file left behind.
Auto-discovers ALL .py files across the entire quant_nanggroe package.
Auto-generates __init__.py for directories missing them.
Auto-cleans stale registrations when files are deleted.
Auto-re-scans on every discover_all() call.

Usage:
    from quant_nanggroe.engine.registry import AutoRegistry

    registry = AutoRegistry()
    registry.discover_all()  # scans everything, no exceptions

    strat = registry.get("WyckoffStrategy")
    registry.list_registered()
    registry.health_check()  # returns full audit
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Directories to scan (recursive). Empty = scan ALL quant_nanggroe subdirs.
_SCAN_ROOTS = [
    "engine",
    "agents",
    "api",
    "exchange",
    "strategies",
    "providers",
    "indicators",
    "memory",
    "data",
    "hedge_fund",
    "mcp",
    "schemas",
    "security",
    "skills",
    "types",
    "utils",
    "backtest",
    "bridge",
    "config",
    "connectors",
    "core",
    "database",
    "llm",
]

# Files to skip (support modules, not components)
_SKIP_FILES = {
    "__init__.py",
    "_df_signal_adapter.py",
    "conftest.py",
    "setup.py",
}


class AutoRegistry:
    """Fully autonomous registry — discovers, registers, maintains itself.

    Scans ALL .py files under quant_nanggroe/ recursively.
    - Auto-discovers every class (no base_class filter needed)
    - Auto-generates __init__.py for missing dirs
    - Auto-cleans stale entries on re-scan
    - Tracks file hashes for change detection
    """

    def __init__(self):
        self._registry: dict[str, type] = {}
        self._modules: dict[str, str] = {}
        self._file_hashes: dict[str, str] = {}
        self._scan_count: int = 0

    # ── Core Discovery ─────────────────────────────────────────────

    def discover_from_dir(
        self,
        directory: str | Path,
        base_class: Optional[type] = None,
        name_suffix: str = "",
        recursive: bool = True,
    ) -> int:
        """Scan a directory and auto-register ALL matching classes."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            logger.warning("Directory not found: %s", directory)
            return 0

        count = 0
        pattern = "**/*.py" if recursive else "*.py"
        for py_file in sorted(dir_path.glob(pattern)):
            if py_file.name in _SKIP_FILES or py_file.name.startswith("__"):
                continue
            if "__pycache__" in str(py_file):
                continue

            mod_name = py_file.stem

            # Check if file changed since last scan
            file_hash = self._file_hash(py_file)
            if mod_name in self._registry and self._file_hashes.get(mod_name) == file_hash:
                continue  # unchanged, skip

            # Remove stale entry if file changed
            if mod_name in self._registry:
                del self._registry[mod_name]
                del self._modules[mod_name]

            try:
                spec = importlib.util.spec_from_file_location(mod_name, py_file)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except Exception as e:
                logger.debug("Skipping %s: %s", py_file.name, e)
                continue

            # Register ALL classes found (no base_class filter by default)
            for obj_name, obj in inspect.getmembers(mod, inspect.isclass):
                if obj.__module__ != mod.__name__:
                    continue  # imported, not defined here
                if name_suffix and not obj_name.endswith(name_suffix):
                    continue
                if base_class is not None and not issubclass(obj, base_class):
                    continue
                if inspect.isabstract(obj):
                    continue
                if base_class is not None and obj_name == base_class.__name__:
                    continue

                key = obj_name.lower()
                self._registry[key] = obj
                self._modules[key] = str(py_file)
                self._file_hashes[key] = file_hash
                count += 1
                logger.debug("Registered: %s -> %s", obj_name, py_file)

        if count:
            logger.info("Discovered %d components in %s", count, directory)
        return count

    def discover_all(
        self,
        strategy_dirs: Optional[list[str | Path]] = None,
        base_class: Optional[type] = None,
        name_suffix: str = "",
    ) -> dict[str, int]:
        """Scan ALL directories. Auto-cleans stale entries.

        Returns dict mapping directory -> number of discoveries.
        """
        if strategy_dirs is None:
            strategy_dirs = self._default_dirs()

        # Snapshot current registrations for stale detection
        before = set(self._registry.keys())

        results: dict[str, int] = {}
        for d in strategy_dirs:
            n = self.discover_from_dir(d, base_class, name_suffix)
            results[str(d)] = n

        # Auto-clean: remove entries whose files no longer exist
        after = set(self._registry.keys())
        stale = before - after
        for key in list(self._registry.keys()):
            mod_path = self._modules.get(key, "")
            if mod_path and not Path(mod_path).exists():
                del self._registry[key]
                del self._modules[key]
                self._file_hashes.pop(key, None)
                stale.add(key)

        if stale:
            logger.info("Auto-cleaned %d stale registrations: %s", len(stale), stale)

        self._scan_count += 1
        return results

    def discover_package(
        self,
        package_name: str,
        base_class: Optional[type] = None,
        name_suffix: str = "",
    ) -> int:
        """Scan an installed Python package by name."""
        try:
            pkg = importlib.import_module(package_name)
        except ImportError:
            logger.warning("Package not found: %s", package_name)
            return 0
        pkg_path = Path(getattr(pkg, "__path__", str(pkg.__file__ or ""))[0])
        return self.discover_from_dir(pkg_path, base_class, name_suffix)

    # ── Auto-Init ──────────────────────────────────────────────────

    def ensure_init_files(self, root: str | Path) -> int:
        """Auto-generate __init__.py for ALL directories missing one.

        Scans recursively under root. Returns count of files created.
        """
        root_path = Path(root)
        if not root_path.is_dir():
            return 0

        created = 0
        for d in sorted(root_path.rglob("*")):
            if not d.is_dir():
                continue
            if "__pycache__" in str(d) or "node_modules" in str(d):
                continue
            if ".git" in str(d):
                continue

            init_file = d / "__init__.py"
            if not init_file.exists():
                # Check if directory has any .py files
                has_python = any(d.glob("*.py"))
                if has_python:
                    pkg_name = d.name
                    init_file.write_text(f"# {pkg_name} module\n")
                    created += 1
                    logger.info("Created __init__.py: %s", init_file)

        return created

    # ── Health Check ───────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        """Full audit of registry health.

        Returns dict with:
        - total: total registered components
        - dirs_scanned: number of directories scanned
        - stale: list of registrations pointing to deleted files
        - missing_init: list of dirs without __init__.py
        - by_directory: component count per directory
        - scan_count: number of times discover_all was called
        """
        # Check for stale entries
        stale = []
        for key, mod_path in self._modules.items():
            if not Path(mod_path).exists():
                stale.append(key)

        # Check for missing __init__.py
        missing_init = []
        base = Path(__file__).resolve().parent.parent
        for d in base.rglob("*"):
            if not d.is_dir():
                continue
            if "__pycache__" in str(d) or "node_modules" in str(d):
                continue
            if ".git" in str(d):
                continue
            has_python = any(d.glob("*.py"))
            has_init = (d / "__init__.py").exists()
            if has_python and not has_init:
                missing_init.append(str(d.relative_to(base)))

        # Count by directory
        by_dir: dict[str, int] = {}
        for mod_path in self._modules.values():
            try:
                rel = str(Path(mod_path).relative_to(base).parent)
                by_dir[rel] = by_dir.get(rel, 0) + 1
            except ValueError:
                by_dir["unknown"] = by_dir.get("unknown", 0) + 1

        return {
            "total": self.count(),
            "dirs_scanned": len(self._default_dirs()),
            "stale": stale,
            "stale_count": len(stale),
            "missing_init": missing_init,
            "missing_init_count": len(missing_init),
            "by_directory": by_dir,
            "scan_count": self._scan_count,
        }

    # ── Access ─────────────────────────────────────────────────────

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
        """Return ALL quant_nanggroe subdirectories for scanning."""
        base = Path(__file__).resolve().parent.parent
        dirs = []
        for root_name in _SCAN_ROOTS:
            d = base / root_name
            if d.is_dir():
                dirs.append(d)
        # Also scan the strategies sub-package
        strategies = base / "strategies"
        if strategies.is_dir():
            dirs.append(strategies)
        return dirs

    def _file_hash(self, path: Path) -> str:
        """Quick content hash for change detection."""
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()[:12]
        except Exception:
            return "error"

    def status(self) -> dict[str, Any]:
        """Report registry status."""
        return {
            "total_registered": self.count(),
            "scan_count": self._scan_count,
            "components": sorted(k for k in self._registry),
        }
