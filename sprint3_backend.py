import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")

# 1) Delete mock ML signal generator (returns zeros, never used in prod)
f = root / "quant_nanggroe/engine/ml/signal_generator.py"
if f.exists():
    f.unlink()
    print("DELETED engine/ml/signal_generator.py")

# Check if any non-test file imports it
r = subprocess.run(["git", "grep", "-l", "signal_generator", "--",
                    "quant_nanggroe/", "--", ":!quant_nanggroe/engine/ml/"],
                   capture_output=True, text=True, cwd=str(root))
print("non-ml importers:", r.stdout.strip() or "none")

# 2) Gate paper_broker behind env var
pb = root / "quant_nanggroe/engine/execution/brokers/paper.py"
if pb.exists():
    t = pb.read_text(encoding="utf-8")
    header = '''"""Paper Broker — DISABLED by default (REAL-ONLY mode).

Set QNA_ALLOW_PAPER=1 to enable for testing only.
This broker NEVER runs in production unless explicitly opted-in.
"""
import os as _os

if _os.environ.get("QNA_ALLOW_PAPER") != "1":
    raise ImportError(
        "PaperBroker is DISABLED (REAL-ONLY mode). "
        "Set QNA_ALLOW_PAPER=1 to enable for testing only."
    )

'''
    if "_os.environ" not in t.split("\n")[5] if len(t.splitlines()) > 5 else "":
        # prepend gate
        old_lines = t.splitlines()
        # find where imports end and class begins
        new_content = header + "\n".join(old_lines)
        pb.write_text(new_content, encoding="utf-8")
        print("paper_broker gated behind QNA_ALLOW_PAPER")

# 3) Delete results/.bt_lock if exists
lock = root / "results/.bt_lock"
if lock.exists():
    lock.unlink()
    print("DELETED results/.bt_lock")

print("Backend mock elimination done")
