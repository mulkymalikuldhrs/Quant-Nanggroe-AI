"""Security analyzer – code and dependency security analysis.

Features:
* Vulnerability pattern detection (regex-based rules)
* Dependency vulnerability checking (CVE database integration point)
* Secret / credential leak detection
* Security score calculation
* Report generation (JSON and Markdown)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..types import AuditLevel

logger = logging.getLogger(__name__)


class SecurityFinding:
    """A single security finding from analysis."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        severity: str,
        description: str,
        location: str = "",
        line: int = 0,
        confidence: float = 1.0,
        remediation: str = "",
        cwe_id: str = "",
    ):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity  # critical | high | medium | low | info
        self.description = description
        self.location = location
        self.line = line
        self.confidence = confidence
        self.remediation = remediation
        self.cwe_id = cwe_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity,
            "description": self.description,
            "location": self.location,
            "line": self.line,
            "confidence": self.confidence,
            "remediation": self.remediation,
            "cwe_id": self.cwe_id,
        }


# Severity weight map for score calculation
SEVERITY_WEIGHTS: Dict[str, float] = {
    "critical": 10.0,
    "high": 7.0,
    "medium": 4.0,
    "low": 1.0,
    "info": 0.0,
}


class SecurityAnalyzer:
    """Analyzes code and dependencies for security issues.

    The analyzer uses a rule-based approach with extensible pattern
    matching.  Built-in rules cover common vulnerability classes:
    SQL injection, XSS, hardcoded secrets, insecure transport,
    weak cryptography, and more.

    Usage::

        analyzer = SecurityAnalyzer()
        findings = analyzer.analyze_code(source_code)
        score = analyzer.calculate_score(findings)
        report = analyzer.generate_report(findings, score, format="markdown")
    """

    def __init__(self):
        self._rules: List[Dict[str, Any]] = []
        self._dependency_vulns: Dict[str, List[Dict[str, Any]]] = {}
        self._load_default_rules()

    # ── Default rules ──────────────────────────────────────────────────────

    def _load_default_rules(self) -> None:
        """Load the built-in vulnerability detection rules."""
        self._rules = [
            {
                "id": "SEC001",
                "name": "SQL Injection",
                "severity": "high",
                "pattern": r"(SELECT|INSERT|UPDATE|DELETE|DROP)\s+.*FROM|\+\s*['\"].*SELECT|OR\s+1\s*=\s*1|UNION\s+SELECT",
                "description": "Potential SQL injection: unsanitized input in SQL query",
                "remediation": "Use parameterized queries or an ORM",
                "cwe_id": "CWE-89",
            },
            {
                "id": "SEC002",
                "name": "Hardcoded Secret",
                "severity": "critical",
                "pattern": r"(password|passwd|secret|api_key|apikey|access_token|private_key|auth_token)\s*[:=]\s*['\"][^'\"]{4,}['\"]",
                "description": "Hardcoded secret or credential detected",
                "remediation": "Move secrets to environment variables or a secrets manager",
                "cwe_id": "CWE-798",
            },
            {
                "id": "SEC003",
                "name": "Insecure HTTP",
                "severity": "medium",
                "pattern": r"http://[^\s\"\']+",
                "description": "Insecure HTTP URL detected (should use HTTPS)",
                "remediation": "Replace http:// with https://",
                "cwe_id": "CWE-319",
            },
            {
                "id": "SEC004",
                "name": "Debug Mode Enabled",
                "severity": "medium",
                "pattern": r"DEBUG\s*=\s*True|debug\s*[:=]\s*true|FLASK_DEBUG\s*=\s*1",
                "description": "Debug mode is enabled in configuration",
                "remediation": "Disable debug mode in production",
                "cwe_id": "CWE-489",
            },
            {
                "id": "SEC005",
                "name": "Weak Cryptography",
                "severity": "high",
                "pattern": r"\bmd5\b|\bsha1\b|\bDES\b|\bRC4\b|\bRC2\b",
                "description": "Weak cryptographic algorithm detected",
                "remediation": "Use SHA-256 or stronger for hashing, AES for encryption",
                "cwe_id": "CWE-327",
            },
            {
                "id": "SEC006",
                "name": "Command Injection",
                "severity": "critical",
                "pattern": r"os\.system\s*\(|subprocess\.call\s*\(.*shell\s*=\s*True|eval\s*\(|exec\s*\(",
                "description": "Potential command injection via shell execution",
                "remediation": "Use subprocess without shell=True, avoid eval/exec",
                "cwe_id": "CWE-78",
            },
            {
                "id": "SEC007",
                "name": "Cross-Site Scripting (XSS)",
                "severity": "high",
                "pattern": r"innerHTML\s*=|document\.write\s*\(|\.html\s*\(",
                "description": "Potential XSS: unsanitized output to DOM",
                "remediation": "Use textContent or proper escaping",
                "cwe_id": "CWE-79",
            },
            {
                "id": "SEC008",
                "name": "Path Traversal",
                "severity": "high",
                "pattern": r"\.\./|\.\.\\|os\.path\.join\s*\(.*\+",
                "description": "Potential path traversal vulnerability",
                "remediation": "Validate and sanitize file paths, use allowlists",
                "cwe_id": "CWE-22",
            },
            {
                "id": "SEC009",
                "name": "Insecure Deserialization",
                "severity": "high",
                "pattern": r"pickle\.loads?\s*\(|yaml\.load\s*\((?!.*Loader)|marshal\.loads?\s*\(",
                "description": "Insecure deserialization detected",
                "remediation": "Use json.loads or yaml.safe_load",
                "cwe_id": "CWE-502",
            },
            {
                "id": "SEC010",
                "name": "Insecure Random",
                "severity": "low",
                "pattern": r"\brandom\.\b(?!SystemRandom|seed)",
                "description": "Use of non-cryptographic random number generator",
                "remediation": "Use secrets module for security-sensitive randomness",
                "cwe_id": "CWE-338",
            },
        ]

    # ── Code analysis ──────────────────────────────────────────────────────

    def analyze_code(self, code: str, filename: str = "<string>") -> List[SecurityFinding]:
        """Analyze source code for security vulnerabilities.

        Parameters
        ----------
        code : str
            The source code to analyze.
        filename : str
            The filename (used in finding locations).

        Returns
        -------
        list[SecurityFinding]
        """
        findings: List[SecurityFinding] = []

        for rule in self._rules:
            pattern = rule["pattern"]
            try:
                for match in re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE):
                    line_num = code[:match.start()].count("\n") + 1
                    finding = SecurityFinding(
                        rule_id=rule["id"],
                        name=rule["name"],
                        severity=rule["severity"],
                        description=rule.get("description", f"Found pattern: {rule['name']}"),
                        location=filename,
                        line=line_num,
                        remediation=rule.get("remediation", ""),
                        cwe_id=rule.get("cwe_id", ""),
                    )
                    findings.append(finding)
            except re.error:
                logger.warning("Invalid regex in rule %s: %s", rule["id"], pattern)

        return findings

    # ── Dependency analysis ────────────────────────────────────────────────

    def analyze_dependencies(self, dependencies: Dict[str, str]) -> List[SecurityFinding]:
        """Analyze a dependency map for known vulnerabilities.

        Parameters
        ----------
        dependencies : dict[str, str]
            Mapping of package name → version string.

        Returns
        -------
        list[SecurityFinding]
        """
        findings: List[SecurityFinding] = []

        for pkg, version in dependencies.items():
            vulns = self._dependency_vulns.get(pkg, [])
            for vuln in vulns:
                affected = vuln.get("affected_versions", "")
                if self._version_matches(version, affected):
                    findings.append(SecurityFinding(
                        rule_id=vuln.get("id", "DEP-UNKNOWN"),
                        name=f"Vulnerable Dependency: {pkg}",
                        severity=vuln.get("severity", "medium"),
                        description=vuln.get("description", f"{pkg} {version} has a known vulnerability"),
                        location=f"{pkg}=={version}",
                        remediation=vuln.get("remediation", f"Upgrade {pkg}"),
                        cwe_id=vuln.get("cwe_id", ""),
                    ))

        return findings

    def add_dependency_vulnerability(
        self,
        package: str,
        vuln_id: str,
        severity: str,
        description: str,
        affected_versions: str,
        remediation: str = "",
        cwe_id: str = "",
    ) -> None:
        """Register a known vulnerability for a dependency."""
        if package not in self._dependency_vulns:
            self._dependency_vulns[package] = []
        self._dependency_vulns[package].append({
            "id": vuln_id,
            "severity": severity,
            "description": description,
            "affected_versions": affected_versions,
            "remediation": remediation,
            "cwe_id": cwe_id,
        })

    @staticmethod
    def _version_matches(version: str, spec: str) -> bool:
        """Simple version range check (supports <, <=, >=, >)."""
        if not spec:
            return True
        try:
            from packaging.version import Version
            v = Version(version)
            for part in spec.split(","):
                part = part.strip()
                if part.startswith("<="):
                    if v > Version(part[2:]):
                        return False
                elif part.startswith("<"):
                    if v >= Version(part[1:]):
                        return False
                elif part.startswith(">="):
                    if v < Version(part[2:]):
                        return False
                elif part.startswith(">"):
                    if v <= Version(part[1:]):
                        return False
            return True
        except Exception:
            return True  # if we can't parse, assume affected

    # ── Secret / credential leak detection ─────────────────────────────────

    def detect_secrets(self, code: str, filename: str = "<string>") -> List[SecurityFinding]:
        """Detect leaked secrets and credentials in code.

        Uses entropy analysis and pattern matching to find:
        * Hardcoded passwords, API keys, tokens
        * AWS/Azure/GCP credentials
        * Private keys
        * Connection strings
        """
        findings: List[SecurityFinding] = []

        # Pattern-based detection
        secret_patterns = [
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "critical"),
            (r"aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]", "AWS Secret Access Key", "critical"),
            (r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "Private Key", "critical"),
            (r"(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]", "Hardcoded Password", "critical"),
            (r"(?:api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9\-_]{20,}['\"]", "API Key", "high"),
            (r"(?:token|auth[_-]?token|bearer)\s*[:=]\s*['\"][A-Za-z0-9\-_.]{20,}['\"]", "Authentication Token", "high"),
            (r"mongodb(?:\+srv)?://[^\s'\"]+", "MongoDB Connection String", "high"),
            (r"postgres(?:ql)?://[^\s'\"]+", "PostgreSQL Connection String", "high"),
            (r"mysql://[^\s'\"]+", "MySQL Connection String", "high"),
            (r"redis://[^\s'\"]+", "Redis Connection String", "medium"),
        ]

        for pattern, name, severity in secret_patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                line_num = code[:match.start()].count("\n") + 1
                findings.append(SecurityFinding(
                    rule_id="SECRET",
                    name=name,
                    severity=severity,
                    description=f"Detected {name.lower()} in source code",
                    location=filename,
                    line=line_num,
                    confidence=0.9,
                    remediation="Move to environment variable or secrets manager",
                    cwe_id="CWE-798",
                ))

        # Entropy-based detection for high-entropy strings
        findings.extend(self._entropy_scan(code, filename))

        return findings

    def _entropy_scan(self, code: str, filename: str, threshold: float = 4.5) -> List[SecurityFinding]:
        """Scan for high-entropy strings that may be secrets."""
        import math
        findings: List[SecurityFinding] = []

        # Find quoted strings
        string_pattern = r'["\']([A-Za-z0-9+/=_\-]{20,})["\']'
        for match in re.finditer(string_pattern, code):
            candidate = match.group(1)
            # Calculate Shannon entropy
            entropy = self._shannon_entropy(candidate)
            if entropy >= threshold:
                line_num = code[:match.start()].count("\n") + 1
                findings.append(SecurityFinding(
                    rule_id="SEC-ENTROPY",
                    name="High-Entropy String",
                    severity="medium",
                    description=f"High-entropy string detected (entropy={entropy:.2f}) - possible secret",
                    location=filename,
                    line=line_num,
                    confidence=0.6,
                    remediation="Verify this is not a leaked secret; use env vars for actual secrets",
                ))

        return findings

    @staticmethod
    def _shannon_entropy(data: str) -> float:
        """Calculate Shannon entropy of a string."""
        import math
        if not data:
            return 0.0
        freq: Dict[str, int] = {}
        for c in data:
            freq[c] = freq.get(c, 0) + 1
        length = len(data)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    # ── Score calculation ──────────────────────────────────────────────────

    def calculate_score(self, findings: List[SecurityFinding]) -> float:
        """Calculate a security score from 0.0 (worst) to 1.0 (best).

        The score is derived from the count and severity of findings.
        No findings = 1.0.  Each finding reduces the score proportionally
        to its severity weight.
        """
        if not findings:
            return 1.0

        total_weight = sum(SEVERITY_WEIGHTS.get(f.severity, 1.0) for f in findings)
        # Normalize: assume 50 points of weight drops score to 0
        score = max(0.0, 1.0 - (total_weight / 50.0))
        return round(score, 3)

    # ── Report generation ──────────────────────────────────────────────────

    def generate_report(
        self,
        findings: List[SecurityFinding],
        score: Optional[float] = None,
        format: str = "json",
    ) -> str:
        """Generate a security analysis report.

        Parameters
        ----------
        findings : list[SecurityFinding]
            The findings to include.
        score : float, optional
            The security score (will be calculated if not provided).
        format : str
            "json" or "markdown".

        Returns
        -------
        str
            The formatted report.
        """
        if score is None:
            score = self.calculate_score(findings)

        if format == "markdown":
            return self._report_markdown(findings, score)
        else:
            return self._report_json(findings, score)

    def _report_json(self, findings: List[SecurityFinding], score: float) -> str:
        """Generate a JSON report."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "security_score": score,
            "total_findings": len(findings),
            "findings_by_severity": self._count_by_severity(findings),
            "findings": [f.to_dict() for f in findings],
        }
        return json.dumps(report, indent=2)

    def _report_markdown(self, findings: List[SecurityFinding], score: float) -> str:
        """Generate a Markdown report."""
        lines = [
            "# Security Analysis Report",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            f"**Security Score:** {score:.3f}",
            f"**Total Findings:** {len(findings)}",
            "",
        ]

        # Summary table
        by_severity = self._count_by_severity(findings)
        lines.append("## Summary by Severity")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev in ["critical", "high", "medium", "low", "info"]:
            lines.append(f"| {sev.title()} | {by_severity.get(sev, 0)} |")
        lines.append("")

        # Detailed findings
        lines.append("## Findings")
        lines.append("")
        for i, f in enumerate(findings, 1):
            lines.append(f"### {i}. [{f.severity.upper()}] {f.name}")
            lines.append(f"- **Rule:** {f.rule_id}")
            lines.append(f"- **Location:** {f.location}:{f.line}")
            lines.append(f"- **Description:** {f.description}")
            if f.remediation:
                lines.append(f"- **Remediation:** {f.remediation}")
            if f.cwe_id:
                lines.append(f"- **CWE:** {f.cwe_id}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _count_by_severity(findings: List[SecurityFinding]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    # ── Rule management ────────────────────────────────────────────────────

    def add_rule(
        self,
        rule_id: str,
        name: str,
        severity: str,
        pattern: str,
        description: str = "",
        remediation: str = "",
        cwe_id: str = "",
    ) -> None:
        """Add a custom vulnerability detection rule."""
        # Validate the regex
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        self._rules.append({
            "id": rule_id,
            "name": name,
            "severity": severity,
            "pattern": pattern,
            "description": description or f"Custom rule: {name}",
            "remediation": remediation,
            "cwe_id": cwe_id,
        })

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by its ID."""
        for i, rule in enumerate(self._rules):
            if rule["id"] == rule_id:
                self._rules.pop(i)
                return True
        return False

    def list_rules(self) -> List[Dict[str, Any]]:
        """List all active rules (without patterns for brevity)."""
        return [
            {"id": r["id"], "name": r["name"], "severity": r["severity"], "cwe_id": r.get("cwe_id", "")}
            for r in self._rules
        ]

    @property
    def rule_count(self) -> int:
        return len(self._rules)
