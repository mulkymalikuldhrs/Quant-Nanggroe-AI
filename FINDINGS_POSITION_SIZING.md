# FINDINGS — POSITION SIZING AUDIT (QNA Live MT5)
**Date:** 2026-08-02 · **Auditor:** Hermes subagent (position-sizing audit)
**Scope:** Lot-size calculation for LIVE orders, Kelly wiring, risk-per-trade, equity adaptation, max-lot/leverage guards.
**Account (context):** Valetax 372044706 — balance ≈ $1,122, equity ≈ $1,480.

> ⚠️ **Repo is a moving target.** During this audit the file `engine_production_bridge_purified.py` changed on disk mid-session; a fix was committed at `fadecf9d` (2026-08-02 08:09:08 +0700, "position_size() now equity+SL-aware LOTS (was units->always 0.01)"). All line numbers below refer to **HEAD (fadecf9d)**, which matches the working tree at audit end. Live processes were restarted 08:12 — some may still run pre-fix code in memory (older PIDs started 01:40 / 03:56 / 08:08).

---

## 1. Where is lot size calculated for live orders? Fixed 0.01 clamp or risk-based?

**LIVE order path:** `quant_nanggroe/autonomous_cycle.py` (AutonomousCycle.run_cycle → `self.engine.cycle(...)` at **autonomous_cycle.py:741**) → `PurifiedEngine.cycle()` → `RiskGuard.position_size()` → `MT5Adapter.execute_order()`.

**Lot formula (HEAD, risk-based — recently fixed):**
- `quant_nanggroe/engine_production_bridge_purified.py:254-269` — `RiskGuard.position_size()`:
  ```
  risk_amount = self.balance * risk_pct * kelly          # risk_pct=0.005, line 268
  lot = risk_amount / (sl_distance * contract_size)      # sl_distance = |price - SL|, line 269
  # returns 0.0 if price<=0 or sl<=0 → fail-closed, no trade (lines 263-264)
  ```
- Call site **purified:331-346**: kelly (line 332), SL (line 333), `contract_size` from MT5 `symbol_info().trade_contract_size` default 100000 FX (lines 334-341), `lot = self.risk.position_size(sig.price, kelly, sl, contract_size)` (line 342).
- **Min-lot forced-risk cap (fail-closed)** **purified:352-374**: if computed lot < broker `volume_min` (0.01), the forced risk of trading min lot (`min_lot × SL_dist × contract_size`) is compared to `hard_cap = max(2 × risk_usd, balance × 0.02)`; if exceeded → order SKIPPED (no oversized min-lot trade).
- `execute_order` **purified:110-120** clamps to broker `[volume_min, volume_max]` and rounds to `volume_step` — the **0.01 floor lives here** (`if lot < min_lot: lot = min_lot`, lines 114-115), but in HEAD it only kicks in when the risk-based lot is legitimately below min lot.

**Pre-fix behavior (what the user experienced):** `git show fadecf9d^` — old `position_size(price, kelly) = balance × 0.005 × kelly / price` (**price-based "units", no SL, no contract size**). For expensive symbols (BTCUSD ~67k, XAUUSD ~2.4k, USDJPY ~155) this produced tiny lots that `round(lot, 2)` + the min-lot clamp collapsed to **0.01 lots fixed** — exactly the reported complaint. The old cycle comment literally said *"Size position (execute_order clamps to broker min 0.01)"*.

**Verdict:** HEAD is now **risk-based (SL-distance)** — but see GAP-1/GAP-2: the equity input is frozen at $10,000, so live behavior still does NOT match the real account.

---

## 2. Is there a Kelly calculator wired to live sizing? Where does kelly_cache come from?

