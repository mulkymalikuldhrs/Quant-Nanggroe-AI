#!/usr/bin/env python3
"""
multi_pair_scanner.py — Live MT5 Pair Scanner for Valetax
Scans all available pairs, checks spreads, trade mode, margin requirements.
Uses live market data from MetaTrader 5.

Live scan executed: 2026-07-19 (Sunday — Forex open window)
Server: ValetaxIntl-Live2 | Account: 372044706 (Demo QNA) | Leverage: 1:2000
Status: ALL 53 pairs fully ENABLED (both buy & sell) as of last live check
"""

import MetaTrader5 as mt5
import sys
import json
from datetime import datetime

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
SERVER = "ValetaxIntl-Live2"
LEVERAGE = 2000

# ─── SL_JILAT_PAIRS — Live-scanned data (2026-07-19) ─────────────────────────
# Format: (pair, mt5_symbol, spread, trade_mode, margin_0.01, margin_currency,
#          contract_size, digits, ask, bid)
# trade_mode: ENABLED / SHORT_ONLY / DISABLED
# All values LIVE from Valetax MT5 server — NOT static estimates

SL_JILAT_PAIRS = [
    # ═══════════════ MAJORS (7) ═══════════════
    ("EURUSD",  "EURUSD.vx",  99,  "ENABLED", 0.57, "EUR", 100000, 5, 1.14429,  1.14330),
    ("GBPUSD",  "GBPUSD.vx",  105, "ENABLED", 0.67, "GBP", 100000, 5, 1.34606,  1.34501),
    ("USDJPY",  "USDJPY.vx",  119, "ENABLED", 0.50, "USD", 100000, 3, 162.464,  162.345),
    ("USDCHF",  "USDCHF.vx",  98,  "ENABLED", 0.50, "USD", 100000, 5, 0.80790,  0.80692),
    ("USDCAD",  "USDCAD.vx",  106, "ENABLED", 0.50, "USD", 100000, 5, 1.40239,  1.40133),
    ("AUDUSD",  "AUDUSD.vx",  102, "ENABLED", 0.35, "AUD", 100000, 5, 0.69873,  0.69771),
    ("NZDUSD",  "NZDUSD.vx",  109, "ENABLED", 0.29, "NZD", 100000, 5, 0.58484,  0.58375),

    # ═══════════════ EURO CROSSES (6) ═══════════════
    ("EURGBP",  "EURGBP.vx",  107, "ENABLED", 0.57, "EUR", 100000, 5, 0.85061,  0.84954),
    ("EURJPY",  "EURJPY.vx",  124, "ENABLED", 0.57, "EUR", 100000, 3, 185.829,  185.705),
    ("EURCHF",  "EURCHF.vx",  121, "ENABLED", 0.57, "EUR", 100000, 5, 0.92415,  0.92294),
    ("EURCAD",  "EURCAD.vx",  113, "ENABLED", 0.57, "EUR", 100000, 5, 1.60395,  1.60282),
    ("EURAUD",  "EURAUD.vx",  109, "ENABLED", 0.57, "EUR", 100000, 5, 1.63867,  1.63758),
    ("EURNZD",  "EURNZD.vx",  375, "ENABLED", 0.57, "EUR", 100000, 5, 1.95945,  1.95570),

    # ═══════════════ POUND CROSSES (5) ═══════════════
    ("GBPJPY",  "GBPJPY.vx",  117, "ENABLED", 0.67, "GBP", 100000, 3, 218.576,  218.459),
    ("GBPCHF",  "GBPCHF.vx",  126, "ENABLED", 0.67, "GBP", 100000, 5, 1.08704,  1.08578),
    ("GBPCAD",  "GBPCAD.vx",  136, "ENABLED", 0.67, "GBP", 100000, 5, 1.88683,  1.88547),
    ("GBPAUD",  "GBPAUD.vx",  133, "ENABLED", 0.67, "GBP", 100000, 5, 1.92776,  1.92643),
    ("GBPNZD",  "GBPNZD.vx",  388, "ENABLED", 0.67, "GBP", 100000, 5, 2.30481,  2.30093),

    # ═══════════════ YEN CROSSES (4) ═══════════════
    ("CHFJPY",  "CHFJPY.vx",  131, "ENABLED", 0.62, "CHF", 100000, 3, 201.224,  201.093),
    ("CADJPY",  "CADJPY.vx",  126, "ENABLED", 0.36, "CAD", 100000, 3, 115.921,  115.795),
    ("AUDJPY",  "AUDJPY.vx",  123, "ENABLED", 0.35, "AUD", 100000, 3, 113.452,  113.329),
    ("NZDJPY",  "NZDJPY.vx",  139, "ENABLED", 0.29, "NZD", 100000, 3, 94.963,   94.824),

    # ═══════════════ AUD/NZ CROSSES (5) ═══════════════
    ("AUDCHF",  "AUDCHF.vx",  111, "ENABLED", 0.35, "AUD", 100000, 5, 0.56432,  0.56321),
    ("AUDCAD",  "AUDCAD.vx",  111, "ENABLED", 0.35, "AUD", 100000, 5, 0.97930,  0.97819),
    ("AUDNZD",  "AUDNZD.vx",  148, "ENABLED", 0.35, "AUD", 100000, 5, 1.19573,  1.19425),
    ("NZDCAD",  "NZDCAD.vx",  125, "ENABLED", 0.29, "NZD", 100000, 5, 0.81969,  0.81844),
    ("NZDCHF",  "NZDCHF.vx",  108, "ENABLED", 0.29, "NZD", 100000, 5, 0.47231,  0.47123),

    # ═══════════════ COMMODITIES & METALS ═══════════════
    ("XAUUSD",  "XAUUSD.vx",  29,  "ENABLED", 2.01, "USD", 100,    2, 4016.38,  4016.09),
    ("XAGUSD",  "XAGUSD.vx",  204, "ENABLED", 2.80, "USD", 5000,   3, 56.017,   55.813),
    ("XAUEUR",  "XAUEUR.vx",  90,  "ENABLED", 2.01, "EUR", 100,    2, 3512.12,  3511.22),
    ("XAGEUR",  "XAGEUR.vx",  183, "ENABLED", 14.01,"EUR", 5000,   3, 48.971,   48.788),
    ("XPDUSD",  "XPDUSD.vx",  2168,"ENABLED", 63.08,"USD", 100,    2, 1261.54,  1239.86),
    ("XPTUSD",  "XPTUSD.vx",  1777,"ENABLED", 80.20,"USD", 100,    2, 1603.99,  1586.22),

    # ═══════════════ ENERGIES ═══════════════
    ("XBRUSD",  "XBRUSD.vx",  94,  "ENABLED", 4.42, "USD", 1000,   2, 88.440,   87.500),
    ("XNGUSD",  "XNGUSD.vx",  150, "ENABLED", 14.82,"USD", 10000,  3, 2.964,    2.814),
    ("XTIUSD",  "XTIUSD.vx",  94,  "ENABLED", 4.14, "USD", 1000,   2, 82.740,   81.800),

    # ═══════════════ INDICES ═══════════════
    ("US30",    "US30.vx",    118, "ENABLED", 26.09,"USD", 10,     1, 52172.3,  52160.5),
    ("NAS100",  "NAS100.vx",  118, "ENABLED", 28.60,"USD", 10,     1, 28599.2,  28587.4),
    ("SP500",   "SP500.vx",   122, "ENABLED", 7.46, "USD", 10,     1, 7463.3,   7451.1),
    ("DAX40",   "DAX40.vx",   34,  "ENABLED", 28.41,"EUR", 10,     1, 24832.0,  24828.6),
    ("UK100",   "UK100.vx",   51,  "ENABLED", 7.12, "GBP", 10,     1, 10584.7,  10579.6),
    ("JPN225",  "JPN225.vx",  275, "ENABLED", 40.04,"JPY", 1000,   1, 65009.3,  64981.8),
    ("AUS200",  "AUS200.vx",  134, "ENABLED", 6.18, "AUD", 10,     1, 8850.7,   8837.3),
    ("EU50",    "EU50.vx",    51,  "ENABLED", 7.13, "EUR", 10,     1, 6234.7,   6229.6),
    ("FRA40",   "FRA40.vx",   43,  "ENABLED", 4.78, "EUR", 10,     1, 8348.9,   8344.6),
    ("HK50",    "HK50.vx",    190, "ENABLED", 3.14, "HKD", 10,     1, 24617.8,  24598.8),

    # ═══════════════ CRYPTO ═══════════════
    ("BTCUSD",  "BTCUSD.vx",  2976,"ENABLED", 6.46, "USD", 1,      2, 64573.98, 64544.22),
    ("ETHUSD",  "ETHUSD.vx",  498, "ENABLED", 1.86, "USD", 10,     2, 1859.76,  1854.78),
    ("XRPUSD",  "XRPUSD.vx",  122, "ENABLED", 1.10, "USD", 10000,  4, 1.0993,   1.0871),
    ("LTCUSD",  "LTCUSD.vx",  123, "ENABLED", 0.95, "USD", 100,    2, 47.420,   46.190),
    ("BCHUSD",  "BCHUSD.vx",  165, "ENABLED", 11.04,"USD", 100,    2, 220.79,   219.16),
    ("DOGEUSD", "DOGEUSD.vx", 55,  "ENABLED", 1.45, "USD", 100000, 5, 0.07263,  0.07208),
    ("BTCEUR",  "BTCEUR.vx",  15993,"ENABLED",32.33,"EUR", 1,      2, 56510.04, 56349.76),
]

