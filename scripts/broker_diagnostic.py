"""MT5 Broker Diagnostic — troubleshoot retcode=10017 (Trade disabled).

Run this script to diagnose why EA trading is blocked.
It tests multiple scenarios and provides actionable recommendations.

Usage:
    set PYTHONPATH= && C:\Python314\python.exe scripts\broker_diagnostic.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# ── Env setup ──
os.environ.pop("PYTHONPATH", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(".env")

import MetaTrader5 as mt5

# ── Constants ──
LOGIN = int(os.getenv("MT5_LOGIN", "0"))
PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "")


def banner(text: str) -> None:
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check(text: str, ok: bool) -> None:
    mark = "[OK]" if ok else "[FAIL]"
    print(f"  {mark} {text}")


def note(text: str) -> None:
    print(f"  ... {text}")


def run_diagnostics() -> dict:
    results = {}

    banner("MT5 CONNECTION")
    # Try attaching to already-logged-in terminal first (same as mt5_broker.py)
    term_path = os.getenv("MT5_TERMINAL_PATH",
                          r"C:\Program Files\MetaTrader 5\terminal64.exe")
    init_ok = mt5.initialize(path=term_path, timeout=15000)
    if not init_ok:
        init_ok = mt5.initialize()
    if not init_ok:
        print(f"  [FAIL] initialize() failed: {mt5.last_error()}")
        return results

    # Check if already logged in
    acct = mt5.account_info()
    if acct is None:
        # Not logged in — try credential login
        login_ok = mt5.login(LOGIN, PASSWORD, SERVER)
        if not login_ok:
            print(f"  [FAIL] login() failed: {mt5.last_error()}")
            mt5.shutdown()
            return results
        acct = mt5.account_info()

    if acct:
        acc = acct
        check(f"Connected to {acc.server}", True)
        check(f"Account: {acc.login} ({acc.name})", True)
        check(f"Balance: ${acc.balance:.2f}", True)
        check(f"Equity: ${acc.equity:.2f}", True)
        check(f"Leverage: 1:{acc.leverage}", True)
        check(f"Trade mode: {acc.trade_mode} ({'ENABLED' if acc.trade_mode == 0 else 'DISABLED'})", acc.trade_mode == 0)
        results["trade_mode"] = acc.trade_mode
        results["balance"] = acc.balance
        results["leverage"] = acc.leverage

    banner("TERMINAL SETTINGS")
    # Check if algo trading is enabled in terminal
    terminal_info = mt5.terminal_info()
    if terminal_info:
        check(f"Algo trading enabled: {terminal_info.trade_allowed}", terminal_info.trade_allowed)
        check(f"Connected: {terminal_info.connected}", terminal_info.connected)
        check(f"Build: {terminal_info.build}", True)
        results["algo_trading"] = terminal_info.trade_allowed
        results["build"] = terminal_info.build

    banner("SYMBOL CHECK (tradable symbols)")
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD", "USDCHF", "XAUUSD"]
    tradeable = []
    for sym in symbols:
        si = mt5.symbol_info(sym)
        if si:
            mode = si.trade_mode
            visible = si.visible
            mode_str = {0: "NORMAL", 1: "LONG_ONLY", 2: "SHORT_ONLY",
                       3: "CLOSE_ONLY", 4: "DISABLED"}.get(mode, f"UNKNOWN({mode})")
            is_tradeable = mode == 0
            check(f"{sym}: trade_mode={mode} ({mode_str}), visible={visible}, "
                  f"vol={si.volume_min}-{si.volume_max}", is_tradeable)
            if is_tradeable:
                tradeable.append(sym)
        else:
            check(f"{sym}: NOT FOUND", False)

    results["tradeable_symbols"] = tradeable

    banner("ORDER TEST — Market Order (IOC)")
    test_symbol = tradeable[0] if tradeable else "EURUSD"
    si = mt5.symbol_info(test_symbol)
    if si and not si.visible:
        mt5.symbol_select(test_symbol, True)

    tick = mt5.symbol_info_tick(test_symbol)
    if tick:
        note(f"Tick: bid={tick.bid}, ask={tick.ask}")
        # Try IOC
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": test_symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "deviation": 10,
            "magic": 999999,
            "comment": "DIAG-IOC",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(req)
        if result:
            check(f"IOC order: retcode={result.retcode}, comment={result.comment}", result.retcode == 0)
            note(f"  Order: {result.order}, Deal: {result.deal}")
            results["ioc_retcode"] = result.retcode
            results["ioc_comment"] = result.comment
        else:
            check("IOC order: returned None", False)
            note(f"  Error: {mt5.last_error()}")

    banner("ORDER TEST — Market Order (FOK)")
    if tick:
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": test_symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "deviation": 10,
            "magic": 999999,
            "comment": "DIAG-FOK",
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        result = mt5.order_send(req)
        if result:
            check(f"FOK order: retcode={result.retcode}, comment={result.comment}", result.retcode == 0)
            results["fok_retcode"] = result.retcode
        else:
            check("FOK order: returned None", False)

    banner("ORDER TEST — Pending LIMIT Order")
    if tick and si:
        # Try a limit order far from current price (won't fill, but tests if placing is allowed)
        limit_price = round(tick.bid - 1.0, 5) if "JPY" not in test_symbol else round(tick.bid - 1.0, 3)
        req = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": test_symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": limit_price,
            "magic": 999999,
            "comment": "DIAG-LIMIT",
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        result = mt5.order_send(req)
        if result:
            check(f"LIMIT order: retcode={result.retcode}, comment={result.comment}", result.retcode == 0)
            if result.retcode == 0 and result.order:
                # Cancel the pending order
                mt5.order_send({
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": result.order,
                })
                note("  (cancelled test order)")
            results["limit_retcode"] = result.retcode
        else:
            check("LIMIT order: returned None", False)

    banner("ORDER CHECK — Pre-validation")
    if tick:
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": test_symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "deviation": 10,
            "magic": 999999,
            "comment": "DIAG-CHECK",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        check_result = mt5.order_check(req)
        if check_result:
            check(f"order_check: retcode={check_result.retcode}, comment={check_result.comment}", check_result.retcode == 0)
            results["check_retcode"] = check_result.retcode
        else:
            check("order_check: returned None", False)

    banner("TRADE HISTORY — Last 10 Deals")
    now = datetime.now(timezone.utc)
    from_time = datetime(now.year, now.month, now.day, tzinfo=None)
    deals = mt5.history_deals_get(from_time, now)
    if deals:
        note(f"Found {len(deals)} deals today")
        for d in deals[-10:]:
            note(f"  Ticket={d.ticket} {d.symbol} {'BUY' if d.type==0 else 'SELL'} "
                 f"vol={d.volume} price={d.price} pnl={d.profit:.2f}")
    else:
        note("No deals found today")

    banner("OPEN POSITIONS")
    positions = mt5.positions_get()
    if positions:
        note(f"Found {len(positions)} open positions")
        for p in positions:
            note(f"  Ticket={p.ticket} {p.symbol} {'BUY' if p.type==0 else 'SELL'} "
                 f"vol={p.volume} pnl={p.profit:.2f}")
    else:
        note("No open positions")

    # ── DIAGNOSIS ──
    banner("DIAGNOSIS")

    algo_enabled = results.get("algo_trading", False)
    ioc_retcode = results.get("ioc_retcode", -1)
    limit_retcode = results.get("limit_retcode", -1)

    if algo_enabled and ioc_retcode == 0:
        print("\n  [OK] ALL CLEAR - EA trading is working!")
        print("  The issue was likely in the code, not the broker.")
        print("  Try running: python qna.py daemon")
    elif not algo_enabled:
        print("\n  [FAIL] ALGO TRADING IS DISABLED IN MT5 TERMINAL")
        print("  -------------------------------------------")
        print("  FIX: Open MT5 Terminal > Tools > Options > Expert Advisors")
        print("       [x] Allow algorithmic trading")
        print("       [x] Allow DLL imports (if needed)")
        print("       Apply > OK")
        print()
        print("  Also check: each EA chart must have 'Allow algo trading' enabled")
        print("  Right-click on chart > Expert Advisors > Properties > Common tab")
    elif ioc_retcode == 10017:
        print("\n  [FAIL] RETCODE 10017 - TRADE DISABLED (broker-side)")
        print("  -------------------------------------------")
        print("  This means the MT5 BROKER is blocking EA orders.")
        print()
        print("  Possible causes:")
        print("  1. Account not approved for algorithmic trading")
        print("  2. Account requires KYC verification for EA trading")
        print("  3. Account type doesn't support API/EA trading")
        print("  4. Broker has disabled EA trading for your account")
        print("  5. Account is in a restricted state (margin call, etc.)")
        print()
        print("  ACTION REQUIRED:")
        print("  1. Contact Valetax broker support:")
        print("     - Ask: 'Why does order_send() return retcode 10017?'")
        print("     - Request: 'Enable algorithmic trading for account", LOGIN, "'")
        print("     - Mention: 'I need EA/programmatic trading access'")
        print()
        print("  2. Check MT5 terminal settings:")
        print("     - Tools > Options > Expert Advisors > Allow algorithmic trading")
        print("     - Each chart > Right-click > Expert Advisors > Allow algo trading")
        print()
        print("  3. Verify account status:")
        print("     - Check if account is fully verified (KYC)")
        print("     - Check if there are any account restrictions")
        print("     - Check margin level (should be > 100%)")
    elif limit_retcode == 0 and ioc_retcode != 0:
        print("\n  ⚠️  LIMIT orders work but MARKET orders are blocked")
        print("  This is unusual — contact broker support")
    else:
        print(f"\n  [FAIL] UNKNOWN STATE - ioc={ioc_retcode}, limit={limit_retcode}")
        print("  Contact broker support with these diagnostic results")

    # Save results
    banner("RESULTS SAVED")
    import json
    results_file = os.path.join("data", "broker_diagnostic.json")
    results["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    note(f"Saved to {results_file}")

    mt5.shutdown()
    return results


if __name__ == "__main__":
    run_diagnostics()
