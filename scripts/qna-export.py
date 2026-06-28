#!/usr/bin/env python3
"""qna-export.py — CSV export for paper run data.

Usage:
    python3 scripts/qna-export.py --state-dir /root/paper_runs/qna-paper-run-001 --output /tmp/export.csv
    python3 scripts/qna-export.py --state-dir ... --table pnl --last 100
    python3 scripts/qna-export.py --state-dir ... --table attribution --since 2026-06-01
    python3 scripts/qna-export.py --state-dir ... --table all --format zip
    python3 scripts/qna-export.py --state-dir ... --list-tables
"""

import argparse
import csv
import io
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="qna-export",
        description="Export paper run data as CSV",
    )
    p.add_argument("--state-dir", default=None,
                   help="Paper run state directory (default: ./paper_state)")
    p.add_argument("--output", default=None,
                   help="Output path (default: stdout)")
    p.add_argument("--table", default=None,
                   help="Table to export: pnl|attribution|metrics|regimes|audit|state|all")
    p.add_argument("--list-tables", action="store_true",
                   help="Show available tables with row counts")
    p.add_argument("--last", type=int, default=None,
                   help="Export last N rows")
    p.add_argument("--since", default=None,
                   help="Filter rows after this timestamp (ISO format)")
    p.add_argument("--format", choices=["csv", "zip"], default="csv",
                   help="Output format (default: csv)")
    return p.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def flatten(d: dict, prefix: str = "") -> dict[str, str]:
    out = {}
    for k, v in d.items():
        key = f"{prefix}_{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        elif isinstance(v, list):
            out[key] = json.dumps(v)
        else:
            out[key] = str(v) if v is not None else ""
    return out


def apply_filters(
    rows: list[dict[str, Any]],
    last: int | None,
    since: str | None,
    ts_col: str = "timestamp",
) -> list[dict[str, Any]]:
    if since and ts_col:
        rows = [r for r in rows if str(r.get(ts_col, "")) >= since]
    if last is not None and last > 0:
        rows = rows[-last:]
    return rows


def write_csv(rows: list[dict[str, Any]], output: Path | None) -> str | None:
    if not rows:
        return None
    fieldnames = sorted({k for r in rows for k in r})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
    content = buf.getvalue()
    if output:
        output.write_text(content)
    return content


def table_pnl(state_dir: Path, last: int | None, since: str | None) -> list[dict[str, Any]]:
    path = state_dir / "pnl.csv"
    if not path.exists():
        return []
    rows = read_csv(path)
    return apply_filters(rows, last, since)


def table_attribution(state_dir: Path, last: int | None, since: str | None) -> list[dict[str, Any]]:
    path = state_dir / "pnl_attribution.csv"
    if not path.exists():
        return []
    rows = read_csv(path)
    return apply_filters(rows, last, since)


def table_metrics(state_dir: Path, last: int | None, since: str | None) -> list[dict[str, Any]]:
    path = state_dir / "metrics.jsonl"
    if not path.exists():
        return []
    rows = read_jsonl(path)
    rows = apply_filters(rows, last, since)
    return rows


def table_regimes(state_dir: Path, last: int | None, since: str | None) -> list[dict[str, Any]]:
    path = state_dir / "regime_state.json"
    if not path.exists():
        return []
    data = read_json(path)
    row = flatten(data)
    rows = [row]
    return apply_filters(rows, last, since)


def table_audit(state_dir: Path, last: int | None, since: str | None) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(state_dir.glob("audit_*.json")):
        data = read_json(path)
        entries = data.get("entries", [])
        for e in entries:
            e_flat = flatten(e)
            e_flat["_source"] = path.name
            rows.append(e_flat)
    rows.sort(key=lambda r: r.get("timestamp", ""))
    return apply_filters(rows, last, since)


def table_state(state_dir: Path, last: int | None, since: str | None) -> list[dict[str, Any]]:
    path = state_dir / "state.json"
    if not path.exists():
        return []
    data = read_json(path)
    row = flatten(data)
    if since:
        ts = row.get("timestamp", "")
        if ts < since:
            return []
    rows = [row]
    return apply_filters(rows, last, since)