- Kelly infrastructure exists: `quant_nanggroe/engine/risk/kelly.py` (legacy shim → `engine/kelly/` package: FullKelly, FractionalKelly, AdaptiveKelly, MultiAssetKelly), plus `PositionSizer.kelly_based` (`engine/risk/position_sizing.py:126-166`).
- Live cache: `RiskGuard.kelly_cache` (**purified:229**, init empty) read at **purified:332**: `kelly = self.risk.kelly_cache.get(sig.strategy, 0.25)` → **default 0.25 always in practice**.
- Writers of `kelly_cache`:
  - `autonomous_cycle.py:436` — `self.engine.risk.kelly_cache[strat] = v["kelly"]` inside `PositionManager._on_position_closed` (journal self-eval). **DEAD in practice:** `PositionManager` is constructed with `self.journal` **before** `self.journal = TradeJournal()` (autonomous_cycle.py:659 vs **665**), so `PositionManager.journal is None` → early return at **line 413-414** → self-eval never runs → cache never populated.
  - `autonomous_cycle.py:609-611` — `PerformanceTracker.record_trade` writes `self.risk_guard._kelly_cache[strategy]` — **wrong attribute name** (RiskGuard has `kelly_cache`, no `_kelly_cache`) → would raise AttributeError; also `record_trade` is **never called** anywhere.
- Other Kelly calculators are **NOT in the live loop**: `agents/execution/tools.py:284` `kelly_lot_size` (agentic tool, FractionalKelly 0.25, leverage_max=0.02), `agents/risk/tools.py:321` `kelly_sizing`, `engine/risk/manager.py:563` `calculate_position_size`.

**Verdict:** Kelly is **not effectively wired** — live sizing uses the constant default `kelly = 0.25` (via two independent dead-code bugs). Risk per trade therefore = 0.5% × 0.25 = **0.125%** of the (frozen) balance.

---

## 3. What is the risk per trade (% of equity)? Config → order trace.

| Layer | Value | Source |
|---|---|---|
| Constitutional `MAX_RISK_PER_TRADE` | 0.5% | `engine/risk/constants.py:28` = `settings.risk_max_per_trade / 100`; `config/settings.py:118-125` default **0.5**, env `QNAI_RISK_MAX_PER_TRADE` (unset in `.env` → default) |
| Hardcoded live `risk_pct` | **0.005** | `engine_production_bridge_purified.py:256,268` — matches constitutional 0.5% but is **hardcoded, not read from config** |
| Kelly multiplier | 0.25 default (never updated) | purified:332; autonomous_cycle.py:96 `DEFAULT_KELLY = 0.25` |
| Equity input | **$10,000 hardcoded** | `autonomous_cycle.py:648` → `PurifiedEngine(initial_balance=10000.0)` (purified:299-301) |
| **Effective risk budget** | $10,000 × 0.005 × 0.25 = **$12.50/trade** | purified:347 |

- **On the real account this is 1.11% of balance ($1,122) / 0.84% of equity ($1,480)** — i.e. ~2.2× the intended 0.5% — and the percentage **drifts** as the frozen $10k stays put while real equity moves.
- `config/system_config.yaml` contains **zero trading/risk parameters** (it is LLM/agent orchestration config only) — risk-per-trade is not config-driven on the live path.
- Kill-switch / DD / daily-3% / weekly-3% vetoes: `RiskGuard.can_trade()` **purified:236-252**, wired in autonomous_cycle.py:667-672, refreshed each cycle at 691.

---

## 4. Does lot size adapt when equity changes?

**NO — CRITICAL.** `RiskGuard.balance` is set once from the hardcoded `initial_balance=10000.0` (purified:220-221) and only ever changes via `update_pnl()` (purified:271-280). **`update_pnl` is never called in the live loop** (callers only exist in `agents/bridges/risk_gate_bridge.py:556` and `engine/risk/manager.py:349` — neither is in the autonomous_cycle path). MT5 `account_info()` is fetched at connect (purified:71) but its balance/equity is **never pushed into RiskGuard**. Consequences:
- Lot size always computed from $10,000 regardless of real balance/equity (incl. floating PnL).
- DD / daily / weekly loss vetoes compare against a **frozen baseline** → 15% DD / 3% daily / 3% weekly limits can **never trip** from real account movements; only the KillSwitch file is effective.
- `status()` reports `balance=10000.0` forever.

---

## 5. Max leverage / max lot guard?

