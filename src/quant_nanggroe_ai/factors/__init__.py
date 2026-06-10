"""
Alpha Factors Package — 456+ Alpha Factors + Registry
======================================================
Factor Libraries:
  - Alpha101: 101 WorldQuant Formulaic Alphas
  - GTJA191: 191 Guotai Junan Alphas
  - Qlib158: 155 Microsoft Qlib Factors
  - Academic: Fama-French 5-factor + Carhart Momentum
  - Technical: RSI, MACD, Bollinger
  - Registry: Central registry with auto-discovery
"""

from quant_nanggroe_ai.factors.alpha101 import ALPHA_FACTORS
from quant_nanggroe_ai.factors.registry import FactorRegistry

__all__ = [
    "ALPHA_FACTORS",
    "FactorRegistry",
]