def table_warehouse(state_dir: Path, table: str) -> list[dict[str, Any]]:
    parquet_path = state_dir / "warehouse" / f"{table}.parquet"
    if not parquet_path.exists():
        return []
    try:
        import pandas as pd
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from quant_nanggroe.data.warehouse import _read_parquet
        df = _read_parquet(parquet_path)
        if df.empty:
            return []
        return df.to_dict("records")
    except Exception:
        return []


AVAILABLE_TABLES: dict[str, str] = {
    "pnl": "pnl.csv",
    "attribution": "pnl_attribution.csv",
    "metrics": "metrics.jsonl",
    "regimes": "regime_state.json",
    "audit": "audit_*.json",
    "state": "state.json",
}

TABLE_FUNCS = {
    "pnl": table_pnl,
    "attribution": table_attribution,
    "metrics": table_metrics,
    "regimes": table_regimes,
    "audit": table_audit,
    "state": table_state,
}


def get_row_count(state_dir: Path, table: str) -> int:
    func = TABLE_FUNCS.get(table)
    if not func:
        return 0
    rows = func(state_dir, None, None)
    if not rows and table in ("cycles", "attribution", "metrics", "regimes", "positions"):
        rows = table_warehouse(state_dir, table)
    return len(rows)


def main() -> None:
    args = parse_args()
    state_dir = Path(args.state_dir or "paper_state")
    if not state_dir.exists():
        print(f"State directory not found: {state_dir}", file=sys.stderr)
        sys.exit(1)

    if args.list_tables:
        print(f"{'Table':<20} {'Rows':<8} {'Source'}")
        print("-" * 50)
        for name, source in AVAILABLE_TABLES.items():
            is_glob = "*" in source
            if is_glob:
                files = list(state_dir.glob(source))
                if files:
                    func = TABLE_FUNCS.get(name)
                    count = len(func(state_dir, None, None)) if func else 0
                    print(f"{name:<20} {count:<8} {source}")
                else:
                    print(f"{name:<20} {'-':<8} {source} (not found)")
            else:
                path = state_dir / source
                if path.exists():
                    rows = get_row_count(state_dir, name)
                    print(f"{name:<20} {rows:<8} {source}")
                else:
                    print(f"{name:<20} {'-':<8} {source} (not found)")
        return

    table = args.table or "pnl"
    output = Path(args.output) if args.output else None

    if table == "all":
        all_data: dict[str, list[dict[str, Any]]] = {}
        for name in AVAILABLE_TABLES:
            func = TABLE_FUNCS.get(name)
            if func:
                rows = func(state_dir, args.last, args.since)
                if not rows:
                    rows = table_warehouse(state_dir, name)
                if rows:
                    all_data[name] = rows

        if args.format == "zip" or (output and output.suffix == ".zip"):
            zip_path = output or Path("export.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, rows in all_data.items():
                    if not rows:
                        continue
                    fieldnames = sorted({k for r in rows for k in r})
                    buf = io.StringIO()
                    w = csv.DictWriter(buf, fieldnames=fieldnames)
                    w.writeheader()
                    w.writerows(rows)
                    zf.writestr(f"{name}.csv", buf.getvalue())
            print(f"Exported {len(all_data)} tables to {zip_path}")
            return
        else:
            for name, rows in all_data.items():
                if rows:
                    csv_content = write_csv(rows, None)
                    if csv_content:
                        print(f"--- {name} ---")
                        print(csv_content, end="")
            return

    func = TABLE_FUNCS.get(table)
    if func:
        rows = func(state_dir, args.last, args.since)
        if not rows:
            rows = table_warehouse(state_dir, table)
    else:
        rows = table_warehouse(state_dir, table)

    if not rows:
        print(f"Table '{table}' is empty or does not exist.", file=sys.stderr)
        sys.exit(1)

    csv_content = write_csv(rows, output)
    if csv_content and not output:
        print(csv_content, end="")


if __name__ == "__main__":
    main()
