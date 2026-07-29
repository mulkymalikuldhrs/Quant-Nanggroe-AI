"""MT5 terminal connection and initialization utilities."""

import subprocess
import threading
import time

from quant_nanggroe.hedge_fund.utils.config import (
    CREDS,
    TERMINAL,
    mt5,
)

_MT5_CREDS_CHECKED = False


def connect(timeout=15):
    """Connect to MT5 terminal.

    1st try: bare initialize() — works if terminal already running and authed.
    2nd try: with CREDS — starts terminal or re-auths if logged out.
    """
    r = [False]
    def _try(**kw):
        r[0] = mt5.initialize(**kw)
    kw = {"timeout": min(timeout * 1000, 15000)}
    th = threading.Thread(target=_try, kwargs=kw); th.daemon = True; th.start(); th.join(timeout)
    if th.is_alive(): return False
    if r[0]:
        return True
    # terminal not authed — try with credentials
    _pwd = CREDS["password"]() if callable(CREDS["password"]) else CREDS["password"]
    if not _pwd:
        return False
    kw2 = {"login": CREDS["login"], "password": _pwd, "server": CREDS["server"], "timeout": 15000}
    th2 = threading.Thread(target=_try, kwargs=kw2); th2.daemon = True; th2.start(); th2.join(timeout)
    if th2.is_alive(): return False
    return r[0]


def ensure_terminal():
    # Try connecting first — don't kill existing terminal
    if mt5.initialize():
        return True
    # Only kill if MT5 is genuinely stuck (e.g. hanging from prev crash)
    subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True)
    time.sleep(2)
    _pwd = CREDS["password"]() if callable(CREDS["password"]) else CREDS["password"]
    subprocess.Popen([TERMINAL, f"/login:{CREDS['login']}", f"/password:{_pwd}", f"/server:{CREDS['server']}"])
    time.sleep(20)
    return mt5.initialize()
