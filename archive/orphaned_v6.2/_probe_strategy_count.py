
import sys
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
try:
    from quant_nanggroe.engine.registry import list_strategies
    s = list_strategies()
    print("COUNT:", len(s))
    print("SAMPLE5:", s[:5])
    print("SAMPLE_LAST5:", s[-5:] if len(s) > 5 else s)
except Exception as e:
    import traceback
    print("ERR_TYPE:", type(e).__name__)
    print("ERR_MSG:", str(e)[:800])
    traceback.print_exc()
