# memory.session

## Class: 

Session-level memory for agent context preservation.

Stores agent outputs, market state, and decisions within a trading session.
Supports both in-memory and file-based persistence.

Usage:
    memory = SessionMemory(session_id="session_2024_01_01")
    memory.store("researcher", {"analysis": "BTC trending upward"})
    context = memory.get_context("researcher")

**Methods:** __init__, session_id, store, get_context, get_latest, get_all_context, clear, save, load, summary

*Line: 18*

---

## Function: 

Initialize session memory.

Args:
    session_id: Unique session identifier
    persist_dir: Directory for file-based persistence
    max_entries: Maximum entries per agent before compaction

*Line: 31*

---

## Function: 

Get session ID.

*Line: 55*

---

## Function: 

Store agent output in session memory.

Args:
    agent_name: Name of the agent producing the output
    data: Output data to store

*Line: 59*

---

## Function: 

Get recent context for an agent.

Args:
    agent_name: Agent name to get context for
    limit: Maximum number of entries to return

Returns:
    List of recent entries for the agent

*Line: 82*

---

## Function: 

Get the most recent entry for an agent.

*Line: 100*

---

## Function: 

Get all stored context.

*Line: 105*

---

## Function: 

Clear memory for a specific agent or all agents.

*Line: 109*

---

## Function: 

Persist session memory to disk.

*Line: 116*

---

## Function: 

Load session memory from disk.

*Line: 131*

---

## Function: 

Get a summary of stored entries per agent.

*Line: 146*

---

