# agents.tools.sentiment

## Class: 

Classification of news events by impact type.

*Line: 44*

---

## Class: 

Classify news items by event type and compute sentiment scores.

**Methods:** classify_event, score_headline

*Line: 135*

---

## Class: 

Minimal TTL cache for sentiment results.

**Methods:** __init__, get, set

*Line: 210*

---

## Class: 

Sentiment analysis tool for agent consumption.

Aggregates news headlines from multiple sources, classifies events,
and produces structured sentiment data with confidence scores.

When no news APIs are configured or available, the tool gracefully
degrades and returns low-confidence neutral sentiment.

Usage::

    tool = SentimentTool()
    result = await tool.analyze("AAPL")
    print(result["overall_score"])  # -1.0 to +1.0
    print(result["confidence"])     # 0.0 to 1.0

**Methods:** __init__, _score_news_items, _aggregate_sentiment, _compute_social_sentiment, _count_event_types

*Line: 231*

---

## Function: 

Get or create the default SentimentTool instance.

*Line: 585*

---

## Function: 

Classify a news headline into an event type.

Args:
    headline: News headline text.

Returns:
    NewsEventType enum value.

*Line: 139*

---

## Function: 

Score a news headline for sentiment and confidence.

Args:
    headline: News headline text.

Returns:
    Tuple of (sentiment_score, confidence).
    sentiment_score: -1.0 to +1.0
    confidence: 0.0 to 1.0

*Line: 165*

---

## Function: 

*Line: 213*

---

## Function: 

*Line: 217*

---

## Function: 

*Line: 227*

---

## Function: 

Initialize the SentimentTool.

Args:
    cache_ttl: Cache TTL in seconds for sentiment results (default 300).

*Line: 249*

---

## Function: 

Score each news headline for sentiment and event classification.

Args:
    raw_headlines: List of headline dicts.
    symbol: Ticker symbol for context.

Returns:
    List of scored news items.

*Line: 430*

---

## Function: 

Aggregate individual news scores into an overall sentiment score.

Uses confidence-weighted average and applies time decay
approximation (more recent headlines weighted more).

Args:
    scored_items: List of scored news items.

Returns:
    Dict with 'score', 'confidence', 'label'.

*Line: 468*

---

## Function: 

Compute simplified social sentiment.

In production, this would connect to Twitter/Reddit APIs.
For now, provides a structured placeholder with basic inference
from available headline volume and sentiment.

Args:
    symbol: Ticker symbol.
    headlines: Available headlines for context.

Returns:
    Dict with social sentiment summary.

*Line: 523*

---

## Function: 

Count events by type.

*Line: 567*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 27*

---

## Function: 

*Line: 31*

---

