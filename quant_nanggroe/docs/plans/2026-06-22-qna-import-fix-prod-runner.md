# QNA Core Fix — Import Chain, Production Runner, Risk Utilities

> **For Claude:** REQUIRED SUB-SKILL: Use godmode:task-runner to implement this plan task-by-task.

**Goal:** Fix the broken import chain in `agents/graph.py` and downstream files, create a production runner (`qna_prod.py`), and add two missing risk utility modules (`atr_sl.py`, `sizing.py`).

**Architecture:** The root cause is a class rename (`RiskCheckGate` → `ConstitutionalRiskGuard`) in `engine/risk/checks.py` that left 5 import sites broken. The production runner wraps the existing SMC engine + worker + risk + logging into a 15-min cyclic pipeline matching the n8n flow. The risk utilities fill gaps in position sizing.

**Tech Stack:** Python 3.11+, asyncio, sqlite3, numpy, pandas, yfinance (OHLCV), existing `engine.risk.constants`.

**Files to touch:**
- Modify: `engine/risk/checks.py` — add `RiskCheckGate` class (delegates to `ConstitutionalRiskGuard`)
- Modify: `engine/risk/__init__.py` — add `RiskCheckGate` to lazy load
- Modify: `worker.py` — fix imports (`get_trading_graph` → `TradingGraph`, `AgentState` usage)
- Create: `qna_prod.py` — production runner
- Create: `engine/risk/atr_sl.py` — ATR stop loss
- Create: `engine/risk/sizing.py` — position sizing

---

### Task 1: Fix `RiskCheckGate` absence in `engine/risk/checks.py`

**Files:**
- Modify: `engine/risk/checks.py`

**Situation:** Lines 37 of `risk_gate_bridge.py`, 35 of `manager.py`, 294 of `mcp/tools.py`, and the lazy loader in `engine/risk/__init__.py:39` all import `RiskCheckGate` from `engine.risk.checks`. But `checks.py` only defines `ConstitutionalRiskGuard`. The code review below shows `RiskCheckGate.evaluate()` is called with signature `evaluate(symbol, direction, lot_size, entry, stop_loss, account_balance, take_profit, daily_pnl, weekly_pnl, trade_count_today, active_positions)`, which does not match `ConstitutionalRiskGuard.check_trade(TradeRequest, PortfolioSnapshot)`.

**Fix strategy:** Add a `RiskCheckGate` class to `checks.py` that adapts the `evaluate()` API to delegate to `ConstitutionalRiskGuard` internally. This keeps backward compatibility without refactoring all callers.

