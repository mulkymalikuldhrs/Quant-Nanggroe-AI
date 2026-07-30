"""Check what strategy .py files exist but aren't registered."""
import sys, os
sys.path.insert(0, r'D:/repositories/Quant-Nanggroe-AI-worktree')

from pathlib import Path
import importlib

quant_root = Path(r'D:/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe/engine/strategies')

# Get registered names from StrategyRegistry
from quant_nanggroe.engine.strategies.registry import list_strategies
from quant_nanggroe.engine.registry import list_categories
registered = list_strategies()
reg_mods = {cls.__module__ for cls in registered.values()}

# Get all .py files in strategies dir that have class Strategy subclasses
py_files = sorted(quant_root.glob('*.py'))

print(f"=== REGISTERED: {len(registered)} ===")
print(f"Categories: {list_categories()}")

print("\n=== FILES NOT REGISTERED ===")
unreg = []
for f in py_files:
    if f.stem.startswith('_') or f.stem in ('base', 'registry', 'strategy_evolver', 'gene_loader'):
        continue
    expected_mod = f'quant_nanggroe.engine.strategies.{f.stem}'
    if expected_mod in reg_mods:
        continue
    # Try importing to check for Strategy subclasses
    try:
        mod = importlib.import_module(expected_mod)
        from quant_nanggroe.engine.strategies.base import Strategy
        import inspect
        found = []
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if obj is not Strategy and issubclass(obj, Strategy):
                found.append(obj.__name__)
        if found:
            print(f'  {f.name}: has Strategy subclasses {found} but NOT registered')
            unreg.append(f.stem)
        else:
            print(f'  {f.name}: imported, no Strategy subclass')
    except Exception as e:
        print(f'  {f.name}: import FAILED - {e}')
        unreg.append(f.stem)

print(f"\n=== UNREGISTERED COUNTS: {len(unreg)} ===")
if unreg:
    print(f"Would add: {len(unreg)}")

# Also check if we can inherit from adapters or other bases
print("\n=== OTHER DIRS WITH STRATEGIES ===")
for d in [quant_root / 'archive', quant_root.parent / 'strategy' / 'strategies']:
    if d.exists():
        for f in sorted(d.glob('*.py')):
            if f.stem.startswith('_'):
                continue
            try:
                mod_name = '.'.join(f.relative_to(quant_root.parent.parent.parent).with_suffix('').parts)
                mod = importlib.import_module(mod_name)
                from quant_nanggroe.engine.strategies.base import Strategy
                import inspect
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if obj is not Strategy and issubclass(obj, Strategy):
                        print(f'  {mod_name}.{obj.__name__} (not in main registry)')
            except:
                pass

# Count files with strategy-related names
total_py = list(quant_root.glob('*.py'))
print(f"\n=== TOTAL .py in strategies dir: {len(total_py)} ===")
print(f"Skipped (_ prefix): {[f.name for f in total_py if f.stem.startswith('_')]}")
