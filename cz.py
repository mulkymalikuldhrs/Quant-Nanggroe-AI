import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
(root / "c7.py").unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(ui): per-symbol specialists panel on strategies page\n\n"
    "- GET /api/export/allocation: full allocation map or per-symbol admitted\n"
    "  list from cpcv_registry (CANONICAL 15.6)\n"
    "- strategies page: 'Per-Symbol Specialists' card — Crypto/Forex/Gold\n"
    "  columns with CPCV-proven strategy badges; hidden when no evidence yet"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:200])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-80:], pu.stderr[-100:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
