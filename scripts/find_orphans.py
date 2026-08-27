import os
import re
from pathlib import Path

root = str(Path(__file__).resolve().parent.parent / 'quant_nanggroe')
py_files = []
for r, dirs, files in os.walk(root):
    if '__pycache__' in r or 'archive' in r:
        continue
    for f in files:
        if f.endswith('.py'):
            py_files.append(os.path.join(r, f).replace('\\', '/'))

imports = {}
for f in py_files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
        content = fh.read()
    mods = set()
    for m in re.findall(r'from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', content):
        mods.add(m)
    for m in re.findall(r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', content, re.M):
        mods.add(m)
    imports[f] = mods

orphans = []
for f in py_files:
    base = os.path.basename(f)[:-3]
    imported = False
    for other, mods in imports.items():
        if other == f:
            continue
        for mod in mods:
            parts = mod.split('.')
            if base in parts or mod.endswith('.' + base) or mod == base:
                imported = True
                break
        if imported:
            break
    if not imported and base != '__init__':
        orphans.append(f)

print(f'Candidate orphans: {len(orphans)}')
for o in sorted(orphans):
    print(f'  {o}')