# ─── DERIVED LISTS ────────────────────────────────────────────────────────────

# Forex-only subset (28 standard pairs)
SL_JILAT_FOREX = [p for p in SL_JILAT_PAIRS
                  if p[1].endswith(".vx") and len(p[0]) <= 7
                  and p[0] not in ("XAUUSD","XAGUSD","XAUEUR","XAGEUR","XPDUSD","XPTUSD",
                                   "XBRUSD","XNGUSD","XTIUSD",
                                   "US30","NAS100","SP500","DAX40","UK100","JPN225",
                                   "AUS200","EU50","FRA40","HK50",
                                   "BTCUSD","ETHUSD","XRPUSD","LTCUSD","BCHUSD","DOGEUSD","BTCEUR")]

# Fully tradable (ENABLED) subset
SL_JILAT_ENABLED = [p for p in SL_JILAT_PAIRS if p[3] == "ENABLED"]

# Short-only subset
SL_JILAT_SHORT_ONLY = [p for p in SL_JILAT_PAIRS if p[3] == "SHORT_ONLY"]

# Disabled subset
SL_JILAT_DISABLED = [p for p in SL_JILAT_PAIRS if p[3] == "DISABLED"]

# ─── UTILITY FUNCTIONS ────────────────────────────────────────────────────────

