# MONEY ESCAPE PLAN — Mulky (29, Aceh) → Exit Indonesia < 3 Bulan

> Target: cari duit yang bisa **dieksekusi & diautomasi** dalam 3 bulan.
> Profil: self-taught dev — Python / JS / TS / React / FastAPI / Docker / Linux, 5 tahun shift pabrik semen.
> Prinsip ranking: **speed-to-first-dollar** + kemudahan untuk dev pemola (belum ada portofolio klien).
> ⚠️ Bug bounty di sini = **research only**. Jangan jalankan scan ke target sungguhan tanpa izin program.

---

## TL;DR — 3 Income Stream (di-rank paling cepat cair)

| # | Stream | First $ | Modal | Ceiling/bln | Cocok krn |
|---|--------|---------|-------|-------------|-----------|
| 1 | **Freelance AI-dev** (Upwork/Contra) | 3–10 hari | $0 | $800–3000 | skill lo udah cocok, tinggal proof |
| 2 | **AI-agent / automation gigs** (produk sendiri + gig) | 1–3 minggu | $0–20 | $500–2500 | leverage FastAPI+Docker, recurring |
| 3 | **Bug bounty** (VDP dulu → paid) | 3–8 minggu | $0 | $0–1500 | slow-burn, skill asset jangka panjang |

**Realistic combined target bulan-3: $1.500–4.000/bln** — cukup buat exit + buffer.

---

## STREAM 1 — Freelance AI-Dev (PALING CEPAT CAIR)

**Kenapa #1:** demand AI-dev meledak, rate AI-literate dev +44% di Upwork. Lo udah punya
stack yang persis dicari (FastAPI backend, React frontend, Docker deploy, Python automation).
Yang kurang cuma *proof* — bukan skill.

### Platform (di-rank)
1. **Upwork** — volume job terbesar, 2600+ job "automation" aktif. Cair paling cepat untuk pemula.
2. **Contra** — 0% commission, bagus buat portfolio + direct client, kompetisi lebih sepi.
3. **Toptal** — bayaran tertinggi TAPI ada screening ketat (skip dulu, apply paralel di bulan-2).

### EXACT FIRST ACTION (hari ini)
```bash
# 1. Bikin akun + profil (30 menit, sekali doang)
#    Upwork:  https://www.upwork.com/nx/create-profile/
#    Contra:  https://contra.com/onboarding
#
# 2. Judul profil (copy-paste, edit dikit):
#    "AI Automation & Full-Stack Dev — FastAPI · React · Docker · Python bots"
#
# 3. WAJIB: 2-3 proof project di GitHub SEBELUM apply job.
#    Bikin repo publik cepat — ini yang bikin klien percaya:
git init ai-invoice-parser && cd ai-invoice-parser
# contoh: FastAPI endpoint yang parse PDF invoice pakai LLM → JSON
# contoh: React dashboard + FastAPI CRUD + Docker compose
# contoh: Python scraper→Sheets automation
```
### Cara menang bid (pemula):
- Filter job **"< 5 proposals"** + **"payment verified"** → apply dalam < 1 jam posting.
- Proposal 4 baris: (1) paham masalahnya, (2) link repo mirip, (3) "gue kirim demo 24 jam", (4) harga.
- Jam Aceh: pantau posting jam kerja US/EU (malam WIB).

### Target duit
- Bulan 1: 1–2 gig kecil ($50–200/gig) → **$150–400**
- Bulan 2: repeat client + rate naik → **$600–1200**
- Bulan 3: **$1000–2500**

---

## STREAM 2 — AI-Agent / Automation Products & Gigs

**Kenapa #2:** lebih lambat dari #1 buat gig pertama, tapi bisa jadi **recurring revenue**
(langganan) + reusable. Lo punya Docker+FastAPI = bisa deploy micro-SaaS/agent sendiri.

### Bentuk paling cepat cair
1. **"Automation-as-a-gig"** di Upwork/Fiverr: "gue automate workflow X pakai Python + AI".
   (email triage, scraping→sheets, report generator, chatbot FastAPI).
2. **Micro-tool berlangganan**: satu agent kecil selesaikan 1 masalah niche, jual $9–29/bln.
3. **Template/boilerplate**: jual FastAPI+LLM starter kit di Gumroad ($15–49 sekali beli).

### EXACT FIRST ACTION
```bash
# 1. Bangun 1 agent demo yang bisa langsung dijual jadi jasa:
mkdir ai-report-agent && cd ai-report-agent
# FastAPI + scheduler: tarik data → ringkas pakai LLM → kirim email/Slack
# Dockerize biar "deploy di server klien" jadi selling point.
docker init && docker build -t ai-report-agent .

# 2. List di Fiverr sbg gig konkret (bukan 'I will do automation'):
#    "I will build a Python AI agent that auto-generates your weekly report"
#    URL: https://www.fiverr.com/start_selling

# 3. Gumroad buat produk pasif:
#    https://gumroad.com/  → upload FastAPI+LLM boilerplate
```
### Target duit
- Bulan 1: **$0–200** (setup + gig pertama)
- Bulan 2: **$300–1000** (2–4 gig + first subscriber)
- Bulan 3: **$500–2000** (recurring mulai numpuk)

