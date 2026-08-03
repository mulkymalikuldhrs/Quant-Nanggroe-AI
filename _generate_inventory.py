#!/usr/bin/env python3
"""Generate QNA audit evidence files: FILE_INVENTORY, PATTERN_SCAN, PY_SCAN.
Excludes generated dirs (.git, node_modules, .venv, __pycache__, .next, dist, *.egg-info).
"""
import os, re, ast, datetime

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
DESK = r"C:\Users\Hi\Desktop"
EXCLUDE_DIRS = {'.git','node_modules','.venv','.venv312','__pycache__','.next',
                'dist','build','.pytest_cache','.mypy_cache','.ruff_cache',
                '.kilocode','.kilo','.idea','.vscode','coverage','.tox',
                'site-packages','.eggs'}
EXCLUDE_FILES = {'.ds_store','thumbs.db'}

ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB")

# ---- collect files ----
files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDE_DIRS]
    for fn in filenames:
        if fn.lower() in EXCLUDE_FILES:
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT)
        try:
            sz = os.path.getsize(full)
        except OSError:
            sz = -1
        ext = os.path.splitext(fn)[1].lower()
        files.append((rel, ext, sz, full))

files.sort()

# ---- 1. FILE INVENTORY ----
ext_counts = {}
total_lines = 0
inv_lines = []
inv_lines.append(f"# QNA FILE INVENTORY  (generated {ts})")
inv_lines.append(f"# Root: {ROOT}")
inv_lines.append(f"# Total files (excl generated): {len(files)}")
inv_lines.append("#")
inv_lines.append("# FORMAT: <relpath> | <ext> | <bytes> | <lines>")
inv_lines.append("")

text_exts = {'.py','.ts','.tsx','.js','.jsx','.md','.txt','.json','.yaml','.yml',
             '.toml','.cfg','.ini','.rst','.csv','.html','.css','.sh','.bat',
             '.sql','.ipynb','.lock','.txt','.cfg'}

for rel, ext, sz, full in files:
    lines = ""
    if ext in text_exts and sz >= 0 and sz < 5_000_000:
        try:
            with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                n = sum(1 for _ in fh)
            lines = str(n)
            total_lines += n
        except Exception:
            lines = "?"
    ext_counts[ext] = ext_counts.get(ext, 0) + 1
    inv_lines.append(f"{rel} | {ext or '(none)'} | {sz} | {lines}")

inv_lines.append("")
inv_lines.append("# === EXTENSION SUMMARY ===")
for ext, c in sorted(ext_counts.items(), key=lambda x: -x[1]):
    inv_lines.append(f"{ext or '(none)'} : {c} files")
inv_lines.append(f"# TOTAL LINES (text files): {total_lines}")

with open(os.path.join(DESK, "QNA_FILE_INVENTORY.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(inv_lines))

# ---- 2. PATTERN SCAN ----
patterns = {
    'TODO': re.compile(r'\bTODO\b'),
    'FIXME': re.compile(r'\bFIXME\b'),
    'HACK': re.compile(r'\bHACK\b'),
    'XXX': re.compile(r'\bXXX\b'),
    'NotImplementedError': re.compile(r'NotImplementedError'),
    'raise NotImplemented': re.compile(r'raise\s+NotImplemented'),
    'stub/dead': re.compile(r'#\s*(stub|dead|unused|placeholder|not implemented|wip)\b', re.I),
    'mock/fake': re.compile(r'\b(mock|fake|dummy|placeholder)\b', re.I),
    'deprecated': re.compile(r'deprecat', re.I),
    'FIXME-USER': re.compile(r'fixme', re.I),
    'pass-only': re.compile(r'^\s*pass\s*$'),
    '...ellipsis': re.compile(r'^\s*\.\.\.\s*$'),
    'noqa': re.compile(r'#\s*noqa'),
    'type-ignore': re.compile(r'#\s*type:\s*ignore'),
}
pat_results = {k: {} for k in patterns}
scan_lines = []
scan_lines.append(f"# QNA PATTERN SCAN  (generated {ts})")
scan_lines.append(f"# Root: {ROOT}")
scan_lines.append("# Patterns searched (case-insensitive where noted):")
for k in patterns:
    scan_lines.append(f"#   - {k}")
scan_lines.append("")

for rel, ext, sz, full in files:
    if ext not in text_exts or sz < 0 or sz > 2_000_000:
        continue
    try:
        with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
            content = fh.readlines()
    except Exception:
        continue
    for i, line in enumerate(content, 1):
        for pname, pat in patterns.items():
            if pat.search(line):
                d = pat_results[pname]
                d.setdefault(rel, []).append((i, line.strip()[:160]))

for pname in patterns:
    d = pat_results[pname]
    total_hits = sum(len(v) for v in d.values())
    scan_lines.append(f"\n## {pname}  ({total_hits} hits in {len(d)} files)")
    for rel in sorted(d.keys()):
        hits = d[rel]
        scan_lines.append(f"  {rel}: {len(hits)}")
        for ln, txt in hits[:8]:
            scan_lines.append(f"    L{ln}: {txt}")
        if len(hits) > 8:
            scan_lines.append(f"    ... +{len(hits)-8} more")

with open(os.path.join(DESK, "QNA_PATTERN_SCAN.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(scan_lines))

# ---- 3. PY SCAN (AST) ----
py_scan = []
py_scan.append(f"# QNA PY SCAN  (generated {ts})")
py_scan.append(f"# Root: {ROOT}")
py_scan.append("# AST-parsed .py files: imports, classes, functions, wiring signals")
py_scan.append("")

py_files = [(rel, full) for rel, ext, sz, full in files if ext == '.py']
parse_ok = 0
parse_fail = 0
for rel, full in sorted(py_files):
    try:
        with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
            src = fh.read()
        tree = ast.parse(src)
    except Exception as e:
        py_scan.append(f"\n### {rel}  [PARSE FAIL: {type(e).__name__}]")
        parse_fail += 1
        continue
    parse_ok += 1
    imports = []
    classes = []
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            names = [a.name for a in node.names]
            imports.append(f"{mod} -> {','.join(names)}")
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(node.name)
    # wiring signals
    body = src.lower()
    signals = []
    if 'fastapi' in body or 'api' in body: signals.append('api')
    if 'create_app' in body: signals.append('create_app()')
    if 'register' in body or 'mount' in body: signals.append('mount/register')
    if 'todo' in body or 'fixme' in body: signals.append('has-TODO')
    py_scan.append(f"\n### {rel}")
    py_scan.append(f"  imports({len(imports)}): {', '.join(imports[:12])}{'...' if len(imports)>12 else ''}")
    py_scan.append(f"  classes({len(classes)}): {', '.join(classes[:15])}")
    py_scan.append(f"  functions({len(funcs)}): {', '.join(funcs[:15])}{'...' if len(funcs)>15 else ''}")
    if signals:
        py_scan.append(f"  signals: {', '.join(signals)}")

py_scan.append(f"\n# PY FILES: {len(py_files)} | parsed OK: {parse_ok} | parse fail: {parse_fail}")
with open(os.path.join(DESK, "QNA_PY_SCAN.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(py_scan))

print(f"FILES: {len(files)} | PY: {len(py_files)} (ok={parse_ok}, fail={parse_fail})")
print("WROTE: QNA_FILE_INVENTORY.txt, QNA_PATTERN_SCAN.txt, QNA_PY_SCAN.txt")
