"""Isolated test of the singleton lock — run directly with .venv312 python."""
import os, sys, time
from pathlib import Path

REPO_ROOT = Path(r"D:/repositories/Quant-Nanggroe-AI-worktree")
sys.path.insert(0, str(REPO_ROOT / "quant_nanggroe"))

# Replicate the guard code standalone
def acquire():
    lock_path = REPO_ROOT / ".autonomous_cycle.lock"
    print(f"Lock path: {lock_path}", flush=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    if os.fstat(fd).st_size == 0:
        os.write(fd, b"0")
    if os.name == "nt":
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            print("LOCK ACQUIRED", flush=True)
        except OSError as e:
            os.close(fd)
            print(f"LOCK DENIED: {e}", flush=True)
            return False
    return True

ok = acquire()
print(f"RESULT: {ok}", flush=True)
if ok:
    print("Holding lock 30s...", flush=True)
    time.sleep(30)
print("DONE", flush=True)
