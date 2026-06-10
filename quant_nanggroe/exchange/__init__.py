"""Unified Exchange Abstraction Layer.

Provides a unified interface for 100+ cryptocurrency exchanges via CCXT,
alongside paper trading, Solana/Jupiter V6 integration, Alpaca equities
trading, and multi-exchange management with failover.

This module bridges the existing execution engine (engine/execution/) with
real exchange connectivity, offering:

- **ExchangeInterface**: Abstract base with full market data + trading API
- **CCXTBroker**: Production CCXT implementation for Binance, Coinbase, Bybit, OKX, etc.
- **PaperExchangeBroker**: Paper trading with slippage, commission, and P&L tracking
- **AlpacaBroker**: Alpaca paper/live trading for US equities and crypto
- **SolanaBroker**: Solana/Jupiter V6 swap integration
- **SolanaWallet**: Solana keypair management and balance queries
- **JupiterV6Client**: Jupiter V6 swap quotes and execution
- **RugChecker**: Token safety analysis for Solana tokens
- **ExchangeManager**: Multi-exchange orchestration, failover, and portfolio sync
- **ExchangeFactory**: Dynamic exchange client creation with capability detection
- **GuardPipeline**: Pre-trade validation with Whitelist/Cooldown/MaxPosition guards
- **PolymarketBroker**: Polymarket prediction market trading via CLOB API with EIP-712 signing
- **Extended Order Types**: TrailingStop, Bracket, OCO, Iceberg orders with state machines

Usage:
    from quant_nanggroe.exchange import ExchangeManager, CCXTBroker, PaperExchangeBroker

    # Create a paper exchange for testing
    paper = PaperExchangeBroker(initial_capital=100_000)
    await paper.connect()

    # Get market data
    ticker = await paper.get_ticker("BTC/USDT")

    # Place an order
    order = await paper.place_order(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1,
    )

    # Multi-exchange setup with failover
    manager = ExchangeManager()
    manager.register("binance", ccxt_broker, primary=True)
    manager.register("paper", paper_broker, failover=True)
    await manager.connect_all()
"""

from quant_nanggroe.exchange.base import (
    ExchangeInterface,
    ExchangeConfig,
    ExchangeState,
    ExchangeError,
    ConnectionError,
    OrderError,
    RateLimitError,
    AuthenticationError,
    InsufficientFundsError,
    MarketDataError,
    WebSocketCallback,
)
from quant_nanggroe.exchange.ccxt_broker import CCXTBroker
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.exchange.manager import ExchangeManager
from quant_nanggroe.exchange.alpaca_broker import AlpacaBroker
from quant_nanggroe.exchange.polymarket_broker import PolymarketBroker

# Solana/Jupiter V6 integration
from quant_nanggroe.exchange.solana import (
    SolanaWallet,
    TokenAccountInfo,
    JupiterV6Client,
    JupiterQuote,
    JupiterSwapResult,
    SolanaMempoolMonitor,
    MempoolEvent,
    MempoolEventType,
    RugChecker,
    TokenSafetyReport,
    SafetyVerdict,
    SolanaBroker,
)

# Exchange factory
from quant_nanggroe.exchange.factory import (
    ExchangeFactory,
    ExchangeFactoryConfig,
    ExchangeFactoryError,
    ExchangeCapabilities,
    MarketType,
    SUPPORTED_EXCHANGES,
)

# Trading guards pipeline
from quant_nanggroe.exchange.guards import (
    BaseGuard,
    WhitelistGuard,
    CooldownGuard,
    MaxPositionGuard,
    GuardPipeline,
    GuardVerdict,
    GuardResult,
    PipelineResult,
)

# Extended order types
from quant_nanggroe.exchange.order_types import (
    ExtendedOrderStatus,
    TrailingStopOrder,
    BracketOrder,
    BracketLegStatus,
    OCOOrder,
    IcebergOrder,
    StateTransitionError,
    TransitionRecord,
    transition_status,
    TERMINAL_STATES,
)

__all__ = [
    # Abstract interface
    "ExchangeInterface",
    "ExchangeConfig",
    "ExchangeState",
    # Errors
    "ExchangeError",
    "ConnectionError",
    "OrderError",
    "RateLimitError",
    "AuthenticationError",
    "InsufficientFundsError",
    "MarketDataError",
    # Callbacks
    "WebSocketCallback",
    # Implementations
    "CCXTBroker",
    "PaperExchangeBroker",
    "AlpacaBroker",
    "PolymarketBroker",
    # Solana/Jupiter V6
    "SolanaWallet",
    "TokenAccountInfo",
    "JupiterV6Client",
    "JupiterQuote",
    "JupiterSwapResult",
    "SolanaMempoolMonitor",
    "MempoolEvent",
    "MempoolEventType",
    "RugChecker",
    "TokenSafetyReport",
    "SafetyVerdict",
    "SolanaBroker",
    # Manager
    "ExchangeManager",
    # Factory
    "ExchangeFactory",
    "ExchangeFactoryConfig",
    "ExchangeFactoryError",
    "ExchangeCapabilities",
    "MarketType",
    "SUPPORTED_EXCHANGES",
    # Guards
    "BaseGuard",
    "WhitelistGuard",
    "CooldownGuard",
    "MaxPositionGuard",
    "GuardPipeline",
    "GuardVerdict",
    "GuardResult",
    "PipelineResult",
    # Extended order types
    "ExtendedOrderStatus",
    "TrailingStopOrder",
    "BracketOrder",
    "BracketLegStatus",
    "OCOOrder",
    "IcebergOrder",
    "StateTransitionError",
    "TransitionRecord",
    "transition_status",
    "TERMINAL_STATES",
]
