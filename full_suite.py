import subprocess, os
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
env = dict(os.environ); env["PYTHONPATH"] = ""
r = subprocess.run([r"C:\Python314\python.exe", "-m", "pytest",
    "tests/test_engine/test_strategy_allocation.py",
    "tests/test_engine/test_self_aware_gate3.py",
    "tests/test_engine/test_tuned_params.py",
    "tests/test_risk/test_trailing_stop_gate7.py",
    "tests/test_risk/test_trading_profile.py",
    "tests/test_api/test_export_center.py",
    "tests/test_api/test_config_files.py",
    "tests/test_connectors/test_mt5_connector_connect.py",
    "-q"], capture_output=True, text=True, cwd=root, env=env, timeout=280)
print((r.stdout + r.stderr)[-500:])
