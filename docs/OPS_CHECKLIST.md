# QNA Operations Checklist

**Version:** 1.0
**Last Updated:** 2026-06-27
**Owner:** Quant Ops Team

---

## 1. Daily Checklist

Run at **start of trading day** (before first daemon cycle) and **end of day** (after market close).

### Morning Startup

- [ ] **Daemon health:** `python scripts/health_check.py` — expect 6/6 passes
  - Daemon running with active PID and cycle count
  - PnL CSVs present with data rows
  - Dashboard HTML generated
  - Test runner compiles clean
  - Exchange prep script exists
  - paper_state/ populated with state files
- [ ] **Kill switch status:** Run `python -c "from quant_nanggroe.engine.risk.kill_switch import KillSwitch; ks = KillSwitch(); print('can_trade:', ks.can_trade(), '| active:', ks.is_active())"`
  - Must report `can_trade: True` and `is_active: False` for normal ops
- [ ] **State file integrity:** Verify `paper_state/state.json` loads without error
  - Check `cycle_count` increments as expected
  - Check `total_pnl` — flag if negative > 1% of initial capital
- [ ] **Auto-disable review:** Read `paper_state/auto_disable_state.json`
  - Confirm no strategies unexpectedly disabled
  - If any disabled, note Sharpe ratio that triggered it
- [ ] **Data freshness (live mode):** Check mtime on `data/cached_ohlcv/*.csv`
  - Data < 24h old: normal
  - Data 24–48h old: investigate, no kill switch expected
  - Data > 48h old: **Kill switch LEVEL_1 activated** — stale data trigger fires
- [ ] **Dashboard:** Open `dashboard/qnai_dashboard.html` — visually confirm P&L, positions, cycle count

### End-of-Day

- [ ] **PnL review:** Read `paper_state/pnl.csv` — review last row
  - `total_pnl`: acceptable range ($0–$500 for $10K portfolio under normal volatility)
  - `drawdown_pct`: must not exceed **4.0%** (early warning) or **5.0%** (hard limit)
  - `positions`: expected count matches active strategy-symbol combos
- [ ] **Cycle completion:** Confirm daemon completed its scheduled cycles
  - `cycle_count` should match expected cycles since last check
- [ ] **Log scan:** Tail daemon logs for ERROR or CRITICAL entries
  - `journalctl -u qna-paper -n 50 --no-pager` (if systemd) or check stdout
  - Flag any order failures, signal errors, or kill switch activations
- [ ] **Correlation state dump:** Read `paper_state/correlation_state.json`
  - Mean Spearman ρ across strategies — should be < 0.85
  - If ρ > 0.85, correlation herding trigger fires (suppressed in paper_mode)
- [ ] **Backup daily state:** `bash quant_nanggroe/scripts/backup.sh daily`

### Threshold Reference

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Daily PnL loss | > 0.75% | > 1.5% (LEVEL_1) | Investigate; LEVEL_1 auto-activates @ 1.5% |
| Volatility spike | > 5% daily | > 10% (LEVEL_1) | Kill switch auto-activates |
| Weekly loss | > 2% | > 4% (LEVEL_2) | Kill switch LEVEL_2 + 60 min cooldown |
| Drawdown | > 4% | > 5% (LEVEL_2/LEVEL_3) | Strategy review required |
| Correlation (mean ρ) | > 0.70 | > 0.85 | Herding trigger — diversify or reduce positions |
| Sharpe (30d trailing) | < 0.5 | < 0.3 | Auto-disable fires after 30d confirmation |
| Data staleness | 24–48h | > 48h | LEVEL_1 kill switch on live data |

---

## 2. Weekly Procedures

Run **every Monday** or after any significant market event.

### Alpha Review

- [ ] **Run alpha destruction:** `python scripts/alpha_destruction.py --symbols BTC,ETH,SOL,XRP,SPY,QQQ,IWM --export docs/alpha_report.json`
  - Verify PSR/DSR scores for all 8 strategies
  - Flag any strategy with PSR < 0.95
  - Review walk-forward OOS Sharpe if `--walk-forward` was used
