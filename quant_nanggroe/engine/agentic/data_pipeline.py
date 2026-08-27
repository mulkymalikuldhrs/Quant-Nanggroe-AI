"""Data Pipeline — Multi-source: MT5 + News + COT + Sentiment."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger("QNA.DataPipeline")

_DATA_DIR = Path(__file__).resolve().parents[3] / "data"
_PIPELINE_DB = _DATA_DIR / "data_pipeline.db"

# Singleton lock
_singleton_lock = threading.Lock()
_singleton_instance: DataPipeline | None = None


@dataclass
class NewsItem:
    title: str
    source: str
    sentiment: float  # -1.0 to 1.0
    relevance: float  # 0.0 to 1.0
    timestamp: str
    url: str = ""
    symbols: list[str] = field(default_factory=list)


@dataclass
class COTReport:
    asset: str
    date: str
    long_institutional: int
    short_institutional: int
    long_speculative: int
    short_speculative: int
    net_long: int
    net_change: int
    classification: str  # "extreme_long", "extreme_short", "neutral"


@dataclass
class MarketSentiment:
    symbol: str
    timestamp: str
    news_sentiment: float = 0.0
    cot_bias: float = 0.0  # -1 to 1
    dxy_correlation: float = 0.0
    vix_level: float = 0.0
    overall_score: float = 0.0  # -1 to 1
    confidence: float = 0.0


class DataPipeline:
    """Multi-source data aggregation for committee agents. Thread-safe singleton."""

    def __new__(cls, db_path: Path | None = None):
        global _singleton_instance
        if _singleton_instance is None:
            with _singleton_lock:
                if _singleton_instance is None:
                    inst = super().__new__(cls)
                    inst._db = db_path or _PIPELINE_DB
                    inst._init_db()
                    _singleton_instance = inst
        return _singleton_instance

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(str(self._db), timeout=5)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _init_db(self) -> None:
        with self._conn() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT, source TEXT, sentiment REAL, relevance REAL,
                    timestamp TEXT, url TEXT, symbols TEXT
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS cot_reports (
                    asset TEXT, date TEXT, long_institutional INTEGER,
                    short_institutional INTEGER, long_speculative INTEGER,
                    short_speculative INTEGER, net_long INTEGER, net_change INTEGER,
                    classification TEXT, PRIMARY KEY (asset, date)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_cache (
                    symbol TEXT PRIMARY KEY, news_sentiment REAL, cot_bias REAL,
                    dxy_correlation REAL, vix_level REAL, overall_score REAL,
                    confidence REAL, timestamp TEXT
                )
            """)

    def fetch_news(self, symbols: list[str] | None = None,
                   max_items: int = 50) -> list[NewsItem]:
        """Fetch news from free sources (Finnhub, fallback to cached)."""
        items = []
        try:
            import urllib.request
            url = "https://finnhub.io/api/v1/news?category=general"
            req = urllib.request.Request(url, headers={"User-Agent": "QNA/8.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                for item in data[:max_items]:
                    title = item.get("headline", "")
                    source = item.get("source", "")
                    summary = item.get("summary", "")
                    pos_words = ["surge", "rally", "gain", "bull", "rise", "up", "high", "growth"]
                    neg_words = ["crash", "drop", "fall", "bear", "down", "low", "loss", "recession"]
                    text = (title + " " + summary).lower()
                    pos = sum(1 for w in pos_words if w in text)
                    neg = sum(1 for w in neg_words if w in text)
                    total = pos + neg
                    sentiment = (pos - neg) / total if total > 0 else 0.0

                    items.append(NewsItem(
                        title=title, source=source, sentiment=sentiment,
                        relevance=0.5,
                        timestamp=item.get("datetime", datetime.now(timezone.utc).isoformat()),
                        url=item.get("url", ""),
                        symbols=self._extract_symbols(title + " " + summary)))

                with self._conn() as con:
                    for item in items:
                        con.execute(
                            "INSERT INTO news (title, source, sentiment, relevance, timestamp, url, symbols) VALUES (?,?,?,?,?,?,?)",
                            (item.title, item.source, item.sentiment, item.relevance,
                             item.timestamp, item.url, json.dumps(item.symbols)))
                logger.info("Fetched %d news items from Finnhub", len(items))
        except Exception as exc:
            logger.warning("News fetch failed: %s — using cache", exc)
            items = self._get_cached_news(max_items)

        return items

    def fetch_cot(self, asset: str = "EUR") -> COTReport | None:
        """Fetch COT data from CFTC (via free CSV)."""
        try:
            import urllib.request
            url = "https://www.cftc.gov/dea/futures/other_lf.htm"
            req = urllib.request.Request(url, headers={"User-Agent": "QNA/8.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                lines = html.split("\n")
                for line in lines:
                    if asset in line.upper():
                        parts = [p.strip() for p in line.split(",") if p.strip()]
                        if len(parts) >= 8:
                            report = COTReport(
                                asset=asset,
                                date=parts[0] if parts else datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                long_institutional=int(parts[1]) if parts[1].lstrip("-").isdigit() else 0,
                                short_institutional=int(parts[2]) if parts[2].lstrip("-").isdigit() else 0,
                                long_speculative=int(parts[3]) if parts[3].lstrip("-").isdigit() else 0,
                                short_speculative=int(parts[4]) if parts[4].lstrip("-").isdigit() else 0,
                                net_long=0, net_change=0, classification="neutral")
                            report.net_long = report.long_institutional - report.short_institutional
                            if report.net_long > 50000:
                                report.classification = "extreme_long"
                            elif report.net_long < -50000:
                                report.classification = "extreme_short"
                            self._cache_cot(report)
                            return report
        except Exception as exc:
            logger.debug("COT fetch failed for %s: %s", asset, exc)

        return self._get_cached_cot(asset)

    def get_sentiment(self, symbol: str) -> MarketSentiment:
        """Get aggregated sentiment for a symbol from all sources."""
        try:
            with self._conn() as con:
                con.row_factory = sqlite3.Row
                row = con.execute(
                    "SELECT * FROM sentiment_cache WHERE symbol=?", (symbol,)).fetchone()
                if row:
                    return MarketSentiment(
                        symbol=symbol,
                        news_sentiment=row["news_sentiment"],
                        cot_bias=row["cot_bias"],
                        dxy_correlation=row["dxy_correlation"],
                        overall_score=row["overall_score"],
                        confidence=row["confidence"],
                        timestamp=row["timestamp"])
        except Exception:
            pass

        sentiment = MarketSentiment(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc).isoformat())

        try:
            with self._conn() as con:
                rows = con.execute(
                    """SELECT sentiment FROM news
                       WHERE symbols LIKE ? ORDER BY timestamp DESC LIMIT 10""",
                    (f'%"{symbol}"%',)).fetchall()
                if rows:
                    sentiment.news_sentiment = float(np.mean([r[0] for r in rows]))
        except Exception:
            pass

        base = symbol.replace("USD", "").replace("XAU", "")[:3]
        if base:
            cot = self.fetch_cot(base)
            if cot:
                if cot.classification == "extreme_long":
                    sentiment.cot_bias = 0.5
                elif cot.classification == "extreme_short":
                    sentiment.cot_bias = -0.5
                else:
                    sentiment.cot_bias = cot.net_long / 100000

        sentiment.overall_score = (
            0.4 * sentiment.news_sentiment +
            0.3 * sentiment.cot_bias +
            0.3 * sentiment.dxy_correlation
        )
        sentiment.confidence = min(1.0, abs(sentiment.overall_score) + 0.2)

        self._cache_sentiment(sentiment)
        return sentiment

    def _extract_symbols(self, text: str) -> list[str]:
        import re
        pairs = re.findall(r'\b(EUR|GBP|USD|JPY|AUD|CAD|CHF|NZD|XAU|BTC)\s*/\s*(EUR|GBP|USD|JPY|AUD|CAD|CHF|NZD)\b',
                          text.upper())
        return [f"{a}{b}" for a, b in pairs]

    def _get_cached_news(self, limit: int) -> list[NewsItem]:
        try:
            with self._conn() as con:
                rows = con.execute(
                    "SELECT title, source, sentiment, relevance, timestamp, url, symbols FROM news ORDER BY timestamp DESC LIMIT ?",
                    (limit,)).fetchall()
                return [NewsItem(title=r[0], source=r[1], sentiment=r[2], relevance=r[3],
                                 timestamp=r[4], url=r[5], symbols=json.loads(r[6]) if r[6] else [])
                        for r in rows]
        except Exception:
            return []

    def _cache_cot(self, report: COTReport) -> None:
        try:
            with self._conn() as con:
                con.execute(
                    "INSERT OR REPLACE INTO cot_reports VALUES (?,?,?,?,?,?,?,?,?)",
                    (report.asset, report.date, report.long_institutional,
                     report.short_institutional, report.long_speculative,
                     report.short_speculative, report.net_long, report.net_change,
                     report.classification))
        except Exception:
            pass

    def _get_cached_cot(self, asset: str) -> COTReport | None:
        try:
            with self._conn() as con:
                row = con.execute(
                    "SELECT * FROM cot_reports WHERE asset=? ORDER BY date DESC LIMIT 1",
                    (asset,)).fetchone()
                if row:
                    return COTReport(
                        asset=row[0], date=row[1], long_institutional=row[2],
                        short_institutional=row[3], long_speculative=row[4],
                        short_speculative=row[5], net_long=row[6], net_change=row[7],
                        classification=row[8])
        except Exception:
            pass
        return None

    def _cache_sentiment(self, sentiment: MarketSentiment) -> None:
        try:
            with self._conn() as con:
                con.execute(
                    "INSERT OR REPLACE INTO sentiment_cache VALUES (?,?,?,?,?,?,?,?)",
                    (sentiment.symbol, sentiment.news_sentiment, sentiment.cot_bias,
                     sentiment.dxy_correlation, sentiment.vix_level,
                     sentiment.overall_score, sentiment.confidence, sentiment.timestamp))
        except Exception:
            pass
