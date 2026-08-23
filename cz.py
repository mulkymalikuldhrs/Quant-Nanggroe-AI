import subprocess, pathlib
root = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
for f in ["p1.py", "rt.py"]:
    (root / f).unlink(missing_ok=True)
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=str(root))
c = subprocess.run(["git", "commit", "-m",
    "feat(profiles): scalp/day/swing timeframe profiles + ATR-adaptive SL/TP\n\n"
    "- engine/risk/trading_profile.py: TradingProfile dataclass with\n"
    "  sl_atr_mult, rr_target, breakeven_trigger_rr, max_hold_hours;\n"
    "  scalp(1x ATR, 1.5R, 4h) / day(1.5x ATR, 2R, 24h) / swing(2.5x ATR,\n"
    "  3R, 120h); detect_profile(timeframe) maps M15->scalp, H1->day, D1->swing\n"
    "- compute_sl_tp(): volatility-adaptive SL/TP replacing hardcoded 5%\n"
    "  fallback (5% was ~500 pips on forex = absurdly wide; 0.5% floor for\n"
    "  zero-ATR edge case)\n"
    "- autonomous.py: wired into SL/TP fallback path — when FinalDecider has\n"
    "  no levels, uses profile-based ATR SL/TP instead of fixed 5%\n"
    "Tests: 9/9 (profile detection, buy/sell direction, scalp<swing width,\n"
    "  RR override, zero-ATR fallback)"],
    capture_output=True, text=True, cwd=str(root))
print("COMMIT:", c.stdout[:250])
pu = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=str(root))
print("PUSH:", pu.stdout[-80:], pu.stderr[-100:])
st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(root)).stdout
print("FINAL:", repr(st))
