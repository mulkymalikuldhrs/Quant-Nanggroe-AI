"""Core signal providers — built-in strategies that run locally or call external ecosystems.

Each returns {"bias": "buy"|"sell"|"neutral", "confidence": 0-1, "source": "name"}.

Providers:
- signal_sma — SMA 20/50 crossover (free, always on)
- signal_wyckoff — Wyckoff Volume Spread Analysis
- signal_aihf — AI Hedge Fund (15 agent investors from E:/ai-hedge-fund)
- signal_hidden — Hidden Markov Model regime detection (E:/hidden-regime)
- signal_tradingagents — Multi-agent trading graph (E:/tradingagents)
- signal_aitrader — Node.js AI trader subprocess (E:/AI-Trader)
- signal_langalpha — LLM alpha research agent (E:/LangAlpha)
- signal_aimarketmaker — AI Market Maker agentic crypto HF (E:/ai-market-maker)
- signal_kronos — Kronos Foundation Model price forecasting (AAAI 2026)
- signal_pyportfolioopt — PyPortfolioOpt optimal position sizing

Related sections in hedge_fund.py: lines 99-286
"""
# TODO: Extract from quant_nanggroe.hedge_fund.hedge_fund
from quant_nanggroe.hedge_fund.hedge_fund import (
    signal_sma, signal_wyckoff, signal_aihf, signal_hidden,
    signal_tradingagents, signal_aitrader, signal_langalpha,
    signal_aimarketmaker, signal_kronos, signal_pyportfolioopt,
)
