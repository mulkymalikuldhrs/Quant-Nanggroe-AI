"""TradeBobby News Scanner — Google News RSS intelligence.

Port of TradeBobbyTerminal/dashboard/news-scanner.js.
32 RSS feeds across 8 categories (GEO, SHIP, ENERGY, AI, METAL, MACRO, CRYPTO,
DEFENSE). Keyword-based sentiment scoring per asset class, critical trigger
detection, risk-off scoring. No API key required. 600s TTL cache.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.request import Request, urlopen

from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RSS Feeds
# ---------------------------------------------------------------------------

FEEDS: list[dict[str, str]] = [
    # GEOPOLITICS
    {"topic": "iran",          "category": "GEO",    "priority": "HIGH",
     "url": "https://news.google.com/rss/search?q=iran+hormuz+IRGC&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "russia",        "category": "GEO",    "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=russia+ukraine+sanctions+oil&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "china",         "category": "GEO",    "priority": "HIGH",
     "url": "https://news.google.com/rss/search?q=china+taiwan+trade+sanctions&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "tariffs",       "category": "GEO",    "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=trump+tariffs+china+trade&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "middle_east",   "category": "GEO",    "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=israel+lebanon+syria+gaza&hl=en-US&gl=US&ceid=US:en"},
    # SHIPPING / MARITIME CHOKEPOINTS
    {"topic": "hormuz",        "category": "SHIP",   "priority": "HIGH",
     "url": "https://news.google.com/rss/search?q=strait+of+hormuz+tanker+attack&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "suez",          "category": "SHIP",   "priority": "HIGH",
     "url": "https://news.google.com/rss/search?q=suez+canal+red+sea+houthi&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "panama",        "category": "SHIP",   "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=panama+canal+drought+shipping&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "tankers",       "category": "SHIP",   "priority": "HIGH",
     "url": "https://news.google.com/rss/search?q=oil+tanker+seized+dark+fleet&hl=en-US&gl=US&ceid=US:en"},
    # ENERGY
    {"topic": "oil",           "category": "ENERGY", "priority": "HIGH",
     "url": "https://news.google.com/rss/search?q=oil+crude+OPEC+sanctions&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "natgas",        "category": "ENERGY", "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=natural+gas+LNG+pipeline+europe&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "uranium",       "category": "ENERGY", "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=uranium+nuclear+reactor+kazatomprom&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "power_grid",    "category": "ENERGY", "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=power+grid+electricity+demand+data+center&hl=en-US&gl=US&ceid=US:en"},
    # AI / TECH
    {"topic": "ai_chips",      "category": "AI",     "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=nvidia+AI+chip+export+control&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "ai_models",     "category": "AI",     "priority": "LOW",
     "url": "https://news.google.com/rss/search?q=OpenAI+Anthropic+Google+AI+model+release&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "ai_compute",    "category": "AI",     "priority": "LOW",
     "url": "https://news.google.com/rss/search?q=data+center+AI+investment+billion&hl=en-US&gl=US&ceid=US:en"},
    # METALS / COMMODITIES
    {"topic": "gold",          "category": "METAL",  "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=gold+price+central+bank&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "silver",        "category": "METAL",  "priority": "HIGH",
     "url": "https://news.google.com/rss/search?q=silver+COMEX+squeeze&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "copper",        "category": "METAL",  "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=copper+supply+mining+chile+peru&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "platinum",      "category": "METAL",  "priority": "LOW",
     "url": "https://news.google.com/rss/search?q=platinum+palladium+deficit&hl=en-US&gl=US&ceid=US:en"},
    # MACRO
    {"topic": "fed",           "category": "MACRO",  "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=federal+reserve+rate+inflation&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "ecb",           "category": "MACRO",  "priority": "LOW",
     "url": "https://news.google.com/rss/search?q=ECB+lagarde+euro+rate&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "dollar",        "category": "MACRO",  "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=DXY+dollar+strength+yen+intervention&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "bonds",         "category": "MACRO",  "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=treasury+yield+bond+auction+10+year&hl=en-US&gl=US&ceid=US:en"},
    # CRYPTO
    {"topic": "bitcoin",       "category": "CRYPTO", "priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=bitcoin+ETF+institutional+flow&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "eth",           "category": "CRYPTO", "priority": "LOW",
     "url": "https://news.google.com/rss/search?q=ethereum+ETF+staking+upgrade&hl=en-US&gl=US&ceid=US:en"},
    # DEFENSE / MILITARY
    {"topic": "defense",       "category": "DEFENSE","priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=defense+contract+missile+raytheon+lockheed&hl=en-US&gl=US&ceid=US:en"},
    {"topic": "nato",          "category": "DEFENSE","priority": "MEDIUM",
     "url": "https://news.google.com/rss/search?q=NATO+troops+deployment+europe&hl=en-US&gl=US&ceid=US:en"},
]

# ---------------------------------------------------------------------------
# Sentiment Keywords
# ---------------------------------------------------------------------------

BULLISH_GOLD: list[str] = [
    "war", "conflict", "escalation", "sanction", "tariff", "crisis",
    "central bank buying", "safe haven", "inflation", "hedge",
    "IRGC", "hardliner", "attack", "strike", "missile", "nuclear",
    "dedollarization", "BRICS", "gold reserves", "repatriate",
]

BEARISH_GOLD: list[str] = [
    "ceasefire", "peace", "deal", "truce", "negotiation", "calm",
    "rate hike", "hawkish", "dollar strength", "risk-on",
    "resolved", "agreement", "moderate",
]

BULLISH_OIL: list[str] = [
    "hormuz", "blockade", "disruption", "sanction", "supply shock",
    "OPEC cut", "shortage", "pipeline damage", "strike", "attack",
    "embargo", "tension", "escalation", "houthi", "tanker seized",
    "dark fleet", "refinery fire", "drone strike",
]

BEARISH_OIL: list[str] = [
    "ceasefire", "deal", "increase production", "oversupply",
    "demand slump", "recession", "stockpile increase", "SPR release",
]

BULLISH_SILVER: list[str] = [
    "comex", "squeeze", "delivery failure", "industrial demand",
    "solar", "deficit", "physical shortage", "EFP", "basis",
]

BULLISH_COPPER: list[str] = [
    "supply cut", "mine strike", "grid", "electrification", "EV",
    "codelco", "deficit", "shortage",
]

BULLISH_URANIUM: list[str] = [
    "nuclear restart", "SMR", "reactor", "supply deficit",
    "kazatomprom", "enrichment", "ban russian uranium",
]

BULLISH_AI: list[str] = [
    "compute", "GPU demand", "data center", "AI investment",
    "breakthrough", "model release", "partnership", "funding",
    "billion", "capex",
]

BEARISH_AI: list[str] = [
    "bubble", "plateau", "scaling wall", "layoffs",
    "regulation", "antitrust", "chip ban",
]

BULLISH_USD: list[str] = [
    "rate hike", "hawkish", "dollar strength", "DXY", "yield",
    "tightening", "strong economy", "taper", "robust payroll",
]

BEARISH_USD: list[str] = [
    "rate cut", "dovish", "dollar weakness", "yield collapse",
    "recession", "QE", "stimulus", "easing", "weak payroll",
]

BULLISH_CRYPTO: list[str] = [
    "ETF flow", "institutional", "adoption", "halving",
    "spot ETF", "approval", "all-time high", "ATH",
]

BEARISH_CRYPTO: list[str] = [
    "ban", "crackdown", "hack", "exploit", "fraud",
    "regulation", "SEC", "delist", "dump",
]

RISK_OFF: list[str] = [
    "recession", "crash", "panic", "selloff", "volatility",
    "bank failure", "credit event", "margin call", "liquidation",
]

# ---------------------------------------------------------------------------
# Critical Triggers
# ---------------------------------------------------------------------------

CRITICAL_TRIGGERS: list[dict[str, Any]] = [
    # EXTREME
    {"word": "hormuz closed",      "impact": "EXTREME", "assets": ["XAUUSD", "USOIL", "XAGUSD"]},
    {"word": "strait closed",      "impact": "EXTREME", "assets": ["XAUUSD", "USOIL"]},
    {"word": "missile strike",     "impact": "EXTREME", "assets": ["XAUUSD", "USOIL"]},
    {"word": "war declared",       "impact": "EXTREME", "assets": ["XAUUSD", "USOIL", "XAGUSD", "NAS100"]},
    {"word": "comex delivery failure", "impact": "EXTREME", "assets": ["XAGUSD"]},
    {"word": "nuclear strike",     "impact": "EXTREME", "assets": ["XAUUSD", "USOIL", "NAS100"]},
    {"word": "bank failure",       "impact": "EXTREME", "assets": ["XAUUSD", "NAS100", "BTCUSD"]},
    # HIGH
    {"word": "IRGC",               "impact": "HIGH",    "assets": ["XAUUSD", "USOIL"]},
    {"word": "ship seized",        "impact": "HIGH",    "assets": ["USOIL", "XAUUSD"]},
    {"word": "tanker attacked",    "impact": "HIGH",    "assets": ["USOIL"]},
    {"word": "pipeline sabotage",  "impact": "HIGH",    "assets": ["USOIL", "NATGAS"]},
    {"word": "refinery fire",      "impact": "HIGH",    "assets": ["USOIL"]},
    {"word": "houthi",             "impact": "HIGH",    "assets": ["USOIL"]},
    {"word": "ceasefire breaks",   "impact": "HIGH",    "assets": ["XAUUSD", "USOIL"]},
    {"word": "silver squeeze",     "impact": "HIGH",    "assets": ["XAGUSD"]},
    {"word": "OPEC surprise",      "impact": "HIGH",    "assets": ["USOIL"]},
    {"word": "sanctions",          "impact": "HIGH",    "assets": ["USOIL", "XAUUSD"]},
    {"word": "chip ban",           "impact": "HIGH",    "assets": ["NAS100"]},
    # MEDIUM
    {"word": "rate cut",           "impact": "MEDIUM",  "assets": ["XAUUSD", "XAGUSD", "NAS100", "BTCUSD"]},
    {"word": "rate hike",          "impact": "MEDIUM",  "assets": ["XAUUSD", "XAGUSD", "NAS100", "BTCUSD"]},
    {"word": "central bank buying","impact": "MEDIUM",  "assets": ["XAUUSD"]},
    {"word": "BRICS",              "impact": "MEDIUM",  "assets": ["XAUUSD"]},
    {"word": "grid stress",        "impact": "MEDIUM",  "assets": ["NATGAS", "URANIUM"]},
    {"word": "data center",        "impact": "MEDIUM",  "assets": ["NAS100", "URANIUM", "NATGAS"]},
]

# ---------------------------------------------------------------------------
# Regex patterns (matching Google News RSS structure)
# ---------------------------------------------------------------------------

_ITEM_RE = re.compile(r"<item>([\s\S]*?)</item>")
_TITLE_RE = re.compile(r"<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</title>")
_PUBDATE_RE = re.compile(r"<pubDate>([\s\S]*?)</pubDate>")
_DESC_RE = re.compile(r"<description>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</description>")
_LINK_RE = re.compile(r"<link>([\s\S]*?)</link>")
_SOURCE_RE = re.compile(r"<source[^>]*>([\s\S]*?)</source>")
_HTML_TAG_RE = re.compile(r"<[^>]+>")

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_CACHE = TTLCache(default_ttl=600)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_rss_xml(url: str, timeout: int = 15) -> Optional[str]:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 TradeBobby/2.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        logger.debug("RSS fetch error %s: %s", url[:60], exc)
        return None


def _parse_rss_items(xml: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for m in _ITEM_RE.finditer(xml):
        content = m.group(1)
        title_m = _TITLE_RE.search(content)
        title = title_m.group(1).strip() if title_m else ""
        if not title:
            continue
        pub_m = _PUBDATE_RE.search(content)
        desc_m = _DESC_RE.search(content)
        link_m = _LINK_RE.search(content)
        src_m = _SOURCE_RE.search(content)
        desc_raw = desc_m.group(1).strip() if desc_m else ""
        desc = _HTML_TAG_RE.sub("", desc_raw)[:200]
        items.append({
            "title": title,
            "pubDate": pub_m.group(1).strip() if pub_m else "",
            "description": desc,
            "link": link_m.group(1).strip() if link_m else "",
            "source": src_m.group(1).strip() if src_m else "",
        })
    return items


def _analyze_sentiment(text: str) -> dict[str, Any]:
    lower = text.lower()
    scores: dict[str, int] = {
        "gold": 0, "oil": 0, "silver": 0, "copper": 0,
        "uranium": 0, "ai": 0, "usd": 0, "crypto": 0, "riskOff": 0,
    }
    for kw in BULLISH_GOLD:
        if kw.lower() in lower:
            scores["gold"] += 1
    for kw in BEARISH_GOLD:
        if kw.lower() in lower:
            scores["gold"] -= 1
    for kw in BULLISH_OIL:
        if kw.lower() in lower:
            scores["oil"] += 1
    for kw in BEARISH_OIL:
        if kw.lower() in lower:
            scores["oil"] -= 1
    for kw in BULLISH_SILVER:
        if kw.lower() in lower:
            scores["silver"] += 1
    for kw in BULLISH_COPPER:
        if kw.lower() in lower:
            scores["copper"] += 1
    for kw in BULLISH_URANIUM:
        if kw.lower() in lower:
            scores["uranium"] += 1
    for kw in BULLISH_AI:
        if kw.lower() in lower:
            scores["ai"] += 1
    for kw in BEARISH_AI:
        if kw.lower() in lower:
            scores["ai"] -= 1
    for kw in BULLISH_USD:
        if kw.lower() in lower:
            scores["usd"] += 1
    for kw in BEARISH_USD:
        if kw.lower() in lower:
            scores["usd"] -= 1
    for kw in BULLISH_CRYPTO:
        if kw.lower() in lower:
            scores["crypto"] += 1
    for kw in BEARISH_CRYPTO:
        if kw.lower() in lower:
            scores["crypto"] -= 1
    for kw in RISK_OFF:
        if kw.lower() in lower:
            scores["riskOff"] += 1

    triggers: list[dict[str, Any]] = []
    for t in CRITICAL_TRIGGERS:
        if t["word"].lower() in lower:
            triggers.append(dict(t))

    return {"scores": scores, "triggers": triggers}


def _priority_value(p: str) -> int:
    return 3 if p == "HIGH" else 2 if p == "MEDIUM" else 1


def _bias(avg_score: float, threshold: float = 0.3) -> str:
    if avg_score > threshold:
        return "BULLISH"
    if avg_score < -threshold:
        return "BEARISH"
    return "NEUTRAL"


def _deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        title_lower = item.get("title", "").lower().strip()
        if title_lower and title_lower not in seen:
            seen.add(title_lower)
            result.append(item)
    return result

# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class TradeBobbyNewsScanner:
    """Google News RSS intelligence scanner.

    Fetches from 30+ feeds across GEO / SHIP / ENERGY / AI / METAL / MACRO /
    CRYPTO / DEFENSE categories. Pure keyword-based (no AI calls).
    """

    def __init__(self) -> None:
        self._cache = _CACHE
        self._last_fetch: Optional[dict[str, Any]] = None

    # ── Public API ────────────────────────────────────────────────────────

    def fetch_news(self) -> dict[str, Any]:
        """Fetch all articles organized by category.

        Returns dict with keys: timestamp, total_items, categories, items.
        Items sorted by priority then recency. Deduplicated by title.
        Cached for 600s.
        """
        cache_key = "tradebobby:news"
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._last_fetch = cached
            return cached

        all_items: list[dict[str, Any]] = []
        category_stats: dict[str, dict[str, int]] = {}

        for feed in FEEDS:
            cat = feed["category"]
            xml = _fetch_rss_xml(feed["url"])
            if not xml:
                continue
            parsed = _parse_rss_items(xml)[:8]
            if cat not in category_stats:
                category_stats[cat] = {"count": 0, "triggers": 0}

            for item in parsed:
                text = f"{item['title']} {item['description']}"
                analysis = _analyze_sentiment(text)
                category_stats[cat]["count"] += 1
                trigger_count = len(analysis["triggers"])
                if trigger_count:
                    category_stats[cat]["triggers"] += trigger_count

                all_items.append({
                    "topic": feed["topic"],
                    "category": cat,
                    "priority": feed["priority"],
                    "title": item["title"],
                    "description": item["description"],
                    "pubDate": item["pubDate"],
                    "link": item["link"],
                    "source": item["source"],
                    "scores": dict(analysis["scores"]),
                    "triggers": [t["word"] for t in analysis["triggers"]],
                })

        # Deduplicate by title
        all_items = _deduplicate(all_items)

        # Sort by priority then recency
        all_items.sort(key=lambda x: (
            -_priority_value(x["priority"]),
            x.get("pubDate", "") or "",
        ))

        result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_items": len(all_items),
            "categories": category_stats,
            "items": all_items[:250],
        }
        self._cache.set(cache_key, result)
        self._last_fetch = result
        return result

    def get_asset_sentiment(self, asset: str) -> dict[str, Any]:
        """Sentiment for a specific asset (gold, oil, silver, copper, usd).

        Returns dict with raw score, average, bias label, and the confirmed
        keyword matches across all fetched articles.
        """
        news = self._last_fetch or self.fetch_news()
        items = news.get("items", [])
        if not items:
            return {"asset": asset, "raw": 0, "avg": 0.0, "bias": "NEUTRAL", "count": 0}

        asset_lower = asset.strip().lower()
        asset_map: dict[str, str] = {
            "gold": "gold", "xauusd": "gold",
            "oil": "oil", "usoil": "oil", "xagusd": "oil",
            "silver": "silver", "xag": "silver",
            "copper": "copper", "xcu": "copper",
            "usd": "usd", "dxy": "usd",
            "uranium": "uranium",
            "ai": "ai",
            "crypto": "crypto", "btc": "crypto", "eth": "crypto",
        }
        score_key = asset_map.get(asset_lower)
        if score_key is None:
            return {"asset": asset, "error": f"unknown asset: {asset}"}

        raw = sum(item["scores"].get(score_key, 0) for item in items)
        count = len(items)
        avg_score = raw / count if count else 0.0

        thresholds: dict[str, float] = {
            "gold": 0.3, "oil": 0.3, "silver": 0.2, "copper": 0.2,
            "usd": 0.2, "uranium": 0.15, "ai": 0.3, "crypto": 0.2,
        }
        thresh = thresholds.get(score_key, 0.2)

        return {
            "asset": asset,
            "raw": raw,
            "avg": round(avg_score, 2),
            "bias": _bias(avg_score, thresh),
            "count": count,
            "source": "tradebobby_news_scanner",
        }

    def get_critical_triggers(self) -> list[dict[str, Any]]:
        """Active critical triggers from current news scan.

        Each trigger: {trigger, impact, assets, title, pubDate, link, category}.
        Deduplicated by trigger word.
        """
        news = self._last_fetch or self.fetch_news()
        items = news.get("items", [])

        all_triggers: list[dict[str, Any]] = []
        seen: set[str] = set()

        for item in items:
            for tword in item.get("triggers", []):
                # Find the full trigger definition
                trigger_def = next(
                    (t for t in CRITICAL_TRIGGERS if t["word"] == tword),
                    None,
                )
                if not trigger_def:
                    continue
                key = f"{tword}|{item.get('title', '')[:40]}"
                if key in seen:
                    continue
                seen.add(key)
                all_triggers.append({
                    "trigger": tword,
                    "impact": trigger_def["impact"],
                    "assets": trigger_def["assets"],
                    "title": item.get("title", ""),
                    "pubDate": item.get("pubDate", ""),
                    "link": item.get("link", ""),
                    "category": item.get("category", ""),
                })

        return all_triggers

    def get_risk_off_score(self) -> int:
        """Risk-off score 0-100 based on risk-off keyword density.

        0 = normal, 50+ = elevated, 80+ = critical risk-off regime.
        """
        news = self._last_fetch or self.fetch_news()
        items = news.get("items", [])
        if not items:
            return 0

        total_risk_off = sum(item["scores"].get("riskOff", 0) for item in items)
        # Normalize: 1 risk-off match per item ~ 3 items → score 5
        # Cap at 100
        density = total_risk_off / max(len(items), 1)
        score = min(100, int(density * 25))
        return score

    def get_news_pulse(self) -> dict[str, Any]:
        """Combined news intelligence pulse.

        Returns a single dict with aggregate sentiment for all tracked assets,
        active critical triggers, risk-off level, and category breakdown.
        """
        news = self._last_fetch or self.fetch_news()
        items = news.get("items", [])

        if not items:
            def _empty_sentiment() -> dict[str, Any]:
                return {"raw": 0, "avg": 0.0, "bias": "NEUTRAL"}
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_items": 0,
                "sentiment": {
                    "gold": _empty_sentiment(),
                    "oil": _empty_sentiment(),
                    "silver": _empty_sentiment(),
                    "copper": _empty_sentiment(),
                    "usd": _empty_sentiment(),
                    "uranium": _empty_sentiment(),
                    "ai": _empty_sentiment(),
                    "crypto": _empty_sentiment(),
                },
                "critical_triggers": [],
                "risk_off": {"raw": 0, "level": "NORMAL", "score": 0},
                "categories": {},
            }

        # Aggregate scores
        sums: dict[str, int] = {"gold": 0, "oil": 0, "silver": 0, "copper": 0,
                                 "uranium": 0, "ai": 0, "usd": 0, "crypto": 0,
                                 "riskOff": 0}
        for item in items:
            for k in sums:
                sums[k] += item["scores"].get(k, 0)

        count = len(items)
        avg: dict[str, float] = {
            k: round(v / count, 2) for k, v in sums.items()
        }

        thresholds: dict[str, float] = {
            "gold": 0.3, "oil": 0.3, "silver": 0.2, "copper": 0.2,
            "usd": 0.2, "uranium": 0.15, "ai": 0.3, "crypto": 0.2,
        }

        sentiment: dict[str, dict[str, Any]] = {}
        for asset_name in ("gold", "oil", "silver", "copper", "usd",
                           "uranium", "ai", "crypto"):
            if asset_name == "riskOff":
                continue
            sentiment[asset_name] = {
                "raw": sums[asset_name],
                "avg": avg[asset_name],
                "bias": _bias(avg[asset_name], thresholds.get(asset_name, 0.2)),
            }

        risk_off_raw = sums["riskOff"]
        if risk_off_raw > 5:
            risk_off_level = "HIGH"
        elif risk_off_raw > 2:
            risk_off_level = "ELEVATED"
        else:
            risk_off_level = "NORMAL"

        triggers = self.get_critical_triggers()

        return {
            "timestamp": news.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "total_items": count,
            "sentiment": sentiment,
            "critical_triggers": triggers,
            "risk_off": {
                "raw": risk_off_raw,
                "level": risk_off_level,
                "score": self.get_risk_off_score(),
            },
            "categories": news.get("categories", {}),
        }
