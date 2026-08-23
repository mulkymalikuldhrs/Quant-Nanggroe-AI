import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
(root / "check_imports.py").unlink(missing_ok=True)
# verify compile
r = subprocess.run(["C:\\Python314\\python.exe", "-m", "py_compile",
                    "quant_nanggroe/engine/models/__init__.py",
                    "quant_nanggroe/autonomous_cycle.py"],
                   capture_output=True, text=True, cwd=str(root))
print("COMPILE:", r.stdout, r.stderr)
