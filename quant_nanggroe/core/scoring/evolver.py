"""Self-evolve loop (weight tuner) for the Quant-Nanggroe-AI scoring engine.

Closed trade → journal (score snapshot + PnL) → evaluator → weight adjustment.
Pattern from Rencana.md: after N trades, compute per-scorer Sharpe, adjust
weights max ±5%/cycle, safety ceiling 20% from original, circuit breaker at 50.

CANONICAL Weight Tuner. WeightUpdater in engine/evolution/ is SECONDARY —
it updates SignalTracker (provider weights) not FusionEngine (scorer weights).
Both systems coexist: WeightEvolver handles scorer weights, WeightUpdater
handles provider weights. No conflict by design.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from quant_nanggroe.core.scoring.base import BaseScorer, _clamp

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_RAW_SCORER_WEIGHTS: dict[str, float] = {
    "BondScorer": 0.10,
    "EconomicScorer": 0.20,
    "GeopoliticalScorer": 0.05,
    "MacroScorer": 0.30,
    "PositioningScorer": 0.10,
    "SentimentScorer": 0.10,
    "TechnicalScorer": 0.10,
    "VolatilityScorer": 0.05,
    "CryptoScorer": 0.08,
    "NewsScorer": 0.02,
}
_NORMALIZER = 1.0 / sum(_RAW_SCORER_WEIGHTS.values())
DEFAULT_SCORER_WEIGHTS: dict[str, float] = {
    k: v * _NORMALIZER for k, v in _RAW_SCORER_WEIGHTS.items()
}

assert abs(sum(DEFAULT_SCORER_WEIGHTS.values()) - 1.0) < 0.001, \
    f"Scorer weights must sum to 1.0, got {sum(DEFAULT_SCORER_WEIGHTS.values())}"

EVOLVE_EVERY_N_TRADES = 20
MAX_ADJUSTMENT_PCT = 0.05
MAX_TOTAL_SHIFT_PCT = 0.20
CIRCUIT_BREAKER_TRADES = 50


@dataclass
class ScoreJournalEntry:
    trade_id: str
    timestamp: str
    symbol: str
    scorer_scores: dict[str, dict[str, float]]
    actual_pnl: float
    predicted_bias: str


class ScoreJournal:
    def __init__(self, path: Optional[str] = None):
        self.path = Path(path) if path else DATA_DIR / "scorer_journal.json"
        self.entries: list[ScoreJournalEntry] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            self.entries = [ScoreJournalEntry(**e) for e in data.get("entries", [])]
        except (json.JSONDecodeError, KeyError, TypeError):
            self.entries = []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(
            {"entries": [asdict(e) for e in self.entries]}, indent=2
        ))

    def record(self, trade_id: str, symbol: str, scorer_scores: dict[str, dict[str, float]],
               actual_pnl: float, predicted_bias: str):
        self.entries.append(ScoreJournalEntry(
            trade_id=trade_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            scorer_scores=scorer_scores,
            actual_pnl=actual_pnl,
            predicted_bias=predicted_bias,
        ))
        self._save()

    def last_n(self, n: int) -> list[ScoreJournalEntry]:
        return self.entries[-n:]

    def __len__(self) -> int:
        return len(self.entries)


class WeightEvolver:
    def __init__(
        self,
        default_weights: Optional[dict[str, float]] = None,
        journal: Optional[ScoreJournal] = None,
        weights_path: Optional[str] = None,
        evolve_every: int = EVOLVE_EVERY_N_TRADES,
        max_adj_pct: float = MAX_ADJUSTMENT_PCT,
        max_total_shift_pct: float = MAX_TOTAL_SHIFT_PCT,
        circuit_breaker_trades: int = CIRCUIT_BREAKER_TRADES,
    ):
        self.default_weights = dict(default_weights or DEFAULT_SCORER_WEIGHTS)
        self.weights_path = Path(weights_path) if weights_path else DATA_DIR / "scorer_weights.json"
        self.current_weights: dict[str, float] = dict(self.default_weights)
        self.journal = journal or ScoreJournal()
        self.evolve_every = evolve_every
        self.max_adj_pct = max_adj_pct
        self.max_total_shift_pct = max_total_shift_pct
        self.circuit_breaker_trades = circuit_breaker_trades
        self._last_eval_idx = 0
        self._load_weights()

    def _load_weights(self):
        if not self.weights_path.exists():
            return
        try:
            data = json.loads(self.weights_path.read_text())
            loaded = data.get("weights", {})
            if loaded and all(k in self.default_weights for k in loaded):
                self.current_weights.update(loaded)
                self._last_eval_idx = data.get("last_eval_idx", 0)
                logger.info("WeightEvolver: loaded weights from %s", self.weights_path)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    def _save_weights(self):
        self.weights_path.parent.mkdir(parents=True, exist_ok=True)
        self.weights_path.write_text(json.dumps({
            "weights": self.current_weights,
            "last_eval_idx": self._last_eval_idx,
            "updated": datetime.now(timezone.utc).isoformat(),
        }, indent=2))

    def record_trade(self, trade_id: str, symbol: str,
                     scorer_scores: dict[str, dict[str, float]],
                     actual_pnl: float, predicted_bias: str):
        self.journal.record(trade_id, symbol, scorer_scores, actual_pnl, predicted_bias)

    def _compute_scorer_alignment(self, window: int = EVOLVE_EVERY_N_TRADES) -> dict[str, float]:
        """Sharpe-like alignment score per scorer over last N trades.

        For each trade: scorer prediction aligned with PnL → +confidence,
        misaligned → -confidence, neutral → 0.
        Returns {scorer_name: alignment_sharpe}.
        """
        recent = self.journal.last_n(window)
        if not recent:
            return {}

        scorer_hits: dict[str, list[float]] = {}

        for entry in recent:
            pnl = entry.actual_pnl
            pnl_direction = 1 if pnl > 0 else (-1 if pnl < 0 else 0)

            for name, scores in entry.scorer_scores.items():
                if name not in scorer_hits:
                    scorer_hits[name] = []

                score_val = scores.get("score", 0.0)
                conf = scores.get("confidence", 0.0)

                pred = 1 if score_val > 5 else (-1 if score_val < -5 else 0)

                if pred == 0 or pnl_direction == 0:
                    hit = 0.0
                elif pred == pnl_direction:
                    hit = conf
                else:
                    hit = -conf

                scorer_hits[name].append(hit)

        alignment: dict[str, float] = {}
        for name, hits in scorer_hits.items():
            n = len(hits)
            if n < 2:
                alignment[name] = 0.0
                continue
            mean_hit = sum(hits) / n
            variance = sum((h - mean_hit) ** 2 for h in hits) / (n - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 1e-10
            alignment[name] = mean_hit / std_dev * math.sqrt(n)

        return alignment

    def evaluate(self) -> Optional[dict[str, float]]:
        """Evaluate scorer performance and adjust weights.

        Returns new weight dict if evaluation was triggered, None otherwise.
        Circuit breaker: composite alignment Sharpe < 0 after 50 trades → reset.
        """
        total_trades = len(self.journal)
        new_trades = total_trades - self._last_eval_idx

        if new_trades < self.evolve_every:
            return None

        logger.info("WeightEvolver: evaluating after %d new trades (%d total)",
                     new_trades, total_trades)

        # Circuit breaker: composite alignment check
        if total_trades >= self.circuit_breaker_trades:
            cb_window = self.journal.last_n(self.circuit_breaker_trades)
            composite_alignments = []
            for entry in cb_window:
                pnl_direction = 1 if entry.actual_pnl > 0 else (-1 if entry.actual_pnl < 0 else 0)
                weighted_pred = 0.0
                total_w = 0.0
                for name, scores in entry.scorer_scores.items():
                    w = self.current_weights.get(name, 0.0)
                    score_val = scores.get("score", 0.0)
                    pred = 1 if score_val > 5 else (-1 if score_val < -5 else 0)
                    weighted_pred += pred * w
                    total_w += w

                composite_pred = weighted_pred / total_w if total_w > 0 else 0
                if composite_pred == 0 or pnl_direction == 0:
                    composite_alignments.append(0.0)
                elif (composite_pred > 0) == (pnl_direction > 0):
                    composite_alignments.append(1.0)
                else:
                    composite_alignments.append(-1.0)

            if len(composite_alignments) >= 2:
                cb_mean = sum(composite_alignments) / len(composite_alignments)
                cb_var = sum((x - cb_mean) ** 2 for x in composite_alignments) / (len(composite_alignments) - 1)
                cb_std = math.sqrt(cb_var) if cb_var > 0 else 1e-10
                cb_sharpe = cb_mean / cb_std * math.sqrt(len(composite_alignments))
                if cb_sharpe < 0:
                    logger.warning("Circuit breaker: composite Sharpe=%.2f < 0 — resetting to defaults", cb_sharpe)
                    self.reset_to_defaults()
                    self._save_weights()
                    return dict(self.current_weights)

        # Per-scorer alignment Sharpe
        alignment = self._compute_scorer_alignment(window=self.evolve_every)
        if not alignment:
            self._last_eval_idx = total_trades
            self._save_weights()
            return dict(self.current_weights)

        # Adjust weights: max ±max_adj_pct per cycle
        for name, sharpe in alignment.items():
            if name not in self.current_weights:
                continue
            adjustment = self.max_adj_pct * _clamp(sharpe, -1.0, 1.0)
            new_w = self.current_weights[name] + adjustment

            # Safety ceiling: max 20% shift from original
            orig = self.default_weights.get(name, new_w)
            max_allowed = orig + self.max_total_shift_pct
            min_allowed = orig - self.max_total_shift_pct
            new_w = _clamp(new_w, min_allowed, max_allowed)

            self.current_weights[name] = new_w

        # Normalize to sum = 1.0
        total = sum(self.current_weights.values())
        if total > 0:
            for name in self.current_weights:
                self.current_weights[name] /= total

        logger.info("WeightEvolver: new weights %s", {
            k: round(v, 4) for k, v in self.current_weights.items()
        })
        self._last_eval_idx = total_trades
        self._save_weights()
        return dict(self.current_weights)

    def get_weights(self) -> dict[str, float]:
        return dict(self.current_weights)

    def apply_weights(self, scorers: list[BaseScorer]):
        for scorer in scorers:
            name = scorer.__class__.__name__
            if name in self.current_weights:
                old = scorer.weight
                scorer.weight = self.current_weights[name]
                if abs(old - scorer.weight) > 0.001:
                    logger.debug("WeightEvolver: %s %.4f → %.4f", name, old, scorer.weight)

    def reset_to_defaults(self):
        self.current_weights = dict(self.default_weights)
        logger.info("WeightEvolver: reset to defaults: %s", self.default_weights)
        self._save_weights()