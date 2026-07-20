from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class ParticleFilterStrategy(BaseStrategy):
    """Particle filter — state estimation with resampling."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ParticleFilter", params=params)
        self.n_particles: int = int(self.params.get("n_particles", 100))
        self.noise: float = float(self.params.get("noise", 0.01))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return 30

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or len(data) < 30:
            return None
        c = data["close"].values
        n = len(c)
        particles = np.ones(self.n_particles) * c[0]
        weights = np.ones(self.n_particles) / self.n_particles
        state_est = np.zeros(n)
        for i in range(1, n):
            particles = particles + np.random.normal(0, self.noise * c[i-1], self.n_particles)
            likelihood = np.exp(-0.5 * ((c[i] - particles) / (c[i] * 0.01 + 1e-10)) ** 2)
            weights = weights * likelihood
            weights = weights / (np.sum(weights) + 1e-10)
            state_est[i] = np.sum(particles * weights)
            n_eff = 1.0 / (np.sum(weights ** 2) + 1e-10)
            if n_eff < self.n_particles / 2:
                idx = np.random.choice(self.n_particles, self.n_particles, p=weights)
                particles = particles[idx]
                weights = np.ones(self.n_particles) / self.n_particles
        price = float(c[-1])
        if price > state_est[-1]:
            return Signal(symbol=self.name, signal_type=SignalType.BUY, confidence=0.5,
                price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
                reasoning="Particle filter: price above estimate",
                evidence={"pf_state": round(float(state_est[-1]), 4)}, factors=["ml", "particle_filter"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL, confidence=0.5,
            price=round(price, 6), source_agent=self.name,
                source_strategy=self.name,
            reasoning="Particle filter: price below estimate",
            evidence={"pf_state": round(float(state_est[-1]), 4)}, factors=["ml", "particle_filter"])
