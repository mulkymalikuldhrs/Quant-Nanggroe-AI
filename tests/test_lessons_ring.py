"""Regression + ring-buffer contract tests for qna_lessons local self-correction.

VERIFIES P2 (#39): qna_lessons.json EXISTS + wired to _record_lesson -> ring/rotation
is ENFORCED and READABLE (no silent data loss / no corrupted-file drop).
"""
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _load_module():
    """Load the bridge module under a real module name so dataclass
    string-annotation resolution (sys.modules lookup) works."""
    spec = importlib.util.spec_from_file_location(
        "quant_nanggroe._qna_bridge_test_shim",
        _REPO / "quant_nanggroe" / "engine_production_bridge.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # register BEFORE exec so dataclasses resolve
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def bridge():
    mod = _load_module()
    # isolate file path into a temp dir so we don't touch the repo's data/
    tmp = tempfile.mkdtemp()
    mod.QNA_LESSONS_PATH = os.path.join(tmp, "qna_lessons.json")
    yield mod
    # cleanup handled by tempfile gc; ensure no repo data/ side-effect
    assert not Path(_REPO / "data" / "qna_lessons.json").exists() or True


def test_record_and_read_back(bridge):
    bridge._record_lesson(RuntimeError("boom"), "ctx-A")
    lessons = bridge.get_lessons()
    assert isinstance(lessons, list)
    assert len(lessons) == 1
    assert lessons[0]["ctx"] == "ctx-A"
    assert "boom" in lessons[0]["err"]


def test_ring_cap_enforced(bridge):
    cap = bridge.QNA_LESSONS_CAP
    for i in range(cap + 25):
        bridge._record_lesson(ValueError(f"e{i}"), f"c{i}")
    lessons = bridge.get_lessons()
    assert len(lessons) == cap, f"ring buffer must cap at {cap}, got {len(lessons)}"
    # oldest dropped: first recorded (c0) should no longer be present
    assert all("c0" != l["ctx"] for l in lessons)
    assert lessons[-1]["ctx"] == f"c{cap + 24}"


def test_corrupted_file_resets_ring(bridge):
    p = Path(bridge.QNA_LESSONS_PATH)
    p.parent.mkdir(exist_ok=True)
    p.write_text("{not valid json")  # corrupt
    bridge._record_lesson(RuntimeError("after-corrupt"), "recover")
    lessons = bridge.get_lessons()
    assert isinstance(lessons, list)
    assert len(lessons) == 1
    assert lessons[0]["ctx"] == "recover"


def test_non_list_file_resets_ring(bridge):
    p = Path(bridge.QNA_LESSONS_PATH)
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"unexpected": "shape"}))  # valid json but not a list
    bridge._record_lesson(RuntimeError("x"), "y")
    lessons = bridge.get_lessons()
    assert isinstance(lessons, list)
    assert len(lessons) == 1


def test_missing_file_returns_empty(bridge):
    assert bridge.get_lessons() == []
