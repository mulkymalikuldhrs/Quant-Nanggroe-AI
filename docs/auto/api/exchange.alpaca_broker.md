# exchange.alpaca_broker

## Class: 

Circuit breaker to prevent cascading failures.

Opens after ``max_errors`` consecutive errors, preventing
further requests until the cooldown period expires.

Parameters
----------
max_errors:
    Consecutive errors before opening.
cooldown_seconds:
    Seconds to wait before allowing a retry when open.

**Methods:** __init__, is_open, record_success, record_error, reset

*Line: 117*

---

## Class: 

Alpaca trading broker implementing ExchangeInterface.

Provides full trading capabilities via the Alpaca paper/live API,
including order placement, cancellation, position tracking, and
portfolio management.

Parameters
----------
config:
    Exchange configuration. ``exchange_id`` should be ``"alpaca"``.
    ``api_key`` is the Alpaca API key.
    ``api_secret`` is the Alpaca API secret.
    ``sandbox`` should be ``True`` for paper trading.

Examples
--------
.. code-block:: python

    config = ExchangeConfig(
        exchange_id="alpaca",
        api_key="YOUR_API_KEY_HERE",
        api_secret="YOUR_API_SECRET_HERE",
        sandbox=True,  # Paper trading
    )
    broker = AlpacaBroker(config)
    await broker.connect()
    order = await broker.place_order(
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=10,
    )

**Methods:** __init__, is_connected, state, name, _check_circuit_breaker, _require_client, _require_data_client, _alpaca_order_to_order, _alpaca_position_to_position, __repr__

*Line: 177*

---

## Function: 

*Line: 131*

---

## Function: 

Whether the circuit breaker is currently open.

*Line: 139*

---

## Function: 

Record a successful operation.

*Line: 148*

---

## Function: 

Record a failed operation.

*Line: 154*

---

## Function: 

Reset the circuit breaker.

*Line: 166*

---

## Function: 

*Line: 212*

---

## Function: 

*Line: 304*

---

## Function: 

*Line: 308*

---

## Function: 

*Line: 312*

---

## Function: 

Check if the circuit breaker is open.

Raises
------
ExchangeError
    If the circuit breaker is open.

*Line: 317*

---

## Function: 

Ensure the trading client is initialized.

*Line: 898*

---

## Function: 

Ensure the data client is initialized.

*Line: 906*

---

## Function: 

Convert an Alpaca order object to our Order model.

Parameters
----------
raw:
    Alpaca order object (from ``alpaca-py``).
strategy_name:
    Optional strategy name.
agent_name:
    Optional agent name.
notes:
    Optional notes.

Returns
-------
Order

*Line: 915*

---

## Function: 

Convert an Alpaca position object to our Position model.

Parameters
----------
raw:
    Alpaca position object.

Returns
-------
Position or None

*Line: 990*

---

## Function: 

*Line: 1029*

---

