import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
subprocess.run(["git", "add", "-A"], capture_output=True, text=True, cwd=root)
r = subprocess.run(["git", "commit", "-m",
    "fix(P0/P1): unify MT5 symbol translation + kill-switch escalation guard + restore sync-dropped files\n\n"
    "P0 mt5_adapter.get_price: route through _mt5_symbol() (same translator as order\n"
    "  path). Old MT5_SYMBOL_MAP(bare)+.upper() fallback turned EURUSD.vx -> EURUSD.VX\n"
    "  -> tick None -> 0.0 -> orders marked REJECTED/ZERO_PRICE despite broker fill.\n"
    "P1 kill_switch.activate: escalation-only guard (reconcile first; lower level can\n"
    "  never flush-overwrite a higher shared level - weekly breach no longer lost)\n"
    "P1 risk manager: _ensure_reconciled before auto-activate; declare RiskState.unrealized_pnl\n"
    "P1 data manager: stale-cache fallback BOUNDED via QNA_MAX_STALE_MINUTES (default 60m)\n"
    "P1 scheduler: zombie-state guard (_running=False after loop crash; was lying healthy)\n"
    "RESTORED (dropped by phase5 sync): config_manager, config_files route + mount,\n"
    "  account_discovery (Valetax paths), builder discovered-authoritative,\n"
    "  connectors connect() attach-to-session, both test suites — 18/18 pass"],
    capture_output=True, text=True, cwd=root)
print("COMMIT:", r.stdout[:300], r.stderr[:200])
r2 = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", r2.stdout[-150:], r2.stderr[-200:])
