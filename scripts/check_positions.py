import MetaTrader5 as mt5
import sys
try:
    if not mt5.initialize():
        print(f"INIT_FAIL: {mt5.last_error()}", flush=True)
        sys.exit(1)
    info = mt5.account_info()
    print(f"BALANCE: {info.balance}", flush=True)
    print(f"EQUITY: {info.equity}", flush=True)
    print(f"MARGIN: {info.margin}", flush=True)
    print(f"FREE_MARGIN: {info.margin_free}", flush=True)
    print(f"MARGIN_LEVEL: {info.margin_level}", flush=True)
    print(f"LEVERAGE: {info.leverage}", flush=True)
    positions = mt5.positions_get()
    count = len(positions) if positions else 0
    print(f"POSITION_COUNT: {count}", flush=True)
    total_vol = 0.0
    total_pnl = 0.0
    if positions:
        for p in positions:
            side = "BUY" if p.type == 0 else "SELL"
            total_vol += p.volume
            total_pnl += p.profit + p.swap
            print(f"POS|{p.symbol}|{side}|{p.volume}|{p.price_open}|{p.sl}|{p.tp}|{p.profit:.2f}|{p.swap:.2f}", flush=True)
    print(f"TOTAL_VOLUME: {total_vol:.2f}", flush=True)
    print(f"TOTAL_PNL: {total_pnl:.2f}", flush=True)
    if info.balance > 0:
        print(f"PNL_PCT: {total_pnl/info.balance*100:.1f}", flush=True)
    mt5.shutdown()
except Exception as e:
    print(f"ERROR: {e}", flush=True)
    sys.exit(1)
