"""Security agent - from OpenHands security + OpenFang patterns.

Specializes in security analysis, vulnerability scanning, dependency
audit, incident response, and compliance enforcement.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.agents.security.prompts import (
    SECURITY_SYSTEM_PROMPT,
    SECURITY_SCAN_PROMPT,
    SECURITY_AUDIT_PROMPT,
    SECURITY_DEPENDENCY_AUDIT_PROMPT,
    SECURITY_INCIDENT_RESPONSE_PROMPT,
    SECURITY_CODE_REVIEW_PROMPT,
)

logger = get_logger(__name__)


class SecurityAgent(BaseAgent):
    """Security agent for threat detection and compliance.

    From OpenHands security patterns and OpenFang colony security.
    Analyzes code, configurations, and actions for security issues,
    performs dependency audits, and handles incident response.

    State-specific behavior:
    - IDLE: Ready for security analysis tasks
    - RUNNING: Actively scanning, auditing, or analyzing
    - THINKING: Analyzing security findings or planning response
    - WAITING: Waiting for scan results or external data
    - PAUSED: Security analysis paused
    - ERROR: Analysis error, attempts recovery with simplified scan
    """

    # Track security findings
    _findings: list[dict[str, Any]]
    _audit_log: list[dict[str, Any]]
    _incidents: list[dict[str, Any]]
    _scan_count: int = 0

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.SECURITY,
                name="security-agent",
                description="Security analysis, threat detection, and compliance enforcement",
                tools=["shell", "file", "code", "memory"],
                system_prompt=SECURITY_SYSTEM_PROMPT,
                temperature=0.0,  # Deterministic for security analysis
                capabilities=AgentCapabilities(
                    security_analysis=True,
                    code_execution=True,
                    file_operations=True,
                    shell_execution=True,
                    memory_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = SECURITY_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["shell", "file", "code", "memory"]

        super().__init__(config=config, **kwargs)
        self._findings = []
        self._audit_log = []
        self._incidents = []
        self._scan_count = 0

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names SecurityAgent requires.

        Returns:
            Tools needed for security operations.
        """
        return ["shell", "file", "code", "memory"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Security agent."""
        return self.config.system_prompt or SECURITY_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "security_agent_running",
            agent_id=self.agent_id,
            scans=self._scan_count,
            findings=len(self._findings),
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state."""
        logger.warning(
            "security_agent_error",
            agent_id=self.agent_id,
            error_count=self.error_count,
        )
        # Store error in findings for tracking
        self._findings.append({
            "type": "agent_error",
            "severity": "INFO",
            "message": f"Security agent entered error state (error_count={self.error_count})",
        })

    # ------------------------------------------------------------------
    # Core security methods
    # ------------------------------------------------------------------

    async def scan(self, target: str, scan_type: str = "full") -> str:
        """Perform a security scan.

        Args:
            target: The target to scan (code, config, URL, etc.).
            scan_type: Type of scan (full, quick, focused, dependency).

        Returns:
            Security scan findings.
        """
        self._scan_count += 1

        if scan_type == "dependency":
            return await self.audit_dependencies(target)

        prompt = SECURITY_SCAN_PROMPT.format(target=target, scan_type=scan_type)
        result = await self.run(prompt)

        # Parse and store findings
        findings = self._parse_findings(result)
        self._findings.extend(findings)

        # Store scan result in memory
        memory = self._get_memory_manager()
        memory.add_entry(
            agent_id=self.agent_id,
            content=f"Security scan ({scan_type}) of {target[:100]}: {len(findings)} findings",
            memory_type=MemoryType.LONG_TERM,
            importance=0.8 if any(f.get("severity") in ("CRITICAL", "HIGH") for f in findings) else 0.5,
            source="security_scan",
        )

        return result

    async def audit_action(self, action: str, agent_id: str, context: str = "") -> str:
        """Audit an agent action for security compliance.

        Args:
            action: The action to audit.
            agent_id: The agent performing the action.
            context: Additional context.

        Returns:
            Audit result with ALLOW/DENY recommendation.
        """
        prompt = SECURITY_AUDIT_PROMPT.format(
            action=action,
            agent_id=agent_id,
            context=context,
        )
        result = await self.run(prompt)

        # Record audit entry
        is_allowed = "ALLOW" in result.upper()
        self._audit_log.append({
            "action": action[:200],
            "agent_id": agent_id,
            "context": context[:200],
            "allowed": is_allowed,
            "result_preview": result[:200],
        })

        return result

    async def audit_dependencies(self, dependencies: str) -> str:
        """Audit dependencies for security vulnerabilities.

        Args:
            dependencies: The dependency list (e.g., requirements.txt content).

        Returns:
            Dependency audit findings.
        """
        prompt = SECURITY_DEPENDENCY_AUDIT_PROMPT.format(dependencies=dependencies)
        result = await self.run(prompt)

        findings = self._parse_findings(result)
        self._findings.extend(findings)

        return result

    async def review_code_security(self, code: str, language: str = "python") -> str:
        """Review code for security vulnerabilities.

        Args:
            code: The code to review.
            language: Programming language.

        Returns:
            Security review findings.
        """
        prompt = SECURITY_CODE_REVIEW_PROMPT.format(
            code=code,
            language=language,
        )
        result = await self.run(prompt)

        findings = self._parse_findings(result)
        self._findings.extend(findings)

        return result

    async def respond_to_incident(
        self,
        incident: str,
        severity: str = "HIGH",
        systems: str = "unknown",
    ) -> str:
        """Respond to a security incident.

        Args:
            incident: Description of the security incident.
            severity: Incident severity (CRITICAL, HIGH, MEDIUM, LOW).
            systems: Affected systems.

        Returns:
            Incident response plan and actions.
        """
        prompt = SECURITY_INCIDENT_RESPONSE_PROMPT.format(
            incident=incident,
            severity=severity,
            systems=systems,
        )
        result = await self.run(prompt)

        # Record incident
        self._incidents.append({
            "incident": incident[:200],
            "severity": severity,
            "systems": systems,
            "response_preview": result[:200],
        })

        # Store in memory as high-importance
        memory = self._get_memory_manager()
        memory.add_entry(
            agent_id=self.agent_id,
            content=f"Security incident ({severity}): {incident[:100]}",
            memory_type=MemoryType.LONG_TERM,
            importance=1.0 if severity in ("CRITICAL", "HIGH") else 0.7,
            source="incident_response",
        )

        return result

    # ------------------------------------------------------------------
    # Finding analysis
    # ------------------------------------------------------------------

    def _parse_findings(self, scan_result: str) -> list[dict[str, Any]]:
        """Parse security findings from a scan result.

        Args:
            scan_result: The raw scan result text.

        Returns:
            List of finding dictionaries.
        """
        findings: list[dict[str, Any]] = []
        severity_keywords = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

        for line in scan_result.split("\n"):
            line = line.strip()
            for severity in severity_keywords:
                if severity in line.upper():
                    findings.append({
                        "severity": severity,
                        "description": line[:300],
                        "source": "scan",
                    })
                    break

        return findings

    def get_findings(self, severity: Optional[str] = None) -> list[dict[str, Any]]:
        """Get security findings, optionally filtered by severity.

        Args:
            severity: Optional severity level filter.

        Returns:
            List of finding dictionaries.
        """
        if severity is None:
            return list(self._findings)
        return [f for f in self._findings if f.get("severity") == severity.upper()]

    def get_critical_findings(self) -> list[dict[str, Any]]:
        """Get only CRITICAL severity findings.

        Returns:
            List of critical findings.
        """
        return self.get_findings("CRITICAL")

    def get_high_findings(self) -> list[dict[str, Any]]:
        """Get only HIGH severity findings.

        Returns:
            List of high severity findings.
        """
        return self.get_findings("HIGH")

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log of all actions reviewed.

        Returns:
            List of audit log entries.
        """
        return list(self._audit_log)

    def get_incidents(self) -> list[dict[str, Any]]:
        """Get the list of security incidents handled.

        Returns:
            List of incident entries.
        """
        return list(self._incidents)

    def clear_findings(self) -> None:
        """Clear all stored security findings."""
        self._findings.clear()
        self._audit_log.clear()
        self._incidents.clear()
        self._scan_count = 0
