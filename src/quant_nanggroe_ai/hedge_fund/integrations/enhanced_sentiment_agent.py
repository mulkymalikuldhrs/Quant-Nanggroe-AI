"""
ENHANCED SENTIMENT AGENT - Integrates quant_hf sentiment analysis
Combines news analysis, social media monitoring, and market sentiment
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class EnhancedSentimentAgent:
    """Enhanced sentiment agent using quant_hf components"""

    def __init__(self):
        self.sentiment_agent = None
        self.news_sources = []
        self.social_media_sources = []
        self.sentiment_scores = {}

    def initialize(self):
        """Initialize sentiment analysis components"""
        try:
            from integrations.quant_hf.sentiment_agent import SentimentAgent

            self.sentiment_agent = SentimentAgent()
            print("✅ Enhanced Sentiment Agent initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize sentiment agent: {e}")
            # Fallback to mock
            self.sentiment_agent = None
            return False

    def analyze_news_sentiment(self, news_data):
        """Analyze sentiment from news sources"""
        if self.sentiment_agent and hasattr(self.sentiment_agent, "analyze_news"):
            return self.sentiment_agent.analyze_news(news_data)
        else:
            # Mock analysis
            return {"overall_sentiment": "neutral", "confidence": 0.5, "sources_analyzed": len(news_data) if isinstance(news_data, list) else 1, "key_themes": ["market", "economy", "technology"]}

    def analyze_social_sentiment(self, social_data):
        """Analyze sentiment from social media"""
        if self.sentiment_agent and hasattr(self.sentiment_agent, "analyze_social"):
            return self.sentiment_agent.analyze_social(social_data)
        else:
            # Mock analysis
            return {"overall_sentiment": "neutral", "confidence": 0.5, "platforms": ["twitter", "reddit", "discord"], "engagement_score": 0.7}

    def get_market_sentiment(self, ticker):
        """Get comprehensive market sentiment for a ticker"""
        # Combine news and social sentiment
        news_sentiment = self.analyze_news_sentiment([f"news about {ticker}"])
        social_sentiment = self.analyze_social_sentiment([f"social about {ticker}"])

        # Aggregate sentiment
        sentiments = [news_sentiment["overall_sentiment"], social_sentiment["overall_sentiment"]]
        confidence = (news_sentiment["confidence"] + social_sentiment["confidence"]) / 2

        # Determine overall sentiment
        if sentiments.count("positive") > sentiments.count("negative"):
            overall = "positive"
        elif sentiments.count("negative") > sentiments.count("positive"):
            overall = "negative"
        else:
            overall = "neutral"

        return {"ticker": ticker, "overall_sentiment": overall, "confidence": confidence, "news_sentiment": news_sentiment, "social_sentiment": social_sentiment, "recommendation": self._get_recommendation(overall, confidence)}

    def _get_recommendation(self, sentiment, confidence):
        """Get trading recommendation based on sentiment"""
        if confidence > 0.7:
            if sentiment == "positive":
                return "BUY_STRONG"
            elif sentiment == "negative":
                return "SELL_STRONG"
            else:
                return "HOLD"
        else:
            return "HOLD"


# Global instance
enhanced_sentiment_agent = EnhancedSentimentAgent()
