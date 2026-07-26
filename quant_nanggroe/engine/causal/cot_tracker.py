"""
COT Tracker — CFTC Commitment of Traders institutional positioning analysis.

Tracks Commercial Hedgers (Smart Money), Non-Commercial (Managed Money/Hedge Funds),
and Non-Reportable (Retail) positions to detect crowded trades and potential reversals.

References:
    - CFTC Commitments of Traders reports
    - cot_reports Python library (github.com/NDelventhal/cot_reports)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default COT contract codes for key futures
# Format: {asset_name: (CFTC_market_name, legacy_fut_code)}
DEFAULT_COT_CONTRACTS = {
    "GC": ("GOLD", "088691"),         # Gold COMEX
    "SI": ("SILVER", "084691"),       # Silver COMEX
    "ES": ("S&P 500", "13874"),       # S&P 500 CME
    "NQ": ("NASDAQ 100", "20974"),    # Nasdaq 100 CME
    "YM": ("DJIA", "12460"),          # Dow Jones CME
    "CL": ("WTI CRUDE OIL", "06765"), # Crude Oil NYMEX
    "NG": ("NATURAL GAS", "02365"),   # Natural Gas NYMEX
    "6E": ("EURO FX", "09974"),       # EUR/USD CME
    "6J": ("JAPANESE YEN", "09774"),  # USD/JPY CME
    "6B": ("BRITISH POUND", "09674"), # GBP/USD CME
    "6A": ("AUSTRALIAN DOLLAR", "23274"), # AUD/USD CME
    "ZC": ("CORN", "00260"),          # Corn CBOT
    "ZW": ("WHEAT", "00160"),         # Wheat CBOT
    "ZS": ("SOYBEANS", "00560"),      # Soybeans CBOT
}


class COTTracker:
    """
    CFTC Commitment of Traders data tracker.

    Fetches weekly COT data and computes positioning percentiles,
    extreme signals, and crowding metrics.

    Usage:
        cot = COTTracker()
        data = cot.fetch_recent()  # Returns dict of asset → positioning stats
    """

    def __init__(
        self,
        contracts: Optional[Dict[str, Tuple[str, str]]] = None,
    ):
        self._contracts = contracts or dict(DEFAULT_COT_CONTRACTS)
        self._data: Dict[str, pd.DataFrame] = {}
        self._last_fetch: Optional[datetime] = None
        self._cot_module = None

        # Attempt lazy import of cot_reports
        try:
            import cot_reports as _cot
            self._cot_module = _cot
            logger.info("COT module loaded (%d contracts)", len(self._contracts))
        except ImportError:
            logger.warning(
                "cot_reports not installed. Install: pip install cot_reports"
            )

    @property
    def has_data(self) -> bool:
        return len(self._data) > 0

    @property
    def last_fetch(self) -> Optional[datetime]:
        return self._last_fetch

    def fetch_all(self, year: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Fetch COT data for all tracked contracts.

        Args:
            year: Year to fetch (default: current year).

        Returns:
            Dict of {asset_name: DataFrame with COT data}.
        """
        if self._cot_module is None:
            logger.warning("cot_reports not available — cannot fetch COT data")
            return {}

        year = year or datetime.now().year
        results: Dict[str, pd.DataFrame] = {}

        for name, (market_name, fut_code) in self._contracts.items():
            try:
                df = self._cot_module.cot_year(
                    year=year,
                    report_type="legacy_fut",
                    contract_code=fut_code,
                )
                if df is not None and not df.empty:
                    results[name] = df
            except Exception as e:
                logger.debug("COT fetch failed for %s: %s", name, e)

        self._data = results
        self._last_fetch = datetime.now()
        logger.info(
            "COT fetch complete: %d/%d contracts",
            len(results),
            len(self._contracts),
        )
        return results

    def get_positioning_percentile(
        self,
        asset_name: str,
        lookback: int = 52,
    ) -> Dict[str, Any]:
        """
        Compute current positioning percentile for an asset.

        Args:
            asset_name: Asset key (e.g. "GC" for gold).
            lookback: Number of weeks for historical percentile (default: 52).

        Returns:
            Dict with percentiles for commercial, non-commercial, non-reportable.
        """
        if asset_name not in self._data:
            return {"error": f"No data for {asset_name}"}

        df = self._data[asset_name]
        if len(df) < 10:
            return {"error": f"Insufficient data ({len(df)} rows)"}

        recent = df.tail(lookback) if len(df) > lookback else df

        result: Dict[str, Any] = {
            "asset": asset_name,
            "n_weeks": len(recent),
            "last_updated": str(self._last_fetch),
        }

        # Non-Commercial (Speculators / Hedge Funds)
        for col, key in [
            ("NonComm_Long", "noncomm_long"),
            ("NonComm_Short", "noncomm_short"),
            ("NonComm_Net", "noncomm_net"),
        ]:
            if col in recent.columns:
                val = recent[col].iloc[-1]
                hist = recent[col].dropna().values
                if len(hist) > 0:
                    pct = np.sum(hist <= val) / len(hist) * 100
                    result[key] = {
                        "value": int(val),
                        "percentile": round(float(pct), 1),
                    }

        # Commercial (Hedgers / Smart Money)
        for col, key in [
            ("Comm_Long", "comm_long"),
            ("Comm_Short", "comm_short"),
        ]:
            if col in recent.columns:
                val = recent[col].iloc[-1]
                hist = recent[col].dropna().values
                if len(hist) > 0:
                    pct = np.sum(hist <= val) / len(hist) * 100
                    result[key] = {
                        "value": int(val),
                        "percentile": round(float(pct), 1),
                    }

        # Non-Reportable (Retail)
        for col, key in [
            ("NonRep_Long", "retail_long"),
            ("NonRep_Short", "retail_short"),
        ]:
            if col in recent.columns:
                val = recent[col].iloc[-1]
                hist = recent[col].dropna().values
                if len(hist) > 0:
                    pct = np.sum(hist <= val) / len(hist) * 100
                    result[key] = {
                        "value": int(val),
                        "percentile": round(float(pct), 1),
                    }

        return result

    def detect_extreme_positioning(
        self,
        threshold: float = 90.0,
    ) -> Dict[str, str]:
        """
        Detect assets with extreme positioning.

        Args:
            threshold: Percentile threshold for "extreme" (default: 90%).

        Returns:
            Dict of {asset_name: signal} where signal is:
                EXTREME_LONG_OVERBOUGHT
                EXTREME_SHORT_OVERSOLD
                BALANCED
        """
        signals: Dict[str, str] = {}

        for asset_name in self._data:
            percentile_data = self.get_positioning_percentile(asset_name)
            if "error" in percentile_data:
                continue

            net = percentile_data.get("noncomm_net", {})
            pct = net.get("percentile", 50.0)

            if pct >= threshold:
                signals[asset_name] = "EXTREME_LONG_OVERBOUGHT"
            elif pct <= (100 - threshold):
                signals[asset_name] = "EXTREME_SHORT_OVERSOLD"
            else:
                signals[asset_name] = "BALANCED"

        return signals


