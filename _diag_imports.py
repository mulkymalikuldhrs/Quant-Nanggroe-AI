import importlib, pkgutil, traceback, sys, os
import quant_nanggroe.engine.strategies as strat_pkg
from quant_nanggroe.engine.strategies.base import Strategy

root = os.path.dirname(strat_pkg.__file__)
ok, fail = [], {}
for finder, name, is_pkg in pkgutil.walk_packages(strat_pkg.__path__, prefix=strat_pkg.__name__ + "."):
    try:
        importlib.import_module(name)
        ok.append(name)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e).splitlines()[0][:160]}"
        fail[name] = msg

print(f"IMPORT OK: {len(ok)}")
print(f"IMPORT FAIL: {len(fail)}")
from collections import Counter
c = Counter(v.split(":")[0] for v in fail.values())
print("FAIL TYPES:", dict(c))
for n, m in sorted(fail.items()):
    print(f"  FAIL {n} -> {m}")