- **Only broker-side clamp:** `execute_order` → `max_lot = info.volume_max or 50.0`, `if lot > max_lot: lot = max_lot` (**purified:112-117**). No pre-trade margin/leverage/equity check → relies on broker rejecting (FOK).
- Constitutional `MAX_LEVERAGE = 3.0` (`engine/risk/constants.py:30`) and `MAX_POSITION_SIZE_PCT = 0.10` (constants.py:29) exist but are **NOT wired into the live PurifiedEngine path**.
- The min-lot forced-risk cap (purified:352-374) is the only account-aware guard (2% of the *frozen* balance).

---

## VERIFIED OK
1. **Risk formula is now SL-distance based** (not price/notional): `lot = risk × equity / (|entry−SL| × contract)` — purified:254-269. ✅
2. **Fail-closed when no SL:** `position_size` returns 0 → order skipped (purified:263-264, 343-346). ✅
3. **Min-lot forced-risk hard cap:** oversized min-lot trades skipped (purified:352-374). ✅
4. **Contract size read live from MT5** `trade_contract_size` (FX default 100000; BTCUSD.vx = 1) — purified:334-341. ✅
5. **Broker lot clamping + step rounding** in execute_order (purified:110-120). ✅
6. **KillSwitch wired fail-closed** and refreshed every cycle (autonomous_cycle.py:667-672, 691-694). ✅

## GAPS

| ID | Severity | Finding (file:line) |
|---|---|---|
| GAP-1 | **CRITICAL** | **Equity frozen at $10,000 hardcoded** — `autonomous_cycle.py:648` passes `initial_balance=10000.0`; `RiskGuard.balance` never synced from MT5 (only `update_pnl` changes it, and it is never called on the live path). Real sizing should use live equity ≈ $1,480. |
| GAP-2 | **CRITICAL** | **No equity adaptation** — GAP-1 + no `account_info()` refresh means lot size is constant regardless of balance/equity changes; the DD/daily/weekly vetoes (purified:236-252) compare against a frozen baseline and can never trip from real PnL. |
| GAP-3 | **CRITICAL** | **Risk-per-trade is ~2.2× intended on this account** — budget $12.50 = 0.84% of real equity $1,480 (1.11% of balance $1,122) instead of 0.5%, because the $10k constant is used (purified:268, 347). Also `risk_pct=0.005` is hardcoded, not config-driven (purified:256). |
| GAP-4 | **MAJOR** | **Kelly dead-wired** — `kelly_cache` never populated: (a) PositionManager built with `journal=None` (autonomous_cycle.py:659 vs 665 → early return 413-414); (b) `_kelly_cache` attribute typo (autonomous_cycle.py:611 vs purified:229); (c) `record_trade` never invoked. Live kelly = constant 0.25. |
| GAP-5 | **MAJOR** | **No max-leverage / margin guard on live path** — `MAX_LEVERAGE=3.0` and `MAX_POSITION_SIZE_PCT=0.10` (constants.py:29-30) not wired; only broker `volume_max` clamp (purified:112-117). A bad contract/SL read could send a margin-busting lot (rejected only by broker). |
| GAP-6 | **MAJOR** | **Multiple divergent sizing implementations** — (a) `engine_bridge.py:533` `EngineRiskManager.position_size = (balance × MAX_POSITION_PCT(0.10) × kelly)/price` — notional, NOT risk-based; (b) `engine/live/adaptive_integration.py:381` `RiskGate.position_size` fallback `(balance × kelly × 0.1)/price`; (c) `engine_production_bridge.py:688` calls `PositionSizer.kelly_based(balance, kelly, price)` but signature is `(equity, win_rate, avg_win, avg_loss, fraction)` (position_sizing.py:126) → TypeError → always fallback; also reads `result.quantity` but the dataclass field is `size` (position_sizing.py:24-32) → double-broken; (d) `agents/execution/tools.py:284` `kelly_lot_size` (2% cap, `max(0.01, ...)` floor). Live (autonomous_cycle) uses only (purified) — the rest are dormant but confusing and unsafe if re-enabled. |
| GAP-7 | **MAJOR** | **4+ concurrent `autonomous_cycle` processes running** (started 08:12:48-50 + older 01:40/03:56/08:08) — no single-instance lock in autonomous_cycle.py → duplicate signal execution / double orders risk. |
| GAP-8 | **MINOR** | Risk settings not configurable — `risk_pct`, `DEFAULT_KELLY`, `initial_balance` hardcoded in code (purified:256, autonomous_cycle.py:96,648); `system_config.yaml` has no trading section; `.env` risk overrides exist (`.env.example` lines) but unused by this path. |
| GAP-9 | **MINOR** | Kelly clamps 5%-25% (autonomous_cycle.py:610) and default 0.25 make the "Kelly" term effectively a fixed 0.25 multiplier until ≥10 trades/strategy — no signal-confidence scaling in lot. |
| GAP-10 | **MINOR** | No SL-width sanity floor in sizing: if a signal's SL distance is degenerate (e.g. tiny), `lot` explodes; only the min-lot forced-risk cap partially mitigates (cap uses frozen $10k balance, purified:364). |

