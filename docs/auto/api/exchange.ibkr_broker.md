# exchange.ibkr_broker

## Class: 

IBKR contract specification.

*Line: 61*

---

## Class: 

IBKR account summary data.

*Line: 74*

---

## Class: 

IBKR execution report.

*Line: 88*

---

## Class: 

Interactive Brokers broker implementing ExchangeInterface.

Provides full trading capabilities via the IB TWS/Gateway API,
including contract lookup, order placement, position management,
and account information.

Parameters
----------
config:
    Exchange configuration. ``exchange_id`` should be ``"ibkr"``.
    ``api_key`` is the TWS client ID (default: 1).
    ``api_secret`` is not used (IB uses socket connection).
    ``options["host"]`` is the TWS/Gateway host (default: "127.0.0.1").
    ``options["port"]`` is the TWS/Gateway port (default: 7497 for paper).
    ``options["client_id"]`` is the client ID (default: 1).
    ``options["timeout"]`` is the connection timeout in seconds.
    ``sandbox`` should be ``True`` for paper trading (port 7497).

Examples
--------
.. code-block:: python

    config = ExchangeConfig(
        exchange_id="ibkr",
        sandbox=True,
        options={"host": "127.0.0.1", "port": 7497, "client_id": 1},
    )
    broker = IBKRBroker(config)
    await broker.connect()
    account = await broker.get_account_summary()

**Methods:** __init__, is_connected, state, name, _require_ib, _map_ib_status, _map_timeframe_to_bar, __repr__

*Line: 105*

---

## Function: 

*Line: 138*

---

## Function: 

*Line: 215*

---

## Function: 

*Line: 224*

---

## Function: 

*Line: 228*

---

## Function: 

Ensure IB client is initialized and connected.

*Line: 867*

---

## Function: 

Map IBKR order status to OrderStatus.

*Line: 877*

---

## Function: 

Map TimeFrame to IBKR bar size string.

*Line: 894*

---

## Function: 

*Line: 909*

---

