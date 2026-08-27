#!/usr/bin/env python3
"""Port Vibe-Trading factor library into Quant-Nanggroe-AI codebase.

Reads all factor .py files from Vibe-Trading source, transforms imports
and structure, and generates the merged module files.
"""

import re
from pathlib import Path

VIBE_ROOT = Path("/home/z/my-project/cluster1-sources/Vibe-Trading/agent/src/factors/zoo")
TARGET_ROOT = Path("/home/z/my-project/cluster1-dev/Quant-Nanggroe-AI/quant_nanggroe/engine/factors")


def extract_helpers(source: str) -> tuple[str, list[tuple[str, str]]]:
    """Extract helper functions from a factor source file.
    
    Returns (source_without_helpers, [(func_name, func_source), ...])
    """
    lines = source.split('\n')
    helpers = []
    cleaned_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        # Check if this line starts a helper function (def _name...)
        if re.match(r'^def _\w+\(', line):
            # Collect the entire function
            func_lines = [line]
            i += 1
            while i < len(lines):
                # Continue if line is indented or blank
                if lines[i].strip() == '' or lines[i].startswith(' ') or lines[i].startswith('\t'):
                    func_lines.append(lines[i])
                    i += 1
                else:
                    break
            # Extract function name
            match = re.match(r'^def (_\w+)\(', line)
            if match:
                func_name = match.group(1)
                func_source = '\n'.join(func_lines).rstrip()
                helpers.append((func_name, func_source))
            continue
        else:
            cleaned_lines.append(line)
            i += 1
    
    return '\n'.join(cleaned_lines), helpers


def transform_factor_source(source: str, stem: str) -> tuple[str, list[tuple[str, str]]]:
    """Transform a Vibe-Trading factor file to use unique names and correct imports.

    Returns (transformed_source, [(helper_name, helper_source), ...])
    """
    lines = source.split('\n')
    out_lines = []

    # We'll skip the module docstring, the from __future__ import, and the 
    # from src.factors.base import block. We keep everything else.
    
    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip module docstring (at the very top)
        if i == 0 and (line.startswith('"""') or line.startswith("'''")):
            delim = line[:3]
            if line.strip().endswith(delim) and len(line.strip()) > 6:
                # Single-line docstring
                i += 1
                continue
            else:
                # Multi-line docstring
                i += 1
                while i < len(lines):
                    if delim in lines[i]:
                        i += 1
                        break
                    i += 1
                continue

        # Skip from __future__ import
        if line.startswith('from __future__'):
            i += 1
            continue

        # Skip import numpy/pandas (we import these at module level)
        if line.startswith('import numpy') or line.startswith('import pandas'):
            i += 1
            continue

        # Skip the entire from src.factors.base import block
        # (including the closing parenthesis which may not be indented)
        if line.startswith('from src.factors.base import'):
            i += 1
            # Skip indented continuation lines
            while i < len(lines) and (lines[i].startswith('    ') or lines[i].startswith('\t')):
                i += 1
            # Skip the closing ')' if present
            if i < len(lines) and lines[i].strip() == ')':
                i += 1
            continue

        # Skip ALPHA_ID = ... lines
        if line.startswith('ALPHA_ID'):
            i += 1
            continue

        # Rename __alpha_meta__ to __alpha_meta_{stem}
        if line.strip().startswith('__alpha_meta__'):
            line = line.replace('__alpha_meta__', f'__alpha_meta_{stem}', 1)

        # Rename def compute( to def compute_{stem}(
        if line.strip().startswith('def compute(') or line.strip().startswith('def compute ('):
            line = line.replace('def compute(', f'def compute_{stem}(', 1)
            line = line.replace('def compute (', f'def compute_{stem}(', 1)

        # Remove "from src.factors.base import" that might appear in compute functions
        if 'from src.factors.base import' in line:
            i += 1
            continue

        out_lines.append(line)
        i += 1

    # Clean up leading/trailing blank lines
    while out_lines and out_lines[0].strip() == '':
        out_lines.pop(0)
    while out_lines and out_lines[-1].strip() == '':
        out_lines.pop()

    transformed = '\n'.join(out_lines)
    
    # Extract helper functions and remove them from the transformed source
    transformed, helpers = extract_helpers(transformed)
    
    # Clean up again
    lines2 = transformed.split('\n')
    while lines2 and lines2[0].strip() == '':
        lines2.pop(0)
    while lines2 and lines2[-1].strip() == '':
        lines2.pop()
    transformed = '\n'.join(lines2)

    return transformed, helpers


