# HERMES QUANT OPERATING SYSTEM - AUTONOMOUS UPGRADE PLAN

## Vision: From Research Lab to Full Autonomous

This document outlines the step-by-step upgrade path from the current Research Lab deployment (Stage 1) to Full Autonomous operation (Stage 5). Each stage has strict entry criteria, and no stage may be skipped. Progression requires documented performance metrics and explicit owner approval.

---

## Current State Assessment

| Dimension | Current Status | Target |
|-----------|---------------|--------|
| Deployment Stage | Stage 1 (Research Lab) | Stage 5 (Full Autonomous) |
| Trading Mode | Paper only | Live autonomous execution |
| Agent Count | 21 tools active | 25+ with venue adapters |
| Execution Venues | Paper only | MT5, OANDA, Binance, Solana |
| LLM Providers | NVIDIA + Groq + OpenCode | + Claude + Gemini + local models |
| Risk Framework | Hardcoded rules, Risk Officer VETO | + Correlation monitor, adaptive sizing |
| Monitoring | Telegram + logs | + Web dashboard + real-time alerts |
| Strategy Evolution | Manual review | Darwinian auto-evolution |
| Alpha Library | Not integrated | 450+ alphas from Vibe-Trading |

---

## Stage 1: Research Lab (CURRENT)

**Objective:** Validate system architecture, tool integration, and risk framework in paper trading mode.

### Current Capabilities
- 21 trading tools across 5 layers operational
- Telegram bot interface for all commands
- Multi-provider LLM with automatic failover
- 3-layer auto-restart infrastructure (watchdog + keeper + on-boot)
- Hardcoded risk rules with Risk Officer FULL VETO
- Session memory with persistent JSON + Markdown

### Tasks to Complete Before Stage 2

| # | Task | Priority | Status | Estimated Effort |
|---|------|----------|--------|------------------|
| 1.1 | Implement autonomous market scanning (no user prompt needed) | HIGH | Planned | 3 days |
| 1.2 | Add correlation monitor (<0.70 between active positions) | HIGH | Planned | 2 days |
| 1.3 | Integrate Vibe-Trading Alpha Zoo (452 alphas) | MEDIUM | Planned (PR-004) | 5 days |
| 1.4 | Add web dashboard for monitoring (basic) | MEDIUM | Planned | 7 days |
| 1.5 | Implement comprehensive unit tests for all tools | HIGH | Planned | 5 days |
| 1.6 | Add configuration validation on startup | LOW | Planned | 1 day |
| 1.7 | Implement structured logging with JSON format | LOW | Planned | 2 days |

### Stage 2 Entry Criteria
- [ ] Minimum 30 consecutive days of paper trading
- [ ] No system crashes exceeding 1-hour downtime
- [ ] All 21 tools passing functional tests
- [ ] Autonomous scanning operational for at least 7 days
- [ ] Correlation monitor implemented and tested
- [ ] Owner sign-off with documented paper trading PnL

---

## Stage 2: Paper Trading (Simulated Execution with Real Data)

**Objective:** Run full simulated execution using real market data. Validate end-to-end pipeline from data ingestion to simulated order placement with realistic fills.

### Upgrade Tasks

| # | Task | Priority | Dependency | Estimated Effort |
|---|------|----------|------------|------------------|
| 2.1 | Implement realistic fill simulation (slippage model) | HIGH | None | 3 days |
| 2.2 | Add dynamic spread modeling per venue | HIGH | 2.1 | 2 days |
| 2.3 | Implement latency simulation (100-500ms) | MEDIUM | 2.1 | 1 day |
| 2.4 | Add order book depth analysis for fill probability | MEDIUM | 2.1 | 3 days |
| 2.5 | Implement PnL tracking with swap/commission modeling | HIGH | None | 2 days |
| 2.6 | Add backtesting engine integration with paper results | MEDIUM | 2.5 | 2 days |
| 2.7 | Implement Darwinian strategy evolution (auto-KILL) | HIGH | None | 3 days |
| 2.8 | Add edge decay detection alerts | MEDIUM | 2.7 | 2 days |
| 2.9 | Implement multi-timeframe analysis pipeline | HIGH | None | 3 days |
| 2.10 | Add Telegram notification for high-confluence setups | MEDIUM | 1.1 | 1 day |

