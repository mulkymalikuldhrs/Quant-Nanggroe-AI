# types.market

## Class: 

Supported timeframes for OHLCV data.

*Line: 16*

---

## Class: 

Open-High-Low-Close-Volume candlestick data.

This is the fundamental market data type used across all analysis engines.
All prices are in quote currency; volume is in base currency units.

**Methods:** high_must_be_highest, low_must_be_lowest

*Line: 29*

---

## Class: 

Real-time ticker data for a trading symbol.

Provides the latest price, volume, and bid/ask information.

*Line: 59*

---

## Class: 

A single price level in an order book.

*Line: 82*

---

## Class: 

Order book snapshot for a trading symbol.

Contains bid and ask levels sorted by price (bids descending, asks ascending).

*Line: 88*

---

## Class: 

Aggregated market data container for a symbol.

Combines OHLCV history, current ticker, and order book
into a single data structure for agent consumption.

*Line: 104*

---

## Function: 

Validate that high is >= open, close, low when available.

*Line: 46*

---

## Function: 

Validate that low is <= open, close, high when available.

*Line: 52*

---

