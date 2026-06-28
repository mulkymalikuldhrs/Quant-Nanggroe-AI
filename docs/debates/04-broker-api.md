# Debate Record: Theme 4 — Broker API & MT5/4 Bridge

**Date:** 2026-06-28
**Presiding:** Dev Lead (w: 1.5)
**Council:** Data Engineer (w: 1.0), QT (w: 1.2), Compliance (w: 1.0)
**Questions:** Q11

---

## Round 1: Initial Stances

### Dev Lead
- **Architecture:** AlpacaExecutor (1 class, ~150 lines). Config file (YAML), no UI.
- **MT5:** Skip. Tier-3 unless client explicitly requires MT execution.
- **Priority:** P0 = paper daemon. P1 = validate 2-4 weeks. P2 = AlpacaExecutor.

### Data Engineer
- **Order:** Broker REST API before MT5 bridge (simpler, more data).
- **MT5 feasibility:** Feasible but ~100-500ms latency vs REST.
- **Requirements:** BrokerBase hardening, symbol mapping registry, execution event bus, credential vault.
- **Effort:** 1-2 weeks broker data pipeline. MT5 bridge 3-4 weeks.

### QT
- **Preference:** Binance (crypto) / IC Markets (forex). Direct API beats MT5 bridge.
- **Priority: LOW.** 0/8 positive OOS means alpha doesn't exist. Fix strategies first.
- **Requirements:** Fill simulation matching L2 queue, WebSocket sub-50ms, LIMIT/IoC/FoK/POST_ONLY.

### Compliance
- **Veto conditions:** Keys env-only. EA must not bypass risk engine. 30-day paper gate + pen test + CI/CD sign-off.
- **Requirements:** Encrypted vault, audit trail, heartbeat, circuit breaker, Chinese Wall, 2FA.
- **Block:** (a) broker key outside env, (b) EA bypassing risk engine, (c) no audit log, (d) UI creds without 2FA, (e) no paper validation, (f) no kill switch on bridge disconnect, (g) SPOF.

---

## Round 2: Dev Lead Final Decision

### Broker Choice
**Alpaca** (primary) + **IC Markets** (forex). Both via direct REST/WebSocket. Alpaca covers paper + live seamlessly. IC Markets for forex when validated strategies need it.

### Architecture
**Direct REST/WebSocket API. MT5 bridge vetoed** unless client contract explicitly requires it. Council unanimous: direct API lower latency, simpler to audit, avoids risk engine bypass.

### Configuration
**Config file (YAML). No UI.** Aligned across all council members. Simpler, faster, audit-friendly, and paper daemon should be headless by design.

### Priority
**Tier-2.** Cannot execute broker integration without validated alpha.
- P0: Deploy RegimeBased live
- P1: Validate strategies OOS, kill 7/8
- P2: Paper trading daemon (Alpaca, YAML, BrokerBase)
- P3: AlpacaExecutor after 30-day paper gate + pen test + CI/CD sign-off
- P4: IC Markets executor (if forex strategies survive)
- P5: Security hardening (encrypted vault, audit trail, heartbeat, circuit breaker, Chinese Wall, 2FA)
- P99: MT5/4 bridge (only if client contract requires)

### Security Gates (adopted from Compliance as binding)
1. Env-only keys — never in code/UI/DB/plaintext
2. 30-day paper trading gate with no anomalous fills
3. Penetration test sign-off
4. CI/CD pipeline with automated security checks
5. Encrypted credential vault
6. Audit trail on every execution event
7. Heartbeat monitoring and circuit breaker
8. Chinese Wall isolation between paper/live environments
9. EA bridge must route through QNA risk engine (zero bypass paths)
10. 2FA for any future UI config

### Vetoes
1. MT5/4 bridge vetoed absent explicit client contract requirement
2. Real-money broker access vetoed without 30-day paper gate + pen test + CI/CD sign-off
3. Hardcoded/stored credentials vetoed absolutely. Env or encrypted vault only
4. Broker integration before strategy validation vetoed — QT correct: 0/8 OOS means alpha absent

---

**Status: COMPLETE**
**Next:** Theme 5 — Logging, Monitoring & Auto-Fix (Q10, Q13)
