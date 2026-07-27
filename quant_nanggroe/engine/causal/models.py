from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CausalContext:
    """Structured macro bias context for signal aggregation.

    Replaces the fragile env-var protocol (QNA_CAUSAL_BIAS_*).
    """
    biases: Dict[str, float] = field(default_factory=dict)
    macro_regime: str = "neutral"
    volatility_regime: str = "normal"

    def bias_for(self, symbol: str) -> float:
        return self.biases.get(symbol.upper(), 0.0)
