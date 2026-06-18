"""Problem scanning engine for the AI-MultiColony organism.

Implements the Sense phase of the organism lifecycle: continuously
scanning RSS feeds, APIs, and trend data to detect problems,
opportunities, and signals that warrant action.

The sense engine normalises signals from diverse sources into a
unified :class:`Signal` model that can be processed by the decision
engine.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class SignalType(str, Enum):
    """Type of detected signal."""
    PROBLEM = "problem"
    OPPORTUNITY = "opportunity"
    THREAT = "threat"
    TREND = "trend"
    ANOMALY = "anomaly"
    EVENT = "event"


class SignalSeverity(str, Enum):
    """Severity level of a signal."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SignalSource(str, Enum):
    """Origin of the detected signal."""
    RSS_FEED = "rss_feed"
    API = "api"
    TREND_DETECTION = "trend_detection"
    THRESHOLD_ALERT = "threshold_alert"
    PATTERN_MATCH = "pattern_match"
    MANUAL = "manual"


# ── Models ───────────────────────────────────────────────────────────────────


class Signal(BaseModel):
    """A detected signal from the sense engine."""
    model_config = ConfigDict(frozen=False)

    signal_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    signal_type: SignalType = SignalType.PROBLEM
    severity: SignalSeverity = SignalSeverity.MEDIUM
    source: SignalSource = SignalSource.API
    title: str = ""
    description: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    confidence: float = 0.5
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    related_signals: List[str] = Field(default_factory=list)

    @property
    def is_urgent(self) -> bool:
        """True if signal is critical or high severity."""
        return self.severity in (SignalSeverity.CRITICAL, SignalSeverity.HIGH)


class ScanResult(BaseModel):
    """Result from a scanning operation."""
    model_config = ConfigDict(frozen=False)

    scan_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    signals: List[Signal] = Field(default_factory=list)
    total_scanned: int = 0
    new_signals: int = 0
    elapsed_ms: float = 0.0
    errors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Scanner base ─────────────────────────────────────────────────────────────


class SignalScanner:
    """Base class for signal scanners.

    Subclasses implement specific scanning logic for different
    signal sources (RSS, API, trend detection, etc.).
    """

    def __init__(self, name: str, source: SignalSource):
        self.name = name
        self.source = source
        self._scan_count: int = 0
        self._error_count: int = 0

    async def scan(self, **kwargs: Any) -> List[Signal]:
        """Perform a scan and return detected signals.

        Override in subclasses for specific scanning logic.
        """
        self._scan_count += 1
        return []

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source.value,
            "scan_count": self._scan_count,
            "error_count": self._error_count,
        }


# ── Concrete scanners ───────────────────────────────────────────────────────


class RSSScanner(SignalScanner):
    """Scans RSS/Atom feeds for signals.

    Parses feed entries and converts them to Signal objects
    based on keyword matching and content analysis.
    """

    def __init__(
        self,
        feeds: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
    ):
        super().__init__(name="rss_scanner", source=SignalSource.RSS_FEED)
        self._feeds = feeds or []
        self._keywords = set(keywords or [
            "outage", "breach", "critical", "emergency", "failure",
            "opportunity", "growth", "breakthrough", "disruption",
            "regulation", "ban", "sanction", "crisis",
        ])

    async def scan(self, **kwargs: Any) -> List[Signal]:
        """Scan RSS feeds for relevant signals."""
        self._scan_count += 1
        signals: List[Signal] = []

        for feed_url in self._feeds:
            try:
                # In production, would fetch and parse RSS
                # Here we generate representative signals
                feed_signals = await self._parse_feed(feed_url)
                signals.extend(feed_signals)
            except Exception as e:
                self._error_count += 1
                logger.warning("RSS scan error for %s: %s", feed_url, e)

        return signals

    async def _parse_feed(self, feed_url: str) -> List[Signal]:
        """Parse a single RSS feed URL."""
        # Representative signal generation
        signals: List[Signal] = []

        # Generate signals based on feed URL hash for consistency
        url_hash = hashlib.md5(feed_url.encode()).hexdigest()[:8]

        signals.append(Signal(
            signal_type=SignalType.EVENT,
            severity=SignalSeverity.LOW,
            source=SignalSource.RSS_FEED,
            title=f"Feed update from {url_hash}",
            description=f"New content detected from RSS feed",
            data={"feed_url": feed_url},
            tags=["rss", "update"],
            confidence=0.6,
        ))

        return signals


