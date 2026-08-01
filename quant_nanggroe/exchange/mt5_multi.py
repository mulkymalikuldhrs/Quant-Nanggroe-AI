"""Multi-account MetaTrader 5 orchestration (Blocker C6).

Why multi-process
-----------------
The official ``MetaTrader5`` Python package is a **process-global singleton**:
``mt5.initialize()`` / ``mt5.login()`` bind the *entire process* to exactly one
terminal + account. A second ``login()`` in the same process silently switches
the active account, so two :class:`MT5Exchange` instances living in one process
would race and corrupt each other's state.

To run N accounts concurrently we therefore need **N OS processes**, one
:class:`MT5Exchange` per process, each bound to its own account. This module
provides that isolation:

* :class:`MT5AccountConfig` — a single account entry parsed from
  ``settings.mt5_accounts`` (JSON list).
* :func:`load_accounts` — parse + validate the JSON config into configs.
* :class:`_MT5Worker` — a child ``multiprocessing.Process`` that owns exactly
  one :class:`MT5Exchange`, driving it via a request/response command queue.
* :class:`MT5MultiAccountManager` — the parent-side facade. Spawns one worker
  per account, routes commands by account login, and fans out/in operations.

Design notes
------------
* Fail-closed: a worker that cannot connect stays ``ERROR``; the manager never
  silently degrades to a single shared connection.
* Each worker runs its own asyncio loop internally (MT5Exchange is async) but
  exposes a synchronous command protocol across the process boundary.
* The manager is intentionally transport-agnostic: commands are plain dicts so
  the same protocol can later be swapped to sockets/ZeroMQ for remote workers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing as mp
import os
import queue
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quant_nanggroe.exchange.base import ExchangeConfig, ExchangeState
from quant_nanggroe.exchange.mt5_broker import MT5Exchange

logger = logging.getLogger(__name__)

# Command timeout (seconds) for a single request round-trip to a worker.
_CMD_TIMEOUT = 90.0
# Grace period when shutting a worker down.
_SHUTDOWN_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Account configuration
# ---------------------------------------------------------------------------

@dataclass
class MT5AccountConfig:
    """A single MT5 account entry (one worker process per instance)."""

    login: int
    password: str
    server: str
    role: str = "primary"  # "primary" | "failover"
    path: Optional[str] = None  # optional per-account terminal path
    options: Dict[str, Any] = field(default_factory=dict)

    def to_exchange_config(self) -> ExchangeConfig:
        """Build the :class:`ExchangeConfig` this account's worker will use."""
        opts: Dict[str, Any] = {"server": self.server}
        if self.path:
            opts["path"] = self.path
        opts.update(self.options)
        return ExchangeConfig(
            exchange_id=f"mt5:{self.login}",
            api_key=str(self.login),
            api_secret=self.password,
            options=opts,
        )


