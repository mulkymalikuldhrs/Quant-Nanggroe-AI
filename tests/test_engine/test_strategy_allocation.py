"""Per-symbol CPCV allocation tests (CANONICAL 15.6 deployment finding)."""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
from unittest.mock import patch

import pytest

from quant_nanggroe.engine import strategy_allocation as sa


SAMPLE = {
    "archive_aroon": {
        "BTC-USD": {"n_combinations": 14, "combo_profit_share": 0.86,
                     "avg_oos_sharpe": 0.356},
        "EURUSD=X": {"n_combinations": 14, "combo_profit_share": 0.64,
                      "avg_oos_sharpe": 0.329},
        "GC=F": {"n_combinations": 14, "combo_profit_share": 1.0,
                  "avg_oos_sharpe": 0.649},
    },
    "archive_amdx": {
        "BTC-USD": {"n_combinations": 14, "combo_profit_share": 0.93},
        "GC=F": {"n_combinations": 14, "combo_profit_share": 0.93},
    },
    "kaufman_ama": {
        "EURUSD=X": {"n_combinations": 14, "combo_profit_share": 0.71},
    },
    "weak_strategy": {
        "GC=F": {"n_combinations": 14, "combo_profit_share": 0.29},
    },
}


@pytest.fixture()
def sample_registry():
    import tempfile
    base = pathlib.Path(r"C:\Users\Hi\AppData\Local\Temp\opencode")
    base.mkdir(parents=True, exist_ok=True)
    d = pathlib.Path(tempfile.mkdtemp(dir=str(base)))
    p = d / "cpcv_registry.json"
    p.write_text(json.dumps(SAMPLE), encoding="utf-8")
    with patch.object(sa, "_REGISTRY_PATH", p):
        yield p
    shutil.rmtree(d, ignore_errors=True)


class TestAllocation:
    def test_gold_admits_aroon_not_amdx(self, sample_registry):
        got = sa.admitted_for_symbol("XAUUSD.vx")
        assert got is not None
        assert "aroon" in got  # archive_ prefix stripped
        assert "weak_strategy" not in got

    def test_crypto_admits_amdx(self, sample_registry):
        got = sa.admitted_for_symbol("BTCUSDT")
        assert "amdx" in got  # archive_ prefix stripped
        assert "kaufman_ama" not in got

    def test_forex_admits_kaufman(self, sample_registry):
        got = sa.admitted_for_symbol("EURUSD")
        assert "kaufman_ama" in got

    def test_low_share_excluded(self, sample_registry):
        got = sa.admitted_for_symbol("XAUUSD")
        assert "weak_strategy" not in got

    def test_unknown_symbol_empty_not_none(self, sample_registry):
        # evidence exists -> empty list means DO NOT trade unproven
        assert sa.admitted_for_symbol("TOTALLYUNKNOWN") == []

    def test_no_registry_returns_none(self):
        import tempfile
        base = pathlib.Path(r"C:\Users\Hi\AppData\Local\Temp\opencode")
        base.mkdir(parents=True, exist_ok=True)
        d = pathlib.Path(tempfile.mkdtemp(dir=str(base)))
        missing = d / "none.json"
        with patch.object(sa, "_REGISTRY_PATH", missing):
            assert sa.admitted_for_symbol("XAUUSD") is None
        shutil.rmtree(d, ignore_errors=True)


    def test_allocation_map_shape(self, sample_registry):
        m = sa.allocation_map()
        assert set(m) <= {"BTC-USD", "EURUSD=X", "GC=F"}
        assert "archive_aroon" in m["GC=F"]

    def test_symbol_normalize_variants(self, sample_registry):
        a = sa.admitted_for_symbol("XAUUSD.vx")
        b = sa.admitted_for_symbol("xauusd")
        c = sa.admitted_for_symbol("XAU-USD")
        assert a == b == c
