#!/usr/bin/env python3
"""security_scan.py — Comprehensive security scanner for Quant-Nanggroe-AI.
Scans the codebase for hardcoded secrets, placeholder keys, print() in prod,
.env tracking issues, insecure crypto, and hardcoded passwords.

Output: JSON report with severity/file/line/finding/recommendation.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["quant_nanggroe", "scripts", "tests"]
EXCLUDE_PATTERNS = [
    r"\.git/", r"__pycache__/", r"\.venv/", r"venv/", r"node_modules/",
    r"/archive/", r"/skills/", r"/ai_multicolony/", r"/docs/", r"/data/",
    r"/\.github/", r"/deploy/", r"/dashboard/", r"/htmlcov/",
    r"scripts/security_scan\.py$",
]

SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"


def should_exclude(path: Path) -> bool:
    s = str(path)
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, s):
            return True
    return False


def get_python_files(root: Path) -> list[Path]:
    files = []
    for scan_dir in SCAN_DIRS:
        d = root / scan_dir
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file() or f.suffix not in (".py", ".sh", ".yml", ".yaml", ".env", ".env.example"):
                continue
            if should_exclude(f):
                continue
            files.append(f)
    # Also scan root-level .py/.sh files
    for f in sorted(root.glob("*.py")):
        files.append(f)
    for f in sorted(root.glob("*.sh")):
        files.append(f)
    # Check .env and .gitignore at root
    for f in sorted(root.glob(".env*")):
        files.append(f)
    return files


def is_production(path: Path) -> bool:
    s = str(path)
    return "/tests/" not in s and "/test_" not in s and s.endswith(".py")


def is_test_file(path: Path) -> bool:
    s = str(path)
    return "/tests/" in s or "/test_" in s


def scan_hardcoded_secrets(lines: list[str], filepath: Path) -> list[dict]:
    findings = []
    patterns = [
        (r"""api[_-]?key\s*=\s*["']([A-Za-z0-9_\-]{16,})["']""", "Hardcoded API key", SEVERITY_HIGH),
        (r"""secret[_-]?key\s*=\s*["']([A-Za-z0-9_\-]{16,})["']""", "Hardcoded secret key", SEVERITY_HIGH),
        (r"""api[_-]?secret\s*=\s*["']([A-Za-z0-9_\-]{16,})["']""", "Hardcoded API secret", SEVERITY_HIGH),
        (r"""token\s*=\s*["']([A-Za-z0-9_\-\.]{20,})["']""", "Hardcoded token", SEVERITY_HIGH),
        (r"""sk-[A-Za-z0-9]{20,}""", "Hardcoded OpenAI-style secret key", SEVERITY_HIGH),
    ]
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Skip test files and docstrings for this check
        for pattern, label, severity in patterns:
            m = re.search(pattern, stripped, re.IGNORECASE)
            if m:
                val = m.group(1) if m.groups() else m.group(0)
                if re.search(r"(YOUR_|your-|placeholder|xxxxx|sk-your|CHANGE_ME|test-key|test_key|my-key|bearer-token|poly-api-key)", val, re.IGNORECASE):
                    continue  # skip placeholders — handled separately
                if is_production(filepath):
                    findings.append({
                        "severity": severity,
                        "file": str(filepath),
                        "line": i,
                        "finding": f"{label} found in production code",
                        "recommendation": "Move to environment variable via KeyVault.get_secret()",
                    })
    return findings


def scan_placeholder_keys(lines: list[str], filepath: Path) -> list[dict]:
    findings = []
    placeholder_patterns = [
        r"""["']YOUR_[A-Z_]+_HERE["']""",
        r"""["']your-[a-z-]+-here["']""",
        r"""["']sk-your[a-z0-9]*["']""",
        r"""["']placeholder["']""",
        r"""["']xxxxx["']""",
        r"""["']CHANGE_ME["']""",
    ]
    combined = "|".join(f"(?:{p})" for p in placeholder_patterns)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.search(combined, stripped, re.IGNORECASE):
            findings.append({
                "severity": SEVERITY_HIGH,
                "file": str(filepath),
                "line": i,
                "finding": "Placeholder API key/secret in test or config file",
                "recommendation": 'Replace with "<placeholder>" or os.environ.get("VAR", "")',
            })
    # Also detect non-placeholder but clearly test-only keys like api_key="test", api_key="test-key", etc.
    if is_test_file(filepath):
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            m = re.search(r"""api_key\s*=\s*["']([^"']+)["']""", stripped)
            if m:
                val = m.group(1)
                if val not in ("<placeholder>", "") and not re.search(r"\{\w+\}", val):
                    findings.append({
                        "severity": SEVERITY_MEDIUM,
                        "file": str(filepath),
                        "line": i,
                        "finding": f"Possibly hardcoded api_key in test (value='{val[:30]}')",
                        "recommendation": 'Replace with "<placeholder>"',
                    })
    return findings


def scan_print_statements(lines: list[str], filepath: Path) -> list[dict]:
    findings = []
    if not is_production(filepath):
        return findings
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.search(r"\bprint\s*\(", stripped) and not stripped.startswith("#"):
            findings.append({
                "severity": SEVERITY_MEDIUM,
                "file": str(filepath),
                "line": i,
                "finding": "print() statement in production code",
                "recommendation": "Replace with logger.info() or logger.warning()",
            })
    return findings


