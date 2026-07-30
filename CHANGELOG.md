# Changelog — Quant Nanggroe AI

## 2026-07-30 — Session 9-10: Massive Parallel Audit + Evolution Loop + Renaissance Blueprint

### Added
- Evolution loop: 8 files in `engine/evolution/` (journal, handler, scheduler, scanner, disabler, updater, config)
- Evolution API endpoint: `api/routes/evolution.py` (5 endpoints)
- Dashboard evolution page: 3 tabs (strategies, trades, config)
- Providers: `providers/hidden_regime_provider.py` (3-tier CFTC/hidden-regime)
- Providers: `providers/news_provider.py` (3-tier AlphaVantage/RSS)
- Strategy wiring: `hedge_fund/signals/engine_strategies.py` (77 engine + 992 mue-x + 10 core = 1079 providers)
- Deployment: `deploy/docker/scripts/entrypoint.sh`
- Documentation: `docs/research_quant_scoring.md`
- Documentation: `docs/STATUS.md` (doc contradictions map)
- Graphify: `graphify-out/code_map.md`
- Color palette: `--color-accent: #D9A441`, `--color-primary: #0F172A`

### Fixed
- FRED API key hardcoded → env var (3 files)
- Bare `except:` → `except Exception` with logging (12 locations)
- `engine/scoring/` duplikat → deleted (11 files)
- Confidence formula → `tanh(|score|/40)`
- Live engine broken import path
- Dual pipeline silent fallback → CRITICAL log
- `asyncio.iscoroutinefunction` → `inspect.iscoroutinefunction`
- CI Python version GitHub 3.11 → 3.12
- Nginx upstream `agentic-ai:5000` → `api:8000`
- `credentials.json` removed from git tracking
- Stale artifacts cleaned (6 files)
- qna.py pipeline bug: `asyncio.run()` → direct `pipeline.run()`, `.get()` → `getattr()`
- Evolution scheduler: time-based trigger + threshold gate
- CSS surface colors: `#050510` → `#0F172A`
- AGENTS.md v15.4.0: all Session 9 changes
- README.md: modernized with pipeline flowchart
- QNA_AGENT_STATE.md: updated scorecard

### Broken (known)
- Evolution loop 4 wiring bugs in `main.py:847-854` — scan_strategy, evaluate, disable, update_weights type mismatches
- `np` undefined in `main.py:715` — StressVaR can't run
- WeightEvolver vs WeightUpdater: duplicate weight management
- Silent error swallowing: 4x `except: pass` + 20x `log.debug()` in main.py
- CryptoScorer + NewsScorer: untested, unweighted, total weight 1.03
- `get_valid_pairs()` missing in `main.py:298`
- credentials.md.txt: 100+ secrets pending Mulky action

## 2026-07-29 — Session 7-8: Core Pipeline + MTF + Evolution Foundation

### Added
- MTF engine: 4 frames + ConflictResolver
- Self-evolve loop: WeightEvolver + ScoreJournal
- SentimentScorer limit=180
- LLM Advisory layer (rule-based + 9router)
- Pair-class config (7 asset classes, 18 symbols)
- Dashboard branch extracted (v2-dashboard)
- FusionEngine wired to run_once() (Session 7)
- PositioningScorer from CFTC COT API
- TTLCache for Economic + Sentiment scorers
- mue-x dynamic discovery (760→51 lines)

### Fixed
- Pipeline refactored: 463→310 lines, 7 clean stages
- Test environment: numpy 2.5.1, httpx, scipy
- np.clip → _clamp() across all scoring files
- Weekly loss veto on Path-B
- Cherry-pick debris restored (8 directories)

## 2026-07-26 — Session 4-6: Initial Audit + Foundation

- Complete architecture graph
- Scoring engine code created (7 scorers)
- E:\ drive discovered and mapped
- github2 divergence documented (4141 files)
- 3 pre-existing test failures documented
- Canister docs updated (6/6 root + 7/7 canonical)
