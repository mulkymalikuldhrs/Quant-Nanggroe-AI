import subprocess, pathlib
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
for f in ["chk.py", "fix1.py", "rtsuite.py"]:
    (pathlib.Path(root) / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=root)
c = subprocess.run(["git", "commit", "-m",
    "docs+ui: CANONICAL gates 1-8 section + awareness panel + sync-drop recovery\n\n"
    "- CANONICAL.md 15.5: all 8 gates documented with evidence; recurring\n"
    "  'phase5 sync drops files' hazard documented with recovery recipe\n"
    "- /export page: Trade Awareness panel (what/why/how/lesson per closed trade)\n"
    "- RESTORED from history after another sync drop: config/page.tsx,\n"
    "  CANONICAL.md (v7.1.0 tri-asset), api-client configFilesApi export\n"
    "- tsc clean; 30/30 gate tests pass"],
    capture_output=True, text=True, cwd=root)
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", pu.stdout[-100:], pu.stderr[-120:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=root).stdout
print("FINAL:", repr(st))
