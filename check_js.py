import sys
sys.path.insert(0, r"D:\repositories\Quant-Nanggroe-AI-worktree")
import quant_nanggroe.engine.journal_sync as js
print("module file:", js.__file__)
print("has _get_db:", hasattr(js, "_get_db"))
print("all names:", sorted(x for x in dir(js) if not x.startswith("__")))
