"""OSINT intelligence sweep engine.

Implements the :class:`OSINTSource` that aggregates intelligence from
27 open-source intelligence categories covering geopolitical events,
conflict zones, satellite imagery analysis, cyber threat intelligence,
supply chain disruptions, and more.

Each category maps to a curated set of publicly available data feeds
and APIs.  The engine normalises, deduplicates, and scores results
by relevance and timeliness.

**Live data mode** – When ``_LIVE_MODE = True`` (default), the source
calls the **GDELT API** (free, no key) and parses **RSS feeds** from
Reuters, AP, etc.  If all live calls fail the module falls back to
:data:`SAMPLE_OSINT_DATABASE` and emits a ``logging.warning`` so
operators are never silently served stale data.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import aiohttp
import feedparser
from cachetools import TTLCache

from .base import (
    SourceCategory,
    SourceConfig,
    SourceItem,
    SourceProvider,
    SourceReliability,
    SourceResult,
    SourceStatus,
)

logger = logging.getLogger(__name__)

# ── Feature flag ──────────────────────────────────────────────────────────

_LIVE_MODE: bool = True
"""When ``True`` the source calls real APIs.  Set to ``False`` to force
SAMPLE_DATA usage (useful in offline tests)."""

_API_TIMEOUT: float = 10.0
"""Default timeout in seconds for every outbound HTTP call."""

_CACHE_TTL: int = 1800  # 30 minutes
"""TTL for the OSINT data cache (seconds)."""

_UA = "Quant-Nanggroe-AI/1.0 (osint-source; +https://github.com/quant-nanggroe)"

# ── Caches ────────────────────────────────────────────────────────────────

_gdelt_cache: TTLCache[str, List[Dict[str, Any]]] = TTLCache(maxsize=128, ttl=_CACHE_TTL)
_rss_cache: TTLCache[str, List[Dict[str, Any]]] = TTLCache(maxsize=64, ttl=_CACHE_TTL)

# GDELT rate limiter: max 1 request per 5 seconds
_gdelt_semaphore = asyncio.Semaphore(1)
_gdelt_last_request: float = 0.0


# ── OSINT Category Definitions ──────────────────────────────────────────────

OSINT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    # Geopolitical (6 sources)
    "geopolitical_conflict": {
        "label": "Geopolitical Conflict Tracker",
        "category": SourceCategory.GEOPOLITICAL,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Track active armed conflicts, border disputes, and military mobilizations",
    },
    "geopolitical_sanctions": {
        "label": "Sanctions & Trade Restrictions",
        "category": SourceCategory.GEOPOLITICAL,
        "reliability": SourceReliability.RELIABLE,
        "description": "Government sanctions, export controls, and trade embargoes",
    },
    "geopolitical_treaties": {
        "label": "Treaties & Diplomatic Events",
        "category": SourceCategory.GEOPOLITICAL,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "International agreements, diplomatic summits, and treaty changes",
    },
    "geopolitical_elections": {
        "label": "Elections & Political Transitions",
        "category": SourceCategory.GEOPOLITICAL,
        "reliability": SourceReliability.FAIRLY_RELIABLE,
        "description": "Election results, regime changes, and political transitions",
    },
    "geopolitical_nationalism": {
        "label": "Nationalism & Separatism Monitor",
        "category": SourceCategory.GEOPOLITICAL,
        "reliability": SourceReliability.FAIRLY_RELIABLE,
        "description": "Independence movements, nationalist sentiment, and separatist activities",
    },
    "geopolitical_maritime": {
        "label": "Maritime Disputes & Piracy",
        "category": SourceCategory.GEOPOLITICAL,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Maritime boundary disputes, piracy incidents, and naval tensions",
    },
    # Economic (5 sources)
    "economic_gdp": {
        "label": "GDP & Growth Indicators",
        "category": SourceCategory.ECONOMIC,
        "reliability": SourceReliability.RELIABLE,
        "description": "National GDP figures, growth rates, and economic forecasts",
    },
    "economic_inflation": {
        "label": "Inflation & CPI Tracker",
        "category": SourceCategory.ECONOMIC,
        "reliability": SourceReliability.RELIABLE,
        "description": "Consumer price indices, inflation rates, and purchasing power data",
    },
    "economic_employment": {
        "label": "Employment & Labor Market",
        "category": SourceCategory.ECONOMIC,
        "reliability": SourceReliability.RELIABLE,
        "description": "Unemployment rates, job creation data, and labor force statistics",
    },
    "economic_trade": {
        "label": "International Trade Flows",
        "category": SourceCategory.ECONOMIC,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Trade balances, import/export data, and trade agreement impacts",
    },
    "economic_central_banks": {
        "label": "Central Bank Policy Monitor",
        "category": SourceCategory.ECONOMIC,
        "reliability": SourceReliability.RELIABLE,
        "description": "Interest rate decisions, quantitative easing, and monetary policy shifts",
    },
    # Conflict (5 sources)
    "conflict_ukraine": {
        "label": "Ukraine Conflict Monitor",
        "category": SourceCategory.CONFLICT,
        "reliability": SourceReliability.FAIRLY_RELIABLE,
        "description": "Military movements, territorial changes, and civilian impact in Ukraine",
    },
    "conflict_middle_east": {
        "label": "Middle East Conflict Tracker",
        "category": SourceCategory.CONFLICT,
        "reliability": SourceReliability.FAIRLY_RELIABLE,
        "description": "Regional tensions, proxy conflicts, and peace negotiations",
    },
    "conflict_africa": {
        "label": "African Conflict Monitor",
        "category": SourceCategory.CONFLICT,
        "reliability": SourceReliability.FAIRLY_RELIABLE,
        "description": "Civil wars, insurgencies, and peacekeeping operations in Africa",
    },
    "conflict_asia": {
        "label": "Asia-Pacific Security",
        "category": SourceCategory.CONFLICT,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Territorial disputes, military buildups, and security alliances",
    },
    "conflict_terrorism": {
        "label": "Terrorism & Extremism Tracker",
        "category": SourceCategory.CONFLICT,
        "reliability": SourceReliability.FAIRLY_RELIABLE,
        "description": "Terrorist incidents, extremist group activities, and counter-terrorism",
    },
    # Satellite & Remote Sensing (4 sources)
    "satellite_imagery": {
        "label": "Satellite Imagery Analysis",
        "category": SourceCategory.SATELLITE,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Commercial satellite imagery for military, environmental, and infrastructure analysis",
    },
    "satellite_weather": {
        "label": "Weather & Climate Satellite Data",
        "category": SourceCategory.SATELLITE,
        "reliability": SourceReliability.RELIABLE,
        "description": "Weather patterns, climate anomalies, and natural disaster tracking",
    },
    "satellite_ais": {
        "label": "AIS Vessel Tracking",
        "category": SourceCategory.SATELLITE,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Ship tracking via AIS data for maritime intelligence",
    },
    "satellite_flight": {
        "label": "Aviation & Flight Tracking",
        "category": SourceCategory.SATELLITE,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Flight tracking data, airport activity, and airspace closures",
    },
    # Market & Financial (4 sources)
    "market_equities": {
        "label": "Global Equity Markets",
        "category": SourceCategory.MARKET,
        "reliability": SourceReliability.RELIABLE,
        "description": "Stock indices, sector performance, and market sentiment",
    },
    "market_commodities": {
        "label": "Commodity Prices & Trends",
        "category": SourceCategory.MARKET,
        "reliability": SourceReliability.RELIABLE,
        "description": "Energy, metals, agriculture commodity prices and supply disruptions",
    },
    "market_crypto": {
        "label": "Cryptocurrency Intelligence",
        "category": SourceCategory.MARKET,
        "reliability": SourceReliability.FAIRLY_RELIABLE,
        "description": "Crypto market data, on-chain analytics, and regulatory developments",
    },
    "market_forex": {
        "label": "Foreign Exchange Monitor",
        "category": SourceCategory.MARKET,
        "reliability": SourceReliability.RELIABLE,
        "description": "Currency pairs, central bank interventions, and forex volatility",
    },
    # Social & Cyber (3 sources)
    "social_media_intel": {
        "label": "Social Media Intelligence",
        "category": SourceCategory.SOCIAL,
        "reliability": SourceReliability.NOT_USUALLY_RELIABLE,
        "description": "Social media trend analysis, sentiment tracking, and bot detection",
    },
    "cyber_threats": {
        "label": "Cyber Threat Intelligence",
        "category": SourceCategory.CYBER,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Malware campaigns, data breaches, and threat actor tracking",
    },
    "cyber_infrastructure": {
        "label": "Critical Infrastructure Monitor",
        "category": SourceCategory.CYBER,
        "reliability": SourceReliability.USUALLY_RELIABLE,
        "description": "Internet outages, DNS disruptions, and infrastructure attacks",
    },
}

# Total: 27 sources


# ── GDELT category → search query mapping ───────────────────────────────────

_GDELT_QUERIES: Dict[str, str] = {
    "geopolitical_conflict": "conflict war military",
    "geopolitical_sanctions": "sanctions trade embargo export controls",
    "geopolitical_treaties": "treaty diplomacy summit agreement",
    "geopolitical_elections": "election vote political transition",
    "geopolitical_nationalism": "nationalism separatism independence",
    "geopolitical_maritime": "maritime piracy naval dispute",
    "economic_gdp": "GDP growth economic forecast",
    "economic_inflation": "inflation CPI consumer prices",
    "economic_employment": "employment unemployment jobs labor",
    "economic_trade": "trade imports exports tariff",
    "economic_central_banks": "central bank interest rate monetary policy",
    "conflict_ukraine": "Ukraine war Russia",
    "conflict_middle_east": "Middle East conflict Gaza Israel",
    "conflict_africa": "Africa conflict civil war insurgency",
    "conflict_asia": "Asia Pacific security Taiwan Korea",
    "conflict_terrorism": "terrorism extremism attack",
    "satellite_imagery": "satellite imagery military construction",
    "satellite_weather": "weather climate hurricane disaster",
    "satellite_ais": "shipping vessel maritime tracking",
    "satellite_flight": "aviation flight airspace",
    "market_equities": "stock market equity S&P",
    "market_commodities": "commodity oil gold copper",
    "market_crypto": "cryptocurrency bitcoin crypto regulation",
    "market_forex": "forex currency exchange rate dollar",
    "social_media_intel": "social media disinformation influence",
    "cyber_threats": "cyber attack malware breach vulnerability",
    "cyber_infrastructure": "internet outage DNS infrastructure",
}

# ── RSS feed URLs ───────────────────────────────────────────────────────────

_RSS_FEEDS: Dict[str, List[str]] = {
    "geopolitical_conflict": [
        "https://feeds.reuters.com/reuters/worldNews",
    ],
    "geopolitical_sanctions": [
        "https://feeds.reuters.com/reuters/businessNews",
    ],
    "economic_gdp": [
        "https://feeds.reuters.com/reuters/businessNews",
    ],
    "economic_inflation": [
        "https://feeds.reuters.com/reuters/businessNews",
    ],
    "market_equities": [
        "https://feeds.reuters.com/reuters/businessNews",
    ],
    "market_commodities": [
        "https://feeds.reuters.com/reuters/commoditiesNews",
    ],
    "cyber_threats": [
        "https://feeds.reuters.com/reuters/technologyNews",
    ],
    "conflict_ukraine": [
        "https://feeds.reuters.com/reuters/worldNews",
    ],
    "conflict_middle_east": [
        "https://feeds.reuters.com/reuters/worldNews",
    ],
}


# ── Sample / fallback data ──────────────────────────────────────────────────

SAMPLE_OSINT_DATABASE: Dict[str, List[Dict[str, str]]] = {
    "geopolitical_conflict": [
        {"title": "Border tensions escalate in South Caucasus", "summary": "Armenia-Azerbaijan border dispute intensifies with reported troop movements near Nagorno-Karabakh", "content": "Satellite imagery confirms military buildup along the Line of Contact. International observers report increased ceasefire violations."},
        {"title": "South China Sea naval deployment detected", "summary": "Multiple PLA Navy vessels sighted near Spratly Islands", "content": "Commercial satellite imagery shows at least 5 warships in the vicinity. Regional allies have increased maritime patrols."},
        {"title": "Korean Peninsula military exercise begins", "summary": "Joint US-South Korea military drills commence", "content": "Annual Freedom Shield exercise involves 15,000 troops. DPRK issues statement condemning the exercises."},
    ],
    "geopolitical_sanctions": [
        {"title": "EU extends sanctions against Russia", "summary": "European Council approves 14th sanctions package", "content": "New measures target LNG transshipment, shadow fleet operations, and sanctions evasion through third countries."},
        {"title": "US imposes export controls on semiconductors", "summary": "Bureau of Industry and Security expands chip export restrictions", "content": "New rules cover advanced computing chips, semiconductor manufacturing equipment, and cloud computing services."},
        {"title": "Iran oil sanctions enforcement tightened", "summary": "Treasury Department designates new network of sanctions evaders", "content": "Network spans UAE, Turkey, and Oman, facilitating billions in illicit oil trades."},
    ],
    "geopolitical_treaties": [
        {"title": "NATO accession protocol signed for new member", "summary": "Alliance unanimously approves expansion", "content": "Accession protocol forwarded to national parliaments for ratification. Expected completion within 6 months."},
        {"title": "Bilateral trade agreement reached in Pacific region", "summary": "Major economies finalize comprehensive trade deal", "content": "Agreement covers digital trade, intellectual property, and environmental standards. Implementation timeline set for 18 months."},
    ],
    "geopolitical_elections": [
        {"title": "National elections produce coalition government", "summary": "No single party achieves majority in parliamentary elections", "content": "Coalition negotiations expected to take several weeks. Markets show moderate volatility in response."},
        {"title": "Presidential transition timeline announced", "summary": "Outgoing administration sets handover schedule", "content": "Transition period of 60 days established. Policy continuity expected in key areas."},
    ],
    "geopolitical_nationalism": [
        {"title": "Catalan independence referendum debate resumes", "summary": "Spanish regional parliament discusses self-determination", "content": "Pro-independence parties hold narrow majority. Spanish constitutional court issues advisory opinion."},
        {"title": "Kurdish autonomy negotiations stall", "summary": "Baghdad-Erbil dialogue reaches impasse over oil revenue sharing", "content": "Constitutional court ruling expected to clarify federal vs. regional powers."},
    ],
    "geopolitical_maritime": [
        {"title": "Gulf of Aden piracy incident reported", "summary": "Commercial vessel boarded 50nm off Somali coast", "content": "International naval forces responding. Crew reported safe in citadel. Fourth incident this quarter."},
        {"title": "Arctic shipping route dispute escalates", "summary": "Northern Sea Route jurisdictional claims contested", "content": "Russia asserts extended jurisdiction; other Arctic Council members dispute the claim under UNCLOS."},
    ],
    "economic_gdp": [
        {"title": "Q3 GDP growth exceeds expectations", "summary": "Advanced economies show resilient growth at 2.8% annualized", "content": "Services sector drives growth; manufacturing remains sluggish. IMF revises global growth forecast upward."},
        {"title": "Emerging market growth slows", "summary": "EM GDP growth decelerates to 4.1% from 4.8%", "content": "Capital outflows and strong dollar weigh on emerging economies. China property sector remains a drag."},
    ],
    "economic_inflation": [
        {"title": "Core CPI remains elevated at 3.2%", "summary": "Sticky services inflation persists despite monetary tightening", "content": "Shelter costs continue to rise. Fed signals potential for additional rate hikes if inflation persists."},
        {"title": "Eurozone inflation falls to 2.4%", "summary": "ECB rate cuts begin to take effect", "content": "Energy prices continue to normalize. Core inflation remains above target at 2.8%."},
    ],
    "economic_employment": [
        {"title": "US nonfarm payrolls add 275K jobs", "summary": "Labor market shows continued resilience", "content": "Unemployment rate edges up to 3.9%. Wage growth moderates to 4.0% year-over-year."},
        {"title": "Global tech layoffs accelerate", "summary": "Major technology companies announce workforce reductions", "content": "Over 50,000 positions eliminated across sector. AI automation cited as contributing factor."},
    ],
    "economic_trade": [
        {"title": "Global trade volumes decline 1.2%", "summary": "WTO reports contraction in merchandise trade", "content": "Geopolitical fragmentation and tariff barriers contributing to decline. Container shipping rates drop 15%."},
        {"title": "Nearshoring trend reshapes supply chains", "summary": "Companies diversify manufacturing away from single-source dependency", "content": "Mexico and Vietnam emerge as primary beneficiaries of supply chain diversification."},
    ],
    "economic_central_banks": [
        {"title": "Federal Reserve holds rates steady", "summary": "FOMC maintains federal funds rate at 5.25-5.50%", "content": "Dot plot suggests 3 cuts in 2025. Powell emphasizes data-dependent approach."},
        {"title": "BOJ ends negative interest rate policy", "summary": "Bank of Japan raises rates for first time since 2007", "content": "Rate set at 0-0.1%. Yen strengthens on announcement. Yield curve control framework modified."},
    ],
    "conflict_ukraine": [
        {"title": "Eastern front line stabilizes", "summary": "Defensive positions consolidate along Donetsk sector", "content": "Both sides report heavy artillery exchanges. Civilian evacuation orders issued for 3 settlements."},
        {"title": "Infrastructure attacks intensify", "summary": "Energy grid targeted in multi-region strikes", "content": "Emergency power outages implemented. Repair crews working to restore electricity to affected regions."},
    ],
    "conflict_middle_east": [
        {"title": "Ceasefire negotiations resume", "summary": "International mediators present new proposal", "content": "Proposal includes phased hostage release and humanitarian corridor expansion. Both sides reviewing terms."},
        {"title": "Red Sea shipping disruptions continue", "summary": "Houthi attacks force continued rerouting of commercial vessels", "content": "Insurance costs for Red Sea transit rise 400%. Shipping delays average 2-3 weeks."},
    ],
    "conflict_africa": [
        {"title": "Sudan humanitarian crisis deepens", "summary": "Fighting displaces additional 500,000 civilians", "content": "Total displaced population exceeds 8 million. Aid organizations report critical supply shortages."},
        {"title": "Sahel security deteriorates", "summary": "Armed group activity increases across Mali, Burkina Faso, and Niger", "content": "Military governments expand operations. Regional cooperation frameworks under discussion."},
    ],
    "conflict_asia": [
        {"title": "Taiwan Strait military activity increases", "summary": "PLA conducts joint exercises near median line", "content": "Multiple fighter aircraft and naval vessels detected. Taiwan defense ministry issues statement."},
        {"title": "India-China border talks progress", "summary": "Military commanders agree on disengagement at remaining friction points", "content": "Buffer zones established. Monitoring mechanisms enhanced with technology-based surveillance."},
    ],
    "conflict_terrorism": [
        {"title": "Counter-terrorism operation succeeds", "summary": "Major international operation disrupts financing network", "content": "Assets worth $150M frozen. Network spanning 12 countries dismantled. 45 arrests made."},
        {"title": "Online extremism trends detected", "summary": "Algorithmic analysis reveals shifting propaganda patterns", "content": "New platforms targeted for recruitment. AI-generated content increasingly used for radicalization."},
    ],
    "satellite_imagery": [
        {"title": "Satellite confirms new military construction", "summary": "Commercial imagery reveals expanded military facility", "content": "Analysis shows 3 new structures consistent with equipment storage. Construction began approximately 60 days ago."},
        {"title": "Deforestation detected in Amazon basin", "summary": "Satellite data shows 2,300 hectare clearing in protected area", "content": "Clearing rate 15% higher than same period last year. Environmental agencies notified."},
    ],
    "satellite_weather": [
        {"title": "El Nino conditions strengthening", "summary": "Sea surface temperatures 2.1C above average in Nino 3.4 region", "content": "Climate models predict peak in December-January. Global precipitation patterns expected to shift."},
        {"title": "Major hurricane forms in Atlantic", "summary": "Category 4 hurricane tracking toward Caribbean", "content": "Maximum sustained winds of 140 mph. Storm surge warnings issued for multiple islands."},
    ],
    "satellite_ais": [
        {"title": "Dark fleet tanker activity detected", "summary": "AIS gap analysis reveals 15 vessels conducting ship-to-ship transfers", "content": "Transfers occurring in Gulf of Oman. Estimated 2M barrels of sanctioned crude moved monthly."},
        {"title": "Port congestion index rises", "summary": "Global container port congestion reaches 7.2 on 10-point scale", "content": "Singapore and Shanghai ports most affected. Average vessel waiting time increases to 4.5 days."},
    ],
    "satellite_flight": [
        {"title": "Airspace restrictions expanded", "summary": "NOTAM issued for expanded conflict zone airspace", "content": "Airlines rerouting flights adding 30-90 minutes to affected routes. Fuel costs increase proportionally."},
        {"title": "Airport capacity constraints reported", "summary": "Major European hubs implement slot reductions", "content": "Air traffic control staffing shortages cited. 15% of scheduled flights affected by delays or cancellations."},
    ],
    "market_equities": [
        {"title": "S&P 500 reaches new all-time high", "summary": "Broad-based rally led by technology and healthcare sectors", "content": "Index closes at record level. VIX drops to 13.2. Market breadth positive with 4:1 advance-decline ratio."},
        {"title": "Emerging market equities face outflows", "summary": "Third consecutive week of EM equity fund redemptions", "content": "Total outflows reach $4.2B. Strong dollar and geopolitical risk cited as primary drivers."},
    ],
    "market_commodities": [
        {"title": "Crude oil prices surge on supply concerns", "summary": "Brent crude rises 4.2% to $92/bbl on OPEC+ production cut extension", "content": "Voluntary cuts of 2.2M bpd extended through Q2. Backwardation in forward curve steepens."},
        {"title": "Copper prices signal economic divergence", "summary": "LME copper drops 8% while gold reaches record high", "content": "Industrial demand weakness contrasts with safe-haven flows. Gold-copper ratio reaches multi-decade high."},
    ],
    "market_crypto": [
        {"title": "Bitcoin ETF inflows reach $1.2B weekly", "summary": "Institutional adoption accelerates following regulatory approvals", "content": "Total AUM across all BTC ETFs exceeds $60B. Options market shows increasing hedging activity."},
        {"title": "DeFi total value locked recovers", "summary": "TVL rises to $95B as yield farming activity increases", "content": "Ethereum liquid staking dominates with 45% share. Cross-chain bridges see renewed activity."},
    ],
    "market_forex": [
        {"title": "Dollar index strengthens to 106", "summary": "USD gains against major currencies on rate differential expectations", "content": "EUR/USD drops to 1.0650. JPY weakens to 155 despite BOJ rate hike. CNY fixed stronger than expected."},
        {"title": "Emerging market currencies under pressure", "summary": "EM FX index drops 3% as dollar strengthens", "content": "Turkish lira, Egyptian pound, and Nigerian naira among worst performers. Central banks intervene to support."},
    ],
    "social_media_intel": [
        {"title": "Coordinated influence operation detected", "summary": "Network analysis reveals cross-platform disinformation campaign", "content": "1,200 accounts identified across 4 platforms. Content focuses on election integrity narratives. Attribution analysis ongoing."},
        {"title": "Viral misinformation trend identified", "summary": "AI-generated deepfake video spreads rapidly", "content": "Video viewed 5M+ times before platform removal. Forensic analysis confirms synthetic generation. Fact-checking deployed."},
    ],
    "cyber_threats": [
        {"title": "Critical vulnerability in widely-used library", "summary": "CVSS 9.8 vulnerability disclosed in popular open-source package", "content": "Active exploitation detected in the wild. Emergency patches released. CISA adds to Known Exploited Vulnerabilities catalog."},
        {"title": "Ransomware group targets healthcare sector", "summary": "New ransomware variant exploits recent zero-day", "content": "At least 8 healthcare organizations affected. Patient data at risk. FBI and HHS issue joint advisory."},
    ],
    "cyber_infrastructure": [
        {"title": "Major cloud provider experiences outage", "summary": "Multi-region service disruption affects thousands of businesses", "content": "Root cause identified as configuration error. Services restored after 4 hours. Post-incident review ongoing."},
        {"title": "DNS hijacking campaign targets government domains", "summary": "Multiple sovereign DNS records modified in coordinated attack", "content": "Affected domains redirected to adversary-controlled servers. Certificate authorities revoke compromised certificates."},
    ],
}

# Backward-compatible alias
OSINT_DATABASE = SAMPLE_OSINT_DATABASE


# ── GDELT API helpers ────────────────────────────────────────────────────────

async def _fetch_gdelt_articles(
    session: aiohttp.ClientSession,
    query: str,
    max_records: int = 10,
) -> List[Dict[str, Any]]:
    """Fetch articles from the GDELT Doc API.

    GDELT is free, requires no key, and returns structured news data.
    Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api/

    Rate-limited to 1 request per 5 seconds as per GDELT policy.
    """
    global _gdelt_last_request

    cache_key = f"gdelt:{query}:{max_records}"
    if cache_key in _gdelt_cache:
        return _gdelt_cache[cache_key]

    # Enforce GDELT rate limit: 1 request per 5 seconds
    async with _gdelt_semaphore:
        now = time.monotonic()
        elapsed_since_last = now - _gdelt_last_request
        if elapsed_since_last < 5.0:
            await asyncio.sleep(5.0 - elapsed_since_last)
        _gdelt_last_request = time.monotonic()

    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "ArtList",
        "maxrecords": str(max_records),
        "format": "json",
        "timespan": "7d",  # last 7 days
    }
    headers = {"User-Agent": _UA, "Accept": "application/json"}
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=_API_TIMEOUT)) as resp:
            if resp.status == 429:
                logger.debug("GDELT rate limited for query=%r", query)
                return []
            if resp.status != 200:
                logger.debug("GDELT HTTP %d for query=%r", resp.status, query)
                return []
            text = await resp.text()
            # GDELT sometimes returns non-JSON; handle gracefully
            try:
                import json
                data = json.loads(text)
            except Exception:
                logger.debug("GDELT non-JSON response for query=%r", query)
                return []
    except Exception as exc:
        logger.debug("GDELT fetch failed for query=%r: %s", query, exc)
        return []

    articles: List[Dict[str, Any]] = []
    try:
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title", ""),
                "summary": article.get("title", ""),  # GDELT doesn't have a separate summary
                "content": article.get("title", ""),
                "url": article.get("url", ""),
                "published_at": article.get("seendate", ""),
                "_source": "gdelt",
                "_timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except (AttributeError, TypeError) as exc:
        logger.debug("GDELT parse error: %s", exc)
        return []

    if articles:
        _gdelt_cache[cache_key] = articles
    return articles


async def _fetch_rss_feed(
    session: aiohttp.ClientSession,
    feed_url: str,
    max_items: int = 10,
) -> List[Dict[str, Any]]:
    """Fetch and parse an RSS feed.

    Uses ``feedparser`` for robust RSS/Atom handling.
    """
    cache_key = f"rss:{feed_url}:{max_items}"
    if cache_key in _rss_cache:
        return _rss_cache[cache_key]

    headers = {"User-Agent": _UA}
    try:
        async with session.get(feed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=_API_TIMEOUT)) as resp:
            if resp.status != 200:
                logger.debug("RSS HTTP %d for %s", resp.status, feed_url)
                return []
            raw = await resp.text()
    except Exception as exc:
        logger.debug("RSS fetch failed for %s: %s", feed_url, exc)
        return []

    try:
        parsed = feedparser.parse(raw)
    except Exception as exc:
        logger.debug("RSS parse error for %s: %s", feed_url, exc)
        return []

    items: List[Dict[str, Any]] = []
    for entry in parsed.entries[:max_items]:
        summary = getattr(entry, "summary", getattr(entry, "title", ""))
        items.append({
            "title": getattr(entry, "title", ""),
            "summary": summary[:500] if summary else "",
            "content": summary[:2000] if summary else "",
            "url": getattr(entry, "link", ""),
            "published_at": getattr(entry, "published", ""),
            "_source": "rss",
            "_timestamp": datetime.now(timezone.utc).isoformat(),
        })

    if items:
        _rss_cache[cache_key] = items
    return items


# ── Source Provider ──────────────────────────────────────────────────────────


class OSINTSource(SourceProvider):
    """OSINT intelligence sweep engine.

    Aggregates intelligence from 27 open-source categories covering
    geopolitical, economic, conflict, satellite, market, social, and
    cyber domains.

    When ``_LIVE_MODE`` is ``True`` (default), each category fetches
    real data from the **GDELT API** and/or **RSS feeds**.  If all
    live sources fail for a category, the engine falls back to
    :data:`SAMPLE_OSINT_DATABASE` and logs a warning.

    Usage::

        source = OSINTSource()
        result = await source.scan(max_items=50)
        for item in result.items:
            print(item.title, item.relevance_score)
    """

    def __init__(
        self,
        config: Optional[SourceConfig] = None,
        categories: Optional[List[str]] = None,
    ):
        super().__init__(
            name="osint",
            category=SourceCategory.GEOPOLITICAL,
            reliability=SourceReliability.USUALLY_RELIABLE,
            config=config,
        )
        self._categories: Dict[str, Dict[str, Any]] = {}
        selected = categories or list(OSINT_CATEGORIES.keys())
        for cat_key in selected:
            if cat_key in OSINT_CATEGORIES:
                self._categories[cat_key] = OSINT_CATEGORIES[cat_key]
        self._seen_hashes: Set[str] = set()
        self._max_seen = 10000

    # ── Fetch (targeted query) ──────────────────────────────────────────

    async def fetch(self, query: str, max_items: int = 50, **kwargs: Any) -> SourceResult:
        """Fetch OSINT items matching a specific query.

        Searches across all enabled categories for items whose title,
        summary, or content match the query terms.

        Parameters
        ----------
        query:
            Search query string.
        max_items:
            Maximum items to return.

        Returns
        -------
        SourceResult
            Matched intelligence items.
        """
        start = time.monotonic()
        self._record_fetch()
        items: List[SourceItem] = []
        errors: List[str] = []
        query_lower = query.lower()
        query_terms = set(re.findall(r"\w+", query_lower))

        try:
            for cat_key, cat_info in self._categories.items():
                try:
                    cat_items = await self._fetch_category(
                        cat_key, cat_info, query_terms, max_items - len(items),
                    )
                    for item in cat_items:
                        h = self._hash_item(item)
                        if h not in self._seen_hashes:
                            self._seen_hashes.add(h)
                            items.append(item)
                    if len(items) >= max_items:
                        break
                except Exception as exc:
                    errors.append(f"Category {cat_key}: {exc}")
                    self._record_error()
                    logger.warning("OSINT fetch error in %s: %s", cat_key, exc)
        except Exception as exc:
            errors.append(str(exc))
            self._record_error()

        # Prune seen hashes if too large
        if len(self._seen_hashes) > self._max_seen:
            excess = len(self._seen_hashes) - self._max_seen
            for _ in range(excess):
                try:
                    self._seen_hashes.pop()
                except KeyError:
                    break

        elapsed = (time.monotonic() - start) * 1000
        return self._make_result(
            items=items[:max_items],
            total_available=len(items),
            errors=errors,
            elapsed_ms=elapsed,
        )

    # ── Scan (broad sweep) ──────────────────────────────────────────────

    async def scan(self, max_items: int = 100, **kwargs: Any) -> SourceResult:
        """Perform a broad OSINT sweep across all categories.

        Parameters
        ----------
        max_items:
            Maximum items to return across all categories.

        Returns
        -------
        SourceResult
            Latest intelligence items from all categories.
        """
        start = time.monotonic()
        self._record_scan()
        items: List[SourceItem] = []
        errors: List[str] = []

        per_category = max(1, max_items // max(1, len(self._categories)))

        try:
            # Fetch categories concurrently
            tasks = []
            for cat_key, cat_info in self._categories.items():
                tasks.append(self._scan_category(cat_key, cat_info, per_category))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for cat_key, result in zip(self._categories.keys(), results):
                if isinstance(result, Exception):
                    errors.append(f"Category {cat_key}: {result}")
                    self._record_error()
                elif isinstance(result, list):
                    for item in result:
                        h = self._hash_item(item)
                        if h not in self._seen_hashes:
                            self._seen_hashes.add(h)
                            items.append(item)
        except Exception as exc:
            errors.append(str(exc))
            self._record_error()

        # Sort by relevance score (descending) and timestamp (newest first)
        items.sort(key=lambda i: (i.relevance_score, i.timestamp), reverse=True)

        elapsed = (time.monotonic() - start) * 1000
        return self._make_result(
            items=items[:max_items],
            total_available=len(items),
            errors=errors,
            elapsed_ms=elapsed,
        )

    # ── Category-level operations ───────────────────────────────────────

    async def _fetch_category(
        self,
        cat_key: str,
        cat_info: Dict[str, Any],
        query_terms: Set[str],
        max_items: int,
    ) -> List[SourceItem]:
        """Fetch items from a single category matching query terms."""
        if max_items <= 0:
            return []

        cat_label = cat_info["label"]
        cat_category = cat_info["category"]
        cat_reliability = cat_info["reliability"]
        cat_desc = cat_info["description"]

        # Try live data first
        base_items = await self._fetch_live_category_items(cat_key, max_items)

        # Fallback to sample data
        if not base_items:
            logger.warning("Using SAMPLE_DATA - live API unavailable for %s", cat_key)
            base_items = SAMPLE_OSINT_DATABASE.get(cat_key, [
                {"title": f"Intelligence update: {cat_label}", "summary": cat_desc, "content": cat_desc},
            ])

        items: List[SourceItem] = []
        for item_data in base_items:
            # Score relevance based on query term overlap
            item_text = f"{item_data.get('title', '')} {item_data.get('summary', '')} {cat_key}".lower()
            item_terms = set(re.findall(r"\w+", item_text))
            # Include category label and key in matching so category-level queries work
            cat_text = f"{cat_label} {cat_key} {cat_desc}".lower()
            cat_terms = set(re.findall(r"\w+", cat_text))
            combined_terms = item_terms | cat_terms
            overlap = len(query_terms & combined_terms)
            if overlap > 0 or not query_terms:
                relevance = min(1.0, overlap / max(1, len(query_terms)))
                source = item_data.get("_source", "sample_data")
                ts = item_data.get("_timestamp", "")
                item = self._make_item(
                    title=item_data.get("title", ""),
                    summary=item_data.get("summary", ""),
                    content=item_data.get("content", item_data.get("summary", "")),
                    url=item_data.get("url", ""),
                    category=cat_category,
                    reliability=cat_reliability,
                    relevance_score=relevance,
                    confidence=0.6 + 0.3 * (overlap / max(1, len(query_terms))),
                    tags=[cat_key, cat_category.value, f"src:{source}"],
                    raw_data={"_source": source, "_timestamp": ts},
                )
                items.append(item)
                if len(items) >= max_items:
                    break

        return items

    async def _scan_category(
        self,
        cat_key: str,
        cat_info: Dict[str, Any],
        max_items: int,
    ) -> List[SourceItem]:
        """Scan a single category for latest items."""
        if max_items <= 0:
            return []

        cat_category = cat_info["category"]
        cat_reliability = cat_info["reliability"]
        cat_label = cat_info["label"]

        # Try live data first
        base_items = await self._fetch_live_category_items(cat_key, max_items)

        # Fallback to sample data
        if not base_items:
            logger.warning("Using SAMPLE_DATA - live API unavailable for %s", cat_key)
            base_items = SAMPLE_OSINT_DATABASE.get(cat_key, [
                {"title": f"Intelligence update: {cat_label}", "summary": cat_info["description"], "content": cat_info["description"]},
            ])

        items: List[SourceItem] = []
        for item_data in base_items[:max_items]:
            source = item_data.get("_source", "sample_data")
            ts = item_data.get("_timestamp", "")
            item = self._make_item(
                title=item_data.get("title", ""),
                summary=item_data.get("summary", ""),
                content=item_data.get("content", item_data.get("summary", "")),
                url=item_data.get("url", ""),
                category=cat_category,
                reliability=cat_reliability,
                relevance_score=0.5,
                confidence=0.7,
                tags=[cat_key, cat_category.value, f"src:{source}"],
                raw_data={"_source": source, "_timestamp": ts},
            )
            items.append(item)

        return items

    # ── Live data fetching ──────────────────────────────────────────────

    async def _fetch_live_category_items(
        self,
        cat_key: str,
        max_items: int,
    ) -> List[Dict[str, Any]]:
        """Fetch live items for a category from GDELT and RSS feeds.

        Returns an empty list (triggering fallback) if ``_LIVE_MODE``
        is ``False`` or every live call fails.
        """
        if not _LIVE_MODE:
            return []

        items: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession() as session:
            # GDELT
            gdelt_query = _GDELT_QUERIES.get(cat_key, cat_key.replace("_", " "))
            gdelt_items = await _fetch_gdelt_articles(session, gdelt_query, max_items)
            items.extend(gdelt_items)

            # RSS feeds for this category
            rss_urls = _RSS_FEEDS.get(cat_key, [])
            for rss_url in rss_urls:
                rss_items = await _fetch_rss_feed(session, rss_url, max_items)
                items.extend(rss_items)

        return items[:max_items]

    # ── Utilities ───────────────────────────────────────────────────────

    @staticmethod
    def _hash_item(item: SourceItem) -> str:
        """Create a deduplication hash for an item."""
        key = f"{item.source_name}:{item.title}:{item.summary[:100]}"
        return hashlib.md5(key.encode()).hexdigest()

    @property
    def category_count(self) -> int:
        """Number of active OSINT categories."""
        return len(self._categories)

    @property
    def available_categories(self) -> List[str]:
        """List of available category keys."""
        return list(self._categories.keys())

    async def health_check(self) -> Dict[str, Any]:
        """Check OSINT source health."""
        # Quick GDELT ping
        gdelt_ok = False
        if _LIVE_MODE:
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://api.gdeltproject.org/api/v2/doc/doc"
                    params = {"query": "test", "mode": "ArtList", "maxrecords": "1", "format": "json"}
                    headers = {"User-Agent": _UA}
                    async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                        gdelt_ok = resp.status == 200
            except Exception:
                gdelt_ok = False

        return {
            "status": self._status,
            "latency_ms": 0.0,
            "error": None,
            "categories": len(self._categories),
            "gdelt_reachable": gdelt_ok,
        }
