# agents.bridges.kelly_bridge

## Class: 

Result from the Kelly Bridge position sizing calculation.

Attributes:
    symbol: Trading symbol.
    direction: Trade direction.
    position_size: Calculated position size in currency units.
    position_size_pct: Position size as percentage of portfolio.
    lot_size: Position size in lots (for forex) or shares (for stocks).
    kelly_fraction: Kelly criterion optimal fraction (before constraints).
    adjusted_fraction: Kelly fraction after applying constitutional limits.
    confidence_adjusted: Whether confidence was used to adjust the fraction.
    capped: Whether the position was capped at constitutional limits.
    cap_reason: Why the position was capped, if applicable.
    risk_amount: Dollar amount at risk.
    risk_pct: Risk as percentage of account.
    stop_loss_distance: Distance from entry to stop loss.
    method: Kelly method used.
    timestamp: When the calculation was performed.

**Methods:** to_dict

*Line: 48*

---

## Class: 

Bridge between the LLM agent pipeline and Kelly Criterion position sizing.

This bridge calculates optimal position sizes using the Kelly Criterion,
then applies constitutional limits to ensure no trade exceeds hardcoded
risk limits.

The Kelly calculation is CONFIRMED by the deterministic engine — it is
NOT just a suggestion from the LLM.

**Methods:** __init__, account_balance, account_balance, calculate, calculate_from_state

*Line: 107*

---

## Function: 

Convert to dictionary for agent state.

*Line: 85*

---

## Function: 

Initialize the Kelly Bridge.

Args:
    account_balance: Current account balance.
    default_method: Default Kelly method (FULL_KELLY, HALF_KELLY, QUARTER_KELLY).
    win_rate_override: Override for default win rate (if historical data available).
    avg_win_override: Override for average win amount.
    avg_loss_override: Override for average loss amount.

*Line: 122*

---

## Function: 

Current account balance.

*Line: 156*

---

## Function: 

Update account balance.

*Line: 161*

---

## Function: 

Calculate optimal position size using Kelly Criterion.

Respects constitutional limits:
- Max 0.5% risk per trade (HARDCODED)
- Position size capped at MAX_POSITION_SIZE_PCT

Args:
    symbol: Trading symbol (e.g., "AAPL", "EURUSD").
    direction: Trade direction ("BUY" or "SELL").
    confidence: Signal confidence (0-1) from the agent pipeline.
    entry: Entry price.
    stop_loss: Stop loss price.
    take_profit: Take profit price.
    win_rate: Override win rate (if historical data available).
    avg_win: Override average win amount.
    avg_loss: Override average loss amount.
    method: Kelly method override.

Returns:
    KellyBridgeResult with position sizing details.

*Line: 165*

---

## Function: 

Calculate Kelly position sizing for all signals/decisions in agent state.

Args:
    state: Current AgentState dictionary.

Returns:
    State updates with Kelly position sizing results.

*Line: 319*

---

