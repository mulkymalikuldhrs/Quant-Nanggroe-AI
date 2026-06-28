# Debate Record: Theme 2 — Strategy Research & Alpha

**Date:** 2026-06-28
**Presiding:** CIO (w: 2.5)
**Council:** QR (w: 1.5), QDev (w: 1.2), PM (w: 2.0)
**Questions:** Q15-Q19 from `/root/qna-debat.txt`

---

## Round 1: Initial Stances

### QR
- **Q15:** Gu-Kelly-Xiu gives cross-sectional ML factor methodology replicable on crypto. Qlib provides institutional-grade backtest infra.
- **Q16:** Momentum, cross-sectional mean reversion (Avellaneda-Lee 2010), volatility carry, betting-against-beta. Most transferable: momentum + reversal + regime-conditional carry.
- **Q17:** Daily arxiv-sanity crawl → LLM extracts methodology → parameterize → walk-forward → rank → archive 90%.
- **Q18:** Holy grail = trap. 0/8 positive OOS proves it. Path: incremental factor stacking + Kelly sizing.
- **Q19:** Need per-symbol transaction cost model, microstructure (VPIN, order book), cross-asset correlation, bootstrap CIs, strategy decomposition.
- **Rejects:** Holy grail ML, any strategy without 3yr walk-forward, raw Sharpe without bootstrap CIs.

### QDev
- **Q15:** Stock return predictor = lowest-hanging fruit. Qlib = biggest bang-for-buck.
- **Q16:** Momentum ~200 lines. Pairs ~300 lines. StatArb ~500 lines. ML via Qlib needs data adapters.
- **Q17:** Arxiv pipeline ~2 weeks v0. Hardest: papers don't publish clean hyperparameters.
- **Q18:** Holy grail = #1 overfitting trap. Real path: feature store → 5-10 strategies → regime detection → meta-labeler → ensemble → auto-disable.
- **Q19:** Gaps: real data, strategy registry with walk-forward, risk management (Kelly, stop-loss, circuit breaker), live trading adapter.
- **Feasibility concerns:** RL hedging months of work. Arxiv auto-ingestion low ROI. Holy grail overfits.

### PM
- **Q15:** Zero deployable code. Qlib worth taking. Everything else academic overhead — skip it.
- **Q16:** Regime switching + vol targeting = proven winner. Add trend following (ATR) + short-term mean reversion (1h).
- **Q17:** **Zero investment in arxiv.** Broken pipeline = more overfit garbage. 100% research into why RegimeBased works.
- **Q18:** No holy grail. Portfolio of uncorrelated simple strategies. RegimeBased + mean reversion + trend following + vol carry.
- **Q19:** Missing: live risk management, portfolio correlation monitoring, trade journal, benchmark comparison.
- **Veto:** Any academic paper until ≥3 strategies positive OOS. Any strategy requiring options/NLP. The term 'holy grail'.

### CIO (Initial)
- **Q15:** 2/10 actionable. López de Prado mandatory reading.
- **Q16:** Poach industry math, reimplement with regime filter. GS-Quant, Qlib, 151 Strategies catalog.
- **Q17:** 10% dev time to research. 90% to deploy RegimeBased + data pipeline.
- **Q18:** Holy grail = capital trap. 180-combo walk-forward proved it.
- **Q19:** Gap is operational, not intellectual.
- **Veto:** New ML research until RegimeBased 30 days paper. No more academic paper tours. No holy grail.

---

## Round 2: CIO Final Decision

### Research Allocation
**15% research, 85% deployment.** Approved research:
1. Factor regression framework (diagnostic for RegimeBased forensic analysis)
2. Regime-conditional slippage model (needed for live execution)
3. Run 151 Trading Strategies catalog through regime filter (15% effort)

**Suspended:** Microstructure/VPIN/order book, academic paper arxiv pipeline, RL hedging, any ML strategy research.

### Strategy Discovery
Mine **151 Trading Strategies catalog** (Kakushadze 2015) — clean formulas, no paper ambiguity, 151 fully specified strategies implementable in days. Run each through regime filter (trending/mean-reverting/risk-off). Select top 2 uncorrelated to RegimeBased. Paper trade 4-week OOS.

No academic paper ingestion, no arxiv, no external APIs, no options, no NLP.

### Priority Ranking
1. Deploy RegimeBased on real data via broker API + 30-day paper trading
2. Build live risk management layer (stop-loss, position sizing, drawdown kill switch, correlation monitor)
3. Wire real data pipeline (yfinance/OpenBB for prices, broker API for fills)
4. Strategy registry with walk-forward framework
5. Implement 2 uncorrelated paper strategies from 151 catalog (momentum + mean reversion) with regime filter → 4-week OOS
6. Factor regression framework + bootstrap CIs on Sharpe
7. Cross-asset correlation tracker + transaction cost model

### Vetoes
1. Academic paper ingestion pipeline (arxiv/automated crawl) — zero investment
2. New ML strategy research until RegimeBased has 30 days paper trading
3. Any strategy requiring options, NLP, or external data APIs — crypto spot only
4. 'Holy grail' banned from all discussion, planning, and code
5. Microstructure/VPIN/order book research as blocker to deployment

---

**Status: COMPLETE**
**Next:** Theme 3 — UI Architecture & Visualization (Q5-Q7, Q14, Q43-Q61)
