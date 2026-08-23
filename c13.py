import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root))
print("STATUS:", repr(r.stdout[:300]))
print(subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True, cwd=str(root)).stdout)
checks = [
    "quant_nanggroe/engine/strategy_allocation.py",
    "quant_nanggroe/engine/journal_sync.py",
    "quant_nanggroe/engine/analytics/trade_awareness.py",
    "quant_nanggroe/engine/risk/trailing_stop.py",
    "quant_nanggroe/engine/risk/trading_profile.py",
    "quant_nanggroe/api/routes/export.py",
    "scripts/qna_tray.py",
    "CANONICAL.md",
]
missing = [f for f in checks if not (root / f).exists()]
print("MISSING:", missing or "none")
