# FINDINGS — SL/TP + TRAILING STOP AUDIT (QNA / Quant-Nanggroe-AI-worktree)

- **Audit date:** 2026-08-02 (working tree; commit `4331e2bf` "SL/TP + TRAILING FIX" landed today 01:33 +0700)
- **Scope:** `quant_nanggroe/autonomous_cycle.py` (live loop, PurifiedEngine), `engine_production_bridge_purified.py`, `connectors/mt5_broker.py`, `engine_production_bridge.py`, `live_engine.py` (`qna.py live`), `risk_levels.py`, `engine/strategies/*`, `engine/risk/constants.py`, `exchange/mt5_broker.py`, `api/routes/trading.py`
- **Method:** code = source of truth (no .md claims). All file:line references verified against the working tree at audit time. NOTE: `autonomous_cycle.py` was concurrently edited during audit (singleton-lock guard added, +55 lines); line numbers below are current working-tree numbers and match committed logic except for offset.

---

## 1. WHERE SL/TP VALUES ARE SET (per strategy / per path)

### A. Autonomous cycle path (the "live" loop per task context) — CENTRALIZED, ATR+structure
| What | File:Line | Mechanism |
|---|---|---|
| ATR computed (M15, 14) | `autonomous_cycle.py:259-260` | `compute_atr(candles, period=14)` |
| SL/TP computed | `autonomous_cycle.py:276-277` | `strategy_sl_tp(symbol, signal, price, atr, candles, min_stop_points, point_size)` |
| Applied to Signal | `autonomous_cycle.py:284-285` | `stop_loss=levels["sl"], take_profit=levels["tp"]` |
| SL/TP formula | `risk_levels.py:52-98` `strategy_sl_tp()` | SL = structure swing (`_find_structure_swing`, min low / max high of last 20 candles, `risk_levels.py:37-49`) vs entry∓1.5–2×ATR; TP = entry±3×ATR (3:2 R:R); clamped to broker min-stop `min_stop_points*point_size` (`:80-95`) |
| ATR fallback | `risk_levels.py:63-64` | `atr = entry*0.005` if ATR unavailable (residual 0.5%) |
| Broker min-stop read | `autonomous_cycle.py:269-273` | `mt5.symbol_info(symbol).trade_stops_level` |
| **point_size (BUG)** | `autonomous_cycle.py:278` | `0.00001 if "JPY" not in symbol else 0.001` — wrong for XAUUSD.vx (point 0.01) and BTCUSD.vx → see GAP-2 |

### B. Strategy-specific SL/TP (engine registry) — COMPUTED BUT NEVER USED by the live loop
| Strategy | File:Line | Basis |
|---|---|---|
| SMC | `engine/strategies/smc_strategy.py:116-124` | 1.5×ATR SL / 3×ATR TP |
| Wyckoff | `engine/strategies/wyckoff.py:114-115,136-137,156-157` | structure (recent_low×0.98 / recent_high / range) |
| MeanRev | `engine/strategies/mean_reversion.py:121-122,136-137,213-214,228-229` | 1.5×ATR / 3×ATR |
| Dhaher | `engine/strategies/dhaher_system.py:297-298,323-324` | adaptive ATR mult × `rr_min` |
| Kronos | `engine/strategies/kronos_wrapper.py` | **NO SL/TP at all** (ML forecast → direction only) |

These live in `StrategySignal` objects (`engine/strategies/base.py:61,129`) returned by `generate_signal(data, **kwargs)`. The cycle calls `strategy.analyze(candles, current_price)` (`autonomous_cycle.py:262`) which does NOT exist on registry strategies → `AttributeError` → swallowed (`autonomous_cycle.py:286-288`) → **zero signals from the registry path**. See GAP-3.

### C. LiveEngine path (`qna.py live` → `LiveEngine`) — HARDCODED % (pre-fix style)
| What | File:Line | Mechanism |
|---|---|---|
| TP price | `live_engine.py:730-731` | `tp_price = price * (1 + TP_TARGETS.get(strategy, 0.05))` (5% default) |
| SL price | `live_engine.py:737` | `stop_loss = price * (1 - TRAILING_STOP_PCT)` |
| TRAILING_STOP_PCT | `engine/risk/constants.py:150` | `0.03` (3%) |
| Fail-safe fallback | `engine_production_bridge.py:401-407` | if `sl/tp is None` → `±0.5% / ±1%` hardcoded (`price*0.995/1.005`, `*1.01/0.99`) |
| Order build | `engine_production_bridge.py:426-434` | `Order(stop_loss=sl, take_profit=tp)` → `MT5Broker.place_order` |

