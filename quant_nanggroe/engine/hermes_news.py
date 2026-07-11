#!/usr/bin/env python3
"""
News Sentinel with Logarithmic Time Decay (from Quant-Nanggroe-AI)
===================================================================
Event classification and time-decay impact scoring.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger("HermesQuantOS.NewsSentinel")


class NewsSentinelTool:
    """
    Enhanced news sentiment with logarithmic time decay.
    
    Source: Quant-Nanggroe-AI v15.2.0 News Sentinel
    Event types with different decay half-lives and directional uncertainty.
    """

    # Event classification rules
    EVENT_TYPES = {
        "SHOCK": {
            "keywords": ["war", "crash", "collapse", "hack", "crisis", "attack",
                         "emergency", "black swan", "default", "sanction"],
            "raw_impact": 1.0,
            "decay_half_life_hours": 4.0,
            "directional_uncertainty": 0.85
        },
        "MACRO": {
            "keywords": ["fed", "cpi", "fomc", "gdp", "inflation", "rates", "interest",
                         "employment", "nonfarm", "nfp", "pmi", "retail sales", "housing"],
            "raw_impact": 0.85,
            "decay_half_life_hours": 2.0,
            "directional_uncertainty": 0.45
        },
        "SCHEDULED": {
            "keywords": ["report", "calendar", "forecast", "expected", "release",
                         "announcement", "meeting", "conference", "earnings"],
            "raw_impact": 0.55,
            "decay_half_life_hours": 1.0,
            "directional_uncertainty": 0.25
        },
        "NOISE": {
            "keywords": [],
            "raw_impact": 0.2,
            "decay_half_life_hours": 0.083,  # 5 minutes
            "directional_uncertainty": 0.25
        }
    }

    def __init__(self):
        self.events = []  # List of stored events

    def classify_event(self, headline: str) -> Dict:
        """Classify a news event by type"""
        headline_lower = headline.lower()

        for event_type, config in self.EVENT_TYPES.items():
            if event_type == "NOISE":
                continue
            for keyword in config["keywords"]:
                if keyword in headline_lower:
                    return {
                        "event_type": event_type,
                        "raw_impact": config["raw_impact"],
                        "decay_half_life_hours": config["decay_half_life_hours"],
                        "directional_uncertainty": config["directional_uncertainty"],
                        "matched_keyword": keyword
                    }

        # Default to NOISE
        noise = self.EVENT_TYPES["NOISE"]
        return {
            "event_type": "NOISE",
            "raw_impact": noise["raw_impact"],
            "decay_half_life_hours": noise["decay_half_life_hours"],
            "directional_uncertainty": noise["directional_uncertainty"],
            "matched_keyword": None
        }

    def add_event(self, headline: str, source: str = "unknown") -> Dict:
        """Add a news event to the sentinel"""
        classification = self.classify_event(headline)

        event = {
            "headline": headline,
            "source": source,
            "event_type": classification["event_type"],
            "raw_impact": classification["raw_impact"],
            "decay_half_life_hours": classification["decay_half_life_hours"],
            "directional_uncertainty": classification["directional_uncertainty"],
            "timestamp": datetime.now().isoformat(),
            "matched_keyword": classification.get("matched_keyword")
        }

        self.events.append(event)
        logger.info(f"NEWS: [{event['event_type']}] {headline[:80]}")

        return event

    def calculate_decayed_impact(self, event: Dict) -> float:
        """
        Calculate impact score with logarithmic time decay.
        
        Formula: impactScore = rawImpact × 0.5^(elapsedSeconds / decayHalfLife)
        """
        event_time = datetime.fromisoformat(event["timestamp"])
        elapsed = (datetime.now() - event_time).total_seconds()
        half_life_seconds = event["decay_half_life_hours"] * 3600

        if half_life_seconds <= 0:
            return 0.0

        decayed = event["raw_impact"] * (0.5 ** (elapsed / half_life_seconds))
        return round(decayed, 4)

    def get_total_impact(self) -> Dict:
        """Get total impact score across all events with decay applied"""
        total_buy_impact = 0.0
        total_sell_impact = 0.0
        active_events = []

        for event in self.events:
            impact = self.calculate_decayed_impact(event)
            if impact < 0.01:
                continue  # Negligible impact, skip

            uncertainty = event["directional_uncertainty"]
            # Uncertainty splits impact between directions
            total_buy_impact += impact * (1.0 - uncertainty)
            total_sell_impact += impact * uncertainty

            active_events.append({
                "headline": event["headline"][:80],
                "type": event["event_type"],
                "decayed_impact": impact,
                "age_minutes": round(
                    (datetime.now() - datetime.fromisoformat(event["timestamp"])).total_seconds() / 60, 1
                )
            })

        total_impact = total_buy_impact + total_sell_impact

        return {
            "total_impact": round(total_impact, 4),
            "buy_impact": round(total_buy_impact, 4),
            "sell_impact": round(total_sell_impact, 4),
            "active_events": len(active_events),
            "events": active_events[-10:],  # Last 10 active events
            "timestamp": datetime.now().isoformat()
        }

    def score_impact(self, headline: str, severity: str = "medium") -> str:
        """Score the impact of a news headline"""
        event = self.add_event(headline)
        impact = self.calculate_decayed_impact(event)
        total = self.get_total_impact()

        return json.dumps({
            "headline": headline,
            "event_type": event["event_type"],
            "raw_impact": event["raw_impact"],
            "decayed_impact": impact,
            "severity": severity,
            "total_active_impact": total["total_impact"],
            "directional_uncertainty": event["directional_uncertainty"],
            "timestamp": datetime.now().isoformat()
        }, indent=2)

    def get_recent_events(self, limit: int = 10) -> str:
        """Get recent news events"""
        recent = self.events[-limit:] if self.events else []
        return json.dumps({
            "total_events": len(self.events),
            "recent": [{
                "headline": e["headline"][:80],
                "type": e["event_type"],
                "raw_impact": e["raw_impact"],
                "timestamp": e["timestamp"]
            } for e in recent],
            "timestamp": datetime.now().isoformat()
        }, indent=2)

    def cleanup_old_events(self, max_age_hours: float = 24.0):
        """Remove events older than max age"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        self.events = [
            e for e in self.events
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