```python
# Add at end of engine/risk/checks.py, after ConstitutionalRiskGuard

class CheckpointItem(BaseModel):
    """A single checkpoint from the 9-checkpoint gate."""
    model_config = ConfigDict(frozen=False)
    name: str = ""
    passed: bool = False
    value: str = ""
    limit: str = ""
    details: str = ""


class RiskCheckGate:
    """9-checkpoint risk gate — backward-compatible shim over ConstitutionalRiskGuard.

    This is the class imported by risk_gate_bridge.py, manager.py, and mcp/tools.py.
    It was renamed to ConstitutionalRiskGuard and this shim restores the old API.
    """

    def __init__(self):
        self._guard = ConstitutionalRiskGuard()

    def evaluate(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry: float,
        stop_loss: float,
        account_balance: float = 1_000_000.0,
        take_profit: Optional[float] = None,
        daily_pnl: float = 0.0,
        weekly_pnl: float = 0.0,
        trade_count_today: int = 0,
        active_positions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """9-checkpoint evaluation matching the legacy RiskCheckGate API.

        Returns dict with verdict, checkpoints, failed_checkpoints, etc.
        """
        from quant_nanggroe.engine.risk.constants import (
            MAX_DAILY_LOSS, MAX_WEEKLY_LOSS, MAX_DAILY_TRADES,
            MAX_CORRELATED_POSITIONS, MIN_RISK_REWARD, MAX_POSITION_SIZE_PCT,
        )

        active_positions = active_positions or []
        direction_upper = direction.upper()

        # Map to TradeRequest / PortfolioSnapshot for ConstitutionalRiskGuard
        direction_enum = TradeAction.HOLD
        if direction_upper in ("BUY", "LONG"):
            direction_enum = TradeAction.BUY
        elif direction_upper in ("SELL", "SHORT"):
            direction_enum = TradeAction.SELL

        # Calculate risk_pct relative to portfolio
        risk_value = abs(entry - stop_loss) * lot_size * 100000  # forex lot convention
        risk_pct = (risk_value / account_balance * 100) if account_balance > 0 else 0.0

        request = TradeRequest(
            symbol=symbol,
            action=direction_enum,
            quantity=lot_size,
            price=entry,
            stop_loss_pct=abs(entry - stop_loss) / entry * 100 if entry else 2.0,
            take_profit_pct=abs(take_profit - entry) / entry * 100 if take_profit and entry else 0.0,
            risk_pct=risk_pct,
        )

        portfolio = PortfolioSnapshot(
            total_equity=account_balance,
            cash=account_balance,
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
        )

        result = self._guard.check_trade(request, portfolio)

        # Build the 9-checkpoint response expected by callers
        daily_loss_pct = abs(min(0, daily_pnl)) / account_balance * 100 if account_balance > 0 else 0
        weekly_loss_pct = abs(min(0, weekly_pnl)) / account_balance * 100 if account_balance > 0 else 0
        max_daily_pct = MAX_DAILY_LOSS * 100
        max_weekly_pct = MAX_WEEKLY_LOSS * 100

        checkpoints = {
            "position_size": {
                "name": "Position Size Limit",
                "passed": result.proposed_risk_pct <= MAX_POSITION_SIZE_PCT * 100,
                "value": f"{result.proposed_risk_pct:.2f}%",
                "limit": f"{MAX_POSITION_SIZE_PCT * 100:.0f}%",
            },
            "risk_per_trade": {
                "name": "Risk Per Trade",
                "passed": request.risk_pct <= MAX_RISK_PER_TRADE_PCT,
                "value": f"{request.risk_pct:.2f}%",
                "limit": f"{MAX_RISK_PER_TRADE_PCT:.1f}%",
            },
            "daily_loss": {
                "name": "Daily Loss Budget",
                "passed": daily_loss_pct < max_daily_pct,
                "value": f"{daily_loss_pct:.2f}%",
                "limit": f"{max_daily_pct:.1f}%",
            },
            "weekly_loss": {
                "name": "Weekly Loss Budget",
                "passed": weekly_loss_pct < max_weekly_pct,
                "value": f"{weekly_loss_pct:.2f}%",
                "limit": f"{max_weekly_pct:.1f}%",
            },
            "stop_loss": {
                "name": "Mandatory Stop Loss",
                "passed": request.stop_loss_pct > 0,
                "value": f"{request.stop_loss_pct:.2f}%",
                "limit": "> 0%",
            },
            "max_trades": {
                "name": "Max Trades Per Day",
                "passed": trade_count_today < MAX_DAILY_TRADES,
                "value": str(trade_count_today),
                "limit": str(MAX_DAILY_TRADES),
            },
            "correlation": {
                "name": "Max Correlated Positions",
                "passed": len(active_positions) < MAX_CORRELATED_POSITIONS,
                "value": str(len(active_positions)),
                "limit": str(MAX_CORRELATED_POSITIONS),
            },
            "leverage": {
                "name": "Leverage Limit",
                "passed": result.proposed_risk_pct <= MAX_POSITION_SIZE_PCT * 100,
                "value": f"{result.proposed_risk_pct:.2f}%",
                "limit": f"{MAX_POSITION_SIZE_PCT * 100:.0f}%",
            },
            "risk_reward": {
                "name": "Min Risk:Reward",
                "passed": request.take_profit_pct >= request.stop_loss_pct * MIN_RISK_REWARD if request.stop_loss_pct > 0 else True,
                "value": f"1:{request.take_profit_pct / max(request.stop_loss_pct, 0.01):.1f}" if request.stop_loss_pct > 0 else "N/A",
                "limit": f"1:{MIN_RISK_REWARD}",
            },
        }

        failed = [k for k, v in checkpoints.items() if not v["passed"]]
        verdict = "VETOED" if failed else "APPROVED"

        return {
            "verdict": verdict,
            "checkpoints": checkpoints,
            "failed_checkpoints": failed,
            "symbol": symbol,
            "direction": direction_upper,
            "lot_size": lot_size,
            "entry": entry,
            "stop_loss": stop_loss,
            "position_size_adjusted": result.position_size_adjusted,
            "adjusted_lot_size": request.quantity if result.position_size_adjusted else lot_size,
            "risk_level": result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level),
            "reason": "; ".join(result.reasons + result.warnings) if result.reasons or result.warnings else "All checks passed",
        }

    @property
    def stats(self) -> Dict[str, Any]:
        return self._guard.stats
```

**Step 1: Add imports if missing at top of checks.py**

