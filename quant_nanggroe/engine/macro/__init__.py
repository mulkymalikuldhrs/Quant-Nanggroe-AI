"""
QNA Macro Engine — Economic calendar, FRED data, and Macro Surprise Index.

Provides:
  - EconomicCalendarProvider: Track scheduled economic releases
  - MacroSurpriseIndex: MSI = (Actual - Consensus) / HistoricalStd via FRED API

Usage:
    from quant_nanggroe.engine.macro import MacroSurpriseIndex
    msi = MacroSurpriseIndex(api_key="YOUR_FRED_KEY")
    result = msi.evaluate_all()
    # Returns dict of indicator -> MSI score + bias direction
"""

from quant_nanggroe.engine.macro.economic_calendar import EconomicCalendarProvider
from quant_nanggroe.engine.macro.macro_surprise_index import (
    ECONOMIC_INDICATORS,
    MacroSurpriseIndex,
    MSIResult,
)

__all__ = [
    "EconomicCalendarProvider",
    "MacroSurpriseIndex",
    "ECONOMIC_INDICATORS",
    "MSIResult",
]
