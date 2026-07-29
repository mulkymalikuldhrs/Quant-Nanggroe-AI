from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Optional


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class ScorerResult:
    score: float
    confidence: float
    metadata: Optional[dict] = None


class BaseScorer(abc.ABC):
    weight: float = 0.0

    @abc.abstractmethod
    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        ...
