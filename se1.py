import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
# check if strategy_evaluator.py already exists (was mentioned in audit as MISSING)
r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=root)
lines = r.stdout.splitlines()
for l in lines:
    if "evaluator" in l.lower() or "scorecard" in l.lower():
        print("FOUND:", l)
if not any("evaluator" in l for l in lines):
    print("strategy_evaluator.py NOT FOUND — needs to be created")
# check what self_eval exists in trade_journal or elsewhere
r2 = subprocess.run(["git", "grep", "-ln", "self_eval\|compute_scorecard"],
                    capture_output=True, text=True, cwd=root)
print(r2.stdout[:500] or "no self_eval found")
