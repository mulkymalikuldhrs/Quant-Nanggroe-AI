<div align="center">

<!-- Animasi: Header Ketik -->
<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=36&duration=3000&pause=1000&color=FF6B35&center=true&vCenter=true&multiline=true&repeat=true&width=800&height=120&lines=HERMES+QUANT+OS;Infrastruktur+Trading+Otonom+Multi-Agent" alt="HERMES QUANT OS" />

<br/>

<!-- Badge Animasi -->
<img src="https://img.shields.io/badge/Versi-4.0.0-FF6B35?style=for-the-badge&logo=semver&logoColor=white&labelColor=0A0A0A" alt="Versi" />
<img src="https://img.shields.io/badge/Status-Alpha_/_Under_Development-FFA500?style=for-the-badge&logo=semver&logoColor=white&labelColor=0A0A0A" alt="Status" />
<img src="https://img.shields.io/badge/Agent-21_di_5_Lapisan-00D4FF?style=for-the-badge&logo=azuredevops&logoColor=white&labelColor=0A0A0A" alt="Agent" />
<img src="https://img.shields.io/badge/Lisensi-MIT-blue?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=0A0A0A" alt="Lisensi" />

<br/><br/>

<!-- Pemilih Bahasa -->
<a href="./README.md"><img src="https://img.shields.io/badge/EN-English-00D4FF?style=flat-square" /></a>
<a href="./README_id.md"><img src="https://img.shields.io/badge/ID-Bahasa_Indonesia-FF6B35?style=flat-square" /></a>
<a href="./README_zh.md"><img src="https://img.shields.io/badge/CN-中文-00FF88?style=flat-square" /></a>

<br/><br/>

<!-- Animasi: Pulse -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0A0A0A,50:1A1A2E,100:16213E&height=120&section=header&text=&fontSize=0&animation=fadeIn" width="100%" alt="Header Wave" />

<br/>

