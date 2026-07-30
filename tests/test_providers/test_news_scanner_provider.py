"""Tests: TradeBobbyNewsScanner — Google News RSS intelligence.

Mocks _fetch_rss_xml (module-level helper) to inject controlled RSS XML
so the full parse + sentiment analysis pipeline executes on test data.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quant_nanggroe.providers.tradebobby.news_scanner_provider import (
    _CACHE,
    TradeBobbyNewsScanner,
)

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
 <item>
  <title><![CDATA[Iran tensions escalate — IRGC warns of Hormuz closure]]></title>
  <description>New tensions in the Strait of Hormuz as IRGC hardliners threaten attack on tankers. Central bank buying gold surges.</description>
  <link>https://example.com/1</link>
  <pubDate>Mon, 29 Jul 2026 10:00:00 GMT</pubDate>
  <source>Reuters</source>
 </item>
 <item>
  <title><![CDATA[OPEC cuts deepen as supply shock looms]]></title>
  <description>Saudi Arabia announces surprise OPEC cut amid recession fears and demand slump. Tanker seized in Red Sea by Houthi rebels.</description>
  <link>https://example.com/2</link>
  <pubDate>Mon, 29 Jul 2026 09:30:00 GMT</pubDate>
  <source>Bloomberg</source>
 </item>
 <item>
  <title><![CDATA[Fed signals dovish pivot — rate cut expectations surge]]></title>
  <description>Federal Reserve hints at easing as recession fears mount. Dollar weakness expected. Bond yields collapse.</description>
  <link>https://example.com/3</link>
  <pubDate>Mon, 29 Jul 2026 09:00:00 GMT</pubDate>
  <source>CNBC</source>
 </item>
 <item>
  <title><![CDATA[Silver COMEX squeeze intensifies — delivery failure fears]]></title>
  <description>Physical silver shortage as COMEX delivery failure looms. Industrial demand from solar sector surges.</description>
  <link>https://example.com/4</link>
  <pubDate>Mon, 29 Jul 2026 08:30:00 GMT</pubDate>
  <source>Mining.com</source>
 </item>
 <item>
  <title><![CDATA[Bitcoin ETF flows hit record as institutional adoption grows]]></title>
  <description>Spot Bitcoin ETF approval drives institutional inflows. Crypto market cap reaches all-time high.</description>
  <link>https://example.com/5</link>
  <pubDate>Mon, 29 Jul 2026 08:00:00 GMT</pubDate>
  <source>CoinDesk</source>
 </item>
 <item>
  <title><![CDATA[NATO deploys troops as Ukraine escalation continues]]></title>
  <description>NATO announces troop deployment to eastern Europe amid Russia Ukraine escalation and missile strike concerns.</description>
  <link>https://example.com/6</link>
  <pubDate>Mon, 29 Jul 2026 07:30:00 GMT</pubDate>
  <source>BBC</source>
 </item>
</channel>
</rss>"""

SAMPLE_RSS_NO_TRIGGERS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
 <item>
  <title><![CDATA[Markets quiet as calm prevails]]></title>
  <description>Trading rangebound with low activity. Peace deal talks progress.</description>
  <link>https://example.com/7</link>
  <pubDate>Mon, 29 Jul 2026 06:00:00 GMT</pubDate>
  <source>Reuters</source>
 </item>
