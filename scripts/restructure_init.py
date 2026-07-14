#!/usr/bin/env python3
"""
Restructure Phase 1: Add missing __init__.py files and fill empty ones.
Dhaher Labs Quant Nanggroe Hedge Fund
"""
import os

BASE = r"D:\repositories\Quant-Nanggroe-AI-worktree"

print("=== PHASE 1: Adding missing __init__.py files ===")
print()

# Directories needing __init__.py
dirs_needing_init = [
    "alembic",
    "engine",
    r"packages\agentic-legacy",
    r"packages\agentic-legacy\web_interface",
    r"packages\hermes-quant\config",
    r"packages\hermes-quant\scripts",
    r"packages\hermes-quant\tests",
    "scripts",
    r"skills\aminer-academic-search\scripts",
    r"skills\aminer-daily-paper\scripts",
    r"skills\blog-writer",
    r"skills\dream-interpreter\scripts",
    r"skills\get-fortune-analysis",
    r"skills\gift-evaluator",
    r"skills\interview-prep\scripts",
    r"skills\jd-resume-tailor\scripts",
    r"skills\job-intent-tracker\scripts",
    r"skills\market-research-reports\scripts",
    r"skills\pdf\scripts",
    r"skills\pptx\ooxml\scripts",
    r"skills\pptx\scripts",
    r"skills\qingyan-research",
    r"skills\quiz-html\scripts",
    r"skills\quiz-mastery\scripts",
    r"skills\resume-builder\scripts",
    r"skills\skill-creator\eval-viewer",
    r"skills\storyboard-manager\scripts",
    r"skills\xlsx",
    r"skills\xlsx\templates",
    "web_interface",
    r"quant_nanggroe\bridge",
    r"quant_nanggroe\database\alembic",
    r"quant_nanggroe\engine\data",
    r"quant_nanggroe\engine\live",
    r"quant_nanggroe\providers",
    r"quant_nanggroe\strategies",
    r"tests\test_agents",
    r"tests\test_api",
    r"tests\test_exchange",
]

added = 0
for d in dirs_needing_init:
    dirpath = os.path.join(BASE, d)
    if not os.path.isdir(dirpath):
        print("  [SKIP] %s - directory not found" % d)
        continue
    init_path = os.path.join(dirpath, "__init__.py")
    if os.path.exists(init_path):
        print("  [EXISTS] %s/__init__.py" % d)
        continue

    # Get .py files (excluding __init__.py itself)
    py_files = sorted([f[:-3] for f in os.listdir(dirpath)
                       if f.endswith(".py") and f != "__init__.py"])

    # Build content
    lines = []
    lines.append("#" + "=" * 60)
    lines.append("# %s - Auto-generated package init" % os.path.basename(d))
    lines.append("# Dhaher Labs Quant Nanggroe Hedge Fund")
    lines.append("#" + "=" * 60)
    lines.append("")

    if py_files:
        lines.append("__all__ = [")
        for f in py_files:
            lines.append('    "%s",' % f)
        lines.append("]")
        lines.append("")
        for f in py_files:
            lines.append("from .%s import *" % f)
    else:
        lines.append("# Package marker")

    lines.append("")

    with open(init_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    added += 1
    print("  [ADDED] %s/__init__.py (%d modules)" % (d, len(py_files)))

print()
print("Added %d new __init__.py files" % added)

print()
print("=== PHASE 2: Filling empty __init__.py files ===")
print()

empty_inits = [
    r"alembic\versions",
    r"quant_nanggroe\database\alembic\versions",
    r"quant_nanggroe\data\models",
    r"skills\skill-creator\scripts",
    r"skills\ui-ux-pro-max\scripts",
    r"tests\test_backtest",
    r"tests\test_browser",
    r"tests\test_channels",
    r"tests\test_colony",
    r"tests\test_core",
    r"tests\test_data",
    r"tests\test_engine",
    r"tests\test_mcp",
    r"tests\test_memory",
    r"tests\test_nvidia_nim",
    r"tests\test_sandbox",
    r"tests\test_scripts",
    r"tests\test_strategy",
    r"tests\test_tools",
    r"tests\test_types",
]

filled = 0
for d in empty_inits:
    dirpath = os.path.join(BASE, d)
    init_path = os.path.join(dirpath, "__init__.py")
    if not os.path.exists(init_path):
        print("  [SKIP] %s - not found" % d)
        continue

    # Get .py files
    py_files = sorted([f[:-3] for f in os.listdir(dirpath)
                       if f.endswith(".py") and f != "__init__.py"])

    lines = []
    lines.append("#" + "=" * 60)
    lines.append("# %s - Test/Module init" % os.path.basename(d))
    lines.append("# Dhaher Labs Quant Nanggroe Hedge Fund")
    lines.append("#" + "=" * 60)
    lines.append("")

    if py_files:
        lines.append("__all__ = [")
        for f in py_files:
            lines.append('    "%s",' % f)
        lines.append("]")
        lines.append("")
        for f in py_files:
            lines.append("from .%s import *" % f)
    else:
        lines.append("# Package marker - no modules yet")

    lines.append("")

    with open(init_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    filled += 1
    print("  [FILLED] %s/__init__.py" % d)

print()
print("Filled %d empty __init__.py files" % filled)
print()
print("=== DONE ===")
