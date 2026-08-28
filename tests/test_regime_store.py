#!/usr/bin/env python3
"""Tests: RegimeStore — SQLite-backed regime history persistence."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import tempfile

from quant_nanggroe.engine.regime.hmm_detector import Regime, RegimeState
from quant_nanggroe.engine.regime.regime_store import RegimeStore


class TestRegimeStore(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmpfile.close()
        self.store = RegimeStore(db_path=self.tmpfile.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmpfile.name)

    def _make_state(self, regime=Regime.BULL, confidence=0.8, method="hmm", features=None):
        return RegimeState(
            regime=regime, confidence=confidence, method=method,
            features=features or {},
        )

    def test_init_creates_table(self):
        conn = self.store._get_conn()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='regime_history'")
        self.assertIsNotNone(cursor.fetchone())

    def test_store_returns_id(self):
        state = self._make_state()
        record_id = self.store.store(state)
        self.assertGreater(record_id, 0)

    def test_get_latest_returns_none_when_empty(self):
        result = self.store.get_latest()
        self.assertIsNone(result)

    def test_get_latest_returns_most_recent(self):
        self.store.store(self._make_state(regime=Regime.BEAR, confidence=0.6))
        self.store.store(self._make_state(regime=Regime.BULL, confidence=0.9))
        latest = self.store.get_latest()
        self.assertEqual(latest.regime, Regime.BULL)
        self.assertAlmostEqual(latest.confidence, 0.9)

    def test_store_and_retrieve_same_state(self):
        state = self._make_state(regime=Regime.CRISIS, confidence=0.95, method="macro",
                                 features={"gdp": -1.0, "inflation": 4.0})
        self.store.store(state)
        latest = self.store.get_latest()
        self.assertEqual(latest.regime, Regime.CRISIS)
        self.assertAlmostEqual(latest.confidence, 0.95)
        self.assertEqual(latest.method, "macro")
        self.assertIn("gdp", latest.features)

    def test_query_returns_all(self):
        self.store.store(self._make_state(regime=Regime.BULL))
        self.store.store(self._make_state(regime=Regime.BEAR))
        results = self.store.query(limit=10)
        self.assertEqual(len(results), 2)

    def test_query_respects_limit(self):
        for _ in range(5):
            self.store.store(self._make_state())
        results = self.store.query(limit=3)
        self.assertEqual(len(results), 3)

    def test_query_respects_offset(self):
        for i in range(5):
            self.store.store(self._make_state(confidence=0.1 * i))
        all_results = self.store.query(limit=10)
        offset_results = self.store.query(limit=10, offset=2)
        self.assertEqual(len(all_results), 5)
        self.assertEqual(len(offset_results), 3)

    def test_regime_distribution(self):
        self.store.store(self._make_state(regime=Regime.BULL))
        self.store.store(self._make_state(regime=Regime.BULL))
        self.store.store(self._make_state(regime=Regime.BEAR))
        dist = self.store.get_regime_distribution()
        self.assertEqual(dist.get("BULL"), 2)
        self.assertEqual(dist.get("BEAR"), 1)

    def test_regime_distribution_with_since(self):
        self.store.store(self._make_state(regime=Regime.BULL))
        dist = self.store.get_regime_distribution(since="2000-01-01")
        self.assertGreater(dist.get("BULL", 0), 0)

    def test_regime_distribution_empty(self):
        dist = self.store.get_regime_distribution()
        self.assertEqual(dist, {})

    def test_prune_removes_old_records(self):
        for _ in range(10):
            self.store.store(self._make_state())
        deleted = self.store.prune(keep_last=3)
        self.assertGreater(deleted, 0)
        remaining = self.store.query(limit=100)
        self.assertLessEqual(len(remaining), 3)

    def test_prune_with_fewer_records_than_keep(self):
        self.store.store(self._make_state())
        deleted = self.store.prune(keep_last=100)
        self.assertEqual(deleted, 0)

    def test_close_releases_connection(self):
        self.store.close()
        self.assertIsNone(self.store._local.conn)

    def test_store_with_features(self):
        features = {"mean_return": 0.001, "volatility": 0.02, "adx": 30}
        state = self._make_state(regime=Regime.BULL, features=features)
        self.store.store(state)
        latest = self.store.get_latest()
        self.assertEqual(latest.features.get("mean_return"), 0.001)

    def test_query_returns_dicts_with_keys(self):
        self.store.store(self._make_state())
        results = self.store.query()
        self.assertIn("regime", results[0])
        self.assertIn("confidence", results[0])
        self.assertIn("method", results[0])
        self.assertIn("features", results[0])
        self.assertIn("timestamp", results[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
