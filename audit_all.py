import pathlib, re
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")

# 1) MOCK/SIM in Python backend (non-test, non-comment)
print("=== MOCK/SIM IN PYTHON (live path) ===")
mock_pat = re.compile(r"(?i)\b(mock|simulated|fake_|_fake\b|placeholder_data|dummy)\b")
qn = root / "quant_nanggroe"
for f in sorted(qn.rglob("*.py")):
    rel = str(f.relative_to(root))
    if "__pycache__" in rel or "test" in rel.lower():
        continue
    t = f.read_text(encoding="utf-8", errors="ignore")
    for i, line in enumerate(t.splitlines(), 1):
        s = line.strip()
        # Skip comments and docstrings that SAY no-mock or REAL-ONLY
        if s.startswith("#") or s.startswith('"""') or s.startswith("'''"):
            continue
        if mock_pat.search(s):
            print(f"  {rel}:{i}: {s[:120]}")

# 2) COT data — is it real or placeholder?
print("\n=== COT DATA CHECK ===")
ps = root / "quant_nanggroe/core/scoring/positioning_scorer.py"
if ps.exists():
    t = ps.read_text(encoding="utf-8", errors="ignore")
    has_real_api = "cftc" in t.lower() or "CFTC_API_URL" in t
    has_hardcoded = re.search(r'"net_\w+":\s*-?\d+[,}]', t)
    print(f"  positioning_scorer: real_api={has_real_api}, hardcoded_data={bool(has_hardcoded)}")

cot = root / "quant_nanggroe/engine/causal/cot_provider.py"
if cot.exists():
    t = cot.read_text(encoding="utf-8", errors="ignore")
    has_real = "cftc" in t.lower() or "CFTC" in t
    print(f"  cot_provider: real_api={has_real}")

# 3) Dashboard remaining fake data
print("\n=== DASHBOARD FAKE DATA ===")
dash = root / "dashboard/src"
for f in sorted(dash.rglob("*.tsx")):
    rel = str(f.relative_to(root))
    if "node_modules" in rel:
        continue
    t = f.read_text(encoding="utf-8", errors="ignore")
    for i, line in enumerate(t.splitlines(), 1):
        if "Math.random" in line and "__test__" not in rel:
            print(f"  {rel}:{i}: {line.strip()[:100]}")

# 4) File count by extension
print("\n=== FILE COUNTS BY EXTENSION ===")
ext_counts: Dict[str, int] = {}
for f in root.rglob("*"):
    if f.is_file() and ".git" not in str(f) and "node_modules" not in str(f) \
       and ".next" not in str(f) and "_attic" not in str(f) and "__pycache__" not in str(f):
        ext = f.suffix.lower() if f.suffix else "(no ext)"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1])[:25]:
    print(f"  {ext:12s} {count:5d}")
