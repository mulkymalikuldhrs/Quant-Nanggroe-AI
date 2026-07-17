# TEMUAN AUDIT — kill_switch.py + guards.py (fail-closed)

Tanggal: 2026-07-17
Auditor: subagent (ponytail mode)

## Ringkasan

- **kill_switch.py**: FAIL-CLOSED ✅ benar jalan. Tidak perlu diubah.
- **guards.py**: FAIL-CLOSED ❌ RUSAK (ada gap serius) → sudah diperbaiki.
- 2 test case minimal ditulis & lulus (`test_guards.py`, 2 passed; full file 71 passed).

---

## 1. kill_switch.py — FAIL-CLOSED ✅

Alur fail-closed (file-backed, env `QNA_KILL_SWITCH_STATE_FILE`):

- `__init__` → `_ks_store_path()` baca env → kalau ada, panggil `_reconcile()`.
- `_ks_read()` (baris ~48-55): `json.loads` dibungkus try/except.
  - `FileNotFoundError` → `None` (belum pernah aktif → INACTIVE, benar).
  - **segala Exception lain (corrupt / permission denied) → return `{"_fail_closed": True}`** (FAIL CLOSED = asumsi ACTIVE/halt).
- `_reconcile()` (baris ~229-250): kalau `data.get("_fail_closed")` → set `status=ACTIVE`, `current_level=LEVEL_2`.
- `_ensure_reconciled()` (baris ~265-268): dipanggil di awal `check_auto_activate()` → gate check selalu lihat truth terbaru (C5 cross-process).

Verifikasi: test `test_kill_switch_fail_closed_on_corrupt_state` — tulis file `"garbage"`, init `KillSwitch` dengan env state-file → `ks.is_active is True`. **PASS.**

Kesimpulan: fail-closed di kill_switch sudah benar (corrupt/unreadable → ACTIVE).

---

## 2. guards.py — FAIL-CLOSED ❌ RUSAK (sudah diperbaiki)

### Gap serius (SEBELUM fix)

`GuardPipeline.check()` (baris ~545-546 asli):

```python
for guard in self._guards:
    result = guard.check(order, context)   # <-- TANPA try/except
    results.append(result)
```

- Kalau sebuah guard **raise exception**, exception tersebut **bocor langsung** (propagate ke caller) — BUKAN menghasilkan hasil FAIL/REJECT.
- Docstring `build_default_guard_pipeline` claim: *"any guard FAIL or exception rejects the order"*. Untuk FAIL benar, untuk **exception SALAH** — exception tidak jadi reject, malah bocor.
- Konsumen (`quant_nanggroe/exchange/solana/broker.py:315-322`):

  ```python
  guard_result = self._guard_pipeline.check(draft_order)
  if not guard_result.passed:
      raise OrderError(...)
  ```

  Kalau guard raise, `check()` sendiri yang melempar exception sebelum baris `if not guard_result.passed` tercapai. Order bisa jatuh ke kondisi error tak terduga alih-alih di-REJECT secara deterministik. Ini bukan fail-closed yang andal.

### Fix (root cause, satu tempat)

Bungkus tiap `guard.check()` di `GuardPipeline.check()` dengan try/except:

```python
for guard in self._guards:
    try:
        result = guard.check(order, context)
    except OrderError:
        raise  # sudah rejection disengaja
    except Exception as exc:  # noqa: BLE001
        logger.error("GuardPipeline [%s]: guard %s raised — FAIL (fail-closed)", self._name, guard.name)
        raise OrderError(
            f"Guard {guard.name} raised {type(exc).__name__}: {exc}",
            exchange=self._name,
            original=exc,
        ) from exc
    results.append(result)
```

- Import `OrderError` dari `quant_nanggroe.exchange.base` (aman: base.py tidak import guards, tidak ada circular import — terverifikasi).
- Guard yang raise sekarang → **raise `OrderError`** (fail-closed). Guard normal → tidak ada jalur baru, zero overhead.

Verifikasi: test `test_guard_pipeline_fail_closed_on_guard_exception` — inject `_RaisingGuard` (raise `RuntimeError`) → `pipeline.check(order)` **harus raise `OrderError`**. **PASS** (sebelum fix: gagal karena `RuntimeError` bocor, bukan `OrderError`).

---

## 3. Test case yang ditulis

File: `tests/test_exchange/test_guards.py` (di-append, ikut konvensi file yg sudah ada).

| Test | Assert | Hasil |
|------|--------|-------|
| `test_kill_switch_fail_closed_on_corrupt_state` | state file `"garbage"` → `KillSwitch().is_active is True` | PASS |
| `test_guard_pipeline_fail_closed_on_guard_exception` | guard raise → `pipeline.check()` raises `OrderError` | PASS |

Jalankan:
```
.venv/Scripts/python -m pytest tests/test_exchange/test_guards.py -q
# 71 passed (termasuk 2 test baru)
```

---

## Catatan / rekomendasi

- **Tidak di-commit** (sesuai instruksi).
- Kill switch: tidak ada aksi perlu. Fail-closed sudah benar.
- Guards: fix sudah diterapkan & ter-test. Disarankan review sekilas dari pemilik repo sebelum merge (ubahan ada di `check()` — jalur kritis pre-trade).
- `monkeypatch.setenv` dipakai di test kill switch — pastikan pytest monkeypatch reset env antar test (default pytest sudah reset).
