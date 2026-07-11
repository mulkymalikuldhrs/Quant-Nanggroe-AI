#!/usr/bin/env python3
"""qna-architect — Quant Nanggroe Codebase Transparency Tool.

Statically analyzes all 414+ Python files:
  - Resolves every import to an actual file path
  - Detects orphans (zero incoming imports)
  - Detects circular imports
  - Detects dead exports (unused symbols in __init__.py)
  - Traces entrypoints → reachable coverage
  - Generates mermaid.js dependency graphs
  - Reports all errors with severity ranking

Usage:
  python3 scripts/qna-architect.py               # full report
  python3 scripts/qna-architect.py --mermaid      # package-level graph
  python3 scripts/qna-architect.py --check        # CI mode (exit 1 on errors)
  python3 scripts/qna-architect.py --focus engine/risk  # deep-dive one package
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ── Config ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
QNA_DIR = REPO_ROOT / "quant_nanggroe"
ENTRYPOINTS = ["cli.py", "api.py", "worker.py", "services.py"]
STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit",
    "base64", "bdb", "binascii", "bisect", "builtins", "bz2",
    "calendar", "codecs", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars",
    "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes",
    "dataclasses", "datetime", "dbm", "decimal", "difflib",
    "dis", "distutils", "doctest", "email", "encodings", "enum",
    "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
    "fnmatch", "fractions", "ftplib", "functools",
    "gc", "getopt", "getpass", "gettext", "glob", "grp",
    "gzip", "hashlib", "heapq", "hmac", "html", "http",
    "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect",
    "io", "ipaddress", "itertools",
    "json", "keyword",
    "lib2to3", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes",
    "mmap", "modulefinder", "multiprocessing",
    "netrc", "nis", "nntplib", "numbers",
    "operator", "optparse", "os", "ossaudiodev",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
    "platform", "plistlib", "poplib", "posix", "posixpath",
    "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
    "pyclbr", "pydoc", "queue", "quopri",
    "random", "re", "readline", "reprlib", "resource", "rlcompleter",
    "runpy", "sched", "secrets", "select", "selectors",
    "shelve", "shlex", "shutil", "signal", "site", "smtpd",
    "smtplib", "sndhdr", "socket", "socketserver", "sqlite3",
    "ssl", "stat", "statistics", "string", "stringprep",
    "struct", "subprocess", "sunau", "symtable", "sys",
    "sysconfig", "syslog",
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
    "test", "textwrap", "threading", "time", "timeit",
    "tkinter", "token", "tokenize", "trace", "traceback",
    "tracemalloc", "tty", "turtle", "turtledemo", "types",
    "typing", "typing_extensions",
    "unicodedata", "unittest", "urllib", "uu", "uuid",
    "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref",
    "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
    "zoneinfo",
    # non-stdlib but known unavailable
    "__future__",
}


@dataclass
class ResolvedImport:
    module_name: str
    resolved_path: Optional[str]
    is_local: bool
    line_number: int
    names: List[str]

@dataclass
class FileInfo:
    path: str
    rel_path: str
    package: str
    lines: int
    imports: List[ResolvedImport] = field(default_factory=list)
    defined_symbols: List[str] = field(default_factory=list)
    exported_symbols: List[str] = field(default_factory=list)
    has_init: bool = False

@dataclass
class AnalysisReport:
    files: Dict[str, FileInfo]
    import_graph: Dict[str, Set[str]]
    reverse_graph: Dict[str, Set[str]]
    orphans: List[str]
    circular_imports: List[List[str]]
    missing_imports: List[Tuple[str, str, int]]
    dead_exports: List[Tuple[str, List[str]]]
    entrypoint_coverage: Dict[str, float]
    errors: List[str]


# ── AST Parsing ────────────────────────────────────────────────────────

def parse_file(filepath: Path, rel_to_qna: Path) -> Optional[FileInfo]:
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    try:
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError:
        return None

    lines = len(content.splitlines())
    info = FileInfo(
        path=str(filepath),
        rel_path=str(rel_to_qna),
        package=str(rel_to_qna.parent).replace("/", ".").lstrip("."),
        lines=lines,
    )

    # Determine if this is an __init__ file
    info.has_init = filepath.name == "__init__.py"

    for node in ast.walk(tree):
        # Import statements: import X, import X.Y
        if isinstance(node, ast.Import):
            for alias in node.names:
                imp = _resolve_import(alias.name, info.package, 0, [], node.lineno or 0)
                if imp:
                    info.imports.append(imp)

        # ImportFrom statements: from X import Y, from . import Z
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            names = [a.name for a in node.names]
            imp = _resolve_import(module, info.package, level, names, node.lineno or 0)
            if imp:
                info.imports.append(imp)

        # Top-level definitions (classes, functions, assigns)
        if isinstance(node, ast.ClassDef):
            info.defined_symbols.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            info.defined_symbols.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    info.defined_symbols.append(target.id)

    return info


def _resolve_import(module: str, current_package: str, level: int,
                    names: List[str], lineno: int) -> Optional[ResolvedImport]:
    # Build the full dotted module path
    if level > 0:
        # Relative import
        parts = current_package.split(".")
        if len(parts) >= level:
            base = parts[:-level]
        else:
            base = []
        full_module = ".".join(base + ([module] if module else []))
    else:
        full_module = module

    if not full_module:
        return None

    # Resolve to file path
    pkg_name = full_module.split(".")[0]

    # Check if local (starts with quant_nanggroe or is a relative sibling)
    is_local = full_module.startswith("quant_nanggroe") or (
        level > 0 and current_package.startswith("quant_nanggroe")
    )

    resolved = None
    if is_local:
        resolved = _resolve_local_path(full_module, QNA_DIR)

    return ResolvedImport(
        module_name=full_module,
        resolved_path=resolved,
        is_local=is_local,
        line_number=lineno,
        names=names,
    )


def _resolve_local_path(module: str, base_dir: Path) -> Optional[str]:
    """Convert 'quant_nanggroe.engine.risk' to 'quant_nanggroe/engine/risk/__init__.py'."""
    # Remove leading package if starts with quant_nanggroe
    parts = module.split(".")
    if parts[0] == "quant_nanggroe":
        parts = parts[1:]

    if not parts:
        return str(base_dir / "__init__.py")

    # Try as package: path/to/module/__init__.py
    pkg_path = base_dir.joinpath(*parts) / "__init__.py"
    if pkg_path.exists():
        return str(pkg_path)

    # Try as module: path/to/module.py
    mod_path = base_dir.joinpath(*parts)
    parent = mod_path.parent / (mod_path.name + ".py")
    if parent.exists():
        return str(parent)

    return None


# ── Graph Building ────────────────────────────────────────────────────

def build_graph(files: Dict[str, FileInfo]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]], List[Tuple[str, str, int]]]:
    graph: Dict[str, Set[str]] = defaultdict(set)
    reverse: Dict[str, Set[str]] = defaultdict(set)
    missing: List[Tuple[str, str, int]] = []

    for rel_path, info in files.items():
        for imp in info.imports:
            if not imp.is_local:
                continue
            if imp.resolved_path:
                target_rel = os.path.relpath(imp.resolved_path, str(QNA_DIR))
                graph[rel_path].add(target_rel)
                reverse[target_rel].add(rel_path)
            else:
                missing.append((rel_path, imp.module_name, imp.line_number))

    return dict(graph), dict(reverse), missing


def detect_orphans(files: Dict[str, FileInfo], graph: Dict[str, Set[str]],
                   reverse: Dict[str, Set[str]], entrypoints: Set[str]) -> List[str]:
    """Files with zero incoming imports from other local files (excluding entrypoints)."""
    orphans = []
    for rel_path in files:
        if rel_path in entrypoints:
            continue
        if rel_path.endswith("__init__.py"):
            continue
        incoming = len(reverse.get(rel_path, set()))
        if incoming == 0:
            # Check if it's reachable from any __init__.py re-export
            # Simple check: does any file reference its package?
            pkg_dir = os.path.dirname(rel_path)
            pkg_init = os.path.join(pkg_dir, "__init__.py") if pkg_dir else ""
            incoming_via_pkg = len(reverse.get(pkg_init, set())) if pkg_init in reverse else 0
            if incoming_via_pkg == 0:
                orphans.append(rel_path)
    return sorted(orphans)


def detect_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Tarjan's algorithm for strongly connected components with size > 1."""
    index_counter = [0]
    stack = []
    lowlink: Dict[str, int] = {}
    index: Dict[str, int] = {}
    on_stack: Dict[str, bool] = {}
    sccs = []

    def strongconnect(v: str):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in graph.get(v, set()):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w, False):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                sccs.append(scc)

    nodes = list(graph.keys())
    for v in nodes:
        if v not in index:
            strongconnect(v)

    return sccs


