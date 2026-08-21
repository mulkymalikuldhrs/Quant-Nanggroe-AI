import subprocess, pathlib
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
# remove any stray helper files from disk + index
for f in ["zz_check.py", "cleanup_now.py", "check_tests.py", "run_tests.py",
          "do_commit.py", "check_files.py", "final_check.py", "cleanup_helper.py"]:
    p = pathlib.Path(root) / f
    if p.exists():
        p.unlink()
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=root)
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=root).stdout
print("PRE-COMMIT STATUS:", repr(st))
if st.strip():
    c = subprocess.run(["git", "commit", "-m", "chore: final helper cleanup"],
                       capture_output=True, text=True, cwd=root)
    print(c.stdout[:200])
    p2 = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
    print("PUSH:", p2.stdout[-100:], p2.stderr[-120:])
final = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=root).stdout
print("FINAL:", repr(final))
