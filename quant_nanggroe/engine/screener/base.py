"""Screener Component ABC — Base class for all screener engines.

Every screener component must implement the analyze() method
and return a ScreenerResult with scores and analysis details.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScreenerDirection(str, Enum):
    """Screener signal direction."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ScreenerResult(BaseModel):
    """Result from a screener component analysis.

    Attributes:
        component_name: Name of the screener component.
        direction: Bullish/bearish/neutral direction.
        score: Score from -1.0 (strong bearish) to 1.0 (strong bullish).
        confidence: Confidence in the analysis (0.0-1.0).
        details: Detailed analysis data.
        status: Status of the analysis (configured, not_configured, error).
        message: Human-readable message about the analysis.
    """

    component_name: str = Field(..., min_length=1)
    direction: ScreenerDirection = Field(default=ScreenerDirection.NEUTRAL)
    score: float = Field(default=0.0, ge=-1.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="configured")
    message: str = Field(default="")

    model_config = {"from_attributes": True}


class ScreenerComponent(ABC):
    """Abstract base class for all screener components.

    Every screener must implement:
    - analyze(): Run analysis on market data and return a ScreenerResult
    """

    def __init__(self) -> None:
        self._configured: bool = True

    @property
    @abstractmethod
    def name(self) -> str:
        """Component name identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Component description."""
        ...

    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        """Run analysis on market data.

        Args:
            data: Dict with market data (prices, fundamentals, etc.)

        Returns:
            ScreenerResult with analysis scores and details.
        """
        ...

    def configure(self, **kwargs: Any) -> None:
        """Configure the component with external data sources."""
        self._configured = True

    @property
    def is_configured(self) -> bool:
        """Whether the component is properly configured."""
        return self._configured

    def _not_configured_result(self) -> ScreenerResult:
        """Return a not-configured result."""
        return ScreenerResult(
            component_name=self.name,
            direction=ScreenerDirection.NEUTRAL,
            score=0.0,
            confidence=0.0,
            status="not_configured",
            message=f"{self.name}: Not configured. Connect data source to enable.",
        )
