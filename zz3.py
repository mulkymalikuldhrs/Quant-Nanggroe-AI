import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m", "chore: drop zz2"],
                   capture_output=True, text=True, cwd=str(root))
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st), "| pushed:", pu.returncode == 0)
