import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
for f in ["cpcv_test.py", "rd.py"]:
    (root / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(PROVE): CPCV per-combo refit validation - tri-asset evidence for top strategies\n\n"
    "- walk_forward.analyze_strategy now dispatches mode='cpcv' to new\n"
    "  _analyze_strategy_cpcv(): splits bars into n_groups, refits strategy\n"
    "  per combination of held-out test groups with purge+embargo, generates\n"
    "  signals bar-by-bar on OOS bars only (no lookahead)\n"
    "- RE-FIXED after external sync reverted twice: direction-first enum\n"
    "  signal mapping + vol-scaling Series->scalar (engine._execute_bar)\n"
    "- ROOT CAUSE of all-zero legacy backtests found: wrapper classes lack\n"
    "  warmup_period() -> 20-bar slices made generate_signal raise -> silent\n"
    "  except turned everything into zeros. Fix: safe default warmup=60 +\n"
    "  first-error logging instead of total silence\n"
    "- engine defense-in-depth: stray enum/object in signal frame coerced to 0\n"
    "- scripts/run_cpcv_validation.py: tri-asset CPCV runner, combo-profit-\n"
    "  share robustness metric, survivor ranking by weakest-link; results in\n"
    "  data/cpcv_registry.json\n"
    "- HONEST RESULT: no strategy survives CPCV with min-sharpe>0 across all\n"
    "  3 assets. Specialists identified: aroon (GC 100%/14 combos +0.649,\n"
    "  BTC 86%), ict_ote (GC 14/14 +0.990), kaufman_ama (EURUSD +0.672,\n"
    "  GC 13/14 +1.083), amdx (BTC 93% +0.627). Per-symbol allocation is the\n"
    "  correct deployment, not one-size-fits-all"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-100:], pu.stderr[-120:])