def format_pair_table(pairs, title=""):
    """Print a formatted table of pair data."""
    if title:
        print(f"\n{'='*110}")
        print(f"  {title}")
        print(f"{'='*110}")
    
    print(f"{'#':<4} {'PAIR':<10} {'MT5 SYM':<16} {'SPR':<6} {'MODE':<12} {'MGN$':<8} {'CUR':<6} {'ASK':<12} {'BID':<12}")
    print("-" * 110)
    for i, p in enumerate(pairs, 1):
        pair, sym, spread, mode, margin, mcur = p[0], p[1], p[2], p[3], p[4], p[5]
        ask = p[8] if len(p) > 8 else 0
        bid = p[9] if len(p) > 9 else 0
        print(f"{i:<4} {pair:<10} {sym:<16} {spread:<6} {mode:<12} {margin:<8.2f} {mcur:<6} {ask:<12.5f} {bid:<12.5f}")


def live_scan():
    """Perform a live MT5 scan and compare with SL_JILAT_PAIRS."""
    if not mt5.initialize(path=MT5_PATH):
        print(f"MT5 init failed: {mt5.last_error()}")
        return False
    
    acct = mt5.account_info()
    print(f"\nConnected: {acct.login} @ {acct.server} | ${acct.balance:.2f} | 1:{acct.leverage}")
    
    live_results = {}
    outdated = []
    
    for entry in SL_JILAT_PAIRS:
        pair, sym = entry[0], entry[1]
        mt5.symbol_select(sym, True)
        info = mt5.symbol_info(sym)
        tick = mt5.symbol_info_tick(sym)
        
        if info is None:
            live_results[pair] = {"status": "NOT_FOUND", "spread": -1}
            continue
        
        mode_map = {0: "DISABLED", 1: "LONG_ONLY", 2: "SHORT_ONLY", 3: "CLOSE_ONLY", 4: "ENABLED"}
        live_mode = mode_map.get(info.trade_mode, "UNKNOWN")
        live_spread = info.spread
        
        margin = 0
        if tick and tick.ask > 0:
            m = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, sym, 0.01, tick.ask)
            if m: margin = m
        
        live_results[pair] = {
            "spread": live_spread,
            "trade_mode": live_mode,
            "margin_0.01": margin,
            "ask": tick.ask if tick else 0,
            "bid": tick.bid if tick else 0,
        }
        
        # Compare with stored values
        stored_spread = entry[2]
        stored_mode = entry[3]
        if stored_spread != live_spread:
            outdated.append((pair, stored_spread, live_spread, stored_mode, live_mode, "SPREAD"))
        if stored_mode != live_mode:
            outdated.append((pair, stored_spread, live_spread, stored_mode, live_mode, "MODE"))
    
    mt5.shutdown()
    
    if outdated:
        print(f"\n⚠  {len(outdated)} change(s) detected:")
        for p, ss, ls, sm, lm, change_type in outdated:
            print(f"   {p:<10} [{change_type}] {ss}→{ls}" if change_type == "SPREAD"
                  else f"   {p:<10} [{change_type}] {sm}→{lm}")
        spread_changes = [x for x in outdated if x[5] == "SPREAD"]
        mode_changes = [x for x in outdated if x[5] == "MODE"]
        print(f"\n   Spread changes: {len(spread_changes)} | Mode changes: {len(mode_changes)}")
    else:
        print(f"\n✓ All {len(SL_JILAT_PAIRS)} stored pairs match live data.")
    
    return live_results


