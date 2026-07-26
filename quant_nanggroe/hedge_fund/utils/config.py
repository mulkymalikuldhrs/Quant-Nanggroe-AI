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
    class _MT5Mock:
        TIMEFRAME_M1=1; TIMEFRAME_M5=5; TIMEFRAME_M15=15; TIMEFRAME_M30=30
        TIMEFRAME_H1=60; TIMEFRAME_H4=240; TIMEFRAME_D1=1440; TIMEFRAME_W1=10080
        TRADE_ACTION_DEAL=1; TRADE_ACTION_SLTP=5
        ORDER_TYPE_BUY=0; ORDER_TYPE_SELL=1; ORDER_TIME_GTC=0; ORDER_FILLING_IOC=2
        def initialize(*a,**kw): return False
        def shutdown(*a,**kw): pass
        def login(*a,**kw): return False
        def symbol_info_tick(*a,**kw): return None
        def account_info(*a,**kw): return None
        def positions_get(*a,**kw): return ()
        def order_send(*a,**kw): return None
        def copy_rates_from_pos(*a,**kw): return None
    mt5 = _MT5Mock()
    MT5_AVAILABLE = False
    if not os.environ.get("PAPER_TRADE"):
        os.environ["PAPER_TRADE"] = "true"

SRC = _HF_DIR
LOG_FILE = _DATA_DIR / 'trades.csv'
VOTE_LOG = _DATA_DIR / 'votes.csv'
PAPER_LOG = _DATA_DIR / 'paper_trades.csv'
GATE_FILE = _DATA_DIR / 'gate_status.json'
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"

CREDS = {
    "login": int(os.environ.get("MT5_LOGIN", "0")),
    "password": lambda: os.environ.get("MT5_PASSWORD"),
    "server": "ValetaxIntl-Live2",
}

PAPER_TRADE = os.environ.get("PAPER_TRADE", "true").lower() in ("1", "true", "yes")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('hf')
