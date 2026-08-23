import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
(root / "cz.py").unlink(missing_ok=True)
subprocess.run(["git", "rm", "--cached", "cz.py", "-q"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m", "chore: drop helper"],
                   capture_output=True, text=True, cwd=str(root))
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st), "| pushed:", pu.returncode == 0)
