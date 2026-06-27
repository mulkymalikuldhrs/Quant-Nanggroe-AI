# exchange.polymarket_broker

## Class: 

Represents a Polymarket prediction market.

*Line: 64*

---

## Class: 

Result from placing an order on Polymarket.

*Line: 82*

---

## Class: 

Wallet configuration for Polygon network.

*Line: 90*

---

## Class: 

Low-level Polymarket CLOB REST API client.

Handles authentication (EIP-712), API key management, and raw
HTTP requests to the Polymarket CLOB endpoints.

Parameters
----------
base_url:
    CLOB API base URL.
wallet_config:
    Wallet configuration for signing.
api_key:
    Optional API key (can be derived from wallet).

**Methods:** __init__, _build_headers

*Line: 105*

---

## Class: 

Polymarket prediction market broker implementing ExchangeInterface.

Provides full trading capabilities via the Polymarket CLOB API,
including market browsing, order placement, position tracking,
and wallet integration for the Polygon network.

Parameters
----------
config:
    Exchange configuration. ``exchange_id`` should be ``"polymarket"``.
    ``api_key`` is the Polymarket API key.
    ``api_secret`` is used as the private key for wallet signing.
    ``sandbox`` should be ``True`` for the staging environment.

Examples
--------
.. code-block:: python

    config = ExchangeConfig(
        exchange_id="polymarket",
        api_key="YOUR_API_KEY_HERE",
        api_secret="YOUR_API_SECRET_HERE",
        sandbox=True,
    )
    broker = PolymarketBroker(config)
    await broker.connect()
    markets = await broker.get_markets()

**Methods:** __init__, is_connected, state, name, _require_client, _parse_outcome_prices, __repr__

*Line: 241*

---

## Function: 

*Line: 124*

---

## Function: 

Build request headers with API key if available.

*Line: 151*

---

## Function: 

*Line: 271*

---

## Function: 

*Line: 378*

---

## Function: 

*Line: 382*

---

## Function: 

*Line: 386*

---

## Function: 

Ensure the CLOB client is initialized.

*Line: 993*

---

## Function: 

Parse outcome prices from API response.

*Line: 1003*

---

## Function: 

*Line: 1014*

---

