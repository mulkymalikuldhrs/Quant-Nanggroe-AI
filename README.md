# Quant Nanggroe AI — Autonomous Quantitative Hedge Fund

**Slogan:** *"Wakafa billahi syahidan" — Gas dengan penuh amarah dan presisi.*

Single-entry autonomous hedge fund: **`python qna.py [mode]`**.

---

## 🏭 PIPELINE QNA — 7 Tahap

Bayangin QNA kayak pabrik mobil otomatis. Masukin data mentah (DXY, FRED, Fear&Greed, COT, harga) → lewat 7 tahap → keluar keputusan trading (BUY/SELL/HOLD) + ukuran posisi + manajemen risiko.

```
START → KONEK MT5 → GATE CHECK → ADA POSISI?
  │                                     │
  ├── YA → TRAIL SL → CLEANUP ──────────┘
  │
  └── TIDAK → CAUSAL CONTEXT (cuaca ekonomi)
              → SCREENER (scan market)
              → AGGREGATE (kumpulin 1079 suara)
              → FUSION ENGINE (8 juri kasih skor)
              → MTF ENGINE (cek 4 timeframe)
              → CONFLUENCE (gabungin semua)
              → BUY/SELL?
                    │
          ┌─────────┘
          ▼
     RISK CHECK (KillSwitch + 9 guard)
          │
     APPROVED? ───TIDAK──→ CLEANUP
          │
          YA
          ▼
     EXECUTE ORDER (kirim ke broker)
          ▼
     EVOLUTION (record PnL → scan → disable → update)
          ▼
     CLEANUP → LOOP LAGI (tiap N menit)
```

### Detail 7 Tahap:

**1. KONEK** — Connect ke MT5. Kalo gagal → paper mode. Gate check (walkforward viable?).

**2. CEK POSISI** — Ada posisi terbuka? Kalo ada → trail SL, selesai. Kalo gak → voting.

**3. VOTING (Otak QNA):**
   - **Causal Context** — Baca cuaca ekonomi (DXY, Bond, Risk On/Off)
   - **Screener** — Scan market cari peluang
   - **Aggregate** — Kumpulin suara dari **1079 "ahli"**: 77 engine strategies (SMC, Wyckoff, ICT) + 992 mue-x evolved + 10 core providers (FRED, Fear&Greed, COT)
   - **FusionEngine** — 8 juri kasih skor: Macro 30%, Economic 20%, Bond 10%, Sentiment 10%, Technical 10%, Positioning 10%, Volatility 5%, Geopolitical 5%
   - **MTF Engine** — Cek 4 timeframe (Monthly/Weekly/Daily/Session). Konflik? HTF ≠ LTF → kurangi posisi (REDUCE) atau batal (HOLD)
   - **ConfluenceScorer** — Gabungin aggregator + screener + fusion jadi satu keputusan (BUY/SELL/HOLD)

**4. RISK CHECK** — Kelly sizing → KillSwitch C5 (daily loss 1%, weekly 3%, drawdown 10%) → RiskGuard 9-checkpoint. Kalo gagal satu → gak jadi trade.

**5. EKSEKUSI** — Kirim order ke MT5 market order + trail SL.

**6. EVOLUSI** (🔴 BUTUH DIPERBAIKI) — Setelah trade closed: record PnL ke EvolutionJournal → cek trigger (20+ trade? 7 hari? 3x rugi?) → scan performance (Sharpe/Win Rate) → disable strategy rugi → update weight strategy profit.

**7. CLEANUP** — Putus koneksi. Selesai. Loop lagi.

---

## 🔴 KRITIKAL — Yang Lagi Rusak (Harus Diperbaiki)

| Blocker | Dampak |
|---------|--------|
| **Evolution loop 4 bug** — `main.py:847-854` | Evolusi gak pernah jalan. Weight gak pernah berubah |
| **np undefined** — StressVaR pake `np.array()` tanpa import numpy | Stress test gak jalan |
| **WeightEvolver vs WeightUpdater** — 2 sistem ngatur weight sama, data source beda | Last writer wins. Kacau |
| **Silent error swallowing** — 4x `except: pass` + 20+ `log.debug()` | Error invisible di production |
| **CryptoScorer + NewsScorer** — untested, unweighted. Total weight 1.03 | Skor kelebihan 3% |
| **get_valid_pairs() missing** — `main.py:298` import fungsi gak ada | Multi-pair discovery mati |

### Yang Udah Diperbaiki (Session 7-10)
✅ FusionEngine wired → 8 scorers 100% weight  
✅ MT5 live → Valetax demo $1,099, 29 closed trades  
✅ 1079 providers wired → 77 engine + 992 mue-x + 10 core  
✅ Evolution loop 8 files → integrated (tapi masih 4 bug)  
✅ E:\ extraction → HiddenRegimeProvider + NewsProvider (3-tier)  
✅ P0 fixes → 12 items (FRED key, bare except, CI, Docker, dll)  
✅ Pipeline bug → `asyncio.run()` diganti direct call  
✅ Dashboard evolution page → API + 3 tabs  
✅ Color palette → #0F172A + #D9A441  
✅ All *.md updated → 10 file root sinkron  
✅ 173+ tests pass → core + evolution

---

## 📦 STATS

| Metrik | Nilai |
|--------|-------|
| Python files | 678 |
| Strategies registered | 84 |
| Providers wired | 1079 (77 engine + 992 mue-x + 10 core) |
| Scorers | 8 (100% weight) |
| Exchange clients | 10 REST + MT5 + Solana |
| API routes | 40+ |
| Dashboard pages | 21 |
| Tests passing | 173+ |
| MT5 Balance | $1,099 (Valetax demo) |
| Git remotes | 4 (codeberg, github, github2, gitlab) |
| E:\ sources | hidden-regime, mue-x, AI-Trader, TradingAgents |

---

## 🚀 QUICK START

```bash
# Entry point
python qna.py [unified|api|daemon|hedge|status|stop]

# Via launcher (PYTHONPATH auto-cleared)
launch.bat api              # FastAPI on :8000
launch.bat daemon           # Background daemon
launch.bat dashboard        # Next.js on :3000

# Lint / Typecheck
ruff check quant_nanggroe/
mypy quant_nanggroe/ --ignore-missing-imports

# Tests
.venv/Scripts/python -m pytest tests/ -v

# Package
uv sync
```

**⚠️ Critical:** `PYTHONPATH=""` mandatory — Hermes venv leak causes crash.

---

## 🔧 STACK

| Layer | Choice |
|-------|--------|
| Language | Python 3.14 |
| Package | `uv` |
| API | FastAPI |
| Dashboard | Next.js 16 + React 19 + Recharts |
| Broker | MetaTrader5 (paper fail-closed) |
| Crypto | CCXT |
| Risk | KillSwitch C5 + DCC-GARCH + VaR + Kelly |
| Agent framework | LangGraph |
| Database | SQLAlchemy + Alembic |

---

## 📚 DOKUMENTASI

| File | Isi |
|------|-----|
| `AGENTS.md` | Panduan agent (canonical) |
| `CLAUDE.md` | Panduan Claude Code |
| `docs/Rencana.md` | Master blueprint 6 fase |
| `docs/QNA_COMPLETE_ARCHITECTURE_2026-07-29.md` | Architecture graph lengkap |
| `QNA_AGENT_STATE.md` | State file + scorecard |
| `docs/STATUS.md` | Doc contradictions map |
| `docs/research_quant_scoring.md` | Best practices |

Built by [Dhaher Labs](https://github.com/mulkymalikuldhaher).
