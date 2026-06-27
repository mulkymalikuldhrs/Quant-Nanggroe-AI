# agents.tools.skill_tool

## Class: 

Source of a skill definition.

*Line: 48*

---

## Class: 

Skill status.

*Line: 56*

---

## Class: 

Skill execution status.

*Line: 64*

---

## Class: 

Skill metadata — lightweight info for system prompt injection.

*Line: 76*

---

## Class: 

Full skill definition with instructions.

*Line: 88*

---

## Class: 

Result from executing a skill.

*Line: 96*

---

## Class: 

DCF valuation input parameters.

*Line: 107*

---

## Class: 

DCF valuation result.

*Line: 121*

---

## Class: 

Skill system and marketplace tool for agent consumption.

Provides skill definition, DCF valuation with sector-WACC,
skill marketplace registry, and skill execution sandbox.

Usage::

    tool = SkillTool()
    dcf = await tool.run_dcf(dcf_input)
    skills = tool.list_skills()
    result = await tool.execute_skill("dcf-valuation", {"symbol": "AAPL"})

**Methods:** __init__, _register_builtin_skills, register_skill, list_skills, get_skill, _build_sensitivity_matrix

*Line: 162*

---

## Function: 

*Line: 469*

---

## Function: 

*Line: 176*

---

## Function: 

Register built-in skills.

*Line: 181*

---

## Function: 

Register a skill in the marketplace.

Args:
    skill: SkillDefinition to register.

*Line: 213*

---

## Function: 

List available skills.

Args:
    source: Filter by source (optional).
    tag: Filter by tag (optional).

Returns:
    List of SkillMetadata.

*Line: 225*

---

## Function: 

Get a skill by name.

Args:
    name: Skill name.

Returns:
    SkillDefinition if found, None otherwise.

*Line: 246*

---

## Function: 

Build 3x3 sensitivity matrix.

*Line: 424*

---

## Function: 

*Line: 34*

---

## Function: 

*Line: 37*

---

