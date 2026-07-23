"""Hedge Fund QNA — Production Runner menggunakan Hermes venv python.

Gunakan ini untuk menjalankan hedge fund dengan numpy/pandas/yfinance yang kompatibel.
"""
import sys, os, subprocess, json
from pathlib import Path

VENV_PYTHON = Path("C:/Users/Hi/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")
TRADING_DIR = Path("E:/trading")

def run_hedge_fund(mode="paper", symbol="EURUSD"):
    """Run hedge fund in paper or live mode"""
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
    timeout = 180 if mode == "paper" else 60
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    return result

def run_backtest(strategy_name="WyckoffStrategy"):
    """Run backtest using venv python"""
    cmd = [
        str(VENV_PYTHON), str(TRADING_DIR / "backtest_pipeline.py"),
        "--strategy", strategy_name
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "paper"
    symbol = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
    
    print(f"Hedge Fund Runner — mode={mode} symbol={symbol}")
    r = run_hedge_fund(mode, symbol)
    for line in r.stdout.split("\n"):
        print(line)
    if r.stderr:
        for line in r.stderr.split("\n"):
            if "Traceback" in line or "Error" in line:
                print(f"ERR: {line}")
    print(f"Exit: {r.returncode}")
