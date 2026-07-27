"""
MacroSurpriseIndex (MSI) — Standardized Surprise Deviation Calculation.

Computes the Macro Surprise Index for QNA's tracked economic indicators
using FRED API historical data.

Formula (from Riset_QNA.md §3.A.2):
    MSI_i = (Actual_i - Consensus_i) / sigma_historical(i)

Where:
  - Actual_i: Latest released value for indicator i
  - Consensus_i: Estimate (approximated from rolling mean or MA)
  - sigma_historical(i): Historical standard deviation (rolling window)

When |MSI| > 1.5:
  - Significant surprise → triggers automatic bias revision in Causal Engine

Since FRED doesn't provide consensus survey data directly, this module
uses a statistical approximation: the "surprise" is computed as the
latest value's deviation from its recent historical trend, standardized
by historical volatility. For exact consensus data, integrate with a
dedicated economic calendar API (e.g., ForexFactory, Investing.com).

Usage:
    from quant_nanggroe.engine.macro import MacroSurpriseIndex

    msi = MacroSurpriseIndex(api_key="YOUR_FRED_API_KEY")
    result = msi.evaluate_all()
    # Returns: {"INFLATION_SURPRISE": {"msi": 2.1, "direction": "hot", ...}, ...}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.macro.economic_calendar import (
    EconomicCalendarProvider,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  MSI Result schema
# ══════════════════════════════════════════════════════════════════════


@dataclass
class MSIResult:
    """Result of a Macro Surprise Index evaluation for one indicator.

    Attributes:
        indicator_name: Human-readable name.
        fred_series_id: FRED series ID.
        msi_score: Computed MSI z-score.
        latest_value: Most recent data point.
        rolling_mean: Rolling mean approximation of "consensus".
        rolling_std: Rolling standard deviation.
        n_observations: Number of historical observations used.
        direction: 'hot' (positive surprise), 'cold' (negative), or 'neutral'.
        is_significant: True if |msi_score| >= 1.5.
        qna_event_type: The QNA event type this maps to.
        timestamp: When this evaluation was run.
        error: Error message if computation failed.
    """

    indicator_name: str = ""
    fred_series_id: str = ""
    msi_score: float = 0.0
    latest_value: float = 0.0
    rolling_mean: float = 0.0
    rolling_std: float = 0.0
    n_observations: int = 0
    direction: str = "neutral"  # 'hot', 'cold', or 'neutral'
    is_significant: bool = False
    qna_event_type: str = ""
    timestamp: str = ""
    error: str = ""


# ══════════════════════════════════════════════════════════════════════
#  Economic indicator → MSI config
# ══════════════════════════════════════════════════════════════════════

# Key economic indicators with their FRED series IDs and MSI computation params.
# Maps directly to the QNA event types used in the causal engine.

ECONOMIC_INDICATORS: dict[str, dict[str, Any]] = {
    # Inflation
    "CPI YoY": {
        "fred_id": "CPIAUCSL",
        "window": 12,  # 12 months for rolling std
        "diff": "pct_change",  # Use YoY % change
        "qna_event": "INFLATION_SURPRISE",
    },
    "Core CPI YoY": {
        "fred_id": "CPILFESL",
        "window": 12,
        "diff": "pct_change",
        "qna_event": "INFLATION_SURPRISE",
    },
    "PPI YoY": {
        "fred_id": "PPIACO",
        "window": 12,
        "diff": "pct_change",
        "qna_event": "INFLATION_SURPRISE",
    },
    # Employment
    "Nonfarm Payrolls": {
        "fred_id": "PAYEMS",
        "window": 12,
        "diff": "diff",  # Month-over-month change
        "qna_event": "EMPLOYMENT_SURPRISE",
    },
    "Unemployment Rate": {
        "fred_id": "UNRATE",
        "window": 12,
        "diff": "level",  # Use level (already a %)
        "qna_event": "EMPLOYMENT_SURPRISE",
    },
    "Initial Jobless Claims": {
        "fred_id": "ICSA",
        "window": 52,  # 52 weeks for weekly data
        "diff": "diff",
        "qna_event": "EMPLOYMENT_SURPRISE",
    },
    # Growth
    "GDP QoQ": {
        "fred_id": "GDPC1",
        "window": 8,  # 8 quarters (2 years)
        "diff": "pct_change",
        "qna_event": "GROWTH_SURPRISE",
    },
    "Industrial Production": {
        "fred_id": "INDPRO",
        "window": 12,
        "diff": "pct_change",
        "qna_event": "GROWTH_SURPRISE",
    },
    # Consumption
    "Retail Sales": {
        "fred_id": "RSAFS",
        "window": 12,
        "diff": "pct_change",
        "qna_event": "CONSUMPTION_SURPRISE",
    },
    "Consumer Confidence": {
        "fred_id": "UMCSENT",
        "window": 12,
        "diff": "level",  # Use level (index)
        "qna_event": "RISK_ON_SENTIMENT",
    },
    # Monetary
    "Fed Funds Rate": {
        "fred_id": "FEDFUNDS",
        "window": 12,
        "diff": "level",
        "qna_event": "CENTRAL_BANK_HAWKISH",
    },
    # Liquidity
    "M2 Money Supply": {
        "fred_id": "M2SL",
        "window": 12,
        "diff": "pct_change",
        "qna_event": "LIQUIDITY_SURPRISE",
    },
}


# ══════════════════════════════════════════════════════════════════════
#  MacroSurpriseIndex
# ══════════════════════════════════════════════════════════════════════


class MacroSurpriseIndex:
    """Macro Surprise Index engine — FRED-powered standardized surprise scores.

    Fetches historical economic data from FRED, computes rolling z-scores
    to quantify how surprising the latest release is relative to recent
    history, and maps results to QNA event types for causal bias evaluation.

    The MSI is a key input to FASE 1 of the QNA master pipeline:
      Causal & Macro Surprise Engine → Macro Surprise Index

    Formula:
        MSI_i = (Actual_i - Consensus_i) / sigma_historical(i)

    Where Consensus_i is approximated as the rolling mean of recent values.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        surprise_threshold: float = 1.5,
        indicators: Optional[dict[str, dict[str, Any]]] = None,
        calendar_provider: Optional[EconomicCalendarProvider] = None,
    ):
        """
        Args:
            api_key: FRED API key. If None, reads from FRED_API_KEY env var.
            surprise_threshold: |MSI| threshold for significance (default: 1.5).
            indicators: Custom indicator config (default: ECONOMIC_INDICATORS).
            calendar_provider: Optional EconomicCalendarProvider instance.
        """
        self.surprise_threshold = surprise_threshold
        self._indicators = indicators or ECONOMIC_INDICATORS
        self._calendar = calendar_provider or EconomicCalendarProvider()
        self._fred = None
        self._api_key = api_key
        self._results: dict[str, MSIResult] = {}
        self._last_eval_time: Optional[datetime] = None

    # ── FRED client (lazy init) ────────────────────────────────

    @property
    def fred(self):
        """Lazy-initialized FRED API client."""
        if self._fred is None:
            try:
                from fredapi import Fred

                if self._api_key:
                    self._fred = Fred(api_key=self._api_key)
                else:
                    self._fred = Fred()
                # Test connection
                self._fred.get_series("GDP", count=1)
                logger.info("FRED API connected successfully")
            except Exception as e:
                logger.warning("FRED API connection failed: %s", e)
                self._fred = None
        return self._fred

    @property
    def is_connected(self) -> bool:
        """True if FRED API is available."""
        return self.fred is not None

    # ── Core MSI computation ───────────────────────────────────

    def evaluate(
        self,
        indicator_name: str,
        force_refresh: bool = False,
    ) -> MSIResult:
        """Compute MSI for a single economic indicator.

        Args:
            indicator_name: Key from ECONOMIC_INDICATORS (e.g. 'CPI YoY').
            force_refresh: Bypass cached result.

        Returns:
            MSIResult with z-score, direction, and significance flag.
        """
        # Check cache
        if not force_refresh and indicator_name in self._results:
            return self._results[indicator_name]

        config = self._indicators.get(indicator_name)
        if config is None:
            return MSIResult(
                indicator_name=indicator_name,
                error=f"Unknown indicator: '{indicator_name}'",
            )

        fred_id = config["fred_id"]
        window = config["window"]
        diff_method = config["diff"]
        qna_event = config.get("qna_event", "")

        if not self.is_connected:
            return MSIResult(
                indicator_name=indicator_name,
                fred_series_id=fred_id,
                error="FRED API not connected. Set FRED_API_KEY env var.",
                qna_event_type=qna_event,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        try:
            # Fetch historical data from FRED
            series: pd.Series = self.fred.get_series(fred_id)
            if series.empty or len(series) < window + 2:
                return MSIResult(
                    indicator_name=indicator_name,
                    fred_series_id=fred_id,
                    error=f"Insufficient data: {len(series)} obs (need {window + 2})",
                    qna_event_type=qna_event,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # Apply differencing method
            if diff_method == "pct_change":
                processed = series.pct_change().dropna()
            elif diff_method == "diff":
                processed = series.diff().dropna()
            else:  # level
                processed = series

            if len(processed) < window + 1:
                return MSIResult(
                    indicator_name=indicator_name,
                    fred_series_id=fred_id,
                    error=f"Insufficient processed data: {len(processed)} obs",
                    qna_event_type=qna_event,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            # Rolling statistics
            try:
                rolling_mean = processed.rolling(window=window, min_periods=window).mean()
                rolling_std = processed.rolling(window=window, min_periods=window).std()
            except Exception as e:
                return MSIResult(
                    indicator_name=indicator_name,
                    fred_series_id=fred_id,
                    error=f"Rolling stats failed: {e}",
                    qna_event_type=qna_event,
                )

            # Latest values
            latest_value = float(processed.iloc[-1])
            latest_mean = float(rolling_mean.iloc[-1])
            latest_std = float(rolling_std.iloc[-1])

            if latest_std == 0 or np.isnan(latest_std):
                return MSIResult(
                    indicator_name=indicator_name,
                    fred_series_id=fred_id,
                    latest_value=latest_value,
                    rolling_mean=latest_mean,
                    rolling_std=latest_std,
                    n_observations=len(processed),
                    error="Zero or NaN rolling std",
                    qna_event_type=qna_event,
                )

            # MSI = (Actual - Consensus) / sigma
            msi = (latest_value - latest_mean) / latest_std

            # Direction
            if msi > 0.5:
                direction = "hot"
            elif msi < -0.5:
                direction = "cold"
            else:
                direction = "neutral"

            result = MSIResult(
                indicator_name=indicator_name,
                fred_series_id=fred_id,
                msi_score=round(msi, 4),
                latest_value=round(latest_value, 4),
                rolling_mean=round(latest_mean, 4),
                rolling_std=round(latest_std, 4),
                n_observations=len(processed),
                direction=direction,
                is_significant=abs(msi) >= self.surprise_threshold,
                qna_event_type=qna_event,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            # Cache
            self._results[indicator_name] = result
            return result

        except Exception as e:
            logger.warning("MSI eval failed for %s: %s", indicator_name, e)
            return MSIResult(
                indicator_name=indicator_name,
                fred_series_id=fred_id,
                error=str(e),
                qna_event_type=qna_event,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def evaluate_all(
        self, force_refresh: bool = False
    ) -> dict[str, MSIResult]:
        """Compute MSI for ALL tracked economic indicators.

        Args:
            force_refresh: Bypass cached results.

        Returns:
            Dict of indicator_name -> MSIResult.
        """
        results: dict[str, MSIResult] = {}
        for name in self._indicators:
            result = self.evaluate(name, force_refresh=force_refresh)
            results[name] = result

        self._last_eval_time = datetime.now(timezone.utc)
        n_significant = sum(1 for r in results.values() if r.is_significant)
        n_errors = sum(1 for r in results.values() if r.error)
        logger.info(
            "MSI evaluated: %d indicators (%d significant, %d errors)",
            len(results), n_significant, n_errors,
        )
        return results

    # ── Aggregated signals for QNA ──────────────────────────────

    def get_event_signals(self) -> dict[str, dict[str, Any]]:
        """Aggregate MSI results by QNA event type.

        Returns:
            Dict of qna_event_type -> aggregated MSI signal dict.
        """
        aggregated: dict[str, dict[str, Any]] = {}

        for name, result in self._results.items():
            if not result.qna_event_type:
                continue

            event = result.qna_event_type
            if event not in aggregated:
                aggregated[event] = {
                    "event_type": event,
                    "msi_scores": [],
                    "indicators": [],
                    "max_abs_msi": 0.0,
                    "avg_msi": 0.0,
                    "is_significant": False,
                    "bias_direction": 0,  # +1 for hot (bullish for some), -1 for cold
                    "n_signals": 0,
                }

            agg = aggregated[event]
            agg["msi_scores"].append(result.msi_score)
            agg["indicators"].append({
                "name": result.indicator_name,
                "msi": result.msi_score,
                "direction": result.direction,
                "significant": result.is_significant,
            })
            agg["n_signals"] += 1

            if abs(result.msi_score) > agg["max_abs_msi"]:
                agg["max_abs_msi"] = abs(result.msi_score)

        # Compute averages and significance
        for event, agg in aggregated.items():
            if agg["msi_scores"]:
                agg["avg_msi"] = round(float(np.mean(agg["msi_scores"])), 4)
            agg["is_significant"] = agg["max_abs_msi"] >= self.surprise_threshold
            # Bias direction: positive MSI = higher-than-expected (hot)
            agg["bias_direction"] = 1 if agg["avg_msi"] > 0.5 else (
                -1 if agg["avg_msi"] < -0.5 else 0
            )

        return aggregated

    def get_summary(self) -> dict[str, Any]:
        """Get an overall MSI landscape summary.

        Returns:
            Dict with event signals, significant surprises count, timestamp.
        """
        event_signals = self.get_event_signals()
        n_significant = sum(
            1 for e in event_signals.values() if e["is_significant"]
        )

        return {
            "n_indicators": len(self._results),
            "n_events": len(event_signals),
            "n_significant": n_significant,
            "events": event_signals,
            "threshold": self.surprise_threshold,
            "last_eval": str(self._last_eval_time) if self._last_eval_time else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Cache management ───────────────────────────────────────

    def clear_cache(self) -> None:
        """Clear cached MSI results."""
        self._results.clear()
        self._last_eval_time = None
        logger.info("MSI cache cleared")
