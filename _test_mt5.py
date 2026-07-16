"""Quick MT5 Valetax connection test — reads QNAI_MT5_ACCOUNTS from env."""
import MetaTrader5 as mt5
import json, os, sys

raw = os.environ.get("QNAI_MT5_ACCOUNTS", "")
if not raw:
    # Try the .venv's python-dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
        raw = os.environ.get("QNAI_MT5_ACCOUNTS", "")
    except ImportError:
        print("ERROR: QNAI_MT5_ACCOUNTS not set and dotenv unavailable")
        sys.exit(1)

if not raw:
    print("ERROR: QNAI_MT5_ACCOUNTS not set")
    sys.exit(1)

acc = json.loads(raw)[0]
print(f"Connecting to: {acc['server']} login: {acc['login']}")

if not mt5.initialize(login=acc["login"], password=acc["password"], server=acc["server"]):
    err = mt5.last_error()
    print(f"MT5 initialize FAILED: {err}")
    sys.exit(1)

print("MT5 CONNECTED OK")
info = mt5.account_info()
if info:
    print(f"Account: {info.login} | Balance: {info.balance} | Equity: {info.equity} | Leverage: 1:{info.leverage}")
else:
    print("account_info() returned None")
mt5.shutdown()
print("DONE")
