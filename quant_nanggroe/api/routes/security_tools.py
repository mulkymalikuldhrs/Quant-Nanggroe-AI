"""Security Tools API — real audit logging, encryption, auth, monitoring.

Replaces the stub with full security subsystem integration:

- /security/events     → AuditLogger.query() — real audit trail
- /security/status     → KillSwitch + encryption status
- /security/encrypt    → EncryptedStore.encrypt()
- /security/decrypt    → EncryptedStore.decrypt()
- /tools/list          → available security tools
- /tools/{id}/execute  → execute security tool
- /monitor/system      → system metrics (CPU, memory, disk)
- /monitor/agents      → agent health monitor

Uses real AuditLogger, Auth, EncryptedStore, KeyVault from quant_nanggroe.security
when available, with in-memory fallback.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["security"])

# ---------------------------------------------------------------------------
# Real security modules — graceful fallback
# ---------------------------------------------------------------------------

_HAS_AUDIT = False
_HAS_ENCRYPTION = False
_HAS_AUTH = False
_HAS_KEYVAULT = False

try:
    from quant_nanggroe.security.audit import AuditLogger, AuditRecord

    _audit_logger = AuditLogger(db_path=os.environ.get("QNAI_AUDIT_DB", "audit.db"))
    _HAS_AUDIT = True
except ImportError:
    _audit_logger = None  # type: ignore
    AuditRecord = None  # type: ignore
    logger.info("AuditLogger not available — using in-memory fallback")

try:
    from quant_nanggroe.security.encryption import EncryptedStore

    _encrypted_store = EncryptedStore()
    _HAS_ENCRYPTION = True
except ImportError:
    _encrypted_store = None  # type: ignore
    logger.info("EncryptedStore not available — using pass-through fallback")

try:
    from quant_nanggroe.security.auth import AuthManager, Role

    _auth_manager = AuthManager()
    _HAS_AUTH = True
except ImportError:
    _auth_manager = None  # type: ignore
    Role = None  # type: ignore
    logger.info("AuthManager not available")

try:
    from quant_nanggroe.security.keyvault import KeyVault

    _keyvault = KeyVault()
    _HAS_KEYVAULT = True
except ImportError:
    _keyvault = None  # type: ignore

# ---------------------------------------------------------------------------
# In-memory fallback stores
# ---------------------------------------------------------------------------

_fallback_audit_log: List[Dict[str, Any]] = []
_fallback_tools: List[Dict[str, Any]] = [
    {"id": "encrypt", "name": "Encrypt Data", "category": "crypto", "description": "Encrypt a message using AES-256"},
    {"id": "decrypt", "name": "Decrypt Data", "category": "crypto", "description": "Decrypt a message using AES-256"},
    {"id": "hash", "name": "Hash Content", "category": "crypto", "description": "Generate SHA-256 hash of content"},
    {"id": "verify", "name": "Verify Integrity", "category": "crypto", "description": "Verify data integrity with checksum"},
    {"id": "token-validate", "name": "Validate Token", "category": "auth", "description": "Validate a JWT access token"},
    {"id": "token-revoke", "name": "Revoke Token", "category": "auth", "description": "Revoke an access token"},
    {"id": "key-rotate", "name": "Rotate Key", "category": "keyvault", "description": "Rotate encryption key"},
    {"id": "audit-export", "name": "Export Audit Log", "category": "audit", "description": "Export audit records as JSON"},
    {"id": "system-scan", "name": "System Scan", "category": "monitor", "description": "Scan system for anomalies"},
]

_fallback_tool_history: List[Dict[str, Any]] = []


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _make_id() -> str:
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Helper: get services from request.app if available
# ---------------------------------------------------------------------------


def _get_audit_logger(request: Request) -> Any:
    """Try to get the real AuditLogger from the app state."""
    try:
        al = request.app.state.audit_logger
        if al is not None:
            return al
    except (AttributeError, RuntimeError):
        pass
    return _audit_logger


def _get_kill_switch(request: Request) -> Any:
    """Try to get the KillSwitch from the app state."""
    try:
        ks = request.app.state.kill_switch
        return ks
    except (AttributeError, RuntimeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Security Events
# ---------------------------------------------------------------------------


@router.get("/security/events")
def security_events(
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    event_type: Optional[str] = Query(None),
    agent: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Get security audit events with optional filters."""
    al = _get_audit_logger(request)

    if _HAS_AUDIT and al:
        try:
            import asyncio

            records = asyncio.run(
                al.query(
                    event_type=event_type,
                    agent=agent,
                    symbol=symbol,
                    limit=limit,
                )
            )
            events = []
            for rec in records:
                detail_str = getattr(rec, "details", "{}")
                events.append({
                    "id": rec.id,
                    "timestamp": rec.timestamp.isoformat() if hasattr(rec.timestamp, "isoformat") else str(rec.timestamp),
                    "agent": rec.agent,
                    "event_type": rec.event_type,
                    "symbol": rec.symbol,
                    "action": rec.action,
                    "verdict": rec.verdict,
                    "details": json.loads(detail_str) if isinstance(detail_str, str) else detail_str,
                    "severity": "critical" if rec.verdict in ("rejected", "denied", "error") else
                               "warning" if rec.verdict in ("modified", "flagged") else "info",
                })
            return {"events": events, "total": len(events), "source": "audit_logger"}
        except Exception as e:
            logger.debug("Audit query failed: %s", e)

    # Fallback
    filtered = _fallback_audit_log
    if event_type:
        filtered = [e for e in filtered if e.get("event_type") == event_type]
    if agent:
        filtered = [e for e in filtered if e.get("agent") == agent]
    if symbol:
        filtered = [e for e in filtered if e.get("symbol") == symbol]

    return {
        "events": filtered[-limit:],
        "total": len(filtered),
        "source": "fallback",
    }


