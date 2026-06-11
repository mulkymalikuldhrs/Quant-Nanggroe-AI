"""PermissionEngine – L0-L4 autonomy levels with dynamic escalation,
approval gate flow, time-bounded elevation, and audit trail.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Autonomy levels ──────────────────────────────────────────────

AUTONOMY_LEVELS = {
    0: "L0_READONLY",
    1: "L1_SAFE_OPS",
    2: "L2_MODERATE",
    3: "L3_SENSITIVE",
    4: "L4_DESTRUCTIVE",
}

AUTONOMY_DESCRIPTIONS = {
    0: "Read-only / informational access",
    1: "Safe operations with no side effects (read, search, navigate)",
    2: "Moderate side-effects (write files, shell exec, docker create)",
    3: "Sensitive operations (credential access, docker destroy, git push)",
    4: "Destructive / irreversible operations (credential rotate, rm -rf)",
}


# ── Pydantic models ──────────────────────────────────────────────

class PermissionCheck(BaseModel):
    """Result of a permission check."""
    model_config = ConfigDict(frozen=False)

    tool_name: str
    autonomy_level: int = 0
    agent_id: str = ""
    colony_id: str = ""
    granted: bool = False
    reason: str = ""
    required_level: int = 0
    current_level: int = 0
    escalation_available: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ApprovalRequest(BaseModel):
    """A request for temporary autonomy elevation."""
    model_config = ConfigDict(frozen=False)

    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    colony_id: str = ""
    current_level: int = 0
    requested_level: int = 1
    justification: str = ""
    tool_name: str = ""
    task_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    duration_hours: int = 1
    status: str = "pending"  # pending | approved | denied | expired
    approved_by: str = ""
    audit_entries: List[Dict[str, Any]] = Field(default_factory=list)


class EscalationGrant(BaseModel):
    """An active (approved) autonomy elevation."""
    model_config = ConfigDict(frozen=False)

    grant_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    original_level: int = 0
    elevated_level: int = 1
    expires_at: str = ""
    reason: str = ""
    approved_by: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AuditRecord(BaseModel):
    """Audit trail record."""
    model_config = ConfigDict(frozen=False)

    record_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    action: str = ""  # check | escalation_request | escalation_grant | escalation_deny
    agent_id: str = ""
    tool_name: str = ""
    autonomy_level: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)


# ── Default tool permissions ─────────────────────────────────────

TOOL_PERMISSIONS: Dict[str, int] = {
    # Shell
    "shell.execute": 2,
    # File
    "file.operations": 1,
    "file.read": 0,
    "file.write": 2,
    "file.delete": 2,
    # Browser
    "browser.control": 1,
    "browser.navigate": 0,
    "browser.screenshot": 0,
    "browser.click": 1,
    "browser.type": 1,
    "browser.extract": 0,
    "browser.execute_js": 2,
    # Search
    "search.web": 0,
    # Code
    "code.operations": 1,
    "code.run": 2,
    # Docker
    "sandbox.docker": 2,
    "sandbox.docker.create": 1,
    "sandbox.docker.exec": 2,
    "sandbox.docker.destroy": 3,
    # Voice
    "voice.io": 1,
    "voice.stt.transcribe": 1,
    "voice.tts.synthesize": 1,
    # Memory
    "memory.manage": 0,
    "memory.store": 1,
    "memory.delete": 2,
    "memory.compact": 2,
    # Channel
    "comm.channel": 2,
    # VCS
    "vcs.github": 1,
    "vcs.git.commit": 2,
    "vcs.git.push": 3,
    "vcs.pr.merge": 3,
    # Security
    "sec.scan.vulnerability": 3,
    "sec.credential.read": 3,
    "sec.credential.write": 3,
    "sec.credential.rotate": 4,
}


# ── Permission Engine ────────────────────────────────────────────

class PermissionEngine:
    """L0-L4 permission engine for MCP tool access control.

    Features
    --------
    * Per-tool required autonomy levels (configurable)
    * Dynamic escalation with approval gate flow
    * Time-bounded elevation (auto-expiring grants)
    * Full audit trail
    """

    def __init__(
        self,
        default_level: int = 1,
        auto_approve_safe: bool = True,
        max_escalation_duration_hours: int = 4,
    ) -> None:
        self._tool_permissions: Dict[str, int] = dict(TOOL_PERMISSIONS)
        self._default_level = default_level
        self._auto_approve_safe = auto_approve_safe
        self._max_escalation_duration = max_escalation_duration_hours

        # Active state
        self._escalation_requests: Dict[str, ApprovalRequest] = {}
        self._active_grants: Dict[str, EscalationGrant] = {}  # grant_id -> Grant
        self._agent_grants: Dict[str, List[str]] = {}  # agent_id -> [grant_ids]
        self._audit_trail: List[AuditRecord] = []

    # ── Permission checking ──────────────────────────────────────

    def check_permission(
        self,
        tool_name: str,
        autonomy_level: int,
        agent_id: str = "",
        colony_id: str = "",
    ) -> PermissionCheck:
        """Check if an agent has permission to use a tool.

        Takes into account any active escalation grants for the agent.
        """
        # Get effective level (may be elevated by a grant)
        effective_level = self._effective_level(agent_id, autonomy_level)

        required = self._tool_permissions.get(tool_name, self._default_level)
        granted = effective_level >= required

        check = PermissionCheck(
            tool_name=tool_name,
            autonomy_level=effective_level,
            agent_id=agent_id,
            colony_id=colony_id,
            granted=granted,
            required_level=required,
            current_level=autonomy_level,
            escalation_available=not granted and effective_level < 4,
        )

        if not granted:
            check.reason = (
                f"Requires level {required} ({AUTONOMY_LEVELS.get(required, '')}), "
                f"agent has effective level {effective_level} "
                f"(base: {autonomy_level})"
            )

        # Audit
        self._audit(AuditRecord(
            action="check",
            agent_id=agent_id,
            tool_name=tool_name,
            autonomy_level=effective_level,
            details={
                "granted": granted,
                "required": required,
                "base_level": autonomy_level,
                "effective_level": effective_level,
            },
        ))

        return check

    def _effective_level(self, agent_id: str, base_level: int) -> int:
        """Compute effective autonomy level considering active grants."""
        if not agent_id:
            return base_level

        max_elevated = base_level
        grant_ids = self._agent_grants.get(agent_id, [])
        now = datetime.utcnow()

        for gid in grant_ids:
            grant = self._active_grants.get(gid)
            if not grant:
                continue
            # Check expiry
            try:
                expires = datetime.fromisoformat(grant.expires_at)
                if now > expires:
                    # Expired – clean up
                    self._active_grants.pop(gid, None)
                    continue
            except (ValueError, TypeError):
                continue
            max_elevated = max(max_elevated, grant.elevated_level)

        return max_elevated

    # ── Tool registration ────────────────────────────────────────

    def register_tool(self, tool_name: str, required_level: int) -> None:
        """Register or update the required level for a tool."""
        self._tool_permissions[tool_name] = required_level

    def unregister_tool(self, tool_name: str) -> None:
        """Remove a tool from the permission table."""
        self._tool_permissions.pop(tool_name, None)

    def get_tool_level(self, tool_name: str) -> int:
        """Get the required autonomy level for a tool."""
        return self._tool_permissions.get(tool_name, self._default_level)

    def list_tools(
        self,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None,
    ) -> Dict[str, int]:
        """List tools with their required levels, optionally filtered."""
        tools = dict(self._tool_permissions)
        if min_level is not None:
            tools = {k: v for k, v in tools.items() if v >= min_level}
        if max_level is not None:
            tools = {k: v for k, v in tools.items() if v <= max_level}
        return tools

    # ── Escalation flow ──────────────────────────────────────────

    def request_escalation(
        self,
        agent_id: str,
        current_level: int,
        requested_level: int,
        justification: str = "",
        tool_name: str = "",
        colony_id: str = "",
        duration_hours: int = 1,
        task_context: Optional[Dict] = None,
    ) -> ApprovalRequest:
        """Request temporary autonomy escalation.

        If ``auto_approve_safe`` is True and the escalation is from
        L0→L1 or stays within safe levels, the request is auto-approved.
        """
        # Cap duration
        duration_hours = min(duration_hours, self._max_escalation_duration)

        # Cannot request above L4
        requested_level = min(requested_level, 4)

        request = ApprovalRequest(
            agent_id=agent_id,
            colony_id=colony_id,
            current_level=current_level,
            requested_level=requested_level,
            justification=justification,
            tool_name=tool_name,
            task_context=task_context or {},
            duration_hours=duration_hours,
            expires_at=(datetime.utcnow() + timedelta(hours=duration_hours)).isoformat(),
        )

        self._escalation_requests[request.request_id] = request

        # Auto-approve safe escalations
        if self._auto_approve_safe and current_level <= 1 and requested_level <= 1:
            self.grant_escalation(request.request_id, approved_by="auto")
        elif self._auto_approve_safe and requested_level <= current_level + 1 and requested_level <= 2:
            # Allow one-step escalation up to L2
            self.grant_escalation(request.request_id, approved_by="auto")

        self._audit(AuditRecord(
            action="escalation_request",
            agent_id=agent_id,
            tool_name=tool_name,
            autonomy_level=requested_level,
            details={
                "request_id": request.request_id,
                "current_level": current_level,
                "requested_level": requested_level,
                "justification": justification,
            },
        ))

        return request

    def grant_escalation(self, request_id: str, approved_by: str = "admin") -> bool:
        """Approve an escalation request, creating an active grant."""
        request = self._escalation_requests.get(request_id)
        if not request:
            return False

        if request.status != "pending":
            return False

        # Create grant
        grant = EscalationGrant(
            agent_id=request.agent_id,
            original_level=request.current_level,
            elevated_level=request.requested_level,
            expires_at=request.expires_at or (datetime.utcnow() + timedelta(hours=request.duration_hours)).isoformat(),
            reason=request.justification,
            approved_by=approved_by,
        )

        # Update request
        request.status = "approved"
        request.approved_by = approved_by

        # Store grant
        self._active_grants[grant.grant_id] = grant
        if request.agent_id not in self._agent_grants:
            self._agent_grants[request.agent_id] = []
        self._agent_grants[request.agent_id].append(grant.grant_id)

        self._audit(AuditRecord(
            action="escalation_grant",
            agent_id=request.agent_id,
            tool_name=request.tool_name,
            autonomy_level=request.requested_level,
            details={
                "grant_id": grant.grant_id,
                "original_level": request.current_level,
                "elevated_level": request.requested_level,
                "approved_by": approved_by,
            },
        ))

        logger.info(
            "Escalation granted: %s L%d->L%d (grant=%s, by=%s)",
            request.agent_id, request.current_level, request.requested_level,
            grant.grant_id, approved_by,
        )
        return True

    def deny_escalation(self, request_id: str, reason: str = "") -> bool:
        """Deny an escalation request."""
        request = self._escalation_requests.get(request_id)
        if not request:
            return False

        request.status = "denied"
        request.audit_entries.append({
            "action": "denied",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })

        self._audit(AuditRecord(
            action="escalation_deny",
            agent_id=request.agent_id,
            tool_name=request.tool_name,
            autonomy_level=request.requested_level,
            details={"reason": reason},
        ))

        return True

    def revoke_grant(self, grant_id: str, reason: str = "") -> bool:
        """Revoke an active escalation grant."""
        grant = self._active_grants.get(grant_id)
        if not grant:
            return False

        # Remove from agent grants
        agent_grants = self._agent_grants.get(grant.agent_id, [])
        self._agent_grants[grant.agent_id] = [g for g in agent_grants if g != grant_id]

        del self._active_grants[grant_id]

        self._audit(AuditRecord(
            action="grant_revoked",
            agent_id=grant.agent_id,
            autonomy_level=grant.elevated_level,
            details={"grant_id": grant_id, "reason": reason},
        ))

        return True

    # ── Cleanup expired grants ───────────────────────────────────

    def cleanup_expired(self) -> int:
        """Remove expired grants. Returns count of grants removed."""
        now = datetime.utcnow()
        expired_ids = []
        for gid, grant in self._active_grants.items():
            try:
                expires = datetime.fromisoformat(grant.expires_at)
                if now > expires:
                    expired_ids.append(gid)
            except (ValueError, TypeError):
                pass

        for gid in expired_ids:
            grant = self._active_grants.pop(gid)
            agent_grants = self._agent_grants.get(grant.agent_id, [])
            self._agent_grants[grant.agent_id] = [g for g in agent_grants if g != gid]

        return len(expired_ids)

    # ── Query helpers ────────────────────────────────────────────

    def get_pending_requests(self, agent_id: Optional[str] = None) -> List[ApprovalRequest]:
        """Get pending escalation requests."""
        requests = [
            r for r in self._escalation_requests.values()
            if r.status == "pending"
        ]
        if agent_id:
            requests = [r for r in requests if r.agent_id == agent_id]
        return requests

    def get_active_grants(self, agent_id: Optional[str] = None) -> List[EscalationGrant]:
        """Get active escalation grants."""
        grants = list(self._active_grants.values())
        if agent_id:
            grants = [g for g in grants if g.agent_id == agent_id]
        return grants

    def get_escalation_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._escalation_requests.get(request_id)

    # ── Audit ────────────────────────────────────────────────────

    def _audit(self, record: AuditRecord) -> None:
        self._audit_trail.append(record)

    def get_audit_trail(
        self,
        agent_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query the audit trail."""
        records = self._audit_trail
        if agent_id:
            records = [r for r in records if r.agent_id == agent_id]
        if action:
            records = [r for r in records if r.action == action]
        return [r.model_dump() for r in records[-limit:]]

    # ── Stats ────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_tools": len(self._tool_permissions),
            "pending_requests": sum(1 for r in self._escalation_requests.values() if r.status == "pending"),
            "active_grants": len(self._active_grants),
            "audit_entries": len(self._audit_trail),
            "default_level": self._default_level,
            "auto_approve_safe": self._auto_approve_safe,
        }
