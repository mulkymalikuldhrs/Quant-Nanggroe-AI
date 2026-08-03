import os, sys, traceback
os.environ.setdefault("QNA_SCHEDULER_ENABLED", "0")
os.environ.setdefault("QNA_LIVE_TRADING", "0")
os.environ.setdefault("QNA_SELF_EVAL_EVERY", "1")
os.environ.setdefault("QNA_EVOLVE_EVERY", "1")
sys.path.insert(0, ".")
try:
    from quant_nanggroe.autonomous_cycle import AutonomousCycle
    cyc = AutonomousCycle()
    cyc.initialize()
    print("INIT_OK")
    for i in range(2):
        st = cyc.run_cycle()
        print(f"CYCLE_{i+1}_OK status_keys={sorted(st.keys())}")
    print("DRY_RUN_GREEN")
except Exception as e:
    print("DRY_RUN_FAILED:", repr(e))
    traceback.print_exc()