class COTAnalyzer:
    """
    High-level COT analysis — generates actionable trading signals from COT data.

    Wraps COTTracker with trading logic to produce hedge fund-grade signals.
    """

    def __init__(
        self,
        cot_tracker: Optional[COTTracker] = None,
        extreme_threshold: float = 90.0,
    ):
        self._tracker = cot_tracker or COTTracker()
        self.extreme_threshold = extreme_threshold

    def analyze(
        self,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run full COT analysis and generate trading signal.

        Returns:
            Dict with signal, grade, extreme assets, and positioning details.
        """
        self._tracker.fetch_all(year=year)

        if not self._tracker.has_data:
            return {
                "signal": "NO_DATA",
                "grade": "D",
                "action": "hold",
                "message": "No COT data available",
            }

        extremes = self._tracker.detect_extreme_positioning(
            threshold=self.extreme_threshold
        )

        n_extreme_long = sum(
            1 for v in extremes.values() if v == "EXTREME_LONG_OVERBOUGHT"
        )
        n_extreme_short = sum(
            1 for v in extremes.values() if v == "EXTREME_SHORT_OVERSOLD"
        )
        n_balanced = sum(1 for v in extremes.values() if v == "BALANCED")

        # Generate signal
        if n_extreme_long > n_extreme_short * 2 and n_extreme_long >= 2:
            signal = "CAUTION_CROWDED_LONG"
            grade = "C"
            action = "reduce_long_increase_short"
        elif n_extreme_short > n_extreme_long * 2 and n_extreme_short >= 2:
            signal = "CAUTION_CROWDED_SHORT"
            grade = "C"
            action = "reduce_short_increase_long"
        elif n_balanced >= len(extremes) * 0.6:
            signal = "NEUTRAL"
            grade = "B"
            action = "follow_trend"
        else:
            signal = "MIXED"
            grade = "B"
            action = "selective"

        return {
            "signal": signal,
            "grade": grade,
            "action": action,
            "n_extreme_long": n_extreme_long,
            "n_extreme_short": n_extreme_short,
            "n_balanced": n_balanced,
            "total_tracked": len(extremes),
            "extreme_assets": extremes,
            "symbol": ",".join(
                k for k, v in extremes.items() if v != "BALANCED"
            ) or "all_balanced",
        }


__all__ = [
    "COTTracker",
    "COTAnalyzer",
    "DEFAULT_COT_CONTRACTS",
]