### Key Architecture Changes

```
BEFORE (Stage 1):
  User Command → Agent → LLM Response → User

AFTER (Stage 2):
  Scheduled Scan → Market Data → Analysis Pipeline →
  Pressure Normalization → Decision Engine → Risk Officer →
  Simulated Execution → Journal → Audit →
  Telegram Notification (results only)
```

### Stage 3 Entry Criteria
- [ ] Minimum 60 consecutive days of paper trading
- [ ] Simulated Sharpe ratio > 0.5 over the period
- [ ] Maximum simulated drawdown < 5%
- [ ] No risk rule violations (all rejections logged)
- [ ] Darwinian evolution operational (at least 1 strategy auto-KILLED)
- [ ] 90%+ system uptime (less than 72 hours total downtime)
- [ ] Owner sign-off with documented simulated performance

---

## Stage 3: Micro Live (Real Money, 0.01 Lot Maximum)

**Objective:** Execute real trades with maximum position size of 0.01 lots. Validate that the system performs identically in live conditions as in paper trading.

### Upgrade Tasks

| # | Task | Priority | Dependency | Estimated Effort |
|---|------|----------|------------|------------------|
| 3.1 | Implement MT5 live connection | CRITICAL | None | 5 days |
| 3.2 | Implement OANDA live connection | HIGH | None | 5 days |
| 3.3 | Implement Binance live connection | HIGH | None | 5 days |
| 3.4 | Add position size hardcap (0.01 lot enforcement) | CRITICAL | None | 1 day |
| 3.5 | Implement real-time PnL tracking from broker | HIGH | 3.1-3.3 | 3 days |
| 3.6 | Add broker connection health monitoring | HIGH | 3.1-3.3 | 2 days |
| 3.7 | Implement emergency close-all-positions command | CRITICAL | None | 1 day |
| 3.8 | Add trade confirmation logging (signed) | HIGH | None | 2 days |
| 3.9 | Implement AutoHedge swarm pipeline for crypto (PR-005) | MEDIUM | 3.3 | 7 days |
| 3.10 | Add Solana venue support via Jupiter API | MEDIUM | 3.9 | 5 days |

### Critical Safety Additions

```python
# STAGE 3: Hardcoded position size cap (ADDED to risk_officer_tool.py)
MAX_MICRO_LOT = 0.01  # NO OVERRIDE - hardcoded for Stage 3

def check_trade(self, symbol, direction, lot_size, entry, sl):
    # Existing 9 checkpoints...
    if lot_size > MAX_MICRO_LOT:
        return {
            'verdict': 'VETO',
            'reason': f'LOT SIZE CAP: {lot_size} > {MAX_MICRO_LOT} (Stage 3 micro limit)',
            'checkpoint_failed': 10  # New checkpoint
        }
```

### Stage 4 Entry Criteria
- [ ] Minimum 90 consecutive days of micro live trading
- [ ] Positive real PnL over the period
- [ ] No risk rule violations
- [ ] Slippage within 10% of paper trading estimates
- [ ] Kill switch tested and verified (manual test required)
- [ ] Emergency close-all verified on each venue
- [ ] Owner sign-off with documented live performance

---

## Stage 4: Semi-Autonomous (Requires User Confirmation for Real Trades)

**Objective:** System generates and validates trade setups autonomously, but requires explicit user confirmation before executing any real trade.

### Upgrade Tasks

