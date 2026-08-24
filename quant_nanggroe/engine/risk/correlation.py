"""Asset Correlation Monitoring.

Monitors pairwise asset correlations to detect:
- Excessive correlation between positions (risk concentration)
- Correlation regime changes (market stress detection)
- Portfolio diversification effectiveness

Provides:
- Rolling correlation matrix
- Correlation regime detection
- Diversification score
- Stress correlation analysis
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchTrigger

logger = logging.getLogger(__name__)


@dataclass
class CorrelationAlert:
    """Alert for correlation anomaly."""

    pair: str
    current_correlation: float
    historical_avg: float
    z_score: float
    alert_type: str  # "high_correlation", "regime_change", "stress"


class CorrelationMonitor:
    """Asset Correlation Monitor.

    Tracks rolling correlations between assets and alerts when:
    - Pairwise correlation exceeds threshold
    - Correlation regime changes (e.g., decorrelation → high correlation)
    - Market stress is detected (everything becomes correlated)
    """

    # Correlated asset groups for correlation checks
    CORRELATED_GROUPS = [
        {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},
        {"USDJPY", "USDCHF", "USDCAD"},
        {"XAUUSD", "XAGUSD"},
        {"BTCUSDT", "ETHUSDT"},
        {"SPY", "QQQ", "IWM"},
    ]

    def __init__(
        self,
        lookback: int = 60,
        high_correlation_threshold: float = 0.7,
        stress_threshold: float = 0.8,
    ) -> None:
        self.lookback = lookback
        self.high_corr_threshold = high_correlation_threshold
        self.stress_threshold = stress_threshold
        self._history: List[pd.DataFrame] = []

    def is_correlated(self, symbol_a: str, symbol_b: str) -> bool:
        """Check if two symbols are in the same correlated group.

        Args:
            symbol_a: First symbol.
            symbol_b: Second symbol.

        Returns:
            True if symbols are known to be correlated.
        """
        for group in self.CORRELATED_GROUPS:
            if symbol_a.upper() in group and symbol_b.upper() in group:
                return True
        return False

    def count_correlated_positions(
        self,
        symbol: str,
        active_positions: List[str],
    ) -> int:
        """Count how many active positions are correlated with the given symbol.

        Args:
            symbol: Symbol to check.
            active_positions: List of currently held symbols.

        Returns:
            Number of correlated positions.
        """
        return sum(1 for p in active_positions if self.is_correlated(p, symbol))

    def compute_rolling_correlation(
        self,
        returns: pd.DataFrame,
        window: Optional[int] = None,
    ) -> pd.DataFrame:
        """Compute rolling correlation matrix.

        Args:
            returns: DataFrame of asset returns (columns = assets).
            window: Rolling window size (default: self.lookback).

        Returns:
            Rolling correlation matrix for the last window.
        """
        if window is None:
            window = self.lookback

        if len(returns) < window:
            return returns.corr()

        return returns.iloc[-window:].corr()

    def compute_diversification_score(
        self,
        returns: pd.DataFrame,
        weights: Optional[np.ndarray] = None,
    ) -> float:
        """Compute portfolio diversification score.

        Score is based on the ratio of weighted average volatility
        to portfolio volatility. Higher = more diversified.

        Args:
            returns: DataFrame of asset returns.
            weights: Portfolio weights (default: equal weight).

        Returns:
            Diversification score (0-1, higher is more diversified).
        """
        n = returns.shape[1]
        if n < 2:
            return 0.0

        if weights is None:
            weights = np.ones(n) / n

        vols = returns.std().values
        weighted_avg_vol = np.sum(weights * vols)

        cov = returns.cov().values
        port_vol = np.sqrt(max(weights @ cov @ weights, 0.0))

        # Max diversification ratio (theoretical, perfectly anticorrelated) = n.
        # Used both as the cap for the div-by-zero case and the normalization max.
        max_div = float(n)

        if weighted_avg_vol <= 0:
            return 0.0

        # Diversification ratio. When assets are anticorrelated, portfolio variance
        # collapses toward 0 (real diversification benefit) — that is MAXIMUM
        # diversification, not zero. Guard against the div-by-zero collapse that
        # previously returned 0.0 for both corr=1 and corr=-1 (degenerate output).
        if port_vol <= 1e-12:
            div_ratio = max_div  # perfect diversification → score 1.0
        else:
            div_ratio = weighted_avg_vol / port_vol

        # Normalize to 0-1 range.
        # Diversification ratio DR = Σ(wi·σi) / σp.
        #   No diversification (perfectly correlated): DR = 1 → score 0
        #   Uncorrelated, equal vol, 2 assets: DR = √2 → score ≈ 0.41
        #   Max diversification (perfectly anticorrelated): DR = n → score 1
        score = (div_ratio - 1.0) / (max_div - 1.0) if max_div > 1 else 0.0
        return float(np.clip(score, 0.0, 1.0))

    def detect_stress(
        self,
        returns: pd.DataFrame,
        window: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Detect market stress via correlation analysis.

        During stress, correlations tend to increase (everything falls together).
        This is measured as the average pairwise correlation.

        Args:
            returns: DataFrame of asset returns.
            window: Rolling window size.

        Returns:
            Dict with stress detection results.
        """
        # Accept DataFrame, dict-of-series, or dict-of-lists — coerce to DataFrame
        # so the stress path never crashes on a dict input.
        if isinstance(returns, dict):
            returns = pd.DataFrame(returns)
        if not isinstance(returns, pd.DataFrame):
            returns = pd.DataFrame(returns)

        corr = self.compute_rolling_correlation(returns, window)

        # Average off-diagonal correlation
        n = corr.shape[0]
        if n < 2:
            return {"stress_detected": False, "avg_correlation": 0.0, "stress_level": "NORMAL"}

        mask = ~np.eye(n, dtype=bool)
        avg_corr = float(corr.values[mask].mean())

        stress_detected = avg_corr > self.stress_threshold
        stress_level = "STRESS" if avg_corr > self.stress_threshold else (
            "ELEVATED" if avg_corr > self.high_corr_threshold else "NORMAL"
        )

        return {
            "stress_detected": stress_detected,
            "avg_correlation": round(avg_corr, 4),
            "stress_level": stress_level,
            "max_pairwise": round(float(corr.values[mask].max()), 4),
            "min_pairwise": round(float(corr.values[mask].min()), 4),
        }


