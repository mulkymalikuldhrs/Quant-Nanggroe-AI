#!/usr/bin/env python
"""QNA knowledge-graph builder (read-only, stdlib AST).
Entities: modules, classes, functions. Relationships: imports, calls, inherits.
"""
import ast, os, json, sys

BASE = r"D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe"
OUT = r"C:\Users\Hi\AppData\Local\hermes\scripts\qna_graph"
os.makedirs(OUT, exist_ok=True)

SKIP = {"node_modules", ".git", "__pycache__", ".venv", "venv", "graphify-out", ".pytest_cache", "build", "dist"}

def mod_name(path):
    rel = os.path.relpath(path, BASE).replace("\\", "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith("/__init__"):
        rel = rel[:-len("/__init__")]
    return rel.replace("/", ".")

nodes = {}   # id -> {type, module, file}
edges = []   # {source, target, type}
defined_funcs = set()
defined_classes = set()

pyfiles = []
for root, dirs, files in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for f in files:
        if f.endswith(".py"):
            pyfiles.append(os.path.join(root, f))

parse_errors = 0
for path in pyfiles:
    m = mod_name(path)
    nodes[m] = {"type": "module", "module": m, "file": os.path.relpath(path, BASE)}
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src, filename=path)
    except Exception:
        parse_errors += 1
        continue

    class V(ast.NodeVisitor):
        def __init__(self):
            self.scope = m
        def visit_Import(self, node):
            for a in node.names:
                edges.append({"source": m, "target": a.name, "type": "imports"})
            self.generic_visit(node)
        def visit_ImportFrom(self, node):
            base = node.module or ""
            for a in node.names:
                tgt = (base + "." + a.name) if base else a.name
                edges.append({"source": m, "target": base or tgt, "type": "imports"})
            self.generic_visit(node)
        def visit_ClassDef(self, node):
            cid = f"{m}.{node.name}"
            nodes[cid] = {"type": "class", "module": m, "file": os.path.relpath(path, BASE)}
            defined_classes.add(cid)
            edges.append({"source": m, "target": cid, "type": "contains"})
            for b in node.bases:
                bn = ast.unparse(b) if hasattr(ast, "unparse") else getattr(b, "id", "?")
                edges.append({"source": cid, "target": bn, "type": "inherits"})
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fid = f"{cid}.{item.name}"
                    nodes[fid] = {"type": "method", "module": m, "file": os.path.relpath(path, BASE)}
                    defined_funcs.add(item.name)
                    edges.append({"source": cid, "target": fid, "type": "contains"})
            self.generic_visit(node)
        def visit_FunctionDef(self, node):
            fid = f"{m}.{node.name}"
            if fid not in nodes:
                nodes[fid] = {"type": "function", "module": m, "file": os.path.relpath(path, BASE)}
                defined_funcs.add(node.name)
                edges.append({"source": m, "target": fid, "type": "contains"})
            self.generic_visit(node)
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_Call(self, node):
            fn = node.func
            name = None
            if isinstance(fn, ast.Name):
                name = fn.id
            elif isinstance(fn, ast.Attribute):
                name = fn.attr
            if name and name in defined_funcs:
                edges.append({"source": m, "target": name, "type": "calls"})
            self.generic_visit(node)
    V().visit(tree)

graph = {"nodes": [dict(id=k, **v) for k, v in nodes.items()], "links": edges}
with open(os.path.join(OUT, "graph.json"), "w", encoding="utf-8") as fh:
    json.dump(graph, fh, indent=1)

# stats
from collections import Counter
ntypes = Counter(v["type"] for v in nodes.values())
etypes = Counter(e["type"] for e in edges)

# code_map.md
lines = ["# QNA Code Map\n", f"Base: `{BASE}`\n"]
lines.append(f"- Files parsed: {len(pyfiles)} ({parse_errors} parse errors)")
lines.append(f"- Nodes: {len(nodes)}  |  Edges: {len(edges)}\n")
lines.append("## Node types")
for t, c in ntypes.most_common():
    lines.append(f"- {t}: {c}")
lines.append("\n## Edge types")
for t, c in etypes.most_common():
    lines.append(f"- {t}: {c}")
# top-level packages
pkgs = Counter(m.split(".")[0] for m in nodes if nodes[m]["type"] == "module")
lines.append("\n## Top-level packages (module count)")
for p, c in pkgs.most_common(25):
    lines.append(f"- {p}: {c}")
with open(os.path.join(OUT, "code_map.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print(json.dumps({"files": len(pyfiles), "parse_errors": parse_errors,
                  "nodes": len(nodes), "edges": len(edges),
                  "node_types": dict(ntypes), "edge_types": dict(etypes)}, indent=1))
