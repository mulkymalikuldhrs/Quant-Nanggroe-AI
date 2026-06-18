"""Safety system for the AI-MultiColony organism.

Implements the Immune phase of the organism lifecycle: detecting
and preventing harmful patterns including infinite loops, runaway
iterations, excessive resource consumption, and safety violations.

The immune system operates as a guard layer that monitors all
organism activities and can intervene to stop dangerous behaviour.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class ThreatLevel(str, Enum):
    """Severity level of a detected threat."""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Type of detected threat."""
    INFINITE_LOOP = "infinite_loop"
    ITERATION_LIMIT = "iteration_limit"
    MEMORY_EXCEEDED = "memory_exceeded"
    CPU_EXCEEDED = "cpu_exceeded"
    TIME_EXCEEDED = "time_exceeded"
    RECURSION_DEPTH = "recursion_depth"
    DUPLICATE_ACTION = "duplicate_action"
    UNAUTHORIZED_ACTION = "unauthorized_action"
    DATA_EXFILTRATION = "data_exfiltration"
    SAFETY_VIOLATION = "safety_violation"


class ImmuneAction(str, Enum):
    """Action taken by the immune system."""
    NONE = "none"
    WARN = "warn"
    THROTTLE = "throttle"
    PAUSE = "pause"
    KILL = "kill"
    QUARANTINE = "quarantine"


# ── Models ───────────────────────────────────────────────────────────────────


class ThreatAlert(BaseModel):
    """An alert from the immune system."""
    model_config = ConfigDict(frozen=False)

    alert_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    threat_type: ThreatType = ThreatType.SAFETY_VIOLATION
    threat_level: ThreatLevel = ThreatLevel.WARNING
    action_taken: ImmuneAction = ImmuneAction.WARN
    description: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False


class ImmuneConfig(BaseModel):
    """Configuration for the immune system."""
    model_config = ConfigDict(frozen=False)

    max_iterations: int = 1000
    max_recursion_depth: int = 50
    max_execution_time_s: float = 3600.0  # 1 hour
    max_memory_mb: float = 2048.0
    max_cpu_percent: float = 90.0
    max_duplicate_actions: int = 10
    loop_detection_window: int = 5  # Number of actions to check for loops
    enable_auto_kill: bool = True
    kill_on_critical: bool = True
    warn_on_warning: bool = True
    throttle_on_danger: bool = True
    quarantine_suspicious: bool = True
    allowed_actions: List[str] = Field(default_factory=lambda: [
        "read", "write", "execute", "search", "communicate", "analyze",
    ])
    forbidden_actions: List[str] = Field(default_factory=lambda: [
        "delete_system", "modify_config", "escalate_privileges",
        "exfiltrate_data", "access_secrets",
    ])


# ── Immune System ────────────────────────────────────────────────────────────


