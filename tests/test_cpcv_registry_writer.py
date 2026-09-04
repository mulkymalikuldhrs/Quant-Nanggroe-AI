"""Writer-extension tests for scripts/run_cpcv_validation.py build_cpcv_entry.

Covers: (a) new keys present-or-null on synthetic analyzer output,
(b) old keys byte-identical to legacy writer, (c) fail-soft None when
analyzer windows lack trade stats. No network, no yfinance.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.run_cpcv_validation import build_cpcv_entry


def _full_windows():
    return [
        SimpleNamespace(out_of_sample_sharpe=0.5, out_of_sample_return=0.02,
                        out_of_sample_max_dd=-0.01, oos_trades=10),
        SimpleNamespace(out_of_sample_sharpe=-0.2, out_of_sample_return=-0.01,
                        out_of_sample_max_dd=-0.05, oos_trades=6),
    ]


def test_new_keys_present_on_full_windows():
    entry = build_cpcv_entry("BTC-USD", _full_windows())
    for k in ("win_rate", "total_trades", "avg_oos_return", "max_oos_dd"):
        assert k in entry, f"missing new key {k}"
    assert entry["total_trades"] == 16
    assert entry["avg_oos_return"] == round((0.02 + -0.01) / 2, 4)
    assert entry["max_oos_dd"] == round(min(-0.01, -0.05), 4)
    # WalkForwardResult carries no per-window win_rate -> explicit null
    assert entry["win_rate"] is None


def test_old_keys_unchanged():
    entry = build_cpcv_entry("GC=F", _full_windows())
    assert entry["symbol"] == "GC=F"
    assert entry["n_combinations"] == 2
    assert entry["profitable_combos"] == 1
    assert entry["combo_profit_share"] == round(0.5, 4)
    assert entry["avg_oos_sharpe"] == round((0.5 + -0.2) / 2, 4)
    assert entry["min_sharpe"] == round(-0.2, 4)
    assert entry["max_sharpe"] == round(0.5, 4)


def test_fail_soft_when_no_trade_stats():
    legacy = [SimpleNamespace(out_of_sample_sharpe=0.3),
              SimpleNamespace(out_of_sample_sharpe=-0.1)]
    entry = build_cpcv_entry("EURUSD=X", legacy)  # must not crash
    assert entry["n_combinations"] == 2
    assert entry["total_trades"] is None
    assert entry["avg_oos_return"] is None
    assert entry["max_oos_dd"] is None
    assert entry["win_rate"] is None


def test_empty_windows_fail_soft():
    entry = build_cpcv_entry("BTC-USD", [])
    assert entry["n_combinations"] == 0
    assert entry["min_sharpe"] is None
    assert entry["max_sharpe"] is None
    assert entry["total_trades"] is None
    assert entry["win_rate"] is None


def test_win_rate_aggregated_when_pipeline_provides_it():
    wins = [SimpleNamespace(out_of_sample_sharpe=0.4, win_rate=0.6),
            SimpleNamespace(out_of_sample_sharpe=0.2, win_rate=0.4)]
    entry = build_cpcv_entry("BTC-USD", wins)
    assert entry["win_rate"] == round((0.6 + 0.4) / 2, 4)
