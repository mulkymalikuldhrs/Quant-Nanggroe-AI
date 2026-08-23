import pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
# Check if portfolio equity-curve endpoint exists
pf = root / "quant_nanggroe/api/routes/portfolio.py"
t = pf.read_text(encoding="utf-8", errors="ignore") if pf.exists() else ""
print("portfolio.py exists:", pf.exists())
print("equity-curve route:", "equity-curve" in t or "equity_curve" in t)
# check dashboard api-client expectation
ac = (root / "dashboard/src/lib/api-client.ts").read_text(encoding="utf-8", errors="ignore")
print("api-client calls:", "equity-curve" in ac or "equity_curve" in ac)
