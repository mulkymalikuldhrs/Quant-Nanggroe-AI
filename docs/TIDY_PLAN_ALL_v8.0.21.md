# TIDY PLAN ALL — QNA v8.0.21 (2026-09-02) — 994 dirs, 1451 files, 55 md, 20 ext

**SSOT:** `CANONICAL.md v8.0.21` — BAL 1445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, dashboard 31p

## 1. Syntax/Extension (files with .)
- **Tracked:** `py 1181` `tsx 62` `md 55` `json 30` `yml 29` `ts 23` `png 12` `yaml 11` `jsonl 8` `csv 5` `html 4` `toml 3` `bat 3` `bak 2` `mjs 2` `(no ext) 5`
- **Total FS:** `1434` `1322 code 98 docs 14 image` `MCP 23689 nodes` `graphify 28208 nodes 52870 edges 1219 communities`
- **Plan:** Keep `py` as SSOT, `tsx/ts` for dashboard, `md` for docs (SSOT footer), `json/yaml` for config, `sh/bat` for launch, `png/svg` for assets. Remove stray `bak`, `(no ext)` in root (`=1.20.0` artifact), `nul`.

## 2. All Directories (994 fs, 23 top)
- **Top:** `quant_nanggroe 836`, `tests 204`, `scripts 135`, `dashboard 96`, `archive 29`, `quant_nanggroe/engine 48`, `api/routes 46`, `tests/test_engine 29`, `engine/risk 27`, `archive/old-scripts 22`, `engine/agentic 12`, etc.
- **994** includes `.venv 800+`, `.git 100+`, `node_modules` — **not counted** for tidy.
- **Live:** `quant_nanggroe` `dashboard` `tests` `scripts` `config` `data` `logs` `docs` `archive` (read-only) `graphify-out` `tasks` `references`

## 3. Plan Tidy All Directories
- **KEEP:** `quant_nanggroe/` (800 py), `dashboard/src/app 31p`, `tests/` (204), `scripts/` (135), `config/` (mt5_accounts.yaml), `data/` (journal, ledger, persistence), `docs/` (54 md, but gitignored 98), `archive/` (read-only, 29), `tasks/` (4), `references/` (1)
- **CLEAN:** `.ruff_cache`, `.mypy_cache`, `.pytest_cache`, `__pycache__`, `quant_nanggroe_ai.egg-info`, `=1.20.0`, `nul`, `temp_file`, `append_p2.py`, `gate4_probe.py`, `walk_forward_fixed.py`, `agentic-ai-cover.png` in root (move to `assets/`), `.commandcode/` (untracked, check .gitignore)
- **ACTION:** `bash: rm -rf .ruff_cache .mypy_cache .pytest_cache __pycache__ quant_nanggroe_ai.egg-info nul temp_file "=\$*"` `powershell: Remove-Item -Recurse -Force`
- **VERIFY:** `git status --short` `py_compile 7 OK` `tsc clean` `MCP re-index 23689`

## 4. Plan Tidy All *md (55 tracked, 427 total)
- **Tracked 55:** `CANONICAL 1` `AGENTS 1` `README 1` `15 target` `v8.0.21` `BAR 1445` `docs/ARCHITECTURE_COMMITTEE 1` `docs/VECTOR_ARBITRAGE 1` (force-add)
- **Total 427:** `docs/vault 19` `docs/archive 5` `tasks 4` `archive/orphaned 3` `.agents/skills 4` etc — many ignored via `.gitignore:98 docs/`
- **Plan:** Bump all `55` to `v8.0.21` `BAL 1445` `vector 6 modul live` `SSOT footer` (done `45317e05`). Keep `docs/vault` filesystem sync (robocopy 13), not git. Remove `archive/orphaned_v6.2/FILE_LISTING.md` `utf-8` error (re-encode). Add `docs/TIDY_PLAN` itself.

## 5. Plan Tidy All Files (any)
- **Junk:** `=1.20.0` (uv version artifact), `nul` (Windows), `temp_file`, `append_p2.py`, `gate4_probe.py`, `walk_forward_fixed.py` (one-off scripts), `agentic-ai-cover.*` in root (duplicate of `dashboard/public/`), `.commandcode/` (opencode artifact, add to .gitignore if needed)
- **Config:** `pyproject.toml: 8.0.21` `openpyxl/reportlab/python-docx` `launch.bat 198` `launch.sh 121` `qna.py 1055` single entry `PYTHONPATH=""`
- **Data:** `data/*.json` `weekly_override 0 WIB` `kill_switch_state.json` `account_ledger.json` `lessons.json` — keep, but gitignore `data/`? Currently tracked `quant_nanggroe/data/account_ledger.json` `M` — keep as ledger
- **ACTION:** `git rm --cached` junk, `rm` filesystem, `echo ".commandcode/" >> .gitignore` if needed, `git add -f docs/VECTOR_ARBITRAGE.md` (force, docs ignored)

## 6. Documentation
- **SSOT:** `CANONICAL.md v8.0.21` `15 target` `v8.0.21` `BAL 1445` `vector Step 4.6`
- **Docs:** `docs/ARCHITECTURE_COMMITTEE.md` `docs/VECTOR_ARBITRAGE.md` `docs/TIDY_PLAN_ALL` `docs/SKILLS.md 92 skills` `docs/auto/graphs 5 mmd` `GRAPH_REPORT.md 341k` `graph.html 1M` `graph.json 33M`
- **Plan:** Keep `README.md` human quick-start, `AGENTS.md` hard shortcuts, `CANONICAL` SSOT, `docs/` for deep, `tasks/` for plan, `references/` for audit.

