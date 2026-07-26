from __future__ import annotations

import logging
from typing import Any

import numpy as np

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class AlternativeDataStrategy(Strategy):
    """Alternative data signals — card spend, satellite, NLP, web scraping.

    Implements:
      - Credit/debit card spending nowcast
      - Satellite imagery (traffic, oil inventory, crop yield)
      - Earnings call NLP sentiment
      - Web scraping price tracking & job postings
      - Geopolitical risk index from news

    Reference: SSRN-3847291, multiple practitioner papers
    """

    name = "alternative_data"
    description = "Alt data: card spend + satellite + earnings NLP + web scrape + geo risk"
    required_indicators = ["close"]

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not isinstance(data, dict):
                return self._hold("No alt data available")

            scores: list[float] = []
            details: list[str] = []

            if "card_spend" in data:
                s = self._score_card_spend(float(data["card_spend"]), str(data.get("category", "discretionary")))
                scores.append(s * 0.25), details.append(f"card={s:.2f}")

            sat = data.get("satellite")
            if isinstance(sat, dict):
                s = self._score_satellite(sat.get("traffic_change"), sat.get("oil_inventory"), sat.get("crop_yield_change"))
                scores.append(s * 0.20), details.append(f"sat={s:.2f}")

            ec = data.get("earnings_call")
            if isinstance(ec, dict):
                s = self._score_earnings(float(ec.get("sentiment", 0)), ec.get("forward_guidance"))
                scores.append(s * 0.25), details.append(f"ec={s:.2f}")

            web = data.get("web_scrape")
            if isinstance(web, dict):
                s = self._score_web(float(web.get("price_change", 0)), float(web.get("review_sentiment", 0)), web.get("job_postings_change"))
                scores.append(s * 0.15), details.append(f"web={s:.2f}")

            g = data.get("geopolitical_risk", data.get("msi_score"))
            if g is not None:
                s = self._score_geo(float(data.get("gri", 0)), float(g))
                scores.append(s * 0.15), details.append(f"geo={s:.2f}")

            if not scores:
                return self._hold("No alt data sources available")

            total = float(np.sum(scores))
            price = float(kwargs.get("price", data.get("price", 0)))

            if total > 0.25:
                direction = SignalDirection.BUY
                conf = min(abs(total), 0.9)
            elif total < -0.25:
                direction = SignalDirection.SELL
                conf = min(abs(total), 0.9)
            else:
                return self._hold(f"alt_score={total:.4f} " + " ".join(details), {"alt_score": total})

            sl = price * (0.97 if direction == SignalDirection.BUY else 1.03)
            tp = price * (1.03 if direction == SignalDirection.BUY else 0.97)

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=SignalStrength.STRONG if conf > 0.6 else SignalStrength.MODERATE,
                confidence=conf,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                risk_reward=self.calculate_risk_reward(price, sl, tp, direction),
                reasoning=f"alt={total:.4f} " + " ".join(details),
                indicators={"alt_score": total},
            )

        except Exception as exc:
            logger.error("AltData error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _score_card_spend(self, growth: float, category: str) -> float:
        w = {"discretionary": 0.7, "luxury": 0.8, "travel": 0.6, "grocery": 0.3, "technology": 0.6, "automotive": 0.5, "energy": 0.5}.get(category, 0.3)
        return float(np.clip(growth * w, -1.0, 1.0))

    def _score_satellite(self, traffic: float | None = None, oil: float | None = None, crop: float | None = None) -> float:
        s = 0.0
        if traffic is not None:
            s += 0.4 * np.tanh(traffic)
        if oil is not None:
            s -= 0.3 * np.tanh(oil)
        if crop is not None:
            s += 0.3 * np.tanh(crop)
        return float(np.clip(s, -1.0, 1.0))

    def _score_earnings(self, sentiment: float, guidance: float | None = None) -> float:
        s = np.tanh(sentiment)
        if guidance is not None:
            s += 0.3 * np.tanh(guidance)
        return float(np.clip(s, -1.0, 1.0))

    def _score_web(self, price_change: float, review_sentiment: float, jobs: float | None = None) -> float:
        s = 0.4 * np.tanh(price_change) + 0.4 * np.tanh(review_sentiment)
        if jobs is not None:
            s += 0.2 * np.tanh(jobs)
        return float(np.clip(s, -1.0, 1.0))

    def _score_geo(self, gri: float, msi: float) -> float:
        return float(np.clip(-np.tanh(gri) + 0.3 * np.tanh(msi), -1.0, 1.0))

    def _hold(self, reason: str, indicators: dict | None = None) -> StrategySignal:
        return StrategySignal(strategy_name=self.name, direction=SignalDirection.HOLD, reasoning=reason, indicators=indicators or {})
