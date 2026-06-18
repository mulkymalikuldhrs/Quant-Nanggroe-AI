#!/usr/bin/env python3
"""Security Audit Scanner — Quant Nanggroe AI.

Scans the codebase for:
    - Hardcoded API keys / secrets
    - Hardcoded passwords / credentials
    - Insecure imports (pickle, subprocess with shell=True, eval, exec)
    - SQL injection patterns (string formatting in queries)
    - Debug / development leftovers

Usage:
    python scripts/security_audit.py
    python scripts/security_audit.py --path quant_nanggroe/
    python scripts/security_audit.py --json

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Patterns ──────────────────────────────────────────────────────────────────

@dataclass
class ScanPattern:
    name: str
    pattern: re.Pattern
    severity: str  # critical, high, medium, low, info
    description: str


SECRET_PATTERNS = [
    ScanPattern(
        name="hardcoded_api_key",
        pattern=re.compile(
            r"""(?:api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]""",
            re.IGNORECASE,
        ),
        severity="critical",
        description="Hardcoded API key detected",
    ),
    ScanPattern(
        name="hardcoded_secret",
        pattern=re.compile(
            r"""(?:secret[_-]?key|client[_-]?secret)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]""",
            re.IGNORECASE,
        ),
        severity="critical",
        description="Hardcoded secret key detected",
    ),
    ScanPattern(
        name="hardcoded_password",
        pattern=re.compile(
            r"""(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{4,}['\"]""",
            re.IGNORECASE,
        ),
        severity="critical",
        description="Hardcoded password detected",
    ),
    ScanPattern(
        name="aws_access_key",
        pattern=re.compile(r"AKIA[0-9A-Z]{16}"),
        severity="critical",
        description="AWS access key ID detected",
    ),
    ScanPattern(
        name="private_key_header",
        pattern=re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
        severity="critical",
        description="Private key embedded in source",
    ),
    ScanPattern(
        name="bearer_token",
        pattern=re.compile(
            r"""(?:bearer|token)\s*[:=]\s*['\"][A-Za-z0-9_\-\.]{20,}['\"]""",
            re.IGNORECASE,
        ),
        severity="high",
        description="Bearer/token credential hardcoded",
    ),
]

INSECURE_IMPORT_PATTERNS = [
    ScanPattern(
        name="pickle_usage",
        pattern=re.compile(r"\bimport\s+pickle\b|\bfrom\s+pickle\s+import\b"),
        severity="medium",
        description="pickle can execute arbitrary code on deserialization",
    ),
    ScanPattern(
        name="eval_usage",
        pattern=re.compile(r"\beval\s*\("),
        severity="high",
        description="eval() can execute arbitrary code",
    ),
    ScanPattern(
        name="exec_usage",
        pattern=re.compile(r"\bexec\s*\("),
        severity="high",
        description="exec() can execute arbitrary code",
    ),
    ScanPattern(
        name="shell_true",
        pattern=re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
        severity="high",
        description="subprocess with shell=True enables shell injection",
    ),
    ScanPattern(
        name="yaml_load_unsafe",
        pattern=re.compile(r"yaml\.load\s*\([^)]*\)(?!.*Loader\s*=)"),
        severity="medium",
        description="yaml.load without safe Loader can execute arbitrary code",
    ),
    ScanPattern(
        name="marshal_usage",
        pattern=re.compile(r"\bimport\s+marshal\b|\bfrom\s+marshal\s+import\b"),
        severity="medium",
        description="marshal can execute arbitrary code on deserialization",
    ),
]

SQL_INJECTION_PATTERNS = [
    ScanPattern(
        name="string_format_query",
        pattern=re.compile(
            r"""(?:execute|cursor\.execute)\s*\(\s*f['\"]|"""
            r"""(?:execute|cursor\.execute)\s*\(\s*['\"].*%s|"""
            r"""(?:execute|cursor\.execute)\s*\(\s*['\"].*\{""",
        ),
        severity="high",
        description="SQL query built with string formatting (potential injection)",
    ),
    ScanPattern(
        name="string_concat_query",
        pattern=re.compile(
            r"""(?:execute|cursor\.execute)\s*\(\s*['\"].*\+\s*""",
        ),
        severity="high",
        description="SQL query built with string concatenation (potential injection)",
    ),
]

DEBUG_PATTERNS = [
    ScanPattern(
        name="debug_print",
        pattern=re.compile(r"\bprint\s*\(\s*['\"]DEBUG"),
        severity="low",
        description="Debug print statement left in source",
    ),
    ScanPattern(
        name="pdb_breakpoint",
        pattern=re.compile(r"\bimport\s+pdb\b|\bpdb\.set_trace\(\)|\bbreakpoint\(\)"),
        severity="medium",
        description="Debugger breakpoint left in source",
    ),
    ScanPattern(
        name="hardcoded_localhost",
        pattern=re.compile(r"localhost:\d{4,5}"),
        severity="info",
        description="Hardcoded localhost URL (check if intentional)",
    ),
]


