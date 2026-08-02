#!/usr/bin/env python3
"""
QNA Monday pre-flight + boot harness.
Runs market-INDEPENDENT checks now; prints the exact boot command and the
at-market verification checklist (DEBATE_ROUND1, 11-step protocol).

Run (pre-market, Sunday):
  env -u PYTHONPATH PYTHONPATH=. .venv312/Scripts/python.exe scripts/qna_monday_preflight.py

Exit 0 = safe to boot at market open. Non-zero = block.
"""
import os
import sys
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(REPO, ".venv312", "Scripts", "python.exe")
MODIFIED = [
    "quant_nanggroe/autonomous_cycle.py",
    "quant_nanggroe/trade_journal.py",
    "quant_nanggroe/engine_production_bridge_purified.py",
]
EQUITY_FLOOR = 1000.0


def run(cmd, cwd=REPO):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)


def check_git_clean():
    r = run("git status --porcelain")
    if r.stdout.strip():
        print("  [WARN] uncommitted changes:\n" + r.stdout)
        return False
    print("  [OK] git tree clean")
    return True


def check_venv():
    ok = os.path.exists(VENV)
    print(("  [OK] venv present" if ok else "  [FAIL] .venv312 missing") )
    return ok


def check_syntax():
    for f in MODIFIED:
        r = run(f'"{sys.executable}" -m py_compile {f}', cwd=REPO)
        if r.returncode != 0:
            print(f"  [FAIL] syntax {f}\n{r.stderr}")
            return False
    print("  [OK] syntax all 3 modified files")
    return True


def check_import_smoke():
    # stub MetaTrader5 so import doesn't need the terminal
    import types
    for m in ("MetaTrader5", "numpy", "pandas", "torch"):
        sys.modules.setdefault(m, types.ModuleType(m))
    try:
        import quant_nanggroe.autonomous_cycle as ac
        has = hasattr(ac.PositionManager, "reconcile_legacy_positions")
        print("  [OK] import OK; reconcile_legacy_positions present="
              + str(has))
        return has
    except Exception as e:
        print("  [FAIL] import: " + repr(e))
        return False


def main():
    print("=== QNA MONDAY PRE-FLIGHT (market-independent) ===")
    checks = [check_git_clean(), check_venv(), check_syntax(), check_import_smoke()]
    print("\n=== BOOT COMMAND (run at market open, 08:00 WIB) ===")
    print("  env -u PYTHONPATH PYTHONPATH=. .venv312/Scripts/python.exe "
          "-m quant_nanggroe.autonomous_cycle")
    print("\n=== AT-MARKET VERIFICATION (DEBATE_ROUND1, 11-step) ===")
    print("  1. git status clean ................. [pre-flight OK]")
    print("  2. single instance (lock G8) ....... check no 2nd process")
    print("  3. log 'MT5 connected LIVE login=372044706 balance~1122'")
    print("  4. LEGACY RECONCILE: 3 orphan positions force-closed")
    print("  5. first order has SL+TP (not naked)")
    print("  6. MT5 comment = STRATEGY:SYMBOL (G12)")
    print("  7. data/qna_trade_journal.db grows w/ strategy filled")
    print("  8. HOLD logging appears (G10)")
    print("  9. caps: max 5 total, 1/symbol (G7)")
    print(" 10. kelly_cache populated after first close (G9)")
    print(" 11. kill-switch file -> loop stops in 1 cycle")
    print("\n  HARD-ABORT: equity<$%.0f | daily>3%% | no-SL order | >1 instance | journal empty"
          % EQUITY_FLOOR)
    ok = all(checks)
    print("\n=== RESULT: " + ("SAFE TO BOOT" if ok else "BLOCKED") + " ===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
