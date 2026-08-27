"""Syntax-check all 50 migrated strategy files without importing deps."""
import os
import py_compile

strategies_dir = r"D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe\engine\strategies"

strategy_files = sorted([
    f for f in os.listdir(strategies_dir)
    if f.endswith(".py") and f not in ("__init__.py", "base.py", "registry.py")
])

# Also check the 2 reference files
ref_files = ["base.py", "registry.py"]

print(f"Found {len(strategy_files)} strategy files in {strategies_dir}")
print(f"Plus {len(ref_files)} reference files")

success = []
failure = []

for fname in strategy_files + ref_files:
    fpath = os.path.join(strategies_dir, fname)
    try:
        py_compile.compile(fpath, doraise=True)
        success.append(fname)
        print(f"  OK  {fname}")
    except py_compile.PyCompileError as exc:
        failure.append((fname, str(exc)))
        print(f"  FAIL {fname}: {exc}")

print("\n\n=== RESULTS ===")
print(f"Total: {len(strategy_files) + len(ref_files)}")
print(f"Success: {len(success)}")
print(f"Failure: {len(failure)}")
if failure:
    print("Failed files:")
    for fname, err in failure:
        print(f"  - {fname}: {err}")

# Verify all strategy files have the @StrategyRegistry.register decorator pattern
print("\n\n=== DECORATOR CHECK ===")
for fname in strategy_files:
    fpath = os.path.join(strategies_dir, fname)
    with open(fpath) as f:
        content = f.read()
    checks = {
        "has_register_decorator": "@StrategyRegistry.register" in content,
        "has_strategy_base": "class " in content and "Strategy):" in content,
        "has_generate_signal": "def generate_signal" in content,
        "has___all__": "__all__" in content,
    }
    failed_checks = [k for k, v in checks.items() if not v]
    if failed_checks:
        print(f"  MISSING {fname}: {failed_checks}")
    else:
        print(f"  OK  {fname}")
