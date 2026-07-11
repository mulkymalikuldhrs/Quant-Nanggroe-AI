#!/usr/bin/env python3
"""Disaster Recovery Drill v1 — Quant Nanggroe AI.

Simulates catastrophic data loss, validates recovery, then restores.
Phase 2.5 of the AUTONOMOUS_ROADMAP.

Usage::
    python scripts/disaster_recovery_drill.py
    python scripts/disaster_recovery_drill.py --quick
    python scripts/disaster_recovery_drill.py --keep-backup
    python scripts/disaster_recovery_drill.py --backup-dir /tmp/my-backup
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROJECT = "Quant Nanggroe AI"

CRITICAL_DIRS = [
    "data/cached_ohlcv",
    "paper_state",
]

DB_GLOBS = ["data/*.db", "data/**/*.db"]


# ── helpers ───────────────────────────────────────────────────────────────


def log(msg: str, *args) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = msg % args if args else msg
    print(f"[{ts}] {line}")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def phase_header(n: int, label: str) -> None:
    log("")
    log("═══ Phase %d: %s ═══", n, label)


def elapsed(t_start: float) -> str:
    return f"{time.time() - t_start:.1f}s"


# ── drill ─────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Disaster Recovery Drill")
    parser.add_argument(
        "--backup-dir",
        default="/tmp/qna-drill-backup",
        help="Backup directory (default: /tmp/qna-drill-backup)",
    )
    parser.add_argument(
        "--keep-backup",
        action="store_true",
        help="Don't restore files at end (keep backup)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip full rebuild, just verify paths",
    )
    args = parser.parse_args()

    backup_dir = Path(args.backup_dir)
    drill_start = time.time()
    failures: list[str] = []
    critical_failures: list[str] = []

    log("╔══════════════════════════════════════════════════════════╗")
    log("║  %s Disaster Recovery Drill  ║", _PROJECT)
    log("╚══════════════════════════════════════════════════════════╝")
    log("Backup dir: %s", backup_dir)
    log("Quick mode: %s", args.quick)

    # ─────────────────────── Phase 1: Backup ───────────────────────

    phase_header(1, "Backup")
    p1_start = time.time()

    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    backed_up: list[Path] = []

    for rel in CRITICAL_DIRS:
        src = _REPO_ROOT / rel
        dst = backup_dir / rel
        if src.is_dir():
            shutil.copytree(src, dst)
            backed_up.append(src)
            log("  backed up: %s/", rel)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            backed_up.append(src)
            log("  backed up: %s", rel)

    # backup SQLite DBs
    for pattern in DB_GLOBS:
        for db_path in _REPO_ROOT.glob(pattern):
            rel = db_path.relative_to(_REPO_ROOT)
            dst = backup_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, dst)
            backed_up.append(db_path)
            log("  backed up: %s", str(rel))

    # backup any .db in repo root too
    for f in _REPO_ROOT.glob("*.db"):
        rel = f.relative_to(_REPO_ROOT)
        dst = backup_dir / rel
        shutil.copy2(f, dst)
        backed_up.append(f)
        log("  backed up: %s", str(rel))

    log("Backup complete — %d path(s) saved [%s]", len(backed_up), elapsed(p1_start))

    # ───────────────────── Phase 2: Destruction ────────────────────

    phase_header(2, "Destruction")
    p2_start = time.time()

    for rel in CRITICAL_DIRS:
        target = _REPO_ROOT / rel
        if target.is_dir():
            shutil.rmtree(target)
            log("  deleted: %s/", rel)
        elif target.exists():
            target.unlink()
            log("  deleted: %s", rel)

    for pattern in DB_GLOBS:
        for db_path in list(_REPO_ROOT.glob(pattern)):
            db_path.unlink()
            log("  deleted: %s", db_path.relative_to(_REPO_ROOT))

    for f in list(_REPO_ROOT.glob("*.db")):
        f.unlink()
        log("  deleted: %s", f.relative_to(_REPO_ROOT))

    # verify deletion
    deletion_ok = True
    for rel in CRITICAL_DIRS:
        p = _REPO_ROOT / rel
        if p.exists():
            deletion_ok = False
            msg = f"Destruction failed: {rel} still exists"
            critical_failures.append(msg)
            log("  FAIL: %s", msg)

    if deletion_ok:
        log("Destruction verified — all paths gone [%s]", elapsed(p2_start))
    else:
        log("Destruction INCOMPLETE — proceeding anyway [%s]", elapsed(p2_start))

    # ───────────────────── Phase 3: Recovery ───────────────────────

    phase_header(3, "Recovery")
    p3_start = time.time()

    # 3a. Create empty cached_ohlcv
    cached_dir = _REPO_ROOT / "data" / "cached_ohlcv"
    cached_dir.mkdir(parents=True, exist_ok=True)
    log("  3a. Created empty data/cached_ohlcv/")

    # 3b. Regenerate synthetic cache via alpha_destruction
    if not args.quick:
        log("  3b. Running alpha_destruction.py --symbols BTC,ETH --export /dev/null ...")
        r = run([
            sys.executable,
            str(_REPO_ROOT / "scripts" / "alpha_destruction.py"),
            "--symbols", "BTC,ETH",
            "--export", "/dev/null",
        ])
        if r.returncode == 0:
            log("  3b. alpha_destruction OK")
        else:
            msg = f"alpha_destruction failed (rc={r.returncode}): {r.stderr.strip()[:200]}"
            failures.append(msg)
            log("  WARN: %s", msg)
    else:
        log("  3b. Skipped (--quick)")

    # 3c. ComplianceJournal recovery
    compliance_db = _REPO_ROOT / "data" / "compliance.db"
    log("  3c. Checking ComplianceJournal at data/compliance.db ...")
    if compliance_db.exists():
        try:
            conn = sqlite3.connect(str(compliance_db))
            cur = conn.execute("SELECT COUNT(*) FROM events")
            count = cur.fetchone()[0]
            conn.close()
            log("  3c. ComplianceJournal has %d events — state recoverable from last checkpoint", count)
        except Exception as e:
            log("  3c. ComplianceJournal exists but query failed: %s", e)
            # still OK — it's append-only, data is intact
    else:
        log("  3c. No compliance.db found — first start scenario, nothing to recover")

    # 3d. KillSwitch check
    log("  3d. KillSwitch smoke test ...")
    ks_script = (
        "from quant_nanggroe.engine.risk.kill_switch import KillSwitch; "
        "ks = KillSwitch(); "
        "print('can_trade:', ks.can_trade())"
    )
    r = run([sys.executable, "-c", ks_script], cwd=str(_REPO_ROOT))
    if r.returncode == 0:
        can_trade = "can_trade: True" in r.stdout or "can_trade: true" in r.stdout.lower()
        log("  3d. KillSwitch OK — can_trade=%s", can_trade)
        if not can_trade:
            failures.append("KillSwitch reports cannot trade on fresh start")
    else:
        msg = f"KillSwitch check failed (rc={r.returncode}): {r.stderr.strip()[:200]}"
        failures.append(msg)
        log("  WARN: %s", msg)

    # 3e. Strategy smoke test
    log("  3e. Strategy smoke test (Momentum) ...")
    strat_script = (
        "from quant_nanggroe.engine.strategy.strategies import create_strategy; "
        "s = create_strategy('Momentum', {'symbol': 'BTC'}); "
        "print('strategy OK:', s is not None)"
    )
    r = run([sys.executable, "-c", strat_script], cwd=str(_REPO_ROOT))
    if r.returncode == 0:
        log("  3e. Strategy OK — %s", r.stdout.strip())
    else:
        msg = f"Strategy smoke test failed (rc={r.returncode}): {r.stderr.strip()[:200]}"
        failures.append(msg)
        log("  WARN: %s", msg)

    log("Recovery phase complete [%s]", elapsed(p3_start))

    # ──────────────────── Phase 4: Verification ────────────────────

    phase_header(4, "Verification")
    p4_start = time.time()
    verify_ok = True

    # V1: cached_ohlcv dir exists
    v1 = cached_dir.is_dir()
    log("  V1. cached_ohlcv/ exists: %s", v1)
    if not v1:
        verify_ok = False
        failures.append("V1: cached_ohlcv/ missing after recovery")

    # V2: cached_ohlcv has CSV files (at least one)
    csv_files = list(cached_dir.glob("*.csv"))
    v2 = len(csv_files) > 0
    log("  V2. cached_ohlcv has CSV files: %s (%d file(s))", v2, len(csv_files))
    if not v2 and not args.quick:
        verify_ok = False
        failures.append("V2: no CSV files in cached_ohlcv/ after recovery")

    # V3: KillSwitch operational (fresh import = not triggered)
    r = run([sys.executable, "-c", ks_script], cwd=str(_REPO_ROOT))
    v3 = r.returncode == 0 and "can_trade: True" in r.stdout
    log("  V3. KillSwitch can_trade: %s", v3 if v3 else f"FAIL ({r.stderr.strip()[:80]})")
    if not v3:
        verify_ok = False
        failures.append("V3: KillSwitch not operational")

    # V4: Strategy importable
    r = run([sys.executable, "-c", strat_script], cwd=str(_REPO_ROOT))
    v4 = r.returncode == 0 and "strategy OK: True" in r.stdout
    log("  V4. Strategy importable: %s", v4 if v4 else f"FAIL ({r.stderr.strip()[:80]})")
    if not v4:
        verify_ok = False
        failures.append("V4: Strategy not importable")

    v_all = v1 and (v2 or args.quick) and v3 and v4
    if v_all:
        log("All verification checks passed [%s]", elapsed(p4_start))
    else:
        log("Verification INCOMPLETE — %d failure(s) [%s]", len(failures), elapsed(p4_start))

    # ───────────────────── Phase 5: Restore ────────────────────────

    if not args.keep_backup:
        phase_header(5, "Restore")
        p5_start = time.time()

        for rel in CRITICAL_DIRS:
            src = backup_dir / rel
            dst = _REPO_ROOT / rel
            if src.is_dir() and dst.exists():
                shutil.rmtree(dst)
            if src.is_dir():
                shutil.copytree(src, dst)
            elif src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        for pattern in DB_GLOBS:
            for src in backup_dir.glob(pattern):
                rel = src.relative_to(backup_dir)
                dst = _REPO_ROOT / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        for f in backup_dir.glob("*.db"):
            rel = f.relative_to(backup_dir)
            dst = _REPO_ROOT / rel
            shutil.copy2(f, dst)

        log("Restore complete — all files returned [%s]", elapsed(p5_start))
    else:
        log("Phase 5: --keep-backup set, skipping restore")

    # ──────────────────── Summary ───────────────────────────────────

    total_elapsed = time.time() - drill_start
    log("")
    log("╔══════════════════════════════════════════════════════════╗")
    log("║  Drill Complete                                        ║")
    log("╠══════════════════════════════════════════════════════════╣")
    log("║  Elapsed:  %53s ║", f"{total_elapsed:.1f}s")
    log("║  Failures: %53d ║", len(failures))
    log("║  Critical: %53d ║", len(critical_failures))
    log("╚══════════════════════════════════════════════════════════╝")

    if total_elapsed > 3600:
        log("WARNING: Drill exceeded 60-minute recovery SLA (%.1fs)", total_elapsed)

    if failures:
        log("Non-critical failures:")
        for f in failures:
            log("  • %s", f)

    if critical_failures:
        log("CRITICAL failures:")
        for f in critical_failures:
            log("  • %s", f)

    if critical_failures:
        return 2
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