- [ ] **Factor regression:** `python scripts/factor_regression.py` (requires per-strategy PnL CSV)
  - Check factor R² — alpha should have low R² to factors
  - Flag any strategy with R² > 0.5 (likely just beta, not alpha)
- [ ] **Strategy performance table:** Update Appendix A in scorecard
  - Record PSR, DSR, Sharpe, Factor R² for each strategy

### Strategy Performance

- [ ] **Per-strategy PnL breakdown:** Review individual strategy PnL contributions
  - Disable any strategy with negative PnL > 2% of capital over 20+ trading days
  - Flag strategies with Sharpe < 0.3 for auto-disable review
- [ ] **Auto-disable state:** Read `paper_state/auto_disable_state.json`
  - Confirm trailing 30-day Sharpe for each strategy
  - If a strategy approaches the 0.3 threshold, decide: retune or accept disable
- [ ] **Slippage calibration refresh:** If market volatility regime has changed:
  - `python scripts/calibrate_slippage.py --symbols BTC ETH SOL XRP`
  - Update docs/SLIPPAGE_CALIBRATION.md with new recommendations

### Correlation Check

- [ ] **Strategy correlation heatmap:** Read `paper_state/correlation_state.json`
  - Confirm no pair has Spearman ρ > 0.85
  - If cluster of highly correlated strategies exists (>0.7), assess concentration risk
- [ ] **Herding backtest:** Review last 7 days of correlation state history
  - Count any correlation herding events and their resolution

### Infrastructure

- [ ] **Backup rotation:** `bash quant_nanggroe/scripts/backup.sh rotate`
- [ ] **Test suite:** `python -m pytest tests/ -x --tb=short -q` — confirm zero regressions
- [ ] **Orphan cleanup review:** Check `docs/ORPHAN_TRIAGE.md` — flag any newly dead files
- [ ] **Disk usage:** Verify paper_state/ and data/ directories aren't growing unbounded
  - `du -sh paper_state/ data/cached_ohlcv/`

---

## 3. Emergency Procedures

### 3.1 Kill Switch Activation

When any threshold is breached, the system auto-activates. Manual activation takes priority.

**To activate manually:**
```python
from quant_nanggroe.engine.risk.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchTrigger
ks = KillSwitch()
ks.activate(level=KillSwitchLevel.LEVEL_3, reason="manual override",
            trigger=KillSwitchTrigger.MANUAL, auto_activated=False)
```

**Verification:**
- `ks.can_trade()` returns `False`
- Daemon skips trade execution until deactivated
- All strategy-symbol combos halt immediately

**To deactivate (only after root cause resolved):**
```python
ks.deactivate()
```

**Level escalation path:**

| Level | Threshold | Duration | De-escalation |
|-------|-----------|----------|---------------|
| LEVEL_1 | 1.5% daily loss / 10% vol spike | 30 min cooldown | Auto-deactivates after cooldown if no new breach |
| LEVEL_2 | 4% weekly loss / 5% drawdown | 60 min cooldown | Ops team must review before deactivation |
| LEVEL_3 | Full shutdown (requires approval) | Indefinite | Requires explicit ops lead approval to deactivate |

**Post-activation process:**
1. Identify which threshold was breached (check daemon log)
2. Pause all trading — do NOT deactivate until root cause is understood
3. Run health check: `python scripts/health_check.py`
4. Review PnL CSV for anomalous rows
5. Document the trigger and resolution in ops log
6. Only deactivate after fix is verified

### 3.2 Disaster Recovery Drill

**Quarterly requirement:** Full DR drill every 90 days.

**Drill command:**
```bash
python scripts/disaster_recovery_drill.py          # full drill
python scripts/disaster_recovery_drill.py --quick  # path-only verification
python scripts/disaster_recovery_drill.py --keep-backup  # no restore
```

**Phase breakdown:**
1. **Backup** — saves `data/cached_ohlcv/`, `paper_state/`, and all `.db` files
2. **Destruction** — deletes all critical files, verifies deletion
3. **Recovery** — recreates empty directories, regenerates cached data, smoke tests KillSwitch + strategies
4. **Verification** — checks directory structure, CSV presence, KillSwitch ops, strategy imports
5. **Restore** — copies everything back from backup (skipped with `--keep-backup`)

