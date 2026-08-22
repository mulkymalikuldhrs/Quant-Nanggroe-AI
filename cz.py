import subprocess, pathlib
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
for f in ["c0.py", "c1.py", "c2.py"]:
    (pathlib.Path(root) / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=root)
c = subprocess.run(["git", "commit", "-m",
    "feat(gate-6 ui): multi-account panel + compat routes + brokers dark-tech re-restore\n\n"
    "- app.py: legacy compat /api/accounts + /api/accounts/ledger aliases\n"
    "  (dashboard consumers expected non-prefixed paths)\n"
    "- api-client: brokersApi.accounts() + ledger() restored (sync casualty);\n"
    "  LedgerAccount/LedgerResponse types re-added\n"
    "- brokers/page: full dark-tech rewrite RE-RESTORED after sync revert,\n"
    "  now with Account Ledger table (all-ever-connected MT5 accounts:\n"
    "  login/server/trades/pnl/last-seen) + registered account tiles +\n"
    "  live detail + order form with auto-resolved symbols"],
    capture_output=True, text=True, cwd=root)
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", pu.stdout[-100:], pu.stderr[-120:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=root).stdout
print("FINAL:", repr(st))
