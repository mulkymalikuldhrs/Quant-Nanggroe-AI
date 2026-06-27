# exchange.mt5_broker

## Class: 

MetaTrader 5 account information.

*Line: 60*

---

## Class: 

MetaTrader 5 symbol information.

*Line: 80*

---

## Class: 

MetaTrader 5 position information.

*Line: 96*

---

## Class: 

MetaTrader 5 broker implementing ExchangeInterface.

Provides full trading capabilities via the MetaTrader5 Python API,
including order placement, position management, market data, and
account information.

Parameters
----------
config:
    Exchange configuration. ``exchange_id`` should be ``"mt5"``.
    ``api_key`` should contain the login ID (as string).
    ``api_secret`` should contain the password.
    ``options["server"]`` should contain the server name.
    ``options["path"]`` should contain the terminal path (optional).

Examples
--------
.. code-block:: python

    config = ExchangeConfig(
        exchange_id="mt5",
        api_key="YOUR_API_KEY_HERE",
        api_secret="YOUR_API_SECRET_HERE",
        options={"server": "MetaQuotes-Demo"},
    )
    broker = MT5Broker(config)
    await broker.connect()
    account = await broker.get_account_info()

**Methods:** __init__, is_connected, state, name, _require_mt5, _get_timeframe_enum, __repr__

*Line: 134*

---

## Function: 

*Line: 165*

---

## Function: 

*Line: 268*

---

## Function: 

*Line: 277*

---

## Function: 

*Line: 281*

---

## Function: 

Ensure MT5 is initialized and connected.

*Line: 1080*

---

## Function: 

Get MT5 timeframe enum value.

*Line: 1089*

---

## Function: 

*Line: 1108*

---

