import subprocess, os
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
env = dict(os.environ); env["PYTHONPATH"] = ""
r = subprocess.run([r"C:\Python314\python.exe", "-m", "pytest",
    "tests/test_connectors/test_mt5_connector_connect.py",
    "tests/test_api/test_config_files.py", "-q"],
    capture_output=True, text=True, cwd=root, env=env, timeout=240)
out = r.stdout + r.stderr
print(out[-500:])
