"""
QNA COT Engine — CFTC Commitment of Traders automated fetching, caching, and analysis.

Provides:
  - COTFetcher:  Automated weekly COT data fetching with disk cache
  - COTAnalyzer: Historical percentile calculation + extreme positioning signals
  - CME symbol → COT market name mapping for QNA's asset universe

Usage:
    from quant_nanggroe.engine.cot import COTAnalyzer

    analyzer = COTAnalyzer()
    analyzer.fetch_history(years=3)
    signal = analyzer.evaluate("GC1!")  # Returns signal dict
"""

from quant_nanggroe.engine.cot.cot_analyzer import (
    CME_TO_COT_MAP,
    POSITIONING_SIGNAL,
    COTAnalyzer,
)
from quant_nanggroe.engine.cot.cot_fetcher import COTFetcher

__all__ = [
    "COTFetcher",
    "COTAnalyzer",
    "CME_TO_COT_MAP",
    "POSITIONING_SIGNAL",
]
