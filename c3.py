import subprocess
import pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
sa = root / "quant_nanggroe/engine/self_aware.py"
print("self_aware exists:", sa.exists())
ev = root / "quant_nanggroe/engine/strategies/strategy_evolver.py"
print("strategy_evolver exists:", ev.exists())
r = subprocess.run(["git", "grep", "-n", "SelfAware", "--",
                    "quant_nanggroe/engine/agentic/autonomous.py"],
                   capture_output=True, text=True, cwd=str(root))
print("autonomous SelfAware refs:")
print((r.stdout or "(none)").strip()[:400])
