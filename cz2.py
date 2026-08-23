import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
for f in ["f3.py", "cz.py", "cw.py"]:
    (root / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(FAZE-0.3): strategy attribution via MT5 comment propagation\n\n"
    "- autonomous.py Order construction: injects strategy_name + symbol into\n"
    "  order.metadata so every trade carries its origin strategy\n"
    "- connectors/mt5_broker.py place_order: reads order.metadata.strategy_name\n"
    "  and sets it as MT5 req['comment'] (max 31 chars) — this propagates\n"
    "  through MT5 terminal to history_deals_get() for journal_sync to parse\n"
    "- journal_sync._attribute_strategy already parses known names from comment\n"
    "- scripts/fix_attribution.py: backfills single-specialist symbols\n"
    "\n"
    "NOTE: 210/243 historical trades remain 'unknown' because they were placed\n"
    "before this fix. All NEW trades will carry correct strategy_name."],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-80:], pu.stderr[-100:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
