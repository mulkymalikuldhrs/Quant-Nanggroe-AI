# ADDITIONAL_RESEARCH.md — DeepResearch Briefing

> Scope: 2024–2026 literature on (a) financial time-series foundation models, (b) academic validity of SMC/ICT, (c) reinforcement learning for trading, (d) regime detection (HMM / ensemble).
> Method: `web_search` + `web_extract` over arXiv / SSRN / RePEc / peer-reviewed venues.
> Generated: 2026-07-15. Beneficiary: Quant-Nanggroe-AI worktree (research pipeline).

---

## 0. Overall Confidence

| Theme | Confidence | One-line verdict |
|---|---|---|
| (a) Financial TSFMs | **High** | Kronos/Time-MoE are real, peer-reviewed (AAAI'26 / ICLR'25), beat baselines on financial tasks. |
| (b) SMC/ICT validity | **Low** | No rigorous academic backing for ICT/SMC as taught; only weak/indirect support (low-tier journals, preprints, repackaged Wyckoff/order-flow). |
| (c) RL for trading | **High** | Active, well-reviewed subfield; systematic reviews + new LLM-news-augmented agents (2024–2025). |
| (d) Regime detection | **High** | HMM + ensemble voting is peer-reviewed (2025) and demonstrably beats buy-and-hold on risk-adjusted basis. |

Net: (a)/(c)/(d) are safe to build on; (b) should be treated as *unvalidated folklore* unless independently backtested in-repo.

---

## (a) Financial Time-Series Foundation Models (Kronos / Time-MoE / TimesNet)

### Confidence
**High.** Multiple peer-reviewed papers (AAAI 2026, ICLR 2025) plus preprint benchmarks.

### Key Findings
- **Kronos** (Shi et al., Tsinghua; arXiv 2508.02739, AAAI 2026) is the first open-source foundation model purpose-built for financial K-line ("language of markets"). A specialized tokenizer discretizes OHLCVA into coarse+fine tokens; pre-trained autoregressively on **>12B K-line records across 45 exchanges, 7 granularities**.
  - Zero-shot price forecasting: **RankIC +93% over leading TSFM, +87% over best non-pre-trained baseline (iTransformer)**.
  - Volatility forecasting MAE −9%; synthetic K-line generative fidelity +22%.
  - Explicitly shows *generic* TSFMs (Chronos, TimesFM, Moirai, Time-MoE) **underperform iTransformer/DLinear on financial tasks** — domain-specific pre-training matters.