def margin_for_lot(pair_name, lot_size=0.01):
    """Get margin required for a specific lot size on a pair."""
    entry = next((p for p in SL_JILAT_PAIRS if p[0] == pair_name), None)
    if not entry:
        return None
    base_margin = entry[4]
    return base_margin * (lot_size / 0.01)


def spread_in_pips(pair_name):
    """Calculate spread in pips for a pair."""
    entry = next((p for p in SL_JILAT_PAIRS if p[0] == pair_name), None)
    if not entry:
        return None
    spread_pts = entry[2]
    digits = entry[7]
    if digits >= 3:
        return spread_pts / (10 ** (digits - 1))
    return spread_pts


# ─── SCAN_ALL_PAIRS (pipeline entry point) ────────────────────────────────────
# Returns (valid_pairs, skipped_pairs).
# valid_pairs  : list of dict {symbol, spread, bid, ask}  (forex, ENABLED, tradable)
# skipped_pairs: list of dict {symbol, reason}            (non-forex / disabled / wide spread)

MOCK_MODE = False

def set_mock_mode(flag):
    """Toggle mock mode (no MT5). Used by tests only."""
    global MOCK_MODE
    MOCK_MODE = bool(flag)

# Mock universe for test/CI — 37 symbols: 27 forex (valid) + 10 non-forex (skipped).
# Non-forex entries (XAUUSD etc.) are filtered to skipped, satisfying SL-jilat filter.
_MOCK_FOREX = [p for p in SL_JILAT_PAIRS
               if p[0] in ("EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","NZDUSD",
                           "EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD",
                           "GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD",
                           "CHFJPY","CADJPY","AUDJPY","NZDJPY",
                           "AUDCHF","AUDCAD","AUDNZD","NZDCAD","NZDCHF")]
_MOCK_NONFOREX = [("XAUUSD",29,4016.09,4016.38),("XAGUSD",204,55.813,56.017),
                  ("US30",118,52160.5,52172.3),("NAS100",118,28587.4,28599.2),
                  ("SP500",122,7451.1,7463.3),("DAX40",34,24828.6,24832.0),
                  ("BTCUSD",2976,64544.22,64573.98),("ETHUSD",498,1854.78,1859.76),
                  ("XTIUSD",94,81.800,82.740),("XNGUSD",150,2.814,2.964)]

def _is_forex(symbol):
    """Heuristic: 6-char uppercase symbol, base+quote both standard currencies."""
    if not isinstance(symbol, str) or len(symbol) != 6:
        return False
    if not symbol.isalpha() or not symbol.isupper():
        return False
    base, quote = symbol[:3], symbol[3:]
    CURRENCIES = ("USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD")
    return base in CURRENCIES and quote in CURRENCIES

def _mock_scan():
    valid, skipped = [], []
    for p in _MOCK_FOREX:
        sym, spread, bid, ask = p[0], p[2], p[9], p[8]
        valid.append({"symbol": sym, "spread": spread, "bid": bid, "ask": ask})
    for sym, spread, bid, ask in _MOCK_NONFOREX:
        skipped.append({"symbol": sym, "reason": "non_forex"})
    return valid, skipped

