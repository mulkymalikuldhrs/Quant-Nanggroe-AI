#!/usr/bin/env python3
"""graphify_scan — Module dependency scanner for Quant-Nanggroe-AI.

Scans all Python modules under quant_nanggroe/, parses imports via AST,
identifies dangling references and isolated modules, then generates
GRAPH_SCAN.html and updates GRAPH-INDEX.html.

Usage:
    python scripts/graphify_scan.py
"""

import ast
import os
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
QNA = REPO / "quant_nanggroe"
GRAPH_INDEX = REPO.parent / "GRAPH-INDEX.html"

# ponytail: count all .py files under quant_nanggroe (excl __pycache__)
def find_modules():
    modules = {}
    for root, dirs, files in os.walk(QNA):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = Path(root) / f
            rel = path.relative_to(QNA)
            modname = str(rel.with_suffix("")).replace(os.sep, ".")
            modules["quant_nanggroe." + modname] = path
    return modules


def parse_imports(path):
    """Return set of module-level import names found in a Python file via AST."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def module_exists(modname, all_modules):
    """Check if an import target exists as one of our modules.

    Handles:
      - exact match (e.g. 'quant_nanggroe.config.settings' is a file)
      - package-with-__init__ match (e.g. 'quant_nanggroe.config' -> __init__.py)
      - namespace-package match (e.g. 'quant_nanggroe.config' has submodules
        even without an explicit __init__.py in the edge-triggered set)
    """
    if modname in all_modules:
        return True
    # Check if this is a reference to a package that has submodules
    # E.g. importing 'quant_nanggroe.engine.strategy.strategies' which is
    # a package containing individual strategy files
    pkg_prefix = modname + "."
    if any(m.startswith(pkg_prefix) for m in all_modules):
        return True
    # Also check the special case: 'quant_nanggroe' itself
    # when someone does 'from quant_nanggroe import ...'
    pkg_init = modname + ".__init__"
    if pkg_init in all_modules:
        return True
    return False


def scan(modules):
    """Build import graph: module -> set of modules it imports."""
    module_imports = {}
    for modname, path in modules.items():
        imports = parse_imports(path)
        # Only keep imports that start with 'quant_nanggroe' (internal references)
        internal = {i for i in imports if i.startswith("quant_nanggroe") or i.startswith("qna")}
        module_imports[modname] = internal
    return module_imports


def compute_reverse_graph(module_imports):
    """Reverse graph: module -> set of modules that import it."""
    rev = defaultdict(set)
    for src, targets in module_imports.items():
        for tgt in targets:
            rev[tgt].add(src)
    return rev


def find_dangling(module_imports, all_modules):
    """Find dangling import references."""
    dangling = defaultdict(list)
    for src, targets in module_imports.items():
        for tgt in targets:
            if not module_exists(tgt, all_modules):
                dangling[src].append(tgt)
    return dangling


def generate_html(modules, module_imports, reverse_graph, dangling):
    modnames = sorted(modules.keys())
    total = len(modnames)

    # Which modules are isolated (imported by no other module)?
    isolated_total = 0
    rows = []
    for m in modnames:
        importers = reverse_graph.get(m, set())
        importers = {i for i in importers if i != m}  # exclude self
        if not importers:
            status = "⚠️ ISOLATED"
            isolated_total += 1
            conn_from = ""
        else:
            status = "✅"
            conn_from = ", ".join(sorted(importers)[:10])
            if len(importers) > 10:
                conn_from += f" … (+{len(importers)-10} more)"
        rows.append((m, status, conn_from))

    dangling_total = sum(len(v) for v in dangling.values())

    today = date.today().isoformat()

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>QNA Module Graph</title>
<style>
body{{font-family:monospace;background:#0f0f23;color:#ccc;padding:20px;max-width:1200px}}
h1{{color:#0f0}} h2{{color:#0a0}} .count{{color:#0f0;font-size:1.2em}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th,td{{border:1px solid #333;padding:4px 8px;text-align:left}}
th{{background:#1a1a3e;color:#0f0;position:sticky;top:0}}
tr:hover{{background:#1a1a3e}}
.iso{{color:#ff0}} .ok{{color:#0f0}} .err{{color:#f44}} .warn{{color:#ff0}}
</style></head>
<body>
<h1>Quant-Nanggroe-AI — Module Connection Graph</h1>
<p>Generated: {today} | <span class="count">Modules: {total}</span> | Isolated: {isolated_total} | Dangling: {dangling_total}</p>

<h2>Dangling Imports</h2>
"""
    if dangling:
        html += "<table><tr><th>Source Module</th><th>Dangling Import</th></tr>\n"
        for src, tgts in sorted(dangling.items()):
            for t in sorted(tgts):
                html += f"<tr><td class='warn'>{src}</td><td class='err'>{t}</td></tr>\n"
        html += "</table>\n"
    else:
        html += "<p class='ok'>✅ Zero dangling imports — all references resolve.</p>\n"

    html += f"""
<h2>Module Status — {total} total, {isolated_total} isolated, {dangling_total} dangling</h2>
<div style='overflow-y:auto;max-height:80vh'><table>
<tr><th>Module</th><th>Status</th><th>Connected From</th></tr>
"""
    for m, status, conn_from in rows:
        cls = "iso" if "ISOLATED" in status else "ok"
        html += f"<tr><td>{m}</td><td class='{cls}'>{status}</td><td>{conn_from}</td></tr>\n"
    html += "</table></div>\n"
    html += "<p><i>Graphify Scan v2 — AST-based import analysis</i></p>\n"
    html += "</body></html>"
    return html, total, isolated_total, dangling_total


