import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
p = subprocess.Path = None
import pathlib
(pathlib.Path(root) / "_ledger_block.py").unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=root)
c = subprocess.run(["git", "commit", "-m",
    "fix(gate-6): restore multi-account endpoints dropped by phase5 sync\n\n"
    "- account_ledger.py restored (record_account was called in builder but\n"
    "  module itself was missing -> silent no-op ledger)\n"
    "- GET /api/trading/accounts (live discovery of every logged-in terminal)\n"
    "- GET /api/trading/accounts/ledger (all-ever-connected, dashboard uses this)\n"
    "- fail-closed: empty list when MT5 unavailable, never fabricated accounts"],
    capture_output=True, text=True, cwd=root)
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", pu.stdout[-100:], pu.stderr[-120:])
