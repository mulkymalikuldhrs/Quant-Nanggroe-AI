#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "=== Auto-Register: Scanning for unregistered modules ==="

python3 -c "
import os
from pathlib import Path

repo = Path('$REPO')
qna = repo / 'quant_nanggroe'

detected = []

for dirpath, dirnames, filenames in os.walk(qna):
    dir = Path(dirpath)
    init = dir / '__init__.py'
    if not init.exists():
        pyfiles = [f for f in filenames if f.endswith('.py') and f != '__init__.py']
        if pyfiles:
            detected.append((dir.relative_to(qna), pyfiles))
            # Create __init__.py
            rel = dir.relative_to(qna)
            pkg = '.'.join(rel.parts)
            with open(init, 'w') as f:
                f.write('import importlib\n')
                f.write('import pkgutil\n\n')
                f.write(f'__all__ = []\n\n')
                for pyf in pyfiles:
                    modname = pyf[:-3]
                    topkg = 'quant_nanggroe'
                    parts = list(rel.parts)
                    fullname = topkg + '.' + '.'.join(parts) + '.' + modname
                    f.write(f'from {fullname} import *\n')
                f.write(f'\n# Auto-registered by auto-register.sh on $(date +%Y-%m-%d)\n')

if detected:
    print('CREATED __init__.py for:')
    for d, files in detected:
        print(f'  /{d}/ — {len(files)} files: {\", \".join(files)}')
else:
    print('All directories already have __init__.py')
"

echo "=== Scanning for loose .py files missing from __init__.py exports ==="

python3 -c "
import ast, os
from pathlib import Path

repo = Path('$REPO')
qna = repo / 'quant_nanggroe'

for dirpath, dirnames, filenames in os.walk(qna):
    dir = Path(dirpath)
    init = dir / '__init__.py'
    if not init.exists():
        continue
    pyfiles = set()
    for f in filenames:
        if f.endswith('.py') and f != '__init__.py':
            pyfiles.add(f[:-3])
    if not pyfiles:
        continue
    try:
        tree = ast.parse(init.read_text())
    except SyntaxError:
        continue
    exported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                exported.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                exported.add(alias.name.split('.')[0] if '.' in alias.name else alias.name)
    missing = pyfiles - exported
    if missing:
        rel = dir.relative_to(qna)
        print(f'/{rel}/ missing exports: {sorted(missing)}')
        # Add missing imports
        with open(init, 'a') as f:
            for m in sorted(missing):
                topkg = 'quant_nanggroe'
                parts = list(rel.parts)
                fullname = topkg + '.' + '.'.join(parts) + '.' + m
                f.write(f'from {fullname} import *\n')
        print(f'  -> Added to {init}')
"

echo "=== Checking pyproject.toml for console_scripts ==="
python3 -c "
import tomllib
with open('$REPO/pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
scripts = data.get('project', {}).get('scripts', {})
print(f'Current console_scripts: {len(scripts)}')
for name, target in scripts.items():
    print(f'  {name} -> {target}')
"

echo "=== Registering new scripts as console_scripts ==="
python3 -c "
import os, ast
from pathlib import Path

repo = Path('$REPO')
scripts_dir = repo / 'scripts'

for f in sorted(scripts_dir.glob('*.py')):
    content = f.read_text()
    # Look for def main() or def run()
    tree = ast.parse(content)
    has_main = any(isinstance(n, ast.FunctionDef) and n.name in ('main', 'run') for n in ast.walk(tree))
    if has_main:
        name = f.stem
        print(f'  {name}.py has main()/run() — candidate for console_script')
"

echo "=== Auto-Register Complete ==="
