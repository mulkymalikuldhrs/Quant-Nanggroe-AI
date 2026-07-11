#!/usr/bin/env python3
"""CI compliance gate — env vars, .gitignore, no print() in prod code."""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {"tests", ".git", "__pycache__", ".venv", "venv", "env", "node_modules", "archive"}
# Production source dirs — only scan these for print() statements
PROD_SOURCE_DIRS = ["quant_nanggroe", "ai_multicolony"]

errors: list[str] = []


def check_env_vars():
    example = REPO / ".env.example"
    env = REPO / ".env"
    if not example.exists():
        errors.append("MISSING .env.example — expected at repo root")
        return
    if not env.exists():
        errors.append("MISSING .env — expected at repo root")
        return

    example_vars = {
        line.split("=")[0].strip()
        for line in example.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    }
    env_vars = {
        line.split("=")[0].strip()
        for line in env.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    }

    for var in sorted(example_vars):
        if var not in env_vars:
            errors.append(f"MISSING ENV VAR: {var} defined in .env.example but not in .env")


def check_env_gitignore():
    gitignore = REPO / ".gitignore"
    if not gitignore.exists():
        errors.append("MISSING .gitignore")
        return
    content = gitignore.read_text()
    if ".env" not in content.splitlines():
        errors.append("GITIGNORE: .env is not listed in .gitignore")


def check_print_statements():
    for source_dir in PROD_SOURCE_DIRS:
        if not (REPO / source_dir).exists():
            continue
        for path in (REPO / source_dir).rglob("*.py"):
            rel = path.relative_to(REPO)
            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if re.match(r"^\s*print\s*\(", stripped):
                    errors.append(f"PRINT STATEMENT: {rel}:{lineno} — {stripped[:80]}")


def main():
    check_env_vars()
    check_env_gitignore()
    check_print_statements()

    if errors:
        print("::group::Compliance Gate FAILED")
        for err in errors:
            print(f"  ❌  {err}")
        print("::endgroup::")
        sys.exit(1)
    else:
        print("✅ Compliance gate passed — all checks OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
