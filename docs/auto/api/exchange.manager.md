# exchange.manager

## Class: 

Role assigned to a registered exchange.

*Line: 62*

---

## Class: 

Internal record for a registered exchange.

*Line: 74*

---

## Class: 

Multi-exchange manager with failover and portfolio aggregation.

Parameters
----------
health_check_interval:
    Seconds between automatic health checks (0 = disabled).
max_errors:
    Mark an exchange unhealthy after this many consecutive errors.

**Methods:** __init__, register, unregister, registered_exchanges, primary_name, _get_trading_exchange, _get_data_exchange, _record_error, _record_success, _promote_failover, get_status

*Line: 93*

---

## Function: 

*Line: 104*

---

## Function: 

Register an exchange connection.

Args:
    name: Unique name for this exchange (e.g. ``"binance"``).
    exchange: An :class:`ExchangeInterface` implementation.
    role: One of ``"primary"``, ``"failover"``, ``"data_only"``.
    priority: Lower = higher priority in failover chain.

Raises:
    ValueError: If an exchange with the same name is already registered.

*Line: 123*

---

## Function: 

Remove a registered exchange.

Args:
    name: Exchange name to remove.

*Line: 172*

---

## Function: 

Names of all registered exchanges.

*Line: 204*

---

## Function: 

Name of the current primary exchange.

*Line: 209*

---

## Function: 

Get the best available trading exchange (primary or failover).

Returns:
    The highest-priority healthy exchange, or ``None``.

*Line: 269*

---

## Function: 

Get the best available data exchange.

Args:
    preferred: Preferred exchange name (tries this first).

Returns:
    The preferred or best available healthy exchange.

*Line: 294*

---

## Function: 

Record an error and potentially mark the exchange unhealthy.

*Line: 320*

---

## Function: 

Reset error count on a successful operation.

*Line: 336*

---

## Function: 

Promote the best failover exchange to primary.

*Line: 343*

---

## Function: 

Get the status of all registered exchanges.

Returns:
    Mapping of exchange name → status dict with keys:
    ``role``, ``connected``, ``healthy``, ``error_count``,
    ``last_health_check``.

*Line: 870*

---