## 7. See Structure Direction with Detail
- **Direction:** `quant_nanggroe 836` **core** → `dashboard 96` **UI** → `tests 204` **guard** → `scripts 135` **automation** → `docs 54` **memory** → `graphify 28208 nodes 1219 communities` **map** → `vector 6 modul` **new dimension** `P=xî+yĵ+zk` `d=||P-P0||` `grid 0.05σ`
- **Graph:** `god BaseModel 284 StrategyParameters 283 safe_div 270 KillSwitch 208 StrategyRegistry 175` `surprising run_mtf_cycle→market_context` `1219 communities` `cohesion 0.025 Archive Market Adx` `question: Why does BaseModel connect 100+ communities?`
- **Weir:** `docs/ ignored but tracked 54` `MCP duplicate D-repositories vs Quant-Nanggroe 23689 vs 23747` `launch.bat 1 launch.sh 1` `scorer 9 shims` `strategies 84` `dashboard 31p` `API 46 file 207 route` `50+ claim vs 46` `commit session.md scrubbed GH013` `vector observability not execution` `committee 0.10 too permissive` `grid lot fixed`

## 8. Rethink + Debate zxy bla bla bla (50-council 18 findings)
- **zxy = vector 3D P=xî+yĵ+zk** `origin USD-base vs EUR/USD` `JPY/100` `√2 45°` `box merah` `threshold sigma*√2=0.0707` `double-trigger d>threshold OR box_breach` `eigenvector hedged vs directional` `all 28 C(28,3)=3276` `tri_arb non-atomic` `grid lot fixed 0.01 vs Kelly` `committee 0.10 noise` `CPCV 10/102 fail-open` `PnL STALE` `yfinance EURUSD=X` `tuning stale` `allocation 10/102`
- **Debate:** Wave1 Quant 10 (tri_arb atomic, grid Kelly, origin bias, committee threshold, CPCV, RR, PnL STALE, allocation), Wave2 AI/SE 16 (NIM REAL-ONLY swallow, d>threshold double, grid sigma, one-position bypass, MT5 thread, Math.random, CurrencyGraph 40 visible), Wave3 Research 18 (7 vs 28, NZD missing, weekly 0 mask, yfinance, tuning 72h, √2)
- **Think:** `zxy` is `manifold` **not** `chart`; `x=USD/100 y=EUR/100 z=EURUSD` `P0=mean 20` `d>threshold trigger` `grid 0.05σ` `eigenvector` `0.01 lot hedged 10 levels 0.1 lot 6.9% margin violates 10%` — **weir**.

## 9. Next Steps
1. **Clean junk:** `rm =1.20.0 nul temp_file append_p2.py gate4_probe.py walk_forward_fixed.py` `+ .commandcode` `.gitignore`
2. **Bump docs:** `v8.0.20→v8.0.21` done `45317e05` `b79f5214` `fb0aa19c` `c346c8bc` `3108f654` `1bcb6dcb` `3dd1d5f1` `b17eadf4`
3. **Wire vector live:** `Step 4.6 observability → grid mesh execution` `TRADE_ACTION_PENDING` `KillSwitch` `one-position`
4. **Fix P0:** `strategy_allocation fail-closed` `grid Kelly` `weekly 72h cap` `committee 0.25` `RR persist` `PnL 3-retry`
5. **Verify:** `py_compile 7 OK` `tsc clean` `MCP 23689` `test_vector 16/16` `test 29/29` `git status 0` `push 5 remote`

## 10. Plus/Minus/Pro/Cons/Weir/etc
- **Plus:** `MCP 23689 nodes` `vector 6 live` `drag SL/TP` `modify/close ticket+sl/tp` `export docx` `assistant LLM` `1s tick 32 checks` `probe 0/32` `weekly 0` `BAL 1445` `MT5 372044706` `FILLED NZDUSD 22:14 WIB`
- **Minus:** `tri_arb dry-run` `grid lot fixed` `committee 0.10 noise` `CPCV 10/102` `weekly 0 mask -13.7%` `yfinance` `tuning stale` `allocation 10/102` `MCP duplicate` `docs ignored` `graphify 164s fallback sequential`
- **Pro:** `fail-closed` `REAL-ONLY` `single position` `trailing short-aware` `BE+ATR` `monotonic` `auto-detect 372044706` `launch 1` `PWA 4h vs Electron 120MB`
- **Cons:** `vector origin bias USD` `JPY/100 normal but EUR-base alternative` `√2 myth` `sigma 0.05 540 pips EURUSD vs 500 pips JPY` `grid 0.05 across vols 10-100x`
- **Weir:** `docs/ 427 md but git 54` `vault 19 not versioned` `session.md scrubbed GH013` `=1.20.0` artifact `nul` Windows `quant_nanggroe 836` core but `tests 204` `scripts 135` `archive 29` `graphify 28208 nodes` `god BaseModel 284` `question BaseModel 100+ communities` `why KillSwitch 208`

## 11. Do Everything We Need
- **Do:** `list 1434` `1322 code 98 docs 14 image` `top 5 quant_nanggroe 836 tests 204 scripts 135 dashboard 96 archive 29` `20 ext py 1181 tsx 62 md 55` `994 dirs` `23 top` `53 md SSOT` `6 vector` `31 page` `46 api 207 route` `MCP 23689` `vector observability` `grid hedged` `docs bump` `clean junk` `push 5 remote`
- **Need:** `wire grid live` `fix P0 3` `verify tsc/py_compile/MCP` `graphify 1219 communities` `ask BaseModel bridge?` `go deeper?`

**Next:** `approve` → `clean junk` `wire grid` `fix P0` `push` `timeout 15000` `parallel sub-agent` `file:line`.
