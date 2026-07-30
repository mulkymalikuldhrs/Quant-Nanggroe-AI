"""Order Flow Risk Monitor — detects CVD/price divergence triggers.

When CVD diverges from price by >2 standard deviations over a 1-hour
window, the monitor classifies the regime as DISTRIBUTION and triggers
kill switch levels based on how many open positions are affected.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from quant_nanggroe.engine.risk.kill_switch import (
    KillSwitch,
    KillSwitchLevel,
    KillSwitchTrigger,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
STD_DEV_THRESHOLD: float = 2.0          # z-score threshold for divergence
WINDOW_MINUTES: int = 60                # look-back window
MIN_SAMPLES: int = 10                   # minimum data points before detection
LEVEL_1_POSITIONS: int = 2              # ≥2 positions in distribution → LEVEL_1
LEVEL_2_POSITIONS: int = 3              # ≥3 positions in distribution → LEVEL_2

DISTRIBUTION_REGIME: str = "distribution"
ACCUMULATION_REGIME: str = "accumulation"
NEUTRAL_REGIME: str = "neutral"


class OrderFlowRegime(str, Enum):
    """Regime classification based on CVD / price divergence."""
    DISTRIBUTION = DISTRIBUTION_REGIME
    ACCUMULATION = ACCUMULATION_REGIME
    NEUTRAL = NEUTRAL_REGIME


@staticmethod
def _zscore(values: List[float], x: float) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    if variance <= 0:
        return 0.0
    return (x - mean) / math.sqrt(variance)


class OrderFlowRiskMonitor:
    """Detects CVD/price divergence and triggers kill switch levels.

    Tracks a rolling window of CVD vs price delta observations per symbol.
    When the current z-score exceeds the threshold, the regime for that
    symbol is labelled DISTRIBUTION (or ACCUMULATION).

    Usage::

        monitor = OrderFlowRiskMonitor()
        monitor.feed("EURUSD", cvd_delta=0.5, price_delta=-0.1)

        trigger_level = monitor.evaluate(active_positions=["EURUSD", "GBPUSD"])
        if trigger_level is not None:
            ks.activate(level=trigger_level,
                        trigger=KillSwitchTrigger.ORDER_FLOW_DIVERGENCE,
                        reason="...")
    """

    def __init__(self) -> None:
        # symbol → deque of (timestamp, cvd_delta, price_delta)
        self._windows: Dict[str, deque] = {}
        # symbol → latest regime
        self._regimes: Dict[str, OrderFlowRegime] = {}

    def feed(
        self,
        symbol: str,
        cvd_delta: float,
        price_delta: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record one CVD / price delta observation.

        Parameters
        ----------
        symbol:
            Instrument symbol.
        cvd_delta:
            Cumulative Volume Delta change (positive = buying pressure).
        price_delta:
            Price change over the same period (positive = up).
        timestamp:
            Observation timestamp (defaults to now).
        """
        ts = timestamp or datetime.now(timezone.utc)
        window = self._windows.setdefault(symbol.upper(), deque())
        window.append((ts, cvd_delta, price_delta))
        self._prune(window)
        self._recompute_regime(symbol.upper())

    def _prune(self, window: deque) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
        while window and window[0][0] < cutoff:
            window.popleft()

    def _recompute_regime(self, symbol: str) -> None:
        window = self._windows.get(symbol)
        if window is None or len(window) < MIN_SAMPLES:
            self._regimes[symbol] = OrderFlowRegime.NEUTRAL
            return

        # Calculate CVD/price divergence z-score
        cvd_values = [w[1] for w in window]
        price_values = [w[2] for w in window]

        latest_cvd = cvd_values[-1]
        latest_price = price_values[-1]
        cvd_z = _zscore(cvd_values, latest_cvd)
        price_z = _zscore(price_values, latest_price)

        divergence = abs(cvd_z) + abs(price_z)

        if divergence > STD_DEV_THRESHOLD:
            # CVD dropping while price rising → distribution
            # CVD rising while price falling → accumulation
            if latest_cvd < 0 and latest_price > 0:
                self._regimes[symbol] = OrderFlowRegime.DISTRIBUTION
            elif latest_cvd > 0 and latest_price < 0:
                self._regimes[symbol] = OrderFlowRegime.ACCUMULATION
            elif abs(latest_cvd) > abs(latest_price):
                self._regimes[symbol] = OrderFlowRegime.DISTRIBUTION
            else:
                self._regimes[symbol] = OrderFlowRegime.ACCUMULATION
        else:
            self._regimes[symbol] = OrderFlowRegime.NEUTRAL

    def get_regime(self, symbol: str) -> OrderFlowRegime:
        """Return the current regime for a symbol."""
        return self._regimes.get(symbol.upper(), OrderFlowRegime.NEUTRAL)

    def evaluate(
        self,
        active_positions: List[str],
    ) -> Optional[KillSwitchLevel]:
        """Check all active positions for CVD/price divergence.

        Parameters
        ----------
        active_positions:
            List of symbol strings currently held.

        Returns
        -------
        KillSwitchLevel or None
            ``LEVEL_1`` if ≥2 positions show DISTRIBUTION (block new).
            ``LEVEL_2`` if ≥3 positions show DISTRIBUTION (close all).
            ``None`` if no trigger.
        """
        distribution_count = 0
        for sym in active_positions:
            regime = self.get_regime(sym)
            if regime == OrderFlowRegime.DISTRIBUTION:
                distribution_count += 1
                logger.debug("  %s → DISTRIBUTION regime", sym)

        if distribution_count >= LEVEL_2_POSITIONS:
            logger.critical(
                "Order flow divergence: %d/%d positions in DISTRIBUTION — LEVEL_2",
                distribution_count, len(active_positions),
            )
            return KillSwitchLevel.LEVEL_2

        if distribution_count >= LEVEL_1_POSITIONS:
            logger.warning(
                "Order flow divergence: %d/%d positions in DISTRIBUTION — LEVEL_1",
                distribution_count, len(active_positions),
            )
            return KillSwitchLevel.LEVEL_1

        return None

    def apply_kill_switch(
        self,
        active_positions: List[str],
        kill_switch: KillSwitch,
    ) -> None:
        """Evaluate and automatically trigger kill switch if needed.

        Safe to call on every pipeline cycle — only activates once.
        """
        if not kill_switch.can_trade():
            return
        level = self.evaluate(active_positions)
        if level is None:
            return
        if level == KillSwitchLevel.LEVEL_1:
            kill_switch.activate(
                level=KillSwitchLevel.LEVEL_1,
                reason=f"CVD/price divergence: ≥{LEVEL_1_POSITIONS} positions in DISTRIBUTION regime",
                trigger=KillSwitchTrigger.ORDER_FLOW_DIVERGENCE,
                auto_activated=True,
            )
        elif level in (KillSwitchLevel.LEVEL_2, KillSwitchLevel.LEVEL_3):
            kill_switch.activate(
                level=KillSwitchLevel.LEVEL_2,
                reason=f"CVD/price divergence: ≥{LEVEL_2_POSITIONS} positions in DISTRIBUTION regime",
                trigger=KillSwitchTrigger.ORDER_FLOW_DIVERGENCE,
                auto_activated=True,
            )

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "windows": {sym: len(q) for sym, q in self._windows.items()},
            "regimes": {sym: r.value for sym, r in self._regimes.items()},
        }
