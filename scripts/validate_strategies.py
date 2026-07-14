"""Strategy implant validation.

For every name in list_strategies(), run create_strategy(name) and count failures.
Categorizes each failure via the exception type:
  - CLASS_NOT_FOUND / UNKNOWN : __init__ raises / _NAME_MAP class missing
  - INIT_ARG_ERROR            : TypeError on no-arg instantiation (missing __init__ arg)
  - OTHER                     : any other exception
"""
from __future__ import annotations
import sys, time, traceback
sys.path.insert(0, "D:/repositories/Quant-Nanggroe-AI-worktree")

from quant_nanggroe.engine.strategy.strategies import list_strategies, create_strategy
import quant_nanggroe.engine.strategy.strategies as pkg

names = list_strategies()
ok, gagal = [], []
errors = {}

for name in names:
    try:
        inst = create_strategy(name)
        if inst is None:
            gagal.append(name); errors[name] = ("RETURNED_NONE", "create_strategy returned None")
        else:
            ok.append(name)
    except TypeError as e:
        gagal.append(name); errors[name] = ("INIT_ARG_ERROR", str(e))
    except (ValueError, AttributeError) as e:
        gagal.append(name); errors[name] = ("NOT_FOUND", str(e))
    except Exception as e:  # noqa: BLE001
        gagal.append(name); errors[name] = ("OTHER", f"{type(e).__name__}: {e}")

print(f"API_TOTAL={len(names)} API_OK={len(ok)} API_GAGAL={len(gagal)}")
if gagal:
    for n in gagal:
        print(f"  [FAIL] {n}: {errors[n][0]} | {errors[n][1]}")

# NAME_MAP integrity: does every _NAME_MAP[mod] class actually exist on the module?
missing_cls = []
for mod_name, cls_name in pkg._NAME_MAP.items():
    mod = pkg.__dict__.get(mod_name)
    if mod is None:
        missing_cls.append((mod_name, cls_name, "MODULE_NOT_IMPORTED"))
    elif getattr(mod, cls_name, None) is None:
        missing_cls.append((mod_name, cls_name, "CLASS_NOT_FOUND"))
print("NAME_MAP_INTEGRITY:", "OK" if not missing_cls else f"{len(missing_cls)} BROKEN")
for m, c, why in missing_cls:
    print(f"  {why}: module={m} expected_class={c}")

# Decorator registry (the parallel engine/strategies system)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry as DecReg
import quant_nanggroe.engine.strategies.market_profile, quant_nanggroe.engine.strategies.volume_delta
dreg = sorted(DecReg.list_strategies())
dfail = []
for nm in dreg:
    try:
        inst = DecReg.create(nm)
        assert inst is not None
    except Exception as e:  # noqa: BLE001
        dfail.append((nm, f"{type(e).__name__}: {e}"))
print(f"DECORATOR_TOTAL={DecReg.count()} DECORATOR_OK={len(dreg)-len(dfail)} DECORATOR_GAGAL={len(dfail)}")
for nm, e in dfail:
    print(f"  [FAIL] {nm}: {e}")