**Acceptance criteria:**
- All 4 verification checks pass (V1–V4)
- Recovery completes within **60 minutes** (hard SLA)
- No critical failures
- Non-critical failures tolerated but must be documented

**If drill fails:**
- Document which phase failed and why
- Retry with `python scripts/disaster_recovery_drill.py --backup-dir /tmp/qna-drill-retry`
- Escalate to engineering if it fails twice

**Real recovery (not drill):**
```bash
python scripts/disaster_recovery_drill.py --keep-backup --backup-dir /path/to/real/backup
```
Note: In real recovery, do NOT run Phase 2 (Destruction). Run backup → manually restore from the actual backup set → verify.

### 3.3 Data Failure

**Symptom:** Cache miss warnings in daemon log, KillSwitch DATA_STALE trigger, zero PnL after cycles.

**Triage:**
1. Check data dir: `ls data/cached_ohlcv/` — are CSV files present?
2. Check freshness: `stat data/cached_ohlcv/BTC.csv` — compare mtime to current time
3. Run fallback test: `python scripts/test_data_fallback.py`

**Resolution:**
- **Partial failure** (one symbol missing): Daemon auto-falls back to synthetic data for that symbol
- **Complete failure** (all cached data missing or >48h stale):
  1. Daemon auto-activates LEVEL_1 kill switch (DATA_STALE trigger)
  2. Regenerate cache: run alpha_destruction with desired symbols
  3. Verify data freshness, then deactivate kill switch
- **Live API failure** (real API keys in use):
  1. Daemon auto-failover to secondary provider (CCXT → CoinGecko → yfinance)
  2. If all providers fail, daemon falls back to cached data
  3. If cache also stale, LEVEL_1 kill switch fires

### 3.4 Daemon Crash

**Symptom:** Health check reports daemon not running, stale PID file.

**Resolution:**
1. Verify crash: `cat paper_state/daemon.pid` → check if process exists
2. Check logs for fatal errors
3. Restart: `bash qna-paper.sh`
4. After restart, verify state is consistent:
   - `paper_state/state.json` loaded correctly (cycle count continues from where it was)
   - Broker state loaded from PaperExchangeBroker persistence
5. If state is corrupted: restore from `quant_nanggroe/scripts/backup.sh restore`

---

## 4. Capital Readiness Policy

### 4.1 Position Sizing Limits

All position sizes calculated via **Kelly criterion** with volatility scaling and a **hard cap**.

| Parameter | Value | Source |
|-----------|-------|--------|
| Kelly fraction | `min(confidence * 0.25, 0.25)` | `qna-paper-daemon.py:242` |
| Target volatility | 25% annualized (configurable) | `--vol-target 0.25` |
| Max leverage | 1.0x (no margin) | `--max-leverage 1.0` |
| Max position per symbol | 25% of capital | Kelly hard cap |
| Max single-strategy allocation | 100% (but limited by per-symbol cap) | — |

**Violation rules:**
- Any computed position > 25% of capital is clamped to 25%
- No short selling (spot-only paper broker)
- Round-trip cost of 32.9 bps is applied to every fill (14 bps slippage + 8 bps commission × 2)

### 4.2 Max Drawdown Policy

| Threshold | Level | Action |
|-----------|-------|--------|
| < 2% | Green | Normal operations, no restriction |
| 2–3.99% | Amber | Monitoring increased, review all open positions |
| 4.0% | Early warning (80% of LEVEL_2) | Prepare kill switch review, notify ops lead |
| 5.0% | Hard limit (LEVEL_2/3) | **Mandatory halt** — kill switch activates |

**Drawdown calculation:**
```
drawdown_pct = (total_value - peak_capital) / peak_capital × 100
```
Calculated every cycle in `qna-paper-daemon.py:285`.

### 4.3 Capital Allocation Tiers

