#!/usr/bin/env python3
"""FAZE 0.3b — Backfill attribution for 'unknown' trades using allocation evidence.

If only ONE strategy is admitted for a symbol's asset class, attribute
historical unknown trades on that symbol to that strategy.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import quant_nanggroe.engine.strategies  # noqa: F401
from quant_nanggroe.engine.strategy_allocation import admitted_for_symbol


def main():
    db_path = ROOT / "quant_nanggroe" / "data" / "qna_trade_journal.db"
    if not db_path.exists():
        print("journal not found")
        return

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    # Get all unknown-attribution trades grouped by symbol
    rows = con.execute(
        """SELECT DISTINCT symbol FROM trades
           WHERE strategy IN ('unknown', 'ensemble')"""
    ).fetchall()

    total_fixed = 0
    for row in rows:
        sym = row["symbol"]
        admitted = admitted_for_symbol(sym)
        if admitted is None or len(admitted) == 0:
            continue
        if len(admitted) > 1:
            # Multiple specialists — can't determine which one; skip
            continue
        # Only one specialist for this symbol -> attribute all unknowns
        strat = admitted[0]
        cur = con.execute(
            "UPDATE trades SET strategy=? WHERE symbol=? AND strategy IN ('unknown','ensemble')",
            (strat, sym))
        n = cur.rowcount
        if n > 0:
            print(f"  {sym}: attributed {n} trades -> {strat}")
            total_fixed += n

    con.commit()
    con.close()
    print(f"\nTotal fixed: {total_fixed}")

    # Post-fix stats
    con = sqlite3.connect(str(db_path))
    unknown = con.execute(
        "SELECT COUNT(*) FROM trades WHERE strategy IN ('unknown','ensemble')").fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    known = total - unknown
    print(f"Attribution: {known}/{total} known ({known/max(total,1):.0%}), "
          f"{unknown}/{total} still unknown")
    con.close()


if __name__ == "__main__":
    main()
