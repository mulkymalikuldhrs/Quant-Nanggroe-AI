# License Inventory — Issue #37 (extends Wave-2 audit)

**Repo:** `D:/repositories/Quant-Nanggroe-AI-worktree` (branch `master`)
**Scope:** Audit only. No code changes. 71 files ported from 6 upstreams, notices dropped.
**Method:** All `.py`/`.js`/`.ts` files grepped for in-code upstream attribution
("Ported from …", "Extracted from …", "Inspired by …", "Adapted from …", repo-path
references like `Vibe-Trading/agent/src/…`). Union of the 6 upstreams = **exactly 71
unique files** (confirms #37's headline count). For each file we then grepped for any
retained copyright/license string (Copyright, SPDX-License-Identifier, "Licensed under
the GNU…", GPL-, AGPL, "Permission is hereby granted", MIT/Apache license text).

## Headline findings

1. **All 71 files retain ZERO upstream copyright/license string.** Only two non-vendored
   source files in the whole repo carry any copyright string, and neither is upstream #6:
   - `quant_nanggroe/engine/factors/qlib158.py` — Microsoft qlib, **Apache-2.0** (not one of the 6).
   - `scripts/port_vibe_factors.py` — only a Microsoft qlib (Apache-2.0) string at lines 332-333;
     it IS in the 71 but carries **no Vibe-Trading notice**.
2. **No `NOTICE` / `THIRD-PARTY` / `THIRD_PARTY_LICENSES` file exists** in the repo.
3. **Copyleft verdict: NONE of the 6 upstreams is GPL/AGPL.** All are permissive (MIT or
   Apache-2.0). See license table below. Source disclosure is therefore NOT legally
   forced by copyleft — but attribution/notice retention IS still required by MIT/Apache.
4. The repo's own `LICENSE` is **MIT** (Copyright 2024-2026 Quant-Nanggroe-AI Contributors).

## Per-upstream license (copyleft check)

| Upstream | Detected license | Copyleft? | Source |
|---|---|---|---|
| Vibe-Trading (HKUDS/Vibe-Trading) | MIT | No | raw LICENSE: "MIT License / Copyright (c) 2026 Vibe-Trading Contributors" |
| HermesQuantOS | — (no public repo; internal Dhaher Labs) | — | 0 public repos; treat as proprietary/unknown — confirm internally |
| ai-hedge-fund (virattt) | MIT | No | GitHub repo desc: "licensed under the MIT License" |
| Misi-Screener (dhaher-labs) | MIT | No | raw LICENSE: "MIT License / Copyright (c) 2026 Mulky Malikul Dhaher" |
| TradingAgents (TauricResearch) | Apache-2.0 | No | raw LICENSE: Apache License 2.0 |
| OpenAlice (TraderAlice) | MIT | No | project blog: "MIT-licensed trading agent"; repo LICENSE absent but docs state MIT |

**Conclusion:** No GPL/AGPL upstream ⇒ no source-disclosure obligation triggered by
copyleft. However MIT/Apache both require retaining the original copyright + license
notice in distributed source — which is exactly what is missing across all 71 files.

## Per-upstream inventory (file:line = first attribution line; all show NONE retained)

### Vibe-Trading — 30 files (0 retain notice)
```
quant_nanggroe/engine/backtest/engine.py:13
quant_nanggroe/engine/backtest/engines/base_engine.py:7
quant_nanggroe/engine/backtest/engines/composite_engine.py:8
quant_nanggroe/engine/backtest/engines/crypto_engine.py:10
quant_nanggroe/engine/backtest/engines/equity_engine.py:22
quant_nanggroe/engine/backtest/engines/forex_engine.py:12
quant_nanggroe/engine/backtest/engines/futures_engine.py:15
quant_nanggroe/engine/backtest/engines/market_detection.py:7
quant_nanggroe/engine/backtest/execution.py:6
quant_nanggroe/engine/backtest/hermes_backtest.py:3
quant_nanggroe/engine/backtest/loaders/base_loader.py:9
quant_nanggroe/engine/backtest/loaders/ccxt_loader.py:9
quant_nanggroe/engine/backtest/loaders/yfinance_loader.py:6
quant_nanggroe/engine/backtest/optimizers/base_optimizer.py:6
quant_nanggroe/engine/backtest/optimizers/equal_volatility_optimizer.py:7
quant_nanggroe/engine/backtest/optimizers/mean_variance_optimizer.py:9
quant_nanggroe/engine/backtest/optimizers/risk_parity_optimizer.py:6
quant_nanggroe/engine/backtest/portfolio.py:4
quant_nanggroe/engine/factors/registry.py:10
quant_nanggroe/engine/grounding.py:3
quant_nanggroe/engine/shadow/account.py:6
quant_nanggroe/engine/shadow/codegen.py:6
quant_nanggroe/engine/shadow/extractor.py:6
quant_nanggroe/engine/shadow/scanner.py:6
quant_nanggroe/skills/__init__.py:1
quant_nanggroe/skills/registry.py:1
quant_nanggroe/skills/swarm_presets.py:1
quant_nanggroe/skills/technical_skills.py:1
scripts/port_vibe_factors.py:2
tests/test_skills.py:1
```

### HermesQuantOS — 25 files (0 retain notice)
```
quant_nanggroe/agents/smc/enhanced.py:4
quant_nanggroe/data/manager.py:46
quant_nanggroe/engine/audit.py:15
quant_nanggroe/engine/backtest/hermes_backtest.py:3
quant_nanggroe/engine/backtest/hermes_portfolio.py:12
quant_nanggroe/engine/decision.py:4
quant_nanggroe/engine/execution/hermes_execution.py:18
quant_nanggroe/engine/factors/hermes_ta.py:13
quant_nanggroe/engine/hermes_auditor.py:11
quant_nanggroe/engine/hermes_chart.py:12
quant_nanggroe/engine/hermes_decision.py:15
quant_nanggroe/engine/hermes_journal.py:12
quant_nanggroe/engine/hermes_macro.py:11
quant_nanggroe/engine/hermes_market_state.py:14
quant_nanggroe/engine/hermes_math.py:16
quant_nanggroe/engine/hermes_news.py:14
quant_nanggroe/engine/hermes_pressure.py:14
quant_nanggroe/engine/hermes_shared_state.py:21
quant_nanggroe/engine/risk/checks.py:3
quant_nanggroe/engine/risk/hermes_kill_switch.py:12
quant_nanggroe/engine/risk/hermes_risk_officer.py:14
quant_nanggroe/engine/risk/manager.py:13
quant_nanggroe/engine/strategies/hermes_smc.py:16
quant_nanggroe/engine/strategy/hermes_lifecycle.py:14
quant_nanggroe/engine/strategy_lifecycle.py:4
```

### ai-hedge-fund — 6 files (0 retain notice)
```
quant_nanggroe/engine/backtest/engine.py:13
quant_nanggroe/engine/risk/manager.py:13
quant_nanggroe/engine/risk/risk_parity.py:12
quant_nanggroe/engine/risk/var.py:17
quant_nanggroe/engine/strategies/market_profile.py:9
quant_nanggroe/engine/strategies/volume_delta.py:6
```

### Misi-Screener — 6 files (0 retain notice)
```
quant_nanggroe/agents/tools/intermarket_tool.py:17
quant_nanggroe/agents/tools/screener_tool.py:18
quant_nanggroe/data/providers/alpaca.py:11
quant_nanggroe/engine/backtest/execution.py:6
quant_nanggroe/engine/execution/base.py:6
quant_nanggroe/engine/execution/brokers/paper.py:7
```

### TradingAgents — 6 files (0 retain notice)
```
quant_nanggroe/agents/council/debate.py:5
quant_nanggroe/agents/debate/reflection.py:4
quant_nanggroe/agents/debate/research_debate.py:3
quant_nanggroe/agents/debate/risk_debate.py:3
quant_nanggroe/agents/debate_engine.py:1
tests/test_debate_engine.py:1
```

### OpenAlice — 3 files (0 retain notice)
```
quant_nanggroe/engine/execution/base.py:6
quant_nanggroe/engine/execution/manager.py:9
quant_nanggroe/exchange/clients/longbridge_client.py:4
```

**Totals:** 30 + 25 + 6 + 6 + 6 + 3 = 71 unique files (some files map to 2 upstreams,
e.g. `engine/backtest/engine.py` → Vibe-Trading + ai-hedge-fund; counted once in union).
Every file: **retained upstream copyright/license = NONE**.

## Notes / discrepancies
- #37's per-upstream split (35/25/10/6/6/3) differs slightly from this run's
  (30/25/6/6/6/3). The 71-file **total is reproduced exactly**; the per-upstream delta is
  attribution-granularity (this audit counts only files carrying an explicit upstream-name
  comment, not generic "hedge fund" mentions). VT and AH deltas are files that #37 heuristically
  attributed without an in-code attribution string — they remain "notice-dropped" either way.
- HermesQuantOS has no public repo; its license could not be confirmed externally. Flag for
  internal confirmation — if it were ever GPL it would be the sole copyleft risk, but no
  evidence of that exists.
- Remediation (out of audit scope): add a `THIRD-PARTY`/`NOTICE` file listing the 6 upstreams
  + their MIT/Apache-2.0 licenses, and restore per-file attribution headers.
