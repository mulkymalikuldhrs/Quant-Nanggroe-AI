import subprocess, os
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
env = dict(os.environ); env["PYTHONPATH"] = ""
r = subprocess.run([r"C:\Python314\python.exe", "-m", "pytest",
    "tests/test_engine/test_strategy_allocation.py",
    "tests/test_api/test_export_center.py",
    "-q"], capture_output=True, text=True, cwd=root, env=env, timeout=180)
print((r.stdout + r.stderr)[-200:])