| # | Task | Priority | Dependency | Estimated Effort |
|---|------|----------|------------|------------------|
| 4.1 | Implement trade approval workflow via Telegram | CRITICAL | None | 3 days |
| 4.2 | Add trade preview message with full details | HIGH | 4.1 | 2 days |
| 4.3 | Implement approval timeout (auto-reject after 5 min) | HIGH | 4.1 | 1 day |
| 4.4 | Add position size scaling (0.01 → calculated) | HIGH | 3.4 | 2 days |
| 4.5 | Implement partial close functionality | MEDIUM | None | 3 days |
| 4.6 | Add trailing stop loss implementation | MEDIUM | None | 3 days |
| 4.7 | Implement break-even stop management | MEDIUM | 4.6 | 1 day |
| 4.8 | Add web dashboard v2 (real-time positions, PnL chart) | MEDIUM | 1.4 | 10 days |
| 4.9 | Implement Claude API integration | LOW | None | 2 days |
| 4.10 | Implement Gemini API integration | LOW | None | 2 days |
| 4.11 | Add local model fallback (Ollama integration) | LOW | None | 3 days |

### Trade Approval Workflow

```
System detects high-confluence setup
    │
    ▼
Full analysis pipeline runs (L1 → L2 → L3)
    │
    ▼
Risk Officer APPROVES
    │
    ▼
Telegram message sent to user:
    "TRADE APPROVAL REQUEST
     Symbol: XAUUSD
     Direction: BUY
     Entry: 2345.50
     SL: 2335.50 (10 pips, 0.4% risk)
     TP1: 2365.50 (1:2 R:R)
     TP2: 2385.50 (1:4 R:R)
     TP3: 2405.50 (1:6 R:R)
     Confluence: 4/5
     Lot Size: 0.05
     Risk: 0.45% of account

     Type APPROVE to execute, REJECT to cancel
     Auto-reject in 5:00"

    │
    ├── User types "APPROVE" → Execute trade
    ├── User types "REJECT" → Cancel, log reason
    └── 5 minutes pass → Auto-reject, log timeout
```

### Stage 5 Entry Criteria
- [ ] Minimum 180 consecutive days of semi-autonomous trading
- [ ] Consistent positive PnL over last 90 days
- [ ] Sharpe ratio > 1.0 over the period
- [ ] Maximum drawdown < 8%
- [ ] Win rate > 45% with average win/loss ratio > 1.5
- [ ] Zero unauthorized trades (all required approval)
- [ ] Risk Officer VETO rate < 30% (system generates quality setups)
- [ ] Darwinian evolution stable (no frequent strategy churn)
- [ ] All venues verified with live positions
- [ ] Owner sign-off with comprehensive performance documentation

---

## Stage 5: Full Autonomous (Agent Executes Independently)

**Objective:** Agent executes trades independently within hardcoded risk limits. User retains emergency override and kill switch, but day-to-day trading is fully automated.

### Upgrade Tasks

| # | Task | Priority | Dependency | Estimated Effort |
|---|------|----------|------------|------------------|
| 5.1 | Remove approval requirement for Risk Officer-approved trades | CRITICAL | Stage 4 completion | 1 day |
| 5.2 | Implement adaptive position sizing based on volatility | HIGH | None | 3 days |
| 5.3 | Add portfolio-level risk management (total exposure cap) | HIGH | None | 3 days |
| 5.4 | Implement multi-strategy portfolio allocation | HIGH | 2.7 (Darwinian) | 5 days |
| 5.5 | Add market regime-adaptive strategy switching | MEDIUM | 5.4 | 3 days |
| 5.6 | Implement continuous learning loop (post-trade → strategy refinement) | HIGH | None | 5 days |
| 5.7 | Add performance degradation auto-pause | HIGH | None | 2 days |
| 5.8 | Implement automated reporting (daily/weekly/monthly) | MEDIUM | None | 3 days |
| 5.9 | Add web dashboard v3 (full control panel) | MEDIUM | 4.8 | 10 days |
| 5.10 | Implement Docker containerization for VPS deployment | LOW | None | 3 days |

