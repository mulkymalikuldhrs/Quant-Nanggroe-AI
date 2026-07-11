"""Strategy Extractor — Extract trading strategies from text descriptions.

Parses text descriptions of trading strategies and converts them into
structured strategy definitions that can be validated and compiled.

Ported from Vibe-Trading/agent/src/shadow_account/extractor.py
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ExtractedRule:
    """A rule extracted from a text description."""

    rule_id: str
    human_text: str
    entry_conditions: Dict[str, Any] = field(default_factory=dict)
    exit_conditions: Dict[str, Any] = field(default_factory=dict)
    holding_days_range: Tuple[int, int] = (1, 30)
    direction: str = "long"  # 'long' or 'short'
    confidence: float = 0.0


@dataclass
class ExtractedStrategy:
    """A strategy extracted from text description."""

    strategy_id: str
    source_text: str
    source_hash: str
    extracted_at: str
    rules: List[ExtractedRule] = field(default_factory=list)
    markets: List[str] = field(default_factory=list)
    timeframe: str = "1d"
    risk_tolerance: str = "moderate"
    profile_summary: str = ""


class StrategyExtractor:
    """Strategy Extractor.

    Extracts trading strategies from natural language text descriptions.
    Identifies entry/exit conditions, risk parameters, and market preferences.

    Ported from Vibe-Trading/agent/src/shadow_account/extractor.py
    """

    # Pattern keywords for rule extraction
    ENTRY_KEYWORDS = {
        "buy": "long",
        "long": "long",
        "enter": "long",
        "purchase": "long",
        "sell": "short",
        "short": "short",
        "exit": "short",
        "close": "short",
    }

    INDICATOR_PATTERNS = {
        r"rsi\s*(?:below|under|less than)\s*(\d+)": ("rsi", "lt"),
        r"rsi\s*(?:above|over|greater than)\s*(\d+)": ("rsi", "gt"),
        r"price\s*(?:above|over|greater than|crosses above)\s*(?:sma|ma)\s*(\d+)": ("sma_cross_above", "gt"),
        r"price\s*(?:below|under|less than|crosses below)\s*(?:sma|ma)\s*(\d+)": ("sma_cross_below", "lt"),
        r"volume\s*(?:above|over|greater than)\s*(\d+(?:\.\d+)?)x": ("volume_ratio", "gt"),
        r"macd\s*(?:bullish\s+)?crossover": ("macd_crossover", "gt"),
        r"macd\s*(?:bearish\s+)?crossover": ("macd_crossover", "lt"),
        r"breakout\s+(?:above|over)\s*([\d.]+)": ("breakout_above", "gt"),
        r"breakdown\s+(?:below|under)\s*([\d.]+)": ("breakdown_below", "lt"),
        r"support\s+(?:at|around)\s*([\d.]+)": ("support", "eq"),
        r"resistance\s+(?:at|around)\s*([\d.]+)": ("resistance", "eq"),
        r"fibonacci\s+(0\.\d+)": ("fibonacci", "eq"),
        r"stop\s*loss\s*(?:at|around)?\s*([\d.]+)": ("stop_loss", "eq"),
        r"take\s*profit\s*(?:at|around)?\s*([\d.]+)": ("take_profit", "eq"),
        r"trailing\s*stop\s*([\d.]+)%?": ("trailing_stop", "eq"),
    }

    MARKET_PATTERNS = {
        r"\bcrypto\b": "crypto",
        r"\bbitcoin\b|\bbtc\b": "crypto",
        r"\bethereum\b|\beth\b": "crypto",
        r"\bforex\b|\bfx\b": "forex",
        r"\bequity\b|\bstock\b": "equity",
        r"\bfutures\b": "futures",
        r"\boptions\b": "options",
    }

    TIMEFRAME_PATTERNS = {
        r"\bscalp(?:ing)?\b": "5m",
        r"\bintraday\b": "1h",
        r"\bswing\b": "1d",
        r"\bposition\b": "1w",
        r"\b1m\b|\bone\s*minute\b": "1m",
        r"\b5m\b|\bfive\s*minute\b": "5m",
        r"\b1h\b|\bone\s*hour\b": "1h",
        r"\b4h\b|\bfour\s*hour\b": "4h",
        r"\b1d\b|\bdaily\b": "1d",
        r"\b1w\b|\bweekly\b": "1w",
    }

    def extract(self, text: str) -> ExtractedStrategy:
        """Extract a strategy from a text description.

        Args:
            text: Natural language description of a trading strategy.

        Returns:
            ExtractedStrategy with parsed rules and parameters.
        """
        source_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        # Extract rules
        rules = self._extract_rules(text)

        # Extract markets
        markets = self._extract_markets(text)

        # Extract timeframe
        timeframe = self._extract_timeframe(text)

        # Extract risk tolerance
        risk_tolerance = self._extract_risk_tolerance(text)

        # Generate profile summary
        profile = self._generate_profile(text, rules, markets)

        return ExtractedStrategy(
            strategy_id=f"strategy_{source_hash}",
            source_text=text,
            source_hash=source_hash,
            extracted_at=datetime.now().isoformat(),
            rules=rules,
            markets=markets,
            timeframe=timeframe,
            risk_tolerance=risk_tolerance,
            profile_summary=profile,
        )

    def validate_strategy(self, strategy: ExtractedStrategy) -> Tuple[bool, List[str]]:
        """Validate an extracted strategy.

        Args:
            strategy: ExtractedStrategy to validate.

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []

        if not strategy.rules:
            errors.append("No trading rules extracted")

        for rule in strategy.rules:
            if not rule.entry_conditions:
                errors.append(f"Rule {rule.rule_id}: No entry conditions")
            if rule.confidence <= 0:
                errors.append(f"Rule {rule.rule_id}: Invalid confidence")

        return len(errors) == 0, errors

    def _extract_rules(self, text: str) -> List[ExtractedRule]:
        """Extract trading rules from text."""
        text_lower = text.lower()
        rules = []

        # Split into sentences for rule extraction
        sentences = re.split(r'[.!?\n]+', text)

        rule_idx = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            entry_conditions = {}
            exit_conditions = {}
            direction = "long"
            has_indicator = False

            # Check for direction keywords
            for keyword, dir_val in self.ENTRY_KEYWORDS.items():
                if keyword in sentence.lower():
                    direction = dir_val
                    break

            # Check for indicator patterns
            for pattern, (indicator, operator) in self.INDICATOR_PATTERNS.items():
                match = re.search(pattern, sentence.lower())
                if match:
                    value = match.group(1) if match.groups() else True
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = True

                    if indicator in ("stop_loss", "take_profit", "trailing_stop"):
                        exit_conditions[indicator] = {"value": value, "operator": operator}
                    else:
                        entry_conditions[indicator] = {"value": value, "operator": operator}
                    has_indicator = True

            if has_indicator or entry_conditions or exit_conditions:
                rule_idx += 1
                rules.append(ExtractedRule(
                    rule_id=f"R{rule_idx}",
                    human_text=sentence[:100],
                    entry_conditions=entry_conditions,
                    exit_conditions=exit_conditions,
                    direction=direction,
                    confidence=0.6 if has_indicator else 0.3,
                ))

        return rules

    def _extract_markets(self, text: str) -> List[str]:
        """Extract target markets from text."""
        text_lower = text.lower()
        markets = set()

        for pattern, market in self.MARKET_PATTERNS.items():
            if re.search(pattern, text_lower):
                markets.add(market)

        return list(markets) if markets else ["equity"]

    def _extract_timeframe(self, text: str) -> str:
        """Extract trading timeframe from text."""
        text_lower = text.lower()

        for pattern, timeframe in self.TIMEFRAME_PATTERNS.items():
            if re.search(pattern, text_lower):
                return timeframe

        return "1d"

    def _extract_risk_tolerance(self, text: str) -> str:
        """Extract risk tolerance from text."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["aggressive", "high risk", "leverage"]):
            return "aggressive"
        elif any(w in text_lower for w in ["conservative", "low risk", "safe"]):
            return "conservative"
        else:
            return "moderate"

    def _generate_profile(
        self, text: str, rules: List[ExtractedRule], markets: List[str]
    ) -> str:
        """Generate a profile summary from extracted data."""
        directions = [r.direction for r in rules]
        long_count = directions.count("long")
        short_count = directions.count("short")

        bias = "bullish" if long_count > short_count else "bearish" if short_count > long_count else "neutral"

        return (
            f"Strategy with {len(rules)} rules, {bias} bias, "
            f"targeting {', '.join(markets)} markets."
        )
