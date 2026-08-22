import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
(root / "clean_pyc.py").unlink(missing_ok=True)
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("STATUS:", repr(st[:300]))
if st.strip():
    subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
    c = subprocess.run(["git", "commit", "-m", "chore: cleanup helper"],
                       capture_output=True, text=True, cwd=str(root))
    print(c.stdout[:120])
    pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
    print("PUSH:", pu.stdout[-80:])
    st2 = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
    print("FINAL:", repr(st2))