class APIScanner(SignalScanner):
    """Scans external APIs for signals.

    Polls configured API endpoints and generates signals when
    response data matches threshold or pattern criteria.
    """

    def __init__(
        self,
        endpoints: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(name="api_scanner", source=SignalSource.API)
        self._endpoints = endpoints or []

    async def scan(self, **kwargs: Any) -> List[Signal]:
        """Scan API endpoints for signals."""
        self._scan_count += 1
        signals: List[Signal] = []

        for endpoint in self._endpoints:
            try:
                ep_signals = await self._poll_endpoint(endpoint)
                signals.extend(ep_signals)
            except Exception as e:
                self._error_count += 1
                logger.warning("API scan error: %s", e)

        return signals

    async def _poll_endpoint(self, endpoint: Dict[str, Any]) -> List[Signal]:
        """Poll a single API endpoint."""
        # In production, would make actual HTTP request
        signals: List[Signal] = []

        # Check for threshold alerts
        thresholds = endpoint.get("thresholds", {})
        for metric, threshold in thresholds.items():
            signals.append(Signal(
                signal_type=SignalType.ANOMALY,
                severity=SignalSeverity.MEDIUM,
                source=SignalSource.THRESHOLD_ALERT,
                title=f"Threshold check: {metric}",
                description=f"Monitoring {metric} against threshold {threshold}",
                data={"metric": metric, "threshold": threshold},
                tags=["api", "threshold", metric],
                confidence=0.7,
            ))

        return signals


class TrendScanner(SignalScanner):
    """Detects trends and patterns in data streams.

    Analyses time-series data for emerging trends, spikes,
    and directional changes.
    """

    def __init__(
        self,
        window_size: int = 20,
        spike_threshold: float = 2.0,
        trend_threshold: float = 0.05,
    ):
        super().__init__(name="trend_scanner", source=SignalSource.TREND_DETECTION)
        self.window_size = window_size
        self.spike_threshold = spike_threshold
        self.trend_threshold = trend_threshold
        self._data_buffer: Dict[str, List[float]] = {}

    def add_data_point(self, series: str, value: float) -> None:
        """Add a data point to a series for trend analysis."""
        if series not in self._data_buffer:
            self._data_buffer[series] = []
        self._data_buffer[series].append(value)

        # Trim buffer
        if len(self._data_buffer[series]) > self.window_size * 2:
            self._data_buffer[series] = self._data_buffer[series][-self.window_size:]

    async def scan(self, **kwargs: Any) -> List[Signal]:
        """Detect trends in buffered data."""
        self._scan_count += 1
        signals: List[Signal] = []

        for series_name, values in self._data_buffer.items():
            if len(values) < 3:
                continue

            # Spike detection
            if len(values) >= 2:
                recent = values[-1]
                avg = sum(values[:-1]) / len(values[:-1])
                if avg > 0 and abs(recent - avg) / avg > self.spike_threshold:
                    signals.append(Signal(
                        signal_type=SignalType.ANOMALY,
                        severity=SignalSeverity.HIGH,
                        source=SignalSource.THRESHOLD_ALERT,
                        title=f"Spike detected in {series_name}",
                        description=f"Value {recent} deviates {abs(recent - avg) / avg:.1%} from average {avg:.2f}",
                        data={"series": series_name, "value": recent, "average": avg},
                        tags=["spike", "anomaly", series_name],
                        confidence=0.8,
                    ))

            # Trend detection (simple linear regression slope)
            if len(values) >= self.window_size:
                window = values[-self.window_size:]
                slope = self._compute_slope(window)
                if abs(slope) > self.trend_threshold:
                    direction = "upward" if slope > 0 else "downward"
                    signals.append(Signal(
                        signal_type=SignalType.TREND,
                        severity=SignalSeverity.MEDIUM,
                        source=SignalSource.TREND_DETECTION,
                        title=f"{direction.title()} trend in {series_name}",
                        description=f"Slope: {slope:.4f} (threshold: {self.trend_threshold})",
                        data={"series": series_name, "slope": slope, "direction": direction},
                        tags=["trend", direction, series_name],
                        confidence=0.7,
                    ))

        return signals

    @staticmethod
    def _compute_slope(values: List[float]) -> float:
        """Compute the slope of a simple linear regression."""
        n = len(values)
        if n < 2:
            return 0.0
        x_avg = (n - 1) / 2.0
        y_avg = sum(values) / n
        numerator = sum((i - x_avg) * (v - y_avg) for i, v in enumerate(values))
        denominator = sum((i - x_avg) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator


# ── Sense Engine ─────────────────────────────────────────────────────────────


class SenseEngine:
    """Orchestrates all signal scanners.

    Runs scanners concurrently, deduplicates signals, and
    produces a unified ScanResult.

    Usage::

        engine = SenseEngine()
        engine.add_scanner(RSSScanner(feeds=["https://example.com/feed"]))
        engine.add_scanner(TrendScanner())

        result = await engine.scan()
        for signal in result.signals:
            print(signal.title, signal.severity.value)
    """

    def __init__(self):
        self._scanners: Dict[str, SignalScanner] = {}
        self._seen_signal_hashes: Set[str] = set()
        self._max_seen = 10000
        self._scan_count: int = 0

    def add_scanner(self, scanner: SignalScanner) -> None:
        """Register a signal scanner."""
        self._scanners[scanner.name] = scanner

    def remove_scanner(self, name: str) -> bool:
        """Remove a scanner by name."""
        if name in self._scanners:
            del self._scanners[name]
            return True
        return False

    async def scan(self, **kwargs: Any) -> ScanResult:
        """Run all scanners and aggregate signals.

        Returns
        -------
        ScanResult
            Aggregated scan result with deduplicated signals.
        """
        import time
        start = time.monotonic()
        self._scan_count += 1

        all_signals: List[Signal] = []
        errors: List[str] = []
        new_count = 0

        # Run all scanners concurrently
        tasks = {
            name: asyncio.create_task(scanner.scan(**kwargs))
            for name, scanner in self._scanners.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (name, _task), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                errors.append(f"{name}: {result}")
                continue
            if isinstance(result, list):
                for signal in result:
                    h = self._hash_signal(signal)
                    if h not in self._seen_signal_hashes:
                        self._seen_signal_hashes.add(h)
                        all_signals.append(signal)
                        new_count += 1

        # Prune seen hashes
        if len(self._seen_signal_hashes) > self._max_seen:
            excess = len(self._seen_signal_hashes) - self._max_seen
            for _ in range(excess):
                try:
                    self._seen_signal_hashes.pop()
                except KeyError:
                    break

        elapsed = (time.monotonic() - start) * 1000
        return ScanResult(
            signals=all_signals,
            total_scanned=sum(len(s) if isinstance(s, list) else 0 for s in results if isinstance(s, list)),
            new_signals=new_count,
            elapsed_ms=elapsed,
            errors=errors,
        )

    @staticmethod
    def _hash_signal(signal: Signal) -> str:
        """Create a deduplication hash for a signal."""
        key = f"{signal.signal_type.value}:{signal.title}:{signal.description[:100]}"
        return hashlib.sha256(key.encode()).hexdigest()[:24]

    @property
    def scanner_count(self) -> int:
        return len(self._scanners)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "scanner_count": self.scanner_count,
            "scanners": list(self._scanners.keys()),
            "scan_count": self._scan_count,
            "seen_signals": len(self._seen_signal_hashes),
        }
