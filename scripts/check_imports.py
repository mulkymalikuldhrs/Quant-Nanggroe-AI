import sys, os, importlib
from pathlib import Path
_REPO = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _REPO)
errors = []
for root, dirs, files in os.walk(os.path.join(_REPO, 'quant_nanggroe')):
    if '__pycache__' in root or 'archive' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            full = os.path.join(root, f)
            mod = full.replace('/', '.').replace('\\\\', '.').replace('.py', '')
            # also try short form
            short = full.replace(_REPO + '/', '').replace('/', '.').replace('\\', '.').replace('.py', '')
            for m in [mod, short]:
                try:
                    importlib.import_module(m)
                except Exception as e:
                    err = str(e)[:120]
                    if 'ModuleNotFoundError' in err or 'ImportError' in err:
                        errors.append(f'{m}: {err}')

print(f'Total import errors: {len(errors)}')
seen = set()
for e in errors:
    key = e.split(':')[0]
    if key not in seen:
        seen.add(key)
        print(e)