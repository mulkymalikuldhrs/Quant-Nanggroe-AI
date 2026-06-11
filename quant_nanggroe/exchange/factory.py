"""Exchange Factory — Dynamic exchange client creation.

Provides a factory for creating exchange clients based on exchange name,
with support for multiple exchanges, market type routing, configuration
validation, and exchange capability detection.

All exchange implementations use CCXT as the underlying library.

Supported Exchanges
-------------------
binance, okx, bybit, bitget, kraken, kucoin, gate, coinbase

Usage
-----
.. code-block:: python

    factory = ExchangeFactory()

    # Create a Binance spot exchange
    broker = factory.create("binance", api_key="...", api_secret="...", market_type="spot")

    # Create an OKX futures exchange
    broker = factory.create("okx", api_key="...", api_secret="...", passphrase="...", market_type="futures")

    # Check capabilities
    caps = factory.get_capabilities("binance")
    if caps.supports_futures:
        ...
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set

from pydantic import BaseModel, Field, field_validator

from quant_nanggroe.exchange.base import ExchangeConfig, ExchangeInterface
from quant_nanggroe.exchange.ccxt_broker import CCXTBroker
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Market type routing
# ---------------------------------------------------------------------------

class MarketType(str, Enum):
    """Supported market types for exchange routing."""

    SPOT = "spot"
    FUTURES = "futures"
    PERPS = "perps"  # perpetual swaps


# ---------------------------------------------------------------------------
# Exchange capability detection
# ---------------------------------------------------------------------------

class ExchangeCapabilities(BaseModel):
    """Describes what an exchange supports.

    Attributes:
        exchange_id: Exchange identifier (e.g. ``"binance"``).
        supports_spot: Whether the exchange supports spot trading.
        supports_futures: Whether the exchange supports dated futures.
        supports_perps: Whether the exchange supports perpetual swaps.
        supports_margin: Whether the exchange supports margin trading.
        supports_websocket: Whether the exchange supports WebSocket streaming.
        supports_paper_trading: Whether paper trading is available.
        requires_passphrase: Whether the exchange requires an API passphrase.
        max_leverage: Maximum leverage supported (1 = no leverage).
        ccxt_id: The CCXT exchange class identifier.
    """

    exchange_id: str
    supports_spot: bool = True
    supports_futures: bool = False
    supports_perps: bool = False
    supports_margin: bool = False
    supports_websocket: bool = True
    supports_paper_trading: bool = True
    requires_passphrase: bool = False
    max_leverage: float = 1.0
    ccxt_id: str = ""

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Exchange capability registry
# ---------------------------------------------------------------------------

_CAPABILITY_REGISTRY: Dict[str, ExchangeCapabilities] = {
    "binance": ExchangeCapabilities(
        exchange_id="binance",
        supports_spot=True,
        supports_futures=True,
        supports_perps=True,
        supports_margin=True,
        supports_websocket=True,
        requires_passphrase=False,
        max_leverage=125.0,
        ccxt_id="binance",
    ),
    "okx": ExchangeCapabilities(
        exchange_id="okx",
        supports_spot=True,
        supports_futures=True,
        supports_perps=True,
        supports_margin=True,
        supports_websocket=True,
        requires_passphrase=True,
        max_leverage=125.0,
        ccxt_id="okx",
    ),
    "bybit": ExchangeCapabilities(
        exchange_id="bybit",
        supports_spot=True,
        supports_futures=True,
        supports_perps=True,
        supports_margin=True,
        supports_websocket=True,
        requires_passphrase=False,
        max_leverage=100.0,
        ccxt_id="bybit",
    ),
    "bitget": ExchangeCapabilities(
        exchange_id="bitget",
        supports_spot=True,
        supports_futures=True,
        supports_perps=True,
        supports_margin=True,
        supports_websocket=True,
        requires_passphrase=True,
        max_leverage=125.0,
        ccxt_id="bitget",
    ),
    "kraken": ExchangeCapabilities(
        exchange_id="kraken",
        supports_spot=True,
        supports_futures=True,
        supports_perps=False,
        supports_margin=True,
        supports_websocket=True,
        requires_passphrase=False,
        max_leverage=50.0,
        ccxt_id="kraken",
    ),
    "kucoin": ExchangeCapabilities(
        exchange_id="kucoin",
        supports_spot=True,
        supports_futures=True,
        supports_perps=True,
        supports_margin=True,
        supports_websocket=True,
        requires_passphrase=True,
        max_leverage=100.0,
        ccxt_id="kucoin",
    ),
    "gate": ExchangeCapabilities(
        exchange_id="gate",
        supports_spot=True,
        supports_futures=True,
        supports_perps=True,
        supports_margin=True,
        supports_websocket=True,
        requires_passphrase=False,
        max_leverage=100.0,
        ccxt_id="gate",
    ),
    "coinbase": ExchangeCapabilities(
        exchange_id="coinbase",
        supports_spot=True,
        supports_futures=True,
        supports_perps=False,
        supports_margin=False,
        supports_websocket=True,
        requires_passphrase=True,
        max_leverage=3.0,
        ccxt_id="coinbase",
    ),
}

# Exchanges that require a passphrase
_PASSPHRASE_EXCHANGES: FrozenSet[str] = frozenset(
    name for name, cap in _CAPABILITY_REGISTRY.items() if cap.requires_passphrase
)

# All supported exchange names
SUPPORTED_EXCHANGES: FrozenSet[str] = frozenset(_CAPABILITY_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------

class ExchangeFactoryConfig(BaseModel):
    """Configuration for the exchange factory.

    Attributes:
        default_market_type: Default market type when not specified.
        sandbox: Use sandbox/testnet mode for all exchanges.
        default_rate_limit: Default rate limit (requests/second).
        default_timeout: Default HTTP timeout in seconds.
        default_retries: Default number of retries.
        custom_options: Per-exchange custom CCXT options.
    """

    default_market_type: MarketType = MarketType.SPOT
    sandbox: bool = False
    default_rate_limit: float = Field(default=5.0, gt=0)
    default_timeout: int = Field(default=30, gt=0)
    default_retries: int = Field(default=3, ge=0)
    custom_options: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class ExchangeFactoryError(Exception):
    """Error raised by the exchange factory."""

    def __init__(self, message: str, exchange: Optional[str] = None) -> None:
        self.exchange = exchange
        super().__init__(message)


# ---------------------------------------------------------------------------
# Exchange Factory
# ---------------------------------------------------------------------------

class ExchangeFactory:
    """Factory for creating exchange clients dynamically.

    Supports creating CCXT-backed exchange clients for 8 major exchanges
    with automatic configuration validation and capability detection.

    Usage
    -----
    .. code-block:: python

        factory = ExchangeFactory()

        # Create a Binance broker
        broker = factory.create("binance", api_key="key", api_secret="secret")

        # Create an OKX broker with passphrase
        broker = factory.create("okx", api_key="key", api_secret="secret", passphrase="pass")

        # Create a paper broker
        broker = factory.create("paper", initial_capital=100_000)

        # Check what an exchange supports
        caps = factory.get_capabilities("binance")
    """

    def __init__(self, config: Optional[ExchangeFactoryConfig] = None) -> None:
        """Initialize the factory.

        Args:
            config: Optional factory configuration. Uses defaults if not provided.
        """
        self._config = config or ExchangeFactoryConfig()
        self._created_exchanges: Dict[str, ExchangeInterface] = {}

    # ------------------------------------------------------------------ #
    # Create exchange
    # ------------------------------------------------------------------ #

    def create(
        self,
        exchange_name: str,
        *,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        market_type: Optional[str] = None,
        sandbox: Optional[bool] = None,
        rate_limit: Optional[float] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
        extra_options: Optional[Dict[str, Any]] = None,
    ) -> ExchangeInterface:
        """Create an exchange client based on the exchange name.

        Args:
            exchange_name: Exchange identifier (e.g. ``"binance"``, ``"okx"``).
                Use ``"paper"`` for a paper trading exchange.
            api_key: Exchange API key.
            api_secret: Exchange API secret.
            passphrase: API passphrase (required for OKX, KuCoin, Bitget, Coinbase).
            market_type: Market type routing (``"spot"``, ``"futures"``, ``"perps"``).
            sandbox: Override sandbox mode for this exchange.
            rate_limit: Override rate limit for this exchange.
            timeout: Override timeout for this exchange.
            retries: Override retries for this exchange.
            initial_capital: Initial capital for paper trading.
            commission_rate: Commission rate for paper trading.
            slippage_bps: Slippage in basis points for paper trading.
            extra_options: Additional CCXT options.

        Returns:
            An :class:`~quant_nanggroe.exchange.base.ExchangeInterface` instance.

        Raises:
            ExchangeFactoryError: If the exchange name is not supported
                or configuration is invalid.
        """
        name_lower = exchange_name.lower().strip()

        # Handle paper trading
        if name_lower == "paper":
            return self._create_paper_broker(
                initial_capital=initial_capital,
                commission_rate=commission_rate,
                slippage_bps=slippage_bps,
            )

        # Validate exchange name
        if name_lower not in SUPPORTED_EXCHANGES:
            raise ExchangeFactoryError(
                f"Unsupported exchange: '{exchange_name}'. "
                f"Supported: {sorted(SUPPORTED_EXCHANGES)}",
                exchange=exchange_name,
            )

        # Resolve market type
        effective_market = self._resolve_market_type(name_lower, market_type)

        # Validate configuration
        self._validate_config(
            name_lower,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )

        # Build exchange config
        options: Dict[str, Any] = {}

        # Add market-type specific options
        if effective_market == MarketType.FUTURES:
            options["defaultType"] = "future"
        elif effective_market == MarketType.PERPS:
            options["defaultType"] = "swap"
        else:
            options["defaultType"] = "spot"

        # Merge custom options from factory config
        custom = self._config.custom_options.get(name_lower, {})
        options.update(custom)

        # Merge extra options
        if extra_options:
            options.update(extra_options)

        exchange_config = ExchangeConfig(
            exchange_id=name_lower,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            sandbox=sandbox if sandbox is not None else self._config.sandbox,
            rate_limit=rate_limit or self._config.default_rate_limit,
            timeout=timeout or self._config.default_timeout,
            retries=retries if retries is not None else self._config.default_retries,
            options=options,
        )

        broker = CCXTBroker(exchange_config)

        # Track created exchange
        self._created_exchanges[name_lower] = broker

        logger.info(
            "ExchangeFactory: Created %s exchange (market=%s, sandbox=%s)",
            name_lower, effective_market.value, exchange_config.sandbox,
        )

        return broker

    def _create_paper_broker(
        self,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        slippage_bps: float = 5.0,
    ) -> PaperExchangeBroker:
        """Create a paper trading exchange.

        Args:
            initial_capital: Starting capital.
            commission_rate: Commission rate.
            slippage_bps: Slippage in basis points.

        Returns:
            A :class:`~quant_nanggroe.exchange.paper_broker.PaperExchangeBroker`.
        """
        broker = PaperExchangeBroker(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_bps=slippage_bps,
        )
        self._created_exchanges["paper"] = broker
        return broker

    # ------------------------------------------------------------------ #
    # Market type routing
    # ------------------------------------------------------------------ #

    def _resolve_market_type(
        self,
        exchange_name: str,
        market_type: Optional[str] = None,
    ) -> MarketType:
        """Resolve the effective market type for an exchange.

        Args:
            exchange_name: Exchange identifier.
            market_type: Requested market type (or None for default).

        Returns:
            Resolved :class:`MarketType`.

        Raises:
            ExchangeFactoryError: If the exchange doesn't support the requested market type.
        """
        if market_type is None:
            return self._config.default_market_type

        try:
            mt = MarketType(market_type.lower().strip())
        except ValueError:
            raise ExchangeFactoryError(
                f"Invalid market type: '{market_type}'. "
                f"Valid options: {[m.value for m in MarketType]}",
                exchange=exchange_name,
            )

        # Check capability
        caps = _CAPABILITY_REGISTRY.get(exchange_name)
        if caps is None:
            return mt  # Unknown exchange, allow anything

        if mt == MarketType.SPOT and not caps.supports_spot:
            raise ExchangeFactoryError(
                f"Exchange '{exchange_name}' does not support spot trading",
                exchange=exchange_name,
            )
        if mt == MarketType.FUTURES and not caps.supports_futures:
            raise ExchangeFactoryError(
                f"Exchange '{exchange_name}' does not support futures trading",
                exchange=exchange_name,
            )
        if mt == MarketType.PERPS and not caps.supports_perps:
            raise ExchangeFactoryError(
                f"Exchange '{exchange_name}' does not support perpetual swaps",
                exchange=exchange_name,
            )

        return mt

    # ------------------------------------------------------------------ #
    # Configuration validation
    # ------------------------------------------------------------------ #

    def _validate_config(
        self,
        exchange_name: str,
        *,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> None:
        """Validate the configuration for an exchange.

        Args:
            exchange_name: Exchange identifier.
            api_key: API key.
            api_secret: API secret.
            passphrase: API passphrase.

        Raises:
            ExchangeFactoryError: If the configuration is invalid.
        """
        caps = _CAPABILITY_REGISTRY.get(exchange_name)
        if caps is None:
            return  # Skip validation for unknown exchanges

        # Warn if API credentials are missing (but don't error — may be public-only)
        if api_key is None or api_secret is None:
            logger.warning(
                "ExchangeFactory: Creating %s without API credentials — "
                "only public endpoints will be available",
                exchange_name,
            )

        # Require passphrase for exchanges that need it
        if caps.requires_passphrase and api_key and not passphrase:
            logger.warning(
                "ExchangeFactory: Exchange '%s' typically requires a passphrase, "
                "but none was provided. Authentication may fail.",
                exchange_name,
            )

    # ------------------------------------------------------------------ #
    # Capability detection
    # ------------------------------------------------------------------ #

    def get_capabilities(self, exchange_name: str) -> ExchangeCapabilities:
        """Get the capabilities of an exchange.

        Args:
            exchange_name: Exchange identifier.

        Returns:
            :class:`ExchangeCapabilities` describing what the exchange supports.

        Raises:
            ExchangeFactoryError: If the exchange is not known.
        """
        name_lower = exchange_name.lower().strip()
        caps = _CAPABILITY_REGISTRY.get(name_lower)
        if caps is None:
            raise ExchangeFactoryError(
                f"Unknown exchange: '{exchange_name}'. "
                f"Known exchanges: {sorted(SUPPORTED_EXCHANGES)}",
                exchange=exchange_name,
            )
        return caps.model_copy()

    @staticmethod
    def list_supported_exchanges() -> List[str]:
        """List all supported exchange names.

        Returns:
            Sorted list of supported exchange identifiers.
        """
        return sorted(SUPPORTED_EXCHANGES)

    @staticmethod
    def list_exchanges_by_capability(capability: str) -> List[str]:
        """List exchanges that support a specific capability.

        Args:
            capability: Capability name (e.g. ``"supports_futures"``,
                ``"supports_perps"``, ``"requires_passphrase"``).

        Returns:
            Sorted list of exchange identifiers with that capability.
        """
        result = []
        for name, caps in _CAPABILITY_REGISTRY.items():
            attr_val = getattr(caps, capability, None)
            if attr_val is True:
                result.append(name)
        return sorted(result)

    # ------------------------------------------------------------------ #
    # Factory state
    # ------------------------------------------------------------------ #

    @property
    def created_exchanges(self) -> Dict[str, ExchangeInterface]:
        """Get all exchanges created by this factory."""
        return dict(self._created_exchanges)

    @property
    def config(self) -> ExchangeFactoryConfig:
        """Get the factory configuration."""
        return self._config
