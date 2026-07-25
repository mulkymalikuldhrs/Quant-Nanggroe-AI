"""Fundamental macro strategy — rates, CPI, PPI, employment, GDP."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class FundamentalStrategy(Strategy):
    """Fundamental macro — rate/CPI/PPI/employment/GDP based signals.

    Supports modes: rate_hike, cpi_surprise, ppi_surprise, employment, gdp.
    """

    name = "fundamental"
    description = "Fundamental macro: rate/CPI/PPI/employment/GDP"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.mode: str = str(self._parameters.get("mode", "rate_hike"))
        self.lookback: int = int(self._parameters.get("lookback", 30))
        self.z_threshold: float = float(self._parameters.get("z_threshold", 1.5))
        self.rate_column: str = str(self._parameters.get("rate_column", "interest_rate"))
        self.cpi_column: str = str(self._parameters.get("cpi_column", "cpi"))
        self.ppi_column: str = str(self._parameters.get("ppi_column", "ppi"))
        self.employment_column: str = str(self._parameters.get("employment_column", "nonfarm_payrolls"))
        self.gdp_column: str = str(self._parameters.get("gdp_column", "gdp_qoq"))
        self.inverse_relationship: bool = bool(self._parameters.get("inverse_relationship", True))

    @staticmethod
    def _zscore(series: pd.Series, period: int) -> pd.Series:
        roll_mean = series.rolling(window=period, min_periods=period).mean()
        roll_std = series.rolling(window=period, min_periods=period).std()
        return (series - roll_mean) / (roll_std + 1e-10)

    def _generic_signal(self, data: pd.DataFrame, column: str, price: float,
                        symbol: str) -> Optional[StrategySignal]:
        if column not in data.columns:
            return None
        series = data[column]
        if len(series) < self.lookback + 5:
            return None
        zs = self._zscore(series, self.lookback)
        z = float(zs.iloc[-1]) if not np.isnan(zs.iloc[-1]) else 0.0

        if z > self.z_threshold:
            direction = SignalDirection.SELL if self.inverse_relationship else SignalDirection.BUY
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                direction=direction,
                confidence=min((z - self.z_threshold) / 2.0, 1.0),
                entry_price=round(price, 6),
                reasoning=f"Fundamental {column}: z-score {z:.2f} > {self.z_threshold}",
                indicators={f"{column}_z": round(z, 3), "mode": self.mode},
            )
        if z < -self.z_threshold:
            direction = SignalDirection.BUY if self.inverse_relationship else SignalDirection.SELL
            return StrategySignal(
                strategy_name=self.name,
                symbol=symbol,
                direction=direction,
                confidence=min((abs(z) - self.z_threshold) / 2.0, 1.0),
                entry_price=round(price, 6),
                reasoning=f"Fundamental {column}: z-score {z:.2f} < {-self.z_threshold}",
                indicators={f"{column}_z": round(z, 3), "mode": self.mode},
            )
        return None

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            price = float(data["close"].iloc[-1]) if "close" in data.columns else 0.0
            symbol = kwargs.get("symbol", "")

            mode_map = {
                "rate_hike": self.rate_column,
                "cpi_surprise": self.cpi_column,
                "ppi_surprise": self.ppi_column,
                "employment": self.employment_column,
                "gdp": self.gdp_column,
            }
            column = mode_map.get(self.mode)
            if column is None:
                return self._hold(f"Unknown mode: {self.mode}")

            result = self._generic_signal(data, column, price, symbol)
            if result is not None:
                return result
            return self._hold(f"No fundamental signal in mode={self.mode}")
        except Exception as exc:
            logger.error("Fundamental error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["FundamentalStrategy"]
