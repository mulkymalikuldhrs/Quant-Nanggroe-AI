"""Module-level constants, paths, credential config, and logging setup."""

import logging
import os
from pathlib import Path

_HF_DIR = Path(__file__).resolve().parent.parent
_QNA_DIR = _HF_DIR.parent
_DATA_DIR = _QNA_DIR / "data"
os.makedirs(_DATA_DIR, exist_ok=True)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

SRC = _HF_DIR
LOG_FILE = _DATA_DIR / 'trades.csv'
VOTE_LOG = _DATA_DIR / 'votes.csv'
PAPER_LOG = _DATA_DIR / 'paper_trades.csv'
GATE_FILE = _DATA_DIR / 'gate_status.json'
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"

CREDS = {
    "login": int(os.environ.get("MT5_LOGIN") or os.environ.get("QNA_MT5_LOGIN", "0")),
    "password": lambda: os.environ.get("MT5_PASSWORD") or os.environ.get("QNA_MT5_PASSWORD"),
    "server": os.environ.get("MT5_SERVER") or os.environ.get("QNA_MT5_SERVER", "ValetaxIntl-Live2"),
}

_default_paper = "false" if MT5_AVAILABLE else "true"
PAPER_TRADE = os.environ.get("PAPER_TRADE", _default_paper).lower() in ("1", "true", "yes")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('hf')