### D. API route (`api/routes/trading.py`)
- `:364` `stop_loss = request.stop_loss or (entry*0.99)`; `:370-372` TP from request; `:567-568,584-585` defaults `sl/tp=0.0` from dicts → see GAP-1 (0.0 reaches execution → naked).

### E. Hardcoded ±0.5%/±1% remnants still present
- `engine_production_bridge.py:404-405` (fail-safe), `api/routes/trading.py:364` (`entry*0.99`), `risk_levels.py:64,109,113,120` (ATR==0 fallback), `autonomous_cycle.py:153` `TRAILING_STOP_PCT=0.005` (fallback trail only), `engine/risk/constants.py:150` (3% — LiveEngine).

---

## 2. TRAILING STOP LOGIC — EXISTS, ATR-BASED (NOT structure/swing)

### A. Autonomous cycle (`PositionManager`, runs every 60 s cycle — `autonomous_cycle.py:708` → `update_positions` `:444-495`)
- R-multiple calc: `autonomous_cycle.py:513-524` (risk = |entry−SL|, or **ATR if position has no SL** — `:520`)
- Partial TP 50% @ 1R: `:526-533`; Full TP (market close) @ 2.5R: `:535-539`
- **Trail loop: `:541-552`** — activates when `r_multiple > 1.0`:
  - ATR-based: `trailing_sl_atr(side, entry, current, current_sl, atr, activation_r=1.0)` (`risk_levels.py:101-125`) → `new_sl = current ∓ 2×ATR`, monotonic (only moves in favor), fallback `_calculate_trailing_sl` 0.5% of entry (`:554-561`)
  - SL pushed to broker via `_modify_sl` (`:612-624`, `TRADE_ACTION_SLTP`, **SL only — MT5 preserves TP** — VERIFIED OK)
- **No swing-high/low trailing.** Structure (`_find_structure_swing`, `risk_levels.py:37-49`) is used only for the INITIAL SL, never for trailing. **No breakeven move exists anywhere** (grep for breakeven/BE/SL→entry: 0 hits in trading code).

### B. LiveEngine (`live_engine.py:840-866`)
- Trail = `highest_since_entry * (1 - 0.03)` (`:857`) → **market close** when price < trail (`:858-859`); does NOT modify broker SL. If loop down → no trailing. Partial exit @ 1×tp_target (`:862-866`).

### C. `exchange/mt5_broker.py:820-860` `modify_position` (TRADE_ACTION_SLTP, preserves sl/tp when new ≤ 0) — defined, **no callers** in any live loop.

---

## 3. WHY TRADES EXECUTE WITH NO SL/TP — exact conditions

### The "omit" conditions (this is the mechanism):
1. **`engine_production_bridge_purified.py:123-124`** — `_sl = sl if (sl and sl > 0) else None; _tp = tp if (tp and tp > 0) else None` → request built WITHOUT `sl`/`tp` keys (`:137-140`) → **MT5 market order fills NAKED**. Signal defaults are `stop_loss=0.0, take_profit=0.0` (`:33-34`), so ANY caller that constructs a `Signal` without explicit levels produces a naked fill through `execute_order()`.
2. **`connectors/mt5_broker.py:90-93`** — `if order.stop_loss is not None: req["sl"]=...` → `Order.stop_loss` default `None` (`broker_base`) → naked. The ExecutionManager path passes `order.stop_loss` straight through (`engine/execution/brokers/mt5_adapter.py:140-141`).
3. **`engine_production_bridge.py:461-473`** (ExecutionManager fallback branch) — passes raw `getattr(signal,"stop_loss",None)` **without** the fail-safe fallback (which only guards the direct MT5 branch, `:401-407`) → naked if signal SL is None.
4. **`api/routes/trading.py:567-568,584-585`** — builds orders with `sl/tp=0.0` defaults → hits condition 1/2 → naked.
5. **TP=0 is never fail-closed.** `PurifiedEngine.position_size` (`engine_production_bridge_purified.py:263-269`) gates ONLY on SL; a signal with valid SL but `tp=0` → order with SL but NO TP.

