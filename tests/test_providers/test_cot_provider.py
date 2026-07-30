"""Tests: COT Provider — CFTC Commitment of Traders data.

Mocks _fetch_raw (module-level helper) to avoid the complexity of
mocking urllib.request.urlopen with its context manager protocol.
Covers resolve_match_string, CotRecord, CotSignal, fetch_cot.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quant_nanggroe.providers.cot_provider import (
    resolve_match_string,
    CotRecord,
    _build_signal,
    fetch_cot,
)


def _make_cot_row(
    date: str = "2026-07-28",
    market: str = "EURO FX",
    spec_long: int = 150000,
    spec_short: int = 80000,
    spec_spread: int = 20000,
    oi: int = 500000,
    comm_long: int = 100000,
    comm_short: int = 120000,
) -> dict[str, Any]:
    return {
        "report_date_as_yyyy_mm_dd": date,
        "contract_market_name": market,
        "noncomm_positions_long_all": str(spec_long),
        "noncomm_positions_short_all": str(spec_short),
        "noncomm_postions_spread_all": str(spec_spread),
        "open_interest_all": str(oi),
        "comm_positions_long_all": str(comm_long),
        "comm_positions_short_all": str(comm_short),
    }


COT_RESPONSE_GOLD = [
    _make_cot_row("2026-07-28", "GOLD", spec_long=300000, spec_short=100000),
    _make_cot_row("2026-07-21", "GOLD", spec_long=280000, spec_short=120000),
    _make_cot_row("2026-07-14", "GOLD", spec_long=260000, spec_short=130000),
    _make_cot_row("2026-07-07", "GOLD", spec_long=250000, spec_short=140000),
    _make_cot_row("2026-06-30", "GOLD", spec_long=240000, spec_short=150000),
    _make_cot_row("2026-06-23", "GOLD", spec_long=230000, spec_short=160000),
    _make_cot_row("2026-06-16", "GOLD", spec_long=220000, spec_short=170000),
    _make_cot_row("2026-06-09", "GOLD", spec_long=210000, spec_short=180000),
]

COT_RESPONSE_EUR = [
    _make_cot_row("2026-07-28", "EURO FX", spec_long=120000, spec_short=180000),
    _make_cot_row("2026-07-21", "EURO FX", spec_long=125000, spec_short=175000),
    _make_cot_row("2026-07-14", "EURO FX", spec_long=130000, spec_short=170000),
    _make_cot_row("2026-07-07", "EURO FX", spec_long=128000, spec_short=172000),
    _make_cot_row("2026-06-30", "EURO FX", spec_long=132000, spec_short=168000),
    _make_cot_row("2026-06-23", "EURO FX", spec_long=135000, spec_short=165000),
    _make_cot_row("2026-06-16", "EURO FX", spec_long=140000, spec_short=160000),
    _make_cot_row("2026-06-09", "EURO FX", spec_long=145000, spec_short=155000),
]

# ---------------------------------------------------------------------------
# resolve_match_string
# ---------------------------------------------------------------------------


class TestResolveMatchString(unittest.TestCase):
    """Symbol → CFTC contract name mapping."""

    def test_gold_symbols(self):
        for sym in ("XAUUSD", "XAU", "GC"):
            self.assertEqual(resolve_match_string(sym), "GOLD")

    def test_oil_symbols(self):
        for sym in ("USOIL", "CL", "WTI"):
            self.assertEqual(resolve_match_string(sym), "CRUDE OIL, LIGHT SWEET")

    def test_spx_symbols(self):
        for sym in ("SPX500", "ES"):
            self.assertEqual(resolve_match_string(sym), "E-MINI S&P 500")

    def test_eurusd(self):
        self.assertEqual(resolve_match_string("EURUSD"), "EURO FX")

    def test_btc(self):
        self.assertEqual(resolve_match_string("BTC"), "BITCOIN")

    def test_usdjpy(self):
        self.assertEqual(resolve_match_string("USDJPY"), "JAPANESE YEN")

    def test_unknown_returns_none(self):
        self.assertIsNone(resolve_match_string("UNKNOWN_ASSET"))

    def test_case_insensitive(self):
        self.assertEqual(resolve_match_string("eurusd"), "EURO FX")
        self.assertEqual(resolve_match_string("xauusd"), "GOLD")

    def test_prefix_matching(self):
        """BTCUSD should match BITCOIN via BTC prefix."""
        self.assertEqual(resolve_match_string("BTCUSD"), "BITCOIN")


# ---------------------------------------------------------------------------
# CotRecord
# ---------------------------------------------------------------------------


class TestCotRecord(unittest.TestCase):
    """CotRecord dataclass construction."""

    def test_from_api_row_parses_correctly(self):
        row = _make_cot_row()
        record = CotRecord.from_api_row(row)
        self.assertIsNotNone(record)
        self.assertEqual(record.date, "2026-07-28")
        self.assertEqual(record.market, "EURO FX")
        self.assertEqual(record.open_interest, 500000)
        self.assertEqual(record.spec_long, 150000)
        self.assertEqual(record.spec_short, 80000)
        self.assertAlmostEqual(record.spec_pct_long, 65.2, places=1)

    def test_from_api_row_handles_empty(self):
        self.assertIsNone(CotRecord.from_api_row({}))

    def test_from_api_row_handles_none(self):
        self.assertIsNone(CotRecord.from_api_row({"noncomm_positions_long_all": None}))

    def test_from_api_row_comm_net_computed(self):
        row = _make_cot_row(comm_long=200000, comm_short=80000)
        record = CotRecord.from_api_row(row)
        self.assertEqual(record.comm_net, 120000)

    def test_from_api_row_spread_fallback_field(self):
        row = _make_cot_row()
        row.pop("noncomm_postions_spread_all", None)
        row["noncomm_positions_spread"] = "15000"
        record = CotRecord.from_api_row(row)
        self.assertEqual(record.spec_spread, 15000)


# ---------------------------------------------------------------------------
# _build_signal
# ---------------------------------------------------------------------------


class TestBuildSignal(unittest.TestCase):
    """Signal construction from history."""

    def test_empty_history_returns_unknown(self):
        signal = _build_signal([])
        self.assertEqual(signal.bias, "UNKNOWN")
        self.assertEqual(signal.percentile_8w, 50)
        self.assertFalse(signal.extreme)

    def test_crowded_long_when_pct_above_70(self):
        records = [
            CotRecord(date="2026-07-28", market="GOLD", open_interest=100000,
                      spec_long=85000, spec_short=15000, spec_spread=0,
                      spec_net=70000, spec_pct_long=85.0,
                      comm_long=10000, comm_short=20000, comm_net=-10000),
            CotRecord(date="2026-07-21", market="GOLD", open_interest=100000,
                      spec_long=80000, spec_short=20000, spec_spread=0,
                      spec_net=60000, spec_pct_long=80.0,
                      comm_long=10000, comm_short=20000, comm_net=-10000),
        ]
        signal = _build_signal(records)
        self.assertEqual(signal.bias, "CROWDED LONG")

    def test_crowded_short_when_pct_below_30(self):
        records = [
            CotRecord(date="2026-07-28", market="GOLD", open_interest=100000,
                      spec_long=20000, spec_short=80000, spec_spread=0,
                      spec_net=-60000, spec_pct_long=20.0,
                      comm_long=20000, comm_short=10000, comm_net=10000),
            CotRecord(date="2026-07-21", market="GOLD", open_interest=100000,
                      spec_long=25000, spec_short=75000, spec_spread=0,
                      spec_net=-50000, spec_pct_long=25.0,
                      comm_long=20000, comm_short=10000, comm_net=10000),
        ]
        signal = _build_signal(records)
        self.assertEqual(signal.bias, "CROWDED SHORT")

    def test_net_long_between_60_and_70(self):
        records = [
            CotRecord(date="2026-07-28", market="GOLD", open_interest=100000,
                      spec_long=65000, spec_short=35000, spec_spread=0,
                      spec_net=30000, spec_pct_long=65.0,
                      comm_long=10000, comm_short=20000, comm_net=-10000),
            CotRecord(date="2026-07-21", market="GOLD", open_interest=100000,
                      spec_long=60000, spec_short=40000, spec_spread=0,
                      spec_net=20000, spec_pct_long=60.0,
                      comm_long=10000, comm_short=20000, comm_net=-10000),
        ]
        signal = _build_signal(records)
        self.assertEqual(signal.bias, "NET LONG")

    def test_net_short_between_30_and_40(self):
        records = [
            CotRecord(date="2026-07-28", market="GOLD", open_interest=100000,
                      spec_long=35000, spec_short=65000, spec_spread=0,
                      spec_net=-30000, spec_pct_long=35.0,
                      comm_long=20000, comm_short=10000, comm_net=10000),
            CotRecord(date="2026-07-21", market="GOLD", open_interest=100000,
                      spec_long=40000, spec_short=60000, spec_spread=0,
                      spec_net=-20000, spec_pct_long=40.0,
                      comm_long=20000, comm_short=10000, comm_net=10000),
        ]
        signal = _build_signal(records)
        self.assertEqual(signal.bias, "NET SHORT")

    def test_extreme_flag_triggers_at_below_10th_percentile(self):
        records = [
            CotRecord(date=f"2026-0{i+1:02d}-01", market="GOLD", open_interest=100000,
                      spec_long=1000 * (i + 1), spec_short=50000, spec_spread=0,
                      spec_net=1000 * (i + 1) - 50000, spec_pct_long=50.0,
                      comm_long=10000, comm_short=10000, comm_net=0)
            for i in range(8)
        ]
        signal = _build_signal(records)
        self.assertTrue(signal.extreme)

    def test_extreme_flag_triggers_at_above_90th_percentile(self):
        records = [
            CotRecord(date=f"2026-0{i+1:02d}-01", market="GOLD", open_interest=100000,
                      spec_long=50000, spec_short=1000 * (i + 1), spec_spread=0,
                      spec_net=50000 - 1000 * (i + 1), spec_pct_long=90.0,
                      comm_long=10000, comm_short=10000, comm_net=0)
            for i in range(8)
        ]
        signal = _build_signal(records)
        self.assertTrue(signal.extreme)

    def test_percentile_rank_between_0_and_100(self):
        for _ in range(5):
            records = [
                CotRecord(date=f"2026-0{i+1:02d}-01", market="TEST", open_interest=100000,
                          spec_long=50000 + i * 1000, spec_short=50000, spec_spread=0,
                          spec_net=i * 1000, spec_pct_long=50.0 + i,
                          comm_long=10000, comm_short=10000, comm_net=0)
                for i in range(8)
            ]
            signal = _build_signal(records)
            self.assertGreaterEqual(signal.percentile_8w, 0)
            self.assertLessEqual(signal.percentile_8w, 100)


# ---------------------------------------------------------------------------
# fetch_cot (public API)
# ---------------------------------------------------------------------------


class TestFetchCotPublic(unittest.TestCase):
    """fetch_cot() end-to-end via mocked _fetch_raw."""

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_returns_data_for_gold(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_GOLD
        result = fetch_cot("XAUUSD")
        self.assertIsNotNone(result)
        self.assertEqual(result["symbol"], "XAUUSD")
        self.assertEqual(result["match_string"], "GOLD")
        self.assertIn("latest", result)
        self.assertIn("signal", result)
        self.assertIn("history", result)

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_returns_data_for_eur(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_EUR
        result = fetch_cot("EURUSD")
        self.assertIsNotNone(result)
        self.assertEqual(result["match_string"], "EURO FX")
        self.assertIn("signal", result)

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_returns_data_for_btc(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_GOLD
        result = fetch_cot("BTCUSD")
        self.assertIsNotNone(result)
        self.assertEqual(result["match_string"], "BITCOIN")

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_signal_has_percentile_between_0_and_100(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_GOLD
        result = fetch_cot("XAUUSD")
        signal = result["signal"]
        self.assertGreaterEqual(signal["percentile_8w"], 0)
        self.assertLessEqual(signal["percentile_8w"], 100)

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_extreme_flag_true_at_extreme(self, mock_fetch_raw):
        extreme_rows = [_make_cot_row(date=f"2026-0{6-i:02d}-28", market="GOLD",
                                       spec_long=300000 - i * 100000,
                                       spec_short=100000 + i * 50000)
                        for i in range(8)]
        mock_fetch_raw.return_value = extreme_rows
        result = fetch_cot("XAUUSD")
        if result:
            self.assertIn("extreme", result["signal"])

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_returns_none_for_unknown_symbol(self, mock_fetch_raw):
        result = fetch_cot("UNKNOWN")
        self.assertIsNone(result)
        mock_fetch_raw.assert_not_called()

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_returns_none_on_empty_response(self, mock_fetch_raw):
        mock_fetch_raw.return_value = []
        result = fetch_cot("XAUUSD")
        self.assertIsNone(result)

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_latest_has_expected_fields(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_GOLD
        result = fetch_cot("XAUUSD")
        latest = result["latest"]
        for field in ("date", "market", "open_interest", "spec_long", "spec_short",
                       "spec_net", "spec_pct_long", "comm_long", "comm_short", "comm_net"):
            self.assertIn(field, latest)

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_history_has_three_fields(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_GOLD
        result = fetch_cot("XAUUSD")
        for entry in result["history"]:
            self.assertIn("date", entry)
            self.assertIn("spec_net", entry)
            self.assertIn("spec_pct_long", entry)

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_week_change_matches_history(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_GOLD
        result = fetch_cot("XAUUSD")
        signal = result["signal"]
        latest_net = result["latest"]["spec_net"]
        next_net = result["history"][1]["spec_net"]
        self.assertEqual(signal["week_change"], latest_net - next_net)

    @patch("quant_nanggroe.providers.cot_provider._fetch_raw")
    def test_fetch_cot_report_date_is_latest(self, mock_fetch_raw):
        mock_fetch_raw.return_value = COT_RESPONSE_GOLD
        result = fetch_cot("XAUUSD")
        self.assertEqual(result["report_date"], "2026-07-28")


if __name__ == "__main__":
    unittest.main(verbosity=2)
