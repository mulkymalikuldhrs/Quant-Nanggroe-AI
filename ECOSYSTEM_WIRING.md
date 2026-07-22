# ECOSYSTEM WIRING — Dhaher Labs

> Peta koneksi antar-repo + 7 profil Hermes. Tujuan: identifikasi silo & propose quick-win automation.
> Generated: 2026-07-23 · Scope: RESEARCH ONLY (no code modified)
> Hermes root: `C:\Users\Hi\AppData\Local\hermes` · Repos: `D:\repositories`, `E:\`

---

## 1. Repository Map

| Repo | Path | Status | Koneksi ke Lainnya |
|------|------|--------|--------------------|
| **Quant-Nanggroe-AI** (QNA worktree) | `D:\repositories\Quant-Nanggroe-AI-worktree` | 🟢 Active (hedge fund inti) | ← ai-hedge-fund (via `qna-aihf-adapter.py`), ← TradeBobbyTerminal (via `tradebobby_bridge.py`), MT5 MCP |
| **QNA duplicate** | `E:\trading` | ⚠️ Divergent copy — `hedge_fund.py` DIFFER dari worktree | Silo/duplikasi dari QNA worktree |
| ai-hedge-fund | `E:\ai-hedge-fund` | 🟢 Wired | → QNA (15-investor debate → MT5 exec) |
| TradeBobbyTerminal | `E:\TradeBobbyTerminal` | 🟢 Wired | → QNA (`trade_brief.json` → vote bias), daemon :3333 |
| ai-market-maker | `E:\ai-market-maker` | 🟡 Trading, siloed | Tidak ada import ke QNA |
| freqtrade / freqtrade-mcp | `E:\freqtrade*` | 🟡 Siloed | MCP ada tapi belum di-wire ke QNA pipeline |
| Lean / qlib / FinRL / RD-Agent | `E:\` | 🔴 Siloed | Quant libs, tidak dipakai QNA |
| AgentQuant / AI-Trader / tradingagents | `E:\` | 🔴 Siloed | Overlap fungsi dgn QNA, tak terhubung |
| blackhornet (+ .git bare) | `D:\repositories\blackhornet` | 🟡 Standalone | Desktop pet / ops |
| Autonomous-Organism | `D:\repositories\Autonomous-Organism` | 🟡 Standalone | Economy loop, tak wire ke QNA |
| JeumpaLLM | `D:\repositories\JeumpaLLM` | 🟡 Standalone | LLM lokal, potensi provider utk QNA |
| seulanga-rag | `D:\repositories\seulanga-rag` | 🟡 Standalone | RAG memory, tak wire |
| mue-x | `E:\mue-x` | 🟡 Standalone | Self-evolving agent |
| Obsidian Vault | `D:\Obsidian\DhaherLabs` | 🔴 Silo | Target sink dokumentasi — belum ada auto-sync |
| Remote (Codeberg org) | 40+ repo | ⚠️ Partial | GitHub token expired; Codeberg aktif (lihat REMOTE_MAP.md) |

---

## 2. Hermes Profiles (8) & Cron

| Profil | Cron Aktif | Status | Fokus |
|--------|-----------|--------|-------|
| **researchbot** | `researchbot-continuous-cycle` (720m) | 🟢 ACTIVE | Scrape GitHub/arXiv quant → `E:\trading\research\*.md` |
| **devbot** | `graphify-dhaherlabs-update` (360m) | 🔴 PAUSED (error: model drift) | Update knowledge graph + Obsidian vault |
| **fangbot** | `remote-job-research-delivery` (1x) | 🔴 PAUSED | Job hunting delivery → Telegram |
| **clawbot** | — (jobs.json kosong) | ⚪ Idle | (belum dialokasikan) |
| **autobot** | — (no jobs.json) | ⚪ Idle | (belum dialokasikan) |
| **hackerbot** | — (no jobs.json) | ⚪ Idle | Security/pentest (implied) |
| **traderbot** | — (no jobs.json) | ⚪ Idle | **KOSONG — seharusnya jalankan QNA/PnL** |
| default | — | ⚪ Base | Session interaktif |

**Delivery target semua cron:** Telegram `1474659350` (Mulky).

---

## 3. Gap Wiring — Yang Seharusnya Terhubung Tapi Tidak

1. **QNA duplikasi D: vs E:** — dua salinan QNA (`D:\...worktree` & `E:\trading`) dengan `hedge_fund.py` yang BERBEDA. Risiko divergence & bug silent. Harus ada satu source-of-truth + sync.
2. **traderbot profil kosong** — profil khusus trader tidak punya cron sama sekali. QNA PnL/status tidak pernah otomatis dilaporkan ke Telegram walau `qna-status.sh` sudah ada.
3. **researchbot → QNA loop terputus** — researchbot menulis `PRIORITY.md` tapi tak ada konsumen otomatis; findings tidak masuk ke strategy_registry QNA.
4. **devbot graphify → Obsidian PAUSED** — pipeline dokumentasi (graphify + vault sync) mati karena model drift. Vault `D:\Obsidian\DhaherLabs` jadi stale/silo.
5. **Quant libs siloed** — Lean/qlib/FinRL/freqtrade-mcp punya kapabilitas kuat tapi 0 integrasi ke QNA.

---

## 4. Tiga Proposal Automasi Prioritas

### 🥇 P1 — traderbot: QNA PnL/Status → Telegram (2x/hari)
Isi kekosongan traderbot; laporan PnL otomatis. `qna-status.sh` sudah ada.
```bash
hermes --profile traderbot cronjob action=create \
  name="qna-pnl-report" \
  schedule="interval:720" \
  workdir="D:\repositories\Quant-Nanggroe-AI-worktree" \
  deliver="telegram:1474659350" \
  prompt="Jalankan ./qna-status.sh, ringkas equity/open positions/PnL harian dari logs/ dan paper_state/, kirim ringkasan ke Telegram. Jika daemon mati, laporkan status DOWN."
