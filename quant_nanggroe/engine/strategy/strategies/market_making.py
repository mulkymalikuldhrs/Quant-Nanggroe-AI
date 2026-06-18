"""Market Making Strategy.

Implements production-quality market making using:
1. Avellaneda-Stoikov optimal quotes
2. Inventory management and skew
3. Spread optimization based on volatility
4. Adverse selection protection
5. Fill probability estimation

Academic References:
    - Avellaneda, M. & Stoikov, S. (2008). "High-Frequency Trading in a Limit Order Book."
      Quantitative Finance, 8(3), 217-224.
    - Glosten, L.R. & Milgrom, P.R. (1985). "Bid, Ask and Transaction Prices in a
      Specialist Market with Heterogeneously Informed Traders." Journal of Financial
      Economics, 14(1), 71-100.
    - Cartea, A., Jaimungal, S., & Penalva, J. (2015). Algorithmic and High-Frequency
      Trading. Cambridge University Press.
    - Stoikov, S. (2018). "The Micro-Price: A High Frequency Estimator of Future Prices."
      Quantitative Finance, 18(12), 2039-2058.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class MarketMakingStrategy(BaseStrategy):
    """Market making strategy using Avellaneda-Stoikov optimal quotes.

    Computes optimal bid and ask prices based on:
    - Current inventory level
    - Volatility estimate
    - Time to close (risk horizon)
    - Risk aversion parameter

    The reservation price shifts away from mid based on inventory:
        r = S - q * gamma * sigma^2 * T

    Optimal spread around reservation price:
        delta_bid = delta_ask = gamma * sigma^2 * T / 2 + (1/gamma) * ln(1 + gamma/k)

    Where k is the order book intensity parameter.

    Parameters:
        gamma: Risk aversion parameter (default 0.1).
        sigma_est_window: Window for volatility estimation (default 50).
        T: Time horizon for inventory risk (default 1.0, in same units as bar frequency).
        k: Order book intensity parameter (default 1.5).
        A: Order arrival rate scaling (default 0.001).
        max_inventory: Maximum absolute inventory (default 10).
        min_spread: Minimum spread to maintain (default 0.0001).
        adverse_selection_threshold: Z-score for adverse selection filter (default 3.0).
        inventory_skew_factor: Additional skew per unit of inventory (default 0.001).
        symbol: Trading symbol (default "ASSET").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="MarketMaking", params=params)
        self.gamma: float = self.params.get("gamma", 0.1)
        self.sigma_est_window: int = self.params.get("sigma_est_window", 50)
        self.T: float = self.params.get("T", 1.0)
        self.k: float = self.params.get("k", 1.5)
        self.A: float = self.params.get("A", 0.001)
        self.max_inventory: int = self.params.get("max_inventory", 10)
        self.min_spread: float = self.params.get("min_spread", 0.0001)
        self.adverse_selection_threshold: float = self.params.get(
            "adverse_selection_threshold", 3.0
        )
        self.inventory_skew_factor: float = self.params.get(
            "inventory_skew_factor", 0.001
        )
        self.symbol: str = self.params.get("symbol", "ASSET")

        # Internal state
        self._current_inventory: int = 0
        self._mid_prices: List[float] = []

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.sigma_est_window + 10

    def estimate_volatility(self, data: pd.DataFrame) -> float:
        """Estimate current volatility for quote computation.

        Uses close-to-close returns over the estimation window,
        annualized appropriately.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Estimated volatility (per-bar).
        """
        close = data["close"]
        returns = close.pct_change().dropna()

        if len(returns) < self.sigma_est_window:
            window = min(len(returns), 20)
            if window < 2:
                return 0.01
        else:
            window = self.sigma_est_window

        recent = returns.iloc[-window:]
        sigma = float(recent.std())
        return max(sigma, 1e-6)

    def compute_reservation_price(
        self, mid_price: float, inventory: int, sigma: float, T: float
    ) -> float:
        """Compute Avellaneda-Stoikov reservation price.

        r = S - q * gamma * sigma^2 * T

        Where:
        - S is the current mid price
        - q is the current inventory (positive = long)
        - gamma is risk aversion
        - sigma is volatility
        - T is time to close

        Reference:
            Avellaneda & Stoikov (2008), Quantitative Finance, 8(3), 217-224.

        Args:
            mid_price: Current mid price.
            inventory: Current inventory position.
            sigma: Estimated per-bar volatility.
            T: Time horizon.

        Returns:
            Reservation price.
        """
        return mid_price - inventory * self.gamma * sigma ** 2 * T

    def compute_optimal_spread(self, sigma: float, T: float) -> float:
        """Compute Avellaneda-Stoikov optimal half-spread.

        delta = gamma * sigma^2 * T / 2 + (1/gamma) * ln(1 + gamma/k)

        Reference:
            Avellaneda & Stoikov (2008), Quantitative Finance, 8(3), 217-224.

        Args:
            sigma: Estimated per-bar volatility.
            T: Time horizon.

        Returns:
            Optimal half-spread.
        """
        if self.k <= 0:
            return sigma * 2.0  # Fallback: 2 sigma

        first_term = self.gamma * sigma ** 2 * T / 2.0
        second_term = (1.0 / self.gamma) * math.log(1.0 + self.gamma / self.k)
        return first_term + second_term

    def compute_optimal_quotes(
        self, mid_price: float, inventory: int, sigma: float, T: float
    ) -> Tuple[float, float, float, float]:
        """Compute optimal bid and ask prices.

        The reservation price adjusts for inventory risk, and the
        optimal spread determines the distance from the reservation price.

        Additional inventory skew shifts quotes further from mid when
        inventory is large.

        Args:
            mid_price: Current mid price.
            inventory: Current inventory (positive = long).
            sigma: Estimated volatility.
            T: Time horizon.

        Returns:
            Tuple of (bid_price, ask_price, bid_size, ask_size).
        """
        reservation = self.compute_reservation_price(mid_price, inventory, sigma, T)
        half_spread = self.compute_optimal_spread(sigma, T)

        # Inventory skew: shift quotes based on inventory
        skew = inventory * self.inventory_skew_factor * mid_price

        bid_price = reservation - half_spread - skew
        ask_price = reservation + half_spread - skew

        # Ensure minimum spread
        if ask_price - bid_price < self.min_spread:
            center = (bid_price + ask_price) / 2
            bid_price = center - self.min_spread / 2
            ask_price = center + self.min_spread / 2

        # Size based on fill probability and inventory limits
        bid_size, ask_size = self._compute_order_sizes(inventory)

        return bid_price, ask_price, bid_size, ask_size

    def _compute_order_sizes(self, inventory: int) -> Tuple[float, float]:
        """Compute order sizes based on fill probability and inventory limits.

        Reduce bid size when heavily long, reduce ask size when heavily short.

        Args:
            inventory: Current inventory.

        Returns:
            Tuple of (bid_size, ask_size).
        """
        # Base size
        base_size = 1.0

        # Reduce buying when long, reduce selling when short
        bid_size = base_size * max(1.0 - inventory / self.max_inventory, 0.1)
        ask_size = base_size * max(1.0 + inventory / self.max_inventory, 0.1)

        return round(bid_size, 4), round(ask_size, 4)

    def estimate_fill_probability(
        self, deviation: float, sigma: float
    ) -> float:
        """Estimate probability of order fill based on distance from mid.

        Uses exponential decay model:
            P(fill) = A * exp(-k * delta)

        Where delta is the distance from mid price in units of sigma.

        Reference:
            Avellaneda & Stoikov (2008), Quantitative Finance, 8(3), 217-224.

        Args:
            deviation: Distance from mid price.
            sigma: Current volatility.

        Returns:
            Fill probability between 0 and 1.
        """
        if sigma < 1e-10:
            return 0.5

        normalized_deviation = deviation / sigma
        prob = self.A * math.exp(-self.k * normalized_deviation)
        return min(max(prob, 0.0), 1.0)

    def detect_adverse_selection(self, data: pd.DataFrame) -> bool:
        """Detect adverse selection using price impact analysis.

        If recent price moves are large relative to normal volatility,
        it may indicate informed traders are active (adverse selection).

        Reference:
            Glosten & Milgrom (1985), Journal of Financial Economics, 14(1), 71-100.

        Args:
            data: OHLCV DataFrame.

        Returns:
            True if adverse selection is detected.
        """
        close = data["close"]
        returns = close.pct_change().dropna()

        if len(returns) < 20:
            return False

        recent_return = float(returns.iloc[-1])
        recent_std = float(returns.iloc[-20:].std())

        if recent_std < 1e-10:
            return False

        z_score = abs(recent_return / recent_std)
        return z_score > self.adverse_selection_threshold

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate market making signal with optimal quotes.

        Produces bid/ask quotes based on the Avellaneda-Stoikov framework
        and current market conditions. Includes adverse selection filter.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Signal with bid/ask quote information, or None if adverse selection detected.
        """
        if not self.validate_data(data):
            return None

        # Check for adverse selection
        is_adverse = self.detect_adverse_selection(data)
        if is_adverse:
            # Widen spreads significantly during adverse selection
            # or temporarily withdraw from market
            return Signal(
                symbol=self.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.3,
                price=round(float(data["close"].iloc[-1]), 6),
                source_agent=self.name,
                source_strategy=self.name,
                reasoning="Market making paused: adverse selection detected",
                evidence={"adverse_selection": True},
                factors=["market_making", "adverse_selection"],
            )

        # Estimate volatility
        sigma = self.estimate_volatility(data)
        mid_price = float(data["close"].iloc[-1])

        # Compute optimal quotes
        bid, ask, bid_size, ask_size = self.compute_optimal_quotes(
            mid_price, self._current_inventory, sigma, self.T
        )

        # Fill probability
        bid_fill_prob = self.estimate_fill_probability(mid_price - bid, sigma)
        ask_fill_prob = self.estimate_fill_probability(ask - mid_price, sigma)

        # Determine primary action
        # If inventory is long-heavy, lean toward sell
        # If inventory is short-heavy, lean toward buy
        if self._current_inventory > self.max_inventory * 0.7:
            signal_type = SignalType.SELL
            confidence = 0.6 + 0.4 * (self._current_inventory / self.max_inventory)
        elif self._current_inventory < -self.max_inventory * 0.7:
            signal_type = SignalType.BUY
            confidence = 0.6 + 0.4 * abs(self._current_inventory / self.max_inventory)
        else:
            signal_type = SignalType.HOLD
            confidence = 0.5

        confidence = min(confidence, 1.0)

        return Signal(
            symbol=self.symbol,
            signal_type=signal_type,
            confidence=round(confidence, 4),
            price=round(mid_price, 6),
            stop_loss=round(mid_price * 0.98, 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=(
                f"MM quotes: bid={bid:.4f} x {bid_size:.2f}, ask={ask:.4f} x {ask_size:.2f}, "
                f"inventory={self._current_inventory}, sigma={sigma:.6f}"
            ),
            evidence={
                "bid_price": round(float(bid), 6),
                "ask_price": round(float(ask), 6),
                "bid_size": round(float(bid_size), 4),
                "ask_size": round(float(ask_size), 4),
                "bid_fill_prob": round(float(bid_fill_prob), 4),
                "ask_fill_prob": round(float(ask_fill_prob), 4),
                "inventory": self._current_inventory,
                "sigma": round(float(sigma), 6),
                "reservation_price": round(
                    float(self.compute_reservation_price(
                        mid_price, self._current_inventory, sigma, self.T
                    )), 6
                ),
                "half_spread": round(
                    float(self.compute_optimal_spread(sigma, self.T)), 6
                ),
            },
            factors=["market_making", "avellaneda_stoikov"],
        )
