#!/usr/bin/env python3
"""qna-warehouse-query.py — CLI query tool for the Parquet data warehouse.

Usage:
    python3 scripts/qna-warehouse-query.py --list-tables
    python3 scripts/qna-warehouse-query.py --query cycles --last 10
    python3 scripts/qna-warehouse-query.py --query cycles --since 2024-06-01
    python3 scripts/qna-warehouse-query.py --summary
"""

import argparse
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from quant_nanggroe.data.warehouse import DataWarehouse


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="qna-warehouse-query",
        description="Query the Parquet data warehouse for paper run data",
    )
    p.add_argument("--state-dir", default=None,
                   help="State directory containing warehouse/ (default: ./paper_state)")
    p.add_argument("--list-tables", action="store_true", help="Show available tables with row counts")
    p.add_argument("--query", metavar="TABLE", default=None,
                   help="Query a table: cycles|attribution|metrics|regimes|positions")
    p.add_argument("--last", type=int, default=None, help="Show last N rows")
    p.add_argument("--since", default=None, help="Filter by start date (ISO format)")
    p.add_argument("--until", default=None, help="Filter by end date (ISO format)")
    p.add_argument("--symbols", nargs="+", default=None, help="Filter by symbols (for attribution/positions)")
    p.add_argument("--summary", action="store_true", help="Show summary stats")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    state_dir = Path(args.state_dir or "paper_state")
    wh = DataWarehouse(state_dir)

    if args.list_tables:
        s = wh.summary()
        print(f"{'Table':<20} {'Rows':<8} {'Start':<28} {'End':<28} {'Size':<10}")
        print("-" * 94)
        for table, info in s.items():
            rows = info.get("rows", 0)
            start = info.get("start") or "-"
            end = info.get("end") or "-"
            size = info.get("size_bytes", 0)
            print(f"{table:<20} {rows:<8} {start:<28} {end:<28} {size:<10}")
        return

    if args.query:
        df = wh.query(args.query, start_date=args.since, end_date=args.until, symbols=args.symbols)
        if df.empty:
            print(f"Table '{args.query}' is empty or does not exist.")
            return
        if args.last is not None:
            df = df.tail(args.last)
        df.to_csv(sys.stdout, index=False)
        return

    if args.summary:
        s = wh.summary()
        for table, info in s.items():
            rows = info.get("rows", 0)
            start = info.get("start") or "-"
            end = info.get("end") or "-"
            size = info.get("size_bytes", 0)
            print(f"{table}: {rows} rows ({start} to {end}), {size} bytes")
        total = sum(v.get("rows", 0) for v in s.values())
        print(f"\nTotal rows across all tables: {total}")
        return

    print("No action specified. Use --list-tables, --query TABLE, or --summary")


if __name__ == "__main__":
    main()
