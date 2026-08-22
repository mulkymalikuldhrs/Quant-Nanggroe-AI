import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
for f in ["c3.py", "c4.py", "rt.py"]:
    (root / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(gate-3 loop): trade awareness feeds SelfAware.reflect — organism remembers its trades\n\n"
    "- autonomous._pipeline_self_state: injects recent-closed awareness summary\n"
    "  (wins/losses/worst_strategy/top_lesson from journal) into SelfState.extra,\n"
    "  fail-closed try/except\n"
    "- self_aware.reflect: new reasoning block — surfaces 'I remember my last N\n"
    "  closed trades', flags worst strategy as anomaly when losses dominate\n"
    "  (feeds keep/tune/kill lifecycle decisions)\n"
    "- pystray 0.19.5 installed via uv --target user-site; tray runtime-ready\n"
    "- tray dep note updated\n"
    "Tests: 2/2 self-awareness regression pass"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-100:], pu.stderr[-120:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
