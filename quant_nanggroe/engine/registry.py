"""AutoRegistry — Self-discovering component registry for QNA v6.0.0.

Scans ALL directories: active strategies, archive/, legacy/,
and any new directory with Strategy subclasses. Zero manual registration.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from quant_nanggroe.engine.strategies.base import Strategy

logger = logging.getLogger("quant_nanggroe.registry")

# Directories to scan (in priority order)
SCAN_DIRS: List[str] = [
    "quant_nanggroe.engine.strategies",  # Active strategies
    "quant_nanggroe.engine.regime",       # Regime detection
    "quant_nanggroe.engine.backtest",     # Backtest engines
    "quant_nanggroe.engine.risk",         # Risk management
    "quant_nanggroe.engine.execution",    # Execution builders
    "quant_nanggroe.engine.memory",       # Memory layer
    "quant_nanggroe.engine.pipeline",     # Pipeline (self-aware, self-evolve)
    "quant_nanggroe.engine.agentic",      # Agentic pipeline
    "quant_nanggroe.engine.self_aware",   # Self-awareness
    "quant_nanggroe.engine.strategies",   # All strategy subdirs (incl archive)
]

_ARCHIVE_DIRS: List[str] = [
    "quant_nanggroe.engine.strategies.archive",
    "quant_nanggroe.engine.strategies.strategies.archive",
]

# Filesystem-based archive root (repository-level archive/ directory)
_ARCHIVE_ROOT: str = str(Path(__file__).resolve().parent.parent.parent / "archive")
_ARCHIVE_PACKAGES: List[str] = []  # populated at scan time from _ARCHIVE_ROOT


class AutoRegistry:
    """Self-discovering strategy and component registry.

    Automatically finds and registers all Strategy subclasses across
    active + archive directories. No manual __all__ or explicit imports needed.
    """

    _instance: Optional["AutoRegistry"] = None
    _registry: Dict[str, Type[Strategy]] = {}
    _scanned: Set[str] = set()
    _archive_scanned: bool = False

    def __new__(cls) -> "AutoRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Public API ──────────────────────────────────────────────────────

    def register(self, name: str, cls: Type[Strategy]) -> None:
        """Register a strategy class by name."""
        self._registry[name] = cls
        logger.info("AutoRegistry: registered %s from %s", name, cls.__module__)

    def unregister(self, name: str) -> None:
        """Remove a strategy from registry."""
        self._registry.pop(name, None)

    def get(self, name: str) -> Optional[Type[Strategy]]:
        """Get a registered strategy class by name."""
        return self._registry.get(name)

    def list_strategies(self) -> Dict[str, Type[Strategy]]:
        """Return all registered strategies."""
        return dict(self._registry)

    def list_strategies_by_category(self, category: str) -> Dict[str, Type[Strategy]]:
        """Filter strategies by category (archive, active, regime, backtest, etc.)."""
        result = {}
        for name, cls in self._registry.items():
            mod = cls.__module__
            if category in mod or category in name.lower():
                result[name] = cls
        return result

    def create(self, name: str, **kwargs) -> Optional[Strategy]:
        """Create a strategy instance by name."""
        cls = self._registry.get(name)
        if cls is None:
            logger.warning("AutoRegistry: strategy '%s' not found", name)
            return None
        try:
            return cls(**kwargs)
        except Exception as e:
            logger.error("AutoRegistry: failed to create %s: %s", name, e)
            return None

    # ── Auto-Discovery ─────────────────────────────────────────────────

    def scan_all(self, force: bool = False) -> int:
        """Scan ALL registered directories and register discovered strategies.

        Returns total number of registered strategies after scan.
        """
        total = 0
        for pkg_path in SCAN_DIRS:
            try:
                count = self._scan_package(pkg_path, force=force)
                total += count
            except Exception as e:
                logger.warning("AutoRegistry: failed to scan %s: %s", pkg_path, e)
        # Always include archive dirs (Python packages)
        if not self._archive_scanned or force:
            for pkg_path in _ARCHIVE_DIRS:
                count = self._scan_archive_package(pkg_path, force=force)
                total += count
            self._archive_scanned = True

        # Also scan filesystem-based archive root for non-package archives
        count = self._scan_archive_filesystem(force=force)
        total += count
        # Merge decorator registry (archive wrappers captured by register loop)
        total += self._merge_decorator_registry()
        return total

    def scan_active(self, force: bool = False) -> int:
        """Scan only active strategy directories (not archive)."""
        count = 0
        for pkg_path in SCAN_DIRS:
            c = self._scan_package(pkg_path, force=force)
            count += c
        return count

    def scan_archive(self, force: bool = False) -> int:
        """Scan archive directories for legacy strategies."""
        if self._archive_scanned and not force:
            return 0
        count = 0
        for pkg_path in _ARCHIVE_DIRS:
            c = self._scan_archive_package(pkg_path, force=force)
            count += c
        self._archive_scanned = True
        return count

    # ── Internal Scanning ──────────────────────────────────────────────

    def _scan_package(self, pkg_path: str, force: bool = False) -> int:
        """Scan a Python package for Strategy subclasses."""
        try:
            module = importlib.import_module(pkg_path)
        except ImportError:
            return 0

        if pkg_path in self._scanned and not force:
            return 0
        self._scanned.add(pkg_path)

        count = 0
        # Scan submodules (skip if module has no __path__ - namespace package issue)
        pkg_path_obj = getattr(module, '__path__', None)
        if pkg_path_obj is None:
            logger.debug("AutoRegistry: skipped %s (no __path__)", pkg_path)
            return 0
        for finder, name, is_pkg in pkgutil.walk_packages(
            pkg_path_obj, prefix=pkg_path + "."
        ):
            if name in self._scanned and not force:
                continue
            self._scanned.add(name)
            try:
                mod = importlib.import_module(name)
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if self._is_strategy_class(obj):
                        strat_name = getattr(obj, 'name', None) or obj.__name__
                        if strat_name not in self._registry:
                            self.register(strat_name, obj)
                            count += 1
                        elif self._registry[strat_name] is not obj:
                            # Override with newer/active version
                            logger.info(
                                "AutoRegistry: overriding %s with %s",
                                strat_name,
                                obj.__module__,
                            )
                            self.register(strat_name, obj)
            except Exception as e:
                logger.debug("AutoRegistry: skipped module %s: %s", name, e)

        # Also scan current module's direct classes
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if self._is_strategy_class(obj):
                strat_name = obj.__name__
                if strat_name not in self._registry:
                    self.register(strat_name, obj)
                    count += 1

        if count > 0:
            logger.info("AutoRegistry: registered %d strategies from %s", count, pkg_path)
        return count

    def _scan_archive_filesystem(self, force: bool = False) -> int:
        """Scan repository-level archive/ directory via filesystem walk."""
        archive_root = Path(_ARCHIVE_ROOT)
        if not archive_root.exists():
            logger.debug("AutoRegistry: archive root does not exist: %s", archive_root)
            return 0

        count = 0
        for py_file in sorted(archive_root.rglob("*.py")):
            rel = py_file.relative_to(archive_root)
            # Convert path to dotted module name
            parts = list(rel.with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            if not parts:
                continue
            module_name = "archive." + ".".join(parts)
            if module_name in self._scanned and not force:
                continue
            self._scanned.add(module_name)

            # We cannot import via Python path since archive/ is not a package
            # under quant_nanggroe. Load source directly instead.
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                loaded = self._load_strategy_from_source(source, module_name, py_file)
                count += loaded
            except Exception as e:
                logger.debug("AutoRegistry: skipped archive file %s: %s", py_file, e)

        logger.info("AutoRegistry: %d archive strategies from filesystem scan", count)
        return count

    @staticmethod
    def _load_strategy_from_source(source: str, module_name: str, filepath: Path) -> int:
        """Extract REAL Strategy subclasses from archive source via import.

        AST is used only to shortlist candidate class names; the module is then
        actually imported and only genuine ``Strategy`` subclasses are registered.
        Modules that fail to import (broken deps, junk) are skipped -- never
        registered as ``None`` placeholders.
        """
        import ast

        try:
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            return 0

        candidate_names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            cls_name = node.name
            if cls_name in ("Strategy", "BaseStrategy", "TradingStrategy", "StrategyBase"):
                continue
            has_strategy_base = False
            for base in node.bases:
                base_name = base.id if isinstance(base, ast.Name) else (
                    base.attr if isinstance(base, ast.Attribute) else None
                )
                if base_name and (
                    base_name
                    in ("Strategy", "BaseStrategy", "TradingStrategy", "StrategyBase")
                    or base_name.endswith("Strategy")
                ):
                    has_strategy_base = True
                    break
            if not has_strategy_base:
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and sub.name == "generate_signals":
                        has_strategy_base = True
                        break
            if has_strategy_base:
                candidate_names.add(cls_name)

        if not candidate_names:
            return 0

        # Real import -- register actual classes, not None placeholders.
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            return 0

        count = 0
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__name__ not in candidate_names:
                continue
            if not (issubclass(obj, Strategy) and obj is not Strategy):
                continue
            if not obj.__module__.startswith("archive."):
                continue
            archive_name = f"archive_{obj.__name__}"
            if archive_name not in _registry._registry:
                _registry.register(archive_name, obj)
                count += 1
        return count

    def _scan_archive_package(self, pkg_path: str, force: bool = False) -> int:
        """Scan archive directories — include ALL strategies even if duplicates."""
        try:
            module = importlib.import_module(pkg_path)
        except ImportError:
            return 0

        if pkg_path in self._scanned and not force:
            return 0
        self._scanned.add(pkg_path)

        count = 0
        for finder, name, is_pkg in pkgutil.walk_packages(
            module.__path__, prefix=pkg_path + "."
        ):
            try:
                mod = importlib.import_module(name)
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if self._is_strategy_class(obj):
                        strat_name = obj.__name__
                        # Archive strategies use archive prefix to avoid clashes
                        archive_name = f"archive_{strat_name}"
                        if archive_name not in self._registry:
                            self.register(archive_name, obj)
                            count += 1
            except Exception:
                pass

        logger.info("AutoRegistry: %d archive strategies from %s", count, pkg_path)
        return count

    @staticmethod
    def _is_strategy_class(obj: type) -> bool:
        """Check if a class is a Strategy subclass (not the base itself)."""
        if obj is Strategy:
            return False
        if obj.__module__.startswith("_"):
            return False
        return issubclass(obj, Strategy)



    def _merge_decorator_registry(self) -> int:
        """Pull strategies from decorator StrategyRegistry (archive wrappers)."""
        try:
            import importlib
            _deco_mod = importlib.import_module('quant_nanggroe.engine.strategies.registry')
        except Exception:
            return 0
        count = 0
        for name, cls in _deco_mod._registry.items():
            if name not in self._registry:
                self.register(name, cls)
                count += 1
        import logging
        logging.getLogger("quant_nanggroe.registry").info(
            "AutoRegistry: merged %d from decorator", count)
        return count


    def ensure_init_files(self, base: Path) -> int:
        """Ensure all subdirectories have __init__.py files. Returns count created."""
        import os
        from pathlib import Path
        count = 0
        for root, dirs, files in os.walk(base):
            # Skip hidden dirs, __pycache__, and .venv
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            init_file = os.path.join(root, '__init__.py')
            if not os.path.exists(init_file):
                # Only create for directories with Python files
                has_py = any(f.endswith('.py') for f in files)
                if has_py:
                    with open(init_file, 'w') as f:
                        f.write('# Auto-generated by AutoRegistry\n')
                    count += 1
        return count

    def health_check(self) -> dict:
        """Return health metrics for the registry."""
        import os
        from pathlib import Path
        base = Path(__file__).resolve().parent.parent
        stale_count = 0
        missing_init_count = 0
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            init_file = os.path.join(root, '__init__.py')
            has_py = any(f.endswith('.py') for f in files)
            if has_py and not os.path.exists(init_file):
                missing_init_count += 1
        return {"stale_count": stale_count, "missing_init_count": missing_init_count}

# ── Singleton + Auto-Init ────────────────────────────────────────────

_registry = AutoRegistry()

# Auto-scan on import
_strategies_found = _registry.scan_all()
logger.info(
    "AutoRegistry initialized: %d strategies registered from active + archive dirs",
    _strategies_found,
)


# ── Public API ───────────────────────────────────────────────────────

def list_strategies() -> Dict[str, Type[Strategy]]:
    """Return all registered strategies (active + archive)."""
    return _registry.list_strategies()


def get_strategy(name: str) -> Optional[Type[Strategy]]:
    """Get a strategy class by name."""
    return _registry.get(name)


def create_strategy(name: str, **kwargs) -> Optional[Strategy]:
    """Create a strategy instance by name."""
    return _registry.create(name, **kwargs)


def list_categories() -> Dict[str, int]:
    """Return strategy counts by category."""
    cats: Dict[str, int] = {}
    for name in _registry.list_strategies():
        if name.startswith("archive_"):
            cat = "archive"
        else:
            cat = "active"
        cats[cat] = cats.get(cat, 0) + 1
    return cats


def reload() -> int:
    """Force re-scan all directories (clear cache)."""
    _registry._scanned.clear()
    _registry._archive_scanned = False
    return _registry.scan_all(force=True)
