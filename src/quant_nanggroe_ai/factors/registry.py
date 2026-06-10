"""
Factor Registry — Central registry for all alpha factors
========================================================
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class FactorRegistry:
    """Central registry for alpha factors."""

    _factors: dict[str, Callable[..., Any]] = {}

    @classmethod
    def register(cls, name: str, fn: Callable[..., Any]) -> None:
        """Register a factor function."""
        cls._factors[name] = fn

    @classmethod
    def get(cls, name: str) -> Callable[..., Any] | None:
        """Get a factor function by name."""
        return cls._factors.get(name)

    @classmethod
    def list_factors(cls) -> list[str]:
        """List all registered factor names."""
        return sorted(cls._factors.keys())

    @classmethod
    def compute(cls, name: str, **kwargs: Any) -> Any:
        """Compute a factor by name."""
        fn = cls.get(name)
        if fn is None:
            raise ValueError(f"Factor '{name}' not registered")
        return fn(**kwargs)
