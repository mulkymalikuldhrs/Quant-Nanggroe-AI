"""
Factor Registry — Central registry for all alpha factors
==========================================================
Consolidates 456+ factors from:
  - Alpha101 (WorldQuant 101 Formulaic Alphas)
  - GTJA191 (Guotai Junan 191 Alphas)
  - Qlib158 (Microsoft Qlib 158 Factors)
  - Academic (Fama-French, Carhart)
  - Technical (RSI, MACD, Bollinger)
"""

from __future__ import annotations

from typing import Any, Callable


class FactorRegistry:
    """Central registry for alpha factors.

    Supports auto-discovery of factors from the factor zoo
    and manual registration.  All look-ups are O(1).
    """

    _factors: dict[str, Callable[..., Any]] = {}
    _categories: dict[str, str] = {}  # factor_name -> category
    _loaded: bool = False

    # ------------------------------------------------------------------ #
    #  Core API                                                           #
    # ------------------------------------------------------------------ #

    @classmethod
    def register(
        cls,
        name: str,
        fn: Callable[..., Any],
        category: str = "uncategorized",
    ) -> None:
        """Register a factor function."""
        cls._factors[name] = fn
        cls._categories[name] = category

    @classmethod
    def get(cls, name: str) -> Callable[..., Any] | None:
        """Get a factor function by name."""
        return cls._factors.get(name)

    @classmethod
    def list_factors(cls) -> list[str]:
        """List all registered factor names (sorted)."""
        return sorted(cls._factors.keys())

    @classmethod
    def compute(cls, name: str, **kwargs: Any) -> Any:
        """Compute a factor by name."""
        fn = cls.get(name)
        if fn is None:
            raise ValueError(f"Factor '{name}' not registered")
        return fn(**kwargs)

    @classmethod
    def get_category(cls, name: str) -> str:
        """Get the category of a factor."""
        return cls._categories.get(name, "uncategorized")

    @classmethod
    def list_by_category(cls, category: str) -> list[str]:
        """List all factors in a given category."""
        return sorted(
            k for k, v in cls._categories.items() if v == category
        )

    @classmethod
    def categories(cls) -> list[str]:
        """List all unique categories."""
        return sorted(set(cls._categories.values()))

    @classmethod
    def count(cls) -> int:
        """Total number of registered factors."""
        return len(cls._factors)

    # ------------------------------------------------------------------ #
    #  Auto-discovery                                                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def auto_discover(cls) -> int:
        """Discover and register all factors from the factor zoo.

        Returns the number of newly registered factors.
        """
        if cls._loaded:
            return 0

        count_before = cls.count()

        # 1. Alpha101 (simplified version — 10 key factors from alpha101.py)
        try:
            from quant_nanggroe_ai.factors.alpha101 import ALPHA_FACTORS
            for name, fn in ALPHA_FACTORS.items():
                cls.register(name, fn, category="alpha101")
        except ImportError:
            pass

        # 2. Alpha101 full (from Vibe-Trading zoo — 101 factors)
        try:
            from quant_nanggroe_ai.factors.zoo.alpha101 import (
                ALPHA_REGISTRY as vt_alpha101,
            )
            for name, fn in vt_alpha101.items():
                if name not in cls._factors:
                    cls.register(name, fn, category="alpha101_full")
        except (ImportError, AttributeError):
            # Individual factor modules
            _discover_alpha101_modules(cls)

        # 3. GTJA191 (from Vibe-Trading zoo — 191 factors)
        try:
            from quant_nanggroe_ai.factors.zoo.gtja191 import (
                ALPHA_REGISTRY as vt_gtja191,
            )
            for name, fn in vt_gtja191.items():
                cls.register(name, fn, category="gtja191")
        except (ImportError, AttributeError):
            _discover_gtja191_modules(cls)

        # 4. Qlib158 (from Vibe-Trading zoo — 155 factors)
        try:
            from quant_nanggroe_ai.factors.zoo.qlib158 import (
                ALPHA_REGISTRY as vt_qlib158,
            )
            for name, fn in vt_qlib158.items():
                cls.register(name, fn, category="qlib158")
        except (ImportError, AttributeError):
            _discover_qlib158_modules(cls)

        # 5. Academic factors (Fama-French 5-factor + Carhart momentum)
        try:
            from quant_nanggroe_ai.factors.fama_french import FAMA_FRENCH_FACTORS
            for name, fn in FAMA_FRENCH_FACTORS.items():
                cls.register(name, fn, category="academic")
        except ImportError:
            pass

        try:
            from quant_nanggroe_ai.factors.zoo.academic import (
                SMB, HML, RMW, CMA, MKT_RF, CARHART_MOM,
            )
            for name, fn in [
                ("smb", SMB), ("hml", HML), ("rmw", RMW),
                ("cma", CMA), ("mkt_rf", MKT_RF), ("carhart_mom", CARHART_MOM),
            ]:
                if name not in cls._factors:
                    cls.register(name, fn, category="academic")
        except (ImportError, AttributeError):
            pass

        # 6. Technical factors
        try:
            from quant_nanggroe_ai.factors.technical import (
                compute_rsi_factor,
                compute_macd_factor,
                compute_bollinger_factor,
            )
            cls.register("rsi", compute_rsi_factor, category="technical")
            cls.register("macd", compute_macd_factor, category="technical")
            cls.register("bollinger", compute_bollinger_factor, category="technical")
        except ImportError:
            pass

        cls._loaded = True
        return cls.count() - count_before