</channel>
</rss>"""


class TestTradeBobbyNewsScannerInit(unittest.TestCase):
    """Provider construction."""

    def setUp(self):
        _CACHE.clear()
        self.provider = TradeBobbyNewsScanner()

    def test_provider_initialises(self):
        self.assertIsInstance(self.provider, TradeBobbyNewsScanner)

    def test_cache_is_wired(self):
        from quant_nanggroe.providers.tradebobby.news_scanner_provider import (
            _CACHE as module_cache,
        )
        self.assertIs(self.provider._cache, module_cache)


class TestFetchNews(unittest.TestCase):
    """fetch_news() behaviour."""

    def setUp(self):
        _CACHE.clear()
        self.provider = TradeBobbyNewsScanner()

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_fetch_news_returns_categorized_articles(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.fetch_news()
        self.assertIn("timestamp", result)
        self.assertIn("total_items", result)
        self.assertIn("categories", result)
        self.assertIn("items", result)
        self.assertGreater(result["total_items"], 0)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_fetch_news_items_have_scores_and_triggers(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.fetch_news()
        for item in result["items"]:
            self.assertIn("scores", item)
            self.assertIn("triggers", item)
            self.assertIn("category", item)
            self.assertIn("priority", item)
            self.assertIn("topic", item)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_fetch_news_deduplicates_by_title(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.fetch_news()
        titles = [i["title"] for i in result["items"]]
        self.assertEqual(len(titles), len(set(titles)))

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_fetch_news_sorts_by_priority(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.fetch_news()
        priorities = [i["priority"] for i in result["items"]]
        rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        mapped = [rank[p] for p in priorities]
        self.assertEqual(mapped, sorted(mapped, reverse=True))

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_fetch_news_graceful_on_feed_failure(self, mock_fetch):
        mock_fetch.return_value = None
        result = self.provider.fetch_news()
        self.assertEqual(result["total_items"], 0)
        self.assertEqual(result["items"], [])

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_fetch_news_preserves_source_info(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.fetch_news()
        for item in result["items"]:
            self.assertIn("title", item)
            self.assertIn("pubDate", item)
            self.assertIn("link", item)
            self.assertIn("source", item)


class TestAssetSentiment(unittest.TestCase):
    """get_asset_sentiment() behaviour."""

    def setUp(self):
        _CACHE.clear()
        self.provider = TradeBobbyNewsScanner()

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_asset_sentiment_gold_returns_score(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.get_asset_sentiment("gold")
        self.assertIn("asset", result)
        self.assertIn("raw", result)
        self.assertIn("avg", result)
        self.assertIn("bias", result)
        self.assertEqual(result["asset"], "gold")

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_asset_sentiment_oil_returns_score(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.get_asset_sentiment("oil")
        self.assertIn("asset", result)
        self.assertIn("bias", result)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_asset_sentiment_usd_returns_score(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.get_asset_sentiment("usd")
        self.assertIn("asset", result)
        self.assertIn("bias", result)

    def test_get_asset_sentiment_unknown_returns_error(self):
        self.provider._last_fetch = {
            "items": [{"scores": {"gold": 0, "oil": 0}, "title": "test"}],
            "timestamp": "2026-01-01T00:00:00",
        }
        result = self.provider.get_asset_sentiment("unknown_asset")
        self.assertIn("error", result)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_asset_sentiment_returns_bias_label(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.get_asset_sentiment("gold")
        self.assertIn(result["bias"], {"BULLISH", "BEARISH", "NEUTRAL"})


class TestCriticalTriggers(unittest.TestCase):
    """get_critical_triggers() behaviour."""

    def setUp(self):
        _CACHE.clear()
        self.provider = TradeBobbyNewsScanner()

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_critical_triggers_returns_list(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        triggers = self.provider.get_critical_triggers()
        self.assertIsInstance(triggers, list)
        for t in triggers:
            self.assertIn("trigger", t)
            self.assertIn("impact", t)
            self.assertIn("assets", t)
            self.assertIn("title", t)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_critical_triggers_detects_extreme_impacts(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        triggers = self.provider.get_critical_triggers()
        self.assertGreater(len(triggers), 0)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_critical_triggers_deduplicates(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        triggers = self.provider.get_critical_triggers()
        trigger_words = [t["trigger"] for t in triggers]
        self.assertEqual(len(trigger_words), len(set(trigger_words)))


class TestRiskOffScore(unittest.TestCase):
    """get_risk_off_score() behaviour."""

    def setUp(self):
        _CACHE.clear()
        self.provider = TradeBobbyNewsScanner()

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_risk_off_score_returns_int(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        score = self.provider.get_risk_off_score()
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_risk_off_score_zero_on_no_risk_off_keywords(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_NO_TRIGGERS
        score = self.provider.get_risk_off_score()
        self.assertEqual(score, 0)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_risk_off_score_zero_on_no_items(self, mock_fetch):
        mock_fetch.return_value = None
        score = self.provider.get_risk_off_score()
        self.assertEqual(score, 0)


class TestGetNewsPulse(unittest.TestCase):
    """get_news_pulse() combined output."""

    def setUp(self):
        _CACHE.clear()
        self.provider = TradeBobbyNewsScanner()

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_news_pulse_returns_all_fields(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.get_news_pulse()
        self.assertIn("timestamp", result)
        self.assertIn("total_items", result)
        self.assertIn("sentiment", result)
        self.assertIn("critical_triggers", result)
        self.assertIn("risk_off", result)
        self.assertIn("categories", result)

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_news_pulse_sentiment_has_all_assets(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.get_news_pulse()
        sentiment = result["sentiment"]
        for asset in ("gold", "oil", "silver", "copper", "usd", "uranium", "ai", "crypto"):
            self.assertIn(asset, sentiment)
            self.assertIn("bias", sentiment[asset])

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_get_news_pulse_risk_off_has_level(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        result = self.provider.get_news_pulse()
        risk_off = result["risk_off"]
        self.assertIn("raw", risk_off)
        self.assertIn("level", risk_off)
        self.assertIn("score", risk_off)
        self.assertIn(risk_off["level"], {"NORMAL", "ELEVATED", "HIGH"})


class TestCacheBehavior(unittest.TestCase):
    """TTLCache wired correctly."""

    def setUp(self):
        _CACHE.clear()
        self.provider = TradeBobbyNewsScanner()

    @patch("quant_nanggroe.providers.tradebobby.news_scanner_provider._fetch_rss_xml")
    def test_fetch_news_caches_on_second_call(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RSS_XML
        first = self.provider.fetch_news()
        mock_fetch.reset_mock()
        second = self.provider.fetch_news()
        self.assertEqual(first, second)
        mock_fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
