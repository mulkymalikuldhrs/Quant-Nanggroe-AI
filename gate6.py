import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
def run(*cmd):
    r = subprocess.run(list(cmd), capture_output=True, text=True, cwd=root)
    return r.stdout + r.stderr
# find historical definition of accounts/ledger endpoint
out = run("git", "grep", "-n", "accounts/ledger", "ba0e060e", "--", "*.py")
print(out[:1200] or "none")
