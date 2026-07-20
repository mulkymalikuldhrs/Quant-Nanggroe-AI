from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class MonteCarloBarrierStrategy(BaseStrategy):
    """Monte Carlo barrier — probability of hitting target vs stop."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MonteCarloBarrier", params=params)
        self.lookback: int = int(self.params.get("lookback", 100))
        self.n_sims: int = int(self.params.get("n_sims", 1000))
        self.fwd_bars: int = int(self.params.get("fwd_bars", 20))
        self.target_pct: float = float(self.params.get("target_pct", 0.03))
        self.stop_pct: float = float(self.params.get("stop_pct", 0.02))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        c = data["close"].values
        rets = np.diff(np.log(c[-self.lookback:]))
        if len(rets) < 20:
            return None
        mu = np.mean(rets)
        sigma = np.std(rets)
        price = float(c[-1])
        paths = np.random.normal(mu, sigma, size=(self.n_sims, self.fwd_bars))
        paths = np.cumsum(paths, axis=1)
        paths = price * np.exp(paths)
        target = price * (1 + self.target_pct)
        stop = price * (1 - self.stop_pct)
        hit_target = np.any(paths >= target, axis=1)
        hit_stop = np.any(paths <= stop, axis=1)
        prob_up = np.mean(hit_target & ~hit_stop)
        prob_down = np.mean(hit_stop & ~hit_target)
        if prob_up > 0.6:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=round(prob_up, 4), price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"MC barrier: P(target)={prob_up:.0%} > P(stop)={prob_down:.0%}",
                evidence={"prob_up": round(float(prob_up), 3), "prob_down": round(float(prob_down), 3)},
                factors=["technical", "monte_carlo"])
        if prob_down > 0.6:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=round(prob_down, 4), price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"MC barrier: P(stop)={prob_down:.0%} > P(target)={prob_up:.0%}",
                evidence={"prob_up": round(float(prob_up), 3), "prob_down": round(float(prob_down), 3)},
                factors=["technical", "monte_carlo"])
        return None
