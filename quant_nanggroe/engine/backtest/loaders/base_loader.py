"""Base data loader with retry/budget helpers and protocol definition.

Provides:
  - ``BaseLoader``: Abstract base class for all data loaders
  - ``NoAvailableSourceError``: Exception for unavailable data sources
  - ``validate_date_range``: Date validation helper
  - ``check_budget`` / ``retry_with_budget``: Bounded retry for flaky APIs

Ported from Vibe-Trading's ``backtest.loaders.base``.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, TypeVar

import pandas as pd


class NoAvailableSourceError(Exception):
    """Raised when no data source is available for a given market."""


def validate_date_range(start_date: str, end_date: str) -> None:
    """Validate that start_date <= end_date.

    Args:
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).

    Raises:
        ValueError: If dates are invalid or start > end.
    """
    try:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
    except Exception as exc:
        raise ValueError(
            f"Invalid date format: start={start_date!r}, end={end_date!r}"
        ) from exc
    if start > end:
        raise ValueError(f"start_date ({start_date}) > end_date ({end_date})")


# ── Bounded retry / budget helpers ──

DEFAULT_BACKOFF: tuple[float, ...] = (0.5, 1.5, 4.0)
DEFAULT_MAX_RETRIES = 3


def check_budget(
    deadline: float, label: str, budget_s: Optional[float] = None
) -> None:
    """Raise ``TimeoutError`` if the monotonic clock has crossed ``deadline``.

    Use this between pages of a paginated fetch to fail fast instead of
    grinding through more requests once the wall-clock budget is gone.

    Args:
        deadline: ``time.monotonic()`` instant past which we abort.
        label: Free-form label used in the exception message.
        budget_s: Original budget in seconds, included in the message when present.

    Raises:
        TimeoutError: If deadline has been exceeded.
    """
    if time.monotonic() > deadline:
        suffix = (
            f" exceeded {budget_s:.0f}s budget" if budget_s is not None else " exceeded budget"
        )
        raise TimeoutError(f"{label}{suffix}")


_T = TypeVar("_T")


def retry_with_budget(
    fn: Callable[[], _T],
    *,
    transient: type[BaseException] | tuple[type[BaseException], ...],
    deadline: float,
    label: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: tuple[float, ...] = DEFAULT_BACKOFF,
) -> _T:
    """Call ``fn`` with a bounded retry budget on declared transient errors.

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
    """
    if len(backoff) < max_retries:
        raise ValueError(
            f"backoff has {len(backoff)} entries; need >= max_retries ({max_retries})"
        )
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except transient as exc:
            remaining = deadline - time.monotonic()
            if attempt == max_retries or remaining <= 0:
                raise TimeoutError(
                    f"{label} failed after {attempt + 1} attempt(s): {exc}"
                ) from exc
            time.sleep(min(backoff[attempt], max(0.0, remaining)))
    raise AssertionError("unreachable: retry loop must return or raise")  # pragma: no cover


class BaseLoader(ABC):
    """Abstract base class for all data source loaders.

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
    """

    name: str = "base"
    markets: set[str] = set()
    requires_auth: bool = False

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this data source is usable.

        Returns:
            True if the data source is available (token present, network ok, etc.).
        """

    @abstractmethod
    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        *,
        interval: str = "1D",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for the given codes.

        Args:
            codes: List of instrument symbols.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            interval: Bar size (1m/5m/15m/30m/1H/4H/1D).
            fields: Optional extra fields to fetch.

        Returns:
            Mapping of ``{symbol: DataFrame(trade_date, open, high, low, close, volume)}``.
        """