### Why the value becomes 0:
- Signal dataclass defaults `0.0` (`engine_production_bridge_purified.py:33-34`); `sl = sig.stop_loss if (sig.stop_loss and sig.stop_loss > 0) else 0.0` (`:333`).
- **Historical root cause (per devs' own diagnosis, `risk_levels.py:4-8` + commit `4331e2bf`):** hardcoded ±0.5%/±1% stops were BELOW broker `trade_stops_level` (BTCUSD.vx=2976 pts) → broker rejected the stops; commit `2897d380` (2026-08-01) then changed `execute_order` to "omit sl/tp when 0" — which is precisely the code that turns a rejected order into a **naked fill** whenever 0.0 reaches it.

### The fail-closed guard that SAVES the cycle() path (VERIFIED OK):
- `PurifiedEngine.cycle`: `sl = 0.0` → `position_size()` returns 0.0 (`engine_production_bridge_purified.py:263-264`) → `if lot <= 0: continue` (`:343-346`) → **trade skipped, not naked**. So the current autonomous_cycle signal path cannot produce a naked entry via `cycle()` — but `execute_order()`/`place_order()` remain public naked-fill surfaces for every other caller.

---

## 4. EXECUTION LAYER PASS-THROUGH TO MT5
- `connectors/mt5_broker.py:90-93` — passes `sl`/`tp` when not None. **VERIFIED OK** (bug is upstream None/0, not here).
- `engine_production_bridge_purified.py:123-124,137-140` — passes when > 0. **VERIFIED OK** (omits when ≤ 0 = naked surface, see §3).
- `exchange/mt5_broker.py:648-651` — passes when not None. **VERIFIED OK**.
- `engine_production_bridge.py:426-434` — Order carries sl/tp to `place_order`. **VERIFIED OK**.
- No tick-size alignment of SL/TP (only `round(x,5)`, `risk_levels.py:97-98`) — minor, see GAP-8.

---

## 5. MONITOR / UPDATE LOOP (BE / trail)
- **YES — autonomous_cycle runs PositionManager every cycle** (`autonomous_cycle.py:708`, cycle interval 60 s `:88`): partial TP 1R, full TP 2.5R, ATR trail 1R+ (see §2A). SL modified on broker (`:612-624`); **TP never modified by the loop** (broker TP stays at entry value; loop enforces its own TP via market close `:535-539`).
- **NO breakeven logic** anywhere.
- LiveEngine has its own 3% trail loop (`live_engine.py:840-866`) — market-close based.
- Note: full-TP and trail enforcement depend on the loop process being alive; if it dies, only broker-side SL/TP protect positions.

---

## VERIFIED OK
1. `PurifiedEngine.cycle()` is fail-closed on SL≤0 → trade skipped, never naked (`engine_production_bridge_purified.py:333,343-346,263-264`).
2. ATR+structure SL/TP now computed centrally with broker min-stop clamp (`risk_levels.py:52-98`; wired `autonomous_cycle.py:259-285`) — replaces the pre-fix hardcoded ±0.5%/±1% (verified in git diff of `4331e2bf`).
3. Trail loop exists and runs each 60 s cycle; ATR-based trail activates after 1R and is monotonic (`autonomous_cycle.py:541-552`, `risk_levels.py:101-125`).
4. `_modify_sl` sends `TRADE_ACTION_SLTP` with SL only; MT5 preserves existing TP — no TP wipe on trail (`autonomous_cycle.py:612-624`).
5. MT5Broker/MT5Adapter pass-through is correct when values are present (`connectors/mt5_broker.py:90-93`, `engine_production_bridge_purified.py:137-140`).
6. Old bridge has a fail-safe stop fallback for the direct MT5 branch (`engine_production_bridge.py:401-407`) — LiveEngine orders always carry stops (though hardcoded %).

## GAPS

### CRITICAL
- **GAP-1 — Naked-fill surface:** omit-if-≤0 / omit-if-None at `engine_production_bridge_purified.py:123-124` + `connectors/mt5_broker.py:90-93` + Signal/Order defaults `0.0`/`None` (`:33-34`, `broker_base`) → any non-cycle caller (API `trading.py:567-568,584-585`, agentic, tests) with sl/tp=0 fills a position with NO protective stops. TP=0 is not fail-closed anywhere.
- **GAP-2 — Broken broker min-stop clamp for XAUUSD.vx / BTCUSD.vx:** `point_size` hardcoded 0.00001 for non-JPY (`autonomous_cycle.py:278`) but XAUUSD/BTCUSD point is ~0.01 → `min_dist = trade_stops_level × point_size` (`risk_levels.py:80-95`) is 100–10000× too small → SL/TP can still violate broker `trade_stops_level` → invalid-stops rejection (purified: raise → no trade) or naked/failed fills on other paths. The headline fix is broken for 2 of the 5 live symbols.
- **GAP-3 — Registry strategies never trade via autonomous_cycle:** cycle calls `strategy.analyze()` but registry strategies implement `generate_signal()` (`engine/strategies/base.py:129`) → AttributeError swallowed (`autonomous_cycle.py:286-288`) → SMC/Wyckoff/MeanRev/Dhaher/Kronos produce zero signals in the live loop; their own ATR/structure SL/TP (`smc_strategy.py:116-124`, `wyckoff.py:114-157`, `mean_reversion.py:121-146`, `dhaher_system.py:297-324`) is dead code. Kronos has no SL/TP concept at all.

### MAJOR
- **GAP-4 — Trailing is NOT structure (SMC swing) based and there is NO breakeven:** trail = 2×ATR behind current price (`risk_levels.py:101-125`); structure swing only used for initial SL. Zero breakeven logic in the whole codebase.
- **GAP-5 — Divergent second live loop (LiveEngine) still hardcoded:** `qna.py live` → `live_engine.py:730-738` uses 3% SL / 5% TP / 3% trail (constants.py:150) and the old bridge fail-safe ±0.5%/±1% (`engine_production_bridge.py:404-405`). Two SL/TP systems with different semantics depending on which loop is running.
- **GAP-6 — Naked positions get no protective stop from PositionManager:** if `pos.sl == 0`, risk = ATR (`autonomous_cycle.py:520`) and an SL is only ADDED after 1R profit (`:541-551`); a naked losing position is never stopped. Loop-down ⇒ no trail/TP enforcement (only broker SL/TP remain).
- **GAP-7 — Engine fallback branch drops fail-safe stops:** `engine_production_bridge.py:461-473` passes raw signal sl/tp (None → naked) unlike the direct MT5 branch (`:401-407`).

### MINOR
- **GAP-8 — No tick-size rounding of SL/TP** (`risk_levels.py:97-98`); round(...,5) is fine for FX/JPY, not aligned to XAUUSD/BTCUSD steps.
- **GAP-9 — Dead code / leftovers:** `autonomous_cycle.py:270-271` `symbol.replace(".vx","") if False else symbol`; `TRAILING_STOP_PCT=0.005` (`:153`) only a fallback; `exchange/mt5_broker.py:820-860` `modify_position` has no callers.
- **GAP-10 — `min_stop_points` read can silently be 0:** `symbol_info` None (MT5 down/not initialized) → no clamp at all (`autonomous_cycle.py:269-273`); also dead `if False` expression.

## RECOMMENDED FIX (priority order)
1. **Fail-closed stops at the broker boundary:** in `engine_production_bridge_purified.py:123-124` and `connectors/mt5_broker.py:90-93`, if sl≤0/None → REJECT the order (raise) instead of omitting, or auto-derive SL=2×ATR / TP=3×ATR from fetched candles (never naked). Apply the same guard to `engine_production_bridge.py:461-473` and API `trading.py` sl/tp defaults.
2. **Fix point_size per symbol** from `mt5.symbol_info(symbol).point` (fallback table: EURUSD/GBPUSD 0.00001, USDJPY 0.001, XAUUSD 0.01, BTCUSD 0.01/0.1) in `autonomous_cycle.py:278`; re-verify clamp math against real `trade_stops_level` (Valetax).
3. **Wire registry strategies properly:** call `generate_signal(candles_df, symbol=...)` in `StrategySignalGenerator` (`autonomous_cycle.py:262`) and USE each StrategySignal's own sl/tp (ATR+structure per strategy); keep `strategy_sl_tp` only as fallback.
4. **Structure-based trailing:** trail SL to the most recent SMC swing high/low (invalidate on BOS) instead of raw 2×ATR; add a breakeven move (SL→entry) after 1R before trailing; in `trailing_sl_atr` accept a structure level parameter.
5. **Unify the two loops:** make `live_engine.py:730-738` use the same `risk_levels.strategy_sl_tp` (or route LiveEngine through PurifiedEngine) so SL/TP semantics are identical regardless of entry point.
6. **TP fail-closed:** treat `tp<=0` like `sl<=0` in `PurifiedEngine.cycle`/`position_size` (skip or derive), so no position ever opens TP-less.
7. **Tick-aligned stops:** round SL/TP to symbol `point`/`digits` steps before `order_send`.
8. Add a startup/health check that reads open positions and alerts on any with sl=0 or tp=0 (guardian).

---
*Line numbers = working tree at audit time (2026-08-02). `autonomous_cycle.py` had uncommitted +55-line singleton-guard diff vs HEAD; all referenced logic lines verified present in both HEAD and working tree.*
