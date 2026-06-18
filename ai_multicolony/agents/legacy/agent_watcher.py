"""
👁️ Agent Watcher - Agent Health Monitoring & Recovery System
Monitors all registered agents, performs health checks, collects metrics,
generates reports, and can restart unhealthy agents

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path


# Optional: psutil for system-level metrics
try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


class AgentWatcherAgent:
    """
    Agent Health Monitoring Agent that:
    - Monitors all registered agents' health
    - Performs health checks (heartbeat, response time, error rate)
    - Can restart unhealthy agents
    - Collects and reports agent metrics
    - Generates health reports
    - Sends alerts when agents fail
    - Integrates with the scheduler for periodic checks
    """

    # Health status constants
    STATUS_HEALTHY = "healthy"
    STATUS_DEGRADED = "degraded"
    STATUS_UNHEALTHY = "unhealthy"
    STATUS_UNKNOWN = "unknown"
    STATUS_OFFLINE = "offline"

    # Alert severity levels
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"

    def __init__(self):
        self.agent_id = "agent_watcher"
        self.name = "Agent Watcher"
        self.status = "ready"
        self.capabilities = [
            "health_monitoring",
            "agent_diagnostics",
            "error_tracking",
            "performance_metrics",
            "auto_restart",
            "alerting",
            "health_reports",
            "agent_lifecycle",
        ]

        # Health data per agent
        self._agent_health: Dict[str, Dict[str, Any]] = {}

        # Alert log
        self._alerts: List[Dict[str, Any]] = []

        # Configuration
        self.heartbeat_timeout = int(os.getenv("WATCHER_HEARTBEAT_TIMEOUT", "30"))  # seconds
        self.max_error_rate = float(os.getenv("WATCHER_MAX_ERROR_RATE", "0.5"))  # 50%
        self.max_response_time = float(os.getenv("WATCHER_MAX_RESPONSE_TIME", "10.0"))  # seconds
        self.restart_cooldown = int(os.getenv("WATCHER_RESTART_COOLDOWN", "300"))  # seconds
        self.max_restart_attempts = int(os.getenv("WATCHER_MAX_RESTART_ATTEMPTS", "3"))
        self.health_check_interval = int(os.getenv("WATCHER_CHECK_INTERVAL", "60"))  # seconds

        # Performance tracking for self-monitoring
        self._stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "alerts_sent": 0,
            "restarts_triggered": 0,
            "avg_check_duration": 0.0,
        }

        # Discovered agents (populated on first health check or manual registration)
        self._registered_agents: Dict[str, Dict[str, Any]] = {}

        # Health report storage directory
        self._report_dir = Path("data/health_reports")

        # Load persisted health state if available
        self._load_state()

    # ------------------------------------------------------------------
    # Agent discovery & registration
    # ------------------------------------------------------------------

    def _discover_agents(self) -> Dict[str, Dict[str, Any]]:
        """Discover agents from the agents module registry."""
        agents = {}
        try:
            from agents import AGENTS_REGISTRY
            for agent_id, agent_instance in AGENTS_REGISTRY.items():
                agents[agent_id] = {
                    "instance": agent_instance,
                    "class_name": type(agent_instance).__name__,
                    "discovered_at": datetime.now().isoformat(),
                }
        except ImportError:
            # AGENTS_REGISTRY not available; will rely on manual registration
            # and the known-agents fallback below
            import logging as _logging
            _logging.getLogger(__name__).debug(
                "AGENTS_REGISTRY not importable; agent discovery will use known-agents fallback"
            )

        # Also try to import agents that aren't yet in the registry
        # but are known to the prompt_master
        known_agents = [
            "cybershell", "ui_designer", "dev_engine", "agent_maker",
            "fullstack_dev", "data_sync", "voice_agent", "github_agent",
            "deploy_manager", "web3_plugin",
        ]
        for agent_id in known_agents:
            if agent_id not in agents:
                instance = self._try_import_agent(agent_id)
                if instance is not None:
                    agents[agent_id] = {
                        "instance": instance,
                        "class_name": type(instance).__name__,
                        "discovered_at": datetime.now().isoformat(),
                    }

        return agents

    def _try_import_agent(self, agent_id: str) -> Any:
        """Attempt to import and instantiate an agent by its ID."""
        module_map = {
            "cybershell": ("agents.cybershell", "CyberShellAgent"),
            "ui_designer": ("agents.ui_designer", "UIDesignerAgent"),
            "dev_engine": ("agents.dev_engine", "DevEngineAgent"),
            "agent_maker": ("agents.agent_maker", "AgentMakerAgent"),
            "fullstack_dev": ("agents.fullstack_dev", "FullStackDevAgent"),
            "data_sync": ("agents.data_sync", "DataSyncAgent"),
            "voice_agent": ("agents.voice_agent", "VoiceAgent"),
            "github_agent": ("agents.github_agent", "GitHubAgent"),
            "deploy_manager": ("agents.deploy_manager", "DeployManagerAgent"),
            "web3_plugin": ("agents.web3_plugin", "Web3Plugin"),
        }

        if agent_id not in module_map:
            return None

        module_name, class_name = module_map[agent_id]
        try:
            import importlib
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            return cls()
        except (ImportError, AttributeError):
            return None

    # ------------------------------------------------------------------
    # Public task dispatcher
    # ------------------------------------------------------------------

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task dictionary to the appropriate handler."""
        try:
            action = task.get("action", "health_check")

            handlers = {
                "health_check": self._health_check,
                "check_agent": self._check_single_agent,
                "restart_agent": self._restart_agent,
                "get_metrics": self._get_metrics,
                "get_alerts": self._get_alerts,
                "generate_report": self._generate_report,
                "register_agent": self._register_agent,
                "unregister_agent": self._unregister_agent,
                "list_agents": self._list_agents,
                "configure": self._configure,
                "watchdog_run": self._watchdog_run,
            }

            handler = handlers.get(action)
            if handler is None:
                return self._create_error_response(f"Unknown action: {action}")

            return await handler(task)

        except Exception as exc:
            return self._create_error_response(str(exc))

    # ------------------------------------------------------------------
    # Health check handlers
    # ------------------------------------------------------------------

    async def _health_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a comprehensive health check on all registered agents.

        Checks heartbeat (is the agent reachable?), response time, and
        error rate for each agent.
        """
        start = time.time()

        # Discover / refresh registered agents
        discovered = self._discover_agents()
        for agent_id, info in discovered.items():
            if agent_id not in self._registered_agents:
                self._registered_agents[agent_id] = info

        # Also include agents registered manually
        all_agent_ids = set(self._registered_agents.keys())

        results: Dict[str, Dict[str, Any]] = {}
        overall_healthy = 0
        overall_degraded = 0
        overall_unhealthy = 0
        overall_offline = 0

        for agent_id in all_agent_ids:
            check_result = await self._perform_agent_check(agent_id)
            results[agent_id] = check_result

            status = check_result.get("status", self.STATUS_UNKNOWN)
            if status == self.STATUS_HEALTHY:
                overall_healthy += 1
            elif status == self.STATUS_DEGRADED:
                overall_degraded += 1
            elif status == self.STATUS_UNHEALTHY:
                overall_unhealthy += 1
            else:
                overall_offline += 1

        elapsed = time.time() - start

        # Determine overall system health
        total = len(all_agent_ids)
        if total == 0:
            system_status = self.STATUS_UNKNOWN
        elif overall_unhealthy > total // 2:
            system_status = self.STATUS_UNHEALTHY
        elif overall_degraded > 0 or overall_offline > 0:
            system_status = self.STATUS_DEGRADED
        else:
            system_status = self.STATUS_HEALTHY

        self._update_stats(True, elapsed)

        # Persist state
        self._save_state()

        return {
            "success": True,
            "system_status": system_status,
            "total_agents": total,
            "healthy": overall_healthy,
            "degraded": overall_degraded,
            "unhealthy": overall_unhealthy,
            "offline": overall_offline,
            "check_duration": round(elapsed, 3),
            "agent_results": results,
            "checked_at": datetime.now().isoformat(),
        }

    async def _check_single_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a health check on a single agent."""
        agent_id = task.get("agent_id", "")
        if not agent_id:
            return self._create_error_response("agent_id is required")

        result = await self._perform_agent_check(agent_id)
        return {
            "success": True,
            "agent_id": agent_id,
            **result,
        }

    async def _perform_agent_check(self, agent_id: str) -> Dict[str, Any]:
        """
        Execute a full health check for a single agent.

        Returns a dict with status, response_time, error_rate, etc.
        """
        agent_info = self._registered_agents.get(agent_id)
        instance = agent_info.get("instance") if agent_info else None

        # Initialize health record if needed
        if agent_id not in self._agent_health:
            self._agent_health[agent_id] = {
                "status": self.STATUS_UNKNOWN,
                "last_check": None,
                "last_healthy": None,
                "consecutive_failures": 0,
                "total_checks": 0,
                "total_failures": 0,
                "restart_attempts": 0,
                "last_restart": None,
                "response_times": [],
                "alerts_triggered": 0,
            }

        health = self._agent_health[agent_id]
        health["total_checks"] += 1
        health["last_check"] = datetime.now().isoformat()

        # If no instance available, mark as offline
        if instance is None:
            health["status"] = self.STATUS_OFFLINE
            return {
                "status": self.STATUS_OFFLINE,
                "reason": "Agent instance not available",
                "agent_id": agent_id,
            }

        # Attempt heartbeat via process_task with a lightweight ping
        check_start = time.time()
        try:
            ping_task = {
                "action": "ping",
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat(),
            }
            # Use a timeout so a hung agent doesn't block the watcher
            result = await asyncio.wait_for(
                instance.process_task(ping_task),
                timeout=self.heartbeat_timeout,
            )
            response_time = time.time() - check_start

            # Track response time
            health["response_times"].append(response_time)
            if len(health["response_times"]) > 100:
                health["response_times"] = health["response_times"][-50:]

            avg_response_time = sum(health["response_times"]) / len(health["response_times"])

            # Check if the response indicates success
            is_responsive = result is not None and isinstance(result, dict)
            error_rate = health["total_failures"] / max(health["total_checks"], 1)

            # Determine status
            if not is_responsive:
                status = self.STATUS_UNHEALTHY
                health["consecutive_failures"] += 1
                health["total_failures"] += 1
            elif avg_response_time > self.max_response_time:
                status = self.STATUS_DEGRADED
                health["consecutive_failures"] = 0
            elif error_rate > self.max_error_rate:
                status = self.STATUS_DEGRADED
                health["consecutive_failures"] = 0
            else:
                status = self.STATUS_HEALTHY
                health["consecutive_failures"] = 0
                health["last_healthy"] = datetime.now().isoformat()

            health["status"] = status

            # Auto-restart logic
            if health["consecutive_failures"] >= 3:
                await self._maybe_restart_agent(agent_id, health)

            return {
                "status": status,
                "responsive": is_responsive,
                "response_time": round(response_time, 3),
                "avg_response_time": round(avg_response_time, 3),
                "error_rate": round(error_rate, 3),
                "consecutive_failures": health["consecutive_failures"],
                "agent_id": agent_id,
            }

        except asyncio.TimeoutError:
            response_time = time.time() - check_start
            health["status"] = self.STATUS_UNHEALTHY
            health["consecutive_failures"] += 1
            health["total_failures"] += 1
            health["response_times"].append(response_time)

            # Maybe restart
            if health["consecutive_failures"] >= 3:
                await self._maybe_restart_agent(agent_id, health)

            return {
                "status": self.STATUS_UNHEALTHY,
                "reason": f"Heartbeat timed out after {self.heartbeat_timeout}s",
                "response_time": round(response_time, 3),
                "consecutive_failures": health["consecutive_failures"],
                "agent_id": agent_id,
            }

        except Exception as exc:
            health["status"] = self.STATUS_UNHEALTHY
            health["consecutive_failures"] += 1
            health["total_failures"] += 1

            return {
                "status": self.STATUS_UNHEALTHY,
                "reason": f"Health check error: {exc}",
                "consecutive_failures": health["consecutive_failures"],
                "agent_id": agent_id,
            }

    async def _maybe_restart_agent(
        self, agent_id: str, health: Dict[str, Any]
    ) -> bool:
        """
        Evaluate whether an agent should be restarted, and if so, attempt it.

        Returns True if a restart was attempted.
        """
        # Check restart cooldown
        last_restart = health.get("last_restart")
        if last_restart:
            last_dt = datetime.fromisoformat(last_restart)
            if (datetime.now() - last_dt).total_seconds() < self.restart_cooldown:
                return False

        # Check max restart attempts
        if health.get("restart_attempts", 0) >= self.max_restart_attempts:
            # Escalate alert
            self._add_alert(
                agent_id=agent_id,
                severity=self.SEVERITY_CRITICAL,
                message=(
                    f"Agent '{agent_id}' has exceeded max restart attempts "
                    f"({self.max_restart_attempts}). Manual intervention required."
                ),
            )
            return False

        # Attempt restart
        self._add_alert(
            agent_id=agent_id,
            severity=self.SEVERITY_WARNING,
            message=f"Agent '{agent_id}' is unhealthy — attempting restart.",
        )

        restart_result = await self._do_restart_agent(agent_id)
        if restart_result:
            health["restart_attempts"] = health.get("restart_attempts", 0) + 1
            health["last_restart"] = datetime.now().isoformat()
            health["consecutive_failures"] = 0
            self._stats["restarts_triggered"] += 1
        return restart_result

    # ------------------------------------------------------------------
    # Agent restart
    # ------------------------------------------------------------------

    async def _restart_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Restart a specific agent by re-instantiating it."""
        agent_id = task.get("agent_id", "") or task.get("target_agent", "")
        if not agent_id:
            return self._create_error_response("agent_id is required")

        success = await self._do_restart_agent(agent_id)
        if success:
            return {
                "success": True,
                "message": f"Agent '{agent_id}' restarted successfully",
                "agent_id": agent_id,
                "restarted_at": datetime.now().isoformat(),
            }
        else:
            return self._create_error_response(f"Failed to restart agent '{agent_id}'")

    async def _do_restart_agent(self, agent_id: str) -> bool:
        """
        Attempt to re-instantiate an agent.

        This creates a fresh instance and replaces it in the registry.
        """
        try:
            new_instance = self._try_import_agent(agent_id)
            if new_instance is None:
                return False

            # Update registered agents
            if agent_id in self._registered_agents:
                self._registered_agents[agent_id]["instance"] = new_instance
            else:
                self._registered_agents[agent_id] = {
                    "instance": new_instance,
                    "class_name": type(new_instance).__name__,
                    "discovered_at": datetime.now().isoformat(),
                }

            # Update AGENTS_REGISTRY if available
            try:
                from agents import AGENTS_REGISTRY
                AGENTS_REGISTRY[agent_id] = new_instance
            except ImportError:
                pass

            # Reset health tracking for this agent
            if agent_id in self._agent_health:
                self._agent_health[agent_id]["consecutive_failures"] = 0
                self._agent_health[agent_id]["restart_attempts"] = 0
                self._agent_health[agent_id]["status"] = self.STATUS_UNKNOWN

            return True

        except Exception:
            return False

    # ------------------------------------------------------------------
    # Metrics & alerts
    # ------------------------------------------------------------------

    async def _get_metrics(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get collected metrics for a specific agent or all agents."""
        agent_id = task.get("agent_id")

        if agent_id:
            health = self._agent_health.get(agent_id, {})
            agent_info = self._registered_agents.get(agent_id, {})
            instance = agent_info.get("instance")

            metrics: Dict[str, Any] = {
                "agent_id": agent_id,
                "health": health,
                "capabilities": getattr(instance, "capabilities", []) if instance else [],
                "status": getattr(instance, "status", "unknown") if instance else "offline",
            }

            # Try to get the agent's own performance metrics
            if instance and hasattr(instance, "get_performance_metrics"):
                try:
                    metrics["agent_metrics"] = instance.get_performance_metrics()
                except Exception:
                    pass

            # System-level metrics
            if _PSUTIL_AVAILABLE:
                metrics["system"] = {
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                }

            return {"success": True, "metrics": metrics}

        # All agents
        all_metrics = {}
        for aid in self._registered_agents:
            health = self._agent_health.get(aid, {})
            instance = self._registered_agents[aid].get("instance")
            all_metrics[aid] = {
                "status": health.get("status", self.STATUS_UNKNOWN),
                "last_check": health.get("last_check"),
                "consecutive_failures": health.get("consecutive_failures", 0),
                "total_checks": health.get("total_checks", 0),
                "total_failures": health.get("total_failures", 0),
                "avg_response_time": (
                    sum(health["response_times"]) / len(health["response_times"])
                    if health.get("response_times")
                    else None
                ),
            }
            if instance and hasattr(instance, "get_performance_metrics"):
                try:
                    all_metrics[aid]["agent_metrics"] = instance.get_performance_metrics()
                except Exception:
                    pass

        return {
            "success": True,
            "total_agents": len(all_metrics),
            "metrics": all_metrics,
        }

    async def _get_alerts(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent alerts, optionally filtered by severity or agent."""
        severity_filter = task.get("severity")
        agent_filter = task.get("agent_id")
        limit = min(task.get("limit", 50), 500)

        filtered = self._alerts
        if severity_filter:
            filtered = [a for a in filtered if a.get("severity") == severity_filter]
        if agent_filter:
            filtered = [a for a in filtered if a.get("agent_id") == agent_filter]

        return {
            "success": True,
            "total": len(filtered),
            "alerts": filtered[-limit:],
        }

    def _add_alert(
        self,
        agent_id: str,
        severity: str,
        message: str,
    ):
        """Record a new alert."""
        alert = {
            "agent_id": agent_id,
            "severity": severity,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self._alerts.append(alert)
        self._stats["alerts_sent"] += 1

        # Keep alerts bounded
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-500:]

        # Update agent health alert count
        if agent_id in self._agent_health:
            self._agent_health[agent_id]["alerts_triggered"] = (
                self._agent_health[agent_id].get("alerts_triggered", 0) + 1
            )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def _generate_report(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive health report."""
        report_type = task.get("report_type", "summary")  # summary | detailed | json

        # Run a fresh health check to get latest data
        health_data = await self._health_check(task)

        # Build report
        report = {
            "generated_at": datetime.now().isoformat(),
            "system_status": health_data.get("system_status"),
            "total_agents": health_data.get("total_agents", 0),
            "summary": {
                "healthy": health_data.get("healthy", 0),
                "degraded": health_data.get("degraded", 0),
                "unhealthy": health_data.get("unhealthy", 0),
                "offline": health_data.get("offline", 0),
            },
        }

        if report_type == "detailed":
            report["agent_details"] = health_data.get("agent_results", {})
            report["recent_alerts"] = self._alerts[-20:]
            report["watcher_metrics"] = self._stats

        # System metrics
        if _PSUTIL_AVAILABLE:
            report["system_metrics"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                },
                "disk": {
                    "total": psutil.disk_usage("/").total,
                    "used": psutil.disk_usage("/").used,
                    "percent": psutil.disk_usage("/").percent,
                },
            }

        # Save report to disk
        try:
            self._report_dir.mkdir(parents=True, exist_ok=True)
            report_file = (
                self._report_dir
                / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            # Clean up old reports (keep last 30)
            reports = sorted(self._report_dir.glob("health_report_*.json"))
            if len(reports) > 30:
                for old_report in reports[:-30]:
                    old_report.unlink()

            report["report_file"] = str(report_file)
        except Exception as exc:
            report["report_save_error"] = str(exc)

        return {"success": True, "report": report}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def _register_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Manually register an agent for monitoring."""
        agent_id = task.get("agent_id", "")
        if not agent_id:
            return self._create_error_response("agent_id is required")

        instance = task.get("instance") or self._try_import_agent(agent_id)

        self._registered_agents[agent_id] = {
            "instance": instance,
            "class_name": type(instance).__name__ if instance else "Unknown",
            "discovered_at": datetime.now().isoformat(),
            "registered_manually": True,
        }

        return {
            "success": True,
            "message": f"Agent '{agent_id}' registered for monitoring",
            "agent_id": agent_id,
        }

    async def _unregister_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Unregister an agent from monitoring."""
        agent_id = task.get("agent_id", "")
        if not agent_id:
            return self._create_error_response("agent_id is required")

        if agent_id in self._registered_agents:
            del self._registered_agents[agent_id]
        if agent_id in self._agent_health:
            del self._agent_health[agent_id]

        return {
            "success": True,
            "message": f"Agent '{agent_id}' unregistered from monitoring",
        }

    async def _list_agents(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List all registered agents and their current health status."""
        agents = []
        for agent_id, info in self._registered_agents.items():
            health = self._agent_health.get(agent_id, {})
            instance = info.get("instance")
            agents.append(
                {
                    "agent_id": agent_id,
                    "class_name": info.get("class_name", "Unknown"),
                    "status": health.get("status", self.STATUS_UNKNOWN),
                    "last_check": health.get("last_check"),
                    "consecutive_failures": health.get("consecutive_failures", 0),
                    "capabilities": (
                        getattr(instance, "capabilities", [])
                        if instance
                        else []
                    ),
                }
            )

        return {
            "success": True,
            "total_agents": len(agents),
            "agents": agents,
        }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    async def _configure(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update watcher configuration at runtime."""
        if task.get("heartbeat_timeout"):
            self.heartbeat_timeout = int(task["heartbeat_timeout"])
        if task.get("max_error_rate"):
            self.max_error_rate = float(task["max_error_rate"])
        if task.get("max_response_time"):
            self.max_response_time = float(task["max_response_time"])
        if task.get("restart_cooldown"):
            self.restart_cooldown = int(task["restart_cooldown"])
        if task.get("max_restart_attempts"):
            self.max_restart_attempts = int(task["max_restart_attempts"])
        if task.get("health_check_interval"):
            self.health_check_interval = int(task["health_check_interval"])

        return {
            "success": True,
            "configuration": {
                "heartbeat_timeout": self.heartbeat_timeout,
                "max_error_rate": self.max_error_rate,
                "max_response_time": self.max_response_time,
                "restart_cooldown": self.restart_cooldown,
                "max_restart_attempts": self.max_restart_attempts,
                "health_check_interval": self.health_check_interval,
            },
        }

    # ------------------------------------------------------------------
    # Watchdog (periodic run — intended to be called by the scheduler)
    # ------------------------------------------------------------------

    async def _watchdog_run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single watchdog cycle: health check + alerting + auto-restart.

        This is the action called by the scheduler's recurring task.
        """
        result = await self._health_check(task)

        # Generate alerts for unhealthy agents
        agent_results = result.get("agent_results", {})
        for agent_id, check in agent_results.items():
            status = check.get("status")
            if status == self.STATUS_UNHEALTHY:
                self._add_alert(
                    agent_id=agent_id,
                    severity=self.SEVERITY_CRITICAL,
                    message=f"Agent '{agent_id}' is unhealthy: {check.get('reason', 'unknown reason')}",
                )
            elif status == self.STATUS_DEGRADED:
                self._add_alert(
                    agent_id=agent_id,
                    severity=self.SEVERITY_WARNING,
                    message=f"Agent '{agent_id}' is degraded: response_time={check.get('avg_response_time', 'N/A')}s",
                )

        return result

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _save_state(self):
        """Persist health state to disk."""
        try:
            self._report_dir.mkdir(parents=True, exist_ok=True)
            state_file = self._report_dir / "watcher_state.json"
            state = {
                "agent_health": self._agent_health,
                "alerts": self._alerts[-100:],  # save last 100 alerts
                "saved_at": datetime.now().isoformat(),
            }
            # Remove non-serializable entries
            clean_health = {}
            for aid, data in self._agent_health.items():
                clean_health[aid] = {
                    k: v for k, v in data.items() if k != "instance"
                }
            state["agent_health"] = clean_health

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception:
            pass  # Best-effort persistence

    def _load_state(self):
        """Load persisted health state from disk."""
        try:
            state_file = self._report_dir / "watcher_state.json"
            if not state_file.exists():
                return

            with open(state_file, "r") as f:
                state = json.load(f)

            self._agent_health = state.get("agent_health", {})
            self._alerts = state.get("alerts", [])
        except Exception:
            pass  # Best-effort load

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------

    def _update_stats(self, success: bool, elapsed: float):
        """Update running performance statistics."""
        self._stats["total_checks"] += 1
        if success:
            self._stats["successful_checks"] += 1
        else:
            self._stats["failed_checks"] += 1
        total = self._stats["total_checks"]
        current_avg = self._stats["avg_check_duration"]
        self._stats["avg_check_duration"] = (current_avg * (total - 1) + elapsed) / total

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        self._stats["failed_checks"] += 1
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return agent performance metrics."""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "capabilities": self.capabilities,
            "stats": self._stats,
            "registered_agents": len(self._registered_agents),
            "total_alerts": len(self._alerts),
            "psutil_available": _PSUTIL_AVAILABLE,
            "configuration": {
                "heartbeat_timeout": self.heartbeat_timeout,
                "max_error_rate": self.max_error_rate,
                "max_response_time": self.max_response_time,
                "restart_cooldown": self.restart_cooldown,
                "max_restart_attempts": self.max_restart_attempts,
                "health_check_interval": self.health_check_interval,
            },
        }


# Global instance
agent_watcher = AgentWatcherAgent()
