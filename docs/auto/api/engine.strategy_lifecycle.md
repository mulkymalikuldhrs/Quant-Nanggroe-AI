# engine.strategy_lifecycle

## Class: 

State of a single strategy.

*Line: 20*

---

## Class: 

Darwinian strategy evolution: survival of the fittest.

Strategy states:
- ACTIVE: Strategy is live and generating trades
- HIBERNATING: Strategy paused due to excessive drawdown
- KILLED: Strategy permanently disabled due to negative expectancy

Auto-evaluation triggers:
- After MIN_TRADES_FOR_EVALUATION trades
- Negative expectancy → KILLED
- Excessive drawdown → HIBERNATING
- Recovery from hibernation → ACTIVE

**Methods:** __init__, register_strategy, update_strategy, _evaluate_lifecycle, _transition, get_active_strategies, get_strategy_report

*Line: 44*

---

## Function: 

*Line: 64*

---

## Function: 

Register a new strategy for lifecycle tracking.

Args:
    name: Strategy name.
    description: Strategy description.

Returns:
    The newly created StrategyState.

*Line: 67*

---

## Function: 

Update strategy performance after a trade.

Args:
    name: Strategy name
    pnl: Trade PnL
    is_win: Whether the trade was a win
    current_drawdown: Current drawdown percentage

Returns:
    Updated strategy state

*Line: 85*

---

## Function: 

Evaluate strategy lifecycle state.

*Line: 138*

---

## Function: 

Transition strategy to new state.

Args:
    name: Strategy name.
    new_state: Target StrategyStatus.
    reason: Reason for the transition.

*Line: 163*

---

## Function: 

Get list of active strategy names.

*Line: 186*

---

## Function: 

Get comprehensive strategy lifecycle report.

*Line: 190*

---

