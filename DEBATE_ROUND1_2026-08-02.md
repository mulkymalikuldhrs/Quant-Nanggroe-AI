# DEBATE ROUND 1 — 2026-08-02 (clawbot-facilitated, 3 kubu paralel)

**Topik:** Apakah QNA aman lanjut live dengan equity $1.122 setelah FASE 0, dan apa syarat minimum sebelum market buka Senin?

**Format:** 3 subagent internal (PRO-LIVE / CONTRA-LIVE / OPERATOR-CTO) → sintesis clawbot (verify-before-accept) → keputusan → ajukan ke @dhaherautobot.

---

## Posisi kubu

### 🟢 PRO-LIVE (hawk)
FASE 0 menutup semua gap kritis (verified di kode, commit 804a716f/a49d6704). Engine sudah live dengan 3 posisi. Self-eval/attribution yang baru diperbaiki hanya menghasilkan bukti DENGAN trading. Paper ≠ live (fills, slippage, psikologi). Data yang diminta skeptis (journal rows, Kelly) hanya muncul dari live trading. **Verdict: GO LIVE with conditions.**

### 🔴 CONTRA-LIVE (bear)
Fix belum live-verified (0 live fill sejak fix). G11 structure trailing baru & unbacktested → hair-trigger di chop. 3 posisi legacy dari kode buggy (unknown risk state, mungkin naked). $1.122 kecil — 1 minggu buruk bisa wipe. Edge UNPROVEN: journal 0 rows, tidak ada strategi yang terbukti positive expectancy. **Verdict: OBSERVE dulu / watch-mode.**

### ⚙️ OPERATOR/CTO (netral) — bobot tertinggi
**Residual risk CRITICAL:**
- **C1:** Registry strategies (G4 fix) go live pertama kali di real money → unproven signal logic. Mitigasi: min-conf 0.6, resolve_conflicts, caps 1/symbol + 5 total, SL-mandatory, worst-case ~$32 (5×$6.50).
- **C2:** 3 legacy positions (20178543987, 20188224176/713) = contaminated inventory: unattributed, **mungkin NAKED (SL=0)**. PositionManager hanya TAMBAH SL setelah 1R profit — naked loser tidak pernah di-stop. Monday gap = risiko unbounded terbesar. **Harus close di tick pertama.**

**Minor:** M1 exit_price math kosmetik salah (autonomous_cycle.py:536).

**Verdict: HYBRID GO-LIVE Monday** — close legacy di open, 11-step verifikasi, kill-switch drill, hard-abort rules, satu loop.

---

## Cross-check clawbot (verify before accept) — 2026-08-02 PM

| Klaim kubu | Verdict clawbot | Bukti kode |
|-----------|----------------|------------|
| C1: `initial_balance=10000.0` masih seed → risk phantom | ❌ **SALAH** — seed hanya nilai awal konstruktor; `engine.start()` (autonomous_cycle.py:775) DAN `cycle()` (bridge:356-359) override `risk.balance = mt5.account_balance()` ($1.122) sebelum trading; daily-loss >3% = block (bridge:267-270) | line 774/775, 335-340, 356-359 |
| G3 doc-only, belum fill-proven | ⚠️ **BENAR tapi kontekstual** — market tutup Minggu, tidak ada fill sejak fix; verifikasi Senin wajib | — |
| Journal DB 0 bytes | ✅ **BENAR tapi bukan bug** — `data/qna_trade_journal.db` 0 bytes (schema dibuat saat first boot); boot Senin pertama akan bikin schema + rows | ls -la |
| Legacy positions mungkin naked (SL=0) | ✅ **VALID & KRITIS** — 3 posisi dari kode pre-fix G6 (naked fill); SL hanya ditambah setelah 1R profit (autonomous_cycle.py:600-615) | line 600-615 |
| G11 trailing unbacktested | ✅ **VALID** — unit-tested only; observasi live 1-2 minggu | risk_levels.py:155-194 |
| Lock G8 stale | ❌ **SALAH** — OS file lock (msvcrt/fcntl), auto-release saat mati; file isi `0` = placeholder normal; proses lama sudah mati | line 45-84 |

---

## ✅ KEPUTUSAN (kesepakatan 3 kubu + cross-check clawbot)

### HYBRID GO-LIVE MONDAY (dengan kondisi — bukan GO LIVE penuh, bukan OBSERVE penuh)

**Post-debate code enforcement (2026-08-02 PM):** Keputusan "close 3 legacy di tick pertama" AWALNYA KONTRADIKTIF dengan kode (loop meng-ADOPT posisi lama via `_manage_position`, tidak menutup). Diperbaiki dengan `reconcile_legacy_positions()` (autonomous_cycle.py:498+) yang **force-close posisi OPEN tanpa journal record** (orphan/pre-FASE0) di cycle #1, sambil mempertahankan posisi QNA-journaled. Verified (unit test): orphan→close, journaled→keep. Ini mengeksekusi C2 secara fail-closed, bukan manual.

1. **CLOSE 3 legacy positions di tick pertama open** (C2) — sekarang otomatis via `reconcile_legacy_positions()`. Menghilangkan risiko unbounded terbesar (naked loser + Monday gap).
2. **Boot SATU instance** `env -u PYTHONPATH PYTHONPATH=. .venv312/Scripts/python.exe -m quant_nanggroe.autonomous_cycle` (G8 lock mencegah ganda).
3. **Verifikasi 11 langkah** (protokol di bawah) — PASS semua → lanjut; FAIL 1 CRITICAL → abort + kill-switch.
4. **Risk terbatas per design:** caps 1/symbol + 5 total, SL mandatory, min-conf 0.6, daily-loss 3% auto-block, worst-case realistic ~$32.
5. **G11 trailing** dipantau 1-2 minggu (unbacktested); kalau chop makan profit berulang → downgrade ke ATR-only (fallback sudah di kode).
6. **$1.000 hard floor:** equity < $1.000 → trading halt + alert.
7. **Self-eval gate:** setelah N≥20 closed trades per strategi, evaluasi expectancy; strategi negative → disable.

### Protokol verifikasi Senin (11 langkah, executable)
1. Cek `git status` bersih / code = commit terakhir (804a716f, a49d6704)
2. Cek hanya SATU proses autonomous_cycle (tasklist + lock)
3. Boot loop → cek log `MT5 connected LIVE — login=372044706 balance=...` (≈$1.122, bukan $10000)
4. Close 3 legacy positions (20178543987, 20188224176, 20188224713) → log CLOSED retcode DONE
5. Tunggu signal pertama → cek order punya SL+TP (tidak naked)
6. Cek comment di MT5 terminal = `STRATEGY:SYMBOL` (G12)
7. Cek `data/qna_trade_journal.db` growth: schema + rows dengan `strategy` terisi (G1/G2)
8. Cek HOLD logging (G10) muncul di log
9. Cek posisi cap: max 5 total, 1/symbol (G7)
10. Cek kelly_cache berisi setelah first close (G9)
11. Cek kill-switch: file kill → loop berhenti dalam 1 siklus (fail-closed)

**Hard-abort:** balance < $1.000 | daily loss > 3% | order tanpa SL | >1 instance | journal tidak menulis | salah satu dari 3 legacy tidak bisa di-close.

---

## Next
- Keputusan ini diajukan ke **@dhaherautobot** (orchestrator) untuk koordinasi final.
- Execute protokol Senin 08:00 WIB (open market).
- Update md status setelah verifikasi live.