**Fork dari [NousResearch/Hermes](https://github.com/NousResearch/Hermes)** ⭐
**Digabungkan dengan [Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI) | [AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem) | [Vibe-Trading](https://github.com/mulkymalikuldhrs/Vibe-Trading) | [AutoHedge](https://github.com/mulkymalikuldhrs/AutoHedge)**

<br/>

<em>"Bukan sekadar asisten. Ini adalah sistem trading otonom yang menjaga arah, kualitas, dan efisiensi modal."</em>

</div>

---

## Daftar Isi

- [Ringkasan](#ringkasan)
- [Asal & Garis Fork](#asal--garis-fork)
- [Arsitektur: 21 Agent, 5 Lapisan](#arsitektur-21-agent-5-lapisan)
- [Arsitektur Risiko (Penjaga Konstitusional)](#arsitektur-risiko-penjaga-konstitusional)
- [Infrastruktur Auto-Restart](#infrastruktur-auto-restart)
- [Mulai Cepat](#mulai-cepat)
- [Perintah](#perintah)
- [Sistem Tool](#sistem-tool)
- [Konfigurasi](#konfigurasi)
- [Tahap Deployment](#tahap-deployment)
- [Struktur Proyek](#struktur-proyek)
- [Riwayat Versi](#riwayat-versi)
- [Peta Jalan](#peta-jalan)
- [Kontribusi](#kontribusi)
- [Kontak](#kontak)
- [Lisensi](#lisensi)

---

## Ringkasan

<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=18&duration=4000&pause=1000&color=00FF88&center=true&vCenter=true&repeat=true&width=700&height=40&lines=Sistem+Trading+Otonom+Grade-Jarvis;Siap+Produksi+untuk+SaaS+%2B+Lokal" alt="Ketik" />
</div>

Hermes Quant Operating System adalah **infrastruktur trading dan riset otonom multi-agent tingkat produksi** yang dirancang untuk pertumbuhan modal yang konsisten dengan pelestarian risiko absolut. Sistem ini beroperasi berdasarkan prinsip bahwa keputusan trading harus **deterministik, berbasis data, dan tunduk pada batasan risiko yang tidak bisa di-override oleh agent manapun** — termasuk LLM itu sendiri.

Arsitektur ini menyintesis pola terkuat dari empat repositori referensi ke dalam sistem trading terpadu, dibangun di atas framework Nous Research Hermes Agent:

| Repositori Sumber | Kontribusi | Versi |
|---|---|---|
| **[NousResearch/Hermes](https://github.com/NousResearch/Hermes)** ⭐ | Framework agent dasar, orkestrasi tool, loop percakapan | upstream |
| **[Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)** | Deterministic Agent Execution, Pressure Normalization, Market Regime Engine, Darwinian Strategy Evolution, 10 tool terintegrasi | v15.2.0 |
| **[AI-MultiColony-Ecosystem](https://github.com/mulkymalikuldhrs/AI-MultiColony-Ecosystem)** | Unified Agent Registry, manajemen lifecycle multi-agent, koordinasi koloni | v8.0.0 |
| **[Vibe-Trading](https://github.com/mulkymalikuldhrs/Vibe-Trading)** | 450+ alpha quant siap pakai, penerapan alpha purity, analisis faktor | v0.1.8 |
| **[AutoHedge](https://github.com/mulkymalikuldhrs/AutoHedge)** | Arsitektur swarm pipeline (Director → Quant → Risk → Execution), integrasi venue-specific | terbaru |

### Kemampuan Utama

- **21 Agent Spesialis** dalam 5 lapisan arsitektural (Data → Analisis → Keputusan → Eksekusi → Pembelajaran)
- **Penjaga Risiko Konstitusional** dengan batasan hardcoded yang tidak bisa di-override oleh agent manapun — termasuk LLM
- **Infrastruktur Auto-Restart 3 Lapisan** meningkatkan keandalan sistem (Watchdog + Keeper + On-Boot)
- **Multi-Provider LLM** dengan failover otomatis (NVIDIA Nemotron 70B → Groq Llama → OpenCode)
- **Persistensi SQLite** untuk state trading, PnL, event kill switch, dan lifecycle strategi
- **Antarmuka Telegram Bot** untuk perintah real-time, sinyal trading, dan alert sistem
- **Cross-Platform** deployment: Android (Termux), Linux (systemd), VPS, atau mesin lokal
- **Jejak Audit Lengkap** dari data sensor hingga keputusan trading akhir

---

## Asal & Garis Fork

```
[NousResearch/Hermes](https://github.com/NousResearch/Hermes) (Hermes Model & Agent Asli)
        │
        │  Fork & Adaptasi
        ▼
┌───────────────────────────────────────────────────┐
│        HERMES QUANT OPERATING SYSTEM               │
│        (HermesQuantOS)                             │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │  Nous Research Hermes (Framework Dasar)     │  │
│  │  - Arsitektur loop agent                    │  │
│  │  - Sistem orkestrasi tool                   │  │
│  │  - Manajemen percakapan                     │  │
│  └─────────────────────────────────────────────┘  │
│        │          │          │          │          │
│        ▼          ▼          ▼          ▼          │
│  ┌──────────┐┌──────────┐┌──────────┐┌────────┐  │
│  │Quant-    ││AI-Multi  ││Vibe-     ││Auto-   │  │
│  │Nanggroe  ││Colony-   ││Trading   ││Hedge   │  │
│  │-AI       ││Ecosystem ││          ││        │  │
│  │          ││          ││          ││        │  │
│  │Pressure  ││Agent     ││Alpha Zoo ││Swarm   │  │
│  │Engine    ││Registry  ││(450+     ││Pipeline│  │
│  │Decision  ││Lifecycle ││alphas)   ││Director│  │
│  │Engine    ││Colony    ││Factor    ││Quant   │  │
│  │Market    ││Coord     ││Analysis  ││Risk    │  │
│  │Regime    ││          ││Backtest  ││Exec    │  │
│  │News      ││          ││          ││        │  │
│  │Sentinel  ││          ││          ││        │  │
│  │Strategy  ││          ││          ││        │  │
│  │Lifecycle ││          ││          ││        │  │
│  │Math      ││          ││          ││        │  │
│  │SMC+      ││          ││          ││        │  │
│  │Backtest  ││          ││          ││        │  │
│  │Audit     ││          ││          ││        │  │
│  └──────────┘└──────────┘└──────────┘└────────┘  │
│                                                    │
│  + AGENTS.md Framework Konstitusional              │
│  + Infrastruktur Auto-Restart 3 Lapisan            │
│  + Persistensi SQLite & SharedState                │
│  + Failover Multi-Provider LLM                     │
└───────────────────────────────────────────────────┘
```

---

## Arsitektur: 21 Agent, 5 Lapisan

<div align="center">

| Lapisan | Agent | Tujuan |
|:---:|:---:|:---:|
| **L1** Data | Market Data, Chart Vision | Ingesti data & analisis visual |
| **L2** Analisis | Technical, Macro/Sentiment, SMC Enhanced, News Sentinel, Market State | Analisis pasar & deteksi regime |
| **L3** Keputusan | Strategy, Risk Officer (VETO), Portfolio, Decision Engine, Pressure Engine, Strategy Lifecycle | Sintesis keputusan & gate risiko |
| **L4** Eksekusi | Execution, Kill Switch, Auto-Switch Engine | Eksekusi trading & kontrol darurat |
| **L5** Pembelajaran | Journal, Auditor, Research, Audit Logger, Backtest, Math Engine | Self-improvement & validasi |

</div>

### Pipeline Aliran Data

```
Market Data (L1)  ──→  Analisis (L2)  ──→  Pressure Normalization  ──→  Keputusan (L3)
                                                                          │
                                                                     Risk Officer
                                                                   9-Checkpoint Gate
                                                                          │
                                                                VETO → DITOLAK (tidak bisa di-override)
                                                                APPROVE → Eksekusi (L4)
                                                                          │
                                                                     Pembelajaran (L5)
                                                                          │
                                                                Loop Self-Improvement
```

---

## Arsitektur Risiko (Penjaga Konstitusional)

<div align="center">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=16&duration=3000&pause=2000&color=FF4444&center=true&vCenter=true&repeat=true&width=600&height=35&lines=0.5%25+per+trade+%7C+1%25+harian+%7C+3%25+mingguan;HARDCODED+%E2%80%94+TIDAK+BISA+DI-OVERRIDE" alt="Aturan Risiko" />
</div>

Sistem risiko **secara arsitektural independen** dari lapisan penalaran LLM. Keputusan risiko dibuat oleh **kode Python deterministik dengan konstanta hardcoded**, bukan oleh LLM. Ini mencegah segala bentuk "menalar di sekitar" aturan keamanan.

### Aturan Risiko (Konstanta Immutable)

```python
RISK_MAX_PER_TRADE = 0.005     # 0.5% — TIDAK BISA DI-OVERRIDE
RISK_DAILY_MAX     = 0.01     # 1.0% — TIDAK BISA DI-OVERRIDE
RISK_WEEKLY_MAX    = 0.03     # 3.0% — TIDAK BISA DI-OVERRIDE
```

Ini adalah konstanta level modul Python. **Tidak** dimuat dari file konfigurasi, **tidak** disimpan dalam environment variable, dan **tidak** dilewatkan sebagai parameter fungsi. Untuk mengubahnya perlu mengedit kode sumber secara langsung, yang akan tertangkap oleh PR review.

### Risk Officer 9-Checkpoint Gate

Setiap trade harus melewati semua 9 checkpoint. Risk Officer memiliki **FULL VETO** — jika checkpoint apapun gagal, trade ditolak dan **tidak ada agent yang bisa meng-override keputusan ini**.

| # | Checkpoint | Aturan |
|---|---|---|
| 1 | Saldo Akun | Saldo mencukupi untuk posisi |
| 2 | Batas Loss Harian | PnL harian dalam 1% |
| 3 | Batas Loss Mingguan | PnL mingguan dalam 3% |
| 4 | Ukuran Posisi | Risiko per trade dalam 0.5% |
| 5 | Rasio Risk:Reward | Minimum 1:2 |
| 6 | Stop Loss Ada | Wajib, tanpa pengecualian |
| 7 | Skor Confluence | Minimum 3/5 |
| 8 | Regime Pasar | Kompatibel dengan regime saat ini |
| 9 | Cek Korelasi | Korelasi posisi aktif < 0.70 (direncanakan) |

### Kill Switch

- Auto-aktif saat batas harian/mingguan terlampaui
- Reset manual hanya setelah review
- Tidak bisa di-override oleh agent manapun, termasuk owner

---

## Infrastruktur Auto-Restart

```
┌─────────────────────────────────────────┐
│  LAPISAN 3: ON-BOOT                     │
│  Termux:Boot / systemd / cron @reboot   │
│  → Menjalankan hermes.sh start on boot  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  LAPISAN 2: KEEPER (Cron, 1-menit)      │
│  Health check → Restart jika keduanya   │
│  tidak aktif                            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  LAPISAN 1: WATCHDOG (10-detik)         │
│  Monitor → Restart dengan exp. backoff  │
│  5s → 10s → 20s → 40s → 80s → 120s    │
│  Crash loop: max 10/jam → cooldown 5m   │
│  Alert Telegram di setiap event         │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  HERMES QUANT OS (Proses Utama)         │
│  21 Tools | Multi-Provider LLM | SQLite │
└─────────────────────────────────────────┘
```

---

## Mulai Cepat

### Android (Termux)

```bash
chmod +x scripts/install_termux.sh
./scripts/install_termux.sh
```

### Server Linux

```bash
chmod +x scripts/install_server.sh
sudo ./scripts/install_server.sh
```

### Mulai Manual

```bash
# Clone repositori
git clone https://github.com/mulkymalikuldhrs/HermesQuantOS.git
cd HermesQuantOS

# Install dependensi
pip install -r requirements.txt

# Konfigurasi environment
cp config/.env.example config/.env
# Edit config/.env dengan API keys Anda

# Mulai dengan watchdog (auto-restart)
bash hermes.sh start
```

---

## Perintah

```bash
bash hermes.sh start      # Mulai dengan watchdog (auto-restart)
bash hermes.sh stop       # Hentikan semua secara graceful
bash hermes.sh restart    # Restart Hermes + Watchdog
bash hermes.sh status     # Kesehatan sistem & status PnL
bash hermes.sh logs       # Tail log terbaru
bash hermes.sh health     # Health check detail
bash hermes.sh install    # Install on-boot + auto-restart
```

### Perintah Telegram Bot

| Perintah | Deskripsi |
|---|---|
| `/start` | Pesan selamat datang & overview sistem |
| `/status` | Kesehatan sistem, uptime, PnL |
| `/market [SIMBOL]` | Data OHLCV (XAUUSD, EURUSD, dll.) |
| `/analyze [SIMBOL]` | Analisis Teknikal SMC |
| `/risk` | Status Risk Officer |
| `/strategy [SIMBOL]` | Analisis 3-skenario |
| `/journal` | Statistik jurnal trading |
| `/kill` | Status kill switch |
| `/pnl` | Laporan PnL |
| `/help` | Menu bantuan lengkap |

---

## Sistem Tool

### L1: Lapisan Data

| Tool | File | Deskripsi |
|---|---|---|
| `market_data` | `src/tools/market_data_tool.py` | Data OHLCV via yfinance/MT5/OANDA/Binance, kalender ekonomi |
| `chart_vision` | `src/tools/chart_vision_tool.py` | Analisis gambar chart via vision LLM |

### L2: Lapisan Analisis

| Tool | File | Deskripsi |
|---|---|---|
| `technical_analysis` | `src/tools/technical_analysis_tool.py` | Deteksi struktur SMC (BOS/CHoCH/OB/FVG/Sweeps) |
| `macro_sentiment` | `src/tools/macro_sentiment_tool.py` | Deteksi regime risk-on/off, analisis sentimen |
| `smc_enhanced` | `src/tools/smc_agent_enhanced.py` | SMC Enhanced dengan Order Blocks, FVG, Liquidity Sweeps |
| `news_sentinel` | `src/tools/news_sentinel.py` | Skor dampak makro dengan peluruhan waktu logaritmik |
| `market_state` | `src/tools/market_state_engine.py` | Mesin Regime Pasar (TRENDING/RANGE/RISK_OFF/PANIC/NO_TRADE) |

### L3: Lapisan Keputusan

| Tool | File | Deskripsi |
|---|---|---|
| `strategy` | `src/tools/strategy_tool.py` | Generator 3-skenario (Bullish/Bearish/Neutral), confluence scoring |
| `risk_officer` | `src/tools/risk_officer_tool.py` | FULL VETO, 9 checkpoint, lot sizing dengan batasan hardcoded |
| `portfolio` | `src/tools/portfolio_tool.py` | Penilaian portofolio, saran alokasi |
| `decision_engine` | `src/tools/decision_engine.py` | Decision Synthesis Engine (Entry/SL/TP1-TP3) |
| `pressure_engine` | `src/tools/pressure_engine.py` | Normalisasi tekanan BUY/SELL (0.0-1.0) |
| `strategy_lifecycle` | `src/tools/strategy_lifecycle.py` | Evolusi Darwinian: auto-KILL strategi dengan ekspektasi negatif |

### L4: Lapisan Eksekusi

| Tool | File | Deskripsi |
|---|---|---|
| `execution` | `src/tools/execution_tool.py` | Eksekusi Paper/MT5/OANDA/Binance dengan gate persetujuan risiko |
| `kill_switch` | `src/tools/kill_switch_tool.py` | Henti darurat, monitoring auto-trigger, reset manual |
| `autoswitch` | `src/tools/autoswitch_engine.py` | Failover provider LLM tanpa gangguan (NVIDIA → Groq → OpenCode) |

### L5: Lapisan Pembelajaran

| Tool | File | Deskripsi |
|---|---|---|
| `journal` | `src/tools/journal_tool.py` | Pencatatan trade, kalkulasi PnL, statistik performa |
| `auditor_research` | `src/tools/auditor_research_tool.py` | Audit trade (rencana vs eksekusi), deteksi edge decay |
| `audit` | `src/tools/audit_logger.py` | Jejak lengkap dari sensor hingga keputusan akhir |
| `backtest` | `src/tools/backtest_engine.py` | Simulasi Spread Dinamis, Slippage Variabel, Latensi |
| `math_engine` | `src/tools/math_engine.py` | Analisis statistik, kalkulasi probabilitas |

---

## Konfigurasi

Semua konfigurasi dikelola melalui `config/.env` (salin dari `config/.env.example`):

```env
# Provider LLM
NVIDIA_API_KEY=nvapi-xxxxx
GROQ_API_KEY=gsk_xxxxx
OPENCODE_API_KEY_1=xxxxx

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-xxxxx
TELEGRAM_CHAT_ID=123456789

# Sistem
MODEL_NAME=meta/llama-3.1-nemotron-70b-instruct
LOG_DIR=./logs
DATA_DIR=./data
```

> **PENTING**: Jangan pernah commit `config/.env` ke version control. Semua API key harus di-rotasi jika terekspos.

---

## Tahap Deployment

Sistem mengikuti **pipeline deployment 5 tahap**. Kemajuan tahap memerlukan persetujuan eksplisit user dengan metrik performa yang terdokumentasi.

| Tahap | Nama | Deskripsi | Status |
|---|---|---|---|
| 1 | Research Lab | Paper trading saja, tanpa uang asli | **SAAT INI** |
| 2 | Paper Trading | Eksekusi simulasi dengan data pasar nyata | Direncanakan |
| 3 | Micro Live | Uang asli, maksimum 0.01 lot | Direncanakan |
| 4 | Semi-Otonom | Memerlukan konfirmasi user untuk trade nyata | Direncanakan |
| 5 | Otonom Penuh | Agent mengeksekusi secara mandiri (memerlukan edge yang terbukti) | Direncanakan |

---

## Struktur Proyek

```
HermesQuantOS/
├── src/
│   ├── hermes_quant.py              # Controller agent utama
│   ├── watchdog.py                  # Daemon watchdog (monitor 10s)
│   └── tools/
│       ├── __init__.py
│       ├── shared_state.py          # Singleton SharedState + SQLite
│       ├── market_data_tool.py      # L1: Data OHLCV
│       ├── chart_vision_tool.py     # L1: Analisis gambar chart
│       ├── technical_analysis_tool.py # L2: Struktur SMC
│       ├── macro_sentiment_tool.py  # L2: Regime risiko
│       ├── smc_agent_enhanced.py    # L2: SMC Enhanced
│       ├── news_sentinel.py         # L2: Dampak berita
│       ├── market_state_engine.py   # L2: Regime pasar
│       ├── strategy_tool.py         # L3: 3-skenario
│       ├── risk_officer_tool.py     # L3: FULL VETO
│       ├── portfolio_tool.py        # L3: Portofolio
│       ├── decision_engine.py       # L3: Sintesis keputusan
│       ├── pressure_engine.py       # L3: Normalisasi tekanan
│       ├── strategy_lifecycle.py    # L3: Evolusi Darwinian
│       ├── execution_tool.py        # L4: Eksekusi trade
│       ├── kill_switch_tool.py      # L4: Henti darurat
│       ├── autoswitch_engine.py     # L4: Failover provider
│       ├── journal_tool.py          # L5: Jurnal trading
│       ├── auditor_research_tool.py # L5: Audit post-trade
│       ├── audit_logger.py          # L5: Jejak audit lengkap
│       ├── backtest_engine.py       # L5: Backtesting
│       └── math_engine.py           # L5: Analisis statistik
├── scripts/
│   ├── keeper.py                    # Monitor health cron
│   ├── install_termux.sh            # Installer Android
│   └── install_server.sh            # Installer Linux
├── config/
│   ├── .env.example                 # Template environment
│   ├── hermes-quant.yaml            # Konfigurasi sistem
│   └── system_prompt.py             # Prompt sistem trading
├── schemas/
│   └── trading_journal.sql          # Skema SQL 7-tabel
├── hermes.sh                        # Script kontrol
├── AGENTS.md                        # Konstitusi operasional
├── CHANGELOG.md                     # Riwayat versi
├── ARCHITECTURE.md                  # Arsitektur sistem
├── STRUCTURE.md                     # Struktur proyek
├── UPGRADE_PLAN.md                  # Peta jalan upgrade otonom
├── PR.md                            # Template PR & proposal
├── ALL.md                           # Referensi gabungan
├── requirements.txt                 # Dependensi Python
└── .gitignore                       # Aturan git ignore
```

---

## Riwayat Versi

| Versi | Tanggal | Nama Kode | Fitur Utama |
|---|---|---|---|
| 1.0.0 | 2026-05-20 | Genesis | 11 trading tools, adaptasi Hermes Agent |
| 1.1.0 | 2026-05-21 | Polyglot | Dukungan LLM multi-provider (NVIDIA + Groq + OpenCode) |
| 2.0.0 | 2026-05-22 | Immortal | Infrastruktur auto-restart & on-boot (3 lapisan) |
| 3.0.0 | 2026-05-23 | Constitution | Framework konstitusional AGENTS.md, aturan risiko hardcoded |
| 3.1.0 | 2026-05-24 | Synthesis | Integrasi 10-tool Quant-Nanggroe-AI (total 21 agent) |
| 3.2.0 | 2026-05-25 | Chronicle | Suite dokumentasi & perencanaan upgrade otonom |
| **4.0.0** | **2026-05-25** | **Production** | **SharedState, sinkronisasi PnL, persistensi SQLite, Telegram HTML, routing 21-tool** |

Lihat [CHANGELOG.md](./CHANGELOG.md) untuk detail lengkap.

---

## Peta Jalan

| Fase | Fitur | Status |
|---|---|---|
| PR-001 | Loop Trading Otonom | Diusulkan |
| PR-002 | Monitor Korelasi Cross-Asset | Diusulkan |
| PR-003 | Evolusi Strategi Darwinian | Diusulkan |
| PR-004 | Integrasi Alpha Zoo (450+ alphas dari Vibe-Trading) | Diusulkan |
| PR-005 | AutoHedge Swarm Pipeline | Diusulkan |
| Masa Depan | Deployment Docker + Kubernetes | Direncanakan |
| Masa Depan | Platform SaaS Multi-Tenant | Direncanakan |
| Masa Depan | Web Dashboard (React/Next.js) | Direncanakan |
| Masa Depan | REST API Gateway | Direncanakan |
| Masa Depan | Live Trading Multi-Exchange | Direncanakan |

Lihat [UPGRADE_PLAN.md](./UPGRADE_PLAN.md) untuk peta jalan upgrade otonom 15-18 bulan lengkap.

---

## Kontribusi

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=20&duration=3000&pause=1500&color=00FF88&center=true&vCenter=true&repeat=true&width=500&height=35&lines=Kontributor+Diterima!;Bergabung+Revolusi+Trading+Otonom" alt="Kontributor Diterima" />

</div>

Kami menerima kontribusi dari developer, analis kuantitatif, insinyur risiko, dan peneliti AI! HermesQuantOS dibangun berdasarkan prinsip bahwa **kolaborasi menghasilkan sistem yang lebih unggul**.

### Cara Berkontribusi

1. **Fork** repositori ini
2. **Buat** branch fitur (`git checkout -b feature/fitur-baru`)
3. **Commit** perubahan Anda (`git commit -m 'Tambah fitur baru'`)
4. **Push** ke branch (`git push origin feature/fitur-baru`)
5. **Buka** Pull Request

### Area Kontribusi

- **Trading Tools**: Tool analisis baru, indikator, atau adaptor eksekusi
- **Rekayasa Risiko**: Peningkatan cek risiko, monitor korelasi, optimasi portofolio
- **Infrastruktur**: Konfigurasi Docker, pipeline CI/CD, dashboard monitoring
- **AI/ML**: Evolusi strategi, riset alpha, peningkatan backtesting
- **Dokumentasi**: Terjemahan, tutorial, diagram arsitektur
- **Testing**: Unit test, integration test, stress test

### Pedoman

- Semua trading tools harus melewati Risk Officer — tanpa bypass
- Aturan risiko **HARDCODED** dan **TIDAK BISA DINEGOSIASIKAN** — jangan kirim PR yang melemahkannya
- Ikuti struktur kode dan konvensi penamaan yang ada
- Tambahkan test untuk fitur baru
- Perbarui dokumentasi (CHANGELOG.md, STRUCTURE.md) dengan perubahan Anda
- Satu PR per fitur — tetap fokus dan dapat di-review

---

## Kontak

<div align="center">

### Mulky Malikul Dhaher

[![Email](https://img.shields.io/badge/Email-mulkymalikuldhaher@email.com-FF6B35?style=for-the-badge&logo=gmail&logoColor=white&labelColor=0A0A0A)](mailto:mulkymalikuldhaher@email.com)
[![GitHub](https://img.shields.io/badge/GitHub-mulkymalikuldhrs-00D4FF?style=for-the-badge&logo=github&logoColor=white&labelColor=0A0A0A)](https://github.com/mulkymalikuldhrs)

<br/>

**Repositori Proyek**: [github.com/mulkymalikuldhrs/HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS)

</div>

---

## Lisensi

Proyek ini dilisensikan di bawah MIT License — lihat file [LICENSE](./LICENSE) untuk detail.

Hermes Agent asli oleh Nous Research juga dilisensikan di bawah MIT.

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1A1A2E,50:16213E,100:0F3460&height=80&section=footer&text=&fontSize=0&animation=fadeIn" width="100%" alt="Footer Wave" />

**HERMES QUANT OPERATING SYSTEM**

*Otonom. Deterministik. Risk-First.*

<br/>

<a href="https://github.com/NousResearch/Hermes"><img src="https://img.shields.io/badge/Fork_dari-NousResearch/Hermes-FF6B35?style=flat-square&logo=github&logoColor=white" /></a>
<img src="https://img.shields.io/badge/Dibangun_dengan-Python-3776AB?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Digerakkan_oleh-NVIDIA_AI-76B900?style=flat-square&logo=nvidia&logoColor=white" />
<img src="https://img.shields.io/badge/LLM-Groq-FF6B35?style=flat-square&logo=groq&logoColor=white" />

</div>