# ── Scanner ───────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    file: str
    line: int
    pattern_name: str
    severity: str
    description: str
    snippet: str


@dataclass
class AuditReport:
    timestamp: str
    scan_path: str
    files_scanned: int = 0
    lines_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache",
    "venv", ".venv", "env", ".env", "dist", "build", ".eggs",
}
SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".docx", ".pdf",
}


def _should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    if path.suffix in SKIP_EXTENSIONS:
        return True
    return False


def scan_file(file_path: Path, all_patterns: list[ScanPattern]) -> list[Finding]:
    """Scan a single file for security issues."""
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    lines = content.splitlines()
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        for sp in all_patterns:
            if sp.pattern.search(line):
                findings.append(Finding(
                    file=str(file_path),
                    line=line_num,
                    pattern_name=sp.name,
                    severity=sp.severity,
                    description=sp.description,
                    snippet=stripped[:120],
                ))
    return findings


def run_audit(scan_path: str, include_info: bool = True) -> AuditReport:
    """Run the full security audit."""
    root = Path(scan_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Scan path does not exist: {scan_path}")

    all_patterns = SECRET_PATTERNS + INSECURE_IMPORT_PATTERNS + SQL_INJECTION_PATTERNS + DEBUG_PATTERNS
    if not include_info:
        all_patterns = [p for p in all_patterns if p.severity != "info"]

    report = AuditReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        scan_path=str(root),
    )

    files = []
    if root.is_file():
        files = [root]
    else:
        files = sorted(f for f in root.rglob("*") if f.is_file() and not _should_skip(f.relative_to(root)))

    report.files_scanned = len(files)

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            report.lines_scanned += content.count("\n") + 1
        except Exception:
            pass
        findings = scan_file(f, all_patterns)
        report.findings.extend(findings)

    # Summary
    severity_counts: dict[str, int] = {}
    for f in report.findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
    report.summary = severity_counts

    return report


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_report(report: AuditReport) -> None:
    """Pretty-print the audit report."""
    print(f"\n{'='*60}")
    print(f"  🛡️  Security Audit Report")
    print(f"{'='*60}")
    print(f"  Scan Path:   {report.scan_path}")
    print(f"  Files:       {report.files_scanned}")
    print(f"  Lines:       {report.lines_scanned}")
    print(f"  Findings:    {len(report.findings)}")
    print(f"  Timestamp:   {report.timestamp}")
    print(f"{'='*60}\n")

    if not report.findings:
        print("  ✅ No security issues found!\n")
        return

    # Group by severity
    severity_order = ["critical", "high", "medium", "low", "info"]
    severity_colors = {
        "critical": "\033[91m",
        "high": "\033[91m",
        "medium": "\033[93m",
        "low": "\033[94m",
        "info": "\033[90m",
    }
    end_color = "\033[0m"

    for severity in severity_order:
        findings = [f for f in report.findings if f.severity == severity]
        if not findings:
            continue

        color = severity_colors.get(severity, "")
        print(f"  {color}━━━ {severity.upper()} ({len(findings)}) ━━━{end_color}")

        for finding in findings:
            print(f"    {color}[{finding.pattern_name}]{end_color} {finding.file}:{finding.line}")
            print(f"      {finding.description}")
            print(f"      > {finding.snippet}")
            print()

    # Summary
    print(f"  {'━'*56}")
    print(f"  Summary:")
    for sev in severity_order:
        count = report.summary.get(sev, 0)
        if count:
            color = severity_colors.get(sev, "")
            print(f"    {color}{sev.upper()}: {count}{end_color}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="security_audit",
        description="Security audit scanner for Quant Nanggroe AI",
    )
    parser.add_argument(
        "--path", default=str(Path(__file__).resolve().parent.parent),
        help="Path to scan (default: project root)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--no-info", action="store_true", help="Exclude info-level findings")
    args = parser.parse_args()

    report = run_audit(args.path, include_info=not args.no_info)

    if args.json:
        output = {
            "timestamp": report.timestamp,
            "scan_path": report.scan_path,
            "files_scanned": report.files_scanned,
            "lines_scanned": report.lines_scanned,
            "findings_count": len(report.findings),
            "summary": report.summary,
            "findings": [asdict(f) for f in report.findings],
        }
        print(json.dumps(output, indent=2))
    else:
        _print_report(report)

    # Exit code: 1 if critical/high findings
    if report.summary.get("critical", 0) > 0 or report.summary.get("high", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