class ImmuneSystem:
    """Safety system for the organism.

    Monitors all organism activities, detects threats, and takes
    protective actions.  Implements loop detection, iteration limits,
    kill switches, and action authorization.

    Usage::

        immune = ImmuneSystem()
        immune.check_action("execute", {"target": "script.py"})
        immune.check_iteration(count=500)
        immune.check_execution_time(elapsed_s=1800)
    """

    def __init__(self, config: Optional[ImmuneConfig] = None):
        self._config = config or ImmuneConfig()
        self._alerts: List[ThreatAlert] = []
        self._action_history: List[Dict[str, Any]] = []
        self._iteration_count: int = 0
        self._start_time: float = time.monotonic()
        self._killed: bool = False
        self._paused: bool = False
        self._quarantined: bool = False
        self._recursion_depth: int = 0

    # ── Check methods ───────────────────────────────────────────────────

    def check_action(self, action: str, context: Optional[Dict[str, Any]] = None) -> ThreatAlert:
        """Check if an action is allowed.

        Parameters
        ----------
        action:
            Name of the action to check.
        context:
            Additional context about the action.

        Returns
        -------
        ThreatAlert
            Alert if the action is forbidden, or a safe alert.
        """
        context = context or {}

        # Check forbidden actions
        if action in self._config.forbidden_actions:
            alert = self._create_alert(
                threat_type=ThreatType.UNAUTHORIZED_ACTION,
                threat_level=ThreatLevel.CRITICAL,
                description=f"Forbidden action attempted: {action}",
                context={"action": action, **context},
            )
            if self._config.kill_on_critical:
                self._kill()
            return alert

        # Check allowed actions
        if self._config.allowed_actions and action not in self._config.allowed_actions:
            alert = self._create_alert(
                threat_type=ThreatType.UNAUTHORIZED_ACTION,
                threat_level=ThreatLevel.WARNING,
                description=f"Action not in allowed list: {action}",
                context={"action": action, **context},
            )
            return alert

        # Record action
        self._action_history.append({
            "action": action,
            "timestamp": time.monotonic(),
            "context": context,
        })

        # Check for duplicate actions (loop detection)
        duplicate_count = self._count_recent_duplicates(action)
        if duplicate_count >= self._config.max_duplicate_actions:
            alert = self._create_alert(
                threat_type=ThreatType.DUPLICATE_ACTION,
                threat_level=ThreatLevel.DANGER,
                description=f"Duplicate action detected: {action} (x{duplicate_count})",
                context={"action": action, "duplicate_count": duplicate_count},
            )
            if self._config.throttle_on_danger:
                self._paused = True
            return alert

        # Loop detection
        if self._detect_loop():
            alert = self._create_alert(
                threat_type=ThreatType.INFINITE_LOOP,
                threat_level=ThreatLevel.CRITICAL,
                description="Infinite loop pattern detected in action history",
                context={"recent_actions": [a["action"] for a in self._action_history[-10:]]},
            )
            if self._config.kill_on_critical:
                self._kill()
            return alert

        # Safe
        return ThreatAlert(
            threat_level=ThreatLevel.SAFE,
            description="Action permitted",
            context={"action": action},
        )

    def check_iteration(self, count: Optional[int] = None) -> ThreatAlert:
        """Check iteration count against limits.

        Parameters
        ----------
        count:
            Current iteration count. If None, increments internal counter.

        Returns
        -------
        ThreatAlert
            Alert if iteration limit is exceeded.
        """
        if count is not None:
            self._iteration_count = count
        else:
            self._iteration_count += 1

        if self._iteration_count > self._config.max_iterations:
            alert = self._create_alert(
                threat_type=ThreatType.ITERATION_LIMIT,
                threat_level=ThreatLevel.CRITICAL,
                description=f"Iteration limit exceeded: {self._iteration_count}/{self._config.max_iterations}",
                context={"iteration_count": self._iteration_count, "limit": self._config.max_iterations},
            )
            if self._config.kill_on_critical:
                self._kill()
            return alert

        if self._iteration_count > self._config.max_iterations * 0.8:
            return self._create_alert(
                threat_type=ThreatType.ITERATION_LIMIT,
                threat_level=ThreatLevel.WARNING,
                description=f"Approaching iteration limit: {self._iteration_count}/{self._config.max_iterations}",
                context={"iteration_count": self._iteration_count, "limit": self._config.max_iterations},
            )

        return ThreatAlert(
            threat_level=ThreatLevel.SAFE,
            description="Iteration count within limits",
        )

    def check_execution_time(self, elapsed_s: Optional[float] = None) -> ThreatAlert:
        """Check execution time against limits."""
        if elapsed_s is None:
            elapsed_s = time.monotonic() - self._start_time

        if elapsed_s > self._config.max_execution_time_s:
            alert = self._create_alert(
                threat_type=ThreatType.TIME_EXCEEDED,
                threat_level=ThreatLevel.CRITICAL,
                description=f"Execution time exceeded: {elapsed_s:.1f}s/{self._config.max_execution_time_s}s",
                context={"elapsed_s": elapsed_s, "limit_s": self._config.max_execution_time_s},
            )
            if self._config.kill_on_critical:
                self._kill()
            return alert

        if elapsed_s > self._config.max_execution_time_s * 0.8:
            return self._create_alert(
                threat_type=ThreatType.TIME_EXCEEDED,
                threat_level=ThreatLevel.WARNING,
                description=f"Approaching time limit: {elapsed_s:.1f}s/{self._config.max_execution_time_s}s",
            )

        return ThreatAlert(threat_level=ThreatLevel.SAFE, description="Execution time within limits")

    def check_recursion_depth(self, depth: Optional[int] = None) -> ThreatAlert:
        """Check recursion depth against limits."""
        if depth is not None:
            self._recursion_depth = depth
        else:
            self._recursion_depth += 1

        if self._recursion_depth > self._config.max_recursion_depth:
            alert = self._create_alert(
                threat_type=ThreatType.RECURSION_DEPTH,
                threat_level=ThreatLevel.DANGER,
                description=f"Recursion depth exceeded: {self._recursion_depth}",
                context={"depth": self._recursion_depth, "limit": self._config.max_recursion_depth},
            )
            return alert

        return ThreatAlert(threat_level=ThreatLevel.SAFE, description="Recursion depth within limits")

    # ── Control methods ─────────────────────────────────────────────────

    def _kill(self) -> None:
        """Activate the kill switch."""
        self._killed = True
        logger.critical("IMMUNE SYSTEM: Kill switch activated!")

    def activate_kill_switch(self, reason: str = "Manual activation") -> ThreatAlert:
        """Manually activate the kill switch.

        Parameters
        ----------
        reason:
            Reason for activation.

        Returns
        -------
        ThreatAlert
            Critical alert confirming kill switch activation.
        """
        self._kill()
        return self._create_alert(
            threat_type=ThreatType.SAFETY_VIOLATION,
            threat_level=ThreatLevel.CRITICAL,
            description=f"Kill switch activated: {reason}",
            action_taken=ImmuneAction.KILL,
        )

    def pause(self, reason: str = "") -> None:
        """Pause the organism."""
        self._paused = True
        logger.warning("Immune system paused organism: %s", reason)

    def resume(self) -> None:
        """Resume the organism after a pause."""
        self._paused = False
        logger.info("Immune system resumed organism")

    def reset(self) -> None:
        """Reset the immune system state."""
        self._iteration_count = 0
        self._start_time = time.monotonic()
        self._killed = False
        self._paused = False
        self._quarantined = False
        self._recursion_depth = 0
        self._action_history.clear()

    # ── Loop detection ──────────────────────────────────────────────────

    def _count_recent_duplicates(self, action: str) -> int:
        """Count recent duplicate actions in the action history."""
        window = self._action_history[-self._config.loop_detection_window * 2:]
        return sum(1 for a in window if a["action"] == action)

    def _detect_loop(self) -> bool:
        """Detect infinite loop patterns in action history.

        Checks if the last N actions form a repeating pattern.
        """
        window_size = self._config.loop_detection_window
        if len(self._action_history) < window_size * 2:
            return False

        recent = [a["action"] for a in self._action_history[-window_size:]]
        previous = [a["action"] for a in self._action_history[-window_size * 2:-window_size]]

        return recent == previous

    # ── Helpers ─────────────────────────────────────────────────────────

    def _create_alert(
        self,
        threat_type: ThreatType,
        threat_level: ThreatLevel,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        action_taken: Optional[ImmuneAction] = None,
    ) -> ThreatAlert:
        """Create and record a threat alert."""
        # Determine action
        if action_taken is None:
            if threat_level == ThreatLevel.CRITICAL:
                action_taken = ImmuneAction.KILL if self._config.kill_on_critical else ImmuneAction.PAUSE
            elif threat_level == ThreatLevel.DANGER:
                action_taken = ImmuneAction.THROTTLE if self._config.throttle_on_danger else ImmuneAction.WARN
            elif threat_level == ThreatLevel.WARNING:
                action_taken = ImmuneAction.WARN if self._config.warn_on_warning else ImmuneAction.NONE
            else:
                action_taken = ImmuneAction.NONE

        alert = ThreatAlert(
            threat_type=threat_type,
            threat_level=threat_level,
            action_taken=action_taken,
            description=description,
            context=context or {},
        )

        self._alerts.append(alert)
        logger.warning("Immune alert: [%s] %s", threat_level.value, description)
        return alert

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def is_killed(self) -> bool:
        """Whether the kill switch has been activated."""
        return self._killed

    @property
    def is_paused(self) -> bool:
        """Whether the organism is paused."""
        return self._paused

    @property
    def is_quarantined(self) -> bool:
        """Whether the organism is quarantined."""
        return self._quarantined

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    @property
    def alerts(self) -> List[ThreatAlert]:
        return list(self._alerts)

    @property
    def config(self) -> ImmuneConfig:
        return self._config

    @property
    def stats(self) -> Dict[str, Any]:
        """Immune system statistics."""
        return {
            "killed": self._killed,
            "paused": self._paused,
            "quarantined": self._quarantined,
            "iteration_count": self._iteration_count,
            "total_alerts": len(self._alerts),
            "critical_alerts": sum(1 for a in self._alerts if a.threat_level == ThreatLevel.CRITICAL),
            "warning_alerts": sum(1 for a in self._alerts if a.threat_level == ThreatLevel.WARNING),
            "elapsed_s": time.monotonic() - self._start_time,
        }