def collect_and_transform_factors(zoo_name: str) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Collect all factors from a Vibe-Trading zoo directory.

    Returns ([(stem, transformed_source), ...], {helper_name: helper_source})
    """
    zoo_dir = VIBE_ROOT / zoo_name
    if not zoo_dir.is_dir():
        print(f"  WARNING: {zoo_dir} not found")
        return [], {}

    factors = []
    all_helpers = {}  # name -> source (first occurrence wins)
    
    for py_file in sorted(zoo_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        source = py_file.read_text(encoding="utf-8")
        transformed, helpers = transform_factor_source(source, py_file.stem)
        factors.append((py_file.stem, transformed))
        
        # Deduplicate helpers by name (keep first occurrence)
        for name, src in helpers:
            if name not in all_helpers:
                all_helpers[name] = src

    return factors, all_helpers


def generate_module(
    zoo_name: str,
    zoo_title: str,
    description: str,
    factors: list[tuple[str, str]],
    helpers: dict[str, str],
    extra_helpers: str = "",
) -> str:
    """Generate a module file from a list of transformed factor sources."""

    header = f'''"""{zoo_title}.

{description}
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_nanggroe.engine.factors.base import (
    decay_linear,
    delta,
    rank,
    safe_div,
    scale,
    signed_power,
    ts_argmax,
    ts_argmin,
    ts_corr,
    ts_cov,
    ts_max,
    ts_mean,
    ts_min,
    ts_rank,
    ts_std,
    vwap,
)

