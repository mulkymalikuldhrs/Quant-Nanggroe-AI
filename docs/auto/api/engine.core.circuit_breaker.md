# engine.core.circuit_breaker

## Class: 

Circuit breaker states.

*Line: 46*

---

## Class: 

Metrics for a single circuit breaker instance.

**Methods:** success_rate

*Line: 54*

---

## Class: 

Raised when a circuit breaker blocks a call.

**Methods:** __init__

*Line: 71*

---

## Class: 

Circuit breaker with CLOSED, OPEN, HALF_OPEN states.

Attributes:
    failure_threshold: Consecutive failures before opening the circuit.
    recovery_timeout: Seconds to wait before transitioning OPEN → HALF_OPEN.
    half_open_max_calls: Max calls allowed in HALF_OPEN state before deciding.
    name: Identifier for this circuit breaker (for logging).

**Methods:** __init__, state, _transition_to, record_success, record_failure, allow_request, reset, get_metrics, protect

*Line: 82*

---

## Class: 

Retry policy with exponential backoff and jitter.

Attributes:
    max_retries: Maximum number of retry attempts.
    base_delay: Base delay in seconds between retries.
    max_delay: Maximum delay cap in seconds.
    backoff_factor: Multiplier for exponential backoff.
    jitter: Whether to add random jitter to delays.
    retryable_exceptions: Tuple of exception types that trigger retry.

**Methods:** compute_delay, execute

*Line: 229*

---

## Class: 

Combines circuit breaker and retry policy for resilient calls.

Usage::

    caller = ResilientCaller(
        circuit_breaker=CircuitBreaker(failure_threshold=3),
        retry_policy=RetryPolicy(max_retries=2),
    )
    result = caller.call(request_fn, arg1, arg2)

**Methods:** __init__, call, get_status

*Line: 335*

---

## Function: 

Get or create a named circuit breaker (singleton per name).

*Line: 430*

---

## Function: 

Decorator that protects a function with a named circuit breaker.

Usage::

    @protect_with_circuit_breaker("data_provider", failure_threshold=5)
    def fetch_data():
        ...

*Line: 445*

---

## Function: 

*Line: 65*

---

## Function: 

*Line: 74*

---

## Function: 

*Line: 92*

---

## Function: 

Current state, auto-transitioning OPEN → HALF_OPEN if timeout expired.

*Line: 112*

---

## Function: 

Transition to a new state with logging.

*Line: 121*

---

## Function: 

Record a successful call.

*Line: 135*

---

## Function: 

Record a failed call.

*Line: 150*

---

## Function: 

Check if a request is allowed through the circuit breaker.

*Line: 166*

---

## Function: 

Reset the circuit breaker to CLOSED state.

*Line: 177*

---

## Function: 

Return current circuit breaker metrics.

*Line: 186*

---

## Function: 

Decorator that wraps a function with circuit breaker protection.

Usage::

    @circuit_breaker.protect
    def call_api():
        ...

*Line: 201*

---

## Function: 

Compute delay for a given retry attempt.

*Line: 247*

---

## Function: 

Execute a function with retry logic.

Args:
    func: Function to execute.
    *args: Positional arguments for func.
    on_retry: Optional callback called with (attempt_number, exception).
    **kwargs: Keyword arguments for func.

Returns:
    Result of func.

Raises:
    Last exception if all retries fail.

*Line: 255*

---

## Function: 

*Line: 347*

---

## Function: 

Execute a function with circuit breaker + retry.

First checks circuit breaker state. If allowed, attempts the call
with retry policy. Records success/failure on circuit breaker.

Raises:
    CircuitBreakerError: If circuit is open.
    Last exception: If all retries fail.

*Line: 357*

---

## Function: 

Return combined status of circuit breaker and retry policy.

*Line: 412*

---

## Function: 

*Line: 211*

---

