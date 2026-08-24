"""System configuration API — read & update runtime settings from UI.

Exposes /api/config (GET) and /api/config/update (PATCH) so the Next.js
Dashboard Settings page can read and modify system config without manual
file editing.

Ponytail: thin wrapper around config.yaml — single source of truth on disk.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])

# ── Config file location ────────────────────────────────────────────

CONFIG_PATH = Path(os.environ.get(
    "QNA_CONFIG_PATH",
    str(Path(__file__).resolve().parent.parent.parent.parent / "config.yaml"),
))


class SystemConfig(BaseModel):
    """System configuration exposed to UI."""
    model_config = ConfigDict(validate_assignment=True)
    # Trading
    symbols: list[str] = Field(default_factory=lambda: ["EURUSD", "XAUUSD", "BTC-USD"])
    max_position_pct: float = 0.02
    max_daily_loss_pct: float = 0.01
    max_weekly_loss_pct: float = 0.03
    max_drawdown_pct: float = 0.10
    max_daily_trades: int = 20

    # Strategy
    active_strategies: list[str] = Field(default_factory=lambda: ["smc", "wyckoff", "mean_reversion"])
    strategy_weights: dict[str, float] = Field(default_factory=dict)

    # Execution
    cycle_interval_seconds: int = 900
    algo_execution: str = "twap"
    slice_count: int = 5

    # Providers
    model_provider: str = "9router"
    model_name: str = "nvidia/minimaxai/minimax-m2.7"

    # Display
    theme: str = "dark"
    language: str = "en"

    class Config:
        extra = "allow"


class ConfigUpdate(BaseModel):
    """Partial config update (PATCH style)."""
    symbols: Optional[list[str]] = None
    max_position_pct: Optional[float] = None
    max_daily_loss_pct: Optional[float] = None
    max_weekly_loss_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    max_daily_trades: Optional[int] = None
    active_strategies: Optional[list[str]] = None
    strategy_weights: Optional[dict[str, float]] = None
    cycle_interval_seconds: Optional[int] = None
    algo_execution: Optional[str] = None
    slice_count: Optional[int] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────


def _load_config() -> dict[str, Any]:
    """Load config from YAML or JSON (with YAML fallback)."""
    if not CONFIG_PATH.exists():
        return SystemConfig().model_dump()

    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except ImportError:
        # No PyYAML — try JSON
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

    # Flatten nested structure for frontend consumption
    flat: dict[str, Any] = {}
    trading = raw.get("trading", {})
    flat["symbols"] = trading.get("symbols", ["EURUSD", "XAUUSD", "BTC-USD"])
    flat["max_position_pct"] = trading.get("max_position_pct", 0.02)
    flat["max_daily_loss_pct"] = trading.get("max_daily_loss_pct", 0.01)
    flat["max_weekly_loss_pct"] = trading.get("max_weekly_loss_pct", 0.03)
    flat["max_drawdown_pct"] = trading.get("max_drawdown_pct", 0.10)
    flat["max_daily_trades"] = trading.get("max_daily_trades", 20)

    strategy = raw.get("strategy", {})
    flat["active_strategies"] = strategy.get("active", ["smc", "wyckoff", "mean_reversion"])
    flat["strategy_weights"] = strategy.get("weights", {})

    execution = raw.get("execution", {})
    flat["cycle_interval_seconds"] = execution.get("cycle_interval_seconds", 900)
    flat["algo_execution"] = execution.get("algo", "twap")
    flat["slice_count"] = execution.get("slice_count", 5)

    model = raw.get("model", {})
    flat["model_provider"] = model.get("provider", "9router")
    flat["model_name"] = model.get("default", "nvidia/minimaxai/minimax-m2.7")

    display = raw.get("display", {})
    flat["theme"] = display.get("theme", "dark")
    flat["language"] = display.get("language", "en")

    return flat


def _save_config(updates: dict[str, Any]) -> None:
    """Save updated config back to YAML."""
    if not CONFIG_PATH.parent.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    current = _load_config()
    current.update({k: v for k, v in updates.items() if v is not None})

    try:
        import yaml
        # Re-nest for YAML storage
        nested = {
            "trading": {
                "symbols": current["symbols"],
                "max_position_pct": current["max_position_pct"],
                "max_daily_loss_pct": current["max_daily_loss_pct"],
                "max_weekly_loss_pct": current["max_weekly_loss_pct"],
                "max_drawdown_pct": current["max_drawdown_pct"],
                "max_daily_trades": current["max_daily_trades"],
            },
            "strategy": {
                "active": current["active_strategies"],
                "weights": current["strategy_weights"],
            },
            "execution": {
                "cycle_interval_seconds": current["cycle_interval_seconds"],
                "algo": current["algo_execution"],
                "slice_count": current["slice_count"],
            },
            "model": {
                "default": current["model_name"],
                "provider": current["model_provider"],
            },
            "display": {
                "theme": current["theme"],
                "language": current["language"],
            },
        }
        CONFIG_PATH.write_text(
            yaml.dump(nested, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except ImportError:
        # Fallback to JSON
        CONFIG_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")

    logger.info("Config saved to %s", CONFIG_PATH)


# ── Routes ───────────────────────────────────────────────────────────


@router.get("")
async def get_config() -> dict[str, Any]:
    """GET /api/config — return current system configuration."""
    return _load_config()


@router.get("/schema")
async def get_config_schema() -> dict[str, Any]:
    """GET /api/config/schema — return config schema for form generation."""
    return SystemConfig.model_json_schema()


@router.patch("")
async def update_config(body: ConfigUpdate) -> dict[str, Any]:
    """PATCH /api/config — partial update of system configuration."""
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(400, "No config fields provided")
    _save_config(updates)
    return _load_config()


@router.get("/validate")
async def validate_config() -> dict[str, Any]:
    """GET /api/config/validate — validate current config."""
    config = _load_config()
    errors = []
    if config.get("max_daily_loss_pct", 0) >= 1.0:
        errors.append("max_daily_loss_pct must be < 1.0 (fraction, not %)")
    if config.get("max_drawdown_pct", 0) >= 1.0:
        errors.append("max_drawdown_pct must be < 1.0")
    if config.get("cycle_interval_seconds", 900) < 60:
        errors.append("cycle_interval_seconds must be >= 60 (1 minute)")
    if not config.get("active_strategies"):
        errors.append("active_strategies cannot be empty")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "config": config,
    }
