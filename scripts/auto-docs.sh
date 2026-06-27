#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/docs/auto/api"
mkdir -p "$OUT"

echo "=== Auto-Docs: Generating API documentation from source ==="

python3 << PYEOF
import ast, os, textwrap
from pathlib import Path

qna = Path('$REPO/quant_nanggroe')
out = Path('$OUT')

def get_docstring(node):
    doc = ast.get_docstring(node)
    return textwrap.dedent(doc).strip() if doc else ''

def extract_info(filepath, rel_path):
    try:
        text = filepath.read_text()
        tree = ast.parse(text)
    except (SyntaxError, UnicodeDecodeError):
        return []
    entries = []
    modname = str(rel_path.with_suffix('')).replace(os.sep, '.')
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = get_docstring(node)
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            entries.append({
                'type': 'class',
                'name': node.name,
                'module': modname,
                'doc': doc,
                'methods': methods,
                'lineno': node.lineno,
            })
        elif isinstance(node, ast.FunctionDef):
            doc = get_docstring(node)
            entries.append({
                'type': 'function',
                'name': node.name,
                'module': modname,
                'doc': doc,
                'lineno': node.lineno,
            })
    return entries

all_entries = []
for f in sorted(qna.rglob('*.py')):
    rel = f.relative_to(qna)
    entries = extract_info(f, rel)
    all_entries.extend(entries)
    if entries:
        modname = str(rel.with_suffix('')).replace(os.sep, '.')
        doc_file = out / f'{modname}.md'
        doc_file.parent.mkdir(parents=True, exist_ok=True)
        with open(doc_file, 'w') as mdf:
            mdf.write(f'# {modname}\n\n')
            for e in entries:
                mdf.write(f'## {e["type"].title()}: `{e["name"]}`\n\n')
                if e['doc']:
                    mdf.write(f'{e["doc"]}\n\n')
                if e['type'] == 'class' and e['methods']:
                    mdf.write(f'**Methods:** {", ".join(e["methods"])}\n\n')
                mdf.write(f'*Line: {e["lineno"]}*\n\n---\n\n')

with open(out / 'INDEX.md', 'w') as idx:
    idx.write('# QNA API Reference\n\n')
    idx.write(f'*Auto-generated from {len(all_entries)} classes/functions*\n\n')
    idx.write('## Package Index\n\n')
    for e in sorted(all_entries, key=lambda x: f'{x["module"]}.{x["name"]}'):
        icon = '\U0001F3DB' if e['type'] == 'class' else '\U0001F527'
        doc_link = f'{e["module"]}.md#{e["type"]}-{e["name"]}'.lower()
        idx.write(f'- {icon} [{e["name"]}]({doc_link}) -- `{e["module"]}`\n')

print(f'Generated {len(all_entries)} API entries')
print(f'Module docs: {len(list(out.rglob("*.md")))} files')
PYEOF
echo "=== Auto-Docs Complete ==="
