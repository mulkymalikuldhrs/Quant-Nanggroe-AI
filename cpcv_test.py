import subprocess, os
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
env = dict(os.environ); env["PYTHONPATH"] = ""
r = subprocess.run([r"C:\Python314\python.exe", "-W", "ignore", "scripts/run_cpcv_validation.py"],
                   capture_output=True, text=True, cwd=root, env=env, timeout=1700)
out = r.stdout + r.stderr
lines = [l for l in out.splitlines()
         if "Not enough bars" not in l and "Fold" not in l and "Kronos" not in l]
print("\n".join(lines))
