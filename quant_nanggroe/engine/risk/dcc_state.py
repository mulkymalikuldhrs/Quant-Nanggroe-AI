"""
DCC State — Shared DCC-GARCH Singleton
=======================================
Provides a single, module-level DCCGARCH instance that all callers
(LiveEngine, RiskEnforcer, API endpoints, MacroContext, Dashboard)
share, so correlation and volatility estimates are computed once
per update cycle rather than redundantly.

Usage:
    from quant_nanggroe.engine.risk.dcc_state import DCCState
    state = DCCState()  # singleton
    state.update(returns_df)  # re-fit with new market data
    corr = state.correlation  # latest DCC correlation matrix
    vol = state.volatilities  # latest GARCH vol vector
    status = state.get_status()  # dict for API / dashboard
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Module-level singleton reference
_DCC_STATE_INSTANCE = None


def get_dcc_state() -> "DCCState":
    """Get or create the shared DCC-GARCH singleton."""
    global _DCC_STATE_INSTANCE
    if _DCC_STATE_INSTANCE is None:
        _DCC_STATE_INSTANCE = DCCState()
    return _DCC_STATE_INSTANCE


class DCCState:
    """
    Shared DCC-GARCH state with caching.

    Wraps DCCGARCH with:
        - Singleton pattern (module-level instance)
        - Last-update timestamp tracking
        - Return data caching (ring buffer)
        - Correlation matrix caching
        - Status dict for API/dashboard consumption
    """

    MAX_RETURN_ROWS = 500  # ring buffer size

    def __init__(self):
        self._dcc: Optional[Any] = None
        self._dcc_a: float = 0.05
        self._dcc_b: float = 0.90
        self._returns_buffer: Optional[pd.DataFrame] = None
        self._last_update: Optional[datetime] = None
        self._update_count: int = 0

        # Cache the latest status to avoid recomputing
        self._cached_status: Dict[str, Any] = {
            "fitted": False,
            "mean_corr": None,
            "mean_vol_pct": None,
            "n_assets": 0,
            "asset_names": [],
            "update_count": 0,
        }

        # Lazy-init DCCGARCH
        self._lazy_dcc()

    def _lazy_dcc(self) -> None:
        """Initialize the DCCGARCH instance if not yet created."""
        if self._dcc is not None:
            return
        try:
            from quant_nanggroe.engine.risk.dcc_garch import DCCGARCH
            self._dcc = DCCGARCH(
                dcc_a=self._dcc_a,
                dcc_b=self._dcc_b,
            )
            logger.info("DCCState: DCCGARCH instance created")
        except Exception as e:
            logger.warning("DCCState: DCCGARCH init failed: %s", e)

    # ── Properties ────────────────────────────────────────────────

    @property
    def correlation(self) -> np.ndarray:
        """Latest DCC correlation matrix (n x n) or empty."""
        if self._dcc is not None and self._dcc.fitted:
            return self._dcc.correlation
        return np.array([[]])

    @property
    def volatilities(self) -> np.ndarray:
        """Latest GARCH volatilities (n,) or empty."""
        if self._dcc is not None and self._dcc.fitted:
            return self._dcc.volatilities
        return np.array([])

    @property
    def asset_names(self) -> List[str]:
        if self._dcc is not None and self._dcc.fitted:
            return self._dcc.asset_names
        return []

    @property
    def fitted(self) -> bool:
        return self._dcc is not None and self._dcc.fitted

    @property
    def last_update(self) -> Optional[datetime]:
        return self._last_update

    @property
    def update_count(self) -> int:
        return self._update_count

    @property
    def returns_buffer(self) -> Optional[pd.DataFrame]:
        """Get the cached returns data."""
        return self._returns_buffer

    # ── Public API ────────────────────────────────────────────────

    def update(self, returns: pd.DataFrame) -> bool:
        """
        Re-fit DCC-GARCH with new returns data.

        Maintains a ring buffer of up to MAX_RETURN_ROWS rows.

        Args:
            returns: (n_days x n_assets) DataFrame of log returns.

        Returns:
            True if fit succeeded, False otherwise.
        """
        if returns is None or returns.empty:
            logger.debug("DCCState.update: empty returns")
            return False

        # Ring buffer: keep last MAX_RETURN_ROWS
        if self._returns_buffer is not None:
            combined = pd.concat(
                [self._returns_buffer, returns], ignore_index=True
            )
            if len(combined) > self.MAX_RETURN_ROWS:
                self._returns_buffer = combined.iloc[-self.MAX_RETURN_ROWS:].copy()
            else:
                self._returns_buffer = combined
        else:
            self._returns_buffer = returns.tail(self.MAX_RETURN_ROWS).copy()

        if self._dcc is None:
            self._lazy_dcc()
        if self._dcc is None:
            return False

        try:
            self._dcc.fit(self._returns_buffer)
            self._last_update = datetime.now()
            self._update_count += 1
            self._refresh_cached_status()
            logger.info(
                "DCCState updated: %d assets, mean vol=%.2f%%, mean corr=%.4f "
                "(update #%d)",
                self._cached_status["n_assets"],
                self._cached_status.get("mean_vol_pct", 0),
                self._cached_status.get("mean_corr", 0),
                self._update_count,
            )
            return True
        except Exception as e:
            logger.warning("DCCState update failed: %s", e)
            return False

    def append_returns(self, new_returns: pd.DataFrame) -> None:
        """
        Append new returns to the buffer without re-fitting.

        Use this for incremental data collection. Call update() to re-fit.
        """
        if new_returns is None or new_returns.empty:
            return
        if self._returns_buffer is not None:
            combined = pd.concat(
                [self._returns_buffer, new_returns], ignore_index=True
            )
            if len(combined) > self.MAX_RETURN_ROWS:
                self._returns_buffer = combined.iloc[-self.MAX_RETURN_ROWS:].copy()
            else:
                self._returns_buffer = combined
        else:
            self._returns_buffer = new_returns.tail(self.MAX_RETURN_ROWS).copy()

    def get_status(self) -> Dict[str, Any]:
        """
        Get full DCC-GARCH status dict for API/dashboard.

        Returns:
            Dict with fitted, mean_corr, mean_vol_pct, n_assets,
            asset_names, correlation_matrix (list), volatilities (list),
            last_update, update_count, dcc_a, dcc_b.
        """
        if self._dcc is None or not self._dcc.fitted:
            return dict(self._cached_status)

        status = dict(self._cached_status)
        status["correlation_matrix"] = self._dcc.correlation.tolist()
        status["volatilities"] = self._dcc.volatilities.tolist()
        status["last_update"] = (
            self._last_update.isoformat() if self._last_update else None
        )
        status["dcc_a"] = self._dcc_a
        status["dcc_b"] = self._dcc_b
        return status

    def get_correlation_matrix(self) -> List[List[float]]:
        """Get the full correlation matrix as nested lists (for JSON)."""
        return self.correlation.tolist() if self.correlation.size > 1 else []

    def get_volatilities(self) -> List[float]:
        """Get the volatility vector as a list."""
        return self.volatilities.tolist() if self.volatilities.size > 0 else []

    def get_pair_correlation(self, asset_i: str, asset_j: str) -> Optional[float]:
        """Get correlation between two specific assets."""
        names = self.asset_names
        if not names or asset_i not in names or asset_j not in names:
            return None
        i, j = names.index(asset_i), names.index(asset_j)
        corr = self.correlation
        if corr.size > 1:
            return float(corr[i, j])
        return None

    def kelly_weights(self, expected_returns: np.ndarray) -> np.ndarray:
        """
        Get Volatility-Regulated Kelly weights from current DCC state.

        Args:
            expected_returns: Array of expected returns for each asset.

        Returns:
            Array of portfolio weights.
        """
        if self._dcc is None or not self._dcc.fitted:
            return np.array([])
        return self._dcc.kelly_weights(expected_returns=expected_returns)

    def reset(self) -> None:
        """Clear all state — forces re-init on next update."""
        self._dcc = None
        self._returns_buffer = None
        self._last_update = None
        self._update_count = 0
        self._cached_status = {
            "fitted": False,
            "mean_corr": None,
            "mean_vol_pct": None,
            "n_assets": 0,
            "asset_names": [],
            "update_count": 0,
        }
        logger.info("DCCState reset")

    # ── Internal ──────────────────────────────────────────────────

    def _refresh_cached_status(self) -> None:
        """Recompute cached summary stats from current DCC state."""
        if self._dcc is None or not self._dcc.fitted:
            return

        corr = self._dcc.correlation
        vols = self._dcc.volatilities

        if corr.size > 1:
            n = corr.shape[0]
            upper_tri = corr[np.triu_indices(n, k=1)]
            mean_corr = float(np.mean(upper_tri)) if len(upper_tri) > 0 else 0.0
        else:
            mean_corr = None

        self._cached_status = {
            "fitted": True,
            "mean_corr": mean_corr,
            "mean_vol_pct": float(np.mean(vols) * 100) if vols.size > 0 else None,
            "n_assets": len(self._dcc.asset_names),
            "asset_names": list(self._dcc.asset_names),
            "update_count": self._update_count,
        }


__all__ = [
    "DCCState",
    "get_dcc_state",
]
