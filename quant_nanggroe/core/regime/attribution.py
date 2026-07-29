from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttributionResult:
    source: str
    contribution: float
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)


class SignalAttribution:
    def __init__(self, source_labels: list[str] | None = None):
        self.source_labels = source_labels or [
            "technical",
            "macro",
            "sentiment",
            "funding",
            "orderflow",
            "cot",
        ]

    def attribute(self, signal: dict[str, Any]) -> list[AttributionResult]:
        if not signal or not isinstance(signal, dict):
            return []

        results: list[AttributionResult] = []
        for source in self.source_labels:
            source_data = signal.get(source)
            if source_data is None:
                continue

            if isinstance(source_data, dict):
                contribution = float(source_data.get("contribution", source_data.get("weight", 0.0)))
                confidence = float(source_data.get("confidence", 0.5))
            elif isinstance(source_data, (int, float)):
                contribution = float(source_data)
                confidence = min(abs(contribution) / 100.0, 1.0)
            else:
                continue

            results.append(
                AttributionResult(
                    source=source,
                    contribution=contribution,
                    confidence=confidence,
                    details={"raw": source_data},
                )
            )

        return results
