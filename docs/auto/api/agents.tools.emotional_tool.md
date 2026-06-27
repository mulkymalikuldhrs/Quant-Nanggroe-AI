# agents.tools.emotional_tool

## Class: 

Trader mood classification.

*Line: 48*

---

## Class: 

Mood category (positive/negative/neutral).

*Line: 64*

---

## Class: 

Discipline enforcement actions.

*Line: 71*

---

## Class: 

Gamification badge types.

*Line: 80*

---

## Class: 

Mood log entry.

*Line: 138*

---

## Class: 

Discipline score calculation result.

*Line: 150*

---

## Class: 

Streak tracking record.

*Line: 167*

---

## Class: 

Emotional lockout state.

*Line: 180*

---

## Class: 

Emotional intelligence and gamified discipline tool for agent consumption.

Provides mood tracking, discipline scoring, gamified enforcement
with streaks and penalties, and emotional lockout integration
with the existing risk module.

Usage::

    tool = EmotionalTool()
    entry = await tool.log_mood("trader1", MoodType.FOCUSED)
    score = await tool.get_discipline_score("trader1")
    lockout = await tool.check_lockout("trader1")

**Methods:** __init__, _get_lockout_reason, _get_reflective_exercises

*Line: 194*

---

## Function: 

*Line: 487*

---

## Function: 

*Line: 209*

---

## Function: 

Get lockout reason message.

*Line: 432*

---

## Function: 

Get reflective exercises for lockout recovery.

*Line: 452*

---

## Function: 

*Line: 34*

---

## Function: 

*Line: 37*

---