| Tier | Capital Range | Strategy Count | Max Symbols | Notes |
|------|---------------|----------------|-------------|-------|
| Sandbox | $0–$10K | 2 | 2 | Paper trading, synthetic data |
| Development | $10K–$50K | 4 | 4 | Paper trading, live data |
| Staging | $50K–$250K | 6 | 7 | Live data, slippage calibration |
| Production | $250K+ | 8 | 10+ | Requires full security audit + DR cert |

Current status: **Sandbox** ($34K paper portfolio, 8 strategy-symbol combos — exceeds tier bounds; formalize at next review).

### 4.4 Capital Readiness Gates

Before moving between tiers, the following must be satisfied:

- [ ] **Sandbox → Development:**
  - All 8 strategies passing PSR > 0.95
  - Factor regression executed with R² < 0.5 for all active strategies
  - 30+ days of paper trading without critical incidents
  - Kill switch test: manual activation/deactivation verified

- [ ] **Development → Staging:**
  - Real API keys obtained and failover-tested
  - Security audit: 0 critical findings
  - DR drill passed with < 60 min recovery
  - Auto-disable manager tested with historical data

- [ ] **Staging → Production:**
  - Full security audit with 0 high+ findings
  - DR drill passed 2 consecutive quarters
  - Correlation monitor tested with real market regime
  - Operations checklist in use for 90+ days

### 4.5 Emergency Capital Actions

| Event | Action |
|-------|--------|
| Daily loss > 1.5% | LEVEL_1 auto-halt; no new trades for 30 min |
| Weekly loss > 4% | LEVEL_2 halt; ops review before resuming |
| Drawdown > 5% | LEVEL_3 halt; ops lead must approve deactivation |
| Correlation herding (ρ > 0.85) | Auto-disable correlated strategies |
| Strategy Sharpe < 0.3 for 30d | Auto-disable that strategy |
| Any 2+ levels activated simultaneously | Escalate to ops lead immediately |

---

## 5. Reporting & Escalation

### Daily Reporting

- **Ops log entry** (end of day): 1-line summary of PnL, kill switch state, any flags
- **Health check output:** Saved to `paper_state/health_check_YYYY-MM-DD.json`

### Weekly Reporting

- **Alpha report:** `docs/alpha_report.json` updated via alpha_destruction.py
- **Strategy performance sheet:** Updated with per-strategy PnL and Sharpe
- **Risk summary:** Max drawdown, correlation state, kill switch activations this week

### Escalation Contacts

| Issue | Contact | Response SLA |
|-------|---------|--------------|
| Kill switch auto-activation | Ops lead | 1 hour |
| DR drill failure | Engineering lead | 4 hours |
| Data pipeline outage | Data engineer | 2 hours |
| Security finding (critical) | Security lead | Immediate |
| Strategy auto-disable | Quant research | 24 hours |

---

## 6. Appendix: Quick Reference

### Common Commands

```bash
# Health check
python scripts/health_check.py

# Status dashboard
bash qna-status.sh

# Paper daemon start / stop
bash qna-paper.sh          # start
bash qna-stop.sh           # stop

# Backup
bash quant_nanggroe/scripts/backup.sh all
bash quant_nanggroe/scripts/backup.sh daily

# Disaster recovery drill
python scripts/disaster_recovery_drill.py

# Alpha validation
python scripts/alpha_destruction.py --symbols BTC,ETH,SOL,XRP,SPY,QQQ,IWM

# Regression test
python -m pytest tests/ -x --tb=short -q
```

### Key File Locations

| File | Purpose |
|------|---------|
| `paper_state/state.json` | Persistent daemon state (cycle count, PnL, peak capital) |
| `paper_state/pnl.csv` | Per-cycle PnL log (append-only) |
| `paper_state/auto_disable_state.json` | Strategy auto-disable tracker (30d Sharpe) |
| `paper_state/correlation_state.json` | Strategy correlation monitor (Spearman ρ) |
| `paper_state/daemon.pid` | Daemon process ID |
| `paper_state/tuned_params.json` | Tuned strategy parameters |
| `data/cached_ohlcv/*.csv` | Cached OHLCV data files (7 symbols) |
| `data/compliance.db` | ComplianceJournal (append-only SQLite) |

---

*End of operations checklist. Update this document whenever thresholds, procedures, or system architecture change.*
