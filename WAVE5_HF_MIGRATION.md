# WAVE 5 — PETA MIGRASI STRATEGI HF → QNA

**Tanggal**: 2026-07-23
**Sumber (HF)**: `E:/trading` (repo hedge fund asli)
**Target (QNA)**: `D:/repositories/Quant-Nanggroe-AI-worktree`
**Bahasa**: Indonesia

---

## 1. RINGKASAN EKSEKUTIF

Penelusuran repo menunjukkan bahwa **worktree QNA saat ini sudah berisi salinan parsial strategi HF** (dhaher/kronos/tradebobby sudah di-copy ke dua paket legacy QNA). Namun strategi-strategi tersebut **belum terdaftar di engine kanonikal QNA yang baru** (`quant_nanggroe/engine/strategy/` — tunggal).

Dari 6 strategi HF yang diminta:

| Strategi HF | Status di QNA | Tindakan |
|---|---|---|
| Wyckoff Sharpe 3.0 (`wyckoff`) | ✅ Sudah ada versi native superior | **JANGAN migrasi** — akan konflik registry |
| MeanRev SR1.98 (`mean_rev`) | ✅ Sudah ada versi native | **JANGAN migrasi** — akan konflik registry |
| Dhaher (`dhaher_system`) | ⚠️ Hanya di paket legacy (sudah di-copy tapi tidak di engine baru) | **MIGRASI ke engine baru** |
| Kronos (`kronos`) | ⚠️ Sama | **MIGRASI** (butuh dep `kronos` model) |
| KronosEnsemble (`kronos_ensemble`) | ⚠️ Sama | **MIGRASI** |
| TradeBobbySMC (`tradebobby_smc`) | ⚠️ Sama | **MIGRASI** |

**Temuan kunci — "dependency yang hilang":**
- `torch` → **SUDAH ADA** di venv QNA (`2.13.0+cpu`). Bukan blocker, tapi harus masuk `requirements`.
- `ai_hf` / `ai-hf` → **BUKAN paket eksternal**. Ini merujuk ke adapter internal QNA sendiri (`quant_nanggroe/engine/agentic/adapters.py::AIHFAdapter`). Sudah ada. Label "ai_hf" adalah nama sistem AI Hedge Fund (debate 15-investor), bukan dependency pip.
- `kronos` wrapper → butuh paket eksternal **Kronos Foundation Model** (`from model import KronosTokenizer, Kronos, KronosPredictor`, `kronos_wrapper.py:26`). Paket ini **TIDAK ada di QNA**. Di-handle oleh guard `KRONOS_AVAILABLE` → fallback `_FallbackKronosPredictor` (momentum). Jadi Kronos migrasi tapi **jalan di mode degraded** sampai model package diinstal.

---

## 2. PETA ARSITEKTUR (3 registry, 2 engine)

### HF asli (`E:/trading`)
```
strategy_registry.py          # decorator register(); dict STRATEGIES{}
  @register WyckoffStrategy      line 406 (name="wyckoff"   line 408)
  @register MeanReversionStrategy line 192 (name="mean_rev"  line 195)  ← "MeanRev SR1.98"
  @register SMCStrategy          line 91  (name="smc")
  @register SMCStrategyOld       line 436 (name="smc_old")
  + 6 lainnya (MSNR, Fibo, EMAADX, QuarterlyTheory, AMDX, Algebra)

strategies/                   # strategi lanjutan, @register di modul masing-masing
  dhaher_system.py            # DhaherSystem        (name="dhaher_system"   line 45)
  kronos_wrapper.py           # KronosSignalProvider(name="kronos"        line 89)  + KronosEnsembleStrategy(name="kronos_ensemble" line 233)
  tradebobby_smc_scanner.py   # TradeBobbySMCStrategy(name="tradebobby_smc" line 484)
  smc_strategy_OLD.py         # SMCStrategy_OLD     (name="smc_old")
```

Label performa (bukan versi kode):
- "Wyckoff Sharpe 3.0"  → `hedge_fund.py:3667` (`signal_wyckoff` "Sharpe 3.0")
- "MeanRev SR1.98"      → `dashboard.py:42` (`("MeanRev", ..., "SR 1.982", ...)`)

