import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
# How are strategies toggled on/off?
r = subprocess.run(["git", "grep", "-n", "def toggle\|def disable\|def enable",
                    "--", "quant_nanggroe/engine/strategy_lifecycle.py"],
                   capture_output=True, text=True, cwd=root)
print("lifecycle:", r.stdout[:500])
# Check strategy config / toggle system
r2 = subprocess.run(["git", "grep", "-n", "_strategy_config\|StrategyConfig",
                     "--", "quant_nanggroe/api/routes/strategies.py"],
                    capture_output=True, text=True, cwd=root)
print("\nstrategies route:", r2.stdout[:400])
