#!/usr/bin/env python3
"""QNA Hedge Fund Production Runner — no_agent cron script.
Runs hedge_fund.py using Hermes venv Python (numpy/pandas compatible).
Exits 0 on success, 1 on failure.

Usage: python qna-production-runner.py [mode=symbol] [symbol=EURUSD]
"""

import sys, os, subprocess, json
from pathlib import Path

VENV_PYTHON = Path("C:/Users/Hi/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")
TRADING_DIR = Path("E:/trading")

def run_hedge_fund(mode="paper", symbol="EURUSD"):
    env = os.environ.copy()
    env["PAPER_TRADE"] = "true" if mode == "paper" else "false"
    env["PYTHONPATH"] = str(TRADING_DIR)
    if "MT5_PASSWORD" not in env and mode == "paper":
        env["MT5_PASSWORD"] = "paper_mode_dummy"

    cmd = [
        str(VENV_PYTHON), "-c", f"""
import sys
sys.path.insert(0, r'{TRADING_DIR}')
from hedge_fund import run_once
run_once(target_symbol='{symbol}')
"""
    ]
    timeout = 180 if mode == "paper" else 90
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    return result

def main():
    mode = "paper"
    symbol = "EURUSD"

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if "=" in arg:
            mode, symbol = arg.split("=", 1)
        elif arg in ("paper", "live"):
            mode = arg
        else:
            symbol = arg
    if len(sys.argv) > 2:
        symbol = sys.argv[2]

    print(f"🤖 QNA Production Runner — mode={mode} symbol={symbol}")
    r = run_hedge_fund(mode, symbol)
    for line in r.stdout.split("\n"):
        if line.strip():
            print(line)
    if r.stderr:
        err_lines = [l for l in r.stderr.split("\n") if "Traceback" in l or "Error" in l]
        for l in err_lines:
            print(f"ERR: {l}")
    print(f"Exit: {r.returncode}")
    return 0 if r.returncode == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
