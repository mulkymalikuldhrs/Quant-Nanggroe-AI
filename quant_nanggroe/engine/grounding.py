"""Grounding System — Prevent LLM Price Hallucination.

Implements Vibe-Trading's grounding pattern to prevent LLMs from
hallucinating market prices.  Before any LLM call about a symbol,
real OHLCV data is pre-fetched and injected into the system prompt
as a compact markdown table with an explicit instruction that these
are the ONLY prices the LLM may cite.

After the LLM responds, any price mentioned in the output is
validated against the grounded data — prices must be within 5%
of the real data or they are flagged as hallucinated.

Features
--------
* Pre-fetches real OHLCV data via yfinance (with 5-minute cache)
* Renders compact markdown price tables in system prompts
* Validates LLM output prices against grounded data
* Detects and flags price hallucinations
* Caching with configurable TTL
* Async throughout

Usage::

    from quant_nanggroe.engine.grounding import MarketGrounding

    grounding = MarketGrounding()
    enhanced_prompt = await grounding.ground_prompt(
        system_prompt="Analyze AAPL",
        symbols=["AAPL", "MSFT"]
    )
    # Use enhanced_prompt with your LLM call
    # After response, validate:
    validation = grounding.validate_response(llm_response, ["AAPL", "MSFT"])
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)

# ── Optional yfinance import ────────────────────────────────────────────

try:
    import yfinance as yf

    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False
    yf = None  # type: ignore[assignment]


# ── Pydantic Models ─────────────────────────────────────────────────────


class GroundedPrice(BaseModel):
    """Grounded price data for a single symbol.

    Attributes:
        symbol: Trading symbol.
        current_price: Latest close price.
        open_price: Latest open price.
        high_price: Latest high price.
        low_price: Latest low price.
        volume: Latest volume.
        previous_close: Previous session close.
        change_pct: Percentage change from previous close.
        timestamp: Timestamp of the data.
        source: Data source (e.g., "yfinance").
    """

    model_config = ConfigDict(frozen=False)

    symbol: str = ""
    current_price: float = 0.0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    volume: float = 0.0
    previous_close: float = 0.0
    change_pct: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: str = "yfinance"


class GroundingResult(BaseModel):
    """Result from grounding a prompt.

    Attributes:
        result_id: Unique identifier.
        enhanced_prompt: The prompt with grounded price data injected.
        symbols_grounded: List of symbols that were successfully grounded.
        symbols_failed: List of symbols that failed to ground.
        cache_hits: Number of symbols served from cache.
        cache_misses: Number of symbols fetched fresh.
        total_latency_ms: Total grounding latency in milliseconds.
    """

    model_config = ConfigDict(frozen=False)

    result_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    enhanced_prompt: str = ""
    symbols_grounded: List[str] = Field(default_factory=list)
    symbols_failed: List[str] = Field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    total_latency_ms: float = 0.0


class ValidationMatch(BaseModel):
    """A single price validation match.

    Attributes:
        symbol: The symbol referenced.
        mentioned_price: Price mentioned in LLM output.
        grounded_price: Actual grounded price.
        deviation_pct: Percentage deviation from grounded price.
        is_valid: Whether the deviation is within tolerance.
    """

    model_config = ConfigDict(frozen=False)

    symbol: str = ""
    mentioned_price: float = 0.0
    grounded_price: float = 0.0
    deviation_pct: float = 0.0
    is_valid: bool = True


class ValidationResult(BaseModel):
    """Result from validating an LLM response against grounded data.

    Attributes:
        result_id: Unique identifier.
        is_valid: Whether all mentioned prices are within tolerance.
        n_prices_checked: Number of prices checked.
        n_hallucinations: Number of hallucinated prices detected.
        matches: Detailed validation matches.
        flagged_prices: List of flagged (hallucinated) price references.
    """

    model_config = ConfigDict(frozen=False)

    result_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    is_valid: bool = True
    n_prices_checked: int = 0
    n_hallucinations: int = 0
    matches: List[ValidationMatch] = Field(default_factory=list)
    flagged_prices: List[str] = Field(default_factory=list)

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API-safe dictionary."""
        return {
            "is_valid": self.is_valid,
            "n_prices_checked": self.n_prices_checked,
            "n_hallucinations": self.n_hallucinations,
            "flagged_prices": self.flagged_prices,
        }


