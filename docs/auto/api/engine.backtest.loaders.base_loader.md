# engine.backtest.loaders.base_loader

## Class: 

Raised when no data source is available for a given market.

*Line: 21*

---

## Function: 

Validate that start_date <= end_date.

Args:
    start_date: Start date string (YYYY-MM-DD).
    end_date: End date string (YYYY-MM-DD).

Raises:
    ValueError: If dates are invalid or start > end.

*Line: 25*

---

## Function: 

Raise ``TimeoutError`` if the monotonic clock has crossed ``deadline``.

Use this between pages of a paginated fetch to fail fast instead of
grinding through more requests once the wall-clock budget is gone.

Args:
    deadline: ``time.monotonic()`` instant past which we abort.
    label: Free-form label used in the exception message.
    budget_s: Original budget in seconds, included in the message when present.

Raises:
    TimeoutError: If deadline has been exceeded.

*Line: 52*

---

## Function: 

Call ``fn`` with a bounded retry budget on declared transient errors.

Between attempts sleeps ``min(backoff[attempt], remaining_budget)`` so a
short remaining budget never spends the full backoff. The terminal
transient failure is wrapped in ``TimeoutError``, preserving the original
exception as ``__cause__``.

Args:
    fn: Zero-arg callable producing the result.
    transient: Exception class(es) considered transient and retryable.
    deadline: ``time.monotonic()`` instant past which retries are aborted.
    label: Free-form label for the TimeoutError message.
    max_retries: Additional attempts after the first call.
    backoff: Per-retry sleep seconds.

Returns:
    Whatever ``fn`` returns.

Raises:
    ValueError: ``backoff`` is shorter than ``max_retries``.
    TimeoutError: All retries exhausted or the deadline crossed.
    Any non-transient exception: Propagated unchanged from ``fn``.

*Line: 78*

---

## Class: 

Abstract base class for all data source loaders.

Subclasses must implement:
  - ``name``: Loader identifier string
  - ``markets``: Set of market types this loader supports
  - ``requires_auth``: Whether authentication is required
  - ``is_available()``: Check if the loader can be used
  - ``fetch()``: Fetch OHLCV data

Attributes:
    name: Loader identifier (e.g. ``"yfinance"``, ``"ccxt"``).
    markets: Set of market types this loader supports.
    requires_auth: Whether authentication is required.

**Methods:** is_available, fetch

*Line: 127*

---

## Function: 

Check whether this data source is usable.

Returns:
    True if the data source is available (token present, network ok, etc.).

*Line: 148*

---

## Function: 

Fetch OHLCV data for the given codes.

Args:
    codes: List of instrument symbols.
    start_date: Start date (YYYY-MM-DD).
    end_date: End date (YYYY-MM-DD).
    interval: Bar size (1m/5m/15m/30m/1H/4H/1D).
    fields: Optional extra fields to fetch.

Returns:
    Mapping of ``{symbol: DataFrame(trade_date, open, high, low, close, volume)}``.

*Line: 156*

---

