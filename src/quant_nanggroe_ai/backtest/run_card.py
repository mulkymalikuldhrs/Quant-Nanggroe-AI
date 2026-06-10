"""Run Card — Trust Layer artifact for backtest provenance.

Writes a JSON run-card alongside backtest artifacts to capture:
  - data sources used
  - strategy code hash
  - key metric snapshot
  - reproducibility metadata
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def write_run_card(
    run_dir: Path,
    config: Dict[str, Any],
    metrics: Dict[str, Any],
    data_sources: Optional[List[str]] = None,
    strategy_path: Optional[Path] = None,
) -> Path:
    """Write a run-card JSON file to the artifacts directory.

    Args:
        run_dir: Root directory for the backtest run.
        config: Backtest configuration dict.
        metrics: Metrics dict produced by calc_metrics.
        data_sources: Names of data sources used.
        strategy_path: Path to the signal engine source file.

    Returns:
        Path to the written run-card JSON file.
    """
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    run_card: Dict[str, Any] = {
        "run_card_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_sources": data_sources or [],
        "config_snapshot": {
            k: v for k, v in config.items()
            if isinstance(v, (str, int, float, bool, list))
        },
        "metrics_snapshot": {
            k: v for k, v in metrics.items()
            if isinstance(v, (str, int, float, bool))
        },
    }

    if strategy_path and strategy_path.exists():
        import hashlib
        content = strategy_path.read_bytes()
        run_card["strategy_hash"] = hashlib.sha256(content).hexdigest()

    card_path = artifacts_dir / "run_card.json"
    card_path.write_text(json.dumps(run_card, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Run card written to %s", card_path)
    return card_path
