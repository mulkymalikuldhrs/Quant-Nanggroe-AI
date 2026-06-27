# security.audit

## Class: 

A single audit trail record.

Attributes
----------
id:
    Unique record ID (auto-incremented).
timestamp:
    When the event occurred.
agent:
    Agent or component that generated the event.
event_type:
    Type of event (e.g. ``"order_placed"``, ``"risk_check"``).
symbol:
    Trading symbol involved (optional).
action:
    Action taken (e.g. ``"buy"``, ``"sell"``, ``"approved"``).
verdict:
    Outcome or decision (e.g. ``"approved"``, ``"rejected"``).
details:
    Additional JSON-serializable details.
metadata:
    Extra metadata (e.g. order IDs, amounts).

*Line: 38*

---

## Class: 

Summary report for a single day's audit trail.

Attributes
----------
date:
    Report date.
total_events:
    Total number of events.
events_by_type:
    Breakdown by event type.
events_by_agent:
    Breakdown by agent.
events_by_verdict:
    Breakdown by verdict.
symbols_traded:
    List of symbols involved in trading events.
risk_rejections:
    Number of risk rejections.
orders_placed:
    Number of orders placed.
orders_filled:
    Number of orders filled.

*Line: 76*

---

## Class: 

Append-only audit logger backed by SQLite.

All records are insert-only. No UPDATE or DELETE operations are
provided, ensuring immutability for compliance.

Parameters
----------
db_path:
    Path to the SQLite database file. If ``None``, uses an
    in-memory database (useful for testing).
auto_create:
    Whether to auto-create the database schema on init.

Examples
--------
.. code-block:: python

    audit = AuditLogger(db_path="audit.db")
    await audit.log_event(
        agent="risk_agent",
        event_type="risk_check",
        symbol="BTC/USDT",
        verdict="approved",
    )
    records = await audit.query(symbol="BTC/USDT")

**Methods:** __init__, _ensure_schema, _get_connection, close, _row_to_record, __repr__

*Line: 118*

---

## Function: 

*Line: 146*

---

## Function: 

Create the audit table if it doesn't exist.

*Line: 159*

---

## Function: 

Get or create the database connection.

*Line: 193*

---

## Function: 

Close the database connection.

*Line: 464*

---

## Function: 

Convert a database row to an AuditRecord.

*Line: 473*

---

## Function: 

*Line: 487*

---

