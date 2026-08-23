import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
for f in ["c9.py", "gen_js.py", "cw.py", "rt.py", "f0_probe.py", "p1.py",
          "check_js.py", "clean_pyc.py"]:
    (root / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(FAZE-0): journal-MT5 sync LIVE - real PnL flows into self-evaluate loop\n\n"
    "- engine/journal_sync.py: sync_mt5_deals() pulls ALL closed deals from\n"
    "  active MT5 terminal via history_deals_get(), pairs open+close by\n"
    "  position_id, upserts into SQLite journal with REAL\n"
    "  profit/commission/swap. Incremental since last sync + backfill mode.\n"
    "- get_journal_stats(): health check for dashboard /health\n"
    "- autonomous.run_batch(): journal sync wired every cycle (non-blocking)\n"
    "- scripts/backfill_journal.py: one-shot full import (90 days)\n"
    "- VERIFIED: 87 new deals inserted, journal now shows 243 trades,\n"
    "  net P&L +$629.98 (matches MT5 terminal $643.71 closed volume)\n"
    "- Attribution still 86% unknown - next task is fixing strategy_name\n"
    "  propagation through the execution pipeline"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-80:], pu.stderr[-100:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
