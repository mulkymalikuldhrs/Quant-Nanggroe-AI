"""
QNA Intermarket Engine — Lead-Lag, SMT Divergence & Cross-Asset Analysis.

Provides:
  - CointegrationSMTDetector: Cointegration-based SMT divergence (Bennett 2022)
  - Lead-lag matrix via time-shifted cross-correlation

Usage:
    from quant_nanggroe.engine.intermarket import CointegrationSMTDetector
    detector = CointegrationSMTDetector()
    detector.fit(price_df)  # DataFrame with columns ['GC1!', 'SI1!', ...]
    result = detector.detect()
"""

from quant_nanggroe.engine.intermarket.cointegration_smt import (
    CORRELATED_PAIRS,
    CointegratedPair,
    CointegrationSMTDetector,
    SMTDivergenceResult,
)

__all__ = [
    "CointegrationSMTDetector",
    "CointegratedPair",
    "SMTDivergenceResult",
    "CORRELATED_PAIRS",
]
