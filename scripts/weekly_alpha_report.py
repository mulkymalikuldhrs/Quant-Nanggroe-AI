#!/usr/bin/env python3
"""Weekly Alpha Report Generator — Quant Nanggroe AI.

Reads paper_state/pnl.csv, computes performance metrics,
and generates a markdown report to docs/ALPHA_REPORT_YYYY-MM-DD.md.

Requires 30+ days of daily data for full alpha analysis.
"""

import csv
import math
import os
import subprocess
import sys
from datetime import date, datetime

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNL_PATH = os.path.join(_REPO_ROOT, "paper_state", "pnl.csv")
REPORT_DIR = os.path.join(_REPO_ROOT, "docs")
MIN_DAYS = 30


def read_pnl(path: str) -> list[tuple[date, float]]:
    """Read PnL CSV, return sorted list of (date, total_value)."""
    if not os.path.isfile(path):
        return []
    daily: dict[date, float] = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row.get("timestamp", "")
            tv = row.get("total_value", "")
            if not ts or not tv:
                continue
            try:
                d = datetime.fromisoformat(ts).date()
                val = float(tv)
            except (ValueError, TypeError):
                continue
            daily[d] = val  # keep last value per day
    return sorted(daily.items())


def compute_metrics(daily: list[tuple[date, float]]) -> dict:
    """Compute performance metrics from daily (date, total_value) pairs."""
    n = len(daily)
    start_val = daily[0][1]
    end_val = daily[-1][1]
    total_return = (end_val - start_val) / start_val if start_val else 0.0

    dr = []
    for i in range(1, n):
        prev = daily[i - 1][1]
        cur = daily[i][1]
        dr.append((cur - prev) / prev if prev else 0.0)

    mean_ret = sum(dr) / len(dr) if dr else 0.0
    variance = sum((r - mean_ret) ** 2 for r in dr) / len(dr) if dr else 0.0
    std = math.sqrt(variance)

    sharpe = (mean_ret / std * math.sqrt(252)) if std > 0 else 0.0

    peak = start_val
    max_dd = 0.0
    cum = start_val
    for r in dr:
        cum *= 1 + r
        if cum > peak:
            peak = cum
        dd = (peak - cum) / peak if peak else 0.0
        if dd > max_dd:
            max_dd = dd

    wins = sum(1 for r in dr if r > 0)
    win_rate = wins / len(dr) if dr else 0.0

    return {
        "n_days": n,
        "start_date": daily[0][0],
        "end_date": daily[-1][0],
        "start_value": start_val,
        "end_value": end_val,
        "total_return": total_return,
        "annualized_sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
    }


def run_alpha_destruction() -> str:
    """Run alpha_destruction.py via subprocess, return output."""
    script = os.path.join(_REPO_ROOT, "scripts", "alpha_destruction.py")
    if not os.path.isfile(script):
        return "  SKIP: scripts/alpha_destruction.py not found"
    try:
        result = subprocess.run(
            [sys.executable, script, "--n", "500", "--export",
             os.path.join(REPORT_DIR, "alpha_report.json")],
            capture_output=True, text=True, timeout=120,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"  ERROR: alpha_destruction failed: {e}"


def run_factor_regression() -> str:
    """Run factor_regression.py if importable, return results."""
    script = os.path.join(_REPO_ROOT, "scripts", "factor_regression.py")
    if not os.path.isfile(script):
        return "  SKIP: scripts/factor_regression.py not found"
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("factor_regression", script)
        if spec is None or spec.loader is None:
            return "  SKIP: factor_regression not importable"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return f"  SKIP: factor_regression import failed ({e})"

    pnl_csv = os.path.join(_REPO_ROOT, "data", "daily_pnl.csv")
    factors_csv = os.path.join(_REPO_ROOT, "data", "daily_factors.csv")

    missing = [p for p in [pnl_csv, factors_csv] if not os.path.isfile(p)]
    if missing:
        return f"  SKIP: missing data files: {missing}"

    try:
        result = subprocess.run(
            [sys.executable, script, "--pnl", pnl_csv, "--factors", factors_csv],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"  ERROR: factor_regression failed: {e}"


def generate_report(metrics: dict, extra: str) -> str:
    """Generate markdown report content."""
    lines = []
    lines.append(f"# Weekly Alpha Report — {metrics['end_date']}")
    lines.append("")
    lines.append(f"**Generated:** {date.today()}")
    lines.append(f"**Period:** {metrics['start_date']} → {metrics['end_date']} ({metrics['n_days']} trading days)")
    lines.append(f"**Data source:** `paper_state/pnl.csv`")
    lines.append("")
    lines.append("## Performance Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Total Return | {metrics['total_return']:.4%} |")
    lines.append(f"| Annualized Sharpe | {metrics['annualized_sharpe']:.4f} |")
    lines.append(f"| Max Drawdown | {metrics['max_drawdown']:.4%} |")
    lines.append(f"| Win Rate (daily) | {metrics['win_rate']:.4%} |")
    lines.append(f"| Start Value | ${metrics['start_value']:.2f} |")
    lines.append(f"| End Value | ${metrics['end_value']:.2f} |")
    lines.append("")
    lines.append("## Alpha Analysis")
    lines.append("")
    if extra:
        lines.append("```")
        lines.append(extra.rstrip())
        lines.append("```")
    else:
        lines.append("*Alpha destruction and factor regression completed with no additional output.*")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    daily = read_pnl(PNL_PATH)

    if len(daily) < MIN_DAYS:
        plural = "s" if len(daily) != 1 else ""
        print(f"Only {len(daily)} day{plural} collected. Need {MIN_DAYS} for alpha analysis.")
        return

    print(f"OK — {len(daily)} trading days collected (≥ {MIN_DAYS}). Generating report...")

    metrics = compute_metrics(daily)
    metrics["total_return"] = round(metrics["total_return"], 6)

    extra_parts = []
    print("  Running alpha destruction...")
    out = run_alpha_destruction()
    extra_parts.append("=== Alpha Destruction ===")
    extra_parts.append(out)

    print("  Running factor regression...")
    out = run_factor_regression()
    extra_parts.append("=== Factor Regression ===")
    extra_parts.append(out)

    extra = "\n".join(extra_parts)
    report = generate_report(metrics, extra)

    report_path = os.path.join(REPORT_DIR, f"ALPHA_REPORT_{metrics['end_date']}.md")
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)

    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
