"""Tests: stale-data veto — freshness consumed as a VETO (FINDING #11).

A frozen feed must produce NO signal. Weekend gaps stay inside the budget.
"""
from __future__ import annotations

import unittest

import pandas as pd

from quant_nanggroe.engine.agentic.autonomous import AutonomousPipeline


def _make_pipeline() -> AutonomousPipeline:
    p = object.__new__(AutonomousPipeline)
    return p


def _df_with_last_bar(age_minutes: float, interval_min: int = 15, bars: int = 60) -> pd.DataFrame:
    now = pd.Timestamp.now()
    idx = pd.date_range(end=now - pd.Timedelta(minutes=age_minutes),
                        periods=bars, freq=f"{interval_min}min")
    return pd.DataFrame(
        {"open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05,
         "volume": 100.0},
        index=idx,
    )


class TestStaleDataVeto(unittest.TestCase):
    def setUp(self):
        self.p = _make_pipeline()

    def test_fresh_data_passes(self):
        df = _df_with_last_bar(age_minutes=5)          # 5 min < 4×15=60
        out = self.p._reject_stale(df, "EURUSD", "M15")
        self.assertIsNotNone(out)

    def test_stale_m15_blocked(self):
        df = _df_with_last_bar(age_minutes=120)        # 2h >> 60min budget
        out = self.p._reject_stale(df, "EURUSD", "M15")
        self.assertIsNone(out, "frozen M15 feed must be VETOED")

    def test_weekend_gap_d1_passes(self):
        # Fri 00:00 -> Mon 06:00 = 78h < 4×1440=5760min budget
        df = _df_with_last_bar(age_minutes=78 * 60, interval_min=1440)
        out = self.p._reject_stale(df, "XAUUSD.vxc", "D1")
        self.assertIsNotNone(out, "weekend gap must NOT veto D1 analysis")

    def test_unknown_timeframe_defaults_d1_budget(self):
        df = _df_with_last_bar(age_minutes=200)
        out = self.p._reject_stale(df, "EURUSD", "WTF")
        self.assertIsNotNone(out)

    def test_empty_df_returns_none(self):
        self.assertIsNone(self.p._reject_stale(None, "EURUSD", "M15"))
        self.assertIsNone(self.p._reject_stale(pd.DataFrame(), "EURUSD", "M15"))

    def test_bad_index_fails_closed(self):
        df = pd.DataFrame(
            {"open": [1.0] * 10, "high": [1.1] * 10, "low": [0.9] * 10,
             "close": [1.05] * 10, "volume": [100.0] * 10},
            index=list(range(10)),  # non-datetime index
        )
        out = self.p._reject_stale(df, "EURUSD", "M15")
        self.assertIsNone(out, "unprovable freshness must FAIL CLOSED")


if __name__ == "__main__":
    unittest.main()
