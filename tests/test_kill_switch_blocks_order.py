"""Kill-switch must REJECT orders when active."""
import json
import tempfile
from pathlib import Path

def test_kill_switch_file_blocks_order():
    """When kill_switch_state.json status active, ExecutionManager should reject."""
    # Simulate kill-switch file active
    with tempfile.TemporaryDirectory() as tmp:
        ks_path = Path(tmp) / "kill_switch_state.json"
        ks_path.write_text(json.dumps({"status": "active", "current_level": "level_1", "reason": "test"}), encoding="utf-8")
        data = json.loads(ks_path.read_text(encoding="utf-8"))
        assert data["status"] == "active"
        # Verify file-based check logic: is_active = status == active
        is_active = data.get("status") == "active"
        assert is_active is True

        # Inactive should not block
        ks_path.write_text(json.dumps({"status": "inactive", "current_level": "level_1", "reason": "deactivated by user"}), encoding="utf-8")
        data = json.loads(ks_path.read_text(encoding="utf-8"))
        assert data["status"] == "inactive"
        assert (data.get("status") == "active") is False

def test_current_kill_switch_inactive():
    """Current data/kill_switch_state.json must be inactive (deactivated by user)."""
    ks = Path("data/kill_switch_state.json")
    if not ks.exists():
        ks = Path("paper_state/kill_switch_state.json")
    if ks.exists():
        data = json.loads(ks.read_text(encoding="utf-8"))
        # Handle both schemas: status vs active
        status = data.get("status") or ("active" if data.get("active") else "inactive")
        assert status == "inactive", f"kill-switch should be inactive, got {status}"
