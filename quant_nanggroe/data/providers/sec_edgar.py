"""SEC EDGAR financial data provider.

Fetches company filings and XBRL financial facts from SEC public APIs.
No API key required. Rate-limited to 10 requests/sec per SEC policy.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime
from enum import StrEnum
from typing import Any, List, Optional

import httpx

from quant_nanggroe.data.providers.base import DataProvider

logger = logging.getLogger(__name__)

SEC_BASE = "https://data.sec.gov"
TICKER_URL = f"{SEC_BASE}/files/company_tickers.json"


class FilingType(StrEnum):
    """SEC filing type identifiers."""

    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"


class SECEdgarError(Exception):
    """SEC EDGAR provider error."""

    pass


def _parse_cik(cik: str | int) -> str:
    """Normalize a CIK value to 10-digit zero-padded string.

    Accepts integer (320193), string number ("320193"), or
    already-padded string ("0000320193").
    """
    if isinstance(cik, int):
        return f"{cik:010d}"
    clean = cik.strip()
    if clean.isdigit():
        return clean.zfill(10)
    return clean


class SECEdgarProvider(DataProvider):
    """SEC EDGAR data provider.

    Fetches company filings and financial data from SEC public EDGAR API.
    No API key required. Follows SEC rate-limiting guidelines.

    Parameters
    ----------
    user_email:
        Contact email for SEC User-Agent header. Falls back to
        ``QNAI_SEC_USER_EMAIL`` env var, then ``dev@quant-nanggroe.local``.
    user_name:
        Optional organization name for User-Agent.
    priority:
        Provider priority in the data provider registry (default 35).
    """

    RATE_LIMIT: float = 10.0  # requests per second

    def __init__(
        self,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        priority: int = 35,
    ) -> None:
        super().__init__(name="sec_edgar", priority=priority)
        self._user_email = (
            user_email
            or os.environ.get("QNAI_SEC_USER_EMAIL")
            or "dev@quant-nanggroe.local"
        )
        self._user_name = user_name or ""
        self._client: httpx.AsyncClient | None = None
        self._ticker_cache: dict[str, str] | None = None
        self._last_request: float = 0.0

    def __repr__(self) -> str:
        return f"SECEdgarProvider(name={self.name!r}, priority={self.priority})"

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": self._get_user_agent(),
                    "Accept": "application/json",
                },
            )
        return self._client

    def _get_user_agent(self) -> str:
        """Build the User-Agent header value."""
        return f"QuantNanggroeAI/1.0 ({self._user_email})"

    async def _rate_limited_request(self, url: str) -> Any:
        """Make a rate-limited HTTP request.

        Enforces SEC's recommended 10 requests/second minimum interval.
        Returns the parsed JSON response.

        Raises
        ------
        SECEdgarError
            On HTTP or network errors.
        """
        now = time.monotonic()
        elapsed = now - self._last_request
        min_interval = 1.0 / self.RATE_LIMIT
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request = time.monotonic()

        try:
            resp = await self._http.get(url)
            resp.raise_for_status()
            return resp.json()
        except httpx.RequestError as e:
            raise SECEdgarError(f"SEC EDGAR request failed: {e}") from e
        except httpx.HTTPStatusError as e:
            raise SECEdgarError(
                f"SEC EDGAR returned {e.response.status_code}: {e.response.text[:200]}"
            ) from e

    async def _resolve_cik(self, ticker: str) -> Optional[str]:
        """Resolve a ticker symbol to a 10-digit CIK number.

        Fetches and caches the SEC company ticker map.
        Returns ``None`` if the ticker is not found.
        """
        if self._ticker_cache is None:
            data = await self._rate_limited_request(TICKER_URL)
            self._ticker_cache = {
                entry["ticker"].upper(): f"{entry['cik_str']:010d}"
                for entry in data.values()
            }
        return self._ticker_cache.get(ticker.upper())

    async def get_filings(
        self,
        cik: str,
        filing_type: Optional[str] = None,
        limit: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[dict[str, Any]]:
        """Fetch SEC filings for a company.

        Parameters
        ----------
        cik:
            Ticker symbol or CIK number.
        filing_type:
            Optional form type filter (e.g. ``"10-K"``, ``"10-Q"``).
        limit:
            Max number of filings to return.
        start:
            Filter filings on or after this date.
        end:
            Filter filings on or before this date.

        Returns
        -------
        List of filing dicts with keys like ``form``, ``filingDate``, etc.
        """
        padded = await self._resolve_cik(cik)
        if padded is None:
            return []

        url = f"{SEC_BASE}/submissions/CIK{padded}.json"
        data = await self._rate_limited_request(url)

        recent = data.get("filings", {}).get("recent", {})
        if not recent:
            return []

        forms = recent.get("form", [])
        filings: List[dict[str, Any]] = []
        for i in range(len(forms)):
            entry = {k: recent[k][i] for k in recent if i < len(recent[k])}

            if filing_type and entry.get("form") != filing_type:
                continue

            if start or end:
                fd = entry.get("filingDate", "")
                if fd:
                    d = datetime.strptime(fd, "%Y-%m-%d")
                    if start and d < start:
                        continue
                    if end and d > end:
                        continue

            filings.append(entry)
            if limit and len(filings) >= limit:
                break

        return filings

    async def get_fundamentals(self, cik: str) -> dict[str, Any]:
        """Fetch XBRL financial facts for a company.

        Parameters
        ----------
        cik:
            Ticker symbol or CIK number.

        Returns
        -------
        Dict with GAAP taxonomy concepts under the ``"us-gaap"`` key.
        Empty dict if ticker is not found or on API error.
        """
        padded = await self._resolve_cik(cik)
        if padded is None:
            return {}

        try:
            url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{padded}.json"
            data = await self._rate_limited_request(url)
            return data.get("facts", {})
        except SECEdgarError:
            logger.warning("Failed to fetch fundamentals for %s", cik)
            return {}

    async def get_financial_statements(
        self,
        cik: str,
        statement_type: str,
        period: str = "annual",
    ) -> dict[str, Any]:
        """Extract a financial statement from XBRL facts.

        Parameters
        ----------
        cik:
            Ticker symbol or CIK number.
        statement_type:
            ``"income_statement"``, ``"balance_sheet"``, or ``"cash_flow"``.
        period:
            ``"annual"`` or ``"quarterly"``.

        Returns
        -------
        Dict mapping GAAP concept labels to their most recent value.
        Empty dict if no facts are available.
        """
        facts = await self.get_fundamentals(cik)
        if not facts:
            return {}

        us_gaap = facts.get("us-gaap", {})

        if statement_type == "income_statement":
            concepts = {
                "Revenues", "NetIncomeLoss", "OperatingIncomeLoss",
                "GrossProfit", "CostOfRevenue", "OperatingExpenses",
                "IncomeTaxExpenseBenefit", "EarningsPerShareBasic",
                "EarningsPerShareDiluted",
            }
        elif statement_type == "balance_sheet":
            concepts = {
                "Assets", "Liabilities", "StockholdersEquity",
                "CurrentAssets", "CurrentLiabilities",
                "CashAndCashEquivalentsAtCarryingValue",
                "CommonStock", "RetainedEarningsAccumulatedDeficit",
                "PropertyPlantAndEquipmentNet", "Goodwill",
            }
        elif statement_type == "cash_flow":
            concepts = {
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInInvestingActivities",
                "NetCashProvidedByUsedInFinancingActivities",
                "CashAndCashEquivalentsPeriodIncreaseDecrease",
            }
        else:
            return {}

        result: dict[str, Any] = {}
        for concept in concepts:
            if concept not in us_gaap:
                continue
            units = us_gaap[concept].get("units", {})
            for unit_key, values in units.items():
                filtered = [
                    v for v in values
                    if (period == "annual" and v.get("fp") == "FY")
                    or (period != "annual" and v.get("fp") != "FY")
                ]
                if filtered:
                    newest = max(filtered, key=lambda x: x.get("end", ""))
                    result[concept] = {
                        "label": us_gaap[concept].get("label", concept),
                        "value": newest.get("val"),
                        "unit": unit_key,
                        "end": newest.get("end"),
                        "filed": newest.get("filed"),
                    }
                    break
        return result

    async def get_insider_transactions(
        self,
        cik: str,
        limit: int = 10,
    ) -> List[dict[str, Any]]:
        """Fetch insider transaction filings (Form 4).

        Parameters
        ----------
        cik:
            Ticker symbol or CIK number.
        limit:
            Max number of transactions to return.

        Returns
        -------
        List of Form 4 filing dicts.
        """
        return await self.get_filings(cik, filing_type="4", limit=limit)

    async def health_check(self) -> bool:
        """Check if the SEC EDGAR API is reachable.

        Tries to fetch the company ticker map.
        Sets ``is_available`` and records errors.
        """
        try:
            await self._rate_limited_request(TICKER_URL)
            self.is_available = True
            return True
        except SECEdgarError as e:
            self.is_available = False
            self.mark_error(str(e))
            return False

    def mark_error(self, error_msg: str) -> None:
        """Record an error and decay the health score."""
        super().mark_error(error_msg)

    # --- DataProvider interface stubs (not applicable to EDGAR) ---

    async def get_ohlcv(self, symbol: str) -> List:
        return []

    async def get_ticker(self, symbol: str) -> None:
        return None

    async def get_orderbook(self, symbol: str) -> None:
        return None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


__all__ = [
    "SECEdgarProvider",
    "SECEdgarError",
    "FilingType",
    "_parse_cik",
]
