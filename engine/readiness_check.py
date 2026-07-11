"""Production readiness checker – evaluates whether all required modules are present and assigns a score out of 100.

The checker scans for the presence of core engine components, the self‑prompting pipeline, and the Ponytail‑enabled council.
Missing components are reported and a simple completeness metric is computed.
"""

import os
from pathlib import Path

REQUIRED_FILES = [
    "engine/fetch_backtest_data.py",
    "engine/run_walkforward.py",
    "engine/generate_alpha_report.py",
    "engine/get_gas_price.py",
    "engine/token_metabolism.py",
    "engine/quantum.py",
    "engine/swarm.py",
    "engine/prompter.py",
    "engine/readiness_check.py",
    "scripts/fetch_backtest_data.py",
    "scripts/run_walkforward.py",
    "scripts/generate_alpha_report.py",
    "scripts/get_gas_price.py",
    "scripts/ponytail.py",
]

def check_readiness(root: Path = Path('.')) -> dict:
    total = len(REQUIRED_FILES)
    present = 0
    missing = []
    for rel in REQUIRED_FILES:
        if (root / rel).exists():
            present += 1
        else:
            missing.append(rel)
    score = int((present / total) * 100)
    return {
        "total_required": total,
        "present": present,
        "missing": missing,
        "score": score,
    }

if __name__ == "__main__":
    root = Path(__file__).parent.parent
    result = check_readiness(root)
    print(f"Production readiness: {result['score']}/100")
    if result['missing']:
        print("Missing components:")
        for m in result['missing']:
            print(f" - {m}")
    else:
        print("All components present. Ready for production!")
