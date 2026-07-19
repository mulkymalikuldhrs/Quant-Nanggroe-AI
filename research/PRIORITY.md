# Hedge Fund — Master Priority List (UPDATED 2026-07-19)
## Dari 197+ resource → 225 resource — REALITY CHECK APPLIED

## ⚠️ KOREKSI: PRIORITAS SEBELUMNYA MEMILIKI KLAIM PALSU
Beberapa item sebelumnya ditandai ✅ KLONE tapi TIDAK PERNAH DI-CLONE. Berikut item yang benar-benar terverifikasi:

**BENAR-BENAR TERCLONE (verified):**
- ✅ PyPortfolioOpt → /e/PyPortfolioOpt
- ✅ Backtesting.py → /e/backtesting.py
- ✅ FinancePy → /e/FinancePy

**KLAIM PALSU — Belum Pernah Di-Clone:**
- ❌ Riskfolio-Lib — TIDAK PERNAH di-clone (diklaim ✅ tapi tidak ada)
- ❌ skfolio — TIDAK PERNAH di-clone
- ❌ VectorBT — TIDAK PERNAH di-clone
- ❌ Alpaca MCP — TIDAK TERVERIFIKASI di config

---

## 🟢 TIER 1 — CLONE + INTEGRASI SEKARANG (HIGHEST IMPACT)

### Data Backbone
| Resource | Stars | Priority | Alasan |
|----------|-------|----------|--------|
| OpenBB | 68K⭐ | 🔴 URGENT | Bloomberg Terminal OS. MISS TERBESAR dari semua research |
| TA-Lib | 8.7K⭐ | 🔴 URGENT | 150+ indikator industri. Wajib untuk semua strategi |
| pandas-ta | 5.8K⭐ | 🔴 URGENT | 130+ indikator + 60 candlestick. Pandas-native |

### Alpha Research
| Resource | Stars | Priority | Alasan |
|----------|-------|----------|--------|
| Alphalens | 3.7K⭐ | 🔴 URGENT | Factor performance analysis. Cari alpha factors dgn Sharpe > 2 |

### AI Trading OS
| Resource | Stars | Priority | Alasan |
|----------|-------|----------|--------|
| NoFxAiOS/nofx | 11.2K⭐ | 🔴 URGENT | AI Trading OS — multi-AI, debate arena, self-evolution. BELUM ADA di semua report sebelumnya! |

### Portfolio Optimization (yang beneran perlu di-clone)
| Resource | Stars | Priority | Alasan |
|----------|-------|----------|--------|
| Riskfolio-Lib | 4.4K⭐ | 🟢 HIGH | 26 risk measures |
| skfolio | 2K⭐ | 🟢 HIGH | scikit-learn API portfolio |
| VectorBT | 8.4K⭐ | 🟢 HIGH | Backtesting tercepat, Numba |

### Production Engine
| Resource | Stars | Priority | Alasan |
|----------|-------|----------|--------|
| nautilus_trader | 5K+⭐ | 🟢 HIGH | Rust-native, deterministik backtesting = live |
| QuantLib | 5K+⭐ | 🟢 HIGH | Standard industri derivatives pricing |

### Support Tools
| Resource | Stars | Priority | Alasan |
|----------|-------|----------|--------|
| mplfinance | 3.8K⭐ | 🟢 HIGH | Visualisasi candlestick wajib |
| zipline-reloaded | 3.5K⭐ | 🟢 HIGH | Factor research backtesting |
| bt | 2.1K⭐ | 🟢 HIGH | Portfolio backtesting |
| ffn | 1.8K⭐ | 🟢 HIGH | Financial metrics |
| py_vollib | 700+⭐ | 🟢 HIGH | Options pricing IV/Greeks |
| optopsy | 400+⭐ | 🟢 HIGH | Options backtesting |
| exchange_calendars | 400+⭐ | 🟢 HIGH | Backtest accuracy |

---

## 🟡 TIER 2 — CLONE NANTI

| Resource | Alasan |
|----------|--------|
| Stock-Prediction-Models (7.6K⭐) | ML model collection, butuh GPU |
| TradeMaster (1.5K⭐) | RL trading, NeurIPS'23, butuh training |
| deepdow (1.2K⭐) | DL portfolio optimization, niche |
| QuantLib | Butuh C++ build |
| LLM-TradeBot (181⭐) | Multi-agent ADF, early stage |

---

## 🔴 TIER 3 — REFERENSI

- awesome-trading-agents (LLMQuant) — Kurasi agent + MCP
- best-of-algorithmic-trading — 109 projects
- VisualHFT — Market microstructure (C#)
- jupyter-quant — Docker research env
- awesome-quant-tools-in-table — Perbandingan tools

---

## ⚡ RENCANA EKSEKUSI (7 Hari)

```bash
# Day 1: Data backbone
pip install openbb
pip install TA-Lib
pip install pandas-ta

# Day 2: Factor research
pip install alphalens-reloaded

# Day 3: AI Trading OS
git clone https://github.com/NoFxAiOS/nofx.git /e/nofx

# Day 4-5: Backtesting + Engine
pip install riskfolio-lib
pip install skfolio
pip install vectorbt
pip install nautilus_trader

# Day 6-7: Support tools
pip install mplfinance
pip install bt
pip install ffn
pip install py_vollib
pip install optopsy
pip install exchange_calendars
```

Updated: 2026-07-19 03:30 WIB | Sumber: RESEARCHBOT Cycle 1
