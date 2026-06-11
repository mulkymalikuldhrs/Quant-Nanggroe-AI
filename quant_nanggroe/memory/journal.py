"""Trade journal for Quant Nanggroe AI.

Records all trade decisions, outcomes, and reflections
for post-trade analysis and agent learning.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TradeJournal:
    """
    Trade journal for recording and analyzing trade history.

    Provides structured trade logging with entry/exit tracking,
    PnL calculation, and reflection/review capabilities.

    Usage:
        journal = TradeJournal()
        journal.record_entry(symbol="BTC/USDT", side="buy", price=50000, quantity=0.1)
        journal.record_exit(symbol="BTC/USDT", price=52000, pnl=200.0)
        journal.add_reflection(symbol="BTC/USDT", notes="Good trend following trade")
    """

    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize trade journal.

        Args:
            persist_path: Path for journal persistence file
        """
        self._persist_path = Path(persist_path) if persist_path else None
        self._trades: List[Dict[str, Any]] = []
        # Dict[str, List[Dict]] — supports multiple open positions per symbol
        self._open_positions: Dict[str, List[Dict[str, Any]]] = {}

    def record_entry(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        agent_name: Optional[str] = None,
        strategy: Optional[str] = None,
        reasoning: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Record a trade entry.

        Args:
            symbol: Trading pair symbol
            side: Trade direction ('buy' or 'sell')
            price: Entry price
            quantity: Trade quantity
            agent_name: Agent that made the decision
            strategy: Strategy name
            reasoning: Decision reasoning
            metadata: Additional metadata

        Returns:
            Trade ID
        """
        trade_id = f"T{len(self._trades) + 1:06d}"
        entry = {
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "entry_price": price,
            "entry_quantity": quantity,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "agent_name": agent_name,
            "strategy": strategy,
            "reasoning": reasoning,
            "metadata": metadata or {},
            "status": "open",
            "exit_price": None,
            "exit_time": None,
            "pnl": None,
            "pnl_pct": None,
            "reflection": None,
        }
        self._trades.append(entry)
        self._open_positions.setdefault(symbol, []).append(entry)
        logger.info(f"Recorded entry: {trade_id} {side} {symbol} @ {price}")
        return trade_id

    def record_exit(
        self,
        symbol: str,
        price: float,
        pnl: Optional[float] = None,
        notes: Optional[str] = None,
        trade_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Record a trade exit.

        Args:
            symbol: Trading pair symbol
            price: Exit price
            pnl: Realized PnL
            notes: Exit notes
            trade_id: Optional specific trade ID to close. If omitted, closes
                      the most recently opened position for the symbol (LIFO).

        Returns:
            Trade ID if found, None otherwise
        """
        positions = self._open_positions.get(symbol, [])
        if not positions:
            logger.warning(f"No open position found for {symbol}")
            return None

        # Find the specific trade or fall back to the last one (LIFO)
        trade = None
        if trade_id:
            for idx, t in enumerate(positions):
                if t["trade_id"] == trade_id:
                    trade = positions.pop(idx)
                    break
            if trade is None:
                logger.warning(f"No open position with trade_id={trade_id} for {symbol}")
                return None
        else:
            trade = positions.pop()  # LIFO: close most recent

        # Clean up empty lists
        if not positions:
            self._open_positions.pop(symbol, None)
        trade["exit_price"] = price
        trade["exit_time"] = datetime.now(timezone.utc).isoformat()
        trade["status"] = "closed"
        trade["notes"] = notes

        if pnl is not None:
            trade["pnl"] = pnl
        else:
            entry_price = trade["entry_price"]
            quantity = trade["entry_quantity"]
            side = trade["side"]
            if side == "buy":
                trade["pnl"] = (price - entry_price) * quantity
            else:
                trade["pnl"] = (entry_price - price) * quantity

        if trade["entry_price"] > 0:
            trade["pnl_pct"] = (trade["pnl"] / (trade["entry_price"] * quantity)) * 100

        logger.info(f"Recorded exit: {trade['trade_id']} {symbol} @ {price}, PnL={trade['pnl']}")
        return trade["trade_id"]

    def add_reflection(self, symbol: str, notes: str, rating: Optional[int] = None, trade_id: Optional[str] = None) -> None:
        """Add reflection notes to an open or recent trade.

        Args:
            symbol: Trading pair symbol
            notes: Reflection notes
            rating: Optional rating (1-5)
            trade_id: Optional specific trade ID. If omitted, applies to the
                      most recent open position for the symbol.
        """
        positions = self._open_positions.get(symbol, [])
        trade = None
        if positions:
            if trade_id:
                trade = next((t for t in positions if t["trade_id"] == trade_id), None)
            if trade is None and positions:
                trade = positions[-1]  # most recent open position
        if trade:
            trade["reflection"] = {"notes": notes, "rating": rating}
        else:
            # Find most recent trade for this symbol
            for t in reversed(self._trades):
                if t["symbol"] == symbol:
                    t["reflection"] = {"notes": notes, "rating": rating}
                    break

    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get trade history with optional filters.

        Args:
            symbol: Filter by symbol
            status: Filter by status ('open', 'closed')
            limit: Maximum trades to return

        Returns:
            List of trade records
        """
        trades = self._trades
        if symbol:
            trades = [t for t in trades if t["symbol"] == symbol]
        if status:
            trades = [t for t in trades if t["status"] == status]
        return trades[-limit:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Calculate performance summary across all closed trades."""
        closed = [t for t in self._trades if t["status"] == "closed"]
        if not closed:
            return {"total_trades": 0}

        pnls = [t["pnl"] for t in closed if t.get("pnl") is not None]
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p < 0]

        return {
            "total_trades": len(closed),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(closed) if closed else 0,
            "total_pnl": sum(pnls) if pnls else 0,
            "avg_pnl": sum(pnls) / len(pnls) if pnls else 0,
            "avg_win": sum(winning) / len(winning) if winning else 0,
            "avg_loss": sum(losing) / len(losing) if losing else 0,
            "best_trade": max(pnls) if pnls else 0,
            "worst_trade": min(pnls) if pnls else 0,
            "profit_factor": abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else float("inf"),
        }

    def save(self) -> None:
        """Persist journal to disk."""
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "w") as f:
            json.dump({"trades": self._trades}, f, indent=2, default=str)

    def load(self) -> bool:
        """Load journal from disk."""
        if not self._persist_path or not self._persist_path.exists():
            return False
        with open(self._persist_path) as f:
            data = json.load(f)
        self._trades = data.get("trades", [])
        # Rebuild open positions index (supports multiple positions per symbol)
        self._open_positions: Dict[str, List[Dict[str, Any]]] = {}
        for t in self._trades:
            if t["status"] == "open":
                self._open_positions.setdefault(t["symbol"], []).append(t)
        return True
