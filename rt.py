import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
junk = [
    "check_structure.py", "test_lock.py", "test_singleton.py", "clean_locks.py",
    "test_live_gate.py", "check_git.py", "check_manager.py", "check_manager2.py",
    "ALL_SOURCE_FILES.txt", "plans.lnk", "QNA_Audit_&_Rewire_b5460bf6.lnk",
    "backtest_all_results.md",  # stale artifact, results/ is canonical
]
removed = []
for f in junk:
    p = root / f
    if p.exists():
        p.unlink()
        removed.append(f)
print("removed:", removed)

subprocess.run(["git", "add", "-A"], capture_output=True, cwd=root)
c = subprocess.run(["git", "commit", "-m",
    "feat(gates3,5,8): trade awareness API + system tray app + repo tidy\n\n"
    "- GATE-3 engine/analytics/trade_awareness.py: deterministic what/why/how/\n"
    "  lesson per closed trade (pure rules, no LLM) + GET /api/export/awareness\n"
    "  wired to journal (hit_type/close_reason already recorded in schema)\n"
    "- GATE-5 scripts/qna_tray.py + qna_tray.bat: tray icon online/error/offline\n"
    "  from /health poll (kill-switch aware), menu: dashboard/docs/start/restart\n"
    "  backend/logs/exit. Deps: pystray only (Pillow present)\n"
    "- GATE-8 tidy: remove root helper/junk per owner list (check_*, test_lock,\n"
    "  clean_locks, test_live_gate, ALL_SOURCE_FILES.txt, .lnk shortcuts,\n"
    "  stale backtest_all_results.md)"],
    capture_output=True, text=True, cwd=root)
print("COMMIT:", c.stdout[:250])
p2 = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", p2.stdout[-120:], p2.stderr[-150:])