### QNA worktree — DUA engine paralel (ini sumber konflik)

**A. Engine KANONIKAL (baru, target migrasi)** — `quant_nanggroe/engine/strategy/` (tunggal)
- Registry dataclass: `quant_nanggroe/engine/strategy/registry.py` (`StrategyRegistry`, `StrategyMetadata`, `register()` line 126, `record_walk_forward()` line 156).
- Loader: `quant_nanggroe/engine/strategy/loader.py` (`StrategyRegistry` line 521, `register()` line 554).
- Strategi: `quant_nanggroe/engine/strategy/strategies/` (**109 file**).
- **Mekanisme registrasi**: BUKAN decorator. Lewat `strategies/__init__.py`:
  - `from . import <modul>` (lines 120–228)
  - dict `_NAME_MAP` (lines 236–351) memetakan `"modul" → "ClassName"`
  - `create_strategy(name)` (line 354).
- Interface strategi: `BaseStrategy` (`generate_signal(self, data: pd.DataFrame) -> Optional[Signal]`), file `strategies/base_strategy.py:47` / class line 21.
- **Equivalen native SUDAH ADA**:
  - `strategies/wyckoff_strategy.py:41` → `class WyckoffStrategy`
  - `strategies/mean_reversion.py:34` → `class MeanReversionStrategy`
  - `strategies/smc_strategy.py:34` → `class SMCStrategy`
- **Dhaher / Kronos / KronosEnsemble / TradeBobbySMC = ABSEN** dari engine ini.

**B. Paket LEGACY (sudah di-copy dari HF)** — ada di 2 lokasi:
- `quant_nanggroe/engine/strategies/` (plural) — `dhaher_system.py`, `kronos_wrapper.py`, `tradebobby_smc_scanner.py`, `smc_strategy_OLD.py`, `registry.py` (decorator `register()` line 23), `__init__.py` (scan lines 14–19).
- `strategies/` (top-level) — salinan sama + `strategy_registry.py` (EXISTS di root QNA, sehingga import HF tidak error).
- `quant_nanggroe/hedge_fund/hedge_fund.py` — salinan HF lengkap dgn `signal_aihf` (line ~110), `signal_kronos`, `QNA_EVOLVED_PROVIDERS`.

> ⚠️ **Konflik registry**: Dhaher/Kronos/TradeBobby saat ini "terdaftar" di `engine/strategies/registry.py` (decorator, legacy) tapi **tidak** di engine kanonikal `engine/strategy/`. Dua registry hidup berdampingan.

---

## 3. TABEL MAPPING STRATEGI (6 HF vs QNA)

| # | Strategi HF | Class HF (file:line) | `name` HF | Equivalent QNA | Lokasi QNA | Keputusan | Catatan |
|---|---|---|---|---|---|---|---|
| 1 | Wyckoff Sharpe 3.0 | `WyckoffStrategy` (`strategy_registry.py:406`, name `:408`) | `wyckoff` | `WyckoffStrategy` native | `engine/strategy/strategies/wyckoff_strategy.py:41` | **NO-MIGRATE** (conflict) | QNA sudah punya versi lebih baik (volume-price phase detection). Migrasi HF = duplikat. |
| 2 | MeanRev SR1.98 | `MeanReversionStrategy` (`strategy_registry.py:192`, name `:195`) | `mean_rev` | `MeanReversionStrategy` native | `engine/strategy/strategies/mean_reversion.py:34` | **NO-MIGRATE** (conflict) | Versi QNA lebih lengkap (stat + half-life). |
| 3 | Dhaher | `DhaherSystem` (`strategies/dhaher_system.py:26`, name `:45`) | `dhaher_system` | — (tidak ada) | legacy `engine/strategies/dhaher_system.py:27` `@register` | **MIGRATE → engine baru** | Dep: pandas/numpy only. Aman. |
| 4 | Kronos | `KronosSignalProvider` (`strategies/kronos_wrapper.py:71`, name `:89`) | `kronos` | — (tidak ada) | legacy `engine/strategies/kronos_wrapper.py` | **MIGRATE** (degraded) | Butuh `torch` (ada) + paket `kronos` model (TIDAK ada → fallback momentum). |
| 5 | KronosEnsemble | `KronosEnsembleStrategy` (`strategies/kronos_wrapper.py:228`, name `:233`) | `kronos_ensemble` | — (tidak ada) | legacy `engine/strategies/kronos_wrapper.py` | **MIGRATE** (degraded) | Sama dgn #4. |
| 6 | TradeBobbySMC | `TradeBobbySMCStrategy` (`strategies/tradebobby_smc_scanner.py:473`, name `:484`) | `tradebobby_smc` | — (tidak ada) | legacy `engine/strategies/tradebobby_smc_scanner.py` | **MIGRATE** | Dep: pandas/numpy/enum only. Aman. |

