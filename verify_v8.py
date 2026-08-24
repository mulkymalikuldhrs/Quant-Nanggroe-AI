import pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
au = (root / "quant_nanggroe/engine/agentic/autonomous.py").read_text(encoding="utf-8", errors="ignore")

# 1) SignalAggregator wired?
print("1. SignalAggregator wired:", "SignalAggregator" in au and "aggregate(" in au)
print("2. Journal sync wired:", "journal_sync" in au or "sync_mt5_deals" in au)
# Check journal sync
js = (root / "quant_nanggroe/engine/journal_sync.py").exists()
print("   journal_sync.py exists:", js)

# 3) Allocation gate wired?
print("3. Allocation gate wired:", "admitted_for_symbol" in au)

# 4) Tuned params injection?
print("4. Tuned params injected:", "best_params_for" in au)

# 5) Trading profile SL/TP?
print("5. Profile SL/TP wired:", "compute_sl_tp" in au)

# 6) Trailing stop wired?
ts = (root / "quant_nanggroe/engine/risk/trailing_stop.py").read_text(encoding="utf-8", errors="ignore")
print("6. Trailing stop breakeven:", "breakeven_trigger_pct" in ts)
print("   Trailing update called:", "self._trailing_stop.update" in au)

# 7) SMC engine exists?
smc = (root / "quant_nanggroe/engine/smc/native_smc.py").exists()
print("7. Native SMC engine:", smc)

# 8) FX-only symbols?
sched = (root / "quant_nanggroe/engine/scheduler.py").read_text(encoding="utf-8", errors="ignore")
fx_only = "EURUSD.vx" in sched and "BTC-USD" not in sched.split("SYMBOLS")[1][:200] if "SYMBOLS" in sched else False
print("8. Scheduler FX-only:", fx_only)
