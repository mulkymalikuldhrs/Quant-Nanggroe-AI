"""Mean Reversion Strategy.

Implements production-quality mean reversion trading using:
1. Bollinger Bands mean reversion
2. Z-score based mean reversion on rolling window
3. Ornstein-Uhlenbeck parameter estimation (half-life calculation)
4. Position sizing based on z-score magnitude

Academic References:
    - Bollinger, J. (2001). Bollinger on Bollinger Bands. McGraw-Hill.
    - Ornstein, L.S. & Uhlenbeck, G.E. (1930). "On the Theory of the Brownian Motion."
      Physical Review, 36(5), 823-841.
    - Avellaneda, M. & Lee, J.H. (2010). "Statistical Arbitrage in the US Equities Market."
      Quantitative Finance, 10(7), 761-782.
    - De Prado, M. (2018). Advances in Financial Machine Learning. Wiley. Ch.5.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands, Z-score, and OU process.

    The strategy enters long when price falls below the lower Bollinger Band
    (or when z-score drops below the entry threshold) and exits when price
    rises above the upper band (or z-score crosses above exit threshold).

    Position sizing is scaled by z-score magnitude: larger deviations receive
    bigger position sizes, following the OU half-life for optimal timing.

    Parameters:
        lookback: Rolling window for mean and std calculation (default 20).
        entry_z: Z-score threshold for entry (default -2.0).
        exit_z: Z-score threshold for exit (default 0.0).
        bb_std: Number of standard deviations for Bollinger Bands (default 2.0).
        stop_loss_pct: Stop loss as fraction of entry price (default 0.03).
        take_profit_pct: Take profit as fraction of entry price (default 0.06).
        max_position_size: Maximum position weight (default 1.0).
        use_ou_half_life: Whether to use OU half-life for timing (default True).
        symbol: Trading symbol for signal generation (default "ASSET").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MeanReversion", params=params)
        self.lookback: int = self.params.get("lookback", 20)
        self.entry_z: float = self.params.get("entry_z", -2.0)
        self.exit_z: float = self.params.get("exit_z", 0.0)
        self.bb_std: float = self.params.get("bb_std", 2.0)
        self.stop_loss_pct: float = self.params.get("stop_loss_pct", 0.03)
        self.take_profit_pct: float = self.params.get("take_profit_pct", 0.06)
        self.max_position_size: float = self.params.get("max_position_size", 1.0)
        self.use_ou_half_life: bool = self.params.get("use_ou_half_life", True)
        self.symbol: str = self.params.get("symbol", "ASSET")

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 10  # Extra buffer for stability

    def estimate_ou_half_life(self, series: pd.Series) -> float:
        """Estimate Ornstein-Uhlenbeck half-life via OLS regression.

        The OU process is:
            dX_t = theta * (mu - X_t) * dt + sigma * dW_t

        Discretized as:
            X_{t+1} - X_t = alpha + beta * X_t + epsilon

        Half-life = -ln(2) / beta  (where beta < 0 for mean-reverting)

        References:
            - Ornstein & Uhlenbeck (1930), Physical Review, 36(5), 823-841.

        Args:
            series: Price or spread series.

        Returns:
            Estimated half-life in number of bars. Returns np.inf if not mean-reverting.
        """
        if len(series) < 10:
            return np.inf

        lagged = series.shift(1).dropna()
        delta = series.diff().dropna()

        # Align indices
        common_idx = lagged.index.intersection(delta.index)
        if len(common_idx) < 5:
            return np.inf

        lagged = lagged.loc[common_idx]
        delta = delta.loc[common_idx]

        # OLS: delta = alpha + beta * lagged
        try:
            from scipy import stats as scipy_stats
            slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(
                lagged.values, delta.values
            )
        except (ValueError, np.linalg.LinAlgError):
            return np.inf

        if slope >= 0:
            # Not mean-reverting
            return np.inf

        half_life = -np.log(2) / slope
        return max(half_life, 1.0)

    def compute_close_zscore(self, data: pd.DataFrame) -> pd.Series:
        """Compute rolling z-score of close prices.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Z-score series.
        """
        return self.compute_zscore(data["close"], self.lookback)

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate mean reversion signal based on Bollinger Bands and Z-score.

        Entry logic (long):
            - Price closes below lower Bollinger Band AND
            - Z-score < entry_z threshold

        Exit logic (close long):
            - Z-score > exit_z threshold (mean reversion complete)

        Short logic is symmetric.

        Position sizing:
            - Scaled by |z-score| / max(|entry_z|, 1) * max_position_size
            - If OU half-life is used and half-life < lookback, boost confidence

        Args:
            data: OHLCV DataFrame.

        Returns:
            Signal if entry/exit condition met, None otherwise.
        """
        if not self.validate_data(data):
            return None

        close = data["close"]
        current_price = close.iloc[-1]

        # Compute Bollinger Bands
        upper, middle, lower = self.compute_bollinger_bands(
            close, self.lookback, self.bb_std
        )

        # Compute Z-score
        z_score_series = self.compute_close_zscore(data)
        current_z = z_score_series.iloc[-1]

        # Previous values for crossover detection
        prev_z = z_score_series.iloc[-2] if len(z_score_series) > 1 else 0.0

        # Estimate half-life if enabled
        half_life = None
        if self.use_ou_half_life:
            half_life = self.estimate_ou_half_life(close)

        # Check for NaN
        if np.isnan(current_z):
            return None

        # --- Entry signals ---
        # Long entry: z-score crosses below entry threshold
        if current_z < self.entry_z and prev_z >= self.entry_z:
            position_size = self._compute_position_size(current_z, half_life)
            stop_loss_price = current_price * (1 - self.stop_loss_pct)
            take_profit_price = current_price * (1 + self.take_profit_pct)

            confidence = min(abs(current_z) / (abs(self.entry_z) + 1), 1.0)
            if half_life is not None and half_life < self.lookback * 2:
                confidence = min(confidence * 1.2, 1.0)  # Boost if strongly mean-reverting

            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(stop_loss_price, 6),
                take_profit=round(take_profit_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Mean reversion BUY: z-score={current_z:.2f} < entry_z={self.entry_z}, "
                    f"price below lower BB={lower.iloc[-1]:.4f}, "
                    f"half_life={half_life:.1f}" if half_life else f"z-score={current_z:.2f}"
                ),
                evidence={
                    "z_score": round(float(current_z), 4),
                    "bb_upper": round(float(upper.iloc[-1]), 4),
                    "bb_middle": round(float(middle.iloc[-1]), 4),
                    "bb_lower": round(float(lower.iloc[-1]), 4),
                    "position_size": round(float(position_size), 4),
                    "half_life": round(float(half_life), 1) if half_life else None,
                },
                factors=["bollinger_band", "z_score", "mean_reversion"],
            )

        # Short entry: z-score crosses above negative entry threshold
        if current_z > -self.entry_z and prev_z <= -self.entry_z:
            position_size = self._compute_position_size(current_z, half_life)
            stop_loss_price = current_price * (1 + self.stop_loss_pct)
            take_profit_price = current_price * (1 - self.take_profit_pct)

            confidence = min(abs(current_z) / (abs(self.entry_z) + 1), 1.0)
            if half_life is not None and half_life < self.lookback * 2:
                confidence = min(confidence * 1.2, 1.0)

            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.SELL,
                confidence=round(confidence, 4),
                price=round(current_price, 6),
                stop_loss=round(stop_loss_price, 6),
                take_profit=round(take_profit_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Mean reversion SELL: z-score={current_z:.2f} > {-self.entry_z:.2f}, "
                    f"price above upper BB={upper.iloc[-1]:.4f}"
                ),
                evidence={
                    "z_score": round(float(current_z), 4),
                    "bb_upper": round(float(upper.iloc[-1]), 4),
                    "bb_middle": round(float(middle.iloc[-1]), 4),
                    "bb_lower": round(float(lower.iloc[-1]), 4),
                    "position_size": round(float(position_size), 4),
                    "half_life": round(float(half_life), 1) if half_life else None,
                },
                factors=["bollinger_band", "z_score", "mean_reversion"],
            )

        # --- Exit signals ---
        # Close long: z-score crosses above exit threshold
        if current_z > self.exit_z and prev_z <= self.exit_z:
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.CLOSE_LONG,
                confidence=0.7,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Mean reversion exit long: z-score={current_z:.2f} > exit_z={self.exit_z}",
                evidence={"z_score": round(float(current_z), 4)},
                factors=["z_score", "mean_reversion"],
            )

        # Close short: z-score crosses below negative exit threshold
        if current_z < -self.exit_z and prev_z >= -self.exit_z:
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.CLOSE_SHORT,
                confidence=0.7,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Mean reversion exit short: z-score={current_z:.2f} < {-self.exit_z:.2f}",
                evidence={"z_score": round(float(current_z), 4)},
                factors=["z_score", "mean_reversion"],
            )

        return None

    def _compute_position_size(
        self, z_score: float, half_life: Optional[float]
    ) -> float:
        """Compute position size scaled by z-score magnitude.

        Larger z-scores imply stronger mean reversion opportunity.
        If OU half-life is available and short, increase position size.

        Args:
            z_score: Current z-score value.
            half_life: Estimated OU half-life (None if not used).

        Returns:
            Position size between 0 and max_position_size.
        """
        base_size = min(abs(z_score) / (abs(self.entry_z) + 1), 1.0)
        position_size = base_size * self.max_position_size

        if half_life is not None and half_life < self.lookback:
            # Shorter half-life = faster mean reversion = more confidence
            position_size = min(position_size * 1.3, self.max_position_size)

        return round(float(position_size), 4)