'''

    # Build the body
    body_parts = []

    # Add deduplicated helper functions at the top
    if helpers:
        body_parts.append("# ─── Shared Helper Functions ────────────────────────────────────────────")
        body_parts.append("")
        for name in sorted(helpers.keys()):
            body_parts.append(helpers[name])
            body_parts.append("")
            body_parts.append("")

    if extra_helpers:
        body_parts.append(extra_helpers)
        body_parts.append("")

    # Add each factor
    factor_stems = []
    for stem, transformed in factors:
        body_parts.append(transformed)
        body_parts.append("")
        body_parts.append("")
        factor_stems.append(stem)

    # Add the get_all function
    get_all_lines = [
        f"def get_all_{zoo_name}_factors() -> list:",
        f'    """Return list of (meta_dict, compute_fn) tuples for all {zoo_title} factors."""',
        "    return [",
    ]
    for stem in factor_stems:
        get_all_lines.append(f"        (__alpha_meta_{stem}, compute_{stem}),")
    get_all_lines.extend([
        "    ]",
        "",
    ])

    body = "\n".join(body_parts)
    get_all = "\n".join(get_all_lines)

    return header + body + get_all


def main():
    print("=" * 60)
    print("Porting Vibe-Trading factors to Quant-Nanggroe-AI")
    print("=" * 60)

    # 1. Collect all alpha101 factors
    print("\n[1/4] Collecting alpha101 factors...")
    alpha101_factors, alpha101_helpers = collect_and_transform_factors("alpha101")
    print(f"  Found {len(alpha101_factors)} alpha101 factors, {len(alpha101_helpers)} unique helpers")

    # 2. Collect all gtja191 factors
    print("\n[2/4] Collecting gtja191 factors...")
    gtja191_factors, gtja191_helpers = collect_and_transform_factors("gtja191")
    print(f"  Found {len(gtja191_factors)} gtja191 factors, {len(gtja191_helpers)} unique helpers")

    # 3. Collect all qlib158 factors
    print("\n[3/4] Collecting qlib158 factors...")
    qlib158_factors, qlib158_helpers = collect_and_transform_factors("qlib158")
    print(f"  Found {len(qlib158_factors)} qlib158 factors, {len(qlib158_helpers)} unique helpers")

    # 4. Collect all academic factors
    print("\n[4/4] Collecting academic factors...")
    academic_factors, academic_helpers = collect_and_transform_factors("academic")
    print(f"  Found {len(academic_factors)} academic factors, {len(academic_helpers)} unique helpers")

    # Generate alpha101.py
    print("\nGenerating alpha101.py...")
    alpha101_content = generate_module(
        zoo_name="alpha101",
        zoo_title="WorldQuant 101 Alphas (Kakushadze 2015)",
        description=(
            "Implements ALL 101 alphas from:\n"
            '"101 Formulaic Alphas" by Zura Kakushadze, arXiv:1601.00991\n\n'
            "Each alpha uses the __alpha_meta__ + compute(panel) pattern.\n"
            "Adapted to use Quant-Nanggroe-AI base.py operators.\n\n"
            "Reference: https://arxiv.org/abs/1601.00991"
        ),
        factors=alpha101_factors,
        helpers=alpha101_helpers,
    )
    (TARGET_ROOT / "alpha101.py").write_text(alpha101_content, encoding="utf-8")
    print(f"  Written: alpha101.py ({len(alpha101_content)} bytes)")

    # Generate gtja191.py
    print("\nGenerating gtja191.py...")
    gtja191_content = generate_module(
        zoo_name="gtja191",
        zoo_title="Guotai Junan 191 Alphas",
        description=(
            "Implements ALL 191 alphas from the Guotai Junan 191 Alpha research report (2014).\n\n"
            "These alphas focus on Chinese A-share market characteristics including:\n"
            "- Volume-price dynamics\n"
            "- Intraday return patterns\n"
            "- Cross-sectional momentum/reversal\n\n"
            "Reference: 国泰君安 191 alpha 研报 (2014)"
        ),
        factors=gtja191_factors,
        helpers=gtja191_helpers,
    )
    (TARGET_ROOT / "gtja191.py").write_text(gtja191_content, encoding="utf-8")
    print(f"  Written: gtja191.py ({len(gtja191_content)} bytes)")

    # Generate qlib158.py
    print("\nGenerating qlib158.py...")
    qlib158_content = generate_module(
        zoo_name="qlib158",
        zoo_title="Qlib 158 Alpha Factors",
        description=(
            "Implements 154 Qlib alpha factors from Microsoft Qlib.\n\n"
            "Adapted from microsoft/qlib:qlib/contrib/data/handler.py (Apache-2.0).\n"
            "Copyright (c) Microsoft Corporation.\n\n"
            "Each factor uses the __alpha_meta__ + compute(panel) pattern."
        ),
        factors=qlib158_factors,
        helpers=qlib158_helpers,
    )
    (TARGET_ROOT / "qlib158.py").write_text(qlib158_content, encoding="utf-8")
    print(f"  Written: qlib158.py ({len(qlib158_content)} bytes)")

    # Generate academic.py
    print("\nGenerating academic.py...")
    academic_content = generate_module(
        zoo_name="academic",
        zoo_title="Academic Alpha Factors (Fama-French, Carhart)",
        description=(
            "Implements 6 academic alpha factors based on classic asset pricing models.\n\n"
            "Fama-French 3-factor model (1993):\n"
            "- MKT_RF: Market factor (21-day return z-score)\n"
            "- SMB: Size factor (inverse dollar-volume z-score)\n"
            "- HML: Value factor (inverse 252-day return z-score)\n\n"
            "Fama-French 5-factor model (2015):\n"
            "- RMW: Profitability factor (inverse volatility z-score)\n"
            "- CMA: Investment factor (inverse volume growth z-score)\n\n"
            "Carhart 4-factor model (1997):\n"
            "- CARHART_MOM: Momentum factor (12m-1m return z-score)\n\n"
            "All factors use price-based proxies when fundamental data is unavailable."
        ),
        factors=academic_factors,
        helpers=academic_helpers,
        extra_helpers="""def _cross_sectional_zscore(df: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Per-row z-score: (x - row_mean) / row_std; zero/NaN std rows -> NaN.\"\"\"
    mean = df.mean(axis=1, skipna=True)
    std = df.std(axis=1, ddof=1, skipna=True)
    centered = df.sub(mean, axis=0)
    result = centered.div(std.where(std > 0), axis=0)
    return result.replace([np.inf, -np.inf], np.nan)

""",
    )
    (TARGET_ROOT / "academic.py").write_text(academic_content, encoding="utf-8")
    print(f"  Written: academic.py ({len(academic_content)} bytes)")

    total = len(alpha101_factors) + len(gtja191_factors) + len(qlib158_factors) + len(academic_factors)
    print(f"\n{'=' * 60}")
    print(f"Total factors ported: {total}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