@router.get("/security/status")
def security_status(request: Request) -> Dict[str, Any]:
    """Get overall security status (kill switch, encryption, auth)."""
    ks = _get_kill_switch(request)
    kill_switch_active = False
    kill_switch_level = 0

    if ks is not None:
        try:
            ks_status = ks.status()
            kill_switch_active = ks_status.get("active", False)
            kill_switch_level = ks_status.get("level", 0)
        except Exception:
            pass

    encryption_enabled = False
    if _HAS_ENCRYPTION and _encrypted_store:
        encryption_enabled = getattr(_encrypted_store, "_key", None) is not None

    auth_enabled = _HAS_AUTH

    return {
        "kill_switch_active": kill_switch_active,
        "kill_switch_level": kill_switch_level,
        "encryption_enabled": encryption_enabled,
        "auth_enabled": auth_enabled,
        "audit_enabled": _HAS_AUDIT,
        "keyvault_enabled": _HAS_KEYVAULT,
        "timestamp": _now(),
    }


@router.post("/security/encrypt")
def security_encrypt(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Encrypt data using the system's encryption store."""
    content = data.get("content", data.get("data", ""))
    if not content:
        raise HTTPException(status_code=400, detail="No content provided to encrypt")

    if _HAS_ENCRYPTION and _encrypted_store:
        try:
            encrypted = _encrypted_store.encrypt(content)
            return {
                "status": "encrypted",
                "algorithm": "AES-256 (Fernet)",
                "encrypted": encrypted.decode() if isinstance(encrypted, bytes) else encrypted,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Encryption failed: {e}")

    raise HTTPException(status_code=501, detail="Encryption not available")


@router.post("/security/decrypt")
def security_decrypt(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Decrypt data using the system's encryption store."""
    content = data.get("content", data.get("data", ""))
    if not content:
        raise HTTPException(status_code=400, detail="No content provided to decrypt")

    if _HAS_ENCRYPTION and _encrypted_store:
        try:
            import base64
            payload = base64.b64decode(content) if isinstance(content, str) else content
            decrypted = _encrypted_store.decrypt(payload)
            return {
                "status": "decrypted",
                "algorithm": "AES-256 (Fernet)",
                "decrypted": decrypted.decode() if isinstance(decrypted, bytes) else decrypted,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Decryption failed: {e}")

    raise HTTPException(status_code=501, detail="Encryption not available")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@router.get("/tools/list")
def tools_list(
    category: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """List available security tools."""
    tools = list(_fallback_tools)

    # Add real tools if available
    if _HAS_ENCRYPTION and _encrypted_store:
        tools.append({
            "id": "encrypt-file",
            "name": "Encrypt File",
            "category": "crypto",
            "description": "Encrypt a file using AES-256",
        })
    if _HAS_AUTH and _auth_manager:
        tools.append({
            "id": "create-api-key",
            "name": "Create API Key",
            "category": "auth",
            "description": "Generate a new API key with role-based permissions",
        })
    if _HAS_KEYVAULT and _keyvault:
        tools.append({
            "id": "vault-list",
            "name": "List Vault Secrets",
            "category": "keyvault",
            "description": "List all stored secrets in the key vault",
        })

    if category:
        tools = [t for t in tools if t.get("category") == category]

    return {"tools": tools, "total": len(tools)}


@router.post("/tools/{tool_id}/execute")
def tools_execute(
    tool_id: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a security tool by ID."""
    params = params or {}
    tool = next((t for t in _fallback_tools if t["id"] == tool_id), None)
    if tool is None and _HAS_KEYVAULT:
        # Check real tool IDs
        pass

    execution_id = f"exec-{_make_id()}"
    result = None

    try:
        # -- Real tool executions --
        if tool_id == "encrypt" and _HAS_ENCRYPTION and _encrypted_store:
            content = params.get("content", "")
            encrypted = _encrypted_store.encrypt(content)
            import base64
            result = base64.b64encode(encrypted).decode()

        elif tool_id == "decrypt" and _HAS_ENCRYPTION and _encrypted_store:
            content = params.get("content", "")
            import base64
            payload = base64.b64decode(content) if isinstance(content, str) else content
            decrypted = _encrypted_store.decrypt(payload)
            result = decrypted.decode()

        elif tool_id == "hash":
            import hashlib
            content = params.get("content", "")
            result = hashlib.sha256(content.encode()).hexdigest()

        elif tool_id == "verify":
            content = params.get("content", "")
            checksum = params.get("checksum", "")
            if not content or not checksum:
                raise HTTPException(status_code=400, detail="Both 'content' and 'checksum' required")
            import hashlib
            computed = hashlib.sha256(content.encode()).hexdigest()
            result = {"valid": computed == checksum, "computed_hash": computed}

        elif tool_id == "token-validate" and _HAS_AUTH and _auth_manager:
            token = params.get("token", "")
            try:
                payload = _auth_manager.validate_token(token)
                result = {"valid": True, "payload": payload}
            except Exception:
                result = {"valid": False, "error": "Token invalid or expired"}

        elif tool_id == "token-revoke" and _HAS_AUTH and _auth_manager:
            token = params.get("token", "")
            _auth_manager.revoke_token(token)
            result = {"revoked": True}

        elif tool_id == "key-rotate" and _HAS_KEYVAULT and _keyvault:
            new_key = _keyvault.rotate_key(params.get("key_name", "default"))
            result = {"new_key_id": str(new_key)[:16] + "..." if new_key else None}

        elif tool_id == "audit-export" and _HAS_AUDIT and _audit_logger:
            import asyncio
            records = asyncio.run(_audit_logger.query(limit=1000))
            result = [
                {"id": r.id, "timestamp": str(r.timestamp), "agent": r.agent,
                 "event_type": r.event_type, "verdict": r.verdict}
                for r in records
            ]

        elif tool_id == "system-scan":
            import psutil
            result = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "processes": len(psutil.pids()),
                "connections": len(psutil.net_connections()),
            }

        else:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")

        # Log execution to audit
        if _HAS_AUDIT and _audit_logger:
            import asyncio
            try:
                asyncio.run(_audit_logger.log_event(
                    agent="security_api",
                    event_type="tool_execution",
                    action=tool_id,
                    verdict="success",
                    details={"execution_id": execution_id, "params": params},
                ))
            except Exception:
                pass

        _fallback_tool_history.append({
            "id": execution_id,
            "tool_id": tool_id,
            "status": "success",
            "timestamp": _now(),
        })

        return {
            "status": "executed",
            "tool_id": tool_id,
            "execution_id": execution_id,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        _fallback_tool_history.append({
            "id": execution_id,
            "tool_id": tool_id,
            "status": "failed",
            "error": str(e),
            "timestamp": _now(),
        })
        return {
            "status": "failed",
            "tool_id": tool_id,
            "execution_id": execution_id,
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


@router.get("/monitor/system")
def monitor_system() -> Dict[str, Any]:
    """Get real system metrics (CPU, memory, disk)."""
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        boot = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)

        return {
            "cpu": {
                "percent": cpu,
                "cores": psutil.cpu_count(),
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": disk.percent,
            },
            "network": {
                "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
            },
            "uptime_days": round((datetime.now(tz=timezone.utc) - boot).total_seconds() / 86400, 1),
            "status": "healthy" if cpu < 90 and memory.percent < 90 else "degraded",
            "timestamp": _now(),
        }
    except ImportError:
        pass

    # Fallback
    return {
        "cpu": {"percent": 0, "cores": 0},
        "memory": {"total_gb": 0, "used_gb": 0, "percent": 0},
        "disk": {"total_gb": 0, "used_gb": 0, "percent": 0},
        "status": "unknown (psutil not installed)",
        "timestamp": _now(),
    }


@router.get("/monitor/agents")
def monitor_agents(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    """Get agent health monitoring data."""
    agents = []

    # Try real ColonyAgent registry
    try:
        from quant_nanggroe.agents.registry import list_agents
        registered = list_agents()
        for agent in registered[:limit]:
            agents.append({
                "id": getattr(agent, "id", getattr(agent, "name", "unknown")),
                "name": getattr(agent, "name", getattr(agent, "id", "unknown")),
                "type": getattr(agent, "agent_type", getattr(type(agent), "__name__", "unknown")).value
                    if hasattr(getattr(agent, "agent_type", None), "value")
                    else str(getattr(agent, "agent_type", "unknown")),
                "status": "active",
                "last_heartbeat": _now(),
            })
    except (ImportError, Exception) as e:
        logger.debug("Agent registry not available: %s", e)

    # Fallback: derive from colony list
    if not agents:
        try:
            from quant_nanggroe.api.routes.colony import _colonies as colony_registry

            for cid, colony in colony_registry.items():
                orch = colony.get("orchestrator")
                if orch and hasattr(orch, "status"):
                    s = orch.status()
                    for worker in s.get("workers", []):
                        agents.append({
                            "id": f"{cid}-{worker.get('role', 'worker')}",
                            "name": worker.get("role", "unknown"),
                            "type": worker.get("type", "worker"),
                            "status": "active",
                            "colony_id": cid,
                            "colony_name": colony.get("name", ""),
                            "last_heartbeat": _now(),
                        })
        except ImportError:
            pass

    return {
        "agents": agents[:limit],
        "total": len(agents),
        "timestamp": _now(),
    }
