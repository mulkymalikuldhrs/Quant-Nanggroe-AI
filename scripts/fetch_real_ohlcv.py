#!/usr/bin/env python3
"""Fetch Real OHLCV — Populate data/cached_ohlcv/ with real CoinGecko data.

Fetches daily OHLCV from CoinGecko public API (no key needed) for
BTC, ETH, SOL, XRP and writes to ``data/cached_ohlcv/{SYMBOL}.csv``
in **date,open,high,low,close,volume** format.

Falls back to GARCH-like synthetic data if the API is unreachable
(rate-limited, Termux network issues, etc.).

Usage:
    python scripts/fetch_real_ohlcv.py                       # real only, skip on failure
    python scripts/fetch_real_ohlcv.py --synthetic-fallback   # GARCH fallback if API fails
    python scripts/fetch_real_ohlcv.py --force                # re-fetch existing files
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_DIR = os.path.join(_REPO_ROOT, "data", "cached_ohlcv")

COINS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
}

USER_AGENT = "QuantNanggroeAI/1.0"


def fetch_json(url: str, retries: int = 1, timeout: int = 10) -> list | dict | None:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            last_err = e
            if attempt < retries - 1:
                wait = 2 ** attempt * 2
                print(f"  [RETRY] {e} — waiting {wait}s...")
                time.sleep(wait)
            continue
    if last_err:
        print(f"  [FAIL] All retries exhausted: {last_err}")
    return None


def fetch_coingecko_ohlcv(
    symbol: str,
    coin_id: str,
    days: int = 500,
    vs_currency: str = "usd",
) -> pd.DataFrame | None:
    """Fetch OHLC + volume from CoinGecko, return daily DataFrame."""
    ohlc_url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        f"?days={days}&vs_currency={vs_currency}"
    )
    ohlc_raw = fetch_json(ohlc_url)
    if not ohlc_raw or not isinstance(ohlc_raw, list):
        print(f"  [WARN] No OHLC data returned for {symbol}")
        return None

    rows = []
    for entry in ohlc_raw:
        ts_ms, o, h, l, c = entry
        rows.append({"timestamp": ts_ms, "open": o, "high": h, "low": l, "close": c})

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("date")
    df = df[["open", "high", "low", "close"]].sort_index()

    vol_url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        f"?days={days}&vs_currency={vs_currency}"
    )
    vol_raw = fetch_json(vol_url)

    if vol_raw and isinstance(vol_raw, dict) and "total_volumes" in vol_raw:
        vol_rows = []
        for ts_ms, vol in vol_raw["total_volumes"]:
            vol_rows.append({"timestamp": ts_ms, "volume": vol})
        df_vol = pd.DataFrame(vol_rows)
        df_vol["date"] = pd.to_datetime(df_vol["timestamp"], unit="ms")
        df_vol = df_vol.set_index("date")
        df_vol = df_vol["volume"].sort_index()
        df["volume"] = df_vol.reindex(df.index, method="nearest")
    else:
        rng = np.random.default_rng(42)
        print(f"  [WARN] No volume data for {symbol}, generating proxy")
        df["volume"] = rng.integers(10_000_000, 100_000_000, len(df))

    daily = df.resample("D").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    print(f"  {symbol}: {len(daily)} daily bars from CoinGecko")
    return daily


def generate_garch_ohlcv(n: int, seed: int = 42) -> pd.DataFrame:
    """GARCH(1,1)-like OHLCV with fat tails, vol clustering, momentum."""
    rng = np.random.default_rng(seed)
    returns = rng.standard_t(df=4, size=n) * 0.015
    for i in range(1, n):
        returns[i] += 0.05 * returns[i - 1]
    vol = np.ones(n) * 0.015
    for i in range(1, n):
        vol[i] = np.sqrt(0.00001 + 0.85 * vol[i - 1] ** 2 + 0.10 * returns[i - 1] ** 2)
    returns *= vol / 0.015

    close = 100 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(10_000, 100_000, n)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="D")

    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    }, index=dates)


def save_csv(symbol: str, df: pd.DataFrame) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    path = os.path.join(_CACHE_DIR, f"{symbol}.csv")
    out = df.reset_index()
    out.columns = ["date", "open", "high", "low", "close", "volume"]
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)
    size_kb = os.path.getsize(path) / 1024
    print(f"  Written {path} ({len(out)} rows, {size_kb:.1f} KB)")


def csv_has_min_rows(symbol: str, min_rows: int = 100) -> bool:
    path = os.path.join(_CACHE_DIR, f"{symbol}.csv")
    if not os.path.isfile(path):
        return False
    try:
        df = pd.read_csv(path)
        return len(df) >= min_rows
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch real OHLCV for Alpha Destruction")
    parser.add_argument("--synthetic-fallback", action="store_true",
                        help="Generate GARCH data if CoinGecko unreachable")
    parser.add_argument("--skip-coingecko", action="store_true",
                        help="Skip CoinGecko entirely, generate GARCH data directly")
    parser.add_argument("--days", type=int, default=500,
                        help="Days of data to request (default: 500)")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch even if cache exists")
    args = parser.parse_args()

    if args.skip_coingecko:
        print("  --skip-coingecko: generating GARCH data for all symbols\n")

    print("━━━ Fetch Real OHLCV ━━━")
    print(f"  Target: {_CACHE_DIR}")
    print(f"  Days:   {args.days}")
    if args.skip_coingecko:
        mode = "GARCH synthetic (CoinGecko skipped)"
    elif args.synthetic_fallback:
        mode = "real + GARCH fallback"
    else:
        mode = "real only"
    print(f"  Mode:   {mode}")

    success: list[str] = []

    for symbol, coin_id in COINS.items():
        if not args.force and csv_has_min_rows(symbol):
            path = os.path.join(_CACHE_DIR, f"{symbol}.csv")
            sz = os.path.getsize(path) / 1024
            print(f"  {symbol}: cache exists ({sz:.0f} KB), skipping")
            success.append(symbol)
            continue

        n_bars = max(args.days, 500)

        if args.skip_coingecko:
            print(f"  {symbol}: generating {n_bars} GARCH bars...")
            df = generate_garch_ohlcv(n=n_bars)
            save_csv(symbol, df)
            success.append(symbol)
            continue

        print(f"  {symbol} ({coin_id})...")
        df = fetch_coingecko_ohlcv(symbol, coin_id, days=args.days)

        if df is not None and len(df) >= 30:
            save_csv(symbol, df)
            success.append(symbol)
        elif args.synthetic_fallback:
            print(f"  [FALLBACK] Generating {n_bars} GARCH bars for {symbol}")
            df = generate_garch_ohlcv(n=n_bars)
            save_csv(symbol, df)
            success.append(symbol)
        else:
            print(f"  [SKIP] {symbol}: no data. Use --synthetic-fallback to generate.")

    print(f"\nDone: {len(success)}/{len(COINS)} symbols populated")
    for symbol in COINS:
        path = os.path.join(_CACHE_DIR, f"{symbol}.csv")
        if os.path.isfile(path):
            rows = len(pd.read_csv(path))
            sz = os.path.getsize(path) / 1024
            print(f"  {symbol}: {rows} rows, {sz:.0f} KB")


if __name__ == "__main__":
    main()
