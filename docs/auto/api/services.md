# services

## Function: 

Ensure app.state has the _services dict initialized.

*Line: 29*

---

## Function: 

Return the shared KillSwitch singleton from app.state.

Creates and stores the instance on first access so that activation
state persists across requests.

*Line: 39*

---

## Function: 

Return the shared RiskManager singleton from app.state.

The shared instance accumulates PnL and trade-count state so that
daily/weekly limits are enforced correctly across all requests.

*Line: 59*

---

## Function: 

Return the shared MarketStateEngine singleton from app.state.

The engine maintains regime history across requests, allowing the
API to serve the most recently detected regime without recomputation.

*Line: 79*

---

## Function: 

Return the shared DecisionSynthesisEngine singleton from app.state.

The engine caches the last decision for quick status queries.

*Line: 99*

---

## Function: 

Return the shared StrategyLifecycleManager singleton from app.state.

Maintains the Darwinian strategy lifecycle across all requests.

*Line: 118*

---

## Function: 

Return the shared AutoSwitchEngine singleton from app.state.

Tracks provider health for failover routing.

*Line: 137*

---

## Function: 

Return the shared AuditLogger singleton from app.state.

Maintains the audit trail across all requests.

*Line: 156*

---

## Function: 

Eagerly initialise all shared singletons and attach them to app.state.

Called during application startup so that any import errors surface
immediately rather than on the first request.

*Line: 175*

---

