from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class HurstExponentStrategy(BaseStrategy):
    """Hurst exponent estimates trend/mean-reversion regime."""

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="HurstExponent", params=params)
        self.lookback: int = int(self.params.get("lookback", 100))
        self.trend_threshold: float = float(self.params.get("trend_threshold", 0.55))
        self.mr_threshold: float = float(self.params.get("mr_threshold", 0.45))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.lookback + 5

    @staticmethod
    def _hurst(series: np.ndarray) -> float:
        """Compute Hurst exponent via R/S analysis."""
        n = len(series)
        if n < 20:
            return 0.5
        max_lag = min(n // 4, 100)
        lags = np.arange(2, max_lag).astype(float)
        rs = []
        for lag in lags:
            lag_int = int(lag)
            chunks = n // lag_int
            rs_vals = []
            for i in range(chunks):
                chunk = series[i * lag_int:(i + 1) * lag_int]
                if len(chunk) < 2:
                    continue
                adj = chunk - chunk.mean()
                cum = np.cumsum(adj)
                r = cum.max() - cum.min()
                s = np.std(chunk) + 1e-10
                rs_vals.append(r / s)
            if rs_vals:
                rs.append(np.mean(rs_vals))
        if len(rs) < 3:
            return 0.5
        return float(np.polyfit(np.log(lags[:len(rs)]), np.log(rs), 1)[0])

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        close = data["close"]
        rets = close.pct_change().dropna().values[-self.lookback:]
        if len(rets) < 20:
            return None
        h = self._hurst(rets)
        price = float(close.iloc[-1])
        if h > self.trend_threshold:
            ret_mom = float(close.iloc[-5:].mean()) / float(close.iloc[-self.lookback:-self.lookback+5].mean()) - 1.0
            sig = 1.0 if ret_mom > 0 else -1.0
            return Signal(symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=min(abs(h - 0.5) * 2, 1.0), price=round(price, 6),
                source_agent=self.name, source_strategy=self.name,
                reasoning=f"Hurst {h:.3f} > {self.trend_threshold}: trending regime",
                evidence={"hurst": round(h, 3)}, factors=["hedge_fund", "hurst"])
        if h < self.mr_threshold:
            zs = self.compute_zscore(close, min(self.lookback, len(close) - 1))
            z = float(zs.iloc[-1]) if not np.isnan(zs.iloc[-1]) else 0.0
            sig = 1.0 if z < 0 else -1.0
            return Signal(symbol=self.name, signal_type=SignalType.BUY if sig > 0 else SignalType.SELL,
                confidence=min(abs(h - 0.5) * 2, 1.0), price=round(price, 6),
                source_agent=self.name, source_strategy=self.name,
                reasoning=f"Hurst {h:.3f} < {self.mr_threshold}: mean-reverting regime",
                evidence={"hurst": round(h, 3), "zscore": round(float(z), 3)},
                factors=["hedge_fund", "hurst"])
        return None
