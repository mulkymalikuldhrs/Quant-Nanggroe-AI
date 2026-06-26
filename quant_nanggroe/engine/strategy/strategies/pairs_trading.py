"""Pairs Trading Strategy.

Pairs trading on two cointegrated assets: estimate hedge ratio via OLS on a
training window, trade the spread z-score, with transaction cost and frequency
controls to avoid lookahead bias and over-trading.

References:
    - Engle, R.F. & Granger, C.W.J. (1987). "Co-Integration and Error
      Correction." Econometrica, 55(2), 251-276.
    - Avellaneda, M. & Lee, J.H. (2010). "Statistical Arbitrage in the US
      Equities Market." Quantitative Finance, 10(7), 761-782.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class PairsTradingStrategy(BaseStrategy):
    """Pairs trading strategy using OLS hedge ratio and spread z-score.

    Spread = price_B - hedge_ratio * price_A.
    Entry when |z-score| > entry_z, exit when |z-score| < exit_z.

    Parameters:
        symbol: Primary symbol (asset A).
        symbol_pair: Second symbol (asset B).
        lookback: Rolling window for spread z-score (default 60).
        entry_z: Z-score threshold to open a position (default 2.0).
        exit_z: Z-score threshold to close a position (default 0.5).
        hedge_ratio_lookback: Bars used for OLS estimation (default 252).
        transaction_cost_bps: Round-turn transaction cost in bps (default 10.0).
        min_trade_interval_bars: Minimum bars between successive trades
            (default 5).
    """

    def __init__(self, params: Optional[Dict] = None) -> None:
        super().__init__(name="PairsTrading", params=params)
        self.symbol: str = self.params.get("symbol", "ASSET_A")
        self.symbol_pair: str = self.params.get("symbol_pair", "ASSET_B")
        self.lookback: int = self.params.get("lookback", 60)
        self.entry_z: float = self.params.get("entry_z", 2.0)
        self.exit_z: float = self.params.get("exit_z", 0.5)
        self.hedge_ratio_lookback: int = self.params.get("hedge_ratio_lookback", 252)
        self.transaction_cost_bps: float = self.params.get("transaction_cost_bps", 10.0)
        self.min_trade_interval_bars: int = self.params.get("min_trade_interval_bars", 5)

        self._last_trade_bar: int = -self.min_trade_interval_bars  # ponytail: negative so first trade is allowed
        self._position: float = 0.0  # +1.0 long spread, -1.0 short spread, 0.0 flat

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.hedge_ratio_lookback + self.lookback

    @staticmethod
    def _ols_hedge_ratio(y: pd.Series, x: pd.Series) -> float:
        """Regress y (B) on x (A) with intercept, return slope.

        Returns 1.0 on failure.
        """
        # ponytail: np.linalg.lstsq instead of statsmodels for speed
        x_ = np.column_stack([np.ones(len(x)), x.values])
        try:
            beta = np.linalg.lstsq(x_, y.values, rcond=None)[0]
            return float(beta[1])
        except np.linalg.LinAlgError:
            return 1.0

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        # Identify close-price columns.  The engine passes a DataFrame whose
        # columns include the symbol names (each containing the close series).
        if self.symbol in data.columns:
            close_a = data[self.symbol].astype(float)
            close_b = data[self.symbol_pair].astype(float)
        else:
            # ponytail: fallback for single-symbol DataFrames — caller error
            return None

        min_bars = self.hedge_ratio_lookback + self.lookback
        if len(close_a) < min_bars:
            return None

        # --- 1. Estimate hedge ratio on the training window (no lookahead) ---
        train = slice(-self.hedge_ratio_lookback, None)
        a_train = close_a.iloc[train]
        b_train = close_b.iloc[train]
        hedge_ratio = self._ols_hedge_ratio(b_train, a_train)

        # --- 2. Compute spread and z-score on the most-recent lookback ---
        spread = b_train - hedge_ratio * a_train
        recent_spread = spread.iloc[-self.lookback:]
        spread_mean = float(recent_spread.mean())
        spread_std = float(recent_spread.std(ddof=1))
        if spread_std < 1e-10:
            return None
        z = (recent_spread - spread_mean) / spread_std
        current_z = float(z.iloc[-1])
        prev_z = float(z.iloc[-2]) if len(z) > 1 else 0.0

        if np.isnan(current_z):
            return None

        current_price = float(close_b.iloc[-1])
        bar_index = len(data) - 1
        bars_since_last = bar_index - self._last_trade_bar

        # --- 3. Exit: z-score reverted past exit threshold ---
        if self._position != 0.0 and abs(current_z) < self.exit_z and abs(prev_z) >= self.exit_z:
            sig_type = SignalType.CLOSE_LONG if self._position > 0 else SignalType.CLOSE_SHORT
            self._position = 0.0
            self._last_trade_bar = bar_index
            return Signal(
                symbol=self.symbol,
                signal_type=sig_type,
                confidence=0.7,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Pairs exit {'long' if sig_type == SignalType.CLOSE_LONG else 'short'}: "
                    f"z={current_z:.2f} reverted to |z| < {self.exit_z}"
                ),
                evidence={
                    "spread_z": round(current_z, 4),
                    "hedge_ratio": round(hedge_ratio, 4),
                },
                factors=["pairs_trading", "spread_mean_reversion"],
            )

        # --- 4. Respect minimum trade interval ---
        if bars_since_last < self.min_trade_interval_bars:
            return None

        # --- 5. Entry: z-score exceeds entry threshold ---
        # Cost-adjusted entry: widen threshold when transaction costs are high
        # so marginal trades are filtered out.
        # ponytail: linear adjustment instead of full portfolio optimisation
        cost_adjust = self.transaction_cost_bps * 0.0001 * 10.0
        effective_entry = self.entry_z + cost_adjust

        # Long spread (long B, short A): z-score is extremely negative
        if current_z < -effective_entry and prev_z >= -effective_entry:
            self._position = 1.0
            self._last_trade_bar = bar_index
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.BUY,
                confidence=1.0,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Pairs long spread: z={current_z:.2f} < -{effective_entry:.1f}, "
                    f"hr={hedge_ratio:.4f}"
                ),
                evidence={
                    "spread_z": round(current_z, 4),
                    "hedge_ratio": round(hedge_ratio, 4),
                    "training_bars": self.hedge_ratio_lookback,
                },
                factors=["pairs_trading", "spread_mean_reversion"],
            )

        # Short spread (short B, long A): z-score is extremely positive
        if current_z > effective_entry and prev_z <= effective_entry:
            self._position = -1.0
            self._last_trade_bar = bar_index
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.SELL,
                confidence=1.0,
                price=round(current_price, 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"Pairs short spread: z={current_z:.2f} > {effective_entry:.1f}, "
                    f"hr={hedge_ratio:.4f}"
                ),
                evidence={
                    "spread_z": round(current_z, 4),
                    "hedge_ratio": round(hedge_ratio, 4),
                    "training_bars": self.hedge_ratio_lookback,
                },
                factors=["pairs_trading", "spread_mean_reversion"],
            )

        return None
