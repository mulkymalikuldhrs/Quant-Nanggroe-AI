import MetaTrader5 as mt5
mt5.initialize()
pos = mt5.positions_get()
if pos:
    for p in pos:
        side = 'BUY' if p.type==0 else 'SELL'
        print(f'{p.symbol} {side} vol={p.volume:.2f} entry={p.price_open:.5f} sl={p.sl:.5f} tp={p.tp:.5f} pnl={p.profit:.2f}')
else:
    print('No positions')
print(f'\nTotal: {len(pos) if pos else 0} positions')
mt5.shutdown()
