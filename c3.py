import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
# uv unsupported --user; use --target into user site-packages (Roaming) which IS writable
target = r"C:\Users\Hi\AppData\Roaming\Python\Python314\site-packages"
r = subprocess.run(["uv", "pip", "install", "--target", target, "pystray",
                    "--python", r"C:\Python314\python.exe"],
                   capture_output=True, text=True, cwd=root, timeout=180)
print("rc:", r.returncode, (r.stdout + r.stderr)[-250:])
v = subprocess.run([r"C:\Python314\python.exe", "-c", "import pystray; print('pystray OK')"],
                   capture_output=True, text=True, cwd=root)
print(v.stdout or v.stderr[-150:])
