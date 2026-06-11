"""Permission engine – RBAC, ABAC, dynamic escalation, and approval gates.

Features:
* 5 autonomy levels (L0–L4)
* RBAC role definitions
* ABAC attribute checking
* Dynamic escalation (time-bounded, auto-approve for L0→L1)
* Approval gate flow
* Audit integration
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from ..types import (
    AutonomyLevel,
    PermissionCheck,
    PermissionDef,
    ApprovalRequest,
    EscalationRecord,
    RoleDef,
    AuditEventType,
)
from ..config import get_settings

logger = logging.getLogger(__name__)


# ── Default RBAC roles ────────────────────────────────────────────────────────

DEFAULT_ROLES: Dict[str, RoleDef] = {
    "admin": RoleDef(
        name="admin",
        autonomy_level=AutonomyLevel.L4_DESTRUCTIVE,
        allowed_tools=["*"],
        allowed_actions=["*"],
        description="Full access to all tools and actions",
    ),
    "operator": RoleDef(
        name="operator",
        autonomy_level=AutonomyLevel.L2_MODERATE,
        allowed_tools=[
            "shell.execute",
            "file.read",
            "file.write",
            "browser.navigate",
            "browser.extract",
            "search.web",
            "search.code",
            "memory.manage",
            "code.analyze",
            "code.test",
        ],
        allowed_actions=["execute", "write", "read", "deploy"],
        description="Standard operator with write and deploy access",
    ),
    "agent": RoleDef(
        name="agent",
        autonomy_level=AutonomyLevel.L1_SAFE_OPS,
        allowed_tools=[
            "search.web",
            "search.code",
            "memory.manage",
            "code.read",
            "code.analyze",
            "file.read",
        ],
        allowed_actions=["read", "search", "analyze"],
        description="Standard agent with safe read-only operations",
    ),
    "viewer": RoleDef(
        name="viewer",
        autonomy_level=AutonomyLevel.L0_READONLY,
        allowed_tools=["search.web", "memory.manage"],
        allowed_actions=["read"],
        description="Read-only access",
        is_default=True,
    ),
}


# ── Default permission definitions ────────────────────────────────────────────

DEFAULT_PERMISSIONS: Dict[str, PermissionDef] = {
    "shell.execute": PermissionDef(
        tool_name="shell.execute",
        required_level=AutonomyLevel.L3_SENSITIVE,
        description="Execute shell commands",
        requires_approval=True,
        approval_timeout_ms=300_000,
        auto_approve_from=AutonomyLevel.L4_DESTRUCTIVE,
    ),
    "file.write": PermissionDef(
        tool_name="file.write",
        required_level=AutonomyLevel.L2_MODERATE,
        description="Write files to disk",
        requires_approval=False,
    ),
    "file.read": PermissionDef(
        tool_name="file.read",
        required_level=AutonomyLevel.L0_READONLY,
        description="Read files from disk",
        requires_approval=False,
    ),
    "file.delete": PermissionDef(
        tool_name="file.delete",
        required_level=AutonomyLevel.L4_DESTRUCTIVE,
        description="Delete files",
        requires_approval=True,
    ),
    "browser.navigate": PermissionDef(
        tool_name="browser.navigate",
        required_level=AutonomyLevel.L1_SAFE_OPS,
        description="Navigate browser to URL",
        requires_approval=False,
    ),
    "browser.extract": PermissionDef(
        tool_name="browser.extract",
        required_level=AutonomyLevel.L1_SAFE_OPS,
        description="Extract data from web pages",
        requires_approval=False,
    ),
    "search.web": PermissionDef(
        tool_name="search.web",
        required_level=AutonomyLevel.L0_READONLY,
        description="Search the web",
        requires_approval=False,
    ),
    "code.execute": PermissionDef(
        tool_name="code.execute",
        required_level=AutonomyLevel.L3_SENSITIVE,
        description="Execute code in sandbox",
        requires_approval=False,
    ),
    "memory.manage": PermissionDef(
        tool_name="memory.manage",
        required_level=AutonomyLevel.L0_READONLY,
        description="Manage agent memory",
        requires_approval=False,
    ),
    "docker.run": PermissionDef(
        tool_name="docker.run",
        required_level=AutonomyLevel.L3_SENSITIVE,
        description="Run Docker containers",
        requires_approval=True,
        approval_timeout_ms=600_000,
        auto_approve_from=AutonomyLevel.L4_DESTRUCTIVE,
    ),
    "deploy.production": PermissionDef(
        tool_name="deploy.production",
        required_level=AutonomyLevel.L4_DESTRUCTIVE,
        description="Deploy to production",
        requires_approval=True,
        approval_timeout_ms=600_000,
    ),
}


class PermissionEngine:
    """Security permission engine with RBAC, ABAC, escalation, and approval gates.

    The engine supports:
    * **RBAC** – assign roles to agents; each role defines allowed tools and max autonomy.
    * **ABAC** – attribute-based checks (e.g., time-of-day, source IP, colony membership).
    * **Dynamic escalation** – temporarily elevate an agent's autonomy level with a time bound.
    * **Approval gates** – some tools require explicit approval before use.
    * **Audit integration** – all permission checks and escalations are logged.
    """

    def __init__(self, audit_trail: Any = None):
        self._audit_trail = audit_trail

        # RBAC
        self._roles: Dict[str, RoleDef] = dict(DEFAULT_ROLES)
        self._role_assignments: Dict[str, str] = {}  # agent_id → role name

        # Permission definitions
        self._permissions: Dict[str, PermissionDef] = dict(DEFAULT_PERMISSIONS)

        # ABAC attributes: agent_id → dict of attributes
        self._agent_attributes: Dict[str, Dict[str, Any]] = {}

        # Active escalations: agent_id → EscalationRecord
        self._escalations: Dict[str, EscalationRecord] = {}

        # Pending approval requests: request_id → ApprovalRequest
        self._pending_approvals: Dict[str, ApprovalRequest] = {}

        # Approval callbacks
        self._approval_callbacks: List[Callable[[ApprovalRequest], None]] = []

        # Settings
        settings = get_settings()
        self._auto_approve_l0_to_l1 = settings.security.auto_approve_l0_to_l1
        self._escalation_default_ttl = timedelta(seconds=settings.security.escalation_default_ttl_s)
        self._approval_timeout = timedelta(seconds=settings.security.approval_timeout_s)

    # ── RBAC ───────────────────────────────────────────────────────────────

    def define_role(self, role: RoleDef) -> None:
        """Define or update a role."""
        self._roles[role.name] = role

    def assign_role(self, agent_id: str, role: str) -> None:
        """Assign a role to an agent."""
        if role not in self._roles:
            raise ValueError(f"Unknown role: {role}")
        self._role_assignments[agent_id] = role
        self._audit_log(
            agent_id=agent_id,
            action="role_assigned",
            details={"role": role},
            event_type=AuditEventType.PERMISSION_CHECK,
        )

    def unassign_role(self, agent_id: str) -> None:
        """Remove an agent's role assignment (falls back to default)."""
        self._role_assignments.pop(agent_id, None)

    def get_role(self, agent_id: str) -> str:
        """Get the role assigned to an agent (or the default role)."""
        role_name = self._role_assignments.get(agent_id)
        if role_name and role_name in self._roles:
            return role_name
        # Find default role
        for name, role_def in self._roles.items():
            if role_def.is_default:
                return name
        return "viewer"

    def get_role_definition(self, agent_id: str) -> RoleDef:
        """Get the RoleDef for an agent."""
        return self._roles[self.get_role(agent_id)]

    def list_roles(self) -> Dict[str, Dict[str, Any]]:
        """List all defined roles."""
        return {name: role.model_dump(mode="json") for name, role in self._roles.items()}

    # ── Permission definitions ─────────────────────────────────────────────

    def define_permission(self, perm: PermissionDef) -> None:
        """Define or update a permission for a tool."""
        self._permissions[perm.tool_name] = perm

    def get_permission(self, tool_name: str) -> Optional[PermissionDef]:
        """Look up the permission definition for a tool."""
        return self._permissions.get(tool_name)

    # ── ABAC ───────────────────────────────────────────────────────────────

    def set_agent_attribute(self, agent_id: str, key: str, value: Any) -> None:
        """Set an ABAC attribute for an agent."""
        if agent_id not in self._agent_attributes:
            self._agent_attributes[agent_id] = {}
        self._agent_attributes[agent_id][key] = value

    def get_agent_attribute(self, agent_id: str, key: str, default: Any = None) -> Any:
        """Get an ABAC attribute for an agent."""
        return self._agent_attributes.get(agent_id, {}).get(key, default)

    def check_abac_attributes(self, agent_id: str, required_attrs: Dict[str, Any]) -> bool:
        """Check if an agent's ABAC attributes match requirements.

        All keys in ``required_attrs`` must be present in the agent's
        attributes with matching values.
        """
        agent_attrs = self._agent_attributes.get(agent_id, {})
        for key, expected in required_attrs.items():
            if key not in agent_attrs or agent_attrs[key] != expected:
                return False
        return True

    # ── Permission checking ────────────────────────────────────────────────

    def get_effective_autonomy(self, agent_id: str) -> AutonomyLevel:
        """Get the effective autonomy level for an agent.

        Takes into account:
        * The agent's role-based autonomy level
        * Any active escalation
        """
        role_def = self.get_role_definition(agent_id)
        base_level = role_def.autonomy_level

        # Check for active escalation
        escalation = self._escalations.get(agent_id)
        if escalation and escalation.expires_at > datetime.now(timezone.utc):
            return escalation.to_level  # escalated level
        elif escalation:
            # Expired – remove it
            del self._escalations[agent_id]

        return base_level

    def check_access(
        self,
        agent_id: str,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PermissionCheck:
        """Check if an agent has access to a tool.

        This performs:
        1. RBAC check (role allows the tool)
        2. Autonomy level check (agent's level >= tool's required level)
        3. ABAC check (if context provides attribute requirements)
        4. Approval gate check (some tools need explicit approval)

        Returns a ``PermissionCheck`` with the result.
        """
        role_def = self.get_role_definition(agent_id)
        effective_level = self.get_effective_autonomy(agent_id)
        perm_def = self._permissions.get(tool_name)

        # 1. RBAC: role allows the tool?
        allowed_tools = role_def.allowed_tools
        if "*" not in allowed_tools and tool_name not in allowed_tools:
            return PermissionCheck(
                tool_name=tool_name,
                autonomy_level=effective_level,
                agent_id=agent_id,
                granted=False,
                reason=f"Role '{role_def.name}' does not allow tool '{tool_name}'",
            )

        # 2. Autonomy level check
        required_level = perm_def.required_level if perm_def else AutonomyLevel.L0_READONLY
        if effective_level.value < required_level.value:
            return PermissionCheck(
                tool_name=tool_name,
                autonomy_level=effective_level,
                agent_id=agent_id,
                granted=False,
                reason=f"Autonomy level {effective_level.value} insufficient "
                       f"(requires {required_level.value})",
            )

        # 3. ABAC check
        if context and "required_attributes" in context:
            if not self.check_abac_attributes(agent_id, context["required_attributes"]):
                return PermissionCheck(
                    tool_name=tool_name,
                    autonomy_level=effective_level,
                    agent_id=agent_id,
                    granted=False,
                    reason="ABAC attribute check failed",
                )

        # 4. Approval gate check
        requires_approval = perm_def.requires_approval if perm_def else False
        if requires_approval:
            auto_approve_from = perm_def.auto_approve_from if perm_def else None
            if auto_approve_from and effective_level.value >= auto_approve_from.value:
                requires_approval = False  # auto-approved due to high autonomy

        result = PermissionCheck(
            tool_name=tool_name,
            autonomy_level=effective_level,
            agent_id=agent_id,
            granted=True,
            reason="Access granted",
            requires_approval=requires_approval,
        )

        # Audit
        self._audit_log(
            agent_id=agent_id,
            action="permission_check",
            details={
                "tool_name": tool_name,
                "granted": result.granted,
                "requires_approval": result.requires_approval,
                "effective_level": effective_level.value,
            },
            event_type=AuditEventType.PERMISSION_CHECK,
        )

        return result

    # ── Dynamic escalation ─────────────────────────────────────────────────

    def request_escalation(
        self,
        agent_id: str,
        colony_id: str,
        requested_level: AutonomyLevel,
        justification: str = "",
        task_context: Optional[Dict[str, Any]] = None,
        ttl: Optional[timedelta] = None,
    ) -> ApprovalRequest:
        """Request an autonomy level escalation for an agent.

        L0 → L1 is auto-approved if ``auto_approve_l0_to_l1`` is True.
        All other escalations require human approval.
        """
        current_level = self.get_effective_autonomy(agent_id)

        if requested_level.value <= current_level.value:
            # No escalation needed
            return ApprovalRequest(
                agent_id=agent_id,
                colony_id=colony_id,
                current_level=current_level,
                requested_level=requested_level,
                justification=justification,
                task_context=task_context or {},
                approved=True,
                auto_approved=True,
            )

        # Auto-approve L0 → L1
        if (
            self._auto_approve_l0_to_l1
            and current_level == AutonomyLevel.L0_READONLY
            and requested_level == AutonomyLevel.L1_SAFE_OPS
        ):
            record = self._grant_escalation(
                agent_id=agent_id,
                colony_id=colony_id,
                from_level=current_level,
                to_level=requested_level,
                reason=justification,
                auto_approved=True,
                ttl=ttl or self._escalation_default_ttl,
            )
            return ApprovalRequest(
                agent_id=agent_id,
                colony_id=colony_id,
                current_level=current_level,
                requested_level=requested_level,
                justification=justification,
                task_context=task_context or {},
                approved=True,
                auto_approved=True,
                approval_request_id=record.record_id,
            )

        # Require approval
        request = ApprovalRequest(
            agent_id=agent_id,
            colony_id=colony_id,
            current_level=current_level,
            requested_level=requested_level,
            justification=justification,
            task_context=task_context or {},
            expires_at=datetime.now(timezone.utc) + self._approval_timeout,
        )
        self._pending_approvals[request.request_id] = request

        self._audit_log(
            agent_id=agent_id,
            action="escalation_requested",
            details={
                "from_level": current_level.value,
                "to_level": requested_level.value,
                "request_id": request.request_id,
            },
            event_type=AuditEventType.ESCALATION,
        )

        # Notify approval callbacks
        for callback in self._approval_callbacks:
            try:
                callback(request)
            except Exception as exc:
                logger.warning("Approval callback error: %s", exc)

        return request

    def approve_escalation(
        self,
        request_id: str,
        approver: str = "system",
        ttl: Optional[timedelta] = None,
    ) -> Optional[EscalationRecord]:
        """Approve a pending escalation request.

        Returns the EscalationRecord if approved, or ``None`` if the
        request was not found.
        """
        request = self._pending_approvals.pop(request_id, None)
        if request is None:
            return None

        if request.expires_at and request.expires_at < datetime.now(timezone.utc):
            logger.warning("Escalation request %s expired", request_id)
            return None

        record = self._grant_escalation(
            agent_id=request.agent_id,
            colony_id=request.colony_id,
            from_level=request.current_level,
            to_level=request.requested_level,
            reason=request.justification,
            auto_approved=False,
            ttl=ttl or self._escalation_default_ttl,
            approval_request_id=request_id,
        )

        self._audit_log(
            agent_id=request.agent_id,
            action="escalation_approved",
            details={
                "approver": approver,
                "to_level": request.requested_level.value,
                "record_id": record.record_id,
            },
            event_type=AuditEventType.ESCALATION,
        )

        return record

    def deny_escalation(self, request_id: str, reason: str = "") -> bool:
        """Deny a pending escalation request."""
        request = self._pending_approvals.pop(request_id, None)
        if request is None:
            return False

        self._audit_log(
            agent_id=request.agent_id,
            action="escalation_denied",
            details={"reason": reason, "requested_level": request.requested_level.value},
            event_type=AuditEventType.ESCALATION,
        )
        return True

    def _grant_escalation(
        self,
        agent_id: str,
        colony_id: str,
        from_level: AutonomyLevel,
        to_level: AutonomyLevel,
        reason: str,
        auto_approved: bool,
        ttl: timedelta,
        approval_request_id: Optional[str] = None,
    ) -> EscalationRecord:
        """Create and store an escalation record."""
        record = EscalationRecord(
            agent_id=agent_id,
            colony_id=colony_id,
            from_level=from_level,
            to_level=to_level,
            reason=reason,
            expires_at=datetime.now(timezone.utc) + ttl,
            auto_approved=auto_approved,
            approval_request_id=approval_request_id,
        )
        self._escalations[agent_id] = record
        return record

    def revoke_escalation(self, agent_id: str) -> bool:
        """Revoke an active escalation for an agent."""
        record = self._escalations.pop(agent_id, None)
        if record is None:
            return False

        self._audit_log(
            agent_id=agent_id,
            action="escalation_revoked",
            details={"from_level": record.from_level.value, "to_level": record.to_level.value},
            event_type=AuditEventType.ESCALATION,
        )
        return True

    def get_active_escalations(self) -> Dict[str, EscalationRecord]:
        """Return all currently active escalations."""
        # Prune expired
        now = datetime.now(timezone.utc)
        expired = [aid for aid, rec in self._escalations.items() if rec.expires_at <= now]
        for aid in expired:
            del self._escalations[aid]
        return dict(self._escalations)

    def get_pending_approvals(self) -> Dict[str, ApprovalRequest]:
        """Return all pending approval requests."""
        # Prune expired
        now = datetime.now(timezone.utc)
        expired = [rid for rid, req in self._pending_approvals.items() if req.expires_at and req.expires_at <= now]
        for rid in expired:
            del self._pending_approvals[rid]
        return dict(self._pending_approvals)

    # ── Approval gates ─────────────────────────────────────────────────────

    def register_approval_callback(self, callback: Callable[[ApprovalRequest], None]) -> None:
        """Register a callback for when an approval is requested."""
        self._approval_callbacks.append(callback)

    # ── Audit integration ──────────────────────────────────────────────────

    def _audit_log(
        self,
        agent_id: str,
        action: str,
        details: Dict[str, Any],
        event_type: AuditEventType = AuditEventType.PERMISSION_CHECK,
    ) -> None:
        """Log a permission-related event to the audit trail."""
        if self._audit_trail and hasattr(self._audit_trail, "record"):
            self._audit_trail.record(
                agent_id=agent_id,
                tool_name=details.get("tool_name", ""),
                action=action,
                autonomy_level=details.get("effective_level", details.get("to_level", 0)),
                approved=details.get("granted", True),
                details=details,
                event_type=event_type,
            )

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def role_count(self) -> int:
        return len(self._roles)

    @property
    def permission_count(self) -> int:
        return len(self._permissions)