```

### 🥈 P2 — Fix + resume devbot graphify → Obsidian sync (repin model)
Pipeline sudah ada, cuma paused karena model drift. Pin ke model saat ini lalu resume.
```bash
# Repin ke inference config aktif, lalu enable
hermes --profile devbot cronjob action=update job_id=35d87f88b640 \
  provider=9router model=combo
hermes --profile devbot cronjob action=resume job_id=35d87f88b640
# Prompt existing sudah: graphify update → D: update → update Obsidian vault
```
Tambahan sync eksplisit repo→vault (rsync markdown QNA ke vault):
```bash
# schedule harian, workdir D:\repositories
rsync -av --include='*.md' --include='*/' --exclude='*' \
  Quant-Nanggroe-AI-worktree/ /d/Obsidian/DhaherLabs/QNA/
```

### 🥉 P3 — researchbot findings → QNA research inbox (close the loop)
Sambungkan output researchbot ke QNA supaya PRIORITY.md dikonsumsi, bukan silo.
```bash
hermes --profile researchbot cronjob action=create \
  name="research-to-qna-bridge" \
  schedule="interval:1440" \
  workdir="D:\repositories\Quant-Nanggroe-AI-worktree" \
  deliver="telegram:1474659350" \
  prompt="Baca E:/trading/research/PRIORITY.md. Untuk tiap repo/paper HIGH-IMPACT baru, tulis 1 entry ringkas ke research/INBOX.md di QNA worktree dgn: nama, link, kenapa relevan ke strategy_registry, action item. Jangan modifikasi kode strategi. Commit INBOX.md saja. Kirim summary ke Telegram."
```

---

## 5. Rekomendasi Tambahan (backlog)
- **Konsolidasi QNA D:/E:** tetapkan `D:\...worktree` sebagai source-of-truth; ubah `E:\trading` jadi symlink atau hapus setelah verifikasi diff.
- **Aktifkan hackerbot** untuk idle-bug-hunt / security scan repo (skill `bug-bounty-hunter`).
- **Wire freqtrade-mcp** sebagai data/exec fallback di QNA multi-pair scanner.
- **Regenerate GitHub PAT** (semua expired per REMOTE_MAP.md) agar push GitHub kembali jalan; Codeberg tetap primary.

---
*RESEARCH ONLY. Semua command di atas adalah proposal — belum dieksekusi.*
