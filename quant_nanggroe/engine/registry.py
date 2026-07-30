"""AutoRegistry — Self-discovering component registry for QNA v6.0.0.

Scans registered directories for Strategy subclasses. No manual __all__ needed.
NOTE: Strategy registration is now canonical via StrategyRegistry decorator.
AutoRegistry still handles non-strategy component discovery (regime, backtest,
risk, execution, memory, pipeline, agentic, self_aware).
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Dict, List, Optional, Set, Type

from quant_nanggroe.engine.strategies.base import Strategy

logger = logging.getLogger("quant_nanggroe.registry")

# Directories to scan (strategy dirs removed — use StrategyRegistry @register decorator)
SCAN_DIRS: List[str] = [
    "quant_nanggroe.engine.regime",       # Regime detection
    "quant_nanggroe.engine.backtest",     # Backtest engines
    "quant_nanggroe.engine.risk",         # Risk management
    "quant_nanggroe.engine.execution",    # Execution builders
    "quant_nanggroe.engine.memory",       # Memory layer
    "quant_nanggroe.engine.pipeline",     # Pipeline (self-aware, self-evolve)
    "quant_nanggroe.engine.agentic",      # Agentic pipeline
    "quant_nanggroe.engine.self_aware",   # Self-awareness
]


class AutoRegistry:
    """Self-discovering component registry.

    Scans registered directories for Strategy subclasses used outside the
    main strategies package. The StrategyRegistry (decorator-driven) is the
    canonical source for trading strategies.
    """

    _instance: Optional["AutoRegistry"] = None
    _registry: Dict[str, Type[Strategy]] = {}
    _scanned: Set[str] = set()

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
        """Filter strategies by category (regime, backtest, risk, etc.)."""
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
        return total

    def scan_active(self, force: bool = False) -> int:
        """Scan only directories in SCAN_DIRS."""
        count = 0
        for pkg_path in SCAN_DIRS:
            c = self._scan_package(pkg_path, force=force)
            count += c
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
                        strat_name = obj.__name__
                        if strat_name not in self._registry:
                            self.register(strat_name, obj)
                            count += 1
                        elif self._registry[strat_name] is not obj:
                            logger.info(
                                "AutoRegistry: overriding %s with %s",
                                strat_name,
                                obj.__module__,
                            )
                            self.register(strat_name, obj)
            except Exception as e:
                logger.debug("AutoRegistry: skipped module %s: %s", name, e)

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if self._is_strategy_class(obj):
                strat_name = obj.__name__
                if strat_name not in self._registry:
                    self.register(strat_name, obj)
                    count += 1

        if count > 0:
            logger.info("AutoRegistry: registered %d strategies from %s", count, pkg_path)
        return count

    @staticmethod
    def _is_strategy_class(obj: type) -> bool:
        """Check if a class is a Strategy subclass (not the base itself)."""
        if obj is Strategy:
            return False
        if obj.__module__.startswith("_"):
            return False
        return issubclass(obj, Strategy)


# ── Singleton + Auto-Init ────────────────────────────────────────────

_registry = AutoRegistry()

_strategies_found = _registry.scan_all()
logger.info(
    "AutoRegistry initialized: %d components registered",
    _strategies_found,
)


# ── Public API (backward-compat shims) ───────────────────────────────


def list_strategies() -> Dict[str, Type[Strategy]]:
    """Return all registered components."""
    return _registry.list_strategies()


def get_strategy(name: str) -> Optional[Type[Strategy]]:
    """Get a component class by name."""
    return _registry.get(name)


def create_strategy(name: str, **kwargs) -> Optional[Strategy]:
    """Create a component instance by name."""
    return _registry.create(name, **kwargs)


def list_categories() -> Dict[str, int]:
    """Return component counts by category."""
    cats: Dict[str, int] = {}
    for name in _registry.list_strategies():
        cat = "active"
        cats[cat] = cats.get(cat, 0) + 1
    return cats


def reload() -> int:
    """Force re-scan all directories (clear cache)."""
    _registry._scanned.clear()
    return _registry.scan_all(force=True)