class StrategyCorrelationMonitor:
    """Monitors pairwise strategy return correlations to detect rank collapse (herding).

    Tracks trailing returns for all registered strategies, computes pairwise
    Spearman rank correlations, and auto-activates the kill switch when the
    mean correlation exceeds the herding threshold.

    Parameters
    ----------
    kill_switch : KillSwitch, optional
        Kill switch instance to trigger on herding. If None, only logs warnings.
    window : int
        Trailing window size for return history (default 30).
    threshold : float
        Mean Spearman correlation threshold for herding detection (default 0.85).
    state_dir : str
        Directory for persisting correlation state as JSON (default "paper_state").
    """

    def __init__(
        self,
        kill_switch: Optional[KillSwitch] = None,
        window: int = 60,
        threshold: float = 0.85,
        state_dir: str = "paper_state",
        paper_mode: bool = False,
    ) -> None:
        self.kill_switch = kill_switch
        self.window = window
        self.threshold = threshold
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.paper_mode: bool = paper_mode

        # strategy_name -> deque of trailing returns (FIFO, maxlen=window)
        self._trailing_returns: Dict[str, deque[float]] = {}

        # One-shot flag: prevent repeated kill switch firings until reset
        self._fired: bool = False

        self.load_state(self.state_dir / "correlation_state.json")

    # ── Public API ─────────────────────────────────────────────────────────

    def update(self, strategy_name: str, returns: np.ndarray) -> None:
        """Feed latest returns for a strategy. Stores trailing window."""
        if strategy_name not in self._trailing_returns:
            self._trailing_returns[strategy_name] = deque(maxlen=self.window)

        for r in np.atleast_1d(returns):
            self._trailing_returns[strategy_name].append(float(r))

    def compute_correlations(self) -> Dict[str, Dict[str, float]]:
        """Pairwise Spearman rank correlations between all tracked strategies.

        Returns
        -------
        Dict[str, Dict[str, float]]
            Nested dict: {strategy_a: {strategy_b: correlation}}.
            Empty dict when fewer than 2 strategies are tracked.
        """
        if len(self._trailing_returns) < 2:
            return {}

        strategies = list(self._trailing_returns.keys())
        correlations: Dict[str, Dict[str, float]] = {}

        for i, s1 in enumerate(strategies):
            correlations[s1] = {}
            arr1 = np.array(list(self._trailing_returns[s1]))

            for s2 in strategies[i + 1:]:
                arr2 = np.array(list(self._trailing_returns[s2]))

                # Need at least 3 points for meaningful Spearman
                if len(arr1) < 3 or len(arr2) < 3:
                    continue

                n = min(len(arr1), len(arr2))
                try:
                    rho, _ = spearmanr(arr1[-n:], arr2[-n:])
                    val = round(float(rho), 4)
                    correlations[s1][s2] = val
                except Exception:
                    continue

        return correlations

    def check_and_act(self) -> Dict[str, Any]:
        """Check for herding and activate kill switch if threshold breached.

        Returns
        -------
        Dict
            Current status dictionary from ``get_status()``.
        """
        status = self.get_status()

        if status["num_strategies"] < 2:
            return status

        avg_corr = status["avg_correlation"]
        if avg_corr is None:
            return status

        if avg_corr > self.threshold:
            if self.paper_mode:
                # Paper mode observes but never acts on the live kill switch.
                logger.warning(
                    "Correlation herding detected in PAPER mode (avg=%.3f) "
                    "— kill switch suppressed", avg_corr,
                )
            elif self.kill_switch is not None and not self._fired:
                self.kill_switch.activate(
                    level=KillSwitchLevel.LEVEL_1,
                    trigger=KillSwitchTrigger.CORRELATION_HERDING,
                    reason=(
                        f"correlation_herding: Mean rank correlation "
                        f"{avg_corr:.3f} > threshold {self.threshold}"
                    ),
                    auto_activated=True,
                )
                self._fired = True
                logger.critical(
                    "Correlation herding detected: avg=%.3f, threshold=%.3f",
                    avg_corr, self.threshold,
                )
            elif self.kill_switch is None:
                logger.warning(
                    "Correlation herding detected (avg=%.3f) but no kill switch installed",
                    avg_corr,
                )

        self.save_state(self.state_dir / "correlation_state.json")
        return status

    def get_status(self) -> Dict[str, Any]:
        """Current correlation matrix summary, avg, max, disabled strategies.

        Returns
        -------
        Dict
            Keys: num_strategies, avg_correlation, max_correlation, matrix,
            threshold, kill_switch_fired, window.
        """
        corr = self.compute_correlations()
        num_strategies = len(self._trailing_returns)

        values = []
        for s1, pairs in corr.items():
            for s2, val in pairs.items():
                if s1 != s2:
                    values.append(val)

        avg_corr = float(np.mean(values)) if values else None
        max_corr = float(np.max(values)) if values else None

        return {
            "num_strategies": num_strategies,
            "avg_correlation": avg_corr,
            "max_correlation": max_corr,
            "matrix": corr,
            "threshold": self.threshold,
            "kill_switch_fired": self._fired,
            "window": self.window,
        }

    # ── Persistence ─────────────────────────────────────────────────────

    def load_state(self, path: Path) -> None:
        """Load persisted trailing returns from JSON file."""
        try:
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                for strategy, returns in data.get("trailing_returns", {}).items():
                    self._trailing_returns[strategy] = deque(
                        returns, maxlen=self.window,
                    )
                self._fired = data.get("kill_switch_fired", False)
                logger.info(
                    "Loaded correlation state for %d strategies",
                    len(self._trailing_returns),
                )
        except Exception as e:
            logger.warning("Failed to load correlation state: %s", e)

    def save_state(self, path: Path) -> None:
        """Persist trailing returns to JSON file."""
        try:
            data: Dict[str, Any] = {
                "trailing_returns": {
                    s: list(dq) for s, dq in self._trailing_returns.items()
                },
                "kill_switch_fired": self._fired,
                "window": self.window,
                "threshold": self.threshold,
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved correlation state to %s", path)
        except Exception as e:
            logger.warning("Failed to save correlation state: %s", e)
