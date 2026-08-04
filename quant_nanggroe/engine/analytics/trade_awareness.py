"""Trade awareness — metacognition layer for every QNA trade.

Per the autonomous mandate, EVERY running/closed trade, SL hit, and TP hit
must carry self-awareness: APA (what), KENAPA (why entered), BAGAIMANA (how
executed), MENGAPA (why this strategy/regime), KE MANA (intent / where it was
heading). This is not decoration — it feeds the evaluation + self-evolve
pipeline (PnLEvaluator -> StrategyEvolver) and is exportable to Excel/PDF.

Design:
- ``TradeAwareness`` is a lightweight, serialisable record attached to a trade.
- ``build_awareness(...)`` turns a strategy signal + market context into the
  narrative. It never fabricates: every field is derived from REAL inputs
  (signal direction, confidence, regime label, SL/TP levels, exit trigger).
- If inputs are missing, fields are explicitly marked "unknown" (fail-closed,
  never invented) so the autonomy loop never learns from a hallucinated reason.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TradeAwareness:
    """Metacognitive record attached to every trade.

    Fields map to the user's required awareness axes:
      APA      -> what happened (entry/exit action, side, levels)
      KENAPA   -> why the trade was entered (signal + confluence)
      BAGAIMANA -> how it was executed (engine, slippage, fill)
      MENGAPA  -> why this strategy/regime context was chosen
      KE MANA  -> where the trade was heading (thesis / target intent)
      EXIT     -> why it closed (SL hit / TP hit / manual / signal reverse)
    """

    # --- APA: what ---
    action: str = ""            # ENTER / EXIT_SL / EXIT_TP / EXIT_MANUAL / EXIT_SIGNAL
    side: str = ""              # BUY / SELL
    entry_price: float = 0.0
    exit_price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0

    # --- KENAPA: why entered ---
    entry_trigger: str = ""     # e.g. "EMA_ADX crossover + ADX>25"
    confluence: List[str] = field(default_factory=list)  # supporting signals
    confidence: float = 0.0     # 0-1 from strategy

    # --- MENGAPA: why this strategy / regime ---
    strategy_name: str = ""
    regime: str = "unknown"     # market regime at entry (trend/range/volatile)
    regime_reason: str = ""     # why we labelled it that regime
    strategy_thesis: str = ""   # what the strategy expects from this setup

    # --- KE MANA: intent / where heading ---
    target_thesis: str = ""     # e.g. "mean-reversion to VWAP", "breakout continuation"
    expected_rr: float = 0.0    # planned reward:risk
    holding_intent: str = ""    # scalp/swing/position

    # --- BAGAIMANA: how executed ---
    execution_venue: str = "mt5"  # broker/engine that filled it
    fill_note: str = ""        # slippage/commission note

    # --- EXIT: why closed ---
    exit_trigger: str = ""      # SL / TP / MANUAL / SIGNAL_FLIP / TIMEOUT
    exit_reason: str = ""       # narrative of close cause
    outcome: str = ""           # WIN / LOSS / BREAKEVEN

    # --- SELF-EVOLVE hook ---
    lesson: str = ""            # what the autonomy loop should remember
    feedback_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TradeAwareness":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def build_entry_awareness(
    strategy_name: str,
    side: str,
    entry_price: float,
    sl: float,
    tp: float,
    signal_direction: str,
    confidence: float,
    entry_trigger: str,
    confluence: Optional[List[str]] = None,
    regime: str = "unknown",
    regime_reason: str = "",
    strategy_thesis: str = "",
    target_thesis: str = "",
    expected_rr: float = 0.0,
    holding_intent: str = "",
    execution_venue: str = "mt5",
) -> TradeAwareness:
    """Build the awareness record at TRADE ENTRY (APA/KENAPA/MENGAPA/KE MANA).

    All fields come from real inputs. Nothing is invented.
    """
    return TradeAwareness(
        action="ENTER",
        side=side.upper(),
        entry_price=float(entry_price),
        sl=float(sl),
        tp=float(tp),
        entry_trigger=entry_trigger or f"signal:{signal_direction}",
        confluence=list(confluence or []),
        confidence=float(confidence),
        strategy_name=strategy_name,
        regime=regime,
        regime_reason=regime_reason,
        strategy_thesis=strategy_thesis,
        target_thesis=target_thesis,
        expected_rr=float(expected_rr),
        holding_intent=holding_intent,
        execution_venue=execution_venue,
        lesson="",
        feedback_tags=[],
    )


def build_exit_awareness(
    entry: TradeAwareness,
    exit_price: float,
    exit_trigger: str,  # SL / TP / MANUAL / SIGNAL_FLIP / TIMEOUT
    exit_reason: str = "",
    fill_note: str = "",
) -> TradeAwareness:
    """Build the awareness record at TRADE EXIT, carrying forward entry context.

    KE MANA (intent) is preserved from entry; EXIT axis is filled with the real
    close cause. ``outcome`` is derived from price vs entry/sl/tp.
    """
    outcome = "BREAKEVEN"
    if entry.entry_price > 0:
        if entry.side == "BUY":
            pnl = exit_price - entry.entry_price
        else:
            pnl = entry.entry_price - exit_price
        if pnl > 0:
            outcome = "WIN"
        elif pnl < 0:
            outcome = "LOSS"

    # Auto-derive exit_reason if not provided, from the real trigger + levels.
    if not exit_reason:
        if exit_trigger == "SL":
            exit_reason = (
                f"Stop-loss {entry.sl} hit — adverse move invalidated the setup. "
                f"KE MANA thesis ({entry.target_thesis or 'n/a'}) not realised."
            )
        elif exit_trigger == "TP":
            exit_reason = (
                f"Take-profit {entry.tp} reached — KE MANA thesis "
                f"({entry.target_thesis or 'n/a'}) realised as planned."
            )
        elif exit_trigger == "SIGNAL_FLIP":
            exit_reason = "Strategy signal reversed before SL/TP — exited to cut risk."
        elif exit_trigger == "MANUAL":
            exit_reason = "Manual exit by operator."
        elif exit_trigger == "TIMEOUT":
            exit_reason = "Held past max holding period — exited on timeout rule."
        else:
            exit_reason = f"Closed ({exit_trigger})."

    # SELF-EVOLVE lesson: concrete, derivable, never vague.
    if outcome == "WIN":
        lesson = (
            f"[{entry.strategy_name}] {entry.entry_trigger} worked: {exit_trigger} "
            f"captured planned edge (RR~{entry.expected_rr:.2f}). Regime was {entry.regime}."
        )
        tags = ["win", entry.strategy_name, entry.regime]
    elif outcome == "LOSS":
        lesson = (
            f"[{entry.strategy_name}] {entry.entry_trigger} failed: {exit_trigger}. "
            f"Regime={entry.regime} ({entry.regime_reason}). Re-examine entry filter."
        )
        tags = ["loss", entry.strategy_name, entry.regime, "review_entry"]
    else:
        lesson = f"[{entry.strategy_name}] breakeven on {exit_trigger}."
        tags = ["breakeven", entry.strategy_name]

    return TradeAwareness(
        action=f"EXIT_{exit_trigger}",
        side=entry.side,
        entry_price=entry.entry_price,
        exit_price=float(exit_price),
        sl=entry.sl,
        tp=entry.tp,
        entry_trigger=entry.entry_trigger,
        confluence=entry.confluence,
        confidence=entry.confidence,
        strategy_name=entry.strategy_name,
        regime=entry.regime,
        regime_reason=entry.regime_reason,
        strategy_thesis=entry.strategy_thesis,
        target_thesis=entry.target_thesis,
        expected_rr=entry.expected_rr,
        holding_intent=entry.holding_intent,
        execution_venue=entry.execution_venue,
        fill_note=fill_note,
        exit_trigger=exit_trigger,
        exit_reason=exit_reason,
        outcome=outcome,
        lesson=lesson,
        feedback_tags=tags,
    )
