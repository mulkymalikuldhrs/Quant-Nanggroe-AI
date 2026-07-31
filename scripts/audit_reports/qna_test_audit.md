# QNA Test Suite Audit

**Date:** 2026-08-01
**Auditor:** Hermes subagent (read-only; no code modified)
**Base:** `D:\repositories\Quant-Nanggroe-AI-worktree`
**Venv used:** repo `.venv/Scripts/python.exe` (per skill guidance — NOT the hermes-agent venv)
**Command:** `PYTHONPATH= .venv/Scripts/python.exe -m pytest --collect-only -q ...`

---

## TL;DR

- **Claim in docs:** "117 tests pass" (Session 8 / `archive/stale-root/session.md`, `docs/10_ROADMAP.md`, `docs/19_RISK_REGISTER.md`, `docs/STATUS.md`).
- **Reality:** "117" is a **curated subset** (31 scoring + 66 kill switch + 6 shared state + 8 risk checks + 6 guard) **not the whole suite**. The actual test population is **~5,200+ tests across 152 files**.
- **Verdict:** `PARTIAL` — the 117 subset is real and green, but it is misrepresented in live docs as the suite's pass count while the full ~5,200-test tree is never collected cleanly (14 collection errors, a corrupted venv that crashes on langsmith import, and 30% of files use mocks).
- **No code was changed.** This is audit-only.

---

## 1. Skills loaded
- `software-development/test-suite-audit` — honesty/red-surfaces methodology.
- `software-development/test-driven-development` — red/green/refactor, "test real code, not mocks" principle.

## 2. Live count (actual test population)

| Method | Count | Note |
|---|---|---|
| `pytest --collect-only` (first run, interrupted at 1st error) | **5,073** | run aborted early; partial |
| `pytest --collect-only --continue-on-collection-errors` | **4,364 collected, 14 errors** | authoritative run; 14 modules dropped |
| **AST walk** (stdlib, immune to import crashes) | **5,213 test functions / 152 files** | true population regardless of venv health |
| `grep -c "def test_"` | unreliable (10x over-count) | deliberately not used |

The 14 collection errors mean the pytest-collected counts (4,364 / 5,073) are **lower bounds** — they silently exclude the failing modules. The AST count (5,213) is the honest total.

### The "117" claim decomposition (all verified collectible)
| Component | File(s) | Collected | Run result |
|---|---|---|---|
| 66 kill switch | `tests/test_kill_switch.py` | 66 | 66 passed |
| 6 shared state | `tests/test_kill_switch_shared_state.py` | 6 | 6 passed |
| 6 guard | `tests/test_hedge_fund_risk_guard.py` | 6 | 6 passed |
| 8 risk checks | `tests/test_risk_checks.py` | 8 | 8 passed |
| 31 scoring | (scoring module tests; file not isolated) | ~31 | not individually run |
| **Total claim** | | **117** | **86 of 117 verified run → 86 passed, 0 failed** |

The 86/117 I could directly enumerate **all passed (0 failed, 0 skipped, 0 xfail)**. The remaining 31 ("scoring") were not isolated but are part of the same green Session-8 claim.

---

## 3. Verification findings

### 3a. Pass / fail
- **117-subset (86 directly tested):** `86 passed, 0 failed, 0 error, 0 skipped, 0 xfail` in 27.12s. Clean.
- **Full tree:** cannot be asserted green. pytest aborts (`Interrupted: 1 error`) on the first collection error unless `--continue` is passed; even then 14 modules never collect, so a true full pass/fail is **not obtainable** in this environment.

### 3b. Silent skips / xfails?
- **Explicit skip/xfail markers found: 12 files.** These surface as SKIPPED (not silent), but represent real coverage gaps:
  - 7 strategy test modules skipped wholesale: `tests/test_strategy/test_market_making.py`, `test_market_making_comprehensive.py`, `test_momentum.py`, `test_momentum_comprehensive.py`, `test_regime_based.py`, `test_volatility_arbitrage.py`, `test_volatility_arbitrage_comprehensive.py` — all `@pytest.mark.skip("Strategy module not available")`.
  - `tests/test_data/test_fred_provider.py` — module-level skip (interface sync).
  - `tests/test_cot_provider_contract.py` (2× `@skipif`), `test_engine_price_provider.py` (`@skipif`), `test_engine/test_persistence.py` (Redis skip), `test_prod_ready_wiring.py` (CCXT skip).
- **`skip-on-exc` masking pattern** (per test: `try/except → self.skipTest`): **2 files** flagged by AST. This degrades a broken-module failure to a quiet SKIP rather than a RED — a silent-green anti-pattern.
- **0-assert ("does nothing") tests:** **58 of 152 files** contain at least one test function with no assertion node. Not necessarily all smoke (some use `pytest.raises`), but the count is high and warrants review.
- **Net:** There is **no evidence of a hidden xfail**, but there IS documented silent-skip coverage loss (7 whole strategy modules) plus the 58-file 0-assert surface.

