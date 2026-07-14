"""Correlation, currency strength, sector heatmap — all from yfinance.

Standalone provider (not a DataProvider subclass) that computes:
- Rolling correlation matrix for all traded symbols
- Currency strength meter from 8 major forex pairs
- Sector performance heatmap from SPDR sector ETFs
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ── symbol maps ────────────────────────────────────────────────────────
# All symbols the strategy trades
TRADED: Dict[str, str] = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "XAUUSD": "GC=F",
    "SPY": "SPY",
    "US10Y": "^TNX",
}

# SPDR sector ETFs used for the sector heatmap
SECTOR_ETFS: Dict[str, str] = {
    "XLF": "Financials",
    "XLK": "Technology",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLP": "Consumer Staples",
    "XLY": "Consumer Discretionary",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
}

# Forex pairs for the currency strength meter
FOREX_PAIRS: Dict[str, str] = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "USDCHF": "USDCHF=X",
    "USDCAD": "USDCAD=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "EURJPY": "EURJPY=X",
}

# All tracked currencies
_CURRENCIES = ["EUR", "GBP", "USD", "JPY", "CHF", "CAD", "AUD", "NZD"]


# ── helpers ───────────────────────────────────────────────────────────

def _close_prices(
    symbols, period: str = "6mo"
) -> pd.DataFrame:
    """Download daily adjusted close for a list of Yahoo symbols.

    *symbols* can be a dict mapping label → Yahoo ticker (e.g. ``{"SPY":
    "SPY", "EURUSD": "EURUSD=X"}``) or a plain list of Yahoo ticker strings.
    When a dict is passed, returned columns use the labels.
    """
    if isinstance(symbols, dict):
        tickers = list(symbols.values())
        label_of = {v: k for k, v in symbols.items()}
    else:
        tickers = list(symbols)
        label_of = {t: t for t in tickers}

    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if raw.empty:
        return pd.DataFrame()

    # yfinance >= 1.5 returns MultiIndex columns; extract Close
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw.xs("Close", axis=1, level=0, drop_level=False)
        close.columns = [col[1] if isinstance(col, tuple) else col for col in close.columns]
    else:
        close = raw

    # Rename Yahoo tickers to our short labels
    close = close.rename(columns=label_of)
    return close.ffill().dropna(how="all", axis=1)


# ── public API ────────────────────────────────────────────────────────

def correlation_matrix(
    window: int = 60,
    period: str = "6mo",
) -> pd.DataFrame:
    """Rolling pairwise correlation matrix for all traded symbols.

    Parameters
    ----------
    window : int
        Rolling window length in trading days (default 60 ≈ 3 months).
    period : str
        yfinance period string for data fetch.

    Returns
    -------
    DataFrame of shape (n_symbols, n_symbols) with the *latest* rolling
    correlation values.
    """
    prices = _close_prices(TRADED, period=period)
    if prices.empty or len(prices) < window:
        return pd.DataFrame(index=TRADED.keys(), columns=TRADED.keys())

    # ponytail: latest value of the rolling window — add full history if needed
    returns = prices.pct_change().dropna()
    rolling_corr = returns.rolling(window=window).corr()
    latest = rolling_corr.groupby(level=1).last()
    return latest.reindex(index=list(TRADED.keys()), columns=list(TRADED.keys()))


def currency_strength_meter(
    period: str = "1mo",
) -> Dict[str, float]:
    """Rank currencies by their net performance across all major pairs.

    For each of the 8 tracked currencies we compute the average % change
    against all counterparties, adjusting the sign so that a positive value
    always means *this* currency strengthened.

    Returns
    -------
    Dict mapping currency code -> strength score (%).  Sorted descending.
    """
    prices = _close_prices(FOREX_PAIRS, period=period)
    if prices.empty or len(prices) < 2:
        return {c: 0.0 for c in _CURRENCIES}

    # ponytail: simple 1-period return from first to last close
    first = prices.iloc[0]
    last = prices.iloc[-1]
    changes: Dict[str, float] = {}
    for label, yahoo_ticker in FOREX_PAIRS.items():
        if label not in prices.columns:
            continue
        chg = (last[label] / first[label] - 1.0) * 100.0
        changes[label] = chg

    # Sum contributions per currency (invert when currency is quote)
    scores: Dict[str, float] = {c: 0.0 for c in _CURRENCIES}
    counts: Dict[str, int] = {c: 0 for c in _CURRENCIES}

    for label, chg in changes.items():
        base, quote = label[:3], label[3:]  # e.g. "EUR" / "USD" from "EURUSD"
        scores[base] += chg
        counts[base] += 1
        scores[quote] -= chg  # flip sign: quote weakening ↔ pair rising
        counts[quote] += 1

    avg = {c: scores[c] / counts[c] if counts[c] else 0.0 for c in _CURRENCIES}
    return dict(sorted(avg.items(), key=lambda x: x[1], reverse=True))


def sector_heatmap(
    period: str = "1mo",
) -> Dict[str, Dict[str, float]]:
    """Current performance of SPDR sector ETFs.

    Parameters
    ----------
    period : str
        yfinance period string.  Use "5d" for weekly, "1mo" for monthly,
        "3mo" for quarterly.

    Returns
    -------
    Dict mapping sector name -> {return_pct, etf, label}.
    Sorted by return descending.
    """
    tickers = list(SECTOR_ETFS.keys())
    prices = _close_prices({t: t for t in tickers}, period=period)
    if prices.empty or len(prices) < 2:
        return {}

    first = prices.iloc[0]
    last = prices.iloc[-1]
    heat: List[Tuple[str, float]] = []
    for etf in tickers:
        if etf not in prices.columns:
            continue
        ret = (last[etf] / first[etf] - 1.0) * 100.0
        heat.append((SECTOR_ETFS[etf], ret))

    heat.sort(key=lambda x: x[1], reverse=True)
    # ponytail: reverse-lookup in SECTOR_ETFS dict — O(n), n=10, fine
    etf_by_sector = {s: e for e, s in SECTOR_ETFS.items()}
    result = {}
    for sector, ret in heat:
        etf = etf_by_sector.get(sector)
        if etf:
            result[sector] = {
                "return_pct": round(ret, 2),
                "etf": etf,
                "label": sector,
            }
    return result


# ── convenience aggregate ─────────────────────────────────────────────

def full_report(
    corr_window: int = 60,
    corr_period: str = "6mo",
    fx_period: str = "1mo",
    sector_period: str = "1mo",
) -> Dict[str, object]:
    """Return all three analytics in a single dict.

    Keys: ``correlation_matrix``, ``currency_strength``, ``sector_heatmap``.
    """
    return {
        "correlation_matrix": correlation_matrix(window=corr_window, period=corr_period),
        "currency_strength": currency_strength_meter(period=fx_period),
        "sector_heatmap": sector_heatmap(period=sector_period),
    }


# ── self-check ────────────────────────────────────────────────────────

def demo() -> None:
    """Quick smoke test against live data."""
    print("=" * 60)
    print("Correlation Provider — smoke test")
    print("=" * 60)

    print("\n--- Correlation Matrix (latest rolling 60d) ---")
    corr = correlation_matrix()
    if not corr.empty:
        print(corr.to_string(float_format="%.3f"))
    else:
        print("(empty — check connectivity)")

    print("\n--- Currency Strength Meter (1mo) ---")
    fx = currency_strength_meter()
    for c, s in fx.items():
        print(f"  {c}: {s:+.2f}%")

    print("\n--- Sector Heatmap (1mo) ---")
    sh = sector_heatmap()
    for sector, data in sh.items():
        print(f"  {sector:22s} {data['return_pct']:+.2f}%  ({data['etf']})")

    print("\n✓ done")


if __name__ == "__main__":
    demo()