---

## STREAM 3 — Bug Bounty (SLOW-BURN, RESEARCH ONLY)

**Kenapa #3:** first-dollar paling lama & tidak pasti untuk pemula — TAPI skill-asset jangka
panjang + bisa diautomasi recon-nya. Perlakukan sebagai **side-bet**, bukan andalan exit.

### Platform (di-rank untuk pemula, dari riset)
1. **Intigriti** — onboarding paling bersih, triage cepat, komunitas suportif. **Mulai di sini.**
2. **Bugcrowd** — banyak program, kompetisi lebih sepi dari HackerOne.
3. **YesWeHack** — ramah pemula (banyak firma EU).
4. **HackerOne** — program terbanyak tapi paling ramai; masuk setelah punya 1–2 laporan valid.

### Jalur pemula → duit
- Mulai dari **VDP** (Vulnerability Disclosure Program, no-pay) buat bangun reputasi + rep points.
- Fokus **1 kelas bug** dulu (IDOR / broken access control / info disclosure) — bukan tembak semua.
- Naik ke paid program setelah 2–3 laporan valid.

### EXACT FIRST ACTION (research/setup only)
```bash
# 1. Daftar & baca policy (GRATIS):
#    https://app.intigriti.com/researcher/programs
#    https://bugcrowd.com/programs
#
# 2. Setup toolkit recon (jangan scan target sungguhan tanpa scope izin):
pipx install bbot            # recon otomatis
sudo apt install -y nuclei subfinder httpx-toolkit
nuclei -update-templates
#
# 3. Latihan LEGAL dulu (bukan real target):
#    - PortSwigger Web Security Academy (gratis, wajib): https://portswigger.net/web-security
#    - HackTheBox / TryHackMe lab
```
### Target duit
- Bulan 1: **$0** (belajar + VDP)
- Bulan 2: **$0–300** (bounty kecil pertama)
- Bulan 3: **$0–1500** (kalau nemu 1 bug medium)

---

## AUTOMASI PAKAI HERMES (cron + skills)

Hermes bisa jalanin loop otomatis biar lo fokus di eksekusi (demo/proposal), bukan cari lead.

### Cron jobs yang disarankan
```bash
# 1. Job hunt otomatis — scan gig baru 3x/hari (pagi/siang/malam WIB)
hermes cron add ai-job-hunt \
  --schedule "0 9,15,21 * * *" \
  --prompt "Jalankan skill ai-job-search-workflow: cari job AI-dev/FastAPI/automation
            di Upwork+Contra yang <5 proposal & payment verified, draft proposal, log ke
            D:/repositories/Quant-Nanggroe-AI-worktree/leads.md"

# 2. Bug bounty recon (RESEARCH ONLY) — tiap 6 jam
hermes cron add bb-passive-recon \
  --schedule "0 */6 * * *" \
  --prompt "Jalankan skill passive-bug-bounty: kumpulkan program baru di Intigriti/Bugcrowd
            yang ramah pemula + scope-nya cocok IDOR/info-disclosure. Passive/OSINT only,
            JANGAN aktif-scan target. Log ke bb-programs.md"

# 3. Weekly review — Minggu malam
hermes cron add weekly-money-review \
  --schedule "0 20 * * 0" \
  --prompt "Ringkas leads.md + income minggu ini, hitung progress vs target exit, saran fokus minggu depan"
```

### Skills Hermes yang dipakai
- **ai-job-search-workflow** → Stream 1 (cari + draft proposal otomatis).
- **passive-bug-bounty** → Stream 3 (discovery program & recon pasif, aman).
- **bug-bounty-hunter** → Stream 3 (HANYA saat sudah punya scope + izin program; jangan auto).

> Catatan: cron cukup buat **discovery + draft**. Keputusan submit proposal / laporan bug
> tetap manual (human-in-the-loop) — biar ga spam & tetap etis.

---

## RENCANA 3 BULAN (ringkas)

| Minggu | Fokus |
|--------|-------|
| 1 | Setup profil Upwork+Contra, bikin 3 repo proof, cron job-hunt nyala |
| 2–4 | Apply 5–10 job/hari, kirim demo cepat, dapat gig pertama (Stream 1) |
| 5–8 | Bangun 1 AI-agent produk (Stream 2), repeat client, mulai VDP (Stream 3) |
| 9–12 | Recurring subscriber + rate naik, target combined **$1500–4000/bln** |

### Prioritas duit → exit
1. **Stream 1 dulu** (cash cepat buat tiket/visa/buffer).
2. **Stream 2** bangun paralel (recurring buat sustain di luar negeri).
3. **Stream 3** side-bet (skill + upside, jangan diandalkan buat deadline).

**Exit trigger:** begitu total tabungan ≥ target biaya pindah + 3 bulan buffer, eksekusi keberangkatan.
