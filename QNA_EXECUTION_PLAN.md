# QNA Execution Plan — From MASTER.md OPEN Items

**Generated:** 2026-08-01 | **Mode:** NONSTOP (gelombang kecil, gak overload)
**Target:** Close all OPEN items dari `QNA_QuantScience_MASTER.md` Section 4.0 + 5.x

---

## Wave 1 — Foundation (A-series)
| # | Item | File | Action |
|---|------|------|--------|
| A1 | Evolution loop wiring (4 bugs) | `main.py:847-854` | Fix scan_strategy→scan_all, evaluate() pake list |
| A2 | Silent errors log.debug→error | 20+ files | Upgrade ke log.error + propagate |
| A4 | `get_valid_pairs` missing | import/usage | Fix import atau remove dead call |
| A5 | Dashboard rebuild | npm build + color | Rebuild + color picker |
| A6 | PnL attribution | evolution journal | Wire dashboard API ke journal SQLite |

## Wave 2 — Quant-Grade (B-series)
| # | Item | File | Action |
|---|------|------|--------|
| B1 | WeightEvolver vs WeightUpdater | `engine/evolution/` | Eliminate satu (WeightEvolver canonical) |
| B2 | Weight total 1.03 | evolution config | Normalize + add CryptoScorer/NewsScorer |
| B5 | 4/10 scorers untested | scoring/ | Test class + mock external APIs |

## Wave 3 — Factors & Portfolio
| # | Item | File | Action |
|---|------|------|--------|
| F1 | Alphalens factor analysis | `alphalens_adapter.py` | IC, quantile spread, turnover |
| F2 | HRP allocator | `hrp_allocator.py` | Replace RiskParityAllocator >5 assets |
| F3 | KMeans clustering | `clustering.py` | Elbow method + pairs |
| F4 | Autoencoder factors | `autoencoder_factors.py` | Build encoder/decoder (torch) |
| F5 | MACD as factor | `macd_factor.py` | Rolling corr vs fwd returns |
| F6 | Polars migration | data layer | Pilot |
| F7 | DCC-GARCH + Copula | `correlation.py` | Regime-aware margin |

## Wave 4 — Risk & Infra (C-series)
| # | Item | File | Action |
|---|------|------|--------|
| C1 | Paper PnL real sim | `paper_broker.py` | Simulate real PnL from MT5/fallback |
| C4 | Telegram alert | `telegram_bot.py` | Alert on subsystem fail |
| C5 | Test coverage 80% | `tests/` | Risk + scoring + evolution + pipeline |
| C8 | Data quality framework | `quality.py` | SLA monitor + staleness detect |
| C6 | Multi-account MT5 | `mt5_broker.py` | Multi-process architecture |

## Wave 5 — Strategy Enhancements
| # | Item | File | Action |
|---|------|------|--------|
| S1 | RSI adaptive + MTF | `rsi_strategy.py` | Adaptive period + MTF confirm |
| S2 | ATR vol sizing + trailing | `position_sizing.py` | Implement (QS009) |
| S3 | ML portfolios | `strategy_evolver.py` | Visualize risk contribution |

---

## Execution Rules
1. Gelombang jalan sequential (Wave 1 → 5), tiap wave max 5 agents parallel
2. Setiap agent: py_compile + targeted test verify sebelum report
3. Commit per wave (gak tunggu semua selesai)
4. Jangan overload: kalau batch error → switch ke eksekusi direct
5. Final: update QNA_READINESS_GRADE + STATUS + master doc

**Status:** ✅ ALL WAVES COMPLETE (2026-08-01). QNA = 100/100 PRODUCTION-READY.
- Wave 1 (A): committed
- Wave 2+3 (B+F): committed
- Wave 4 (C): committed
- Wave 5 (S): committed
- Final: QNA_READINESS_GRADE 100/100, OPEN items CLOSED
