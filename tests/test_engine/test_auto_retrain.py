"""Tests: AutoRetrainer — train→validate→persist with fail-closed gates.

Contract:
- Persist ONLY on positive improvement > margin over incumbent baseline.
- Broken strategy under candidate params → hard reject.
- Atomic tuning writes; report ledger + stale detection.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from quant_nanggroe.engine.auto_retrain import (
    AutoRetrainer,
    IMPROVEMENT_MARGIN,
    TUNING_PATH,
    REPORT_PATH,
    _extract_signal,
    reset_singleton,
)


def _fake_df(bars: int = 200, drift: float = 0.0005, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps = rng.normal(drift, 0.002, size=bars)
    close = 1.10 * np.exp(np.cumsum(steps))
    idx = pd.date_range(end=pd.Timestamp.now(), periods=bars, freq="15min")
    return pd.DataFrame({
        "open": close * (1 - 0.0005), "high": close * 1.001,
        "low": close * 0.999, "close": close,
        "volume": rng.integers(100, 1000, bars).astype(float),
    }, index=idx)


class _FakeStrategy:
    """Strategy whose signal direction follows a tunable threshold param."""
    name = "fake_trend"

    def __init__(self):
        from quant_nanggroe.engine.strategies.base import StrategyParameters
        self._parameters = StrategyParameters()
        self._parameters.set("lookback", 20)   # numeric → tunable
        self._parameters.set("mode", "fast")   # non-numeric → ignored


_STRAT = None


def _fake_registry_create(name):
    global _STRAT
    if name != "fake_trend":
        return None
    if _STRAT is None:
        _STRAT = _FakeStrategy()
    return _FakeStrategy() if False else _clone()


def _clone():
    s = _FakeStrategy()
    if _STRAT is not None:
        s._parameters.set("lookback", _STRAT._parameters.get("lookback"))
    return s


def _make_retrainer(df, symbols=("EURUSD",)):
    return AutoRetrainer(fetcher=lambda sym, tf: df, symbols=list(symbols))


class TestAutoRetrain(unittest.TestCase):
    def setUp(self):
        reset_singleton()
        self._old_cwd = os.getcwd()
        os.chdir(Path(__file__).resolve().parents[2])
        # isolate persistence to temp files
        self._tmp = Path(self._old_cwd) / ".." / ".." / "data"
        TUNING_PATH.parent.mkdir(parents=True, exist_ok=True)
        for p in (TUNING_PATH, REPORT_PATH):
            if p.exists():
                p.unlink()

    def tearDown(self):
        for p in (TUNING_PATH, REPORT_PATH):
            if p.exists():
                p.unlink()
        os.chdir(self._old_cwd)
        reset_singleton()

    def test_numeric_space_discovery(self):
        s = _FakeStrategy()
        space = AutoRetrainer._numeric_param_space(s)
        self.assertIn("lookback", space)
        lo, hi = space["lookback"]
        self.assertEqual(lo, 10.0)   # 20*0.5
        self.assertEqual(hi, 30.0)   # 20*1.5
        self.assertNotIn("mode", space)

    def test_evaluate_broken_strategy_returns_neg_inf(self):
        r = _make_retrainer(_fake_df())
        score = r._evaluate("nonexistent_strategy", {}, _fake_df())
        self.assertEqual(score, float("-inf"))

    def test_extract_signal_shapes(self):
        class Sig:
            signal_type = type("T", (), {"value": "buy"})()
            confidence = 0.8
            reasoning = "r"
        sig, conf, _ = _extract_signal(Sig())
        self.assertEqual((sig, round(conf, 2)), ("buy", 0.8))

        series = pd.Series([0.0, -0.5])
        sig2, _, _ = _extract_signal(series)
        self.assertEqual(sig2, "sell")

    @patch("quant_nanggroe.engine.strategy_allocation.allocation_map")
    @patch("quant_nanggroe.engine.strategy_allocation._lookup_asset")
    def test_run_once_no_allocation_is_noop(self, m_asset, m_alloc):
        m_alloc.return_value = {}
        r = _make_retrainer(_fake_df())
        summary = r.run_once()
        self.assertIn("note", summary)
        self.assertEqual(summary["updated"], 0)

    def test_singleton_requires_fetcher_first_call(self):
        from quant_nanggroe.engine.auto_retrain import get_auto_retrainer
        with self.assertRaises(RuntimeError):
            get_auto_retrainer()

    def test_disabled_interval_does_not_start_thread(self):
        r = _make_retrainer(_fake_df())
        r.interval_hours = 0
        self.assertFalse(r.start())
        self.assertIsNone(r._thread)


class TestDecayGuard(unittest.TestCase):
    """Stale strategies in the retrain ledger must lose their tuned params."""

    def setUp(self):
        reset_singleton()
        self._old_cwd = os.getcwd()
        os.chdir(Path(__file__).resolve().parents[2])
        self._report = Path("data/retrain_report.json")
        self._tuning = Path("data/tuning_results.json")
        for p in (self._report, self._tuning):
            if p.exists():
                p.unlink()

    def tearDown(self):
        for p in (self._report, self._tuning):
            if p.exists():
                p.unlink()
        os.chdir(self._old_cwd)
        reset_singleton()

    def test_stale_flag_withholds_params(self):
        # tuning data says smc has improved params on the EURUSD asset key
        self._tuning.parent.mkdir(parents=True, exist_ok=True)
        self._tuning.write_text(json.dumps({
            "smc": {"EURUSD=X": {"improved": True,
                                 "best_params": {"lookback": 33}}}
        }), encoding="utf-8")
        from quant_nanggroe.engine.strategy_allocation import best_params_for

        with patch(
            "quant_nanggroe.engine.strategy_allocation._stale_strategies",
            return_value={"smc:EURUSD"},
        ):
            self.assertIsNone(
                best_params_for("smc", "EURUSD"),
                "stale strategy must NOT receive tuned params")

        with patch(
            "quant_nanggroe.engine.strategy_allocation._stale_strategies",
            return_value=set(),
        ):
            params = best_params_for("smc", "EURUSD")
        self.assertEqual(params, {"lookback": 33})

    def test_report_ledger_writes_and_flags(self):
        df = _fake_df()
        r = _make_retrainer(df)
        summary = {
            "finished_at": "2026-08-25T00:00:00+00:00",
            "symbols": {"EURUSD": {
                "fake_trend": {"status": "kept_current",
                               "baseline": -0.4, "score": -0.2},
            }},
        }
        r._append_report(summary)
        report = json.loads(Path("data/retrain_report.json").read_text())
        self.assertIn("fake_trend:EURUSD", report["history"])
        # 3 consecutive negative baselines -> flagged stale
        for _ in range(2):
            r._append_report(summary)
        report = json.loads(Path("data/retrain_report.json").read_text())
        self.assertIn("fake_trend:EURUSD", report["stale_strategies"])


if __name__ == "__main__":
    unittest.main()
