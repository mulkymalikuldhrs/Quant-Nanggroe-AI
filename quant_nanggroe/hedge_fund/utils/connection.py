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
    r = [False]
    def t(): r[0] = mt5.initialize()
    th = threading.Thread(target=t); th.daemon = True; th.start(); th.join(timeout)
    if th.is_alive(): return False
    return r[0]


def ensure_terminal():
    subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True)
    time.sleep(2)
    _pwd = CREDS["password"]() if callable(CREDS["password"]) else CREDS["password"]
    subprocess.Popen([TERMINAL, f"/login:{CREDS['login']}", f"/password:{_pwd}", f"/server:{CREDS['server']}"])
    time.sleep(20)
    return mt5.initialize()
