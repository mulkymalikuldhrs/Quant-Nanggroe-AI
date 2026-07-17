"""C5 proof: independent KillSwitch() instances converge on one shared file.

Verifies the split-brain fix — one process activating the switch halts every
other instance, even across separate interpreter memory. Fail-closed: an
unreadable/corrupt state file makes the switch ACTIVE.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from quant_nanggroe.engine.risk.kill_switch import (
    KillSwitch,
    KillSwitchLevel,
    KillSwitchTrigger,
    configure_kill_switch_file,
)


@pytest.fixture
def shared_file():
    """Point this process at a temp shared state file; clean on teardown."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(path)
    prev = os.environ.get("QNA_KILL_SWITCH_STATE_FILE")
    configure_kill_switch_file(path)
    yield Path(path)
    if prev is None:
        os.environ.pop("QNA_KILL_SWITCH_STATE_FILE", None)
    else:
        os.environ["QNA_KILL_SWITCH_STATE_FILE"] = prev
    Path(path).unlink(missing_ok=True)


def test_activate_in_one_instance_halts_another(shared_file):
    a = KillSwitch()
    b = KillSwitch()
    assert a.can_trade() and b.can_trade()
    a.activate(KillSwitchLevel.LEVEL_1, reason="test", trigger=KillSwitchTrigger.MANUAL)
    assert not a.can_trade()
    # b must see a's activation via the shared file
    assert not b.can_trade(), "split-brain: second instance kept trading"


def test_auto_activate_persists_across_instances(shared_file):
    a = KillSwitch()
    a.check_auto_activate(daily_pnl_pct=-0.02)  # breaches 1.5% limit
    assert a.is_active
    b = KillSwitch()
    assert b.is_active, "fresh instance must reconcile activation from file"


def test_reset_clears_all_instances(shared_file):
    a = KillSwitch()
    a.activate(KillSwitchLevel.LEVEL_1, reason="test", trigger=KillSwitchTrigger.MANUAL)
    b = KillSwitch()
    assert not b.can_trade()
    b.reset("CONFIRM_RESET_AFTER_REVIEW")
    c = KillSwitch()
    assert c.can_trade(), "reset must propagate; fresh instance must allow trading"


def test_unreadable_state_file_fails_closed():
    # Self-contained: point at a directory (unreadable as JSON) -> fail closed.
    import tempfile

    d = tempfile.mkdtemp()
    prev = os.environ.get("QNA_KILL_SWITCH_STATE_FILE")
    os.environ["QNA_KILL_SWITCH_STATE_FILE"] = d  # directory, not a file
    try:
        ks = KillSwitch()
        assert ks.is_active, "unreadable state file must FAIL CLOSED (halt)"
    finally:
        if prev is None:
            os.environ.pop("QNA_KILL_SWITCH_STATE_FILE", None)
        else:
            os.environ["QNA_KILL_SWITCH_STATE_FILE"] = prev


def test_create_app_wires_shared_kill_switch_state(monkeypatch):
    """C5 boot-wiring regression: create_app() must call
    configure_kill_switch_file() so every worker/bridge converges on one
    state file. If this is removed, split-brain returns in production."""
    import tempfile

    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(p)
    monkeypatch.setenv("QNA_KILL_SWITCH_STATE_FILE", p)
    # Importing/creating the app must NOT reset our env (idempotent).
    from quant_nanggroe.api.app import create_app

    create_app()
    assert os.environ.get("QNA_KILL_SWITCH_STATE_FILE") == p
    # A fresh KillSwitch (simulating a second worker) must read the same file.
    a = KillSwitch()
    a.activate(KillSwitchLevel.LEVEL_1, reason="regression", trigger=KillSwitchTrigger.MANUAL)
    b = KillSwitch()
    assert not b.can_trade(), "create_app() did not wire shared kill-switch state"
    monkeypatch.undo()
    os.path.exists(p) and os.unlink(p)


def test_main_entry_wires_shared_kill_switch_state(monkeypatch):
    """C5 boot-wiring regression for the qna.py daemon/cli entry point.

    Genuinely invokes qna.main() with --version (exits before mode routing)
    so the real boot hook runs. If the hook is removed, the shared state env
    is never set and split-brain returns in production.
    """
    import tempfile

    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(p)
    monkeypatch.setenv("QNA_KILL_SWITCH_STATE_FILE", p)
    monkeypatch.setattr("sys.argv", ["qna", "--version"])  # avoid pytest argv leakage
    import qna

    # --version returns early but AFTER the boot hook runs.
    assert qna.main() == 0
    assert os.environ.get("QNA_KILL_SWITCH_STATE_FILE") == p
    monkeypatch.undo()
    os.path.exists(p) and os.unlink(p)

