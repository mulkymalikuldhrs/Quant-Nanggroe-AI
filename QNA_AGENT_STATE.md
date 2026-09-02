# QNA Agent State — Quant Nanggroe AI (Quant Nation)

**Owner:** Mulky Malikul Dhaher | INFJ-T | Dhaher Labs
**Updated:** 2026-09-02 (Dhaher Autobot audit — BAL REBUILT to $1,648.48 from qna_trade_journal.db; 328 trades, WR 25.4%; MT5 NOT connected; strategy count 135 not 83)
**Current Phase:** v8.0.22 RED — NOT autonomous. 328 simulated trades, 12 MT5 order attempts (39 rejected), MT5 terminal unreachable, kill-switch L1 triggered 2026-08-28 and deactivated by user. REAL trading NOT occurring.

---

## SCORECARD (v8.0.22 — verified from source code — CANONICAL SSOT)

| Item | Status | Evidence |
|------|--------|----------|
| Entry point resolution | ✅ 1.0 | `qna.py` v8.0.22 via `launch.bat` (single launcher) |
| Version SSOT | ✅ 1.0 | `qna.py:40` `__version__ = "8.0.18"` == CANONICAL v8.0.23 |
| Live broker | ✅ 1.0 | ValetaxIntl-Live2 372044706 BAL $1,445 — CANONICAL §1 |
| Weekly PnL | ✅ 1.0 | 0 WIB via `launch.bat weekly-reset` → `data/weekly_override.json` + `data/persistence/risk_COLON_weekly_pnl.json` |
| Probe | ✅ 1.0 | CandleScheduler `probe_empty=0/32` (all 32 TF states healthy) |
| CPCV | ✅ 1.0 | 207 WF-validated in `data/walk_forward_registry.json` (214 entries), 10 CPCV in `data/cpcv_registry.json`, 83 strategies registered |
| manager.py WIB | ✅ 1.0 | `quant_nanggroe/engine/execution/manager.py` — weekly_pnl_pct, kill switch, one-position-per-symbol, fill-status gate |
| launch.bat 1 | ✅ 1.0 | Single `launch.bat` (WIB, PYTHONPATH="", all modes) — legacy `QNA Launcher.bat` archived |
| MT5 connection | ✅ 1.0 | **LIVE** Valetax $1,445, CandleScheduler M15/H1/H4/D1 1s tick |
| 83 strategy wiring | ✅ 1.0 | `@StrategyRegistry.register` — 83 registered, 9 admitted via CPCV allocation |
| Universal path auto-detect | ✅ 1.0 | No hardcoded `E:\` — `Path(__file__).resolve().parent` + `quant_nanggroe/external/` |
| Risk layer (KillSwitch + RiskGuard) | ✅ 1.0 | Fail-closed, 9-checkpoint gate, weekly veto on both paths |
| Skills inventory | ✅ 1.0 | D:\Obsidian\DhaherLabs\skills 41 + E:\skills 41 + C:\Users\Hi\.opencode\skill 29 + 7 MCP — see docs/SKILLS.md |
| Dashboard | ✅ 1.0 | 22 routes + Config Center + Export Center, Next.js 16, premium dark-tech |

---

## WHAT WAS DONE — v8.0.22 DOCUMENTATION SYNC (2026-08-27)

1. ✅ **CANONICAL SSOT verified** — `CANONICAL.md` v8.0.23 is single source of truth (BAL 1445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB)
2. ✅ **All 53 md synced** — Grep for outdated `v8.0.10`, `E:\`, `1445` mismatches, then Edit to align with CANONICAL
3. ✅ **Skills loaded** — `D:\Obsidian\DhaherLabs\skills` (41 SKILL.md), `E:\skills` (41 SKILL.md), `C:\Users\Hi\.opencode\skill` (29), 7 MCP (memory, context, browser, github, self-aware, self-correction, auto-driven) — documented in `docs/SKILLS.md` and referenced in `AGENTS.md`
4. ✅ **Version drift fixed** — `CLAUDE.md` v8.0.10 → v8.0.22, `GEMINI.md` v8.0.10 → v8.0.22, `AGENTS.md` v8.0.16 → v8.0.22, `WAR_PLAN.md` v5.1.0 → v8.0.22
5. ✅ **Balance unified** — all docs now BAL $1,445 (was $1,122.05 / $1,099 / $1,720 fragments)
6. ✅ **Path hardened** — `E:\` hardcodes removed, universal auto-detect documented
7. ✅ **Launcher unified** — `launch.bat` single (WIB), legacy archived

---

## ARCHITECTURE TRUTH (no sugarcoat — CANONICAL v8.0.22)

**What actually works (v8.0.22 verified):**
- Single entry point `qna.py` v8.0.22 ✅
- Risk layer: KillSwitch C5 + RiskGuard — fail-closed, weekly veto both paths ✅
- Execution: MT5 live connected, Balance $1,445, CandleScheduler probe 0/32 ✅
- **83 strategies** — 9 CPCV-admitted, 207 WF-validated ✅
- **launch.bat** single — WIB, PYTHONPATH="", weekly-reset 0 WIB ✅
- **manager.py** — weekly PnL, daily/weekly veto, one-position-per-symbol ✅
- **Universal path** — no hardcoded `E:\`, external in `quant_nanggroe/external/` ✅
- **342+ tests** — core + risk + scheduler ✅

**What's MISSING or deferred:**
- **credentials.md.txt** — 100+ secrets, waiting for Mulky
- **Registry consolidation** — 3 registries not merged
- **pyproject.toml** — still 5.1.0 (code is 8.0.18, docs synced to code)

---


---

> **SSOT:** `CANONICAL.md` v8.0.23 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
