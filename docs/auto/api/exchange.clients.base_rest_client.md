# exchange.clients.base_rest_client

## Class: 

Exchange capability flags.

*Line: 23*

---

## Class: 

Configuration for REST exchange client.

*Line: 33*

---

## Class: 

Standardized order request.

*Line: 45*

---

## Class: 

Standardized order result.

*Line: 59*

---

## Class: 

Account balance information.

*Line: 73*

---

## Class: 

Position information.

*Line: 81*

---

## Class: 

Single orderbook entry.

*Line: 92*

---

## Class: 

Orderbook snapshot.

*Line: 98*

---

## Class: 

Single kline/candlestick bar.

*Line: 106*

---

## Class: 

Abstract base class for exchange REST API clients.

All exchange clients inherit from this class, which provides:
- Rate limiting (token bucket)
- Request signing interface
- Error handling with retries
- Capability detection
- Unified order/balance/position models

Usage::

    class BinanceClient(BaseRestClient):
        exchange_id = "binance"
        capabilities = ExchangeCapability.SPOT | ExchangeCapability.FUTURES

        async def place_order(self, order: OrderRequest) -> OrderResult:
            ...

**Methods:** __init__, has_spot, has_futures, has_perpetuals, has_websocket, _sign

*Line: 116*

---

## Function: 

*Line: 139*

---

## Function: 

*Line: 146*

---

## Function: 

*Line: 150*

---

## Function: 

*Line: 154*

---

## Function: 

*Line: 158*

---

## Function: 

Sign request parameters with HMAC-SHA256.

*Line: 181*

---

