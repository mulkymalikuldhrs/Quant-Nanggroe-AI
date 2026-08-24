#!/usr/bin/env python3
"""security_audit.py — Phase 4.3: scan for hardcoded secrets, dangerous functions, file permission issues."""
import argparse
import datetime
import json
import re
import stat
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = str(REPO_ROOT / "credentials.md")
EXCLUDE_PATTERNS = [
    ".git/", "__pycache__/", ".venv/", "node_modules/",
    "data/backup-orphans/", CREDENTIALS_PATH, "scripts/security_audit.py",
]

SECRET_PATTERNS = [
    ("API Key", r"(api[_-]?key|apikey|api_secret|secret_key)\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}", "HIGH"),
    ("JWT Secret", r"jwt[_-]?secret|JWT_SECRET", "MEDIUM"),
    ("Private Key", r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "CRITICAL"),
    ("Password", r"password\s*[:=]\s*[\"'][^\"']{6,}", "HIGH"),
    ("Token", r"token\s*[:=]\s*[\"'][A-Za-z0-9_\-\.]{20,}", "HIGH"),
    ("Seed Phrase", r"(seed[_-]?(phrase|words?)|mnemonic)\s*[:=]\s*[\"'][a-z\s]{20,}", "CRITICAL"),
    ("Wallet Address", r"0x[a-fA-F0-9]{40}", "MEDIUM"),
]

DANGEROUS_PATTERNS = [
    ("eval()", r"\beval\s*\(", "CRITICAL"),
    ("exec()", r"\bexec\s*\(", "CRITICAL"),
    ("compile()", r"\bcompile\s*\(", "CRITICAL"),
    ("os.system()", r"os\.system\s*\(", "CRITICAL"),
    ("subprocess shell=True", r"subprocess\.(Popen|call)\s*\([^)]*shell\s*=\s*True", "CRITICAL"),
    ("pickle.loads", r"pickle\.loads?\s*\(", "CRITICAL"),
    ("__import__()", r"__import__\s*\(", "CRITICAL"),
    ("yaml.load()", r"yaml\.load\s*\(", "MEDIUM"),
    ("SQL injection", r"(f[\"']|\.format\().*SELECT\s|execute\s*\(\s*f[\"']", "MEDIUM"),
]


def should_exclude(path):
    """Check if a path matches any exclude pattern."""
    path_str = str(path)
    for pat in EXCLUDE_PATTERNS:
        if pat in path_str:
            return True
    return False


def gather_files(quick=False):
    """Collect files to scan: quant_nanggroe/, scripts/, tests/, root .py/.sh."""
    files = []
    scan_dirs = []

    if not quick:
        qn = REPO_ROOT / "quant_nanggroe"
        if qn.is_dir():
            scan_dirs.append(qn)

    scripts_dir = REPO_ROOT / "scripts"
    if scripts_dir.is_dir():
        scan_dirs.append(scripts_dir)

    tests_dir = REPO_ROOT / "tests"
    if tests_dir.is_dir():
        scan_dirs.append(tests_dir)

    for d in scan_dirs:
        for f in sorted(d.rglob("*")):
            if f.is_file() and f.suffix in (".py", ".sh"):
                if not should_exclude(f):
                    files.append(f)

    for f in sorted(REPO_ROOT.glob("*.py")):
        if not should_exclude(f):
            files.append(f)
    for f in sorted(REPO_ROOT.glob("*.sh")):
        if not should_exclude(f):
            files.append(f)

    return files


def scan_file(filepath):
    """Scan a single file for all patterns. Returns list of findings."""
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings

    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        for label, pattern, severity in SECRET_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                findings.append({
                    "file": str(filepath),
                    "line": i,
                    "severity": severity,
                    "type": label,
                    "detail": stripped[:120],
                })

        for label, pattern, severity in DANGEROUS_PATTERNS:
            if re.search(pattern, stripped):
                findings.append({
                    "file": str(filepath),
                    "line": i,
                    "severity": severity,
                    "type": label,
                    "detail": stripped[:120],
                })

    return findings


def check_permissions(filepath):
    """Check for world-writable files."""
    findings = []
    try:
        mode = filepath.stat().st_mode
        if mode & stat.S_IWOTH:
            rel = filepath.relative_to(REPO_ROOT)
            findings.append({
                "file": str(filepath),
                "line": 0,
                "severity": "LOW",
                "type": "World-writable file",
                "detail": f"{rel} is world-writable (mode {oct(mode & 0o777)})",
            })
    except Exception:
        pass
    return findings


def compute_score(findings):
    """Calculate security score from findings."""
    score = 100
    severity_deductions = {"CRITICAL": 20, "HIGH": 10, "MEDIUM": 5, "LOW": 2}
    for f in findings:
        deduction = severity_deductions.get(f["severity"], 0)
        score = max(5, score - deduction)
    score = min(100, score)
    return score


def score_band(score):
    if score >= 90:
        return "SAFE"
    elif score >= 70:
        return "MODERATE"
    elif score >= 50:
        return "CONCERNING"
    return "CRITICAL"


def fmt_severity(s):
    return s


def print_report(findings, files_scanned, score, band, output_path=None):
    """Print human-readable report to stdout."""
    date_str = datetime.date.today().isoformat()
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

    grouped = {}
    for f in findings:
        sev = f["severity"]
        if sev not in grouped:
            grouped[sev] = []
        grouped[sev].append(f)

    header = "Security Audit"
    print(f"  {header}")
    print(f"  {'═' * len(header)}")
    print(f"  Date: {date_str}")
    print(f"  Files scanned: {files_scanned}")
    print(f"  Findings: {len(findings)}")
    print()

    for sev in sorted(grouped.keys(), key=lambda s: severity_order.get(s, 99)):
        items = grouped[sev]
        print(f"  {sev} ({len(items)}):")
        for item in items:
            short_file = item["file"]
            line = item["line"]
            detail = item["detail"]
            if line:
                print(f"    {short_file}:{line}  {detail}")
            else:
                print(f"    {short_file}  {detail}")
        print()

    print(f"  Score: {score}/100 ({band})")


def save_json(findings, files_scanned, score, band, output_path):
    """Save JSON report to file."""
    report = {
        "date": datetime.date.today().isoformat(),
        "files_scanned": files_scanned,
        "findings_count": len(findings),
        "score": score,
        "band": band,
        "findings": findings,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Quant Nanggroe AI Security Audit")
    parser.add_argument("--quick", action="store_true", help="Skip quant_nanggroe/, scan scripts/ and root only")
    parser.add_argument("--json", type=str, default=None, help="Output JSON report to custom path")
    parser.add_argument("--threshold", type=int, default=None, help="Exit code 1 if score below this threshold")
    args = parser.parse_args()

    files = gather_files(quick=args.quick)
    all_findings = []
    perm_findings = []

    for f in files:
        all_findings.extend(scan_file(f))

    for f in files:
        perm_findings.extend(check_permissions(f))

    all_findings.extend(perm_findings)
    all_findings.sort(key=lambda x: (x["severity"], x["file"], x["line"]))

    score = compute_score(all_findings)
    band = score_band(score)

    print_report(all_findings, len(files), score, band)

    json_path = args.json or str(REPO_ROOT / "paper_state" / "security_audit.json")
    save_json(all_findings, len(files), score, band, json_path)
    print(f"\n  JSON report saved to: {json_path}")

    if args.threshold is not None and score < args.threshold:
        print(f"\n  Score {score} is below threshold {args.threshold} — exiting with code 1")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
