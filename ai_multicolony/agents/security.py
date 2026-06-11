"""Security agent – vulnerability scanning, dependency auditing, and secret detection.

Performs security analysis including vulnerability scanning, dependency
auditing, secret/credential detection, and generates comprehensive
security reports.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from ..types import AgentSpec, AgentType, Task, TaskResult

logger = logging.getLogger(__name__)

# ── Vulnerability patterns ──

SECRET_PATTERNS: Dict[str, Dict[str, str]] = {
    "aws_access_key": {"pattern": "AKIA[0-9A-Z]{16}", "severity": "critical"},
    "aws_secret_key": {"pattern": "[A-Za-z0-9/+=]{40}", "severity": "critical"},
    "github_token": {"pattern": "ghp_[A-Za-z0-9]{36}", "severity": "critical"},
    "private_key": {"pattern": "-----BEGIN (RSA |EC )?PRIVATE KEY-----", "severity": "critical"},
    "api_key_generic": {"pattern": "(?i)(api[_-]?key|apikey)\\s*[:=]\\s*['\"][^'\"]{16,}", "severity": "high"},
    "password_in_code": {"pattern": "(?i)(password|passwd|pwd)\\s*[:=]\\s*['\"][^'\"]{6,}", "severity": "high"},
    "jwt_secret": {"pattern": "(?i)(jwt[_-]?secret)\\s*[:=]\\s*['\"][^'\"]{8,}", "severity": "high"},
    "database_url": {"pattern": "(?i)(postgres|mysql|mongodb)://[^\\s'\"]+", "severity": "medium"},
}

VULNERABILITY_CATEGORIES: Dict[str, List[str]] = {
    "injection": ["sql_injection", "command_injection", "xss", "ldap_injection"],
    "auth": ["broken_auth", "session_fixation", "credential_stuffing"],
    "data_exposure": ["sensitive_data_exposure", "info_leak", "misconfigured_cors"],
    "misconfig": ["security_misconfig", "default_credentials", "open_storage"],
    "deps": ["known_vulnerability", "outdated_dependency", "transitive_vulnerability"],
}


class SecurityAgent(BaseAgent):
    """Security analysis agent for vulnerability scanning and auditing.

    Features
    --------
    * **Vulnerability scanning** – detect OWASP Top 10 patterns.
    * **Dependency auditing** – check for known CVEs in dependencies.
    * **Secret detection** – find hardcoded credentials and API keys.
    * **Security reporting** – generate comprehensive audit reports.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.SECURITY, autonomy_level=3)
        if spec.agent_type != AgentType.SECURITY:
            spec.agent_type = AgentType.SECURITY
        super().__init__(spec=spec, **kwargs)
        self._scan_history: List[Dict] = []
        self._findings: List[Dict[str, Any]] = []
        self._audit_reports: Dict[str, Dict[str, Any]] = {}

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Execute security task based on ``payload.action``."""
        action = task.payload.get("action", "scan")
        if action == "scan":
            return await self._vulnerability_scan(task)
        elif action == "dependency_audit":
            return await self._dependency_audit(task)
        elif action == "secret_scan":
            return await self._secret_scan(task)
        elif action == "audit_report":
            return await self._audit_report(task)
        elif action == "full_audit":
            return await self._full_audit(task)
        elif action == "get_findings":
            return self._get_findings()
        else:
            return {"action": action, "result": f"Unknown security action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle A2A messages for security operations."""
        msg_type = message.get("message_type", "")
        if msg_type == "security_scan_request":
            target = message.get("payload", {}).get("target", "")
            return {"scan_initiated": True, "target": target}
        elif msg_type == "findings_query":
            severity = message.get("payload", {}).get("severity")
            return {"findings": self._filter_findings(severity)}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare security capabilities."""
        return [
            "vulnerability_scanning", "dependency_audit", "secret_detection",
            "security_reporting", "owasp_top10", "cve_checking",
        ]

    # ── Vulnerability scanning ──

    async def _vulnerability_scan(self, task: Task) -> Dict[str, Any]:
        """Scan a target for vulnerabilities.

        Payload fields:
        * ``target`` – code, URL, or path to scan.
        * ``scan_type`` – ``"full"`` or ``"quick"``.
        * ``categories`` – list of vulnerability categories to check.
        """
        target = task.payload.get("target", "unknown")
        scan_type = task.payload.get("scan_type", "quick")
        categories = task.payload.get("categories", list(VULNERABILITY_CATEGORIES.keys()))

        vulnerabilities: List[Dict[str, Any]] = []
        risk_level = "low"

        # Scan for patterns in target content
        target_str = str(target)
        for category, vuln_types in VULNERABILITY_CATEGORIES.items():
            if category not in categories:
                continue
            # Simple pattern-based detection
            for vuln_type in vuln_types:
                if self._check_vulnerability_pattern(vuln_type, target_str):
                    vulnerabilities.append({
                        "type": vuln_type,
                        "category": category,
                        "severity": self._severity_for_vuln(vuln_type),
                        "description": f"Potential {vuln_type.replace('_', ' ')} detected",
                        "location": "target",
                    })

        # Determine overall risk
        if any(v["severity"] == "critical" for v in vulnerabilities):
            risk_level = "critical"
        elif any(v["severity"] == "high" for v in vulnerabilities):
            risk_level = "high"
        elif any(v["severity"] == "medium" for v in vulnerabilities):
            risk_level = "medium"

        result = {
            "action": "scan",
            "target": target,
            "scan_type": scan_type,
            "vulnerabilities": vulnerabilities,
            "vulnerability_count": len(vulnerabilities),
            "risk_level": risk_level,
            "categories_checked": categories,
        }

        self._scan_history.append(result)
        self._findings.extend(vulnerabilities)

        return result

    def _check_vulnerability_pattern(self, vuln_type: str, target: str) -> bool:
        """Check for a specific vulnerability pattern in target text."""
        patterns: Dict[str, List[str]] = {
            "sql_injection": ["SELECT * FROM", "DROP TABLE", "' OR '1'='1", "UNION SELECT"],
            "command_injection": ["os.system(", "subprocess.call(", "eval(", "exec("],
            "xss": ["<script>", "onerror=", "onload=", "javascript:"],
            "broken_auth": ["password = ", "default_password", "admin:admin"],
            "sensitive_data_exposure": ["credit_card", "ssn", "social_security"],
            "security_misconfig": ["debug=True", "CORS: *", "Allow-Origin: *"],
            "default_credentials": ["admin:admin", "root:root", "default:default"],
        }
        for pattern in patterns.get(vuln_type, []):
            if pattern.lower() in target.lower():
                return True
        return False

    def _severity_for_vuln(self, vuln_type: str) -> str:
        """Return default severity for a vulnerability type."""
        critical_types = {"sql_injection", "command_injection", "broken_auth"}
        high_types = {"xss", "sensitive_data_exposure", "default_credentials"}
        if vuln_type in critical_types:
            return "critical"
        if vuln_type in high_types:
            return "high"
        return "medium"

    # ── Dependency auditing ──

    async def _dependency_audit(self, task: Task) -> Dict[str, Any]:
        """Audit project dependencies for known vulnerabilities.

        Payload fields:
        * ``dependencies`` – list of dependency dicts with name/version.
        * ``lockfile`` – contents of a lock file.
        """
        dependencies = task.payload.get("dependencies", [])
        lockfile = task.payload.get("lockfile", "")

        vulnerable_deps: List[Dict[str, Any]] = []
        total_deps = len(dependencies)

        for dep in dependencies:
            name = dep.get("name", "")
            version = dep.get("version", "")
            # Simulated CVE check
            cves = self._check_cves(name, version)
            if cves:
                vulnerable_deps.append({
                    "name": name,
                    "version": version,
                    "vulnerabilities": cves,
                    "severity": max(c.get("severity", "low") for c in cves),
                })

        risk_level = "low"
        if any(d["severity"] == "critical" for d in vulnerable_deps):
            risk_level = "critical"
        elif any(d["severity"] == "high" for d in vulnerable_deps):
            risk_level = "high"
        elif vulnerable_deps:
            risk_level = "medium"

        result = {
            "action": "dependency_audit",
            "total_deps": total_deps,
            "vulnerable_deps": vulnerable_deps,
            "vulnerability_count": len(vulnerable_deps),
            "risk_level": risk_level,
        }

        self._scan_history.append(result)
        return result

    def _check_cves(self, name: str, version: str) -> List[Dict[str, Any]]:
        """Check for known CVEs in a dependency (simulated).

        In production this would query an NVD / OSV / Snyk API.
        """
        # Known vulnerable versions (simulated)
        known_vulns: Dict[str, Dict[str, List[Dict]]] = {
            "requests": {
                "2.25.0": [{"cve": "CVE-2023-32681", "severity": "medium", "description": "Unintended leak of Proxy-Authorization header"}],
            },
            "django": {
                "3.2.0": [{"cve": "CVE-2023-46695", "severity": "high", "description": "DoS via large username"}],
            },
            "log4j": {
                "2.14.1": [{"cve": "CVE-2021-44228", "severity": "critical", "description": "Remote code execution"}],
            },
        }
        return known_vulns.get(name, {}).get(version, [])

    # ── Secret detection ──

    async def _secret_scan(self, task: Task) -> Dict[str, Any]:
        """Scan for hardcoded secrets and credentials.

        Payload fields:
        * ``content`` – text or code content to scan.
        * ``path`` – file path or scope label.
        """
        content = task.payload.get("content", "")
        path = task.payload.get("path", "unknown")

        secrets_found: List[Dict[str, Any]] = []
        locations: List[Dict[str, Any]] = []

        for secret_name, config in SECRET_PATTERNS.items():
            import re
            try:
                matches = list(re.finditer(config["pattern"], content))
                for match in matches:
                    secrets_found.append({
                        "type": secret_name,
                        "severity": config["severity"],
                        "line": content[:match.start()].count("\n") + 1,
                        "masked": match.group()[:4] + "****",
                    })
                    locations.append({
                        "type": secret_name,
                        "line": content[:match.start()].count("\n") + 1,
                    })
            except re.error:
                # Invalid regex pattern – skip
                continue

        severity = "none"
        if any(s["severity"] == "critical" for s in secrets_found):
            severity = "critical"
        elif any(s["severity"] == "high" for s in secrets_found):
            severity = "high"
        elif secrets_found:
            severity = "medium"

        result = {
            "action": "secret_scan",
            "path": path,
            "secrets_found": len(secrets_found),
            "details": secrets_found,
            "locations": locations,
            "severity": severity,
        }

        self._scan_history.append(result)
        self._findings.extend(secrets_found)
        return result

    # ── Security reporting ──

    async def _audit_report(self, task: Task) -> Dict[str, Any]:
        """Generate a comprehensive security audit report.

        Aggregates all past scans and findings into a structured report.
        """
        report_id = f"rpt-{uuid.uuid4().hex[:8]}"
        total_findings = len(self._findings)
        findings_by_severity: Dict[str, int] = {}
        for f in self._findings:
            sev = f.get("severity", "low")
            findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1

        # Determine compliance
        critical_count = findings_by_severity.get("critical", 0)
        high_count = findings_by_severity.get("high", 0)
        compliance = "pass" if critical_count == 0 and high_count == 0 else "fail"

        report = {
            "report_id": report_id,
            "action": "audit_report",
            "total_findings": total_findings,
            "findings_by_severity": findings_by_severity,
            "scans_performed": len(self._scan_history),
            "compliance": compliance,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "recommendations": self._generate_recommendations(findings_by_severity),
        }

        self._audit_reports[report_id] = report
        return report

    async def _full_audit(self, task: Task) -> Dict[str, Any]:
        """Run a full audit: vulnerability scan + dependency audit + secret scan."""
        target = task.payload.get("target", "unknown")
        dependencies = task.payload.get("dependencies", [])
        content = task.payload.get("content", "")

        vuln_result = await self._vulnerability_scan(task)
        dep_result = await self._dependency_audit(task)
        secret_result = await self._secret_scan(task)

        # Generate combined report
        report = await self._audit_report(task)
        report["vulnerability_scan"] = vuln_result
        report["dependency_audit"] = dep_result
        report["secret_scan"] = secret_result
        return report

    # ── Helpers ──

    def _get_findings(self) -> Dict[str, Any]:
        """Return all accumulated findings."""
        return {
            "total": len(self._findings),
            "findings": self._findings,
            "scans_performed": len(self._scan_history),
        }

    def _filter_findings(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filter findings by severity level."""
        if severity is None:
            return self._findings
        return [f for f in self._findings if f.get("severity") == severity]

    def _generate_recommendations(self, findings_by_severity: Dict[str, int]) -> List[str]:
        """Generate remediation recommendations based on findings."""
        recommendations: List[str] = []
        if findings_by_severity.get("critical", 0) > 0:
            recommendations.append("CRITICAL: Address all critical findings immediately")
        if findings_by_severity.get("high", 0) > 0:
            recommendations.append("HIGH: Remediate high-severity findings within 24 hours")
        if findings_by_severity.get("medium", 0) > 0:
            recommendations.append("MEDIUM: Plan remediation for medium-severity findings")
        if findings_by_severity.get("low", 0) > 0:
            recommendations.append("LOW: Review low-severity findings at next maintenance window")
        if not recommendations:
            recommendations.append("No security findings – maintain current security posture")
        return recommendations
