# agents.tools.market_data

## Class: 

Simple TTL-based in-memory cache for market data.

**Methods:** __init__, get, set, clear

*Line: 85*

---

## Function: 

Determine if a symbol refers to a crypto asset.

*Line: 110*

---

## Function: 

Determine if a symbol refers to a forex pair.

*Line: 123*

---

## Function: 

Normalize a yfinance/ccxt DataFrame into our standard OHLCV dict.

*Line: 128*

---

## Class: 

Unified market data tool for agent consumption.

Routes data requests to the appropriate backend:
  - Crypto symbols → ccxt (Binance by default)
  - Stock symbols  → yfinance
  - Forex symbols  → yfinance

Features:
  - In-memory TTL cache to reduce API calls
  - Data normalization across all sources
  - Graceful fallback when a data source is unavailable
  - Trust-score metadata per data source

**Methods:** __init__, circuit_breaker, _normalize_crypto_symbol

*Line: 166*

---

## Function: 

Get or create the default MarketDataTool instance.

*Line: 505*

---

## Function: 

*Line: 88*

---

## Function: 

*Line: 92*

---

## Function: 

*Line: 102*

---

## Function: 

*Line: 106*

---

## Function: 

Initialize the MarketDataTool.

Args:
    cache_ttl: Cache time-to-live in seconds (default 60).

*Line: 182*

---

## Function: 

Access the circuit breaker for introspection or manual reset.

*Line: 195*

---

## Function: 

Normalize a crypto symbol to ccxt format.

Examples:
    'BTC-USD'  → 'BTC/USDT'
    'BTC/USD'  → 'BTC/USDT'
    'BTCUSDT'  → 'BTC/USDT'
    'BTC/USDT' → 'BTC/USDT'

*Line: 472*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 24*

---

## Function: 

*Line: 28*

---

