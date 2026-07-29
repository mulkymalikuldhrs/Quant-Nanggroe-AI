import os, sys, subprocess, json, sqlite3, glob
ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "quant_nanggroe"))

def sh(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60,
                           cwd=ROOT, env={**os.environ, "PYTHONPATH": ""})
        return r.stdout + r.stderr
    except Exception as e:
        return f"ERR {e}"

print("=== 1. FILE INVENTORY ===")
out = sh('cd /d ' + ROOT + ' && dir /s /b /a-d | find /v /c ".."')
print("total files (incl node_modules):", out.strip()[:200])
py = [f for f in glob.glob("quant_nanggroe/**/*.py", recursive=True) if "__pycache__" not in f]
print("quant_nanggroe .py files:", len(py))

print("\n=== 2. /archive INVENTORY ===")
for dp, dn, fn in os.walk("archive"):
    if "__pycache__" in dp: continue
    if fn:
        rel = os.path.relpath(dp, "archive")
        print(f"  {rel}/ : {len(fn)} files -> {fn[:8]}")

print("\n=== 3. JOURNAL ROWS (does it trade?) ===")
for j in glob.glob("**/qna_journal.db", recursive=True) + glob.glob("data/qna_journal.db"):
    try:
        c = sqlite3.connect(j)
        try:
            n = c.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
            print(f"  {j}: trades={n}")
        except Exception as e:
            print(f"  {j}: no trades table ({e})")
    except Exception as e:
        print(f"  {j}: open fail {e}")

print("\n=== 4. STRATEGY REGISTRY COUNT ===")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("reg", os.path.join(ROOT,"quant_nanggroe","engine","strategies","registry.py"))
    # try import via package
    import quant_nanggroe.engine.strategies.registry as R
    lst = R.StrategyRegistry.list_strategies()
    print("  registered strategies:", len(lst))
except Exception as e:
    print("  registry import fail:", str(e)[:150])

print("\n=== 5. ORPHAN MODULE CHECK (grep callers) ===")
for m in ["engine/stress_testing", "engine/pattern_recorder", "engine/screener", "exchange/clients", "agents/geopolitics", "engine/factors"]:
    p = os.path.join("quant_nanggroe", m)
    if os.path.isdir(p):
        files = glob.glob(p+"/**/*.py", recursive=True)
        files = [f for f in files if "__init__" not in f and "__pycache__" not in f]
        # count how many of these are imported elsewhere
        cnt = 0
        for f in files[:5]:
            mod = f.replace("/","\\").replace(".py","").replace("quant_nanggroe\\","")
        print(f"  {m}: {len(files)} py files")

print("\n=== 6. DASHBOARD BUILD STATUS ===")
for log in ["dashboard/build_err.log", "dashboard/dash_err.log", "dashboard/dash_out.log"]:
    if os.path.exists(log):
        sz = os.path.getsize(log)
        print(f"  {log}: {sz}b")
        if sz < 5000:
            print("    " + open(log, encoding="utf-8", errors="replace").read()[-400:].replace("\n"," | "))

print("\n=== 7. UI WIRING: dashboard api calls ===")
src = os.path.join("dashboard","src")
if os.path.isdir(src):
    apis = []
    for f in glob.glob(src+"/**/*.{ts,tsx,js}", recursive=True):
        t = open(f, encoding="utf-8", errors="replace").read()
        for line in t.splitlines():
            if ":8000" in line or "/api/" in line:
                apis.append(line.strip()[:90])
    print(f"  dashboard src api refs: {len(apis)}")
    for a in apis[:10]:
        print("   ", a)

print("\n=== 8. GIT STATUS ===")
print(sh("cd /d " + ROOT + " && git status --short | head -20"))
print(sh("cd /d " + ROOT + " && git log --oneline -3"))
