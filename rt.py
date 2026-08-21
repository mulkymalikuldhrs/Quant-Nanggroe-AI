import subprocess
root = r"D:\repositories\Quant-Nanggroe-AI-worktree"
subprocess.run(["git", "add", "-A"], capture_output=True, cwd=root)
r = subprocess.run(["git", "commit", "-m",
    "feat(gates1-2,7): scorers verified wired + broker symbol auto-detect + live breakeven/ATR trailing\n\n"
    "GATE-1: all 10 scorers CONFIRMED wired in main.py:418-447 (Bond/Crypto/Economic/\n"
    "  Geopolitical/Macro/News/Positioning/Sentiment/Technical/Volatility + evolver\n"
    "  weights). Not lost - they live in core/scoring/, never in engine/.\n"
    "GATE-2: MT5Broker.resolve_symbol() - snapshot terminal's real symbol catalog at\n"
    "  connect (symbols_get), resolve candidates exact/stripped/map/suffixed.\n"
    "  Works with any broker suffix (.vx Valetax, bare Exness, .m IC Markets).\n"
    "GATE-7 P0 fix: TrailingStopManager.update() was NEVER called on the live path -\n"
    "  positions tracked but zero price feeds = dead feature. Wired into autonomous\n"
    "  run() step 1.2b with ATR(14) computed from fetched bars; fires exit via\n"
    "  _make_decision('trailing_stop'). Manager upgraded: breakeven ratchet at +1%,\n"
    "  volatility-adaptive ATR trail (atr_multiple), monotonic stop tightening.\n"
    "Tests: 9 new gate-7 regression tests pass (breakeven/ATR/ratchet/fire)."],
    capture_output=True, text=True, cwd=root)
print("COMMIT:", r.stdout[:250])
r2 = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=root)
print("PUSH:", r2.stdout[-120:], r2.stderr[-150:])