def load_accounts(mt5_accounts_json: Optional[str]) -> List[MT5AccountConfig]:
    """Parse ``settings.mt5_accounts`` (a JSON list) into account configs.

    Each element must be an object with ``login``, ``password`` and ``server``.
    ``role`` and ``path`` are optional. Raises ``ValueError`` on malformed
    input (fail-closed — do not start trading against a mis-parsed config).
    """
    if not mt5_accounts_json:
        return []
    try:
        raw = json.loads(mt5_accounts_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"mt5_accounts is not valid JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("mt5_accounts must be a JSON list of account objects")

    accounts: List[MT5AccountConfig] = []
    seen: set[int] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"mt5_accounts[{i}] must be an object")
        try:
            login = int(item["login"])
            password = str(item["password"])
            server = str(item["server"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(
                f"mt5_accounts[{i}] missing/invalid login|password|server: {exc}"
            ) from exc
        if login in seen:
            raise ValueError(f"mt5_accounts: duplicate login {login}")
        seen.add(login)
        accounts.append(
            MT5AccountConfig(
                login=login,
                password=password,
                server=server,
                role=str(item.get("role", "primary")),
                path=item.get("path"),
                options=item.get("options", {}) or {},
            )
        )
    return accounts


# ---------------------------------------------------------------------------
# Worker process — owns exactly one MT5Exchange
# ---------------------------------------------------------------------------

def _worker_main(
    exchange_config_json: str,
    cmd_q: "mp.Queue[Dict[str, Any]]",
    res_q: "mp.Queue[Dict[str, Any]]",
) -> None:
    """Entry point run inside a child process.

    Owns one :class:`MT5Exchange`, drives a private asyncio loop, and services
    commands from ``cmd_q``, replying on ``res_q``. Exactly one MT5 binding
    lives in this process, so no cross-account interference is possible.
    """
    logging.basicConfig(level=os.getenv("QNAI_LOG_LEVEL", "INFO"))
    log = logging.getLogger(f"mt5.worker.{os.getpid()}")

    config = ExchangeConfig.model_validate_json(exchange_config_json)
    exchange = MT5Exchange(config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _reply(req_id: Any, ok: bool, payload: Any) -> None:
        res_q.put({"id": req_id, "ok": ok, "result": payload})

    try:
        while True:
            try:
                cmd = cmd_q.get(timeout=1.0)
            except queue.Empty:
                continue

            action = cmd.get("action")
            req_id = cmd.get("id")

            if action == "shutdown":
                try:
                    loop.run_until_complete(exchange.disconnect())
                except Exception as exc:  # noqa: BLE001
                    log.warning("worker disconnect error: %s", exc)
                _reply(req_id, True, {"state": ExchangeState.DISCONNECTED.value})
                break

            try:
                method = getattr(exchange, action, None)
                if method is None:
                    _reply(req_id, False, f"unknown action: {action}")
                    continue
                args = cmd.get("args", [])
                kwargs = cmd.get("kwargs", {})
                res = method(*args, **kwargs)
                if asyncio.iscoroutine(res):
                    res = loop.run_until_complete(res)
                # Pydantic models -> dicts for pickling safety across procs.
                if hasattr(res, "model_dump"):
                    res = res.model_dump()
                elif isinstance(res, list):
                    res = [r.model_dump() if hasattr(r, "model_dump") else r for r in res]
                _reply(req_id, True, res)
            except Exception as exc:  # noqa: BLE001
                log.exception("worker action %s failed", action)
                _reply(req_id, False, f"{type(exc).__name__}: {exc}")
    finally:
        try:
            loop.close()
        except Exception:  # noqa: BLE001
            pass


class _MT5Worker:
    """Parent-side handle to one child worker process."""

    def __init__(self, account: MT5AccountConfig) -> None:
        self.account = account
        self._cmd_q: "mp.Queue[Dict[str, Any]]" = mp.Queue()
        self._res_q: "mp.Queue[Dict[str, Any]]" = mp.Queue()
        self._proc: Optional[mp.Process] = None
        self._req_counter = 0

    @property
    def login(self) -> int:
        return self.account.login

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.is_alive()

    def start(self) -> None:
        if self.is_alive:
            return
        cfg_json = self.account.to_exchange_config().model_dump_json()
        self._proc = mp.Process(
            target=_worker_main,
            args=(cfg_json, self._cmd_q, self._res_q),
            name=f"mt5-worker-{self.login}",
            daemon=True,
        )
        self._proc.start()
        logger.info("MT5 worker started: login=%s pid=%s", self.login, self._proc.pid)

    def call(self, action: str, *args: Any, timeout: float = _CMD_TIMEOUT, **kwargs: Any) -> Any:
        """Send a command to the worker and block for the reply."""
        if not self.is_alive:
            raise RuntimeError(f"MT5 worker {self.login} is not running")
        self._req_counter += 1
        req_id = self._req_counter
        self._cmd_q.put({"id": req_id, "action": action, "args": list(args), "kwargs": kwargs})
        try:
            reply = self._res_q.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(
                f"MT5 worker {self.login} timed out on action '{action}'"
            ) from exc
        if reply.get("id") != req_id:
            # Out-of-order reply — protocol is strictly request/response, so
            # this indicates a desync; surface it rather than returning stale data.
            raise RuntimeError(
                f"MT5 worker {self.login} reply id mismatch "
                f"(want {req_id}, got {reply.get('id')})"
            )
        if not reply.get("ok"):
            raise RuntimeError(f"MT5 worker {self.login} action '{action}': {reply.get('result')}")
        return reply.get("result")

    def stop(self) -> None:
        if not self.is_alive:
            return
        try:
            self._cmd_q.put({"id": -1, "action": "shutdown"})
            self._proc.join(timeout=_SHUTDOWN_TIMEOUT)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("MT5 worker %s graceful stop failed: %s", self.login, exc)
        finally:
            if self.is_alive:
                logger.warning("MT5 worker %s did not exit — terminating", self.login)
                self._proc.terminate()  # type: ignore[union-attr]
                self._proc.join(timeout=5.0)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Manager — one worker per account
# ---------------------------------------------------------------------------

class MT5MultiAccountManager:
    """Spawn and coordinate one MT5 worker process per configured account.

    Usage
    -----
    .. code-block:: python

        mgr = MT5MultiAccountManager.from_settings(settings)
        mgr.start_all()
        mgr.connect_all()
        info = mgr.call(login, "get_account_info")
        mgr.stop_all()
    """

    def __init__(self, accounts: List[MT5AccountConfig]) -> None:
        self._workers: Dict[int, _MT5Worker] = {
            acc.login: _MT5Worker(acc) for acc in accounts
        }

    # ----- construction -----

    @classmethod
    def from_settings(cls, settings: Any) -> "MT5MultiAccountManager":
        """Build from a settings object exposing ``mt5_accounts`` (JSON str)."""
        accounts = load_accounts(getattr(settings, "mt5_accounts", None))
        return cls(accounts)

    # ----- introspection -----

    @property
    def logins(self) -> List[int]:
        return list(self._workers)

    def primary_logins(self) -> List[int]:
        return [w.login for w in self._workers.values() if w.account.role == "primary"]

    def failover_logins(self) -> List[int]:
        return [w.login for w in self._workers.values() if w.account.role == "failover"]

    def worker(self, login: int) -> _MT5Worker:
        try:
            return self._workers[login]
        except KeyError as exc:
            raise KeyError(f"No MT5 worker for login {login}") from exc

    # ----- lifecycle -----

    def start_all(self) -> None:
        for w in self._workers.values():
            w.start()

    def connect_all(self) -> Dict[int, bool]:
        """Connect every worker's MT5Exchange. Returns {login: connected?}."""
        out: Dict[int, bool] = {}
        for login, w in self._workers.items():
            try:
                out[login] = bool(w.call("connect"))
            except Exception as exc:  # noqa: BLE001
                logger.error("MT5 worker %s connect failed: %s", login, exc)
                out[login] = False
        return out

    def stop_all(self) -> None:
        for w in self._workers.values():
            w.stop()

    # ----- routed operations -----

    def call(self, login: int, action: str, *args: Any, **kwargs: Any) -> Any:
        """Route a single command to the worker owning ``login``."""
        return self.worker(login).call(action, *args, **kwargs)

    def broadcast(self, action: str, *args: Any, **kwargs: Any) -> Dict[int, Any]:
        """Run ``action`` on every worker; returns {login: result_or_exception}."""
        out: Dict[int, Any] = {}
        for login, w in self._workers.items():
            try:
                out[login] = w.call(action, *args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                out[login] = exc
        return out

    def __enter__(self) -> "MT5MultiAccountManager":
        self.start_all()
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.stop_all()

    def __repr__(self) -> str:
        return f"MT5MultiAccountManager(accounts={self.logins})"


__all__ = [
    "MT5AccountConfig",
    "MT5MultiAccountManager",
    "load_accounts",
]
