"""EvolutionConfig — load/save evolution configuration per account from JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


_DEFAULT_PATH = Path("data/evolution_config.json")

_DEFAULTS: dict[str, Any] = {
    "threshold_trades": 20,
    "schedule_days": 7,
    "drawdown_trigger": 5.0,
    "consecutive_loss": 3,
    "min_sharpe": 0.5,
    "min_win_rate": 0.40,
    "max_drawdown_allowed": 15.0,
    "evolve_on_schedule": True,
    "evolve_on_drawdown": True,
    "evolve_on_loss_streak": True,
    "auto_disable": True,
    "update_weights": True,
}


class EvolutionConfig:
    """Per-account evolution configuration persisted as JSON."""

    def __init__(self, path: str | Path = "") -> None:
        self._path = Path(path) if path else _DEFAULT_PATH
        self._data: dict[str, Any] = {}
        self._load()

    # ── Load / Save ──────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._data = {**_DEFAULTS, **raw}
            except (json.JSONDecodeError, OSError):
                self._data = dict(_DEFAULTS)
        else:
            self._data = dict(_DEFAULTS)
            self.save()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, default=str), encoding="utf-8"
        )

    # ── Per-account config ───────────────────────────────────────────

    def get_account_config(self, account: str = "default") -> dict[str, Any]:
        """Return evolution config for a specific account.

        Falls back to global defaults if account not found.
        """
        accounts: dict[str, dict[str, Any]] = self._data.get("accounts", {})
        return {**self._data.get("global", {}), **accounts.get(account, {})}

    def set_account_config(
        self, account: str, config: dict[str, Any]
    ) -> None:
        """Set evolution config for a specific account."""
        accounts: dict[str, dict[str, Any]] = self._data.setdefault("accounts", {})
        accounts[account] = config
        self.save()

    def get_global(self) -> dict[str, Any]:
        """Return global evolution defaults."""
        return dict(self._data.get("global", _DEFAULTS))

    def set_global(self, config: dict[str, Any]) -> None:
        """Set global evolution defaults."""
        self._data["global"] = config
        self.save()

    # ── Direct key access ────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._data)
