"""Pairs Trading Strategy.

Implements production-quality pairs trading using:
1. Cointegration testing (Engle-Granger, Johansen)
2. Spread calculation and z-scoring
3. Dynamic hedge ratio estimation (OLS, Kalman Filter)
4. Entry/exit based on spread z-score
5. Half-life based position management

Academic References:
    - Engle, R.F. & Granger, C.W.J. (1987). "Co-Integration and Error Correction."
      Econometrica, 55(2), 251-276.
    - Johansen, S. (1991). "Estimation and Hypothesis Testing of Cointegration
      Vectors in Gaussian Vector Autoregressive Models." Econometrica, 59(6), 1551-1580.
    - Elliott, R.J., Van Der Hoek, J., & Malcolm, W.P. (2005). "Pairs Trading."
      Quantitative Finance, 5(3), 271-276.
    - Avellaneda, M. & Lee, J.H. (2010). "Statistical Arbitrage in the US Equities Market."
      Quantitative Finance, 10(7), 761-782.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from statsmodels.tsa.stattools import coint, adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class PairsTradingStrategy(BaseStrategy):
    """Pairs trading strategy using cointegration and spread mean reversion.

    Identifies cointegrated pairs, computes the spread, and trades the
    spread when it deviates significantly from its mean.

    Parameters:
        symbol_y: Dependent variable symbol (default "ASSET_Y").
        symbol_x: Independent variable symbol (default "ASSET_X").
        lookback: Rolling window for spread statistics (default 60).
        entry_z: Z-score threshold for spread entry (default 2.0).
        exit_z: Z-score threshold for spread exit (default 0.5).
        stop_loss_pct: Stop loss fraction (default 0.05).
        coint_method: Cointegration test method: 'engle_granger' or 'johansen'
            (default 'engle_granger').
        hedge_method: Hedge ratio estimation: 'ols' or 'kalman' (default 'ols').
        kalman_Q: Kalman filter process noise (default 1e-5).
        kalman_R: Kalman filter measurement noise (default 1e-3).
        use_half_life: Whether to adjust exit based on half-life (default True).
        min_coint_pvalue: Minimum cointegration p-value to trade (default 0.05).
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="PairsTrading", params=params)
        self.symbol_y: str = self.params.get("symbol_y", "ASSET_Y")
        self.symbol_x: str = self.params.get("symbol_x", "ASSET_X")
        self.lookback: int = self.params.get("lookback", 60)
        self.entry_z: float = self.params.get("entry_z", 2.0)
        self.exit_z: float = self.params.get("exit_z", 0.5)
        self.stop_loss_pct: float = self.params.get("stop_loss_pct", 0.05)
        self.coint_method: str = self.params.get("coint_method", "engle_granger")
        self.hedge_method: str = self.params.get("hedge_method", "ols")
        self.kalman_Q: float = self.params.get("kalman_Q", 1e-5)
        self.kalman_R: float = self.params.get("kalman_R", 1e-3)
        self.use_half_life: bool = self.params.get("use_half_life", True)
        self.min_coint_pvalue: float = self.params.get("min_coint_pvalue", 0.05)

    def required_columns(self) -> List[str]:
        return ["close_y", "close_x"]

    def warmup_period(self) -> int:
        return self.lookback + 30

    def test_cointegration_engle_granger(
        self, y: pd.Series, x: pd.Series
    ) -> Tuple[float, float]:
        """Test cointegration using Engle-Granger two-step method.

        Step 1: Regress y on x to get hedge ratio beta.
        Step 2: Test residuals for stationarity using ADF test.

        Reference:
            Engle & Granger (1987), Econometrica, 55(2), 251-276.

        Args:
            y: Dependent variable series.
            x: Independent variable series.

        Returns:
            Tuple of (t_statistic, p_value) from cointegration test.
        """
        try:
            score, pvalue, _ = coint(y, x, method="aeg")
            return float(score), float(pvalue)
        except Exception:
            return 0.0, 1.0

    def test_cointegration_johansen(
        self, y: pd.Series, x: pd.Series
    ) -> Tuple[float, float]:
        """Test cointegration using Johansen procedure.

        Estimates the cointegration rank using trace and eigenvalue tests.

        Reference:
            Johansen, S. (1991), Econometrica, 59(6), 1551-1580.

        Args:
            y: First variable series.
            x: Second variable series.

        Returns:
            Tuple of (trace_stat, p_value_proxy) for rank >= 1.
        """
        try:
            data = pd.DataFrame({"y": y, "x": x}).dropna()
            if len(data) < 30:
                return 0.0, 1.0

            result = coint_johansen(data.values, det_order=0, k_ar_diff=1)

            # Trace test for r=0 (at least one cointegration vector)
            trace_stat = float(result.lr1[0])
            # Critical value at 5% for n=2
            crit_5pct = float(result.cvt[0, 1])

            # Proxy p-value: if trace_stat > critical value, cointegration exists
            p_proxy = 0.01 if trace_stat > crit_5pct else 0.5
            return trace_stat, p_proxy
        except Exception:
            return 0.0, 1.0

    def compute_hedge_ratio_ols(
        self, y: pd.Series, x: pd.Series
    ) -> Tuple[float, pd.Series]:
        """Compute hedge ratio using OLS regression.

        y_t = alpha + beta * x_t + epsilon_t

        Args:
            y: Dependent variable series.
            x: Independent variable series.

        Returns:
            Tuple of (hedge_ratio, residuals).
        """
        try:
            x_with_const = np.column_stack([np.ones(len(x)), x.values])
            beta_full = np.linalg.lstsq(x_with_const, y.values, rcond=None)[0]
            hedge_ratio = float(beta_full[1])
            residuals = y.values - x_with_const @ beta_full
            return hedge_ratio, pd.Series(residuals, index=y.index)
        except (np.linalg.LinAlgError, ValueError):
            return 1.0, y - x

    def compute_hedge_ratio_kalman(
        self, y: pd.Series, x: pd.Series
    ) -> Tuple[pd.Series, pd.Series]:
        """Compute dynamic hedge ratio using Kalman Filter.

        State equation:  beta_t = beta_{t-1} + w_t,  w_t ~ N(0, Q)
        Observation:     y_t = x_t * beta_t + v_t,   v_t ~ N(0, R)

        The Kalman filter adaptively estimates the hedge ratio at each
        time step, allowing for time-varying relationships.

        Reference:
            Elliott, Van Der Hoek, & Malcolm (2005), Quantitative Finance, 5(3), 271-276.

        Args:
            y: Dependent variable series.
            x: Independent variable series.

        Returns:
            Tuple of (hedge_ratios, residuals) as Series.
        """
        n = len(y)
        hedge_ratios = np.zeros(n)
        residuals = np.zeros(n)

        # Initialize
        beta = 0.0  # Initial hedge ratio estimate
        P = 1.0  # Initial state covariance

        Q = self.kalman_Q  # Process noise
        R = self.kalman_R  # Measurement noise

        for t in range(n):
            # Predict
            beta_pred = beta
            P_pred = P + Q

            # Observation
            x_t = float(x.iloc[t])
            y_t = float(y.iloc[t])

            # Innovation
            innovation = y_t - x_t * beta_pred

            # Innovation covariance
            S = x_t * P_pred * x_t + R

            # Kalman gain
            if abs(S) > 1e-15:
                K = P_pred * x_t / S
            else:
                K = 0.0

            # Update
            beta = beta_pred + K * innovation
            P = (1 - K * x_t) * P_pred

            hedge_ratios[t] = beta
            residuals[t] = innovation

        return (
            pd.Series(hedge_ratios, index=y.index),
            pd.Series(residuals, index=y.index),
        )

    def compute_spread(
        self, y: pd.Series, x: pd.Series, hedge_ratio: float
    ) -> pd.Series:
        """Compute the spread: spread_t = y_t - hedge_ratio * x_t.

        Args:
            y: Dependent variable prices.
            x: Independent variable prices.
            hedge_ratio: Estimated hedge ratio.

        Returns:
            Spread series.
        """
        return y - hedge_ratio * x

    def estimate_half_life(self, spread: pd.Series) -> float:
        """Estimate half-life of mean reversion of the spread.

        Uses OLS regression on the spread's changes:
            delta_spread_t = alpha + beta * spread_{t-1} + epsilon

        Half-life = -ln(2) / beta

        Args:
            spread: Spread series.

        Returns:
            Estimated half-life in bars. Returns np.inf if not mean-reverting.
        """
        if len(spread) < 10:
            return np.inf

        spread_lag = spread.shift(1).dropna()
        spread_delta = spread.diff().dropna()

        common_idx = spread_lag.index.intersection(spread_delta.index)
        if len(common_idx) < 5:
            return np.inf

        spread_lag = spread_lag.loc[common_idx]
        spread_delta = spread_delta.loc[common_idx]

        try:
            slope, _, _, _, _ = scipy_stats.linregress(
                spread_lag.values, spread_delta.values
            )
        except (ValueError, np.linalg.LinAlgError):
            return np.inf

        if slope >= 0:
            return np.inf

        half_life = -np.log(2) / slope
        return max(half_life, 1.0)

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate pairs trading signal based on spread z-score.

        The method:
        1. Test cointegration between Y and X
        2. Estimate hedge ratio (OLS or Kalman)
        3. Compute spread and its z-score
        4. Enter when z-score exceeds threshold
        5. Exit when z-score reverts

        Args:
            data: DataFrame with 'close_y' and 'close_x' columns.

        Returns:
            Signal if spread condition met, None otherwise.
        """
        if not self.validate_data(data):
            return None

        y = data["close_y"]
        x = data["close_x"]

        # Test cointegration
        if self.coint_method == "johansen":
            _, pvalue = self.test_cointegration_johansen(y, x)
        else:
            _, pvalue = self.test_cointegration_engle_granger(y, x)

        is_cointegrated = pvalue < self.min_coint_pvalue

        # Estimate hedge ratio
        if self.hedge_method == "kalman":
            hedge_ratios, _ = self.compute_hedge_ratio_kalman(y, x)
            current_hedge = float(hedge_ratios.iloc[-1])
            # For spread computation, use the latest Kalman estimate
            spread = self.compute_spread(y, x, current_hedge)
        else:
            current_hedge, spread = self.compute_hedge_ratio_ols(y, x)

        # Compute rolling z-score of spread
        if len(spread) < self.lookback:
            return None

        rolling_mean = spread.rolling(window=self.lookback, min_periods=self.lookback).mean()
        rolling_std = spread.rolling(window=self.lookback, min_periods=self.lookback).std()

        z_score = (spread - rolling_mean) / (rolling_std + 1e-10)
        current_z = float(z_score.iloc[-1])
        prev_z = float(z_score.iloc[-2]) if len(z_score) > 1 else 0.0

        if np.isnan(current_z):
            return None

        # Estimate half-life
        half_life = self.estimate_half_life(spread) if self.use_half_life else None

        # Adjust entry threshold based on half-life
        effective_entry_z = self.entry_z
        if half_life is not None and half_life < self.lookback:
            effective_entry_z = max(self.entry_z * 0.8, 1.5)  # More aggressive for fast MR

        # --- Entry signals ---
        # Long Y / Short X: spread is too low (buy the spread)
        if current_z < -effective_entry_z and prev_z >= -effective_entry_z:
            confidence = min(abs(current_z) / effective_entry_z, 1.0)
            if not is_cointegrated:
                confidence *= 0.5  # Reduce confidence if not cointegrated

            return Signal(
                symbol=self.symbol_y,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 4),
                price=round(float(y.iloc[-1]), 6),
                stop_loss=round(float(y.iloc[-1]) * (1 - self.stop_loss_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Pairs BUY {self.symbol_y}/SELL {self.symbol_x}: "
                    f"z={current_z:.2f} < -{effective_entry_z:.1f}, "
                    f"hedge={current_hedge:.4f}, coint_p={pvalue:.3f}"
                ),
                evidence={
                    "spread_z": round(current_z, 4),
                    "hedge_ratio": round(current_hedge, 4),
                    "coint_pvalue": round(pvalue, 4),
                    "is_cointegrated": is_cointegrated,
                    "half_life": round(half_life, 1) if half_life else None,
                },
                factors=["pairs_trading", "cointegration", "spread_mean_reversion"],
            )

        # Short Y / Long X: spread is too high (sell the spread)
        if current_z > effective_entry_z and prev_z <= effective_entry_z:
            confidence = min(abs(current_z) / effective_entry_z, 1.0)
            if not is_cointegrated:
                confidence *= 0.5

            return Signal(
                symbol=self.symbol_y,
                signal_type=SignalType.SELL,
                confidence=round(confidence, 4),
                price=round(float(y.iloc[-1]), 6),
                stop_loss=round(float(y.iloc[-1]) * (1 + self.stop_loss_pct), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Pairs SELL {self.symbol_y}/BUY {self.symbol_x}: "
                    f"z={current_z:.2f} > {effective_entry_z:.1f}, "
                    f"hedge={current_hedge:.4f}, coint_p={pvalue:.3f}"
                ),
                evidence={
                    "spread_z": round(current_z, 4),
                    "hedge_ratio": round(current_hedge, 4),
                    "coint_pvalue": round(pvalue, 4),
                    "is_cointegrated": is_cointegrated,
                    "half_life": round(half_life, 1) if half_life else None,
                },
                factors=["pairs_trading", "cointegration", "spread_mean_reversion"],
            )

        # --- Exit signals ---
        # Close long spread (close Y long)
        if current_z > -self.exit_z and prev_z <= -self.exit_z:
            return Signal(
                symbol=self.symbol_y,
                signal_type=SignalType.CLOSE_LONG,
                confidence=0.7,
                price=round(float(y.iloc[-1]), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Pairs exit long: z={current_z:.2f} reverted to -{self.exit_z:.1f}",
                evidence={"spread_z": round(current_z, 4)},
                factors=["pairs_trading", "spread_mean_reversion"],
            )

        # Close short spread (close Y short)
        if current_z < self.exit_z and prev_z >= self.exit_z:
            return Signal(
                symbol=self.symbol_y,
                signal_type=SignalType.CLOSE_SHORT,
                confidence=0.7,
                price=round(float(y.iloc[-1]), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"Pairs exit short: z={current_z:.2f} reverted to {self.exit_z:.1f}",
                evidence={"spread_z": round(current_z, 4)},
                factors=["pairs_trading", "spread_mean_reversion"],
            )

        return None
