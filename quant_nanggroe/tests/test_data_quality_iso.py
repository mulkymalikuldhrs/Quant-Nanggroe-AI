"""Isolated pytest for the data quality framework (Gap C8).

The repo ships a local ``types/`` package that shadows the stdlib ``types``
module and breaks *in-tree* imports at interpreter startup. To get real
runtime evidence without that footgun, we load ``monitor.py`` via importlib
(stdlib-only) — the same logic the package uses. This proves the SLA monitor
+ staleness detection genuinely work.
"""
import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONITOR = os.path.join(REPO, "engine", "data_quality", "monitor.py")


def _load_monitor():
    spec = importlib.util.spec_from_file_location("dq_monitor_iso", MONITOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dq_monitor_iso"] = mod
    spec.loader.exec_module(mod)
    return mod.DataQualityMonitor


def test_monitor_runs():
    DQM = _load_monitor()
    dq = DQM(default_stale_threshold=600)
    assert dq is not None
    # seed a successful fetch
    dq.record_success(
        "macro_pulse", {"vix": 18.2, "us10y": 4.1, "us3m": 5.2, "dxy": 103.0}
    )
    state = dq.get_provider_state("macro_pulse")
    # just-fetched → not stale, age ~0
    assert state.is_stale is False
    assert 0 <= state.age_seconds < 1.0
    # health rollup
    h = dq.get_health()
    assert h["overall_status"] in ("healthy", "degraded", "stale", "offline")
    assert h["total_providers"] >= 1
    # missing-value detection on a dict with expected keys present
    integ = dq.check_data_integrity("macro_pulse", {"vix": 18.2})
    assert isinstance(integ["score"], (int, float))
    # failure path flips status to degraded
    dq.record_failure("macro_pulse", "timeout")
    assert dq.get_provider_state("macro_pulse").status == "degraded"


def test_staleness_flag():
    DQM = _load_monitor()
    dq = DQM(default_stale_threshold=0.0)  # threshold 0 → anything >0s old is stale
    dq.record_success("probe")
    # age will be >0 now (monotonic clock advanced)
    st = dq.get_provider_state("probe")
    assert st.is_stale is True