## RECOMMENDED FIX (exact formula)

1. **Sync equity every cycle** (purified `PurifiedEngine.cycle` / autonomous_cycle.py run_cycle):
   ```python
   acc = mt5.account_info()
   self.risk.equity = acc.equity if acc else self.risk.balance   # live MTM
   self.risk.balance = acc.balance if acc else self.risk.balance  # realized baseline for vetoes
   ```
2. **Risk-based lot (replace purified:254-269):**
   ```python
   RISK_PCT = 0.005                      # 0.5% per trade (config-driven: QNAI_RISK_MAX_PER_TRADE)
   risk_amount = equity * RISK_PCT * kelly           # kelly from kelly_cache (default 0.25)
   sl_dist = abs(entry - stop_loss)                  # points, not pips
   if sl_dist <= 0: return 0.0                       # fail-closed
   lot = risk_amount / (sl_dist * contract_size)     # contract_size = symbol_info().trade_contract_size
   lot = round(lot / step) * step                    # step = volume_step (0.01)
   lot = max(min_lot, min(lot, volume_max))
   # hard cap: never risk more than 2× budget incl. min-lot floor:
   if lot * sl_dist * contract_size > min(2 * risk_amount, equity * 0.01):
       lot = max(min_lot, min(lot, (equity * 0.01) / (sl_dist * contract_size)))
   if lot < min_lot: skip_trade(reason="min-lot risk exceeds cap")   # fail-closed
   ```
3. **Wire Kelly properly:** construct `PositionManager` after `self.journal = TradeJournal()` (move autonomous_cycle.py:665 before 659), fix `_kelly_cache`→`kelly_cache` (line 611), and call `record_trade`/`update_pnl` on every close so `kelly_cache[strategy]` and `RiskGuard.balance/equity` track reality.
4. **Add margin guard:** `if lot * price * contract_size > equity * MAX_LEVERAGE (3.0)` → skip. Wire `constants.MAX_LEVERAGE` into `execute_order` or `cycle`.
5. **Single-instance lock** for autonomous_cycle.py (PID file / `socket` bind) to stop the 4 concurrent loops.
6. **Delete or fix dormant sizers** — repair `engine_production_bridge.py:688` signature/field bug or remove the dead `EngineRiskManager.position_size` notional formula to prevent future misuse.

**Worked example (Valetax, EURUSD.vx, equity $1,480, 0.5% risk, kelly 0.25):**
`risk_amount = 1480 × 0.005 × 0.25 = $1.85`; SL 20 pips = 0.0020, contract 100,000 → `lot = 1.85 / (0.0020 × 100000) = 0.00925` → below min 0.01 → forced risk of 0.01 lot = `0.01 × 0.0020 × 100000 = $2.00` ≈ 0.135% of equity ≤ cap → trade at **0.01**. With 2× ATR SL = 40 pips → `lot = 1.85/(0.0040×100000) = 0.0046` → 0.01 min (forced risk $4.00 = 0.27%). Only when forced risk > 1% equity (or 2× budget) the trade is skipped — exactly the risk-based behavior requested.

---

