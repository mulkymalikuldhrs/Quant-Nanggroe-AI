"""
AI Hedge Fund - Professional Quantitative Trading System

A comprehensive, production-ready hedge fund trading system with:
- Multiple quantitative strategies
- AI-powered signal generation
- Portfolio optimization
- Risk management
- Paper trading
- FREE broker integrations (Alpaca, Binance, OANDA)
- Virtual Trading Terminal (no paid MetaTrader API!)
- Autonomous trading capabilities

Built with ❤️ for the crypto and stock markets
"""

__version__ = "3.0.0"
__author__ = "AI Hedge Fund Team"

from .strategies import *
from .analysis import *

# Temporarily disabled for core functionality testing
# from .backtesting import *
# from .brokers import *  # Requires plotly
# from .automation import *  # Depends on brokers
from .optimization import *
from .risk import *
from .ml import *
from .paper_trading import *
from .options import *
from .indicators import *
from .fund_management import *
from .utils import *

__all__ = ["__version__", "__author__"]