# ---------------------------------------------------------------------- #
#  Module-level discovery helpers                                         #
# ---------------------------------------------------------------------- #

def _discover_alpha101_modules(registry: type[FactorRegistry]) -> None:
    """Discover Alpha101 factors from individual modules."""
    import importlib
    for i in range(1, 102):
        mod_name = f"quant_nanggroe_ai.factors.zoo.alpha101.alpha_{i:03d}"
        try:
            mod = importlib.import_module(mod_name)
            # Convention: each module exposes a compute function or alpha_NNN function
            fn = getattr(mod, "compute", None) or getattr(mod, f"alpha_{i:03d}", None)
            if fn and callable(fn):
                registry.register(f"alpha101_{i:03d}", fn, category="alpha101_full")
        except ImportError:
            pass


def _discover_gtja191_modules(registry: type[FactorRegistry]) -> None:
    """Discover GTJA191 factors from individual modules."""
    import importlib
    for i in range(1, 192):
        mod_name = f"quant_nanggroe_ai.factors.zoo.gtja191.alpha_{i:03d}"
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, "compute", None) or getattr(mod, f"alpha_{i:03d}", None)
            if fn and callable(fn):
                registry.register(f"gtja191_{i:03d}", fn, category="gtja191")
        except ImportError:
            pass


def _discover_qlib158_modules(registry: type[FactorRegistry]) -> None:
    """Discover Qlib158 factors from individual modules."""
    import importlib
    import quant_nanggroe_ai.factors.zoo.qlib158 as qlib_pkg
    import pkgutil

    for importer, modname, ispkg in pkgutil.iter_modules(qlib_pkg.__path__):
        if modname.startswith("_"):
            continue
        try:
            mod = importlib.import_module(
                f"quant_nanggroe_ai.factors.zoo.qlib158.{modname}"
            )
            fn = getattr(mod, "compute", None) or getattr(mod, modname, None)
            if fn and callable(fn):
                registry.register(f"qlib158_{modname}", fn, category="qlib158")
        except (ImportError, AttributeError):
            pass


# ---------------------------------------------------------------------- #
#  Convenience auto-discover on import                                    #
# ---------------------------------------------------------------------- #

# Auto-discover factors when the registry is first used
FactorRegistry.auto_discover()
