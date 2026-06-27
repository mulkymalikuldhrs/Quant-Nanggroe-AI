# exchange.factory

## Class: 

Supported market types for exchange routing.

*Line: 56*

---

## Class: 

Describes what an exchange supports.

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

*Line: 68*

---

## Class: 

Configuration for the exchange factory.

Attributes:
    default_market_type: Default market type when not specified.
    sandbox: Use sandbox/testnet mode for all exchanges.
    default_rate_limit: Default rate limit (requests/second).
    default_timeout: Default HTTP timeout in seconds.
    default_retries: Default number of retries.
    custom_options: Per-exchange custom CCXT options.

*Line: 206*

---

## Class: 

Error raised by the exchange factory.

**Methods:** __init__

*Line: 232*

---

## Class: 

Factory for creating exchange clients dynamically.

Supports creating CCXT-backed exchange clients for 8 major exchanges
with automatic configuration validation and capability detection.

Usage
-----
.. code-block:: python

    factory = ExchangeFactory()

    # Create a Binance broker
    broker = factory.create("binance", api_key="YOUR_API_KEY_HERE", api_secret="YOUR_API_SECRET_HERE")

    # Create an OKX broker with passphrase
    broker = factory.create("okx", api_key="YOUR_API_KEY_HERE", api_secret="YOUR_API_SECRET_HERE", passphrase="YOUR_API_PASSPHRASE_HERE")

    # Create a paper broker
    broker = factory.create("paper", initial_capital=100_000)

    # Check what an exchange supports
    caps = factory.get_capabilities("binance")

**Methods:** __init__, create, _create_paper_broker, _resolve_market_type, _validate_config, get_capabilities, list_supported_exchanges, list_exchanges_by_capability, created_exchanges, config

*Line: 244*

---

## Function: 

*Line: 235*

---

## Function: 

Initialize the factory.

Args:
    config: Optional factory configuration. Uses defaults if not provided.

*Line: 269*

---

## Function: 

Create an exchange client based on the exchange name.

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

*Line: 282*

---

## Function: 

Create a paper trading exchange.

Args:
    initial_capital: Starting capital.
    commission_rate: Commission rate.
    slippage_bps: Slippage in basis points.

Returns:
    A :class:`~quant_nanggroe.exchange.paper_broker.PaperExchangeBroker`.

*Line: 396*

---

## Function: 

Resolve the effective market type for an exchange.

Args:
    exchange_name: Exchange identifier.
    market_type: Requested market type (or None for default).

Returns:
    Resolved :class:`MarketType`.

Raises:
    ExchangeFactoryError: If the exchange doesn't support the requested market type.

*Line: 424*

---

## Function: 

Validate the configuration for an exchange.

Args:
    exchange_name: Exchange identifier.
    api_key: API key.
    api_secret: API secret.
    passphrase: API passphrase.

Raises:
    ExchangeFactoryError: If the configuration is invalid.

*Line: 480*

---

## Function: 

Get the capabilities of an exchange.

Args:
    exchange_name: Exchange identifier.

Returns:
    :class:`ExchangeCapabilities` describing what the exchange supports.

Raises:
    ExchangeFactoryError: If the exchange is not known.

*Line: 523*

---

## Function: 

List all supported exchange names.

Returns:
    Sorted list of supported exchange identifiers.

*Line: 546*

---

## Function: 

List exchanges that support a specific capability.

Args:
    capability: Capability name (e.g. ``"supports_futures"``,
        ``"supports_perps"``, ``"requires_passphrase"``).

Returns:
    Sorted list of exchange identifiers with that capability.

*Line: 555*

---

## Function: 

Get all exchanges created by this factory.

*Line: 577*

---

## Function: 

Get the factory configuration.

*Line: 582*

---

