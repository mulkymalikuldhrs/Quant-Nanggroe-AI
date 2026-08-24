import pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
ps = root / "quant_nanggroe/core/scoring/positioning_scorer.py"
t = ps.read_text(encoding="utf-8", errors="ignore")
# Find the CFTC fetch function and check if it uses real API
import re
m = re.search(r'CFTC_API_URL\s*=\s*["\']([^"\']+)', t)
print("CFTC_API_URL:", m.group(1) if m else "NOT FOUND")
# Check if there are hardcoded values
hardcoded = re.findall(r'"net_\w+":\s*(-?[\d.]+)', t)
print("hardcoded net values:", hardcoded[:5] or "none")
# Check report_date handling
has_report_date = "report_date" in t
print("handles report_date:", has_report_date)