def update_graph_index(total, isolated, dangling):
    """Update the GRAPH-INDEX.html with current module counts."""
    if not GRAPH_INDEX.exists():
        print(f"  SKIP: {GRAPH_INDEX} not found")
        return
    html = GRAPH_INDEX.read_text(encoding="utf-8")

    # Update module count in header
    import re
    html = re.sub(
        r'Modules: \d+',
        f'Modules: {total}',
        html,
    )
    # Update dangling imports row
    status = "✅" if dangling == 0 else "❌"
    badge = f"{dangling}" if dangling > 0 else "0"
    html = re.sub(
        r'<tr><td>Dangling Imports</td><td class="[^"]*">[^<]*</td><td>[^<]*</td></tr>',
        f'<tr><td>Dangling Imports</td><td class="ok">{status} {badge}</td><td>{"All resolved" if dangling == 0 else f"{dangling} unresolved"}</td></tr>',
        html,
    )
    # Update Module Graph section
    html = re.sub(
        r'<li class="[^"]*">quant_nanggroe\.\S+[^<]*</li>',
        "",
        html,
    )
    html = re.sub(
        r'(<h2>Module Graph</h2>\s*<ul>)',
        f'\\1\n<li class="ok">quant_nanggroe → {total} modules, {isolated} isolated, {dangling} dangling</li>',
        html,
    )

    GRAPH_INDEX.write_text(html, encoding="utf-8")
    print(f"  Updated: {GRAPH_INDEX}")
    print(f"    - Module count: {total}")
    print(f"    - Isolated: {isolated}")
    print(f"    - Dangling: {dangling}")


def main():
    print("=" * 60)
    print("Graphify Scan — Module Dependency Analysis")
    print("=" * 60)
    print(f"Repo: {REPO}")
    print(f"Scanning: {QNA}")
    print()

    print("[1/4] Finding modules...")
    modules = find_modules()
    print(f"  Found {len(modules)} Python modules in quant_nanggroe/")

    print("[2/4] Parsing imports via AST...")
    module_imports = scan(modules)
    internal_refs = sum(len(v) for v in module_imports.values())
    print(f"  Parsed {internal_refs} internal import references across {len(module_imports)} modules")

    print("[3/4] Building dependency graph...")
    reverse_graph = compute_reverse_graph(module_imports)
    dangling = find_dangling(module_imports, set(modules.keys()))
    dangling_total = sum(len(v) for v in dangling.values())
    isolated_total = sum(
        1 for m in modules if m not in reverse_graph or not {i for i in reverse_graph[m] if i != m}
    )
    print(f"  Reverse graph: {len(reverse_graph)} modules have importers")
    print(f"  Isolated modules: {isolated_total}")
    print(f"  Dangling imports: {dangling_total}")

    if dangling:
        print("\n  ⚠️  DANGLING IMPORTS FOUND:")
        for src, tgts in sorted(dangling.items()):
            for t in sorted(tgts):
                print(f"    {src} → {t}")
    else:
        print("\n  ✅ Zero dangling imports.")

    print("[4/4] Generating reports...")

    # Write GRAPH_SCAN.html
    html, total, isolated, dangling_count = generate_html(modules, module_imports, reverse_graph, dangling)
    out_path = REPO / "GRAPH_SCAN.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  Generated: {out_path}")

    # Update GRAPH-INDEX.html
    update_graph_index(total, isolated, dangling_count)

    print()
    print("=" * 60)
    print("FINAL COUNTS:")
    print(f"  Modules:  {total}")
    print(f"  Isolated: {isolated}")
    print(f"  Dangling: {dangling_count}")
    print(f"  Verified: {'✅ ZERO DANGLING' if dangling_count == 0 else '❌ HAS DANGLING'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