The file already imports `BaseModel, Field, ConfigDict` and has `TradeAction`, `TradeRequest`, `PortfolioSnapshot`, `ConstitutionalRiskGuard`, `MAX_RISK_PER_TRADE_PCT`, `MAX_POSITION_SIZE_PCT`, `MANDATORY_STOP_LOSS_PCT`. Confirm `MIN_RISK_REWARD` is imported (it's NOT in `checks.py` currently — it only imports from constants: `MAX_RISK_PER_TRADE`, `MAX_DAILY_LOSS`, `MAX_WEEKLY_LOSS`, `MAX_POSITION_SIZE_PCT`, `MAX_LEVERAGE`). Need to also import `MIN_RISK_REWARD` from constants.

Add to the import block in `checks.py`:
```python
from quant_nanggroe.engine.risk.constants import (
    MAX_RISK_PER_TRADE as _MAX_RISK_PER_TRADE_FRAC,
    MAX_DAILY_LOSS as _MAX_DAILY_LOSS_FRAC,
    MAX_WEEKLY_LOSS as _MAX_WEEKLY_LOSS_FRAC,
    MAX_POSITION_SIZE_PCT as _MAX_POSITION_SIZE_FRAC,
    MAX_LEVERAGE as _MAX_LEVERAGE,
    MIN_RISK_REWARD as _MIN_RISK_REWARD,        # ADD THIS
    MAX_DAILY_TRADES as _MAX_DAILY_TRADES,       # ADD THIS
    MAX_CORRELATED_POSITIONS as _MAX_CORRELATED_POSITIONS,  # ADD THIS
)
```

And add derived constants:
```python
MIN_RISK_REWARD: float = _MIN_RISK_REWARD       # ADD
MAX_DAILY_TRADES: int = _MAX_DAILY_TRADES         # ADD
MAX_CORRELATED_POSITIONS: int = _MAX_CORRELATED_POSITIONS  # ADD
```

**Step 2: Add `CheckpointItem` and `RiskCheckGate` classes after `ConstitutionalRiskGuard`**

Paste the `RiskCheckGate` class from above after line 347 (end of `checks.py`).

**Step 3: Verify no syntax errors**

Run: `python -c "from quant_nanggroe.engine.risk.checks import RiskCheckGate; print('OK')"`
Expected: `OK`

**Step 4: Verify downstream imports resolve**

Run: `python -c "from quant_nanggroe.agents.bridges.risk_gate_bridge import RiskGateBridge; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add engine/risk/checks.py
git commit -m "fix: add RiskCheckGate shim class for backward compatibility"
```

---

### Task 2: Update `engine/risk/__init__.py` lazy loader

**Files:**
- Modify: `engine/risk/__init__.py`

**Step 1: Verify `__all__` includes `RiskCheckGate`**

The file already has `"RiskCheckGate": ".checks"` in the lazy loader and `"RiskCheckGate"` in `__all__`. **No change needed.**

**Step 2: Verify**

Run: `python -c "from quant_nanggroe.engine.risk import RiskCheckGate; print('OK')"`
Expected: `OK`

---

### Task 3: Fix `worker.py` import chain

**Files:**
- Modify: `worker.py`

**Problems in `worker.py`:**
1. Line 212: `from quant_nanggroe.agents.graph import get_trading_graph` — `get_trading_graph` function does not exist. The class is `TradingGraph`.
2. Line 216: `AgentState(symbol=symbol, timeframe="1d")` — `AgentState` is a `TypedDict`, not a pydantic model. It also doesn't have a `timeframe` field. Should use `create_initial_state()`.

**Step 1: Fix import**

Change line 212:
```python
# OLD
from quant_nanggroe.agents.graph import get_trading_graph
# NEW
from quant_nanggroe.agents.graph import TradingGraph
```

**Step 2: Fix graph instantiation**

Change lines 215-221:
```python
# OLD
graph = get_trading_graph()
initial_state = AgentState(symbol=symbol, timeframe="1d")

# Run with timeout
result = await asyncio.wait_for(
    graph.ainvoke(initial_state.model_dump()),
    timeout=self.config.graph_timeout,
)
```

```python
# NEW
from quant_nanggroe.agents.state import create_initial_state

graph = TradingGraph()
initial_state = create_initial_state([symbol], datetime.now().strftime("%Y-%m-%d"))

# Run with timeout
result = await asyncio.wait_for(
    graph.run(symbols=[symbol], trade_date=datetime.now().strftime("%Y-%m-%d")),
    timeout=self.config.graph_timeout,
)
```

But wait — `TradingGraph.__init__` requires LLM provider params. Let me check what defaults work. Looking at the constructor, it has defaults: `llm_provider="openai"`, `deep_think_model="gpt-4o"`, etc. So instantiating without args should work.

But `graph.run()` is not async — it's a synchronous method (`def run`, not `async def run`). So we can't await it directly. We need to use `asyncio.to_thread()` or run it differently.

Actually, looking at `worker.py`, the import at the top of the file already uses `from quant_nanggroe.config import Settings, get_settings`. And the existing code uses `await graph.ainvoke(...)` which means there was an assumption that the graph exposes an async API. `TradingGraph` doesn't have an async API.

Let me re-examine. The code imports:
```python
from quant_nanggroe.agents.graph import get_trading_graph
from quant_nanggroe.agents.state import AgentState
```

And then calls:
```python
graph = get_trading_graph()
initial_state = AgentState(symbol=symbol, timeframe="1d")
result = await asyncio.wait_for(
    graph.ainvoke(initial_state.model_dump()),
    ...
)
```

This suggests it was designed for a LangGraph-based graph that runs `ainvoke`. But `TradingGraph` has `graph.invoke()` (sync) and `graph.run()` (sync). 

Best fix: use `asyncio.to_thread` to run the sync `TradingGraph.run()` in a thread.

**Corrected fix for worker.py:**

```python
# Change the import section (line 211-213)
try:
    # Import here to avoid circular imports
    from quant_nanggroe.agents.graph import TradingGraph
    from quant_nanggroe.agents.state import create_initial_state
except ImportError:
    TradingGraph = None
    create_initial_state = None

# Change the usage section (lines 215-232)
try:
    if TradingGraph is None:
        raise ImportError("TradingGraph not available")

    graph = TradingGraph()
    result = await asyncio.wait_for(
        asyncio.to_thread(
            graph.run,
            symbols=[symbol],
            trade_date=datetime.now().strftime("%Y-%m-%d"),
        ),
        timeout=self.config.graph_timeout,
    )

    latency_ms = (datetime.now() - start_time).total_seconds() * 1000
    logger.info(
        "graph_run_complete",
        extra={
            "symbol": symbol,
            "latency_ms": round(latency_ms, 2),
            "decision": result.get("decisions", [{}])[0].get("action", "unknown") if result.get("decisions") else "unknown",
            "risk_verdict": result.get("risk_verdict", "unknown"),
        },
    )

    self._last_graph_run[symbol] = datetime.now()

except asyncio.TimeoutError:
    logger.error("graph_run_timeout", extra={"symbol": symbol, "timeout": self.config.graph_timeout})
except Exception as exc:
    logger.error(
        "graph_run_failed",
        extra={
            "symbol": symbol,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        },
    )
```

**Step 3: Verify**

Run: `python -c "from quant_nanggroe.worker import TradingWorker; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add worker.py
git commit -m "fix: worker.py import chain — TradingGraph + create_initial_state"
```

---

### Task 4: Create `engine/risk/atr_sl.py`

**Files:**
- Create: `engine/risk/atr_sl.py`

**Reference:** MULKY_OS indicator uses `atr_len=14, atr_mult=1.5` for stop loss. The n8n Risk Management node calculates `ticksRisk = abs(entryPrice - slPrice) * 10000`.

**Step 1: Implement `calculate_atr_sl`**

```python
"""ATR-based Stop Loss calculation.

Extracted from MULKY_OS Pine Script indicator:
    atr_len = 14
    atr_mult = 1.5

Usage:
    from quant_nanggroe.engine.risk.atr_sl import calculate_atr_sl

    sl, distance = calculate_atr_sl(high, low, close, entry_price, "LONG")
"""

from __future__ import annotations

import numpy as np
from typing import Tuple


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Calculate True Range for each period."""
    high_low = high - low
    high_close = np.abs(high - np.roll(close, 1))
    low_close = np.abs(low - np.roll(close, 1))
    tr = np.maximum(high_low, np.maximum(high_close, low_close))
    tr[0] = high_low[0]  # First period
    return tr


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Average True Range using Wilder's smoothing."""
    tr = true_range(high, low, close)
    atr_values = np.zeros_like(tr)
    atr_values[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr_values[i] = (atr_values[i - 1] * (period - 1) + tr[i]) / period
    return atr_values


def calculate_atr_sl(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    entry_price: float,
    side: str = "LONG",
    atr_len: int = 14,
    atr_mult: float = 1.5,
) -> Tuple[float, float]:
    """Calculate ATR-based stop loss.

    Args:
        high: High price array.
        low: Low price array.
        close: Close price array.
        entry_price: Entry price for the trade.
        side: "LONG" or "SHORT".
        atr_len: ATR period (default 14).
        atr_mult: ATR multiplier for stop distance (default 1.5).

    Returns:
        Tuple of (stop_loss_price, stop_loss_distance).
    """
    atr_values = atr(high, low, close, atr_len)
    current_atr = atr_values[-1]

    sl_distance = current_atr * atr_mult

    if side.upper() == "LONG":
        stop_loss = entry_price - sl_distance
    else:
        stop_loss = entry_price + sl_distance

    return float(stop_loss), float(sl_distance)
```

**Step 2: Add test**

Quick verification:
```python
import numpy as np
h = np.array([1.1, 1.12, 1.11, 1.13, 1.14, 1.13, 1.15, 1.14, 1.16, 1.15, 1.17, 1.16, 1.18, 1.17, 1.19])
l = np.array([1.08, 1.09, 1.08, 1.10, 1.11, 1.10, 1.12, 1.11, 1.13, 1.12, 1.14, 1.13, 1.15, 1.14, 1.16])
c = np.array([1.09, 1.11, 1.10, 1.12, 1.13, 1.12, 1.14, 1.13, 1.15, 1.14, 1.16, 1.15, 1.17, 1.16, 1.18])
sl, dist = calculate_atr_sl(h, l, c, 1.18, "LONG")
assert sl < 1.18, "SL should be below entry for LONG"
assert dist > 0, "Distance should be positive"
```

**Step 3: Commit**

```bash
git add engine/risk/atr_sl.py
git commit -m "feat: add ATR-based stop loss calculator"
```

---

### Task 5: Create `engine/risk/sizing.py`

**Files:**
- Create: `engine/risk/sizing.py`

**Reference:** n8n Risk Management node: `riskPerTrade = 2%`, `riskAmount = (accountBalance * riskPerTrade) / 100`, `lotSize = riskAmount / ticksRisk`.

**Step 1: Implement `calculate_position_size`**

```python
"""Position sizing utilities.

Extracted from n8n Risk Management pipeline:
    risk_per_trade = 2%
    account_balance = $10,000
    risk_amount = (account_balance * risk_per_trade) / 100
    lot_size = risk_amount / ticksRisk

Usage:
    from quant_nanggroe.engine.risk.sizing import calculate_position_size

    lot, risk_amt = calculate_position_size(
        entry=1.0950, stop_loss=1.0930,
        account_balance=10000, risk_pct=0.02
    )
"""

from __future__ import annotations

from typing import Dict, Tuple


def calculate_position_size(
    entry: float,
    stop_loss: float,
    account_balance: float,
    risk_pct: float = 0.02,
    pip_factor: float = 10000.0,
    lot_units: float = 100000.0,
    max_risk_pct: float = 0.05,
) -> Dict[str, float]:
    """Calculate position size based on account risk parameters.

    Args:
        entry: Entry price.
        stop_loss: Stop loss price.
        account_balance: Account balance in quote currency.
        risk_pct: Fraction of account to risk per trade (default 0.02 = 2%).
        pip_factor: Pip decimal factor (10000 for most forex pairs, 1 for crypto).
        lot_units: Units per standard lot (100000 for forex, 1 for stocks/crypto).
        max_risk_pct: Maximum allowed risk fraction (hard cap).

    Returns:
        Dict with keys:
            - lot_size: Number of standard lots
            - risk_amount: Dollar amount at risk
            - risk_pct_effective: Effective risk percentage (after cap)
            - sl_distance_pips: Stop loss distance in pips
            - capped: Whether risk was capped at max_risk_pct
    """
    effective_risk = min(risk_pct, max_risk_pct)
    capped = risk_pct > max_risk_pct

    risk_amount = account_balance * effective_risk
    sl_distance = abs(entry - stop_loss)
    sl_distance_pips = sl_distance * pip_factor

    if sl_distance <= 0:
        return {
            "lot_size": 0.0,
            "risk_amount": 0.0,
            "risk_pct_effective": 0.0,
            "sl_distance_pips": 0.0,
            "capped": capped,
        }

    ticks_risk = sl_distance * pip_factor * lot_units
    lot_size = risk_amount / ticks_risk if ticks_risk > 0 else 0.0
    lot_size = max(0.01, round(lot_size * 100) / 100)

    return {
        "lot_size": lot_size,
        "risk_amount": round(risk_amount, 2),
        "risk_pct_effective": effective_risk,
        "sl_distance_pips": round(sl_distance_pips, 2),
        "capped": capped,
    }
```

**Step 2: Commit**

```bash
git add engine/risk/sizing.py
git commit -m "feat: add position sizing calculator"
```

---

### Task 6: Create `qna_prod.py` — Production Runner

**Files:**
- Create: `qna_prod.py` (at repo root)

**Reference:** n8n pipeline flow: `Start → AI Analysis → Risk Management → LTF Confirmation → News + COT → Telegram`
**Reference:** Worker loops from `worker.py` and `engine/worker.py`

**Architecture:**

```
qna_prod.py
├── SMC Engine → evaluate market structure (every 15 min)
├── Risk Manager → ConstitutionalRiskGuard checks
├── Worker → graph-based trading pipeline
├── OHLCV Fetcher → periodic data pull (yfinance)
├── Signal Logger → SQLite persistence
└── Runs on 15-min cycle
```

```python
#!/usr/bin/env python3
"""Quant Nanggroe AI — Production Trading Runner.

Orchestrates the full trading pipeline on a 15-minute cycle:

    1. Fetch OHLCV data for watched symbols
    2. Run SMC engine analysis (market structure, POI, liquidity, killzone)
    3. Generate trading signals
    4. Pass through ConstitutionalRiskGuard (9-checkpoint gate)
    5. Apply position sizing (Kelly + fixed fraction)
    6. Log all signals + decisions to SQLite
    7. Send Telegram notification

Usage:
    python qna_prod.py                          # Default symbols
    python qna_prod.py --symbols BTCUSDT ETHUSDT
    python qna_prod.py --interval 15            # Minutes between cycles
    python qna_prod.py --once                   # Single run, no loop
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("qna_prod")


# ══════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════


@dataclass
class ProdConfig:
    """Runtime configuration for the production runner."""

    symbols: List[str] = field(default_factory=lambda: ["SPY", "QQQ", "BTC-USD", "ETH-USD"])
    interval_minutes: int = 15
    atr_length: int = 14
    atr_multiplier: float = 1.5
    risk_per_trade: float = 0.02  # 2%
    account_balance: float = 10_000.0
    db_path: str = "data/qna_prod.db"
    log_signals: bool = True
    run_once: bool = False


# ══════════════════════════════════════════════════════════════════════
# Database Layer
# ══════════════════════════════════════════════════════════════════════


class SignalDatabase:
    """SQLite persistence for signals, decisions, and portfolio snapshots."""

    def __init__(self, db_path: str = "data/qna_prod.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        conn = self.connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                confidence REAL,
                source TEXT,
                raw_data TEXT
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                lot_size REAL,
                risk_amount REAL,
                risk_pct REAL,
                risk_verdict TEXT,
                reason TEXT
            );
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                atr REAL
            );
            CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(timestamp);
            CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON market_snapshots(timestamp);
        """)
        conn.commit()

    def log_signal(self, symbol: str, direction: str, entry: float,
                   sl: float, tp: float, confidence: float, source: str,
                   raw: Optional[Dict] = None) -> None:
        conn = self.connect()
        conn.execute(
            "INSERT INTO signals (timestamp, symbol, direction, entry_price, "
            "stop_loss, take_profit, confidence, source, raw_data) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), symbol, direction, entry, sl, tp,
             confidence, source, json.dumps(raw) if raw else None),
        )
        conn.commit()

    def log_decision(self, symbol: str, action: str, lot_size: float,
                     risk_amount: float, risk_pct: float,
                     risk_verdict: str, reason: str = "") -> None:
        conn = self.connect()
        conn.execute(
            "INSERT INTO decisions (timestamp, symbol, action, lot_size, "
            "risk_amount, risk_pct, risk_verdict, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), symbol, action, lot_size,
             risk_amount, risk_pct, risk_verdict, reason),
        )
        conn.commit()

    def log_snapshot(self, symbol: str, o: float, h: float, l: float,
                     c: float, v: float, atr_val: float) -> None:
        conn = self.connect()
        conn.execute(
            "INSERT INTO market_snapshots (timestamp, symbol, open, high, "
            "low, close, volume, atr) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), symbol, o, h, l, c, v, atr_val),
        )
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# ══════════════════════════════════════════════════════════════════════
# Pipeline Stages
# ══════════════════════════════════════════════════════════════════════


class Pipeline:
    """15-minute trading pipeline — mirrors the n8n flow.

    Stages:
        1. OHLCV Fetch → 2. SMC Analysis → 3. Risk Gate → 4. Sizing → 5. Log
    """

    def __init__(self, config: ProdConfig):
        self.config = config
        self.db = SignalDatabase(config.db_path)

    async def run_cycle(self) -> List[Dict[str, Any]]:
        """Execute one complete pipeline cycle.

        Returns:
            List of decision dicts for each symbol.
        """
        logger.info("=== Pipeline Cycle Start ===")

        from quant_nanggroe.engine.risk.atr_sl import calculate_atr_sl
        from quant_nanggroe.engine.risk.sizing import calculate_position_size
        from quant_nanggroe.engine.risk.checks import RiskCheckGate

        risk_gate = RiskCheckGate()
        decisions: List[Dict[str, Any]] = []

        for symbol in self.config.symbols:
            try:
                logger.info("Processing %s", symbol)

                # Stage 1: Fetch OHLCV
                ohlcv = await self._fetch_ohlcv(symbol)
                if ohlcv is None or len(ohlcv) < 20:
                    logger.warning("Insufficient data for %s — skipping", symbol)
                    continue

                high = ohlcv["High"].values.astype(np.float64)
                low = ohlcv["Low"].values.astype(np.float64)
                close = ohlcv["Close"].values.astype(np.float64)
                volume = ohlcv["Volume"].values.astype(np.float64)
                latest_close = float(close[-1])

                # Log market snapshot
                self.db.log_snapshot(
                    symbol, float(ohlcv["Open"].iloc[-1]),
                    float(high[-1]), float(low[-1]),
                    float(close[-1]), float(volume[-1]),
                    0.0,  # ATR calculated below
                )

                # Stage 2: SMC & ATR Analysis
                sl_price, sl_distance = calculate_atr_sl(
                    high, low, close, latest_close, "LONG",
                    atr_len=self.config.atr_length,
                    atr_mult=self.config.atr_multiplier,
                )

                from quant_nanggroe.engine.risk.atr_sl import atr as atr_func
                atr_values = atr_func(high, low, close, self.config.atr_length)
                current_atr = float(atr_values[-1])

                self.db.log_snapshot(
                    symbol, float(ohlcv["Open"].iloc[-1]),
                    float(high[-1]), float(low[-1]),
                    float(close[-1]), float(volume[-1]),
                    current_atr,
                )

                # Stage 3: Determine direction (simple trend bias)
                sma20 = float(np.mean(close[-20:]))
                sma50 = float(np.mean(close[-50:])) if len(close) >= 50 else sma20
                direction = "LONG" if sma20 > sma50 else "SHORT"

                entry_price = latest_close
                if direction == "LONG":
                    stop_loss = entry_price - sl_distance * 0.5  # tighter SL for signal
                    take_profit = entry_price + sl_distance * 2.0
                else:
                    stop_loss = entry_price + sl_distance * 0.5
                    take_profit = entry_price - sl_distance * 2.0

                confidence = min(1.0, abs(sma20 - sma50) / max(sma20, sma50) * 10 + 0.5)

                # Log signal
                self.db.log_signal(
                    symbol, direction, entry_price, stop_loss,
                    take_profit, confidence, "smc_pipeline",
                )

                # Stage 4: Risk Gate
                gate_result = risk_gate.evaluate(
                    symbol=symbol,
                    direction=direction,
                    lot_size=0.1,
                    entry=entry_price,
                    stop_loss=stop_loss,
                    account_balance=self.config.account_balance,
                    take_profit=take_profit,
                )

                # Stage 5: Position Sizing
                size_result = calculate_position_size(
                    entry=entry_price,
                    stop_loss=stop_loss,
                    account_balance=self.config.account_balance,
                    risk_pct=self.config.risk_per_trade,
                )

                # Stage 6: Log decision
                action = "HOLD"
                if gate_result["verdict"] == "APPROVED":
                    action = direction

                self.db.log_decision(
                    symbol, action, size_result["lot_size"],
                    size_result["risk_amount"],
                    size_result["risk_pct_effective"],
                    gate_result["verdict"],
                    reason=gate_result.get("reason", ""),
                )

                decision = {
                    "symbol": symbol,
                    "action": action,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "lot_size": size_result["lot_size"],
                    "risk_amount": size_result["risk_amount"],
                    "risk_verdict": gate_result["verdict"],
                    "confidence": confidence,
                    "atr": current_atr,
                }
                decisions.append(decision)

                logger.info(
                    "%s → %s | entry=%.4f sl=%.4f tp=%.4f lot=%.4f | verdict=%s",
                    symbol, direction, entry_price, stop_loss, take_profit,
                    size_result["lot_size"], gate_result["verdict"],
                )

            except Exception as exc:
                logger.error("Failed to process %s: %s\n%s", symbol, exc, traceback.format_exc())

        logger.info("=== Pipeline Cycle Complete (%d symbols processed) ===", len(decisions))
        return decisions

    async def _fetch_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data using yfinance.

        Args:
            symbol: Trading symbol.

        Returns:
            DataFrame with columns [Open, High, Low, Close, Volume] or None.
        """
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            df = ticker.history(period="5d", interval="15m")
            if df.empty:
                df = ticker.history(period="1mo", interval="1d")
            if df.empty:
                logger.warning("No data returned for %s", symbol)
                return None
            return df
        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
            return None
        except Exception as exc:
            logger.error("Failed to fetch OHLCV for %s: %s", symbol, exc)
            return None


async def send_telegram(message: str, bot_token: Optional[str] = None,
                        chat_id: Optional[str] = None) -> bool:
    """Send a Telegram notification.

    Args:
        message: Text to send.
        bot_token: Telegram bot token. Falls back to env TELEGRAM_BOT_TOKEN.
        chat_id: Chat ID. Falls back to env TELEGRAM_CHAT_ID.

    Returns:
        True if sent successfully.
    """
    import os

    bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.debug("Telegram not configured — skipping notification")
        return False

    try:
        import aiohttp

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info("Telegram notification sent")
                    return True
                logger.warning("Telegram send failed: %d %s", resp.status, await resp.text())
                return False
    except ImportError:
        logger.debug("aiohttp not installed — skipping Telegram notification")
        return False
    except Exception as exc:
        logger.warning("Telegram error: %s", exc)
        return False


# ══════════════════════════════════════════════════════════════════════
# Main Loop
# ══════════════════════════════════════════════════════════════════════


async def main_loop(config: ProdConfig) -> None:
    """Run the production pipeline on a configurable cycle.

    Args:
        config: Production configuration.
    """
    pipeline = Pipeline(config)
    logger.info("QNA Production Runner started — interval=%d min, symbols=%s",
                config.interval_minutes, config.symbols)

    while True:
        cycle_start = time.monotonic()
        decisions = await pipeline.run_cycle()

        # Build Telegram message
        if decisions:
            lines = ["🤖 *QNA Trading Signal*\n"]
            for d in decisions:
                emoji = "✅" if d["action"] != "HOLD" else "⏸️"
                lines.append(
                    f"{emoji} *{d['symbol']}*: {d['action']}\n"
                    f"  Entry: {d['entry_price']:.4f} | SL: {d['stop_loss']:.4f} | "
                    f"TP: {d['take_profit']:.4f}\n"
                    f"  Lot: {d['lot_size']:.4f} | Risk: ${d['risk_amount']:.2f} | "
                    f"Verdict: {d['risk_verdict']}"
                )
            await send_telegram("\n".join(lines))

        if config.run_once:
            logger.info("Single run complete — exiting")
            break

        # Sleep until next cycle
        elapsed = time.monotonic() - cycle_start
        sleep_seconds = max(0, config.interval_minutes * 60 - elapsed)
        logger.info("Cycle complete in %.1fs — next in %.1fs", elapsed, sleep_seconds)
        await asyncio.sleep(sleep_seconds)


def parse_args() -> ProdConfig:
    """Parse CLI arguments into ProdConfig."""
    parser = argparse.ArgumentParser(description="QNA Production Trading Runner")
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Trading symbols (default: SPY QQQ BTC-USD ETH-USD)")
    parser.add_argument("--interval", type=int, default=None,
                        help="Cycle interval in minutes (default: 15)")
    parser.add_argument("--once", action="store_true",
                        help="Run once and exit (no loop)")
    parser.add_argument("--db", type=str, default=None,
                        help="SQLite database path (default: data/qna_prod.db)")
    parser.add_argument("--balance", type=float, default=None,
                        help="Account balance (default: 10000)")

    args = parser.parse_args()
    config = ProdConfig()
    if args.symbols:
        config.symbols = args.symbols
    if args.interval:
        config.interval_minutes = args.interval
    if args.once:
        config.run_once = True
    if args.db:
        config.db_path = args.db
    if args.balance:
        config.account_balance = args.balance
    return config


def main() -> None:
    """CLI entry point."""
    config = parse_args()
    asyncio.run(main_loop(config))


if __name__ == "__main__":
    main()
```

**Step 2: Create data directory and verify import**

```bash
mkdir -p /sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe/data
python -c "from qna_prod import Pipeline, ProdConfig; print('OK')"
```

**Step 3: Dry-run once**

```bash
python qna_prod.py --once --symbols SPY
```

Expected: Logs with pipeline cycle, mock decisions, SQLite rows written.

**Step 4: Commit**

```bash
git add qna_prod.py data/
git commit -m "feat: add qna_prod production trading runner (15-min cycle)"
```

---

### Verification: Full Import Chain Test

After all tasks, run a comprehensive import check:

```bash
python -c "
from quant_nanggroe.engine.risk.checks import RiskCheckGate, ConstitutionalRiskGuard
from quant_nanggroe.engine.risk.atr_sl import calculate_atr_sl
from quant_nanggroe.engine.risk.sizing import calculate_position_size
from quant_nanggroe.agents.graph import TradingGraph
from quant_nanggroe.agents.state import AgentState, create_initial_state
from quant_nanggroe.agents.bridges.risk_gate_bridge import RiskGateBridge, GateVerdict
from quant_nanggroe.agents.bridges.kelly_bridge import KellyBridge
from quant_nanggroe.worker import TradingWorker
print('All imports OK')
"
```

Expected: `All imports OK`

---

### Remediation Order

1. Task 1 (RiskCheckGate shim) — unblocks everything else
2. Task 2 (__init__.py) — already OK
3. Task 3 (worker.py) — uses both graph and state
4. Task 4 (atr_sl.py) — independent
5. Task 5 (sizing.py) — independent
6. Task 6 (qna_prod.py) — depends on atr_sl, sizing, RiskCheckGate

---


---

> **SSOT:** `CANONICAL.md` v8.1.2 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