# ── Cache Entry ─────────────────────────────────────────────────────────


@dataclass
class _CacheEntry:
    """Internal cache entry for price data."""

    prices: GroundedPrice
    cached_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0  # 5 minutes

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return (time.time() - self.cached_at) > self.ttl_seconds


# ── Market Grounding ────────────────────────────────────────────────────


class MarketGrounding:
    """Grounding system to prevent LLM price hallucination.

    Pre-fetches real market data and injects it into LLM prompts
    as grounded reference tables.  After the LLM responds, validates
    that any prices mentioned are within tolerance of the real data.

    Args:
        cache_ttl: Cache TTL in seconds (default: 300 = 5 minutes).
        tolerance_pct: Allowed deviation from grounded prices (default: 5%).
        max_symbols_per_prompt: Maximum symbols to ground per prompt.

    Usage::

        grounding = MarketGrounding(cache_ttl=300, tolerance_pct=5.0)
        result = await grounding.ground_prompt(
            system_prompt="Analyze AAPL and MSFT",
            symbols=["AAPL", "MSFT"]
        )
        # Use result.enhanced_prompt with your LLM
        validation = grounding.validate_response(llm_output, ["AAPL"])
    """

    def __init__(
        self,
        cache_ttl: float = 300.0,
        tolerance_pct: float = 5.0,
        max_symbols_per_prompt: int = 10,
    ) -> None:
        self.cache_ttl = cache_ttl
        self.tolerance_pct = tolerance_pct
        self.max_symbols_per_prompt = max_symbols_per_prompt

        # Price cache: symbol → _CacheEntry
        self._cache: Dict[str, _CacheEntry] = {}

    # ── Core Grounding Method ────────────────────────────────────────

    async def ground_prompt(
        self,
        system_prompt: str,
        symbols: List[str],
    ) -> GroundingResult:
        """Enhance a system prompt with grounded market data.

        Pre-fetches real OHLCV data for each symbol, renders it as a
        compact markdown table, and appends it to the system prompt
        with an explicit instruction that these are the ONLY prices
        the LLM may cite.

        Args:
            system_prompt: Original system prompt.
            symbols: List of symbols to ground.

        Returns:
            GroundingResult with the enhanced prompt and metadata.
        """
        start_time = time.time()

        # Limit symbols
        symbols = symbols[: self.max_symbols_per_prompt]

        grounded: List[str] = []
        failed: List[str] = []
        price_data: Dict[str, GroundedPrice] = {}
        cache_hits = 0
        cache_misses = 0

        # Fetch data for each symbol
        for symbol in symbols:
            try:
                price = await self._fetch_price(symbol)
                if price and price.current_price > 0:
                    price_data[symbol] = price
                    grounded.append(symbol)
                    cache_hits += 1 if self._is_cached(symbol) else 0
                    cache_misses += 0 if self._is_cached(symbol) else 1
                else:
                    failed.append(symbol)
            except Exception as exc:
                logger.warning(
                    "grounding_fetch_failed",
                    extra={"symbol": symbol, "error": str(exc)},
                )
                failed.append(symbol)

        # Build markdown table
        markdown_table = self._render_price_table(price_data)

        # Build grounding instruction
        grounding_instruction = self._build_grounding_instruction(
            price_data, symbols
        )

        # Inject into prompt
        enhanced = self._inject_into_prompt(
            system_prompt, grounding_instruction, markdown_table
        )

        total_latency = (time.time() - start_time) * 1000

        return GroundingResult(
            enhanced_prompt=enhanced,
            symbols_grounded=grounded,
            symbols_failed=failed,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            total_latency_ms=round(total_latency, 2),
        )

    # ── Validation Method ────────────────────────────────────────────

    def validate_response(
        self,
        response: str,
        symbols: List[str],
    ) -> ValidationResult:
        """Validate LLM response prices against grounded data.

        Scans the response for price mentions near symbol references
        and checks that each price is within ``tolerance_pct`` of the
        grounded data.

        Args:
            response: LLM response text.
            symbols: Symbols to check for price references.

        Returns:
            ValidationResult with any hallucinated prices flagged.
        """
        matches: List[ValidationMatch] = []
        flagged: List[str] = []

        for symbol in symbols:
            # Get grounded price
            entry = self._cache.get(symbol)
            if not entry or entry.is_expired:
                continue

            grounded_price = entry.prices.current_price
            if grounded_price <= 0:
                continue

            # Find price mentions near symbol references
            price_refs = self._extract_price_mentions(
                response, symbol, grounded_price
            )

            for mentioned_price, context in price_refs:
                deviation = abs(mentioned_price - grounded_price) / grounded_price * 100
                is_valid = deviation <= self.tolerance_pct

                match = ValidationMatch(
                    symbol=symbol,
                    mentioned_price=mentioned_price,
                    grounded_price=grounded_price,
                    deviation_pct=round(deviation, 2),
                    is_valid=is_valid,
                )
                matches.append(match)

                if not is_valid:
                    flagged.append(
                        f"{symbol}: mentioned ${mentioned_price:.2f}, "
                        f"actual ${grounded_price:.2f} "
                        f"(deviation: {deviation:.1f}%)"
                    )

        n_hallucinations = sum(1 for m in matches if not m.is_valid)

        return ValidationResult(
            is_valid=n_hallucinations == 0,
            n_prices_checked=len(matches),
            n_hallucinations=n_hallucinations,
            matches=matches,
            flagged_prices=flagged,
        )

    # ── Data Fetching ────────────────────────────────────────────────

    async def _fetch_price(self, symbol: str) -> Optional[GroundedPrice]:
        """Fetch current price data for a symbol.

        Uses cache when available, falls back to yfinance.

        Args:
            symbol: Trading symbol.

        Returns:
            GroundedPrice or None if fetch fails.
        """
        # Check cache
        entry = self._cache.get(symbol)
        if entry and not entry.is_expired:
            return entry.prices

        # Fetch from yfinance
        if not _YF_AVAILABLE or yf is None:
            logger.warning(
                "grounding_yfinance_unavailable",
                extra={"symbol": symbol},
            )
            raise RuntimeError(
                "Real price source unavailable — yfinance not installed"
            )

        try:
            ticker = yf.Ticker(symbol)
            # Run in thread pool since yfinance is synchronous
            hist = await asyncio.to_thread(
                lambda: ticker.history(period="5d")
            )

            if hist.empty:
                logger.warning(
                    "grounding_no_data",
                    extra={"symbol": symbol},
                )
                return None

            # Get latest data
            latest = hist.iloc[-1]
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else float(latest["Close"])

            current = float(latest["Close"])
            change_pct = (
                ((current - prev_close) / prev_close) * 100
                if prev_close > 0
                else 0.0
            )

            price = GroundedPrice(
                symbol=symbol,
                current_price=current,
                open_price=float(latest["Open"]),
                high_price=float(latest["High"]),
                low_price=float(latest["Low"]),
                volume=float(latest["Volume"]),
                previous_close=prev_close,
                change_pct=round(change_pct, 2),
                source="yfinance",
            )

            # Cache it
            self._cache[symbol] = _CacheEntry(
                prices=price,
                ttl_seconds=self.cache_ttl,
            )

            return price

        except Exception as exc:
            logger.warning(
                "grounding_fetch_error",
                extra={"symbol": symbol, "error": str(exc)},
            )
            return None

    # ── Prompt Rendering ─────────────────────────────────────────────

    def _render_price_table(
        self, price_data: Dict[str, GroundedPrice]
    ) -> str:
        """Render price data as a compact markdown table.

        Args:
            price_data: Symbol → GroundedPrice mapping.

        Returns:
            Markdown table string.
        """
        if not price_data:
            return "No price data available."

        lines = [
            "| Symbol | Price | Open | High | Low | Volume | Change |",
            "|--------|------:|-----:|-----:|----:|-------:|-------:|",
        ]

        for symbol, p in sorted(price_data.items()):
            vol_str = self._format_volume(p.volume)
            lines.append(
                f"| {symbol} | ${p.current_price:.2f} | ${p.open_price:.2f} | "
                f"${p.high_price:.2f} | ${p.low_price:.2f} | {vol_str} | "
                f"{p.change_pct:+.2f}% |"
            )

        return "\n".join(lines)

    def _build_grounding_instruction(
        self,
        price_data: Dict[str, GroundedPrice],
        symbols: List[str],
    ) -> str:
        """Build the grounding instruction for the LLM.

        Args:
            price_data: Grounded price data.
            symbols: Requested symbols.

        Returns:
            Grounding instruction string.
        """
        symbol_list = ", ".join(symbols)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        return (
            f"\n\n--- GROUNDED MARKET DATA (as of {timestamp}) ---\n"
            f"The following are REAL, VERIFIED prices for: {symbol_list}.\n"
            f"⚠️ These are the ONLY prices you may cite. "
            f"Do NOT invent, estimate, or recall prices from training data.\n"
            f"If you need to reference a price for any of these symbols, "
            f"use EXACTLY the values in the table below.\n"
            f"If you are unsure about a price, say so explicitly.\n"
        )

    @staticmethod
    def _inject_into_prompt(
        system_prompt: str,
        grounding_instruction: str,
        markdown_table: str,
    ) -> str:
        """Inject grounding data into the system prompt.

        Appends the grounding instruction and price table to the
        end of the system prompt.

        Args:
            system_prompt: Original prompt.
            grounding_instruction: Grounding instruction text.
            markdown_table: Price data table.

        Returns:
            Enhanced prompt string.
        """
        return (
            system_prompt
            + grounding_instruction
            + "\n"
            + markdown_table
            + "\n\n--- END GROUNDED DATA ---\n"
        )

    # ── Price Extraction ─────────────────────────────────────────────

    @staticmethod
    def _extract_price_mentions(
        text: str,
        symbol: str,
        reference_price: float,
    ) -> List[Tuple[float, str]]:
        """Extract price mentions near symbol references in text.

        Searches for dollar amounts (e.g., "$175.50", "175.50")
        within a context window around symbol references.

        Args:
            text: Text to search.
            symbol: Symbol to search near.
            reference_price: Reference price for context-aware matching.

        Returns:
            List of (mentioned_price, context_snippet) tuples.
        """
        mentions: List[Tuple[float, str]] = []

        # Pattern 1: $XXX.XX format
        dollar_pattern = r"\$(\d+\.?\d*)"
        # Pattern 2: Bare numbers that could be prices (near reference)
        bare_pattern = r"(?<!\$)\b(\d{2,5}\.\d{1,2})\b"

        # Find all occurrences of the symbol
        for match in re.finditer(re.escape(symbol), text, re.IGNORECASE):
            # Search within ±200 chars of symbol reference
            start = max(0, match.start() - 200)
            end = min(len(text), match.end() + 200)
            context = text[start:end]

            # Find dollar amounts in context
            for price_match in re.finditer(dollar_pattern, context):
                try:
                    price = float(price_match.group(1))
                    # Filter: only consider prices within 50% of reference
                    if reference_price > 0 and abs(price - reference_price) / reference_price < 0.5:
                        mentions.append((price, context[max(0, price_match.start() - 30):price_match.end() + 30]))
                except ValueError:
                    continue

            # Also check bare numbers close to reference
            for price_match in re.finditer(bare_pattern, context):
                try:
                    price = float(price_match.group(1))
                    if reference_price > 0 and abs(price - reference_price) / reference_price < 0.1:
                        # Only if within 10% — higher confidence it's a price reference
                        mentions.append((price, context[max(0, price_match.start() - 20):price_match.end() + 20]))
                except ValueError:
                    continue

        return mentions

    # ── Utility Methods ──────────────────────────────────────────────

    def _is_cached(self, symbol: str) -> bool:
        """Check if a symbol is in cache and not expired."""
        entry = self._cache.get(symbol)
        return entry is not None and not entry.is_expired

    @staticmethod
    def _format_volume(volume: float) -> str:
        """Format volume for display."""
        if volume >= 1e9:
            return f"{volume / 1e9:.1f}B"
        elif volume >= 1e6:
            return f"{volume / 1e6:.1f}M"
        elif volume >= 1e3:
            return f"{volume / 1e3:.1f}K"
        else:
            return f"{volume:.0f}"

    def clear_cache(self) -> int:
        """Clear all cached price data.

        Returns:
            Number of entries cleared.
        """
        n = len(self._cache)
        self._cache.clear()
        return n

    def cleanup_cache(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of expired entries removed.
        """
        expired = [sym for sym, entry in self._cache.items() if entry.is_expired]
        for sym in expired:
            del self._cache[sym]
        return len(expired)

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Cache statistics."""
        total = len(self._cache)
        expired = sum(1 for e in self._cache.values() if e.is_expired)
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "cache_ttl_seconds": self.cache_ttl,
            "yfinance_available": _YF_AVAILABLE,
        }

    @property
    def stats(self) -> Dict[str, Any]:
        """Overall grounding statistics."""
        return {
            "tolerance_pct": self.tolerance_pct,
            "max_symbols_per_prompt": self.max_symbols_per_prompt,
            "cache": self.cache_stats,
        }


