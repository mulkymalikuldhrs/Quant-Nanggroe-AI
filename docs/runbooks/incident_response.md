# Incident Response Runbook (Paper Phase)

**Version:** 1.0
**Scope:** Paper trading phase only (no real money)
**Owner:** Ops Manager
**Last Updated:** 2026-06-28

## Classification

| Severity | Definition | Example | Response Time |
|----------|------------|---------|---------------|
| SEV1 | Daemon crash / KillSwitch active | Daemon process dead, drawdown breach | 30 min |
| SEV2 | Data pipeline failure | Alpha Vantage API down, stale cache | 2 hours |
| SEV3 | Non-critical degradation | Single symbol data missing, audit log error | 24 hours |
| SEV4 | Informational | OOS Sharpe decay alert, strategy disabled | Next cycle review |

## SEV1: Daemon Crash

### Detection
- Watchdog (`qna-watchdog.py`) checks PID every 5 min
- `daemon.pid` stale → watchdog auto-restarts
- No watchdog → email/notify ops (not configured in paper phase)

### Response
1. Check if watchdog is running: `ps aux | grep qna-watchdog`
2. Check logs: `tail -50 /root/paper_runs/qna-paper-run-001/daemon.log`
3. Manual restart: `python3 /root/start_paper_run.py`
4. Reset watchdog: `python3 /root/start_watchdog.py`

### Recovery
- Daemon resumes from persisted state (state.json)
- Open positions are preserved
- Cycle counter continues from last saved state

### Post-Mortem
- Save full log for analysis
- Check for recurring crash pattern

## SEV1: KillSwitch Active

### Detection
- Log entry: `Kill switch activated: drawdown=XX% exceeds max=15%`
- Audit log: `[RISK] CRITICAL` entry
- No new trades executed

### Response
1. Assess drawdown: `cat /root/paper_runs/qna-paper-run-001/state.json | grep peak`
2. Check regime state: `cat /root/paper_runs/qna-paper-run-001/regime_state.json`
3. Wait for manual reset (no auto-reset in paper phase)
4. Reset kill switch if risk assessed: edit state.json → `"kill_switch_active": false`

### Prevention
- Tighten risk parameters in constants.py
- Reduce position sizing
- Add more symbols for diversification

## SEV2: Data Pipeline Failure

### Detection
- Log: `Alpha Vantage fetch failed for BTC`
- KillSwitch LEVEL_1: "data_stale"
- Watchdog: "Stale cache: BTC.csv"

### Response
1. Check API key: `echo $QNAI_ALPHA_VANTAGE_API_KEY`
2. Test Alpha Vantage: `curl "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=BTC&interval=5min&apikey=$KEY" | head`
3. Force cache refresh: watchdog auto-refreshes every 5 min
4. If API down permanently, daemon falls back to cached CSV data

### Fallback
- Alpha Vantage → cached CSV → synthetic data (last resort)
- Synthetic data triggers regime detection but prices are unrealistic

## SEV3: OOS Decay

### Detection
- Watchdog log: `OOS Decay: ... decayed: true`
- Live Sharpe significantly below backtest Sharpe (-0.335)

### Response
1. Check recent attribution: `tail -20 /root/paper_runs/qna-paper-run-001/pnl_attribution.csv`
2. Compare regime detection quality: `cat /root/paper_runs/qna-paper-run-001/regime_state.json`
3. If decay persists >7 days, consider disabling RegimeBased and returning to synthetic validation

## Resilience Features

| Feature | Mechanism | Auto-Fix? |
|---------|-----------|-----------|
| Daemon crash | Watchdog restarts within 5 min | YES |
| Stale data cache | Alpha Vantage refresh or CSV fallback | YES |
| Stuck PID | Watchdog kills processes >7 days old | YES |
| Drawdown breach | KillSwitch LEVEL_2 auto-activates | YES (non-monetary) |
| Data pipeline failure | API→CSV→synthetic cascade | YES |
| Single symbol failure | Other symbols continue trading | YES |

## Escalation

Paper phase escalation is manual:
1. Check logs
2. Check state files
3. Restart processes if needed
4. If pattern repeats, file issue at https://github.com/mulkymalikuldhr/Quant-Nanggroe-AI

## Recovery Drills

1. **Kill daemon:** `kill $(cat /root/paper_runs/qna-paper-run-001/daemon.pid)` → watchdog auto-restarts within 5 min ✓
2. **Corrupt state:** delete `state.json` → daemon starts fresh with initial capital ✓
3. **Stale data:** delete CSV cache → daemon fetches from Alpha Vantage ✓

## Improvement Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-28 | Initial paper phase runbook | Ops Manager (Theme 5) |
