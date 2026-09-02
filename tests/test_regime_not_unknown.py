"""Regime must not be unknown after stub fix."""
import json
from pathlib import Path
from quant_nanggroe.engine.state_writer import PaperStateWriter

def test_write_state_unknown_becomes_ranging(tmp_path):
    """write_state with regime unknown should become ranging (stub unblocks breaker)."""
    w = PaperStateWriter(state_dir=tmp_path)
    w.write_state({"total_value": 100, "regime": "unknown"})
    data = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert data["regime"] != "unknown", f"regime still unknown: {data}"
    assert data["regime"] == "ranging"

def test_write_state_with_closes_uses_detector(tmp_path):
    """With closes provided, detector should produce non-unknown regime."""
    w = PaperStateWriter(state_dir=tmp_path)
    closes = [100 + i*0.5 for i in range(50)]  # trending up
    w.write_state({"total_value": 100, "regime": "unknown", "closes": closes})
    data = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert data["regime"] != "unknown"

def test_write_state_explicit_regime_preserved(tmp_path):
    """Explicit regime should be preserved."""
    w = PaperStateWriter(state_dir=tmp_path)
    w.write_state({"total_value": 100, "regime": "trending_up"})
    data = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert data["regime"] == "trending_up"
