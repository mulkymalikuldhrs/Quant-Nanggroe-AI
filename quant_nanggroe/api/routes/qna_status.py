"""QNA Status API route — kill-switch, guard config, ledger, version."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/qna-status")
async def qna_status() -> dict:
    """Return QNA system status: version, kill switch state, and module flags.

    Never 500s — every sub-block is wrapped in try/except so a transient
    failure in one area (e.g. unimportable kill_switch) doesn't break the
    whole response.
    """
    result: dict = {
        "version": "",
        "kill_switch": {"active": False, "file_path": ""},
        "guard_config": {
            "allowed_symbols": [],
            "blocked_symbols": [],
            "cooldown": 0,
            "max_position_pct": 0,
            "max_notional": 0,
        },
        "graph_queue": [],
        "last_ledger": "",
        "module_flags": {},
        "timestamp": datetime.utcnow().isoformat(),
    }

    # ── Version ───────────────────────────────────────────────────────
    try:
        from quant_nanggroe import __version__
        result["version"] = __version__
    except Exception as exc:
        logger.warning("qna_status_version_failed: %s", exc)

    # ── Kill switch ───────────────────────────────────────────────────
    try:
        from quant_nanggroe.engine.risk.kill_switch import KillSwitch, _ks_store_path, configure_kill_switch_file
        configure_kill_switch_file()
        ks = KillSwitch()
        ks_status = ks.status()
        result["kill_switch"] = {
            "active": ks_status.get("is_active", False),
            "current_level": ks_status.get("current_level", "none"),
            "status": ks_status.get("status", "inactive"),
            "file_path": str(_ks_store_path() or ""),
        }
    except Exception as exc:
        logger.warning("qna_status_kill_switch_failed: %s", exc)

    # ── Module flags ──────────────────────────────────────────────────
    try:
        from quant_nanggroe.agents import __all__ as agent_modules
        result["module_flags"]["available_agents"] = agent_modules
    except Exception as exc:
        logger.warning("qna_status_module_flags_failed: %s", exc)

    return result
