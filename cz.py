import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
(root / "f1.py").unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(FAZE-1): reduce position sizing to proof-phase conservative level\n\n"
    "- autonomous.py qty formula: confidence * 0.05 (was 0.1)\n"
    "  → max ~0.045 lots on high confidence (was 0.09)\n"
    "  → 0.01 floor unchanged for micro accounts\n"
    "  → scale up only after portfolio expectancy > 0 over 50+ live trades\n"
    "- allocation gate already active at autonomous.py:1283 — narrows\n"
    "  candidates per symbol via CPCV evidence before ensemble voting"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-80:], pu.stderr[-100:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
