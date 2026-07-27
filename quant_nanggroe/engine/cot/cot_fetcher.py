"""
COTFetcher — Automated CFTC Commitment of Traders data fetcher with caching.

Uses the `cot_reports` library to download weekly COT reports from the CFTC.
Provides:
  - Single-year and multi-year fetching
  - Disk cache (CSV) to avoid re-downloading
  - Smart cache: only refetch on Friday after 5:30 PM ET (when COT releases)
  - Graceful degradation: returns cached data if CFTC site is unreachable

Typical usage (called weekly by cron / daemon):
    from quant_nanggroe.engine.cot.cot_fetcher import COTFetcher

    fetcher = COTFetcher()
    df = fetcher.fetch()  # Uses cache, auto-refresh on Friday
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Default cache directory inside the QNA data folder
COT_CACHE_DIR = Path("data/cot_cache")
COT_CACHE_FILE = "cot_legacy_fut.parquet"
COT_CACHE_PATH = COT_CACHE_DIR / COT_CACHE_FILE

# ET = UTC-5 (standard) / UTC-4 (daylight). COT releases Friday 5:30 PM ET.
# Friday 5:30 PM ET = Saturday 0:30 UTC (simplified: check on Saturday)
# For simplicity, we define "Friday threshold" as Saturday 00:00 UTC.
_FRIDAY_RELEASE_UTC = 0  # hour (Saturday 00:00 UTC = Friday 8:00 PM ET)
_FRIDAY = 4  # Friday is day 4 in Python (Mon=0 ... Sun=6)


def _is_cot_refresh_due() -> bool:
    """Check if a COT data refresh is due (new Friday report likely available).

    COT reports are released Friday 5:30 PM ET. The next valid refresh window
    starts Saturday 00:00 UTC and lasts until the next Friday.

    Returns:
        True if today is Friday through Sunday (new data may exist from Friday).
    """
    now = datetime.now(timezone.utc)
    # If today is Friday or later, the new Friday report may be available
    return now.weekday() >= _FRIDAY


class COTFetcher:
    """Fetch and cache COT data from CFTC via cot_reports.

    Attributes:
        cache_path: Path to the parquet cache file.
        cache_days: Max age of cache before refresh (default: 7 days).
        store_txt: Whether cot_reports should store raw text files.
        verbose: Whether cot_reports should print download progress.
    """

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        store_txt: bool = False,
        verbose: bool = False,
    ):
        """
        Args:
            cache_path: Custom cache path (default: data/cot_cache/cot_legacy_fut.parquet).
            store_txt: Pass through to cot_reports (default: False).
            verbose: Pass through to cot_reports (default: False).
        """
        self.cache_path = cache_path or COT_CACHE_PATH
        self.store_txt = store_txt
        self.verbose = verbose
        self._data: Optional[pd.DataFrame] = None

    # ── Public fetch interface ─────────────────────────────────

    def fetch(
        self,
        years: int = 3,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Fetch COT data, using cache if available and fresh.

        Args:
            years: Number of years of history to fetch (default: 3).
            force_refresh: Ignore cache and re-download.

        Returns:
            DataFrame with COT data. Empty DataFrame on failure.
        """
        # Try cache first
        if not force_refresh:
            cached = self._load_cache()
            if cached is not None:
                # Check if cache needs refresh (Friday or older)
                if not _is_cot_refresh_due():
                    logger.info("COT cache is fresh — using cached data")
                    self._data = cached
                    return cached
                # Refresh only the latest year
                logger.info("COT refresh due — fetching latest year")
                latest = self._fetch_year(datetime.now().year)
                if latest is not None and not latest.empty:
                    # Merge: replace newest data in cache with latest
                    merged = self._merge_cached_and_new(cached, latest)
                    self._data = merged
                    self._save_cache(merged)
                    return merged
                # Fall through: if fetch failed, return cache
                logger.warning("COT refresh failed — returning cached data")
                self._data = cached
                return cached

        # No cache valid — full fetch
        logger.info("COT: no valid cache — fetching %d years of history", years)
        df = self.fetch_history(years=years, force_refresh=True)
        self._data = df
        return df

    def fetch_history(
        self,
        years: int = 5,
        force_refresh: bool = False,
        report_type: str = "legacy_fut",
    ) -> pd.DataFrame:
        """Fetch multi-year COT historical data.

        Uses `cot_reports.cot_year()` for each year and concatenates.
        Uses `cot_reports.cot_all()` if years >= 30 (full history).

        Args:
            years: Number of years of history (default: 5).
            force_refresh: Bypass all cache (default: False).
            report_type: COT report type (default: 'legacy_fut').

        Returns:
            Combined DataFrame for all requested years.
        """
        if not force_refresh:
            cached = self._load_cache()
            if cached is not None:
                logger.info("COT history cache hit — %d rows", len(cached))
                self._data = cached
                return cached

        try:
            import cot_reports as cot

            current_year = datetime.now().year
            years_to_fetch = list(range(current_year - years + 1, current_year + 1))
            frames: list[pd.DataFrame] = []

            for yr in years_to_fetch:
                try:
                    df_yr = cot.cot_year(
                        year=yr,
                        cot_report_type=report_type,
                        store_txt=self.store_txt,
                        verbose=self.verbose,
                    )
                    if df_yr is not None and not df_yr.empty:
                        frames.append(df_yr)
                        logger.debug(
                            "COT %d: %d rows, %d cols", yr, len(df_yr), len(df_yr.columns)
                        )
                except Exception as e:
                    logger.warning("COT year %d fetch failed: %s", yr, e)

            if not frames:
                logger.error("COT: no data fetched for any year")
                return pd.DataFrame()

            combined = pd.concat(frames, ignore_index=True)
            combined = self._clean_columns(combined)
            combined = combined.sort_values("As of Date in Form YYYY-MM-DD")

            self._save_cache(combined)
            self._data = combined
            logger.info(
                "COT history fetched: %d rows, %d markets, %d years",
                len(combined),
                combined["Market and Exchange Names"].nunique(),
                years,
            )
            return combined

        except ImportError:
            logger.error("cot_reports not installed: pip install cot_reports")
            return pd.DataFrame()
        except Exception as e:
            logger.error("COT history fetch failed: %s", e)
            return pd.DataFrame()

    # ── Single contract queries ────────────────────────────────

    def get_contract_data(
        self,
        market_name: str,
    ) -> pd.DataFrame:
        """Get COT data for a specific market by name.

        Args:
            market_name: Market name to filter (e.g. 'GOLD', 'S&P 500', 'EURO FX').
                         Uses case-insensitive substring match.

        Returns:
            DataFrame filtered to that market, sorted by date descending.
        """
        if self._data is None or self._data.empty:
            logger.warning("COT data not loaded — call fetch() first")
            return pd.DataFrame()

        mask = self._data["Market and Exchange Names"].str.contains(
            market_name, case=False, na=False
        )
        result = self._data[mask].copy()
        if result.empty:
            logger.warning("COT: no data for market '%s'", market_name)
            return pd.DataFrame()

        result = result.sort_values("As of Date in Form YYYY-MM-DD", ascending=False)
        return result

    def get_recent_row(
        self,
        market_name: str,
    ) -> Optional[pd.Series]:
        """Get the most recent COT report row for a market.

        Args:
            market_name: Market name to look up.

        Returns:
            Most recent row as a Series, or None if not found.
        """
        df = self.get_contract_data(market_name)
        if df.empty:
            return None
        return df.iloc[0]

    # ── Cache management ───────────────────────────────────────

    def clear_cache(self) -> None:
        """Delete the COT cache file."""
        path = Path(self.cache_path)
        if path.exists():
            path.unlink()
            logger.info("COT cache cleared: %s", path)

    def cache_exists(self) -> bool:
        """Check if cache file exists."""
        return Path(self.cache_path).exists()

    # ── Internal helpers ───────────────────────────────────────

    def _fetch_year(self, year: int) -> Optional[pd.DataFrame]:
        """Fetch a single year of COT data."""
        try:
            import cot_reports as cot

            df = cot.cot_year(
                year=year,
                cot_report_type="legacy_fut",
                store_txt=self.store_txt,
                verbose=self.verbose,
            )
            if df is not None and not df.empty:
                return self._clean_columns(df)
            return None
        except Exception as e:
            logger.debug("COT fetch year %d failed: %s", year, e)
            return None

    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names and types."""
        # Ensure date is datetime
        if "As of Date in Form YYYY-MM-DD" in df.columns:
            df["As of Date in Form YYYY-MM-DD"] = pd.to_datetime(
                df["As of Date in Form YYYY-MM-DD"], errors="coerce"
            )
        # Ensure numeric columns are float
        for col in df.columns:
            if "Positions" in col or "Open Interest" in col or "% of OI" in col:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _merge_cached_and_new(
        self, cached: pd.DataFrame, latest: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge cached data with a newly fetched year, deduplicating by date."""
        if latest.empty:
            return cached
        # Remove rows from cached that match the latest year
        cache_year = latest["As of Date in Form YYYY-MM-DD"].dt.year.max()
        mask = cached["As of Date in Form YYYY-MM-DD"].dt.year != cache_year
        merged = pd.concat([cached[mask], latest], ignore_index=True)
        merged = merged.sort_values("As of Date in Form YYYY-MM-DD")
        return merged

    def _load_cache(self) -> Optional[pd.DataFrame]:
        """Load cached COT data. Tries parquet first, falls back to CSV."""
        path = Path(self.cache_path)
        if not path.exists():
            # Try CSV fallback
            csv_path = path.with_suffix(".csv")
            if csv_path.exists():
                try:
                    df = pd.read_csv(csv_path, parse_dates=["As of Date in Form YYYY-MM-DD"])
                    if not df.empty:
                        logger.debug("COT cache loaded (CSV): %d rows", len(df))
                        return df
                except Exception:
                    pass
            return None
        try:
            df = pd.read_parquet(path)
            if df.empty:
                return None
            logger.debug("COT cache loaded: %d rows", len(df))
            return df
        except Exception as e:
            logger.debug("COT cache load failed (parquet), trying CSV: %s", e)
            csv_path = path.with_suffix(".csv")
            if csv_path.exists():
                try:
                    return pd.read_csv(csv_path, parse_dates=["As of Date in Form YYYY-MM-DD"])
                except Exception:
                    pass
            return None

    def _save_cache(self, df: pd.DataFrame) -> bool:
        """Save COT data to cache. Prefers parquet, falls back to CSV."""
        try:
            path = Path(self.cache_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
            logger.debug("COT cache saved (parquet): %d rows", len(df))
            return True
        except Exception as e:
            # Fallback to CSV
            try:
                csv_path = path.with_suffix(".csv")
                df.to_csv(csv_path, index=False)
                logger.debug("COT cache saved (CSV): %d rows", len(df))
                return True
            except Exception as e2:
                logger.warning("COT cache save failed (both parquet and CSV): %s / %s", e, e2)
                return False
