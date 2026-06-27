# engine.execution.manager

## Class: 

Result from guard pipeline evaluation.

*Line: 31*

---

## Class: 

Execution Manager with Smart Order Routing.

Manages order execution across multiple broker connections,
enforcing guard pipelines and tracking fills.

Usage:
    manager = ExecutionManager()
    manager.add_broker(paper_broker)
    manager.add_guard(CooldownGuard(seconds=60))
    result = await manager.execute_order(order)

**Methods:** __init__, add_broker, remove_broker, set_kill_switch, _run_guards, _route_order, get_audit_log, order_manager, fill_tracker

*Line: 39*

---

## Function: 

*Line: 52*

---

## Function: 

Add a broker connection.

Args:
    broker: Broker instance.
    primary: Whether this is the primary broker.

*Line: 64*

---

## Function: 

Remove a broker connection.

*Line: 75*

---

## Function: 

Attach a KillSwitch instance for early warning checks.

Args:
    kill_switch: KillSwitch instance to query for warnings.

*Line: 81*

---

## Function: 

Run all guard checks on an order.

Args:
    order: Order to check.

Returns:
    GuardResult with allow/deny decision.

*Line: 209*

---

## Function: 

Smart order routing.

Selects the best broker for each order based on:
- Symbol availability
- Broker health
- Latency

Args:
    order: Order to route.

Returns:
    Broker name to use.

*Line: 241*

---

## Function: 

Get the execution audit log.

*Line: 259*

---

## Function: 

Get the order manager.

*Line: 264*

---

## Function: 

Get the fill tracker.

*Line: 269*

---

