import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=root)
r = subprocess.run(["git", "commit", "-m",
    "feat(gate-4): Export Center - trades/summary custom range to xlsx/csv/md/json/pdf\n\n"
    "- api/routes/export.py: /api/export/trades (filter date_from/date_to/strategy/\n"
    "  symbol; csv|xlsx|md|json now, pdf honest 501 until reportlab installed)\n"
    "  + /api/export/summary per-strategy stats\n"
    "- dashboard /export page: date pickers + strategy/symbol filters + format\n"
    "  buttons with authed download + live summary table (REAL journal data)\n"
    "- sidebar: Export entry restored; /config re-restored after phase5 sync drop\n"
    "- fix pre-existing tsc errors in evolution/page.tsx (invalid Badge variants)\n"
    "Tests: 7/7 export API regression pass"],
    capture_output=True, text=True, cwd=root)
print("COMMIT:", r.stdout[:250])
r2 = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", r2.stdout[-120:], r2.stderr[-150:])
