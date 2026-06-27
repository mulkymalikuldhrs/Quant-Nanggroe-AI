# agents.council.debate

## Class: 

Structured debate mechanism for the trading council.

Implements two debate formats:
1. Bull vs. Bear researchers for investment analysis
2. Conservative vs. Neutral vs. Aggressive risk debaters

Inspired by the TradingAgents multi-debate framework.

**Methods:** __init__, run_investment_debate, run_risk_debate, run_full_debate

*Line: 152*

---

## Function: 

Initialize the council debate.

Args:
    llm: Language model for debate participants
    max_debate_rounds: Maximum bull/bear debate rounds
    max_risk_rounds: Maximum risk debate rounds

*Line: 163*

---

## Function: 

Run the bull vs. bear investment debate.

Args:
    state: Current agent state with research outputs

Returns:
    Updated DebateState with debate history and judge decision

*Line: 181*

---

## Function: 

Run the conservative/neutral/aggressive risk debate.

Args:
    state: Current agent state with trader decision

Returns:
    Updated RiskDebateState with debate history and judge decision

*Line: 262*

---

## Function: 

Run both investment and risk debates.

Args:
    state: Current agent state

Returns:
    Dictionary with both debate results

*Line: 375*

---