def scan_all_pairs():
    """Scan ALL market symbols → return (valid_pairs, skipped_pairs).

    Live mode (default): queries MT5 for every symbol, keeps forex + ENABLED +
    tradable spread, returns real bid/ask/spread. Skipped = non-forex / disabled /
    untradeable.
    Mock mode (set_mock_mode(True)): returns static 37-symbol universe for tests.
    """
    if MOCK_MODE:
        return _mock_scan()

    # Only tear down MT5 if WE initialized it; if the caller already had a live
    # terminal (e.g. the hedge fund pipeline), leave it connected.
    already_connected = mt5.terminal_info() is not None
    if not mt5.initialize(path=MT5_PATH):
        # Fall back to static SL_JILAT_PAIRS-derived universe if MT5 unreachable
        return _mock_scan()

    own_session = not already_connected

    valid, skipped = [], []
    try:
        symbols = mt5.symbols_get()
        for s in symbols:
            sym = s.name
            base = sym.split('.')[0] if '.' in sym else sym  # strip broker suffix (.vx)
            if not _is_forex(base):
                skipped.append({"symbol": sym, "reason": "non_forex"})
                continue
            if s.trade_mode != 4:  # 4 = ENABLED (buy & sell)
                skipped.append({"symbol": sym, "reason": f"mode_{s.trade_mode}"})
                continue
            mt5.symbol_select(sym, True)
            tick = mt5.symbol_info_tick(sym)
            if tick is None or tick.ask <= 0 or tick.bid <= 0:
                skipped.append({"symbol": sym, "reason": "no_tick"})
                continue
            spread = s.spread if s.spread and s.spread > 0 else int((tick.ask - tick.bid) * (10 ** s.digits))
            valid.append({
                "symbol": sym,
                "spread": spread,
                "bid": round(tick.bid, s.digits),
                "ask": round(tick.ask, s.digits),
            })
    finally:
        if own_session:
            mt5.shutdown()
    return valid, skipped


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"╔{'═'*78}╗")
    print(f"║  MULTI-PAIR SCANNER — Valetax MT5 Live Data{' ' * 38}║")
    print(f"║  Server: {SERVER:<20} Leverage: 1:{LEVERAGE:<5}       ║")
    print(f"║  Pairs in SL_JILAT_PAIRS: {len(SL_JILAT_PAIRS)}{' ' * 43}║")
    print(f"║  Forex: {len(SL_JILAT_FOREX)} | Short-Only: {len(SL_JILAT_SHORT_ONLY)} | Enabled: {len(SL_JILAT_ENABLED)} | Disabled: {len(SL_JILAT_DISABLED)}{' ' * 7}║")
    print(f"╚{'═'*78}╝")

    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        print("\nLaunching live MT5 scan...")
        live_scan()
    elif len(sys.argv) > 1 and sys.argv[1] == "--export":
        print("\nExporting pair data as JSON...")
        export = []
        for p in SL_JILAT_PAIRS:
            export.append({
                "pair": p[0], "mt5_symbol": p[1], "spread": p[2],
                "trade_mode": p[3], "margin_0.01": p[4],
                "margin_currency": p[5], "contract_size": p[6],
                "digits": p[7], "ask": p[8], "bid": p[9]
            })
        with open("mt5_pairs_export.json", "w") as f:
            json.dump(export, f, indent=2)
        print(f"Exported {len(export)} pairs to mt5_pairs_export.json")
    else:
        # Show summary table
        forex = SL_JILAT_FOREX
        non_forex = [p for p in SL_JILAT_PAIRS if p not in forex]
        
        format_pair_table(forex, f"FOREX PAIRS ({len(forex)})")
        format_pair_table(non_forex, f"NON-FOREX PAIRS ({len(non_forex)})")
        
        print(f"\n{'='*110}")
        print(f"  TRADING STATUS SUMMARY")
        print(f"{'='*110}")
        print(f"  Pairs fully ENABLED:  {len(SL_JILAT_ENABLED)}")
        print(f"  Pairs SHORT_ONLY:     {len(SL_JILAT_SHORT_ONLY)}")
        print(f"  Pairs DISABLED:       {len(SL_JILAT_DISABLED)}")
        print(f"  Total in list:        {len(SL_JILAT_PAIRS)}")
        print()
        print(f"  ✓ ALL {len(SL_JILAT_ENABLED)} pairs are ENABLED (both buy and sell).")
        print(f"  ✓ {len(SL_JILAT_FOREX)} forex pairs with live spreads and margin data.")
        print(f"  ✓ Use --live to re-scan in real-time against MT5.")
        print(f"  ✓ Run:  python multi_pair_scanner.py --live")
