"""Risk guard adversarial test — break it, prove fail-closed."""
import sys, os

# Use QNA venv
venv_python = r"D:\repositories\Quant-Nanggroe-AI-worktree\.venv\Scripts\python.exe"
if os.path.exists(venv_python):
    print(f"venv python exists: {venv_python}")
else:
    print(f"venv python MISSING: {venv_python}")

# Check alternative paths
for p in [
    r"D:\repositories\Quant-Nanggroe-AI-worktree\.venv\Scripts\python.exe",
    r"D:\repositories\Quant-Nanggroe-AI-worktree\venv\Scripts\python.exe",
]:
    print(f"{p}: exists={os.path.exists(p)}")