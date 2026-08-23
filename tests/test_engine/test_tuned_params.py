"""Tuned param injection test (per-symbol best params from CPCV grid search)."""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
from unittest.mock import patch

from quant_nanggroe.engine.strategy_allocation import best_params_for

SAMPLE_TUNING = {
    "archive_aroon": {
        "GC=F": {
            "best_params": {"period": 14, "threshold": 65.0},
            "best_profit_share": 1.0,
            "best_avg_sharpe": 0.889,
            "improved": True,
        },
        "BTC-USD": {
            "best_params": {"period": 35, "threshold": 70.0},
            "best_profit_share": 0.86,
            "best_avg_sharpe": 0.425,
            "improved": True,
        },
    },
}

_BASE = pathlib.Path(r"C:\Users\Hi\AppData\Local\Temp\opencode")


def _make_tuning():
    _BASE.mkdir(parents=True, exist_ok=True)
    d = pathlib.Path(tempfile.mkdtemp(dir=str(_BASE)))
    p = d / "tuning_results.json"
    p.write_text(json.dumps(SAMPLE_TUNING), encoding="utf-8")
    return d, p


def test_gold_gets_short_period():
    d, p = _make_tuning()
    with patch("quant_nanggroe.engine.strategy_allocation._TUNING_PATH", p):
        params = best_params_for("archive_aroon", "XAUUSD.vx")
    shutil.rmtree(d, ignore_errors=True)
    assert params == {"period": 14, "threshold": 65.0}


def test_btc_gets_long_period():
    d, p = _make_tuning()
    with patch("quant_nanggroe.engine.strategy_allocation._TUNING_PATH", p):
        params = best_params_for("archive_aroon", "BTCUSDT")
    shutil.rmtree(d, ignore_errors=True)
    assert params == {"period": 35, "threshold": 70.0}


def test_no_tuning_returns_none():
    d = pathlib.Path(tempfile.mkdtemp(dir=str(_BASE)))
    missing = d / "none.json"
    with patch("quant_nanggroe.engine.strategy_allocation._TUNING_PATH", missing):
        assert best_params_for("archive_aroon", "XAUUSD") is None
    shutil.rmtree(d, ignore_errors=True)
