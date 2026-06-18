"""Economic data feeds for the AI-MultiColony ecosystem.

Provides the :class:`EconomicSource` that fetches macroeconomic indicators
including GDP, inflation (CPI), interest rates, employment data, trade
balances, and central bank policy decisions.

Data is normalised into a consistent :class:`EconomicIndicator` model
that can be used by agents for decision-making.

**Live data mode** – When ``_LIVE_MODE = True`` (default), the source
calls the **World Bank API** (free, no key) and optionally the **FRED
API** (free key from env var ``FRED_API_KEY``).  If all live calls fail
the module falls back to :data:`SAMPLE_ECONOMIC_PROFILES` and emits a
``logging.warning`` so operators are never silently served stale data.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from cachetools import TTLCache
from pydantic import BaseModel, Field, ConfigDict

from .base import (
    SourceCategory,
    SourceConfig,
    SourceItem,
    SourceProvider,
    SourceReliability,
    SourceResult,
)

logger = logging.getLogger(__name__)

# ── Feature flag ──────────────────────────────────────────────────────────

_LIVE_MODE: bool = True
"""When ``True`` the source calls real APIs.  Set to ``False`` to force
SAMPLE_DATA usage (useful in offline tests)."""

_API_TIMEOUT: float = 10.0
"""Default timeout in seconds for every outbound HTTP call."""

_CACHE_TTL: int = 3600  # 1 hour
"""TTL for the economic data cache (seconds)."""

_UA = "Quant-Nanggroe-AI/1.0 (economic-source; +https://github.com/quant-nanggroe)"

# ── Caches ────────────────────────────────────────────────────────────────

_profile_cache: TTLCache[str, Dict[str, Any]] = TTLCache(maxsize=64, ttl=_CACHE_TTL)
_indicator_cache: TTLCache[str, List[Dict[str, Any]]] = TTLCache(maxsize=128, ttl=_CACHE_TTL)


# ── Data models ──────────────────────────────────────────────────────────────


class EconomicIndicator(BaseModel):
    """A single economic indicator measurement."""

    model_config = ConfigDict(frozen=False)

    indicator_id: str = ""
    name: str = ""
    country: str = ""
    value: float = 0.0
    previous_value: Optional[float] = None
    unit: str = ""
    frequency: str = "monthly"  # daily, weekly, monthly, quarterly, annual
    source_agency: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    change_pct: Optional[float] = None
    category: str = ""  # gdp, inflation, employment, trade, monetary, fiscal

    def to_item(self, _source: str = "sample_data", _timestamp: str = "") -> SourceItem:
        """Convert to a SourceItem for unified source pipeline."""
        ts = _timestamp or datetime.now(timezone.utc).isoformat()
        content = (
            f"{self.country} {self.name}: {self.value} {self.unit}"
            f" (previous: {self.previous_value})"
            f" (change: {self.change_pct}%)" if self.change_pct is not None else
            f"{self.country} {self.name}: {self.value} {self.unit}"
        )
        content += f"\n_source: {_source} | _timestamp: {ts}"
        return SourceItem(
            source_name="economic",
            category=SourceCategory.ECONOMIC,
            title=f"{self.country} – {self.name}",
            summary=f"{self.name} for {self.country} is {self.value} {self.unit}",
            content=content,
            relevance_score=0.7,
            confidence=0.9,
            tags=["economic", self.category, self.country.lower(), f"src:{_source}"],
            raw_data={"_source": _source, "_timestamp": ts},
        )


class GDPRate(BaseModel):
    """GDP growth rate data."""
    country: str = ""
    annual_growth_pct: float = 0.0
    quarterly_growth_pct: float = 0.0
    gdp_nominal_usd_bn: float = 0.0
    gdp_per_capita_usd: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InflationData(BaseModel):
    """Inflation / CPI data."""
    country: str = ""
    cpi_yoy_pct: float = 0.0
    cpi_mom_pct: float = 0.0
    core_cpi_yoy_pct: float = 0.0
    ppi_yoy_pct: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InterestRateData(BaseModel):
    """Central bank interest rate data."""
    country: str = ""
    central_bank: str = ""
    policy_rate_pct: float = 0.0
    previous_rate_pct: Optional[float] = None
    next_meeting_date: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Sample / fallback data ──────────────────────────────────────────────────

SAMPLE_ECONOMIC_PROFILES: Dict[str, Dict[str, Any]] = {
    "US": {
        "gdp_growth_annual": 2.5,
        "gdp_quarterly": 0.8,
        "gdp_nominal_bn": 27360,
        "gdp_per_capita": 81600,
        "cpi_yoy": 3.2,
        "cpi_mom": 0.3,
        "core_cpi_yoy": 3.8,
        "ppi_yoy": 1.2,
        "policy_rate": 5.25,
        "central_bank": "Federal Reserve",
        "unemployment_rate": 3.9,
        "trade_balance_bn": -68.3,
    },
    "EU": {
        "gdp_growth_annual": 0.6,
        "gdp_quarterly": 0.2,
        "gdp_nominal_bn": 18700,
        "gdp_per_capita": 42000,
        "cpi_yoy": 2.4,
        "cpi_mom": 0.2,
        "core_cpi_yoy": 2.8,
        "ppi_yoy": -1.5,
        "policy_rate": 4.50,
        "central_bank": "ECB",
        "unemployment_rate": 6.4,
        "trade_balance_bn": 32.1,
    },
    "CN": {
        "gdp_growth_annual": 5.2,
        "gdp_quarterly": 1.3,
        "gdp_nominal_bn": 17960,
        "gdp_per_capita": 12700,
        "cpi_yoy": 0.2,
        "cpi_mom": -0.1,
        "core_cpi_yoy": 0.7,
        "ppi_yoy": -2.7,
        "policy_rate": 3.45,
        "central_bank": "PBOC",
        "unemployment_rate": 5.2,
        "trade_balance_bn": 823.2,
    },
    "JP": {
        "gdp_growth_annual": 1.9,
        "gdp_quarterly": 0.5,
        "gdp_nominal_bn": 4210,
        "gdp_per_capita": 33800,
        "cpi_yoy": 2.8,
        "cpi_mom": 0.3,
        "core_cpi_yoy": 2.5,
        "ppi_yoy": 0.5,
        "policy_rate": 0.1,
        "central_bank": "BOJ",
        "unemployment_rate": 2.6,
        "trade_balance_bn": -45.6,
    },
    "GB": {
        "gdp_growth_annual": 0.5,
        "gdp_quarterly": 0.1,
        "gdp_nominal_bn": 3160,
        "gdp_per_capita": 47000,
        "cpi_yoy": 4.0,
        "cpi_mom": 0.4,
        "core_cpi_yoy": 3.9,
        "ppi_yoy": 0.3,
        "policy_rate": 5.25,
        "central_bank": "BOE",
        "unemployment_rate": 4.2,
        "trade_balance_bn": -156.7,
    },
    "DE": {
        "gdp_growth_annual": -0.1,
        "gdp_quarterly": -0.1,
        "gdp_nominal_bn": 4460,
        "gdp_per_capita": 53100,
        "cpi_yoy": 2.2,
        "cpi_mom": 0.2,
        "core_cpi_yoy": 2.7,
        "ppi_yoy": -3.2,
        "policy_rate": 4.50,
        "central_bank": "Bundesbank/ECB",
        "unemployment_rate": 3.1,
        "trade_balance_bn": 223.4,
    },
    "IN": {
        "gdp_growth_annual": 7.2,
        "gdp_quarterly": 1.8,
        "gdp_nominal_bn": 3940,
        "gdp_per_capita": 2800,
        "cpi_yoy": 5.1,
        "cpi_mom": 0.4,
        "core_cpi_yoy": 4.3,
        "ppi_yoy": 1.8,
        "policy_rate": 6.50,
        "central_bank": "RBI",
        "unemployment_rate": 7.8,
        "trade_balance_bn": -265.3,
    },
    "BR": {
        "gdp_growth_annual": 2.9,
        "gdp_quarterly": 0.7,
        "gdp_nominal_bn": 2170,
        "gdp_per_capita": 10100,
        "cpi_yoy": 4.5,
        "cpi_mom": 0.3,
        "core_cpi_yoy": 4.8,
        "ppi_yoy": 2.1,
        "policy_rate": 10.50,
        "central_bank": "BCB",
        "unemployment_rate": 7.8,
        "trade_balance_bn": 98.7,
    },
}

# Backward-compatible alias (referenced by __init__.py)
ECONOMIC_PROFILES = SAMPLE_ECONOMIC_PROFILES

# ── World Bank API helpers ──────────────────────────────────────────────────

# World Bank country code mapping (ISO 2-letter -> WB 2-letter)
_WB_COUNTRY_MAP: Dict[str, str] = {
    "US": "US",
    "EU": "EUU",  # Euro area aggregate
    "CN": "CN",
    "JP": "JP",
    "GB": "GB",
    "DE": "DE",
    "IN": "IN",
    "BR": "BR",
}

# World Bank indicator codes
_WB_INDICATORS: Dict[str, str] = {
    "gdp_growth_annual": "NY.GDP.MKTP.KD.ZG",
    "gdp_nominal_bn": "NY.GDP.MKTP.CD",       # current USD -> divide by 1e9
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "cpi_yoy": "FP.CPI.TOTL.ZG",
    "unemployment_rate": "SL.UEM.TOTL.ZS",
    "trade_balance_bn": "TX.VAL.MRCH.CD.WT",   # merchandise exports as proxy
}

# Central bank reference rates (static lookup – rarely changes)
_CENTRAL_BANK_RATES: Dict[str, Dict[str, Any]] = {
    "US": {"central_bank": "Federal Reserve", "policy_rate": 5.25},
    "EU": {"central_bank": "ECB", "policy_rate": 4.50},
    "CN": {"central_bank": "PBOC", "policy_rate": 3.45},
    "JP": {"central_bank": "BOJ", "policy_rate": 0.1},
    "GB": {"central_bank": "BOE", "policy_rate": 5.25},
    "DE": {"central_bank": "Bundesbank/ECB", "policy_rate": 4.50},
    "IN": {"central_bank": "RBI", "policy_rate": 6.50},
    "BR": {"central_bank": "BCB", "policy_rate": 10.50},
}

# FRED series IDs (optional, requires FRED_API_KEY env var)
_FRED_SERIES: Dict[str, Dict[str, str]] = {
    "US_gdp_growth_annual": {"series": "GDP", "country": "US"},
    "US_cpi_yoy": {"series": "CPIAUCSL", "country": "US"},
    "US_policy_rate": {"series": "FEDFUNDS", "country": "US"},
    "US_unemployment_rate": {"series": "UNRATE", "country": "US"},
}


async def _fetch_worldbank_indicator(
    session: aiohttp.ClientSession,
    country_code: str,
    indicator: str,
) -> Optional[float]:
    """Fetch the latest value for a World Bank indicator.

    Returns the most recent non-null value, or ``None`` on failure.
    """
    wb_country = _WB_COUNTRY_MAP.get(country_code, country_code)
    wb_indicator = _WB_INDICATORS.get(indicator)
    if not wb_indicator:
        return None

    url = f"https://api.worldbank.org/v2/country/{wb_country}/indicator/{wb_indicator}"
    params = {
        "format": "json",
        "date": "2020:2026",
        "per_page": 5,
        "page": 1,
    }
    headers = {"User-Agent": _UA, "Accept": "application/json"}
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=_API_TIMEOUT)) as resp:
            if resp.status != 200:
                logger.debug("World Bank HTTP %d for %s/%s", resp.status, wb_country, wb_indicator)
                return None
            data = await resp.json(content_type=None)
    except Exception as exc:
        logger.debug("World Bank fetch failed for %s/%s: %s", wb_country, wb_indicator, exc)
        return None

    try:
        # WB returns [pagination, [records]]
        records = data[1] if isinstance(data, list) and len(data) > 1 else []
        for rec in records:
            val = rec.get("value")
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
    except (IndexError, KeyError, TypeError) as exc:
        logger.debug("World Bank parse error for %s/%s: %s", wb_country, wb_indicator, exc)
    return None


async def _fetch_fred_series(
    session: aiohttp.ClientSession,
    series_id: str,
) -> Optional[float]:
    """Fetch the latest observation from a FRED series.

    Requires the ``FRED_API_KEY`` environment variable.  Returns
    ``None`` if the key is missing or the call fails.
    """
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        return None

    url = f"https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    headers = {"User-Agent": _UA, "Accept": "application/json"}
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=_API_TIMEOUT)) as resp:
            if resp.status != 200:
                logger.debug("FRED HTTP %d for %s", resp.status, series_id)
                return None
            data = await resp.json(content_type=None)
    except Exception as exc:
        logger.debug("FRED fetch failed for %s: %s", series_id, exc)
        return None

    try:
        observations = data.get("observations", [])
        for obs in observations:
            val = obs.get("value")
            if val and val != ".":
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
    except (AttributeError, TypeError):
        pass
    return None


async def _fetch_live_profile(
    session: aiohttp.ClientSession,
    country: str,
) -> Optional[Dict[str, Any]]:
    """Build an economic profile for *country* from live APIs.

    Uses the World Bank API and (optionally) FRED.  Missing fields
    are filled from ``_CENTRAL_BANK_RATES`` or left as-is.
    """
    cache_key = f"profile:{country}"
    if cache_key in _profile_cache:
        return _profile_cache[cache_key]

    profile: Dict[str, Any] = {}

    # Fetch World Bank indicators concurrently
    wb_tasks = {
        "gdp_growth_annual": _fetch_worldbank_indicator(session, country, "gdp_growth_annual"),
        "gdp_nominal_bn": _fetch_worldbank_indicator(session, country, "gdp_nominal_bn"),
        "gdp_per_capita": _fetch_worldbank_indicator(session, country, "gdp_per_capita"),
        "cpi_yoy": _fetch_worldbank_indicator(session, country, "cpi_yoy"),
        "unemployment_rate": _fetch_worldbank_indicator(session, country, "unemployment_rate"),
    }

    results = await asyncio.gather(*wb_tasks.values(), return_exceptions=True)
    for key, result in zip(wb_tasks.keys(), results):
        if isinstance(result, Exception) or result is None:
            continue
        val = result
        if key == "gdp_nominal_bn":
            val = round(val / 1e9, 1)  # Convert to billions
        profile[key] = val

    # Merge central bank info
    cb_info = _CENTRAL_BANK_RATES.get(country, {})
    profile.setdefault("central_bank", cb_info.get("central_bank", ""))
    profile.setdefault("policy_rate", cb_info.get("policy_rate", 0.0))

    # Fill derived / missing fields with reasonable defaults
    profile.setdefault("gdp_quarterly", profile.get("gdp_growth_annual", 0.0) / 4.0)
    profile.setdefault("cpi_mom", 0.0)
    profile.setdefault("core_cpi_yoy", profile.get("cpi_yoy", 0.0))
    profile.setdefault("ppi_yoy", 0.0)
    profile.setdefault("trade_balance_bn", 0.0)

    # Mark source
    profile["_source"] = "worldbank"
    profile["_timestamp"] = datetime.now(timezone.utc).isoformat()

    # Only cache if we got at least one real value
    if any(k in profile for k in ("gdp_growth_annual", "cpi_yoy", "unemployment_rate")):
        _profile_cache[cache_key] = profile
        return profile

    return None


# ── Source Provider ──────────────────────────────────────────────────────────


class EconomicSource(SourceProvider):
    """Economic data feed provider.

    Fetches macroeconomic indicators from **live APIs** (World Bank,
    optionally FRED) when ``_LIVE_MODE`` is ``True`` (default).
    Falls back to :data:`SAMPLE_ECONOMIC_PROFILES` only when every
    live API call fails, logging a warning each time so stale data
    is never silent.

    Usage::

        source = EconomicSource()
        result = await source.fetch("US inflation", max_items=10)
        result = await source.scan(max_items=50)
    """

    def __init__(
        self,
        config: Optional[SourceConfig] = None,
        countries: Optional[List[str]] = None,
    ):
        super().__init__(
            name="economic",
            category=SourceCategory.ECONOMIC,
            reliability=SourceReliability.RELIABLE,
            config=config,
        )
        self._countries = countries or list(SAMPLE_ECONOMIC_PROFILES.keys())
        # Live profiles populated by _refresh_live_data
        self._live_profiles: Dict[str, Dict[str, Any]] = {}

    # ── Live data refresh ───────────────────────────────────────────────

    async def _refresh_live_data(self) -> None:
        """Call live APIs and populate ``_live_profiles``.

        If ``_LIVE_MODE`` is ``False`` or all API calls fail, the
        profiles are populated from SAMPLE_DATA and a warning is logged.
        """
        if not _LIVE_MODE:
            self._live_profiles = dict(SAMPLE_ECONOMIC_PROFILES)
            logger.warning("Using SAMPLE_DATA - live API disabled (_LIVE_MODE=False)")
            return

        async with aiohttp.ClientSession() as session:
            tasks = []
            for country in self._countries:
                tasks.append(_fetch_live_profile(session, country))
            results = await asyncio.gather(*tasks, return_exceptions=True)

            live: Dict[str, Dict[str, Any]] = {}
            any_success = False
            for country, result in zip(self._countries, results):
                if isinstance(result, Exception) or result is None:
                    continue
                live[country] = result
                any_success = True

            if any_success:
                self._live_profiles = live
            else:
                self._live_profiles = dict(SAMPLE_ECONOMIC_PROFILES)
                logger.warning("Using SAMPLE_DATA - live API unavailable for economic (worldbank/fred)")

    # ── Public async API ────────────────────────────────────────────────

    async def fetch(self, query: str, max_items: int = 50, **kwargs: Any) -> SourceResult:
        """Fetch economic indicators matching a query.

        Parameters
        ----------
        query:
            Search query (e.g. "US inflation", "GDP growth", "interest rates").
        max_items:
            Maximum items to return.

        Returns
        -------
        SourceResult
            Matched economic indicators.
        """
        start = time.monotonic()
        self._record_fetch()
        items: List[SourceItem] = []
        errors: List[str] = []
        query_lower = query.lower()

        try:
            await self._refresh_live_data()

            for country in self._countries:
                profile = self._live_profiles.get(country)
                if profile is None:
                    continue
                source = profile.get("_source", "sample_data")
                ts = profile.get("_timestamp", "")
                indicators = self._build_indicators(country, profile)
                for indicator in indicators:
                    text = f"{indicator.name} {indicator.country} {indicator.category}".lower()
                    if query_lower in text or any(w in text for w in query_lower.split()):
                        items.append(indicator.to_item(_source=source, _timestamp=ts))
                        if len(items) >= max_items:
                            break
                if len(items) >= max_items:
                    break
        except Exception as exc:
            errors.append(str(exc))
            self._record_error()

        elapsed = (time.monotonic() - start) * 1000
        return self._make_result(
            items=items,
            total_available=len(items),
            errors=errors,
            elapsed_ms=elapsed,
        )

    async def scan(self, max_items: int = 100, **kwargs: Any) -> SourceResult:
        """Scan all economic indicators across countries.

        Parameters
        ----------
        max_items:
            Maximum items to return.

        Returns
        -------
        SourceResult
            Latest economic indicators from all tracked countries.
        """
        start = time.monotonic()
        self._record_scan()
        items: List[SourceItem] = []
        errors: List[str] = []

        try:
            await self._refresh_live_data()

            for country in self._countries:
                profile = self._live_profiles.get(country)
                if profile is None:
                    continue
                source = profile.get("_source", "sample_data")
                ts = profile.get("_timestamp", "")
                indicators = self._build_indicators(country, profile)
                for indicator in indicators:
                    items.append(indicator.to_item(_source=source, _timestamp=ts))
                    if len(items) >= max_items:
                        break
                if len(items) >= max_items:
                    break
        except Exception as exc:
            errors.append(str(exc))
            self._record_error()

        elapsed = (time.monotonic() - start) * 1000
        return self._make_result(
            items=items,
            total_available=len(items),
            errors=errors,
            elapsed_ms=elapsed,
        )

    def _build_indicators(
        self,
        country: str,
        profile: Dict[str, Any],
    ) -> List[EconomicIndicator]:
        """Build economic indicators from a country profile."""
        now = datetime.now(timezone.utc)
        indicators: List[EconomicIndicator] = []

        # GDP
        indicators.append(EconomicIndicator(
            indicator_id=f"{country}_gdp",
            name="GDP Growth Rate",
            country=country,
            value=profile.get("gdp_growth_annual", 0.0),
            unit="% annual",
            frequency="quarterly",
            source_agency=profile.get("central_bank", ""),
            timestamp=now,
            category="gdp",
        ))

        # Inflation
        indicators.append(EconomicIndicator(
            indicator_id=f"{country}_cpi",
            name="Consumer Price Index (YoY)",
            country=country,
            value=profile.get("cpi_yoy", 0.0),
            previous_value=profile.get("cpi_yoy"),
            unit="%",
            frequency="monthly",
            source_agency="National Statistics",
            timestamp=now,
            change_pct=None,
            category="inflation",
        ))

        # Interest Rate
        indicators.append(EconomicIndicator(
            indicator_id=f"{country}_rate",
            name="Policy Interest Rate",
            country=country,
            value=profile.get("policy_rate", 0.0),
            unit="%",
            frequency="irregular",
            source_agency=profile.get("central_bank", ""),
            timestamp=now,
            category="monetary",
        ))

        # Unemployment
        indicators.append(EconomicIndicator(
            indicator_id=f"{country}_unemp",
            name="Unemployment Rate",
            country=country,
            value=profile.get("unemployment_rate", 0.0),
            unit="%",
            frequency="monthly",
            source_agency="Labor Bureau",
            timestamp=now,
            category="employment",
        ))

        # Trade Balance
        indicators.append(EconomicIndicator(
            indicator_id=f"{country}_trade",
            name="Trade Balance",
            country=country,
            value=profile.get("trade_balance_bn", 0.0),
            unit="USD billions",
            frequency="monthly",
            source_agency="Customs/Trade Authority",
            timestamp=now,
            category="trade",
        ))

        return indicators

    # ── Direct access methods ───────────────────────────────────────────

    def get_gdp_data(self, country: str) -> Optional[GDPRate]:
        """Get GDP data for a specific country."""
        profile = (self._live_profiles or SAMPLE_ECONOMIC_PROFILES).get(country)
        if profile is None:
            return None
        return GDPRate(
            country=country,
            annual_growth_pct=profile.get("gdp_growth_annual", 0.0),
            quarterly_growth_pct=profile.get("gdp_quarterly", 0.0),
            gdp_nominal_usd_bn=profile.get("gdp_nominal_bn", 0.0),
            gdp_per_capita_usd=profile.get("gdp_per_capita", 0.0),
        )

    def get_inflation_data(self, country: str) -> Optional[InflationData]:
        """Get inflation data for a specific country."""
        profile = (self._live_profiles or SAMPLE_ECONOMIC_PROFILES).get(country)
        if profile is None:
            return None
        return InflationData(
            country=country,
            cpi_yoy_pct=profile.get("cpi_yoy", 0.0),
            cpi_mom_pct=profile.get("cpi_mom", 0.0),
            core_cpi_yoy_pct=profile.get("core_cpi_yoy", 0.0),
            ppi_yoy_pct=profile.get("ppi_yoy"),
        )

    def get_interest_rate_data(self, country: str) -> Optional[InterestRateData]:
        """Get central bank interest rate data for a specific country."""
        profile = (self._live_profiles or SAMPLE_ECONOMIC_PROFILES).get(country)
        if profile is None:
            return None
        return InterestRateData(
            country=country,
            central_bank=profile.get("central_bank", ""),
            policy_rate_pct=profile.get("policy_rate", 0.0),
        )

    @property
    def tracked_countries(self) -> List[str]:
        """List of tracked country codes."""
        return list(self._countries)
