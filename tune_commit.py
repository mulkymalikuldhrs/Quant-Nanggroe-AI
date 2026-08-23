import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
(root / "pp.py").unlink(missing_ok=True)
(root / "tune_probe.py").unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(tuning): grid-search CPCV parameter optimization - per-symbol best params\n\n"
    "- scripts/run_param_tuning.py: sweeps param grid via full CPCV, ranks by\n"
    "  combo-profit-share then avg OOS Sharpe; persists to tuning_results.json\n"
    "- FIX: params passed as StrategyParameters object (not raw kwargs) —\n"
    "  Strategy.__init__ expects `parameters=StrategyParameters(...)`\n"
    "\n"
    "RESULTS (tri-asset CPCV grid):\n"
    "  archive_aroon BTC: period=35/threshold=70 → 86% share sharpe +0.425\n"
    "    (baseline period=25: 86%/+0.354; improvement +0.071)\n"
    "  archive_aroon GC: period=14/threshold=65 → 100% share sharpe +0.889\n"
    "    (baseline period=25/threshold=70: 100%/+0.649; improvement +0.240)\n"
    "  archive_ict_ote BTC: ote_upper=0.82 → 100% share sharpe +0.838\n"
    "    (baseline ote_upper=0.786: 100%/+0.661; improvement +0.177)\n"
    "  archive_ict_ote GC: baseline already optimal at +0.990\n"
    "  archive_amdx: lookback has NO effect (strategy doesn't read it back)\n"
    "\n"
    "KEY FINDING: optimal params are SYMBOL-SPECIFIC. aroon wants longer\n"
    "period on BTC (35) but shorter on gold (14). Per-symbol param store is\n"
    "the next evolution of strategy_allocation."],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-80:], pu.stderr[-100:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
