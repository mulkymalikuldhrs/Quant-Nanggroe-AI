"""Adversarial test: break the QNA risk guard. Prove fail-closed."""
from quant_nanggroe.engine.risk.manager import RiskManager

EQ = 1000.0  # $1K demo account (matches Valetax demo)

def mk():
    return RiskManager(initial_equity=EQ)

def trade(rm, sym="EURUSD"):
    return rm.check_trade(symbol=sym, direction="BUY", lot_size=0.01,
                           entry=1.1, stop_loss=1.09, account_balance=EQ)

# ---- TEST 1: daily loss > 5% MUST veto + block ALL orders ----
rm = mk()
rm.state.daily_pnl = -60.0  # -6% of 1000
r = trade(rm)
assert r["verdict"] == "VETOED", f"TEST1 FAIL: {r}"
for sym in ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"]:
    rr = trade(rm, sym)
    assert rr["verdict"] == "VETOED", f"TEST1 FAIL not-blocking {sym}: {rr}"
print("TEST1 daily>5%: PASS (veto fires, blocks ALL orders)")

# ---- TEST 2: phantom veto check — no broker, 0 real fills, floating loss ----
# Guard must NOT veto when there are zero realized deals (no floating-equity read).
rm2 = mk()  # daily_pnl=0, no mt5 handle -> _sync_realized_pnl early-returns
r2 = trade(rm2)
assert r2["verdict"] == "APPROVED", f"TEST2 FAIL phantom-veto: {r2}"
print("TEST2 no-phantom-veto: PASS (no floating-equity read, 0 fills -> APPROVED)")

# ---- TEST 3: weekly loss > 3% MUST veto ----
rm3 = mk()
rm3.state.weekly_pnl = -40.0  # -4% of 1000
r3 = trade(rm3)
assert r3["verdict"] == "VETOED", f"TEST3 FAIL: {r3}"
print("TEST3 weekly>3%: PASS (weekly-loss veto present + fires)")

# ---- TEST 4: kill switch early-warning fires at 2% daily (not only at 1% hard) ----
rm4 = mk()
rm4.state.daily_pnl = -20.0  # -2% -> should trip early-warning (0.8%) if wired
rm4._auto_check_kill_switch()
print(f"TEST4 killswitch active={rm4.kill_switch.is_active} (daily_pnl=-20 -> -2%)")
# NOTE: if KILL_SWITCH_DAILY_PNL dead, this only fires at >=1% (i.e. -10 abs) -> would be False here

# ---- TEST 5: stale-state phantom veto via _sync_realized_pnl != 0.0 guard ----
# Simulate: day had -60 loss, then reversed to flat (realized 0). If _sync keeps -60 -> still vetoed.
class FakeMT5:
    def history_deals_get(self, a, b):
        return []  # flat day, 0 realized
rm5 = mk()
rm5.set_broker_handle(FakeMT5())
rm5.state.daily_pnl = -60.0  # stale from prior state
rm5._sync_realized_pnl()
print(f"TEST5 after flat-day sync: state.daily_pnl={rm5.state.daily_pnl} "
      f"(if still -60 -> STALE PHANTOM VETO)")
r5 = trade(rm5)
print(f"TEST5 verdict={r5['verdict']} (VETOED with 0 realized = phantom veto bug)")

print("ALL ADVERSARIAL TESTS EXECUTED")
