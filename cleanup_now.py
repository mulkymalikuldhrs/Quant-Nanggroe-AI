import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
import pathlib
for f in ["check_files.py", "check_tests.py", "do_commit.py", "run_tests.py",
          "cleanup_helper.py", "final_check.py"]:
    p = pathlib.Path(root) / f
    if p.exists():
        p.unlink()
r = subprocess.run(["git", "add", "-A"], capture_output=True, text=True, cwd=root)
r2 = subprocess.run(["git", "commit", "-m", "chore: remove session helper scripts"],
                    capture_output=True, text=True, cwd=root)
print(r2.stdout[:200])
r3 = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", r3.stdout[-120:], r3.stderr[-150:])
