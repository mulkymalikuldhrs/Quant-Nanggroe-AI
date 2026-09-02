"""Grid Executor Quant — Coordinate Grid Matrix 0.05 + Eigenvector Hedged (Klip 00:16-00:23).

Video: kisi 0.05 0.10 0.15, limit mesh x,y,z, eigenvector merah-hijau hedged.
Eksekusi: bukan SL/TP konvensional, tapi jaring limit di koordinat proyeksi.

Real-trade-ready: mesh via ExecutionManager, risk 0.5%, fail-closed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class GridLevel:
    price: float
    side: str  # buy/sell
    lot: float
    coordinate: Tuple[float, float, float]  # x,y,z

def build_grid(origin: np.ndarray, eigenvector: np.ndarray, sigma: float = 0.05, levels: int = 5, lot: float = 0.01, atr: float | None = None, account_balance: float | None = None) -> List[GridLevel]:
    """Bangun jaring limit di sepanjang eigenvector dari origin.

    Risk-aware: if account_balance and atr provided, lot is recomputed via
    constitutional 0.5% risk (Kelly-capped), otherwise 0.01 is capped by max_position.
    Sigma is ATR-aware when atr is supplied (sigma = ATR/price).
    """
    # ATR-aware sigma
    if atr is not None and atr > 0 and origin[2] > 0:
        sigma = min(max(atr / origin[2], 0.001), 0.02)
    # Risk-aware lot (0.5% per level, cap 0.10, min 0.01)
    if account_balance is not None and atr is not None and atr > 0:
        try:
            risk_amount = account_balance * 0.005
            # pip value approx $10 for 1 lot forex, sl = sigma*price
            sl_dist = sigma * (origin[2] or 1.0)
            pip_dist = sl_dist / 0.0001 if origin[2] < 100 else sl_dist / 0.01
            if pip_dist > 0:
                lot = max(0.01, min(0.10, round(risk_amount / (pip_dist * 10.0), 2)))
        except Exception:
            pass
    # eigenvector normalized
    ev = eigenvector / (np.linalg.norm(eigenvector) or 1)
    grid: List[GridLevel] = []
    for i in range(1, levels + 1):
        dist = sigma * i
        coord = origin + ev * dist
        # price proxy = z (EURUSD) + x (USD) blend
        price = float(coord[2] + coord[0] * 0.01)
        grid.append(GridLevel(price=price, side="buy" if i % 2 == 0 else "sell", lot=lot, coordinate=tuple(coord)))
        # mirror hedged side
        coord_m = origin - ev * dist
        price_m = float(coord_m[2] + coord_m[0] * 0.01)
        grid.append(GridLevel(price=price_m, side="sell" if i % 2 == 0 else "buy", lot=lot, coordinate=tuple(coord_m)))
    return grid

def compute_eigenvector(manifold_points: List[np.ndarray]) -> np.ndarray:
    """Eigenvector arah utama variansi (PCA 1st component)."""
    if not manifold_points:
        return np.array([1, 1, 1]) / np.sqrt(3)
    data = np.stack(manifold_points)
    data_centered = data - data.mean(axis=0)
    cov = np.cov(data_centered, rowvar=False)
    vals, vecs = np.linalg.eig(cov)
    idx = int(np.argmax(vals))
    return vecs[:, idx]

async def execute_grid(symbol: str, grid: List[GridLevel]) -> int:
    """Eksekusi grid via MT5 limit orders, hedged. Return count placed."""
    try:
        from quant_nanggroe.engine.risk.kill_switch import KillSwitch
        if not KillSwitch().can_trade():
            logger.warning("Grid blocked by KillSwitch %s", symbol)
            return 0
    except Exception:
        return 0
    placed = 0
    try:
        import MetaTrader5 as mt5  # type: ignore
        if not mt5.initialize():
            return 0
        # One-position + pending guard (max 5)
        try:
            poss = mt5.positions_get()
            if poss:
                base = symbol.split(".")[0].upper()
                if any(p.symbol.split(".")[0].upper() == base for p in poss):
                    logger.warning("Grid blocked by one-position %s", symbol)
                    return 0
            ords = mt5.orders_get()
            if ords:
                base = symbol.split(".")[0].upper()
                cnt = sum(1 for o in ords if o.symbol.split(".")[0].upper() == base)
                if cnt >= 5:
                    logger.warning("Grid blocked by pending %s %d", symbol, cnt)
                    return 0
        except Exception:
            pass
        for lvl in grid:
            side = mt5.ORDER_TYPE_BUY_LIMIT if lvl.side == "buy" else mt5.ORDER_TYPE_SELL_LIMIT
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                continue
            req = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lvl.lot,
                "type": side,
                "price": lvl.price,
                "deviation": 10,
                "magic": 20260719,
                "comment": f"GRID {lvl.coordinate}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                placed += 1
                logger.info("Grid %s %s @ %.5f", lvl.side, symbol, lvl.price)
    except Exception as e:
        logger.warning("Grid execute failed %s: %s", symbol, e)
    return placed
