import sys, logging
sys.path.insert(0, 'E:/trading')
logging.basicConfig(level=logging.INFO)

from multi_pair_scanner import scan_all_pairs
valid, _ = scan_all_pairs()
print(f'Pairs: {len(valid)}')

from market_context import get_dxy
dxy = get_dxy()
print(f'DXY: {dxy["price"]} ({dxy["trend"]})')

from risk_guard import approve
r = approve({'symbol':'EURUSD','action':'buy','volume':0.02,'price':1.143,'sl':1.142,'account_balance':1000,'daily_pnl':0,'open_positions':0,'market_volatility':0.001})
print(f'Risk: {r["status"]}')

from strategies.dhaher_system import DhaherSystem
d = DhaherSystem()
print(f'Dhaher WR target: 42.1%')

import MetaTrader5 as mt5
if mt5.initialize():
    a = mt5.account_info()
    if a:
        print(f'MT5: ${a.balance:.0f}')
    mt5.shutdown()

print()
print('=== HEDGE FUND OK ===')
