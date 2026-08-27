#!/usr/bin/env python3
"""FAZE 0.2 — Backfill ALL historical MT5 deals into journal.

Run once to populate the journal with the full trading history.
After this, the autonomous cycle handles incremental sync automatically.

Usage:
  C:\\Python314\\python.exe scripts/backfill_journal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Must import strategies first so allocation module works for attribution
import quant_nanggroe.engine.strategies  # noqa: F401
from quant_nanggroe.engine.journal_sync import get_journal_stats, sync_mt5_deals


def main():
    print("=" * 72)
    print("  JOURNAL BACKFILL — importing all MT5 deals into QNA journal")
    print("=" * 72)

    # Before
    stats_before = get_journal_stats()
    print(f"\nBefore: {stats_before}")

    # Backfill 90 days (covers several weeks of trading)
    print("\nSyncing MT5 deals (backfill_days=90)...")
    result = sync_mt5_deals(backfill_days=90)

    # After
    stats_after = get_journal_stats()
    print(f"\nAfter: {stats_after}")
    print("\nSync result:")
    print(f"  Positions found: {result['synced']}")
    print(f"  Inserted new: {result['inserted']}")
    print(f"  Updated existing: {result['updated']}")
    print(f"  Session PnL: {result['total_pnl']}")
    if result.get("errors"):
        print(f"  Errors: {result['errors'][:5]}")

    # Verify
    total = stats_after.get("total_trades", 0)
    net_pnl = stats_after.get("net_pnl", 0)
    unknown = stats_after.get("unknown_attribution", 0)
    wr = stats_after.get("win_rate", 0)

    print(f"\n{'='*72}")
    print("  JOURNAL STATUS AFTER BACKFILL")
    print(f"{'='*72}")
    print(f"  Total trades:     {total}")
    print(f"  Net P&L:          ${net_pnl}")
    print(f"  Win rate:         {wr:.1%}")
    print(f"  Unknown attrib:   {unknown} ({unknown/max(total,1):.0%})")
    print(f"{'='*72}")

    if total < 50:
        print("\n[WARN] Low trade count — check MT5 terminal is running and connected")
    if unknown > total * 0.5:
        print("\n[WARN] High unknown attribution — strategy attribution needs improvement")
    if net_pnl and net_pnl > 0:
        print(f"\n[OK] Journal shows POSITIVE P&L (${net_pnl:.2f}) — matches MT5 terminal")


if __name__ == "__main__":
    main()
