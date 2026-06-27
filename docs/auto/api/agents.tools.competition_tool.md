# agents.tools.competition_tool

## Class: 

Agent performance tier.

*Line: 49*

---

## Class: 

A/B experiment status.

*Line: 58*

---

## Class: 

Team mission status.

*Line: 67*

---

## Class: 

Registered agent profile.

*Line: 80*

---

## Class: 

Signal quality assessment.

*Line: 98*

---

## Class: 

A/B experiment for comparing strategies.

*Line: 114*

---

## Class: 

Team mission for collaborative trading.

*Line: 135*

---

## Class: 

Leaderboard entry.

*Line: 148*

---

## Class: 

Agent competition and scoring tool for agent consumption.

Provides agent registration, leaderboard, A/B experiments,
signal quality scoring, and team mission management.

Usage::

    tool = CompetitionTool()
    agent = await tool.register_agent("my-strategy", "My Strategy")
    score = await tool.score_signal("agent1", "AAPL", "BUY", 150.0)
    lb = await tool.get_leaderboard()

**Methods:** __init__, _calculate_overall_score

*Line: 164*

---

## Function: 

*Line: 545*

---

## Function: 

*Line: 178*

---

## Function: 

Calculate composite overall score for an agent.

*Line: 525*

---

## Function: 

*Line: 35*

---

## Function: 

*Line: 38*

---

