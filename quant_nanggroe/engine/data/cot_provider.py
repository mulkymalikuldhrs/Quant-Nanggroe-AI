"""COT Data Provider — backward-compatible redirect to engine/cot/ (the real implementation).

This module previously contained a broken COTProvider/COTAnalyzer that raised
NotImplementedError. It now redirects to the working engine/cot/ module which
uses cot_reports + CFTC data with proper percentile-based analysis.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class COTDataNotAvailableError(RuntimeError):
    """Raised when COT data is requested but no CFTC data source is configured."""


class COTProvider:
    """Backward-compatible COT provider — delegates to engine/cot/ real implementation."""

    def __init__(self, data_source: str | None = None):
        self._analyzer = None
        self._data: dict = {}
        self._lazy_init()

    def _lazy_init(self):
        try:
            from quant_nanggroe.engine.cot import COTAnalyzer as RealCOTAnalyzer
            self._analyzer = RealCOTAnalyzer(years_history=3)
            self._analyzer.fetch_history()
        except Exception as e:
            logger.debug("Real COT analyzer unavailable: %s", e)

    def fetch(self) -> dict:
        """Fetch COT data. Returns evaluation dict or empty dict on failure."""
        if self._analyzer is not None and self._analyzer.is_loaded:
            return self._analyzer.evaluate_all()
        return {}

    def get_positioning(self, symbol: str) -> dict:
        if self._analyzer is not None and self._analyzer.is_loaded:
            return self._analyzer.evaluate(symbol)
        raise COTDataNotAvailableError(f"COT data not loaded for {symbol}.")

    def get_extreme_readings(self) -> list:
        if self._analyzer is not None and self._analyzer.is_loaded:
            summary = self._analyzer.get_summary()
            return list(summary.get("extreme_signals", {}).values())
        return []


class COTAnalyzer:
    """Backward-compatible COT analyzer — delegates to engine/cot/ real implementation."""

    def __init__(self, data_or_provider=None):
        self._real_analyzer = None
        self._lazy_init()

    def _lazy_init(self):
        try:
            from quant_nanggroe.engine.cot import COTAnalyzer as RealCOTAnalyzer
            self._real_analyzer = RealCOTAnalyzer(years_history=3)
            self._real_analyzer.fetch_history()
        except Exception as e:
            logger.debug("Real COT analyzer unavailable: %s", e)

    def generate_signal(self, symbol: str, price_series=None) -> dict:
        """Generate COT signal. Returns dict compatible with strategy interface."""
        if self._real_analyzer is None or not self._real_analyzer.is_loaded:
            return {"symbol": symbol, "signal": "neutral", "confidence": 0.0, "reasoning": "COT data not available"}
        eval_result = self._real_analyzer.evaluate(symbol)
        signal_name = eval_result.get("signal", "BALANCED")
        # Map real signals to strategy-compatible signals
        if signal_name in ("EXTREME_SHORT_OVERSOLD", "COMMERCIAL_ACCUMULATION", "RETAIL_EXTREME_SHORT"):
            side = "buy"
        elif signal_name in ("EXTREME_LONG_OVERBOUGHT", "COMMERCIAL_DISTRIBUTION", "RETAIL_EXTREME_LONG"):
            side = "sell"
        else:
            side = "neutral"
        percentile = eval_result.get("percentile_noncomm") or 0.5
        confidence = abs(percentile - 0.5) * 2  # 0 at center, 1 at extremes
        return {
            "symbol": symbol,
            "signal": side,
            "confidence": round(confidence, 3),
            "reasoning": f"COT {signal_name}: pct={percentile:.2f}",
        }

    def cot_index(self, symbol: str) -> float:
        """Compute COT index for a symbol (percentile-based)."""
        if self._real_analyzer is not None and self._real_analyzer.is_loaded:
            result = self._real_analyzer.evaluate(symbol)
            return float(result.get("percentile_noncomm") or 0.5)
        return 0.5

    def detect_divergence(self, symbol: str) -> Optional[str]:
        """Detect COT divergence for a symbol."""
        if self._real_analyzer is not None and self._real_analyzer.is_loaded:
            result = self._real_analyzer.evaluate(symbol)
            signal = result.get("signal", "BALANCED")
            if signal != "BALANCED":
                return signal
        return None

    def classify_extreme(self, symbol: str) -> Optional[str]:
        """Classify extreme positioning."""
        if self._real_analyzer is not None and self._real_analyzer.is_loaded:
            result = self._real_analyzer.evaluate(symbol)
            signal = result.get("signal", "BALANCED")
            if "EXTREME" in signal:
                return signal
        return None


# Backward-compatible alias
COTDataProvider = COTProvider
