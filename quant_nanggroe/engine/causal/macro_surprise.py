"""
Macro Surprise Index (MSI) — FRED-based economic surprise detection.

Computes standardized surprise deviations for key economic indicators:

    MSI_i = (Actual_i - Consensus_i) / sigma_historical(i)

Deviations above |1.5 sigma| mark significant expectation shocks that
trigger automatic bias revision.

References:
    - SSRN-3847291: "Quantifying News Sentiment and Geopolitical Risk
      in Systematic Macro Trading"
    - FRED API: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Default FRED series IDs for key economic indicators
DEFAULT_FRED_SERIES = {
    "CPI": "CPIAUCSL",            # Consumer Price Index
    "Core_CPI": "CPILFESL",       # Core CPI
    "PPI": "PPIACO",              # Producer Price Index
    "Unemployment": "UNRATE",      # Unemployment Rate
    "GDP": "GDP",                  # Gross Domestic Product
    "Industrial_Production": "INDPRO",  # Industrial Production
    "Retail_Sales": "RSXFS",       # Retail Sales
    "Housing_Starts": "HOUST",     # Housing Starts
    "Consumer_Sentiment": "UMCSENT",  # Consumer Sentiment
    "Nonfarm_Payrolls": "PAYEMS",  # Nonfarm Payrolls
}


class MacroSurpriseIndex:
    """
    Macro Surprise Index — detects expectation shocks from economic releases.

    Connects to FRED API to fetch actual economic indicator values and
    computes standardized surprise scores.

    Usage:
        msi = MacroSurpriseIndex()
        if msi.connected:
            surprises = msi.get_recent_surprises(threshold=1.5)
    """

    def __init__(
        self,
        fred_api_key: Optional[str] = None,
        series_map: Optional[Dict[str, str]] = None,
    ):
        """
        Args:
            fred_api_key: FRED API key. If None, reads from FRED_API_KEY env var.
            series_map: Dict mapping series names to FRED series IDs.
        """
        self._api_key = fred_api_key or os.environ.get("FRED_API_KEY")
        self._series_map = series_map or dict(DEFAULT_FRED_SERIES)
        self._connected = False
        self._client: Any = None

        if self._api_key:
            try:
                from fredapi import Fred
                self._client = Fred(api_key=self._api_key)
                self._connected = True
                logger.info(
                    "MSI connected to FRED (%d series)", len(self._series_map)
                )
            except ImportError:
                logger.warning(
                    "fredapi not installed. Install: pip install fredapi"
                )
            except Exception as e:
                logger.warning("FRED connection failed: %s", e)
        else:
            logger.info(
                "MSI in disconnected mode. Set FRED_API_KEY env var for live data."
            )

    @property
    def connected(self) -> bool:
        return self._connected

    def get_recent_surprises(
        self,
        threshold: float = 1.5,
        lookback_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Fetch recent economic indicators and compute surprise scores.

        Args:
            threshold: |MSI| threshold for significant surprise (default: 1.5 sigma).
            lookback_days: Lookback period for historical std calculation.

        Returns:
            Dict with:
                connected: True/False
                n_significant: Count of significant surprises
                events: Dict of event_name → {msi, direction, is_significant}
        """
        if not self._connected or self._client is None:
            return {
                "connected": False,
                "n_significant": 0,
                "events": {},
                "message": "FRED not connected",
            }

        events: Dict[str, Dict[str, Any]] = {}
        n_significant = 0

        for name, series_id in self._series_map.items():
            try:
                # Fetch recent data
                data = self._client.get_series(
                    series_id,
                    observation_start=(
                        datetime.now() - timedelta(days=lookback_days)
                    ).strftime("%Y-%m-%d"),
                )

                if data is None or len(data) < 10:
                    continue

                values = data.dropna().values
                if len(values) < 10:
                    continue

                # Compute MSI: (latest - mean) / std
                latest = values[-1]
                historical = values[:-1]
                mean = np.mean(historical)
                std = np.std(historical)

                if std == 0:
                    continue

                msi = float((latest - mean) / std)
                direction = "positive" if msi > 0 else "negative"
                is_significant = abs(msi) >= threshold

                if is_significant:
                    n_significant += 1

                events[name] = {
                    "msi": round(msi, 3),
                    "direction": direction,
                    "is_significant": is_significant,
                    "latest_value": float(latest),
                    "historical_mean": float(mean),
                    "historical_std": float(std),
                    "series_id": series_id,
                }

            except Exception as e:
                logger.debug("MSI fetch failed for %s: %s", name, e)
                events[name] = {"error": str(e)}

        return {
            "connected": True,
            "n_significant": n_significant,
            "events": events,
            "total_series": len(self._series_map),
            "threshold": threshold,
        }

    def calculate_msi(
        self,
        actual: float,
        consensus: float,
        hist_std: float,
    ) -> float:
        """
        Calculate a single MSI score from actual, consensus, and historical std.

        Args:
            actual: Released economic indicator value.
            consensus: Market consensus expectation.
            hist_std: Historical standard deviation of the indicator.

        Returns:
            Standardized surprise score. |MSI| > 1.5 = significant.
        """
        if hist_std == 0:
            return 0.0
        return float((actual - consensus) / hist_std)

    def get_connected_status(self) -> Dict[str, Any]:
        """Get FRED connection status and available series."""
        return {
            "connected": self._connected,
            "n_series": len(self._series_map),
            "series": list(self._series_map.keys()),
        }


__all__ = [
    "MacroSurpriseIndex",
    "DEFAULT_FRED_SERIES",
]