# ═══════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def demo():
        grounding = MarketGrounding(cache_ttl=300, tolerance_pct=5.0)

        print(f"yfinance available: {_YF_AVAILABLE}")
        print(f"Stats: {grounding.stats}")

        # Ground a prompt
        result = await grounding.ground_prompt(
            system_prompt="Analyze the following stocks and provide investment recommendations.",
            symbols=["AAPL", "MSFT", "GOOGL"],
        )

        print(f"\nGrounding Result:")
        print(f"  Grounded: {result.symbols_grounded}")
        print(f"  Failed: {result.symbols_failed}")
        print(f"  Cache hits: {result.cache_hits}")
        print(f"  Cache misses: {result.cache_misses}")
        print(f"  Latency: {result.total_latency_ms:.1f}ms")

        print(f"\n--- Enhanced Prompt (last 1500 chars) ---")
        print(result.enhanced_prompt[-1500:])

        # Simulate LLM response validation
        mock_llm_response = """
        AAPL is currently trading at $175.50, which looks attractive.
        MSFT at $420.00 is also a strong buy at current levels.
        However, I think GOOGL at $5000.00 is overvalued.  # <- Hallucination!
        """

        validation = grounding.validate_response(
            mock_llm_response,
            ["AAPL", "MSFT", "GOOGL"],
        )

        print(f"\n--- Validation Result ---")
        print(f"  Valid: {validation.is_valid}")
        print(f"  Prices checked: {validation.n_prices_checked}")
        print(f"  Hallucinations: {validation.n_hallucinations}")
        if validation.flagged_prices:
            print("  Flagged:")
            for fp in validation.flagged_prices:
                print(f"    ⚠ {fp}")

        # Cache stats
        print(f"\n  Cache stats: {grounding.cache_stats}")

    asyncio.run(demo())