---

## 4. KONFLIK REGISTRY (detail)

1. **Colliding class names (HF vs QNA baru)**
   - `WyckoffStrategy`, `MeanReversionStrategy`, `SMCStrategy` ada **di kedua sisi** dengan base class & interface BERBEDA:
     - HF: `generate_signals(self, df) -> df` (returns column `entry`)
     - QNA baru: `generate_signal(self, data) -> Signal`
   - Jika `strategy_registry.py` HF di-import mentah ke engine baru → NameError / override kelas. **Solusi**: jangan impor HF registry; gunakan equivalen native (#1,#2) atau adaptasi interface.

2. **Dua registry aktif di QNA**
   - `engine/strategy/registry.py` (dataclass, kanonikal) vs `engine/strategies/registry.py` (decorator, legacy/HF-imported).
   - `strategies/__init__.py` (top-level) & `engine/strategies/__init__.py` keduanya scan & import modul HF yang sama → registrasi ganda di dua registry.

3. **`_NAME_MAP` QNA baru belum punya entry** dhaher/kronos/tradebobby → `create_strategy("dhaher_system")` akan `ValueError` di engine baru (meski jalan di legacy).

---

## 5. DEPENDENCY YANG HILANG / KONDISIONAL

| Dependency | Status di QNA | Dampak | Tindakan |
|---|---|---|---|
| `torch` | ✅ `2.13.0+cpu` (venv) | Kronos butuh `import torch` (`kronos_wrapper.py:123`) | Pastikan di `requirements.txt`. Sudah dipakai `engine/model_registry.py:672`. |
| `ai_hf` / `ai-hf` | ✅ Internal (`engine/agentic/adapters.py::AIHFAdapter`) | "aihf" = sistem QNA sendiri, bukan pip pkg | Tidak ada yang diinstal. Pastikan `adapters.py` ter-import. |
| `kronos` (Foundation Model) | ❌ TIDAK ADA | `from model import KronosTokenizer, Kronos, KronosPredictor` (`kronos_wrapper.py:26`) gagal → `KRONOS_AVAILABLE=False` | Kronos jalan di **fallback momentum** (`_FallbackKronosPredictor`, `kronos_wrapper.py:34`). Instal paket `kronos` bila ingin prediksi penuh. |
| `numpy`/`pandas` | ✅ Standar | Semua strategi | — |

---

## 6. TARGET REGISTER (file:line) DI QNA — UNTUK MIGRASI #3,#4,#5,#6

Engine kanonikal `quant_nanggroe/engine/strategy/` adalah target resmi.

**Langkah A — Buat modul adaptor** (interface `BaseStrategy.generate_signal`):
- `quant_nanggroe/engine/strategy/strategies/dhaher_system.py`  (adaptasi dari `E:/trading/strategies/dhaher_system.py`)
- `quant_nanggroe/engine/strategy/strategies/kronos_wrapper.py`  (adaptasi dari `E:/trading/strategies/kronos_wrapper.py`, pertahankan guard `KRONOS_AVAILABLE`)
- `quant_nanggroe/engine/strategy/strategies/tradebobby_smc_scanner.py` (adaptasi dari `E:/trading/strategies/tradebobby_smc_scanner.py`)

**Langkah B — Daftarkan import** di `quant_nanggroe/engine/strategy/strategies/__init__.py`:
- Sisipkan setelah line **228** (`from . import dark_pool_flow`):
  ```python
  from . import dhaher_system
  from . import kronos_wrapper
  from . import tradebobby_smc_scanner
  ```
- Sisipkan entry di dict `_NAME_MAP` (antara line **350** dan **351** `}`):
  ```python
  "dhaher_system": "DhaherSystem",
  "kronos_wrapper": "KronosSignalProvider",
  "tradebobby_smc_scanner": "TradeBobbySMCStrategy",
  ```
  (`create_strategy()` di line **354** akan otomatis mengenali.)

**Langkah C — Opsional, hindari duplikasi**: hapus/nonaktifkan salinan legacy di `engine/strategies/` & `strategies/` agar hanya satu registry (kanonikal) yang berlaku, menyelesaikan konflik #2 & #3.

**Verifikasi**:
```bash
python -c "from quant_nanggroe.engine.strategy.strategies import create_strategy as c; \
  [print(n, type(c(n)).__name__) for n in ('dhaher_system','kronos_wrapper','tradebobby_smc_scanner')]"
```

---

## 7. PLAN EKSEKUSI SINGKAT

1. **JANGAN** migrasi `wyckoff` & `mean_rev` — sudah ada native (`wyckoff_strategy.py:41`, `mean_reversion.py:34`). Hapus duplikat HF bila ada di legacy.
2. **MIGRASI** `dhaher_system`, `kronos`, `kronos_ensemble`, `tradebobby_smc` ke engine kanonikal via Langkah A–C (§6).
3. **Tambah `torch` ke requirements** (sudah terpasang, tapi explicit).
4. **Catat** Kronos berjalan degraded (fallback momentum) sampai paket `kronos` Foundation Model diinstal.
5. **Resolusi konflik**: konsolidasi ke satu registry (`engine/strategy/registry.py`); sunting/arsip legacy `engine/strategies/` & top-level `strategies/`.

---

## 8. BUKTI GREP (reproduksi)

```
# HF strategy names
E:/trading/strategy_registry.py:406  class WyckoffStrategy / name="wyckoff" :408
E:/trading/strategy_registry.py:192  class MeanReversionStrategy / name="mean_rev" :195
E:/trading/strategies/dhaher_system.py:26      class DhaherSystem / name="dhaher_system" :45
E:/trading/strategies/kronos_wrapper.py:71     class KronosSignalProvider / name="kronos" :89
E:/trading/strategies/kronos_wrapper.py:228    class KronosEnsembleStrategy / name="kronos_ensemble" :233
E:/trading/strategies/tradebobby_smc_scanner.py:473 class TradeBobbySMCStrategy / name="tradebobby_smc" :484
E:/trading/strategies/kronos_wrapper.py:26     from model import KronosTokenizer, Kronos, KronosPredictor
E:/trading/strategies/kronos_wrapper.py:123    import torch
E:/trading/dashboard.py:42   ("MeanRev", ..., "SR 1.982", ...)
E:/trading/hedge_fund.py:3667  signal_wyckoff "Sharpe 3.0"

# QNA equivalent native (engine baru)
quant_nanggroe/engine/strategy/strategies/wyckoff_strategy.py:41    class WyckoffStrategy
quant_nanggroe/engine/strategy/strategies/mean_reversion.py:34      class MeanReversionStrategy
quant_nanggroe/engine/strategy/strategies/smc_strategy.py:34        class SMCStrategy
quant_nanggroe/engine/strategy/strategies/__init__.py:228  last from . import (before insert)
quant_nanggroe/engine/strategy/strategies/__init__.py:236  _NAME_MAP start / :351 close / :354 create_strategy
quant_nanggroe/engine/strategy/registry.py:126  StrategyRegistry.register
quant_nanggroe/engine/strategy/strategies/base_strategy.py:21  class BaseStrategy / :47 generate_signal

# QNA legacy (sudah di-copy HF)
quant_nanggroe/engine/strategies/dhaher_system.py:27   @StrategyRegistry.register
quant_nanggroe/engine/strategies/registry.py:23        def register
quant_nanggroe/engine/strategies/__init__.py:14-19     scan list (dhaher,kronos,tradebobby,smc_old)
strategies/__init__.py:15-17                            same top-level
strategy_registry.py (root QNA) EXISTS  -> HF import tidak error

# torch & ai_hf
venv: import torch -> 2.13.0+cpu  OK
quant_nanggroe/engine/agentic/adapters.py:89  aihf / AIHFAdapter (internal)
```
