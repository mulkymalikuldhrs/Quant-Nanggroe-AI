"""Statistical Arbitrage Strategy.

PCA-based factor model for statistical arbitrage. Decomposes a universe
of stock returns into systematic factors via PCA and trades mean reversion
on the idiosyncratic residuals (orphan alpha).

The strategy:
1. Builds a cross-sectional universe of stocks from the input data
2. Computes multi-period returns and standardizes them
3. Extracts top K principal components via SVD (K = n_factors)
4. Computes residuals = actual returns - factor-model predicted returns
5. Z-scores residuals and enters when |z| exceeds entry_threshold
6. Exits when the residual z-score reverts below exit_threshold

Academic References:
    - Avellaneda, M. & Lee, J.H. (2010). "Statistical Arbitrage in the US
      Equities Market." Quantitative Finance, 10(7), 761-782.
    - Chamberlain, G. & Rothschild, M. (1983). "Arbitrage, Factor Structure,
      and Mean-Variance Analysis on Large Asset Markets." Econometrica,
      51(5), 1281-1304.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class StatisticalArbitrageStrategy(BaseStrategy):
    """Statistical arbitrage via PCA factor model and residual mean reversion.

    Builds a universe of stocks, extracts common risk factors via PCA on
    standardized returns, and trades stocks whose residual returns deviate
    significantly from zero. The systematic factor exposure is hedged out,
    leaving only the idiosyncratic (orphan) alpha to trade.

    Parameters:
        lookback: Rolling window for PCA estimation (default 60).
        n_factors: Number of PCA factors to extract (default 3).
        entry_threshold: Z-score threshold to enter (default 2.0).
        exit_threshold: Z-score threshold to exit (default 0.5).
        return_lookback: Period for multi-period return computation (default 20).
        universe_size: Maximum number of stocks in the universe (default 20).
        transaction_cost_bps: Estimated transaction cost in basis points (default 10.0).
        min_trade_interval_bars: Minimum bars between trades (default 10).
        symbol: Primary trading symbol (default "ASSET").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="StatisticalArbitrage", params=params)
        self.lookback: int = self.params.get("lookback", 60)
        self.n_factors: int = self.params.get("n_factors", 3)
        self.entry_threshold: float = self.params.get("entry_threshold", 2.0)
        self.exit_threshold: float = self.params.get("exit_threshold", 0.5)
        self.return_lookback: int = self.params.get("return_lookback", 20)
        self.universe_size: int = self.params.get("universe_size", 20)
        self.transaction_cost_bps: float = self.params.get("transaction_cost_bps", 10.0)
        self.min_trade_interval_bars: int = self.params.get("min_trade_interval_bars", 10)
        self.symbol: str = self.params.get("symbol", "ASSET")

        # Internal state
        self._has_position: bool = False
        self._last_trade_bar: int = -self.min_trade_interval_bars  # ponytail: start eligible

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return max(self.lookback, self.return_lookback) + 1

    @staticmethod
    def _compute_pca(returns_matrix: np.ndarray, n_components: int) -> tuple[np.ndarray, np.ndarray]:  # ponytail: no sklearn dep
        """PCA via SVD. Returns (factor_returns, factor_loadings).

        Args:
            returns_matrix: Centered returns, shape (T, N).
            n_components: Number of principal components.

        Returns:
            Tuple of (factors, loadings) where factors is (T, K)
            and loadings is (N, K).
        """
        centered = returns_matrix - returns_matrix.mean(axis=0)
        _U, _S, Vt = np.linalg.svd(centered, full_matrices=False)  # ponytail: U,S unused
        loadings = Vt[:n_components].T
        factors = centered @ loadings
        return factors, loadings

    def _select_universe(self, close: pd.DataFrame) -> List[str]:
        """Select the top stocks by average price for the trading universe."""
        n = min(self.universe_size, len(close.columns))
        ranked = close.mean().sort_values(ascending=False)
        return ranked.index[:n].tolist()

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate statistical arbitrage signal from PCA residuals.

        Expects data["close"] to be a DataFrame with one column per stock
        in the universe. Computes cross-sectional returns, runs PCA, and
        trades the primary symbol's residual z-score.

        Signal value (stored in evidence) ranges from -1.0 (short) to
        +1.0 (long), with 0.0 meaning flat / no position.

        Args:
            data: DataFrame with 'close' column (DataFrame of stock prices).

        Returns:
            Signal if entry/exit condition met, None otherwise.
        """
        if not self.validate_data(data):
            return None

        close = data["close"]
        if isinstance(close, pd.Series):
            return None

        universe = self._select_universe(close)
        if len(universe) < self.n_factors + 1:
            return None

        returns = close[universe].pct_change(self.return_lookback).dropna()
        if len(returns) < self.lookback:
            return None

        # PCA on trailing window
        returns_window = returns.iloc[-self.lookback:].values
        n_components = min(self.n_factors, returns_window.shape[1] - 1)
        if n_components < 1:
            return None

        factors, loadings = self._compute_pca(returns_window, n_components)
        predicted = factors @ loadings.T
        centered = returns_window - returns_window.mean(axis=0)
        residuals = centered - predicted

        # Z-score each stock's residuals cross-sectionally at the last time step
        residual_mean = residuals.mean(axis=0)
        residual_std = residuals.std(axis=0, ddof=1)
        residual_std = np.where(residual_std < 1e-10, 1.0, residual_std)  # ponytail: div-by-zero guard
        z_scores = (residuals[-1] - residual_mean) / residual_std

        if self.symbol not in universe:
            return None

        idx = universe.index(self.symbol)
        current_z = float(z_scores[idx])

        if np.isnan(current_z):
            return None

        bar_count = len(data)
        bars_since_last = bar_count - self._last_trade_bar
        current_price = round(float(close[self.symbol].iloc[-1]), 6)
        signal_value = 0.0

        # Exit on reversion
        if abs(current_z) < self.exit_threshold:
            if self._has_position:
                self._has_position = False
                self._last_trade_bar = bar_count
                return Signal(
                    symbol=self.symbol,
                    signal_type=SignalType.EXIT_ALL,
                    confidence=0.7,
                    price=current_price,
                    source_agent=self.name,
                source_strategy=self.name,
                    reasoning=(
                        f"StatArb EXIT: residual z={current_z:.2f} reverted "
                        f"below |{self.exit_threshold}|"
                    ),
                    evidence={
                        "residual_z": round(current_z, 4),
                        "signal_value": 0.0,
                        "universe_size": len(universe),
                        "n_factors": n_components,
                        "transaction_cost_bps": self.transaction_cost_bps,
                    },
                    factors=["statistical_arbitrage", "pca_residual", "mean_reversion"],
                )
            return None

        # Trade frequency gate for new entries
        if bars_since_last < self.min_trade_interval_bars:
            return None

        # Entry: short (z > +threshold)
        if current_z > self.entry_threshold:
            self._has_position = True
            self._last_trade_bar = bar_count
            confidence = min(abs(current_z) / self.entry_threshold, 1.0)
            signal_value = -confidence
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.SELL,
                confidence=round(confidence, 4),
                price=current_price,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"StatArb SHORT: residual z={current_z:.2f} > "
                    f"{self.entry_threshold}, n_factors={n_components}"
                ),
                evidence={
                    "residual_z": round(current_z, 4),
                    "signal_value": round(signal_value, 4),
                    "universe_size": len(universe),
                    "n_factors": n_components,
                    "transaction_cost_bps": self.transaction_cost_bps,
                },
                factors=["statistical_arbitrage", "pca_residual", "mean_reversion"],
            )

        # Entry: long (z < -threshold)
        if current_z < -self.entry_threshold:
            self._has_position = True
            self._last_trade_bar = bar_count
            confidence = min(abs(current_z) / self.entry_threshold, 1.0)
            signal_value = confidence
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 4),
                price=current_price,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"StatArb LONG: residual z={current_z:.2f} < "
                    f"{-self.entry_threshold}, n_factors={n_components}"
                ),
                evidence={
                    "residual_z": round(current_z, 4),
                    "signal_value": round(signal_value, 4),
                    "universe_size": len(universe),
                    "n_factors": n_components,
                    "transaction_cost_bps": self.transaction_cost_bps,
                },
                factors=["statistical_arbitrage", "pca_residual", "mean_reversion"],
            )

        return None