### Autonomous Safeguards

Even at Full Autonomous, the following safeguards remain active and cannot be disabled:

1. **Hardcoded Risk Limits**: 0.5%/trade, 1%/day, 3%/week - NEVER changes
2. **Risk Officer VETO**: Every trade must pass 9+ checkpoints
3. **Kill Switch**: Auto-triggers on any limit breach
4. **Daily Performance Review**: System generates daily report regardless
5. **Weekly Audit**: Post-trade auditor runs weekly analysis
6. **Strategy Health Monitor**: Auto-pauses if edge decay detected
7. **Emergency Close-All**: User can halt everything at any time
8. **Notification Requirement**: Every executed trade must be reported to user within 30 seconds

### Performance Degradation Auto-Pause

```
IF weekly_pnl < -1.5%:
    → Reduce position size by 50%
    → Increase confluence requirement to 4/5
    → Send alert to user

IF weekly_pnl < -2.5%:
    → Pause new trade generation
    → Only allow closes
    → Send URGENT alert to user

IF weekly_pnl >= -3.0% (weekly limit):
    → Kill switch activates
    → All positions closed
    → System enters NO_TRADE until manual reset
```

---

## Timeline Estimate

| Stage | Duration | Cumulative Time | Key Milestone |
|-------|----------|-----------------|---------------|
| Stage 1 (current) | 1-2 months | 0-2 months | Autonomous scanning + Alpha Zoo |
| Stage 2 | 2-3 months | 2-5 months | Simulated Sharpe > 0.5 |
| Stage 3 | 3-4 months | 5-9 months | First real money trade (0.01 lot) |
| Stage 4 | 4-6 months | 9-15 months | Semi-autonomous with approval |
| Stage 5 | Ongoing | 15+ months | Full autonomous operation |

**Total estimated time to Full Autonomous: 15-18 months from today**

---

## Technology Roadmap

### Phase 1: Foundation (Months 1-3)
- Autonomous scanning loop
- Correlation monitor
- Unit test coverage > 80%
- Alpha Zoo integration (PR-004)

### Phase 2: Simulation (Months 3-6)
- Realistic fill simulation
- Darwinian strategy evolution
- Multi-timeframe analysis
- Web dashboard v1

### Phase 3: Micro Live (Months 6-9)
- Broker connections (MT5, OANDA, Binance)
- Position size hardcap
- Emergency controls
- AutoHedge swarm pipeline (PR-005)

### Phase 4: Semi-Auto (Months 9-15)
- Trade approval workflow
- Position management (trailing stops, partial closes)
- Multi-LLM provider support
- Web dashboard v2

### Phase 5: Full Autonomous (Months 15+)
- Remove approval gate
- Adaptive position sizing
- Portfolio-level risk management
- Continuous learning loop
- Docker containerization
- Web dashboard v3

---

## Rollback Procedures

### Stage Rollback Rules

If performance degrades significantly at any stage, the system MUST roll back to the previous stage:

| Condition | Rollback Action |
|-----------|----------------|
| 3 consecutive losing weeks at Stage 3+ | Roll back to previous stage |
| Drawdown exceeds 8% at any stage | Immediate halt + review |
| Risk Officer VETO rate > 60% | System generating poor setups, review strategy |
| System downtime > 24 hours in a week | Infrastructure not stable, fix before proceeding |
| Any unauthorized trade executed | Immediate halt + full audit |

### Emergency Procedures

1. **User types `/kill`** → Kill switch activates, all positions closed
2. **User types `/halt`** → New trades paused, existing positions kept open
3. **User types `/rollback`** → System reverts to previous stage configuration
4. **Daily PnL limit breach** → Automatic kill switch, no user action needed
5. **Weekly PnL limit breach** → Automatic kill switch, requires manual reset

---

**Document maintained by Mulky Malikul Dhaher**
**Repository: github.com/mulkymalikuldhrs/hermes-quant-os**