## TOP 10 FINDINGS (condensed)
1. Live lot calc is at `engine_production_bridge_purified.py:254-269` (RiskGuard.position_size) via autonomous_cycle.py:741 — **HEAD is SL/contract-based and fail-closed**, but pre-`fadecf9d` code (still in some running processes) was `balance×0.005×kelly/price` → clamped to **fixed 0.01** (user complaint root cause). [CRITICAL context]
2. **Equity input frozen at $10,000** (autonomous_cycle.py:648) — real account is ~$1,122/$1,480. [CRITICAL]
3. **No MTM sync**: `RiskGuard.balance` never updated (update_pnl uncalled on live path) → sizing & DD/daily/weekly vetoes use frozen baseline; **lot size does NOT adapt to equity**. [CRITICAL]
4. Effective risk = $12.50/trade = **0.84-1.11% of real capital** (intended 0.5%) — 2.2× over budget. [CRITICAL]
5. **Kelly dead-wired** — kelly_cache never populated (journal wired as None at autonomous_cycle.py:659/665; `_kelly_cache` typo at 611; record_trade never called) → constant kelly 0.25. [MAJOR]
6. **No max-leverage/margin guard** on live path (MAX_LEVERAGE=3.0 exists but unwired; only broker volume_max clamp). [MAJOR]
7. **4+ concurrent autonomous_cycle processes**, no single-instance lock → duplicate-order risk. [MAJOR]
8. **5 divergent sizing implementations** in repo; `engine_production_bridge.py:688` calls `kelly_based(balance,kelly,price)` with wrong signature + reads wrong field → always fallback `(balance×0.1×kelly)/price` (10% notional). [MAJOR]
9. Risk-pct hardcoded (0.005), not config-driven; `system_config.yaml` has no trading section; `.env` overrides unused. [MINOR]
10. Min-lot forced-risk cap exists (purified:352-374) but computed against frozen $10k; no SL-distance sanity floor for degenerate tiny SL. [MINOR]

*Note: this audit ran while another agent was actively committing to the repo; the sizing fix landed at 08:09 (fadecf9d) mid-audit. Re-verify line numbers if the repo moves again.*


<!-- CODE-TRUTH STATUS FOOTER — appended 2026-08-03 23:43:45 by autobot (QNA audit 2026-08-03) -->
<!-- Method: append-only. Source of truth = code, not prior .md claims. -->
## 🔍 CODE-TRUTH STATUS (2026-08-03 audit)
- **FusionEngine**: EXISTS — `quant_nanggroe/core/scoring/fusion_engine.py:27` (prior claim "false" RETRACTED).
- **API server**: EXISTS + startable — `quant_nanggroe/cli.py:603` uvicorn :8000; `launch.bat api`; 223 routes wired.
- **Dashboard**: UNWIRED only because server not started; UI code present (`dashboard/`, 261 tsx+ts).
- **Phantom-equity ($1M default)**: MITIGATED — P1b fail-CLOSED `_resolve_equity()` floor $1000 in `risk_gate_bridge.py` (ctor:145, evaluate:194, evaluate_from_state:449). Live path uses `evaluate_from_state` -> real MT5 equity.
- **Polars**: NOT imported anywhere (`import polars`=0) -> `engine/data/providers/yahoo_polars.py` genuinely MISSING (archive gap real).
- **Secrets**: 0 hardcoded (grep `sk-`/`AKIA`=0). `eval`/`pickle`: 0 live vulns (only security-linter strings).
- **ENV BLOCKER**: all venv numpy ABI broken (cp311 `.pyd` under cp312) -> runtime import unverified until `uv sync`. Patch syntax+logic verified standalone.
- **Archive upgrade**: 8/11 new modules ALREADY in code; 4 missing (quality.py, yahoo_polars.py, feature_engine.py, alerting/).
- **Audit trail**: `C:/Users/Hi/Desktop/QNA_AUDIT_DEBAT.txt` | inventory `QNA_FILE_INVENTORY.txt` | `QNA_EXTENSION_LEDGER.txt`.
<!-- END CODE-TRUTH FOOTER -->
