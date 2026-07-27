# News Scanner Daemon — Fetches Google News RSS with sentiment scoring
# Ported from TradeBobbyTerminal/dashboard/news-scanner.js

import json
import time
import logging
import re
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree as ET

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# News RSS feeds organized by category
NEWS_FEEDS = {
    "macro": [
        "https://news.google.com/rss/search?q=federal+reserve+interest+rates&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=inflation+CPI+PPI&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=GDP+economic+growth&hl=en-US&gl=US&ceid=US:en",
    ],
    "crypto": [
        "https://news.google.com/rss/search?q=bitcoin+crypto&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=ethereum+crypto&hl=en-US&gl=US&ceid=US:en",
    ],
    "commodities": [
        "https://news.google.com/rss/search?q=gold+price+commodity&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=oil+crude+OPEC&hl=en-US&gl=US&ceid=US:en",
    ],
    "earnings": [
        "https://news.google.com/rss/search?q=earnings+report+quarterly&hl=en-US&gl=US&ceid=US:en",
    ],
    "geopolitics": [
        "https://news.google.com/rss/search?q=geopolitics+trade+war+sanctions&hl=en-US&gl=US&ceid=US:en",
    ],
}

# Sentiment keywords (simple rule-based)
BULLISH_KEYWORDS = [
    "rally", "surge", "jump", "soar", "bull", "bullish", "gain", "rise", "breakout",
    "record high", "all-time high", "recovery", "optimism", "dovish", "rate cut",
    "stimulus", "growth", "strong", "beat expectations",
]
BEARISH_KEYWORDS = [
    "crash", "plunge", "drop", "fall", "bear", "bearish", "decline", "loss", "breakdown",
    "record low", "recession", "pessimism", "hawkish", "rate hike", "tightening",
    "weakness", "miss expectations", "default", "crisis",
]


def score_sentiment(text: str) -> dict:
    """Simple rule-based sentiment scoring."""
    text_lower = text.lower()
    bull_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bear_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)
    total = bull_count + bear_count

    if total == 0:
        score = 50
    else:
        score = int((bull_count / total) * 100)

    if score > 60:
        label = "bullish"
    elif score < 40:
        label = "bearish"
    else:
        label = "neutral"

    return {"score": score, "label": label, "bull_hits": bull_count, "bear_hits": bear_count}


class NewsScannerDaemon:
    """Fetches and scans news RSS feeds every 30 minutes."""

    def __init__(self, data_dir: str = "data/news"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.running = False

    def fetch_rss(self, url: str) -> list:
        """Fetch and parse an RSS feed."""
        if httpx is None:
            return []
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url)
                resp.raise_for_status()
                root = ET.fromstring(resp.text)
                items = []
                for item in root.findall(".//item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub_date = item.findtext("pubDate", "")
                    description = item.findtext("description", "")
                    # Strip HTML tags from description
                    description = re.sub(r"<[^>]+>", "", description)[:300]
                    sentiment = score_sentiment(f"{title} {description}")
                    items.append({
                        "title": title,
                        "link": link,
                        "pub_date": pub_date,
                        "description": description,
                        "sentiment": sentiment,
                    })
                return items[:10]  # Limit per feed
        except Exception as e:
            logger.error(f"RSS fetch failed for {url}: {e}")
            return []

    def scan_all_feeds(self) -> dict:
        """Scan all configured news feeds."""
        all_news = {}
        total_count = 0

        for category, urls in NEWS_FEEDS.items():
            category_items = []
            for url in urls:
                items = self.fetch_rss(url)
                category_items.extend(items)
            all_news[category] = category_items
            total_count += len(category_items)

        # Calculate aggregate sentiment per category
        sentiments = {}
        for category, items in all_news.items():
            if items:
                avg_score = sum(i["sentiment"]["score"] for i in items) / len(items)
                sentiments[category] = {
                    "avg_score": round(avg_score),
                    "label": "bullish" if avg_score > 60 else "bearish" if avg_score < 40 else "neutral",
                    "count": len(items),
                }

        return {"news": all_news, "sentiments": sentiments, "total_count": total_count}

    def run_once(self) -> dict:
        """Run one scan cycle."""
        logger.info("Scanning news feeds...")
        result = self.scan_all_feeds()

        output = {
            **result,
            "updated_at": datetime.now().isoformat(),
        }

        out_file = self.data_dir / "news_scan.json"
        out_file.write_text(json.dumps(output, indent=2))
        logger.info(f"News scan saved to {out_file} ({result['total_count']} articles)")

        return output

    def stop(self):
        self.running = False
