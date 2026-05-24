<!-- 🦅 QUANT NANGGROE AI — README Bahasa Indonesia -->
<!-- Language: Bahasa Indonesia -->

<a href="https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI">
  <img align="center" src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=36&duration=3000&pause=1500&color=00D4AA&center=true&vCenter=true&multiline=true&repeat=true&width=800&height=120&lines=QUANT+NANGGROE+AI;OS+Intelijen+Keputusan+Multi-Agent" alt="Typing SVG" />
</a>

<div align="center">

[![Versi](https://img.shields.io/badge/Versi-15.2.0-gold?style=for-the-badge&logo=semver&logoColor=white)](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Lisensi](https://img.shields.io/badge/Lisensi-MIT-green?style=for-the-badge&logo=open-source-initiative&logoColor=white)](./LICENSE)
[![Status](https://img.shields.io/badge/Status-Operasional_Penuh-22C55E?style=for-the-badge&logo=checkmarx&logoColor=white)](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)

</div>

<div align="center">

**Bahasa / Language / 语言:**
[![English](https://img.shields.io/badge/EN-English-blue?style=flat-square)](./README.md)
[![Bahasa Indonesia](https://img.shields.io/badge/ID-Bahasa_Indonesia-red?style=flat-square)](./README_id.md)
[![中文](https://img.shields.io/badge/CN-中文-yellow?style=flat-square)](./README_zh.md)

</div>

---

## 🏛️ Ringkasan

**Quant Nanggroe AI** adalah **Sistem Operasi Intelijen Keputusan Multi-Agent** tingkat lanjut yang dirancang untuk riset kuantitatif dan perdagangan sistematis di pasar keuangan. Dibangun berdasarkan prinsip **Intelijen Keputusan Deterministik**, platform ini secara fundamental menolak narasi AI subjektif dan bias psikologis, dan menggantinya dengan penalaran yang dibatasi secara matematis atas data numerik mentah. Sistem ini memperlakukan Large Language Model bukan sebagai penasihat, melainkan sebagai **Mesin Penalaran Logis** — yang masing-masing beroperasi di bawah kontrak ketat yang melarang opini subjektif, mewajibkan grounding data, dan mensyaratkan keluaran berbasis tekanan numeris alih-alih sinyal perdagangan langsung.

Pada intinya, Quant Nanggroe AI mengimplementasikan **Stack Eksekusi 5 Lapis** yang memproses data pasar dari umpan L1/L2 mentah melalui deteksi rezim, analisis sensor multi-agent, normalisasi tekanan, dan akhirnya sintesis keputusan dengan penegakan risiko. Arsitektur ini terinspirasi dari meja perdagangan kuantitatif institusional, di mana setiap keputusan harus dapat dilacak, diaudit, dan dapat dipertahankan. Sistem ini menggunakan **Siklus Hidup Strategi Darwinian** yang secara otomatis membunuh strategi yang berkinerja buruk, **Mesin Realitas Eksekusi** yang memperhitungkan slippage, spread, dan latensi dalam backtesting, serta **Konstitusi Penjaga Risiko** yang bertindak sebagai laporan independen dari aturan keselamatan hard-code yang kebal terhadap penalaran AI.

Frontend adalah antarmuka bergaya desktop-OS yang dibangun dengan React 19 dan TypeScript, menampilkan jendela yang dapat didrag, dock bergaya macOS, pusat perintah bertenaga AI (OmniBar), dan visualisasi real-time dari swarm multi-agent. Dirancang sebagai stasiun kerja riset dan dukungan keputusan yang lengkap — bukan sekadar dashboard, melainkan lingkungan operasi untuk intelijen kuantitatif.

> 🔗 **Bagian dari [HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) Proyek Terpadu** — Ekosistem intelijen kuantitatif full-stack.

---

## 🏗️ Arsitektur

Quant Nanggroe AI dibangun di atas **Stack Eksekusi Deterministik 5 Lapis**, di mana setiap lapisan bertindak sebagai filter ketat yang meneruskan data atau memblokirnya sepenuhnya. Tidak ada lapisan yang dapat dilewati, dan tidak ada agent yang dapat mengabaikan batasan yang diberlakukan oleh lapisan di atasnya. Desain ini memastikan bahwa setiap keputusan perdagangan adalah hasil dari pipeline yang sepenuhnya dapat diaudit dan deterministik — dari ingestion data pasar mentah hingga parameter eksekusi akhir dengan persetujuan risiko.

### Lapisan 0: Grounding Neural Kontekstual (Fondasi Data)
Landasan seluruh sistem. Lapisan ini memanen data pasar L1/L2 real-time dari beberapa penyedia — Binance, CoinCap, AlphaVantage, Polygon, dan Finnhub — menggunakan mesin **AutoSwitch** untuk failover otomatis dan pemantauan kesehatan penyedia. Setiap data yang masuk ke sistem diberi tag metadata termasuk sumber, skor kepercayaan (0.0–1.0), estimasi latensi, frekuensi pembaruan, dan tipe domain. Metadata ini mengalir ke hilir, memungkinkan setiap agent dan mesin menimbang kepercayaannya berdasarkan kualitas data. **MarketService** mengorkestrasi semua akses data, menyediakan API terpadu untuk umpan harga, data candle, berita, dan indikator teknikal.

### Lapisan 1: Mesin Rezim Pasar (Penjaga Gerbang)
**MarketStateEngine** berada di atas semua agent dan berfungsi sebagai penjaga gerbang sistem. Mesin ini menentukan kondisi pasar global — `TRENDING`, `RANGE`, `MEAN_REVERT`, `RISK_OFF`, `PANIC`, atau `NO_TRADE` — menggunakan kombinasi kekuatan tren ADX, ekstrem RSI, dan deteksi perubahan harga cepat. Jika rezim adalah `NO_TRADE` atau `PANIC`, semua agent hilir dipaksa ke mode idle, melindungi modal selama kondisi yang tidak sesuai. Ini adalah batasan keras yang tidak dapat diganti oleh agent atau penalaran LLM mana pun.

### Lapisan 2: Sensor Multi-Agent (Mata)
Empat agent khusus beroperasi secara paralel sebagai sensor numeris, masing-masing menghasilkan tipe keluaran terstruktur alih-alih analisis subjektif:
- **QuantScanner** (`quant_scanner.ts`) — Momentum teknikal, kekuatan tren ADX, ekspansi volatilitas, dan status struktur (BULL/BEAR/NEUTRAL).
- **SMCAgent** (`smc_agent.ts`) — Smart Money Concepts: sapuan likuiditas, kekuatan displacement, dan validitas Point of Interest.
- **NewsSentinel** (`news_sentinel.ts`) — Klasifikasi peristiwa makroekonomi (MACRO/SCHEDULED/SHOCK/NOISE) dengan peluruhan waktu logaritmik dan penilaian ketidakpastian arah.
- **FlowAgent** (`flow_agent.ts`) — Pelacakan arus ikan paus institusional, bias posisi COT (LONG/SHORT/NEUTRAL), dan pengukuran ketidakseimbangan arus.

### Lapisan 3: Mesin Normalisasi Tekanan (Kompiler)
**PressureNormalizationEngine** mengagregasi keluaran sensor mentah dari keempat agent dan mengompilasinya menjadi dua vektor utama: `BUY_PRESSURE` (0.0–1.0) dan `SELL_PRESSURE` (0.0–1.0), bersama dengan klasifikasi risiko volatilitas, kondisi likuiditas, dan skor kepercayaan keseluruhan. Setiap sensor berkontribusi porsi berbobot pada perhitungan tekanan, dengan bobot spesifik yang diturunkan dari spesifikasi Blueprint Final. Lapisan ini menghilangkan masalah sinyal agent yang saling bertentangan dengan mengurangi semuanya menjadi satu bidang tekanan yang dinormalisasi.

### Lapisan 4: Mesin Sintesis Keputusan (Hakim)
**DecisionSynthesisEngine** adalah otoritas akhir. Mesin ini menggunakan **Tabel Keputusan** (aturan yang dapat dibaca mesin) untuk mengevaluasi apakah kondisi tekanan, rezim, volatilitas, dan tingkat kepercayaan saat ini memenuhi kriteria untuk masuk. Jika konfluensi tercapai, **EntryRiskEngine** menghitung parameter masuk geometris — harga masuk, stop loss struktural (berbasis invalidasi, bukan persentase), dan take profit berjenjang (TP1: likuiditas terdekat, TP2: ekstensi volatilitas, TP3: ekstensi volatilitas x2). Persetujuan risiko diverifikasi secara independen oleh modul **RiskManagement**, yang menegakkan Konstitusi Perdagangan.

---

## ⚡ Fitur Utama

### 🧠 Swarm Multi-Agent Deterministik
Sistem mengkoordinasikan 5 agent swarm default — Alpha Prime (manajer portofolio), Quant-Scanner (analis teknikal), News-Sentinel (makro/sentimen), Risk-Guardian (kontrol risiko), dan Strategy-Weaver (pengembang algoritma) — masing-masing dengan cakupan penalaran yang dibatasi, domain input eksplisit, dan batasan keras yang mencegah analisis subjektif atau keluaran yang dihalusinasi. Agent berkomunikasi melalui kontrak terstruktur, bukan teks bentuk bebas.

### 🛡️ Konstitusi Penjaga Risiko
Manajemen risiko di-hard-code dan independen dari logika AI. Konstitusi Perdagangan menegakkan: batas drawdown harian maksimum dengan kill-switch otomatis, korelasi maksimum antara posisi aktif (ambang 0.70), eksposur maksimum per aset, dan stop loss berbasis invalidasi struktural yang diutamakan di atas rasio risiko-imbalan. Tidak ada agent yang dapat "menalar di sekitar" aturan ini.

### 🧬 Siklus Hidup Strategi Darwinian
Setiap strategi dipantau untuk signifikansi statistik. Jika **ekspektansi** strategi menjadi negatif pada ukuran sampel yang memadai (minimum 20 perdagangan), strategi tersebut secara otomatis ditandai sebagai `KILLED` dan sumber daya dialihkan ke varian yang berkinerja lebih tinggi. Strategi dengan drawdown melebihi 15% ditempatkan dalam status `HIBERNATING`. Mekanisme seleksi alami ini memastikan sistem terus berevolusi menuju profitabilitas.

### 📊 Mesin Realitas Eksekusi
Backtesting bukan fantasi. **BacktestEngine** memperhitungkan spread dinamis (disesuaikan volatilitas), slippage acak, probabilitas pengisian parsial (2–15% tergantung volatilitas), simulasi penolakan order, dan latensi realistis (100–500ms). Ini memastikan bahwa kinerja backtest mencerminkan kondisi perdagangan dunia nyata daripada asumsi yang diidealkan.

### 🔍 Jejak Audit Penuh
**AuditLogger** mencatat setiap peristiwa di semua lapisan — Pasar, Sensor, Tekanan, Keputusan, Risiko, dan Eksekusi — dengan stempel waktu, payload data terstruktur, dan tingkat keparahan. Setiap keputusan yang dibuat sistem sepenuhnya dapat dilacak dan dapat direproduksi, memenuhi persyaratan kepatuhan institusional.

### 🔄 Failover API AutoSwitch
Mesin **AutoSwitch** menyediakan failover penyedia otomatis dengan logika coba ulang exponential backoff, prioritisasi penyedia berbasis kesehatan, mekanisme cooldown untuk penyedia yang gagal, dan pelaporan kesehatan real-time. Ini memastikan aliran data yang tidak terputus bahkan ketika penyedia API individu mengalami pemadaman atau batas tarif.

### 📚 Agent Riset Otonom
**ResearchAgent** berjalan terus-menerus pada interval yang dapat dikonfigurasi, memanen intelijen dari 8+ sumber termasuk berita global, snapshot pasar, data geopolitik, sentimen sosial, arus institusional, dan pembaruan ekosistem AI. Semua intelijen yang dipanen disimpan ke Basis Pengetahuan untuk referensi silang dan analisis historis.

### 🧮 Mesin Matematika Tingkat Institusional
**MathEngine** menyediakan rangkaian indikator matematika murni yang komprehensif: RSI, SMA, EMA, MACD, Bollinger Bands, VWAP dengan bands, Volume Profile, Stochastic Oscillator, CCI, ADX, dan ATR. Setiap perhitungan 100% deterministik tanpa keterlibatan AI — menghilangkan risiko halusinasi dari analisis teknikal.

---

## 🖥️ Deskripsi Komponen

| Komponen | File | Deskripsi |
|---|---|---|
| **Launchpad** | `components/Launchpad.tsx` | Peluncur aplikasi bergaya macOS yang menyediakan akses cepat ke semua jendela dan alat sistem. Menampilkan semua aplikasi yang tersedia dalam tata letak grid dengan ikon animasi dan label. |
| **TradingTerminal** | `components/TradingTerminalWindow.tsx` | Terminal perdagangan profesional yang menampilkan candlestick chart real-time powered by Lightweight Charts v4.1, antarmuka penempatan order, dan pelacakan posisi live dengan tampilan equity/margin/PnL. |
| **SwarmGraph** | `components/SwarmConfigModal.tsx` | Panel konfigurasi intelijen swarm untuk mengelola kemampuan agent, menetapkan alat, dan memantau kesehatan serta aktivitas setiap agent dalam swarm. |
| **NexusWindow** | `components/NexusWindow.tsx` | Dashboard visualisasi Quantum Nexus yang menampilkan metrik koherensi sistem, qubit aktif, beban sinaptik, dan status operasional pipeline pemrosesan neural. |
| **MarketWindow** | `components/MarketWindow.tsx` | Dashboard data pasar real-time yang menampilkan ticker harga, perubahan 24 jam, volume, indikator teknikal, dan klasifikasi kondisi pasar untuk aset yang dilacak. |
| **ResearchAgentWindow** | `components/ResearchAgentWindow.tsx` | Konsol intelijen riset yang menampilkan log riset otonom, ringkasan intelijen yang dipanen, dan status pemindaian sumber untuk semua 8+ sumber intelijen. |
| **KnowledgeBaseWindow** | `components/KnowledgeBaseWindow.tsx` | Antarmuka manajemen pengetahuan untuk menelusuri, mencari, dan mengelola item riset, analisis pasar, dan intelijen institusional yang disimpan dalam basis pengetahuan persisten. |
| **BrowserWindow** | `components/BrowserWindow.tsx` | Browser web terintegrasi untuk menavigasi situs berita keuangan, makalah riset, dan sumber data pasar langsung dalam lingkungan Quant Nanggroe OS. |
| **PortfolioWindow** | `components/PortfolioWindow.tsx` | Dashboard manajemen portofolio dengan pelacakan equity real-time, status margin, perhitungan PnL, visualisasi alokasi aset, dan manajemen posisi. |
| **SystemArchitecture** | `components/SystemArchitecture.tsx` | Diagram arsitektur sistem visual yang menampilkan stack eksekusi 5 lapis, aliran data antara mesin, dan jalur komunikasi agent. |
| **AgentHud** | `components/AgentHud.tsx` | Heads-Up Display untuk memantau status agent swarm, termasuk tindakan saat ini, emosi, status berpikir, dan pelacakan URL browser aktif. |
| **ControlCenter** | `components/ControlCenter.tsx` | Panel kontrol sistem dengan matriks keamanan, dashboard penjaga risiko, toggle tema, dan opsi konfigurasi sistem. |
| **OmniBar** | `components/OmniBar.tsx` | Bar perintah universal bergaya Spotlight untuk akses cepat ke fungsi sistem apa pun, perintah pemindaian pasar (`/scan`), dan pencarian bertenaga AI. |
| **Taskbar** | `components/Taskbar.tsx` | Dock bergaya macOS di bagian bawah layar yang menyediakan manajemen jendela, peluncuran aplikasi, dan indikator status sistem. |
| **WindowFrame** | `components/WindowFrame.tsx` | Kontainer jendela yang dapat didrag dan diubah ukurannya dengan bilah judul, tombol minimize/close, manajemen z-index, dan pelacakan fokus untuk pengalaman desktop OS. |

---

## 🚀 Mulai Cepat

### Prasyarat
- **Node.js** >= 18.0.0
- **npm** >= 9.0.0 (atau yarn/pnpm)
- Kunci API (opsional tetapi disarankan):
  - **Google Gemini** — untuk intelijen swarm bertenaga LLM
  - **Finnhub** — untuk data pasar real-time
  - **AlphaVantage** — untuk data teknikal saham/forex

### Instalasi

```bash
# Klon repositori
git clone https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI.git

# Navigasi ke direktori proyek
cd Quant-Nanggroe-AI

# Instal dependensi
npm install

# Mulai server pengembangan
npm run dev
```

### Konfigurasi

1. Jalankan aplikasi dengan `npm run dev`
2. Buka panel **Pengaturan** dari Control Center atau Taskbar
3. Masukkan kunci API Anda di bagian konfigurasi:
   - `Kunci API Google` — Diperlukan untuk swarm agent bertenaga Gemini
   - `Kunci API Finnhub` — Untuk umpan data pasar real-time
   - `Kunci API AlphaVantage` — Untuk indikator teknikal saham
4. Sistem akan secara otomatis menginisialisasi layanan penyimpanan (IndexedDB, BrowserFS, Memory Manager) saat startup
5. **ResearchAgent** akan memulai pemanenan intelijen otonom secara langsung

### Build untuk Produksi

```bash
# Buat build produksi yang dioptimalkan
npm run build

# Pratinjau build produksi secara lokal
npm run preview
```

---

## 📁 Struktur Proyek

```
Quant-Nanggroe-AI/
├── 📄 App.tsx                          # Komponen aplikasi utama dengan manajemen jendela bergaya OS
├── 📄 index.tsx                         # Titik masuk aplikasi
├── 📄 types.ts                          # Definisi tipe inti (MarketState, DecisionSynthesis, AgentContract, dll.)
├── 📄 index.html                        # Titik masuk HTML
├── 📄 vite.config.ts                    # Konfigurasi build Vite
├── 📄 tsconfig.json                     # Konfigurasi TypeScript
├── 📄 package.json                      # Dependensi dan skrip
├── 📄 metadata.json                     # Metadata sistem (versi, deskripsi)
├── 📄 CHANGELOG.md                      # Riwayat versi dan catatan rilis
│
├── 📂 components/                       # Komponen UI React
│   ├── 📄 Launchpad.tsx                 # Peluncur aplikasi
│   ├── 📄 TradingTerminalWindow.tsx     # Terminal perdagangan dengan chart
│   ├── 📄 MarketWindow.tsx              # Dashboard data pasar
│   ├── 📄 PortfolioWindow.tsx           # Manajemen portofolio
│   ├── 📄 ResearchAgentWindow.tsx       # Konsol intelijen riset
│   ├── 📄 KnowledgeBaseWindow.tsx       # Browser basis pengetahuan
│   ├── 📄 BrowserWindow.tsx             # Browser web terintegrasi
│   ├── 📄 NexusWindow.tsx              # Visualisasi Quantum Nexus
│   ├── 📄 SwarmConfigModal.tsx          # Konfigurasi agent swarm
│   ├── 📄 SystemArchitecture.tsx        # Diagram arsitektur
│   ├── 📄 AgentHud.tsx                  # Tampilan HUD agent
│   ├── 📄 ControlCenter.tsx             # Panel kontrol sistem
│   ├── 📄 OmniBar.tsx                   # Bar perintah universal
│   ├── 📄 Taskbar.tsx                   # Dock/taskbar
│   ├── 📄 WindowFrame.tsx              # Kontainer jendela yang dapat didrag
│   ├── 📄 ChatMessage.tsx              # Komponen pesan chat
│   ├── 📄 InputArea.tsx                # Area input pesan
│   ├── 📄 ArtifactWindow.tsx           # Jendela tampilan artefak
│   ├── 📄 Avatar.tsx                   # Komponen avatar pengguna
│   ├── 📄 RealTimeChart.tsx            # Komponen chart real-time
│   ├── 📄 SystemUpdater.tsx            # Pemeriksa pembaruan sistem
│   └── 📄 Icons.tsx                    # Pustaka ikon SVG
│
├── 📂 services/                         # Logika bisnis inti dan mesin
│   ├── 📄 strategy_engine.ts           # Evaluasi strategi (SMC, S/R, Retail TA)
│   ├── 📄 quantum_engine.ts            # Normalisasi tekanan & sintesis keputusan
│   ├── 📄 decision_synthesis_engine.ts  # Tabel keputusan & logika sintesis
│   ├── 📄 pressure_normalization_engine.ts # Kompilasi sensor-ke-tekanan
│   ├── 📄 market_state_engine.ts       # Deteksi rezim pasar (Lapisan 1)
│   ├── 📄 entry_risk_engine.ts         # Geometri masuk & perhitungan risiko
│   ├── 📄 smc_agent.ts                # Sensor Smart Money Concepts
│   ├── 📄 news_sentinel.ts             # Klasifikasi berita & peristiwa makro
│   ├── 📄 flow_agent.ts               # Pelacakan arus institusional
│   ├── 📄 quant_scanner.ts            # Pemindai momentum kuantitatif
│   ├── 📄 math_engine.ts              # Indikator matematika murni
│   ├── 📄 ml_engine.ts                # Utilitas pembelajaran mesin
│   ├── 📄 backtest_engine.ts          # Backtesting dengan realitas eksekusi
│   ├── 📄 strategy_lifecycle.ts        # Manajemen strategi Darwinian
│   ├── 📄 audit_logger.ts             # Sistem jejak audit penuh
│   ├── 📄 autoswitch.ts               # Mesin failover API
│   ├── 📄 research_agent.ts           # Pemanen riset otonom
│   ├── 📄 knowledge_base.ts           # Penyimpanan pengetahuan persisten
│   ├── 📄 browser_core.ts             # Pengontrol navigasi browser
│   ├── 📄 llm_router.ts              # Mesin routing multi-LLM
│   ├── 📄 gemini.ts                   # Integrasi Google Gemini AI
│   ├── 📄 market.ts                   # Layanan data pasar (API terpadu)
│   ├── 📄 risk_management.ts          # Penegakan Penjaga Risiko
│   ├── 📄 correlation_monitor.ts      # Pelacakan korelasi aset
│   ├── 📄 memory_manager.ts           # Manajemen memori sesi
│   ├── 📄 storage_manager.ts          # Orkestrasi penyimpanan hibrida
│   ├── 📄 storage_adapter.ts          # Pola adaptor penyimpanan
│   ├── 📄 file_system.ts             # Sistem file berbasis browser
│   ├── 📄 drive.ts                   # Manajemen drive virtual
│   ├── 📄 adaptive_layout.ts          # Mesin tata letak responsif
│   ├── 📄 evolution_monitor.ts        # Pelacakan evolusi strategi
│   ├── 📄 backup_service.ts           # Backup & pemulihan sistem
│   └── 📄 desktop_intelligence.ts     # Integrasi AI desktop
│
└── 📂 docs/                            # Dokumentasi
    ├── 📄 ARCHITECTURE.md              # Referensi arsitektur sistem
    ├── 📄 BLUEPRINT.md                 # Cetak biru desain
    ├── 📄 BUILD_PLAN.md               # Peta jalan pembangunan
    ├── 📄 EVOLUTION_MANIFEST.md       # Filosofi evolusi strategi
    ├── 📄 SERVICES_GUIDE.md           # Dokumentasi layanan
    ├── 📄 STORAGE.md                  # Arsitektur penyimpanan
    ├── 📄 SYSTEM_AUDIT_LOG.md         # Referensi audit sistem
    └── 📄 USER_GUIDE.md              # Panduan pengguna
```

---

## 🤝 Berkontribusi

Kami menyambut kontributor dari seluruh dunia! Quant Nanggroe AI adalah proyek ambisius yang berada di persimpangan keuangan kuantitatif, kecerdasan buatan, dan rekayasa sistem. Apakah Anda seorang pengembang kuant berpengalaman, spesialis React/TypeScript, peneliti pembelajaran mesin, atau seseorang yang bersemangat membangun sistem perdagangan cerdas — ada tempat untuk Anda di sini.

### Cara Berkontribusi

1. **Fork** repositori di [https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI](https://github.com/mulkymalikuldhrs/Quant-Nanggroe-AI)
2. **Buat** branch fitur: `git checkout -b feature/nama-fitur-anda`
3. **Commit** perubahan Anda dengan pesan yang jelas dan deskriptif
4. **Push** ke fork Anda: `git push origin feature/nama-fitur-anda`
5. **Buka** Pull Request dengan deskripsi detail tentang perubahan Anda

### Area yang Membutuhkan Bantuan

- 🧪 **Pengujian** — Unit test, integration test, dan end-to-end testing untuk semua mesin
- 📊 **Indikator** — Indikator teknikal tambahan untuk MathEngine (Ichimoku, Fibonacci, Elliott Wave)
- 🔌 **Penyedia Data** — Integrasi API baru (Yahoo Finance, CoinGecko, TradingView)
- 🎨 **UI/UX** — Peningkatan komponen, aksesibilitas, responsivitas mobile
- 📖 **Dokumentasi** — Dokumentasi API, tutorial, dan contoh
- 🌐 **Internasionalisasi** — Terjemahan dan dukungan lokalisasi
- 🏗️ **Deployment Cloud** — Konfigurasi Docker, Kubernetes, dan cloud-native

### Pedoman Pengembangan

- Semua kode TypeScript harus lulus pemeriksaan tipe ketat (`strict: true`)
- Ikuti struktur proyek dan konvensi penamaan yang ada
- Setiap layanan baru harus menyertakan logging audit melalui `AuditLogger`
- Semua perhitungan keuangan harus deterministik dan dapat diuji
- Komponen UI harus mendukung tema terang dan gelap

### Kontak

Untuk pertanyaan, saran, atau permintaan kolaborasi, hubungi:

[![Email](https://img.shields.io/badge/Email-mulkymalikuldhaher@email.com-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:mulkymalikuldhaher@email.com)
[![GitHub](https://img.shields.io/badge/GitHub-mulkymalikuldhrs-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/mulkymalikuldhrs)

---

## 🔗 Proyek Terkait

| Proyek | Deskripsi | Tautan |
|---|---|---|
| **HermesQuantOS** | Ekosistem Intelijen Kuantitatif Terpadu — proyek induk yang mengintegrasikan Quant Nanggroe AI dengan layanan backend | [https://github.com/mulkymalikuldhrs/HermesQuantOS](https://github.com/mulkymalikuldhrs/HermesQuantOS) |

---

## 📜 Lisensi

Proyek ini dilisensikan di bawah Lisensi MIT. Lihat file [LICENSE](./LICENSE) untuk detailnya.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0D9488,50:065F46,100:020205&height=120&section=footer" width="100%" />
</p>

<p align="center">
  <strong>&copy; 2026 Quant Nanggroe AI</strong><br/>
  Dibangun dengan 💎 oleh <a href="https://github.com/mulkymalikuldhrs">Mulky Malikul Dhaher</a><br/>
  <em>Menunggu Kontributor dari Seluruh Dunia 🌎</em>
</p>
