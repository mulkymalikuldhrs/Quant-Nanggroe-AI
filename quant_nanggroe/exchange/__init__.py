"""Unified Exchange Abstraction Layer.

Provides a unified interface for 100+ cryptocurrency exchanges via CCXT,
alongside paper trading, Solana/Jupiter V6 integration, Alpaca equities
trading, MetaTrader 5, Interactive Brokers, Polymarket prediction markets,
and multi-exchange management with failover.

This module bridges the existing execution engine (engine/execution/) with
real exchange connectivity, offering:

- **ExchangeInterface**: Abstract base with full market data + trading API
- **CCXTBroker**: Production CCXT implementation for Binance, Coinbase, Bybit, OKX, etc.
- **PaperExchangeBroker**: Paper trading with slippage, commission, and P&L tracking
- **AlpacaBroker**: Alpaca paper/live trading for US equities and crypto
- **PolymarketBroker**: Polymarket CLOB prediction market trading
- **MT5Broker**: MetaTrader 5 forex/CFD trading
- **IBKRBroker**: Interactive Brokers TWS/Gateway trading
- **QuantDingerFactory**: Multi-exchange factory for 9+ crypto exchanges
- **SolanaBroker**: Solana/Jupiter V6 swap integration
- **SolanaWallet**: Solana keypair management and balance queries
- **JupiterV6Client**: Jupiter V6 swap quotes and execution
- **RugChecker**: Token safety analysis for Solana tokens
- **ExchangeManager**: Multi-exchange orchestration, failover, and portfolio sync
- **ExchangeFactory**: Dynamic exchange client creation with capability detection
- **GuardPipeline**: Pre-trade validation with Whitelist/Cooldown/MaxPosition guards
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

# CCXTBroker requires the ``ccxt`` package (optional)
try:
    from quant_nanggroe.exchange.ccxt_broker import CCXTBroker
except ImportError:
    CCXTBroker = None  # type: ignore[assignment,misc]

from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.exchange.manager import ExchangeManager

# AlpacaBroker requires the ``alpaca-py`` package (optional)
try:
    from quant_nanggroe.exchange.alpaca_broker import AlpacaBroker
except ImportError:
    AlpacaBroker = None  # type: ignore[assignment,misc]

# New broker modules (optional dependencies)
try:
    from quant_nanggroe.exchange.polymarket_broker import PolymarketBroker, PolymarketCLOBClient
except ImportError:
    PolymarketBroker = None  # type: ignore[assignment,misc]
    PolymarketCLOBClient = None  # type: ignore[assignment,misc]

try:
    from quant_nanggroe.exchange.mt5_broker import MT5Broker
except ImportError:
    MT5Broker = None  # type: ignore[assignment,misc]

try:
    from quant_nanggroe.exchange.ibkr_broker import IBKRBroker
except ImportError:
    IBKRBroker = None  # type: ignore[assignment,misc]

try:
    from quant_nanggroe.exchange.quantdinger_factory import QuantDingerFactory
except ImportError:
    QuantDingerFactory = None  # type: ignore[assignment,misc]

# Solana/Jupiter V6 integration (optional – requires solders/solana)
try:
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
except ImportError:
    SolanaWallet = None  # type: ignore[assignment,misc]
    TokenAccountInfo = None  # type: ignore[assignment,misc]
    JupiterV6Client = None  # type: ignore[assignment,misc]
    JupiterQuote = None  # type: ignore[assignment,misc]
    JupiterSwapResult = None  # type: ignore[assignment,misc]
    SolanaMempoolMonitor = None  # type: ignore[assignment,misc]
    MempoolEvent = None  # type: ignore[assignment,misc]
    MempoolEventType = None  # type: ignore[assignment,misc]
    RugChecker = None  # type: ignore[assignment,misc]
    TokenSafetyReport = None  # type: ignore[assignment,misc]
    SafetyVerdict = None  # type: ignore[assignment,misc]
    SolanaBroker = None  # type: ignore[assignment,misc]

# Exchange factory
try:
    from quant_nanggroe.exchange.factory import (
        ExchangeFactory,
        ExchangeFactoryConfig,
        ExchangeFactoryError,
        ExchangeCapabilities,
        MarketType,
        SUPPORTED_EXCHANGES,
    )
except ImportError:
    ExchangeFactory = None  # type: ignore[assignment,misc]
    ExchangeFactoryConfig = None  # type: ignore[assignment,misc]
    ExchangeFactoryError = None  # type: ignore[assignment,misc]
    ExchangeCapabilities = None  # type: ignore[assignment,misc]
    MarketType = None  # type: ignore[assignment,misc]
    SUPPORTED_EXCHANGES = None  # type: ignore[assignment,misc]

# Trading guards pipeline
try:
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
except ImportError:
    BaseGuard = None  # type: ignore[assignment,misc]
    WhitelistGuard = None  # type: ignore[assignment,misc]
    CooldownGuard = None  # type: ignore[assignment,misc]
    MaxPositionGuard = None  # type: ignore[assignment,misc]
    GuardPipeline = None  # type: ignore[assignment,misc]
    GuardVerdict = None  # type: ignore[assignment,misc]
    GuardResult = None  # type: ignore[assignment,misc]
    PipelineResult = None  # type: ignore[assignment,misc]

# Extended order types
try:
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
except ImportError:
    ExtendedOrderStatus = None  # type: ignore[assignment,misc]
    TrailingStopOrder = None  # type: ignore[assignment,misc]
    BracketOrder = None  # type: ignore[assignment,misc]
    BracketLegStatus = None  # type: ignore[assignment,misc]
    OCOOrder = None  # type: ignore[assignment,misc]
    IcebergOrder = None  # type: ignore[assignment,misc]
    StateTransitionError = None  # type: ignore[assignment,misc]
    TransitionRecord = None  # type: ignore[assignment,misc]
    transition_status = None  # type: ignore[assignment,misc]
    TERMINAL_STATES = None  # type: ignore[assignment,misc]

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
    # New brokers
    "PolymarketBroker",
    "PolymarketCLOBClient",
    "MT5Broker",
    "IBKRBroker",
    "QuantDingerFactory",
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
