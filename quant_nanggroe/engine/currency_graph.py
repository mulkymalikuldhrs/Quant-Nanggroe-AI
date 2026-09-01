"""Currency Graph Network — Weighted Directed Graph (Klip 00:00-00:04).

Video: EUR, USD, GBP, JPY, AUD, CAD, CHF sebagai node V.
Teori: Graf Terarah Berbobot WDG — Node = mata uang, Edge = pair E_ij,
bobot w_ij = R_A/B. Ekuilibrium: R_A/B * R_B/C * R_C/A = 1.

Real-trade-ready: build dari MT5 tick live (.vxc), fail-closed, no mock.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MAJORS = ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF"]
# All-pair expansion: broker tradable 28 FX + XAU/XAG via MT5 MarketWatch
ALL_CURRENCIES = ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]

@dataclass
class CurrencyEdge:
    base: str
    quote: str
    rate: float  # R_base/quote
    symbol: str  # broker symbol e.g. EURUSD.vx

@dataclass
class CurrencyGraph:
    """Weighted Directed Graph untuk forex."""
    nodes: List[str] = field(default_factory=lambda: list(MAJORS))
    def __post_init__(self):
        if not self.nodes or self.nodes[0] == "MA":
            self.nodes = list(MAJORS)
    edges: Dict[Tuple[str, str], CurrencyEdge] = field(default_factory=dict)
    rates: Dict[str, float] = field(default_factory=dict)  # symbol -> rate

    def add_rate(self, base: str, quote: str, rate: float, symbol: str = "") -> None:
        if rate <= 0:
            return
        self.edges[(base, quote)] = CurrencyEdge(base, quote, rate, symbol)
        self.edges[(quote, base)] = CurrencyEdge(quote, base, 1.0 / rate, symbol)
        self.rates[symbol or f"{base}{quote}"] = rate

    def get_rate(self, base: str, quote: str) -> Optional[float]:
        e = self.edges.get((base, quote))
        return e.rate if e else None

    def check_equilibrium(self, a: str, b: str, c: str, tol: float = 1e-4) -> Tuple[bool, float]:
        """Cek R_A/B * R_B/C * R_C/A ==1 . Return (is_eq, product)."""
        r_ab = self.get_rate(a, b)
        r_bc = self.get_rate(b, c)
        r_ca = self.get_rate(c, a)
        if None in (r_ab, r_bc, r_ca):
            return False, 0.0
        prod = r_ab * r_bc * r_ca  # type: ignore
        return abs(prod - 1.0) < tol, prod

    def find_triangular_cycles(self, threshold: float = 0.0002) -> List[Dict]:
        """Brute-force semua C(n,3) = 35 (n=7) atau 3276 (n=28) — cari Δ>threshold."""
        out: List[Dict] = []
        n = len(self.nodes)
        for i in range(n):
            for j in range(i + 1, n):
                for k in range(j + 1, n):
                    for (a, b, c) in [(self.nodes[i], self.nodes[j], self.nodes[k]),
                                      (self.nodes[i], self.nodes[k], self.nodes[j]),
                                      (self.nodes[j], self.nodes[i], self.nodes[k])]:
                        r_ab = self.get_rate(a, b)
                        r_bc = self.get_rate(b, c)
                        r_ca = self.get_rate(c, a)
                        if None in (r_ab, r_bc, r_ca):
                            continue
                        prod = r_ab * r_bc * r_ca  # type: ignore
                        delta = abs(prod - 1.0)
                        if delta > threshold:
                            out.append({"cycle": (a, b, c), "product": prod, "delta": delta})
        out.sort(key=lambda x: x["delta"], reverse=True)
        return out


def build_graph_from_rates(rates: Dict[str, float], symbol_map: Optional[Dict[str, Tuple[str,str]]] = None) -> CurrencyGraph:
    """Build graph dari dict symbol->rate. symbol_map: symbol -> (base,quote)."""
    g = CurrencyGraph()
    for sym, rate in rates.items():
        base_quote = symbol_map.get(sym) if symbol_map else None
        if base_quote:
            b, q = base_quote
        else:
            # parse EURUSD.vx -> EUR/USD
            raw = sym.split(".")[0].upper().replace("/", "")
            if len(raw) >= 6:
                b, q = raw[:3], raw[3:6]
            else:
                continue
        g.add_rate(b, q, rate, sym)
    return g


def build_graph_from_mt5(all_pairs: bool = True) -> CurrencyGraph:
    """Live MT5 tick -> graph. Fail-closed: return empty graph jika MT5 offline."""
    try:
        import MetaTrader5 as mt5  # type: ignore
        if not mt5.initialize():
            logger.warning("MT5 not initialized for currency graph")
            return CurrencyGraph()
        # discover symbols: use MarketWatch or static majors
        symbols = []
        if all_pairs:
            # all tradable FX via account discovery helper if available
            try:
                from quant_nanggroe.engine.execution.account_discovery import discover_accounts  # noqa: F401
                # use static 28 for now — dynamic scan via mt5.symbols_get would need filtering
                symbols = [s.name for s in (mt5.symbols_get() or []) if s.visible][:40]
            except Exception:
                symbols = ["EURUSD.vx", "GBPUSD.vx", "USDJPY.vx", "AUDUSD.vx", "USDCAD.vx", "USDCHF.vx", "EURJPY.vx"]
        else:
            symbols = ["EURUSD.vx", "GBPUSD.vx", "USDJPY.vx", "AUDUSD.vx", "USDCAD.vx", "USDCHF.vx"]
        rates: Dict[str, float] = {}
        for sym in symbols:
            tick = mt5.symbol_info_tick(sym)
            if tick and tick.bid > 0:
                rates[sym] = float((tick.bid + tick.ask) / 2)
        return build_graph_from_rates(rates)
    except Exception as e:
        logger.warning("build_graph_from_mt5 failed: %s", e)
        return CurrencyGraph()