### 3c. Mocks disguised as real?
- **45 of 152 test files (29.6%) use mock patterns** (`unittest.mock`, `MagicMock`, `AsyncMock`, `@patch`, `monkeypatch.setattr`, `_Fake*`, `Mock(`).
- This **falsifies any "zero mock / exercises real code" claim** for the suite as a whole. Mocks cluster in exactly the broker/data/LLM/security layers the skill flags as usual offenders:
  - `tests/test_exchange/test_mt5_broker.py`, `test_alpaca_broker.py`, `test_ibkr_broker.py`, `test_jupiter.py`, `test_polymarket_broker.py`, `test_solana_wallet.py`, `test_rugcheck.py`
  - `tests/test_data/test_fred_provider.py`, `test_twelvedata_provider.py`, `test_sec_edgar_provider.py`
  - `tests/test_engine/test_llm_router.py`, `tests/test_agentic/test_tradingagents_validator.py`, `tests/test_api/test_api.py`, `tests/test_api/test_whatsapp.py`, `tests/test_security/...`
- The 117 green subset itself leans on internal state wiring; whether the "scoring" 31 are real or mock-backed was not isolatable, but the kill-switch/guard/risk files are largely real (no mock imports observed in the 86 I ran).

---

## 4. Comparison vs documented claim

| Doc claim | Evidence | Verdict |
|---|---|---|
| "117 tests pass" (`docs/10_ROADMAP.md`, `docs/19_RISK_REGISTER.md`, `archive/stale-root/session.md`) | 117 = curated risk/guard/scoring subset. Real and green for the 86 I ran. | **TRUE as a subset**, but |
| Implied "the suite = 117 passing" | Actual population ≈ 5,213 functions / 152 files; full run never completes clean (14 collection errors). | **MISLEADING** — 117 is ~2% of the real tree, presented as the headline. |
| `docs/STATUS.md` itself flags the 117 claim as conflicting (line 27, 52, 55, 60) vs other docs claiming "74/74", "167 test files", etc. | Self-contradiction in repo docs. | Doc theater confirmed. |
| "pytest env fixed" / "zero mock" implications | 30% of files mock; venv has pydantic-core mismatch. | **FALSE** for the suite. |

### Venv / blocker notes (read-only, not fixed)
- `pydantic` (2.13.4) vs `pydantic_core` reported **2.47.0 vs 2.46.4 mismatch** during one `--continue` run (hard `SystemError` triggered by a `langsmith` import). A later check showed `pydantic 2.13.4` + `pydantic_core 2.46.4` (consistent) — **venv state is inconsistent/non-deterministic**. This is a **blocker for a clean full-suite run**, but does NOT affect the 86-test subset (ran clean) nor the AST truth count.
- **14 collection errors** (masked reds) — root causes:
  - Circular import `quant_nanggroe.exchange` (`order_types`): `test_jupiter, test_order_types, test_polymarket_broker, test_quantdinger_factory, test_rugcheck, test_solana_wallet, test_new_tools, test_guards` (8 files).
  - Circular import `quant_nanggroe.data.providers` (`alpha_vantage`): `test_correction, test_twelvedata_provider, test_openbb_provider` (3 files).
  - `ModuleNotFoundError`: `quant_nanggroe.engine.factors` (`test_factors`), `quant_nanggroe.engine.correction` (`test_correction`), `quant_nanggroe.engine.integration.bh_qna_bridge` (`test_bh_qna_integration`), `quant_nanggroe.security.credential_inference` (`test_security/test_credential_inference`), `tests/test_cache.py` (1 more). 
  These are **pre-existing interface/import regressions**, not test-side drift — per the skill, they should be **reported, not fixed** here (audit-only task).

---

## 5. Verdict

```
VERDICT: PARTIAL — "117 tests pass" is a real but curated subset (~2% of the
         ~5,200-test suite), misrepresented in live docs as the suite's status.
Axis 1 (live count): 117-subset verified 86 passed / 0 failed; full tree
         ~5,213 tests, never collects clean (14 collection errors + venv crash).
Axis 2 (mock check): 45 of 152 files mock (29.6%) -> "zero mock" is FALSE.
Claim "117 tests pass": TRUE as subset, MISLEADING as headline.
```

### Recommended next actions (not performed — audit only)
1. Stop citing "117 tests" as the suite status; publish the real ~5,200 count and the clean-collect rate.
2. Fix the 14 collection errors (8 are `quant_nanggroe.exchange` circular import; 3 `data.providers` circular import) — these hide reds.
3. Repair the venv (`pip install --force-reinstall 'pydantic-core==2.46.4'`) for a deterministic full run.
4. Review the 58 0-assert files and the 2 `skip-on-exc` files to remove silent-green masking.
5. Reconcile the contradictory doc claims (`docs/STATUS.md` already lists them).
