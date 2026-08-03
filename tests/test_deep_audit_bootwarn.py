"""Deep-audit tests: boot WARN observability for degraded state (GAP-D3 follow-up)."""

import os


def test_boot_warn_logic_kill_switch_active_source():
    """create_app _background_init must WARN when kill switch is active at boot."""
    import quant_nanggroe.api.app as app_mod

    src = open(app_mod.__file__, encoding="utf-8").read()
    assert "boot_kill_switch_active" in src
    assert "boot_execution_backend_unavailable" in src
    assert "get_execution_backend_status" in src


def test_kill_switch_state_file_resettable_to_inactive():
    """Kill switch file can be reset to inactive via CONFIRM_RESET_AFTER_REVIEW."""
    import json
    from pathlib import Path

    # Point at a temp state file so we don't touch the real one
    import tempfile

    tf = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tf.write(json.dumps({"status": "active", "current_level": "level_2", "activated_at": "2026-08-03T00:00:00+00:00", "reason": "Test activation"}).encode())
    tf.close()
    os.environ["QNA_KILL_SWITCH_STATE_FILE"] = tf.name
    try:
        from quant_nanggroe.engine.risk.kill_switch import KillSwitch, configure_kill_switch_file

        configure_kill_switch_file()
        ks = KillSwitch()
        assert ks.is_active is True
        res = ks.reset("CONFIRM_RESET_AFTER_REVIEW")
        assert res["status"] == "RESET"
        # re-read file
        data = json.loads(Path(tf.name).read_text(encoding="utf-8"))
        assert data["status"] == "inactive"
    finally:
        os.environ.pop("QNA_KILL_SWITCH_STATE_FILE", None)
        Path(tf.name).unlink(missing_ok=True)