- **Time-MoE** (Shi, Wang, Nie et al.; arXiv 2409.16040, ICLR'25 Spotlight) scales TSFMs to **2.4B params** via sparse Mixture-of-Experts on **Time-300B (~300B time points, 9 domains)**. Sparse activation = same compute as dense but higher capacity; validates scaling laws for time series. Strong zero-shot, but financially generic.
- **TimesNet** (Wu et al., ICLR 2023) remains the canonical "unify all analysis tasks via 2D temporal variation" backbone; still used as a baseline in 2025 financial-FM benchmarks (Kronos compares against it directly).
- **Moirai / Moirai-MoE** (Salesforce; arXiv 2410.10469, ICML'25) and **Moirai 2.0** (arXiv 2511.11698, 2025, 36M series) are the general-purpose leaders Kronos beats on finance-specific tasks.
- A 2026 benchmark paper (arXiv 2606.27100) tests pre-trained TSFMs vs train-from-scratch neural nets in a *conservative* financial setting — useful caution that zero-shot FMs are not universally dominant.

### Sources
1. Kronos — https://arxiv.org/abs/2508.02739 (code: https://github.com/shiyu-coder/Kronos)
2. Time-MoE — https://arxiv.org/abs/2409.16040 (code: https://github.com/Time-MoE/Time-MoE)
3. TimesNet — https://arxiv.org/abs/2210.02186 (lib: https://github.com/thuml/Time-Series-Library)
4. Moirai-MoE — https://arxiv.org/abs/2410.10469
5. Moirai 2.0 — https://arxiv.org/abs/2511.11698
6. Pretrained TSFMs for Financial (benchmark) — https://arxiv.org/abs/2606.27100

### Gaps
- Kronos/Time-MoE results are *research* backtests; no live-trading or transaction-cost-aware crypto proof yet.
- Most FMs benchmark on daily/15m K-line; behavior at high-frequency (tick/L2) untested.
- "Generative fidelity" for synthetic K-line is self-reported; no adversarial robustness check vs real market microstructure.

---

## (b) Academic Validity of SMC / ICT

### Confidence
**Low.** Strong negative signal: the academic literature does *not* validate ICT/SMC as taught. Support is indirect and low-tier.

### Key Findings
- **Direct ICT test:** Agarwal (OSF Preprint, 2023; DOI 10.31219/osf.io/7yw86) backtested "ICT Power of 3" on 14 forex pairs over 21 years and claims confidence in the concepts. **Caveat:** this is a *non-peer-reviewed, self-described enthusiast preprint* ("I have come to accept him as my mentor"), with only 2 references and no statistical-significance / overfitting controls. Not citable as rigorous evidence.
- **SMC + ML paper:** Whorra, Chandra & Lamba (IJNRD, Nov 2024) build an "SMC + Adaptive Market Hypothesis + non-linear ML" framework and claim backtest outperformance. **Caveat:** IJNRD is a low-tier open journal; methodology section lacks walk-forward / deflated-Sharpe controls; claims are assertive without robustness stats.
- **Roots are real, the branding is new:** SMC/ICT map onto (1) Wyckoff (1910) tape reading, (2) institutional order-flow / informed trading (Harris 2003; Osler 2000, 2001 — Fed NY support/resistance & currency orders), (3) support/resistance and liquidity zones — all of which *do* have academic grounding. The **ICT-specific narrative** (fair-value gaps, liquidity voids, "kill zones", "power of 3") has **no peer-reviewed validation**; trader communities (Reddit r/Forex, r/Trading) repeatedly note the absence of academic backing and call the logic repackaged/flawed.
- **Implication for the repo:** SMC/ICT concepts are *usable as feature hypotheses* (order blocks ≈ institutional imbalance zones; FVG ≈ price dislocation) but must be **independently backtested with CSCV / deflated-Sharpe** before any production weight.

### Sources
1. Agarwal (2023) ICT Power of 3 preprint — https://doi.org/10.31219/osf.io/7yw86 (RePEc: https://ideas.repec.org/p/osf/osfxxx/7yw86.html)
2. Whorra, Chandra & Lamba (2024) SMC+AMH framework — https://www.ijnrd.org/papers/IJNRD2411009.pdf
3. Osler (2000) Support for resistance / technical analysis — https://ideas.repec.org/a/fip/fednep/y2000ijulp53-68nv.6no.2.html
4. Osler (2001) Currency orders & exchange-rate dynamics — https://ideas.repec.org/p/fip/fednsr/125.html
5. Harris (2003) Trading and Exchanges (informed trading / microstructure) — Oxford UP (cited in Whorra et al.)
6. Community skepticism — https://www.reddit.com/r/Trading/comments/1l40jau/ , https://www.reddit.com/r/Forex/comments/p600uh/

### Gaps
- **No high-impact (Q1/Q2) journal or conference paper validates ICT/SMC edge.** The best available are a preprint and a low-tier journal.
- No study applies deflated-Sharpe / CSCV / multiple-testing correction to SMC signals → survivorship/overfitting unknown.
- "Smart money" (Ozik SSRN 2010) refers to *hedge-fund skill*, not ICT retail methodology — terminology collision creates false authority.

---

## (c) Reinforcement Learning for Trading

### Confidence
**High.** Active, systematic-review-backed subfield (2024–2025).

### Key Findings
- **News-Aware Direct Reinforcement Trading** (Lan et al., arXiv 2510.19173, Oct 2025): feeds **LLM-derived news sentiment scores + raw price/volume** straight into RL (DDQN & GRPO), *no handcrafted features, no manual rules*. On crypto, beats market benchmarks; confirms **time-series information is critical**. Hyper-tuned via Optuna/TPE.
- **Systematic review** (Bhuiyan et al., *ScienceDirect* 2025, cited 54×): surveys DL for algorithmic trading, validates prior advances and real-world performance — good entry map.
- **Trends review 2020–2025** (Cureus 2025): DRL for stock/portfolio/crypto matured; flags reproducibility and overfitting as open problems.
- **LLMs as reward shapers** (Samani, OpenReview): leverage LLMs to improve RL reward mechanisms for trading — aligns with the news-aware direction above.
- **Hybrid / risk-aware RL** (SSRN 5417114, 2025 "Balancing Profit and Risk"): augments reward with risk penalty — directly relevant to drawdown control.
- **Dynamic portfolio DRL** (Huang, arXiv 2412.18563, 2025): addresses dynamic asset-weight adjustment.

### Sources
1. News-Aware Direct RL Trading — https://arxiv.org/abs/2510.19173
2. Systematic review (Bhuiyan et al. 2025) — https://www.sciencedirect.com/science/article/pii/S2590005625000177
3. DRL trends 2020–2025 — https://www.cureusjournals.com/articles/12720-deep-reinforcement-learning-for-stock-portfolio-and-crypto-trading-insights-and-trends-2020-2025
4. LLM reward shaping for trading — https://openreview.net/forum?id=w7BGq6ozOL
5. Hybrid RL (profit/risk) SSRN — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5417114
6. Dynamic portfolio DRL — https://arxiv.org/abs/2412.18563

### Gaps
- Most RL trading papers still **overfit in-sample**; few report deflated-Sharpe or out-of-sample walk-forward with costs.
- Crypto RL (e.g. news-aware paper) uses limited symbols/periods; generalization to multi-asset FX/crypto unclear.
- Reward-engineering remains brittle; LLM-sentiment rewards add prompt-injection / drift risk.

---

## (d) Regime Detection — HMM / Ensemble

### Confidence
**High.** Peer-reviewed 2025 framework with reproducible metrics; corroborated by HMM+NN and HMM+RL studies.

### Key Findings
- **"A forest of opinions" — ensemble-HMM voting** (Gupta, Kapoor, Gupta, Natesan; *Data Science in Finance and Economics*, 2025, doi:10.3934/DSFE.2025019): combines tree ensembles (XGBoost bagging/boosting) with a 3-state HMM (bull/neutral/bear) on Russell 3000 & S&P 500 ETFs, **walk-forward 2010→2025**.
  - Voting (boosting–HMM): **Sharpe 1.40 vs 0.84 buy-and-hold**; max drawdown −16.7% vs −34.0%; win rate 69.8%.
  - Pure HMM underperforms (Sharpe 0.66) → **ensemble voting is the value-add**, not HMM alone.
- **HMM + Neural Networks + Black-Litterman** (Monteiro, arXiv 2407.19858, 2025): dual-model alpha on energy large-caps (QuantConnect, COVID 2019–2022) → **83% return, Sharpe 0.77**. HMM captures regime/temporal deps; NN captures non-linear patterns.
- **HMM + RL for portfolio** (Ndoutoumou, IDS2025): HMM-detected regimes feed an RL allocation layer — bridges (c) and (d).
- Practical implementations widely reproduced (QuantStart, QuantInsti) using `hmmlearn` as a trade filter.

### Sources
1. Ensemble-HMM voting framework — https://www.aimspress.com/article/id/69045d2fba35de34708adb5d (doi:10.3934/DSFE.2025019)
2. HMM + NN + Black-Litterman — https://arxiv.org/abs/2407.19858
3. HMM + RL portfolio (IDS2025) — https://www.cloud-conf.net/datasec/2025/proceedings/pdfs/IDS2025-3SVVEmiJ6JbFRviTl4Otnv/966100a067/966100a067.pdf
4. HMM practical filter (QuantStart) — https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/
5. HMM regime overview (QuantInsti) — https://blog.quantinsti.com/regime-adaptive-trading-python/

### Gaps
- HMM state-count is arbitrary (2/3/4); no principled selection beyond BIC in most studies.
- Regime labels are latent & non-stationary; HMM re-estimation frequency is under-studied (stale params in drift regimes).
- Ensemble-HMM gains concentrate in crisis avoidance (drawdown), not raw return — must be judged on risk-adjusted terms, not cumulative %.

---

## Cross-Cutting Takeaways for Quant-Nanggroe-AI
1. **Use Kronos (or Time-MoE) as a zero-shot feature/forecasting backbone**, but validate against iTransformer/DLinear before trusting — generic FMs can regress on finance.
2. **Treat SMC/ICT as unvalidated hypotheses.** Convert order-block / FVG ideas into testable features, then CSCV + deflated-Sharpe them. Do not ship on community claims.
3. **RL + LLM-news sentiment** is the 2025 state-of-the-art direction; pair with risk-penalized rewards (SSRN 5417114) for drawdown control.
4. **Regime gating is high-value:** an ensemble-HMM (boosting+HMM) filter materially cuts drawdown — a cheap, high-confidence module to add ahead of any signal model.
