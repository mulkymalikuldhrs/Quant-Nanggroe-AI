import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
for f in ["c10.py", "rt.py"]:
    (root / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(tuned-params): per-symbol tuned params injected into live signal generation\n\n"
    "- strategy_allocation.best_params_for(strategy, symbol): reads\n"
    "  data/tuning_results.json (CPCV grid-search output), returns best params\n"
    "  for that strategy on the symbol's asset class; None when no data\n"
    "- autonomous ensemble: injects tuned params into each strategy instance\n"
    "  before generate_signal — additive, never blocks signal generation\n"
    "- Tests: 3/3 (gold short period, BTC long period, no-data None)\n"
    "\n"
    "CLOSES THE LOOP: CPCV evidence -> allocation gate -> tuned params ->\n"
    "signal generation -> risk -> execution -> awareness -> reflect -> evolve"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-80:], pu.stderr[-100:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
