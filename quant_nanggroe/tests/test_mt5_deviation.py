"""Tests for per-symbol slippage deviation (Blocker 2).

Covers the three deviation buckets:
    FX majors/crosses -> 5, indices/metals -> 20, crypto CFDs -> 50,
plus unknown-symbol classification and broker-suffix stripping.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchange.mt5_broker import _resolve_deviation  # noqa: E402


@pytest.mark.parametrize(
    "symbol, expected",
    [
        # FX majors -> 5
        ("EURUSD", 5),
        ("USDJPY", 5),
        ("GBPUSD", 5),
        ("USDCHF", 5),
        ("AUDUSD", 5),
        ("USDCAD", 5),
        ("NZDUSD", 5),
        ("EURJPY", 5),
        ("GBPJPY", 5),
        ("EURGBP", 5),
        # Metals -> 20
        ("XAUUSD", 20),
        ("XAGUSD", 20),
        # Indices -> 20
        ("US30", 20),
        ("US500", 20),
        ("USTEC", 20),
        ("NAS100", 20),
        ("SPX500", 20),
        ("GER40", 20),
        ("DE40", 20),
        ("UK100", 20),
        # Crypto CFDs -> 50
        ("BTCUSD", 50),
        ("ETHUSD", 50),
    ],
)
def test_known_symbols(symbol, expected):
    assert _resolve_deviation(symbol) == expected


@pytest.mark.parametrize(
    "symbol, expected",
    [
        # Broker-suffixed known symbols keep their bucket.
        ("eurusd.pro", 5),
        ("XAUUSD-ecn", 20),
        ("btcusd.c", 50),
        # Unknown symbols classified by category.
        ("SOLUSD", 50),   # crypto base
        ("XPTUSD", 20),   # metal base
        ("JP225", 20),    # index base
        ("GBPNZD", 5),    # FX pair
        # Unknown & unclassifiable -> DEFAULT_DEVIATION (20)
        ("UKOIL", 20),
        ("FOOBAR", 20),
        ("", 20),
    ],
)
def test_unknown_and_suffixed_symbols(symbol, expected):
    assert _resolve_deviation(symbol) == expected