def scan_dotenv_tracking(root: Path) -> list[dict]:
    findings = []
    gitignore = root / ".gitignore"
    env_file = root / ".env"
    if env_file.exists():
        if not gitignore.exists():
            findings.append({
                "severity": SEVERITY_HIGH,
                "file": str(env_file),
                "line": 0,
                "finding": ".env file exists but no .gitignore found",
                "recommendation": "Create .gitignore and add .env to it",
            })
        else:
            gitignore_content = gitignore.read_text(encoding="utf-8", errors="replace")
            if ".env" not in gitignore_content:
                findings.append({
                    "severity": SEVERITY_HIGH,
                    "file": str(env_file),
                    "line": 0,
                    "finding": ".env file exists but is NOT listed in .gitignore",
                    "recommendation": "Add '.env' to .gitignore",
                })
    return findings


def scan_insecure_crypto(lines: list[str], filepath: Path) -> list[dict]:
    findings = []
    if not is_production(filepath):
        return findings
    insecure = [
        (r"\bmd5\b", "MD5 hash", SEVERITY_MEDIUM),
        (r"\bsha1\b", "SHA-1 hash", SEVERITY_MEDIUM),
        (r"\bDES\b(?![A-Z_])", "DES encryption", SEVERITY_HIGH),
        (r"\bRC4\b", "RC4 encryption", SEVERITY_HIGH),
    ]
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern, label, severity in insecure:
            if re.search(pattern, stripped, re.IGNORECASE):
                findings.append({
                    "severity": severity,
                    "file": str(filepath),
                    "line": i,
                    "finding": f"Insecure cryptographic function: {label}",
                    "recommendation": f"Replace {label} with SHA-256 or better (hashlib.sha256)",
                })
    return findings


def scan_hardcoded_passwords(lines: list[str], filepath: Path) -> list[dict]:
    findings = []
    if not is_production(filepath):
        return findings
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"""password\s*=\s*["']([^"']{2,})["']""", stripped)
        if m:
            val = m.group(1)
            if val not in ("", "<placeholder>") and not re.search(r"\{\w+\}", val):
                findings.append({
                    "severity": SEVERITY_HIGH,
                    "file": str(filepath),
                    "line": i,
                    "finding": "Hardcoded password detected",
                    "recommendation": "Move to environment variable via KeyVault.get_secret()",
                })
    return findings


def scan_env_for_real_secrets(root: Path) -> list[dict]:
    """Check .env for real-looking secrets that might be committed."""
    findings = []
    env_path = root / ".env"
    if not env_path.exists():
        return findings
    try:
        content = env_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings
    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        if val and not re.search(r"^['\"]?$", val) and val not in ("true", "false", "True", "False"):
            # If value looks like a real key/token (not empty, not a boolean)
            if len(val) >= 8 and not re.search(r"(YOUR_|your-|placeholder|^$|CHANGE_ME)", val):
                if not re.search(r"^https?://", val) and not re.search(r"^\d+$", val):
                    findings.append({
                        "severity": SEVERITY_LOW,
                        "file": str(env_path),
                        "line": i,
                        "finding": f"Potential real secret in .env file ({key})",
                        "recommendation": "Ensure .env is in .gitignore (already tracked: verify git status)",
                    })
    return findings


def scan_one_file(filepath: Path) -> list[dict]:
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    lines = content.split("\n")
    findings = []
    findings.extend(scan_hardcoded_secrets(lines, filepath))
    findings.extend(scan_placeholder_keys(lines, filepath))
    findings.extend(scan_print_statements(lines, filepath))
    findings.extend(scan_insecure_crypto(lines, filepath))
    findings.extend(scan_hardcoded_passwords(lines, filepath))
    return findings


def format_report(findings: list[dict], files_scanned: int):
    return json.dumps({
        "report_title": "Quant-Nanggroe-AI Security Scan",
        "scan_date": datetime.utcnow().isoformat(),
        "files_scanned": files_scanned,
        "total_findings": len(findings),
        "severity_summary": {
            sev: len([f for f in findings if f["severity"] == sev])
            for sev in [SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW]
        },
        "findings": sorted(findings, key=lambda x: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x["severity"]], x["file"], x["line"])),
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Quant-Nanggroe-AI Security Scan")
    parser.add_argument("--json", type=str, default=None, help="Output path for JSON report")
    parser.add_argument("--exit-code", action="store_true", help="Exit with code 1 if any HIGH findings")
    args = parser.parse_args()

    files = get_python_files(REPO_ROOT)
    all_findings = []
    for f in files:
        all_findings.extend(scan_one_file(f))
    all_findings.extend(scan_dotenv_tracking(REPO_ROOT))
    all_findings.extend(scan_env_for_real_secrets(REPO_ROOT))

    report_json = format_report(all_findings, len(files))

    out_path = args.json or str(REPO_ROOT / "paper_state" / "security_scan_report.json")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(report_json + "\n")

    parsed = json.loads(report_json)
    print(report_json)

    if args.exit_code:
        high_count = parsed["severity_summary"].get(SEVERITY_HIGH, 0)
        if high_count > 0:
            print(f"\n❌ {high_count} HIGH findings — exiting with code 1", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
