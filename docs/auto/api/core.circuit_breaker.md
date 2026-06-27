# core.circuit_breaker

## Class: 

Circuit breaker states.

*Line: 38*

---

## Class: 

Thread-safe circuit breaker with configurable threshold and timeout.

Parameters
----------
name : str
    Human-readable name used in log messages.
failure_threshold : int
    Number of consecutive failures before the circuit opens.
recovery_timeout : float
    Seconds to wait in OPEN state before transitioning to HALF_OPEN.
half_open_max : int
    Number of successful calls in HALF_OPEN needed to close the circuit.

**Methods:** __init__, state, is_open, failure_count, success_count, can_execute, record_success, record_failure, reset, to_dict, _transition

*Line: 48*

---

## Class: 

Wrap an async callable with circuit-breaker protection.

Parameters
----------
breaker : CircuitBreaker
    The circuit breaker instance to use.
fallback : callable
    A zero-argument async callable (or plain callable) returned when
    the circuit is OPEN.

Usage::

    cb = CircuitBreaker(name="nim_client", failure_threshold=3)
    mw = CircuitBreakerMiddleware(cb, fallback=lambda: default_response())

    result = await mw.call(external_fetch_func, arg1, arg2)

**Methods:** __init__

*Line: 204*

---

## Function: 

*Line: 63*

---

## Function: 

Current state, automatically transitioning OPEN -> HALF_OPEN after timeout.

*Line: 85*

---

## Function: 

True when the circuit is OPEN (calls should be rejected).

*Line: 93*

---

## Function: 

*Line: 106*

---

## Function: 

*Line: 110*

---

## Function: 

Return True if a call is allowed to proceed.

*Line: 115*

---

## Function: 

Record a successful call.

*Line: 121*

---

## Function: 

Record a failed call.

*Line: 139*

---

## Function: 

Force the circuit back to CLOSED state.

*Line: 162*

---

## Function: 

Return a serializable snapshot of the circuit state.

*Line: 169*

---

## Function: 

*Line: 183*

---

## Function: 

*Line: 223*

---

