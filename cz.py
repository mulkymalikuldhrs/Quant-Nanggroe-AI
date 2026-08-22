import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
for f in ["pa.py", "rt.py"]:
    (root / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(allocation): per-symbol CPCV strategy allocation wired into live ensemble\n\n"
    "- engine/strategy_allocation.py: maps trading symbols to asset-class\n"
    "  evidence (BTC-USD/EURUSD=X/GC=F), admits strategies with\n"
    "  combo_profit_share >= 0.50 over >= 10 combinations from\n"
    "  data/cpcv_registry.json. Fail-closed: no registry -> None (caller keeps\n"
    "  lifecycle behavior); registry present but nothing qualifies -> empty\n"
    "  list (no unproven trading on that symbol)\n"
    "- autonomous ensemble: narrows candidate strategies per symbol after the\n"
    "  lifecycle gate — implements CANONICAL 15.6 finding that specialists\n"
    "  beat one-size-fits-all admission\n"
    "Tests: 10/10 (8 allocation + 2 awareness) pass"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-100:], pu.stderr[-120:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
