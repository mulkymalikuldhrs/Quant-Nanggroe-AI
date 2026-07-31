"""
SMT Divergence Detector — Smart Money Technique divergence detection.

Extends the structural Higher-High / Lower-High check on top of the existing
cointegration-based model in ``engine/intermarket/cointegration_smt.py``:

  * Both correlated assets make a higher high → aligned move.
  * One makes a higher high while the other makes a lower high → divergence
    → fake breakout → NO TRADE or REDUCE bias.
  * Both make lower highs → typically aligned downside move.

Pairs monitored:
  - GC1! / SI1! (gold / silver)
  - NQ1! / ES1! (nasdaq / sp500)
  - BTC1! / ETH1! (crypto)
  - DXY / 6E1! (dollar index / euro)

Output contract:
    {
        "divergence_detected": bool,
        "pairs_affected": [str, ...],
        "confidence": float,
        "recommendation": str,
        "details": {pair_key: { ... }}
    }

References:
  - Bennett et al. (2022), arXiv:2201.08283 — Lead-lag detection.
  - Existing cointegration detector: ``engine/intermarket/cointegration_smt.py``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Symbolic monitored pairs with short display names for reporting.
MONITORED_PAIRS: list[tuple[str, str, str]] = [
    ("GC1!", "SI1!", "Gold/Silver"),
    ("NQ1!", "ES1!", "Nasdaq/S&P500"),
    ("BTC1!", "ETH1!", "BTC/ETH"),
    ("DXY", "6E1!", "DXY/EUR"),
]


@dataclass
class PairDivergenceDetail:
    """Structural SMT state for a single pair."""

    pair: str = ""
    asset_a: str = ""
    asset_b: str = ""
    aligned: bool = False
    divergence: bool = False
    a_higher_high: bool = False
    b_higher_high: bool = False
    a_lower_high: bool = False
    b_lower_high: bool = False
    confidence: float = 0.0
    recommendation: str = "HOLD"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        return {
            "pair": self.pair,
            "asset_a": self.asset_a,
            "asset_b": self.asset_b,
            "aligned": self.aligned,
            "divergence": self.divergence,
            "a_higher_high": self.a_higher_high,
            "b_higher_high": self.b_higher_high,
            "a_lower_high": self.a_lower_high,
            "b_lower_high": self.b_lower_high,
            "confidence": round(self.confidence, 4),
            "recommendation": self.recommendation,
            "extra": self.extra,
        }


@dataclass
class SMTDivergenceReport:
    """Top-level SMT divergence evaluation across all monitored pairs."""

    divergence_detected: bool = False
    pairs_affected: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommendation: str = "HOLD"
    details: dict[str, PairDivergenceDetail] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "divergence_detected": self.divergence_detected,
            "pairs_affected": list(self.pairs_affected),
            "confidence": round(self.confidence, 4),
            "recommendation": self.recommendation,
            "details": {k: v.to_dict() for k, v in self.details.items()},
        }


class SMTDivergenceDetector:
    """Smart Money Technique divergence detector.

    Detects fake breakouts by comparing Higher High / Lower High structure
    between correlated pairs. This is intentionally coupled with the
    existing cointegration model in ``engine/intermarket/cointegration_smt.py``
    by sharing pair definitions and providing a combined analysis hook.
    """

    def __init__(
        self,
        lookback: int = 3,
        confidence_threshold: float = 0.5,
        pairs: Optional[list[tuple[str, str, str]]] = None,
    ) -> None:
        """Initialize the SMT divergence detector.

        Args:
            lookback: Number of recent bars used to evaluate HH/LH.
            confidence_threshold: Minimum confidence to upgrade REDUCE → NO TRADE.
            pairs: Optional custom pair list of ``(asset_a, asset_b, label)``.
        """
        self.lookback = lookback
        self.confidence_threshold = confidence_threshold
        self._pairs = pairs or list(MONITORED_PAIRS)

    @staticmethod
    def _is_higher_high(series: pd.Series, lookback: int) -> bool:
        if len(series) < lookback + 1:
            return False
        return bool(series.iloc[-1] > series.iloc[-lookback:-1].max())

    @staticmethod
    def _is_lower_high(series: pd.Series, lookback: int) -> bool:
        if len(series) < lookback + 1:
            return False
        return bool(series.iloc[-1] < series.iloc[-lookback:-1].max())

    # ----------------------------------------------------------------
    # Core structural divergence check
    # ----------------------------------------------------------------

    def _analyze_pair(
        self,
        name_a: str,
        name_b: str,
        label: str,
        data: pd.DataFrame,
    ) -> PairDivergenceDetail:
        series_a = data[name_a].dropna()
        series_b = data[name_b].dropna()

        a_hh = self._is_higher_high(series_a, self.lookback)
        b_hh = self._is_higher_high(series_b, self.lookback)
        a_lh = self._is_lower_high(series_a, self.lookback)
        b_lh = self._is_lower_high(series_b, self.lookback)

        aligned = (a_hh and b_hh) or (a_lh and b_lh)
        divergence = (a_hh and b_lh) or (a_lh and b_hh)

        confidence = 0.0
        recommendation = "HOLD"
        if divergence:
            # Stronger confidence when both indicators point opposite directions.
            confidence = 0.8 if (a_hh or b_hh) else 0.6
            recommendation = "NO TRADE"
            if confidence < self.confidence_threshold:
                recommendation = "REDUCE"
        elif aligned:
            confidence = 0.75 if (a_hh or b_lh) else 0.4
            recommendation = "HOLD"
        else:
            confidence = 0.2
            recommendation = "HOLD"

        detail = PairDivergenceDetail(
            pair=label,
            asset_a=name_a,
            asset_b=name_b,
            aligned=aligned,
            divergence=divergence,
            a_higher_high=a_hh,
            b_higher_high=b_hh,
            a_lower_high=a_lh,
            b_lower_high=b_lh,
            confidence=confidence,
            recommendation=recommendation,
            extra={
                "lookback": self.lookback,
                "last_a": round(float(series_a.iloc[-1]), 6) if len(series_a) else None,
                "last_b": round(float(series_b.iloc[-1]), 6) if len(series_b) else None,
            },
        )
        return detail

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def detect(self, price_data: pd.DataFrame) -> dict[str, Any]:
        """Evaluate SMT divergence across all monitored pairs.

        Args:
            price_data: DataFrame with columns for every monitored asset symbol.

        Returns:
            Dict matching the required output contract:
            ``{divergence_detected, pairs_affected, confidence, recommendation, details}``
        """
        if price_data is None or price_data.empty:
            logger.warning("SMT detector received empty price data")
            return SMTDivergenceReport(
                divergence_detected=False,
                pairs_affected=[],
                confidence=0.0,
                recommendation="HOLD",
            ).to_dict()

        details: dict[str, PairDivergenceDetail] = {}
        pairs_affected: list[str] = []
        total_confidence = 0.0
        evaluated = 0

        for asset_a, asset_b, label in self._pairs:
            if asset_a not in price_data.columns or asset_b not in price_data.columns:
                logger.debug(
                    "SMT detector skipping %s/%s — missing data columns", asset_a, asset_b
                )
                continue

            detail = self._analyze_pair(asset_a, asset_b, label, price_data)
            details[detail.pair] = detail
            evaluated += 1
            total_confidence += detail.confidence

            if detail.divergence:
                pairs_affected.append(detail.pair)

        divergence_detected = bool(pairs_affected)
        confidence = total_confidence / evaluated if evaluated else 0.0

        if divergence_detected and confidence >= self.confidence_threshold:
            recommendation = "NO TRADE"
        elif divergence_detected:
            recommendation = "REDUCE"
        else:
            recommendation = "HOLD"

        report = SMTDivergenceReport(
            divergence_detected=divergence_detected,
            pairs_affected=pairs_affected,
            confidence=round(confidence, 4),
            recommendation=recommendation,
            details=details,
        )

        logger.info(
            "SMT divergence report: detected=%s pairs=%s confidence=%.2f recommendation=%s",
            divergence_detected,
            pairs_affected,
            confidence,
            recommendation,
        )
        return report.to_dict()

    # ----------------------------------------------------------------
    # Extension hook — combines structural divergence with cointegration breakdown
    # ----------------------------------------------------------------

    def detect_hybrid(
        self, price_data: pd.DataFrame
    ) -> dict[str, Any]:
        """Combine structural HH/LH divergence with cointegration breakdown.

        Imports the existing ``CointegrationSMTDetector`` from
        ``engine/intermarket/cointegration_smt.py`` and merges its signals.

        Returns:
            Combined report with an extra ``cointegration_active`` flag.
        """
        structural = self.detect(price_data)

        try:
            from quant_nanggroe.engine.intermarket.cointegration_smt import (
                CointegrationSMTDetector,
            )

            coint_detector = CointegrationSMTDetector()
            coint_detector.fit(price_data)
            coint_summary = coint_detector.get_summary()
        except Exception as exc:  # pragma: no cover — statsmodels optional path
            logger.debug("Hybrid SMT: cointegration model unavailable (%s)", exc)
            coint_summary = {}

        structural["cointegration_active"] = bool(
            coint_summary.get("divergent_pairs", 0) > 0
        )
        structural["cointegration_summary"] = coint_summary
        return structural


__all__ = [
    "MONITORED_PAIRS",
    "PairDivergenceDetail",
    "SMTDivergenceDetector",
    "SMTDivergenceReport",
]
