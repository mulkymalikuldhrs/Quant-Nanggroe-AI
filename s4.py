import pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
au = (root / "quant_nanggroe/engine/agentic/autonomous.py").read_text(encoding="utf-8", errors="ignore")
lines = au.splitlines()
# Find where signals are aggregated/voted
for i, l in enumerate(lines, 1):
    s = l.strip()
    if ("SignalAggregator" in s or "signal_aggregator" in s
            or "aggregate" in s.lower() and "signal" in s.lower()):
        print(f"{i}: {s[:120]}")

# Also find _ensemble_signal or similar
for i, l in enumerate(lines, 1):
    if "_ensemble_signal" in l or "def _make_decision" in l:
        print(f"{i}: {l.strip()[:120]}")

# Check if buy_weight/sell_weight aggregation exists (the old ensemble)
for i, l in enumerate(lines, 1):
    if "buy_weight" in l or "sell_weight" in l:
        print(f"OLD_ENSEMBLE {i}: {l.strip()[:110]}")
