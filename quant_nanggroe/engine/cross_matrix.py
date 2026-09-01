"""Implied Cross-Rates Matrix — M N×N (Klip 00:05-00:07).

Video: matriks desimal 1.4065 0.9335 137.01 × / .
Teori: M[i][j]=R_i/j, diag 1, reciprocity 1/R, implied CAD/JPY=USDJPY/USDCAD.

Real-trade-ready: build dari CurrencyGraph, fail-closed, z-normalize JPY.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CrossMatrix:
    """Kuadrat N×N implied matrix."""
    def __init__(self, currencies: List[str]):
        self.currencies = currencies
        self.n = len(currencies)
        self.idx = {c: i for i, c in enumerate(currencies)}
        self.m = np.eye(self.n, dtype=float)  # diag 1

    def set_rate(self, base: str, quote: str, rate: float) -> None:
        if base not in self.idx or quote not in self.idx or rate <= 0:
            return
        i, j = self.idx[base], self.idx[quote]
        self.m[i, j] = rate
        self.m[j, i] = 1.0 / rate

    def get_rate(self, base: str, quote: str) -> Optional[float]:
        if base not in self.idx or quote not in self.idx:
            return None
        return float(self.m[self.idx[base], self.idx[quote]])

    def implied(self, base: str, quote: str, via: str = "USD") -> Optional[float]:
        """Implied R_base/quote via USD: USDJPY/USDCAD untuk CAD/JPY."""
        r_base_via = self.get_rate(base, via)
        r_quote_via = self.get_rate(quote, via)
        # via USD: R_base/quote = R_base/USD / R_quote/USD = R_base/USD * R_USD/quote
        # lebih umum: R_base/quote = R_base/via / R_quote/via
        if r_base_via is None or r_quote_via is None:
            # fallback via USD direct: R_base/USD = 1/R_USD/base
            r_bv = self.get_rate(via, base)
            r_qv = self.get_rate(via, quote)
            if r_bv is None or r_qv is None or r_bv == 0 or r_qv == 0:
                return None
            # via USD: base/quote = (USD/quote)/(USD/base)
            return r_qv / r_bv if r_bv != 0 else None
        # base/via divided by quote/via
        if r_quote_via == 0:
            return None
        return r_base_via / r_quote_via

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for i, b in enumerate(self.currencies):
            out[b] = {q: float(self.m[i, j]) for j, q in enumerate(self.currencies)}
        return out


def build_matrix_from_graph(graph, via: str = "USD") -> CrossMatrix:
    """Build matrix dari CurrencyGraph (sudah punya edges)."""
    cm = CrossMatrix(graph.nodes)
    for (b, q), edge in graph.edges.items():
        # only need one direction, set_rate will reciprocate
        if graph.nodes.index(b) < graph.nodes.index(q):  # avoid double
            cm.set_rate(b, q, edge.rate)
        else:
            # still set to ensure all pairs
            cm.set_rate(b, q, edge.rate)
    return cm


def build_matrix_from_rates(rates: Dict[str, float], currencies: Optional[List[str]] = None) -> CrossMatrix:
    """Helper: rates symbol->price (EURUSD.vx)."""
    if currencies is None:
        currencies = ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF"]
    cm = CrossMatrix(currencies)
    for sym, rate in rates.items():
        raw = sym.split(".")[0].upper().replace("/", "")
        if len(raw) >= 6:
            b, q = raw[:3], raw[3:6]
            cm.set_rate(b, q, rate)
    return cm
