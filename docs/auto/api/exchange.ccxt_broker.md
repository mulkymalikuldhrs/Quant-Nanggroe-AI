# exchange.ccxt_broker

## Class: 

CCXT-based exchange broker supporting 100+ cryptocurrency exchanges.

This implementation wraps ``ccxt.async_support`` exchange classes and
translates between CCXT's data structures and Quant Nanggroe's Pydantic
domain types.

Parameters
----------
config:
    :class:`ExchangeConfig` with API credentials and settings.

Examples
--------
.. code-block:: python

    config = ExchangeConfig(
        exchange_id="binance",
        api_key="YOUR_API_KEY_HERE",
        api_secret="YOUR_API_SECRET_HERE",
        sandbox=True,
    )
    broker = CCXTBroker(config)
    await broker.connect()
    ticker = await broker.get_ticker("BTC/USDT")

**Methods:** __init__, is_connected, state, name, _require_exchange, _ccxt_order_to_order, _ccxt_position_to_position

*Line: 102*

---

## Function: 

*Line: 129*

---

## Function: 

*Line: 234*

---

## Function: 

*Line: 238*

---

## Function: 

*Line: 242*

---

## Function: 

Return the exchange instance or raise ConnectionError.

*Line: 325*

---

## Function: 

Convert a CCXT order dict to our Order model.

*Line: 784*

---

## Function: 

Convert a CCXT position dict to our Position model.

*Line: 830*

---

