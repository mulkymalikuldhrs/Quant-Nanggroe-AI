# exchange.quantdinger_factory

## Class: 

Supported market types for data source routing.

*Line: 51*

---

## Class: 

Abstract base class for QuantDinger-style exchange adapters.

Each adapter provides a consistent interface for a specific exchange,
wrapping the CCXT implementation with additional capabilities.

**Methods:** get_exchange_name, get_supported_symbols

*Line: 64*

---

## Class: 

Generic CCXT-based exchange adapter.

Wraps the existing CCXTBroker or uses ccxt directly for data access.

**Methods:** __init__, get_exchange_name, get_supported_symbols

*Line: 127*

---

## Class: 

Binance exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 226*

---

## Class: 

Bybit exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 237*

---

## Class: 

OKX exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 247*

---

## Class: 

KuCoin exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 257*

---

## Class: 

Kraken exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 267*

---

## Class: 

Gate.io exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 277*

---

## Class: 

Bitfinex exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 287*

---

## Class: 

Bitget exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 297*

---

## Class: 

Coinbase exchange adapter.

**Methods:** __init__, get_supported_symbols

*Line: 307*

---

## Class: 

US Stock data adapter using yfinance.

**Methods:** get_exchange_name, get_supported_symbols

*Line: 321*

---

## Class: 

CN Stock (A-Share) data adapter using akshare.

**Methods:** get_exchange_name, get_supported_symbols

*Line: 387*

---

## Class: 

Futures data adapter (uses yfinance for futures quotes).

**Methods:** get_exchange_name, get_supported_symbols

*Line: 440*

---

## Class: 

Forex data adapter (uses yfinance for forex quotes).

**Methods:** get_exchange_name, get_supported_symbols

*Line: 492*

---

## Class: 

Factory for creating multi-exchange and multi-market data adapters.

Follows the QuantDinger architecture pattern to provide consistent
access to 9+ crypto exchanges and multiple data source types.

Usage::

    factory = QuantDingerFactory()

    # Create a Binance adapter
    binance = factory.create_exchange_adapter("binance")
    klines = await binance.get_kline("BTC/USDT", "1h", 100)

    # Create a data source by market type
    stock_source = factory.create_data_source("us_stock")
    prices = await stock_source.get_ticker_price("AAPL")

    # Use convenience method
    klines = await factory.get_kline("crypto", "BTC/USDT", "1h", 100)

**Methods:** __init__, create_exchange_adapter, create_data_source, get_supported_exchanges, get_supported_market_types

*Line: 573*

---

## Function: 

Return the exchange name identifier.

*Line: 115*

---

## Function: 

Return list of commonly supported symbols.

*Line: 119*

---

## Function: 

*Line: 133*

---

## Function: 

*Line: 213*

---

## Function: 

*Line: 216*

---

## Function: 

*Line: 229*

---

## Function: 

*Line: 232*

---

## Function: 

*Line: 240*

---

## Function: 

*Line: 243*

---

## Function: 

*Line: 250*

---

## Function: 

*Line: 253*

---

## Function: 

*Line: 260*

---

## Function: 

*Line: 263*

---

## Function: 

*Line: 270*

---

## Function: 

*Line: 273*

---

## Function: 

*Line: 280*

---

## Function: 

*Line: 283*

---

## Function: 

*Line: 290*

---

## Function: 

*Line: 293*

---

## Function: 

*Line: 300*

---

## Function: 

*Line: 303*

---

## Function: 

*Line: 310*

---

## Function: 

*Line: 313*

---

## Function: 

*Line: 380*

---

## Function: 

*Line: 383*

---

## Function: 

*Line: 433*

---

## Function: 

*Line: 436*

---

## Function: 

*Line: 485*

---

## Function: 

*Line: 488*

---

## Function: 

*Line: 537*

---

## Function: 

*Line: 540*

---

## Function: 

*Line: 595*

---

## Function: 

Create an exchange adapter by name.

Args:
    exchange_name: Exchange identifier (e.g., "binance", "bybit").
    config: Optional exchange-specific configuration.

Returns:
    BaseExchangeAdapter instance.

Raises:
    ValueError: If exchange_name is not supported.

*Line: 598*

---

## Function: 

Create a data source adapter by market type.

Args:
    market_type: Market type (crypto, us_stock, cn_stock, futures, forex).
    config: Optional configuration.

Returns:
    BaseExchangeAdapter instance for the market type.

Raises:
    ValueError: If market_type is not supported.

*Line: 637*

---

## Function: 

Get list of supported exchange names.

*Line: 734*

---

## Function: 

Get list of supported market types.

*Line: 739*

---