def detect_dead_exports(files: Dict[str, FileInfo], reverse: Dict[str, Set[str]]) -> List[Tuple[str, List[str]]]:
    """Symbols exported by __init__.py but never imported by any other module."""
    dead = []
    for rel_path, info in files.items():
        if not info.has_init or not info.exported_symbols:
            continue
        unused = []
        for sym in info.exported_symbols:
            # Check if any import references this symbol from this package
            imported_anywhere = False
            for other_path, other_info in files.items():
                if other_path == rel_path:
                    continue
                for imp in other_info.imports:
                    if imp.module_name == "quant_nanggroe." + info.package and sym in imp.names:
                        imported_anywhere = True
                        break
                    # Also check `from quant_nanggroe.engine import KillSwitch`
                    parent = ".".join(info.package.split(".")[:-1])
                    if parent and imp.module_name == "quant_nanggroe." + parent and sym in imp.names:
                        imported_anywhere = True
                        break
                if imported_anywhere:
                    break
            if not imported_anywhere:
                unused.append(sym)
        if unused:
            dead.append((rel_path, unused))
    return dead


def trace_entrypoints(files: Dict[str, FileInfo], graph: Dict[str, Set[str]],
                      entrypoint_names: List[str]) -> Dict[str, float]:
    """BFS from entrypoints → what % of files are reachable."""
    total = len(files)
    coverage = {}
    for ep_name in entrypoint_names:
        # Find the actual file path
        ep_path = None
        for rel_path in files:
            if rel_path.endswith(ep_name):
                ep_path = rel_path
                break
        if not ep_path:
            continue

        visited: Set[str] = set()
        queue = [ep_path]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for neighbor in graph.get(current, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        coverage[ep_name] = len(visited) / total * 100 if total > 0 else 0

    return coverage


# ── Mermaid Rendering ──────────────────────────────────────────────────

def generate_mermaid(files: Dict[str, FileInfo], graph: Dict[str, Set[str]],
                     orphans: List[str], cycles: List[List[str]],
                     focus_package: str = "") -> str:
    lines = ["graph TD"]

    # Group by top-level package
    packages: Dict[str, List[str]] = defaultdict(list)
    for rel_path in files:
        parts = rel_path.split("/")
        pkg = parts[0] if len(parts) > 1 else "root"
        if focus_package and focus_package not in rel_path:
            continue
        packages[pkg].append(rel_path)

    orphan_set = set(orphans)
    cycle_nodes: Set[str] = set()
    for cycle in cycles:
        cycle_nodes.update(cycle)

    # Build subgraphs per package
    for pkg, file_list in sorted(packages.items()):
        if not file_list:
            continue
        is_focused = focus_package and focus_package in pkg
        if not is_focused and len(file_list) > 20:
            # For large packages not in focus mode, show only __init__ files
            file_list = [f for f in file_list if f.endswith("__init__.py") or f in orphan_set or f in cycle_nodes]
            if not file_list:
                continue

        label = pkg.replace("_", " ")
        lines.append(f"  subgraph {pkg} [\"{label}\"]")
        for rel_path in sorted(file_list):
            node_id = _node_id(rel_path)
            label = os.path.basename(rel_path)
            lines.append(f"    {node_id}[{label}]")
        lines.append("  end")

        # Edges between files in this package
        for rel_path in file_list:
            src_id = _node_id(rel_path)
            for target in graph.get(rel_path, set()):
                if target in file_list:
                    tgt_id = _node_id(target)
                    lines.append(f"  {src_id} --> {tgt_id}")

    # Cross-package edges
    for rel_path, targets in graph.items():
        src_id = _node_id(rel_path)
        for target in targets:
            tgt_id = _node_id(target)
            if _in_subgraph(rel_path) != _in_subgraph(target):
                lines.append(f"  {src_id} -.-> {tgt_id}")

    # Highlight orphans
    for orphan in orphan_set:
        nid = _node_id(orphan)
        lines.append(f"  style {nid} fill:#ff9,stroke:#f90")

    # Highlight cycle nodes
    for node in cycle_nodes:
        nid = _node_id(node)
        lines.append(f"  style {nid} stroke:#f00,stroke-width:2px")

    return "\n".join(lines)


def _node_id(path: str) -> str:
    return path.replace("/", "_").replace(".", "_").replace("-", "_")


def _in_subgraph(path: str) -> str:
    return path.split("/")[0] if "/" in path else "root"


# ── Report Generation ──────────────────────────────────────────────────

def generate_report(files: Dict[str, FileInfo], graph: Dict[str, Set[str]],
                    reverse: Dict[str, Set[str]], orphans: List[str],
                    cycles: List[List[str]], missing: List[Tuple[str, str, int]],
                    dead_exports: List[Tuple[str, List[str]]],
                    coverage: Dict[str, float]) -> str:
    total_files = len(files)
    total_lines = sum(f.lines for f in files.values())
    incoming_counts = {p: len(v) for p, v in reverse.items()}

    lines_out = []
    w = lines_out.append

    w("=" * 64)
    w("  QNA CODEBASE ARCHITECTURE REPORT")
    w("=" * 64)
    w("")

    # Summary
    w(f"  Files:            {total_files}")
    w(f"  Lines:            {total_lines}")
    w(f"  Packages:         {len({f.package for f in files.values()})}")
    w(f"  Entrypoints:      {', '.join(ENTRYPOINTS)}")
    w("")

    # Health indicators
    w("─" * 40)
    w("  HEALTH SUMMARY")
    w("─" * 40)
    w(f"  Orphans:          {len(orphans)}")
    w(f"  Circular imports: {len(cycles)}")
    w(f"  Missing imports:  {len(missing)}")
    w(f"  Dead exports:     {sum(len(syms) for _, syms in dead_exports)}")
    w("")

    for ep_name, pct in coverage.items():
        status = "OK" if pct > 50 else "WARN" if pct > 20 else "LOW"
        w(f"  Entrypoint {ep_name}: {pct:.1f}% coverage ({status})")

    w("")

    # Orphans
    if orphans:
        w("─" * 40)
        w(f"  ORPHANS — {len(orphans)} files with zero incoming imports")
        w("─" * 40)
        for orphan in orphans[:30]:
            info = files.get(orphan)
            pkg = info.package if info else "?"
            w(f"  • {orphan}  [{pkg}]")
        if len(orphans) > 30:
            w(f"  ... and {len(orphans) - 30} more")
        w("")

    # Circular imports
    if cycles:
        w("─" * 40)
        w(f"  CIRCULAR IMPORTS — {len(cycles)} cycles")
        w("─" * 40)
        for i, cycle in enumerate(cycles[:10], 1):
            w(f"  Cycle {i}:")
            for node in cycle:
                w(f"    {node}")
            w("")
        if len(cycles) > 10:
            w(f"  ... and {len(cycles) - 10} more")
        w("")

    # Missing imports
    if missing:
        w("─" * 40)
        w(f"  MISSING IMPORTS — {len(missing)} unresolved")
        w("─" * 40)
        for src, mod, lineno in missing[:20]:
            w(f"  • {src}:{lineno}  -> {mod}")
        if len(missing) > 20:
            w(f"  ... and {len(missing) - 20} more")
        w("")

    # Dead exports
    if dead_exports:
        w("─" * 40)
        w("  DEAD EXPORTS — unused __init__.py symbols")
        w("─" * 40)
        for path, syms in dead_exports[:10]:
            w(f"  • {path}: {', '.join(syms)}")
        if len(dead_exports) > 10:
            w(f"  ... and {len(dead_exports) - 10} more")
        w("")

    # Top-level import counts
    w("─" * 40)
    w("  MOST IMPORTED MODULES (by incoming edges)")
    w("─" * 40)
    sorted_incoming = sorted(incoming_counts.items(), key=lambda x: -x[1])
    for path, count in sorted_incoming[:15]:
        w(f"  {count:3d}x  {path}")
    w("")

    # Package dependency matrix (top-level)
    w("─" * 40)
    w("  CROSS-PACKAGE DEPENDENCIES")
    w("─" * 40)
    pkg_edges: Dict[Tuple[str, str], int] = defaultdict(int)
    for src, targets in graph.items():
        src_pkg = src.split("/")[0]
        for tgt in targets:
            tgt_pkg = tgt.split("/")[0]
            if src_pkg != tgt_pkg:
                pkg_edges[(src_pkg, tgt_pkg)] += 1
    for (src, tgt), count in sorted(pkg_edges.items(), key=lambda x: -x[1]):
        w(f"  {src}  -->  {tgt}  ({count} edges)")

    w("")
    w("=" * 64)
    w("  REPORT COMPLETE")
    w("=" * 64)

    return "\n".join(lines_out)


# ── Main ────────────────────────────────────────────────────────────────

def scan_all_files() -> Dict[str, FileInfo]:
    files: Dict[str, FileInfo] = {}
    for pyfile in sorted(QNA_DIR.rglob("*.py")):
        rel = pyfile.relative_to(QNA_DIR)
        info = parse_file(pyfile, rel)
        if info:
            files[str(rel)] = info
    return files


def extract_init_exports(files: Dict[str, FileInfo]) -> None:
    """Extract __all__ and lazy-import exports from __init__.py files."""
    for rel_path, info in files.items():
        if not info.has_init:
            continue
        filepath = Path(info.path)
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
        except Exception:
            continue

        # Extract __all__
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    info.exported_symbols.append(elt.value)

            # Extract lazy import keys (__getattr__ pattern)
            if isinstance(node, ast.FunctionDef) and node.name == "__getattr__":
                for child in ast.walk(node):
                    if isinstance(child, ast.Dict):
                        for key in child.keys:
                            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                info.exported_symbols.append(key.value)


def run_analysis(focus_package: str = "", check_mode: bool = False) -> Dict:
    print(f"Scanning {QNA_DIR}...", file=sys.stderr)
    files = scan_all_files()
    extract_init_exports(files)
    print(f"  Found {len(files)} Python files", file=sys.stderr)

    graph, reverse, missing = build_graph(files)
    print(f"  Built dependency graph ({sum(len(v) for v in graph.values())} edges)", file=sys.stderr)

    entrypoint_set = set()
    for ep in ENTRYPOINTS:
        for rel_path in files:
            if rel_path.endswith(ep):
                entrypoint_set.add(rel_path)
                break

    orphans = detect_orphans(files, graph, reverse, entrypoint_set)
    cycles = detect_cycles(graph)
    dead_exports = detect_dead_exports(files, reverse)
    coverage = trace_entrypoints(files, graph, ENTRYPOINTS)

    report = generate_report(files, graph, reverse, orphans, cycles,
                             missing, dead_exports, coverage)
    mermaid = generate_mermaid(files, graph, orphans, cycles, focus_package)

    if check_mode:
        error_count = len(orphans) + len(cycles) + len(missing) + sum(len(s) for _, s in dead_exports)
        status = "PASS" if error_count == 0 else f"FAIL ({error_count} issues)"
        print(f"CHECK: {status}", file=sys.stderr)

    return {
        "summary": {
            "files": len(files),
            "lines": sum(f.lines for f in files.values()),
            "orphans": len(orphans),
            "cycles": len(cycles),
            "missing_imports": len(missing),
            "dead_exports": sum(len(s) for _, s in dead_exports),
        },
        "orphans": orphans[:50],
        "cycles": cycles[:20],
        "missing": [{"file": s, "module": m, "line": l} for s, m, l in missing[:50]],
        "coverage": coverage,
        "report_text": report,
        "mermaid": mermaid,
    }


def main():
    parser = argparse.ArgumentParser(description="QNA Codebase Architect")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--mermaid", action="store_true", help="Output mermaid graph only")
    parser.add_argument("--check", action="store_true", help="CI mode: exit 1 on issues")
    parser.add_argument("--focus", type=str, default="", help="Deep-dive one package (e.g. engine/risk)")
    args = parser.parse_args()

    result = run_analysis(focus_package=args.focus, check_mode=args.check)

    if args.mermaid:
        print(result["mermaid"])
    elif args.json:
        # Remove text fields for clean JSON
        clean = dict(result)
        del clean["report_text"]
        del clean["mermaid"]
        print(json.dumps(clean, indent=2))
    else:
        print(result["report_text"])
        print()
        print("─" * 40)
        print("  MERMAID GRAPH")
        print("─" * 40)
        print(result["mermaid"])

    if args.check:
        total = result["summary"]["orphans"] + result["summary"]["cycles"] + \
                result["summary"]["missing_imports"] + result["summary"]["dead_exports"]
        sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
