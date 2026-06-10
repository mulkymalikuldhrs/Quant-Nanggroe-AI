"""
AI Auto-Trading Engine - Fully Autonomous Trading System

This package contains the "brain" of our AI hedge fund:
- Signal generation and aggregation
- Autonomous order execution
- Risk management
- Performance optimization
"""

from .ai_auto_trader import SignalStrength, SignalSource, TradingSignal, Trade, AIAutoTrader, create_auto_trader

__all__ = ["SignalStrength", "SignalSource", "TradingSignal", "Trade", "AIAutoTrader", "create_auto_trader"]
