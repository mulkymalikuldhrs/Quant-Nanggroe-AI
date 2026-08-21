"""Account Ledger — tracks all MT5 accounts that have ever connected."""

import json
import os
from datetime import datetime, timezone

LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "account_ledger.json",
)


def record_account(login: int, server: str, name: str = ""):
    """Record an account that connected. Updates last_seen timestamp."""
    ledger = load_ledger()
    key = str(login)
    now = datetime.now(timezone.utc).isoformat()
    if key not in ledger:
        ledger[key] = {
            "login": login,
            "server": server,
            "name": name,
            "first_seen": now,
            "trades": 0,
        }
    ledger[key]["last_seen"] = now
    if server:
        ledger[key]["server"] = server
    if name:
        ledger[key]["name"] = name
    _save_ledger(ledger)


def increment_trade_count(login: int):
    """Increment the trade count for an account."""
    ledger = load_ledger()
    key = str(login)
    if key in ledger:
        ledger[key]["trades"] = ledger[key].get("trades", 0) + 1
        ledger[key]["last_seen"] = datetime.now(timezone.utc).isoformat()
        _save_ledger(ledger)


def get_all_accounts() -> list:
    """Return all accounts that have ever connected."""
    return list(load_ledger().values())


def load_ledger() -> dict:
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_ledger(data: dict):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
