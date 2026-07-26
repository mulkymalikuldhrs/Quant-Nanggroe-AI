"""Backtest walk-forward gate — prevents execution if strategy fails validation."""

import json
import subprocess
import sys

from quant_nanggroe.hedge_fund.utils.config import GATE_FILE, _QNA_DIR, log


def check_gate():
    r = subprocess.run([sys.executable, str(_QNA_DIR / 'backtest_pipeline.py')],
                       capture_output=True, text=True, timeout=120)
    if '"pass": true' in r.stdout or '"pass": true' in r.stderr:
        return True
    if GATE_FILE.exists():
        data = json.loads(GATE_FILE.read_text())
        return data.get("pass", False)
    return False
