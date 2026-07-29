from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from quant_nanggroe.core.config.pair_config import AssetClass, get_alignment, get_pair_config
from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult
from quant_nanggroe.core.scoring.fusion_engine import FusionEngine

logger = logging.getLogger(__name__)

CONFIDENCE_HIGH = 0.60


class TimeframeFrame(str, Enum):
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    SESSION = "session"


class TimeframeResolution(str, Enum):
    PROCEED = "proceed"
    REDUCE = "reduce"
    HOLD = "hold"


@dataclass
class FrameScore:
    frame: TimeframeFrame
    score: float
    confidence: float
    bias: str
    details: list[tuple[str, ScorerResult]] = field(default_factory=list)


@dataclass
class MultiTimeframeResult:
    frames: dict[TimeframeFrame, FrameScore]
    htf_bias: str
    ltf_bias: str
    resolution: TimeframeResolution
    message: str = ""


FRAME_SCORER_MAP: dict[TimeframeFrame, list[str] | None] = {
    TimeframeFrame.MONTHLY: ["MacroScorer"],
    TimeframeFrame.WEEKLY: ["MacroScorer", "EconomicScorer"],
    TimeframeFrame.DAILY: None,
    TimeframeFrame.SESSION: ["SentimentScorer", "TechnicalScorer"],
}


class MultiTimeframeEngine:
    def __init__(self, scorers: list[BaseScorer]):
        self._scorers = scorers
        self._scorer_map: dict[str, BaseScorer] = {
            s.__class__.__name__: s for s in scorers
        }

    def evaluate(self, ctx: dict[str, Any], symbol: str = "") -> MultiTimeframeResult:
        frames: dict[TimeframeFrame, FrameScore] = {}

        pair_cfg = get_pair_config(symbol) if symbol else None

        if pair_cfg and pair_cfg.asset_class in (AssetClass.CRYPTO, AssetClass.FOREX_EXOTIC):
            crypto_htf_frames = [TimeframeFrame.DAILY, TimeframeFrame.SESSION]
            crypto_ltf_frames = [TimeframeFrame.MONTHLY, TimeframeFrame.WEEKLY]
            frame_order = list(TimeframeFrame)
        else:
            crypto_htf_frames = None
            crypto_ltf_frames = None

        for frame in TimeframeFrame:
            try:
                frames[frame] = self._score_frame(frame, ctx)
            except Exception as exc:
                logger.debug("MTF frame %s failed: %s", frame.value, exc)
                frames[frame] = FrameScore(
                    frame=frame, score=0.0, confidence=0.0, bias="neutral",
                )

        if crypto_htf_frames is not None:
            htf_frames = [frames[f] for f in crypto_htf_frames if f in frames]
            ltf_frames = [frames[f] for f in crypto_ltf_frames if f in frames]
        else:
            htf_frames = [
                frames[TimeframeFrame.MONTHLY], frames[TimeframeFrame.WEEKLY],
            ]
            ltf_frames = [
                frames[TimeframeFrame.DAILY], frames[TimeframeFrame.SESSION],
            ]

        htf_bias = self._frame_consensus(htf_frames)

        ltf_bias = self._frame_consensus(ltf_frames)

        resolution, message = self._conflict_resolve(
            htf_bias, ltf_bias, htf_frames, ltf_frames,
        )

        return MultiTimeframeResult(
            frames=frames,
            htf_bias=htf_bias,
            ltf_bias=ltf_bias,
            resolution=resolution,
            message=message,
        )

    def _score_frame(
        self, frame: TimeframeFrame, ctx: dict[str, Any]
    ) -> FrameScore:
        scorer_names = FRAME_SCORER_MAP[frame]

        if scorer_names is None:
            frame_scorers = self._scorers
        else:
            frame_scorers = [
                self._scorer_map[n] for n in scorer_names
                if n in self._scorer_map
            ]

        if not frame_scorers:
            return FrameScore(
                frame=frame, score=0.0, confidence=0.0, bias="neutral",
            )

        engine = FusionEngine(scorers=frame_scorers)
        signal = engine.evaluate(ctx)

        return FrameScore(
            frame=frame,
            score=signal.composite_score,
            confidence=signal.confidence,
            bias=signal.bias,
            details=signal.details,
        )

    @staticmethod
    def _frame_consensus(frame_scores: list[FrameScore]) -> str:
        votes: dict[str, float] = {}
        for fs in frame_scores:
            if fs.bias == "neutral":
                continue
            votes[fs.bias] = votes.get(fs.bias, 0.0) + fs.confidence

        if not votes:
            return "neutral"

        return max(votes, key=votes.get)

    def _conflict_resolve(
        self,
        htf_bias: str,
        ltf_bias: str,
        htf_frames: list[FrameScore],
        ltf_frames: list[FrameScore],
    ) -> tuple[TimeframeResolution, str]:
        if htf_bias == "neutral" and ltf_bias == "neutral":
            return TimeframeResolution.HOLD, "both HTF and LTF are neutral"

        if htf_bias == "neutral":
            return (
                TimeframeResolution.REDUCE,
                "HTF neutral, LTF leads with reduced size",
            )

        if ltf_bias == "neutral":
            return (
                TimeframeResolution.REDUCE,
                "LTF neutral, HTF leads with reduced size",
            )

        if htf_bias != ltf_bias:
            return (
                TimeframeResolution.HOLD,
                f"HTF={htf_bias} conflicts with LTF={ltf_bias}",
            )

        htf_conf = sum(fs.confidence for fs in htf_frames) / len(htf_frames)
        ltf_conf = sum(fs.confidence for fs in ltf_frames) / len(ltf_frames)
        avg_conf = (htf_conf + ltf_conf) / 2.0

        if avg_conf >= CONFIDENCE_HIGH:
            return (
                TimeframeResolution.PROCEED,
                f"aligned {htf_bias} with high confidence ({avg_conf:.2f})",
            )

        return (
            TimeframeResolution.REDUCE,
            f"aligned {htf_bias} but low confidence ({avg_conf:.2f})",
        )
