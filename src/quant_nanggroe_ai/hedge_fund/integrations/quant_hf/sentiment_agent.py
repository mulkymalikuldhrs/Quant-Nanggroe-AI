"""
🌟 ORCHID QUANTUM AI - Sentiment Agent
========================================
Specialized agent for sentiment analysis from multiple sources.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from .base import BaseAgent, AgentMessage, MessageType, AgentState
import logging
import re


class SentimentType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentData:
    """Sentiment data for a symbol."""
    symbol: str
    sentiment_score: float  # -1 to 1
    sentiment_type: SentimentType
    confidence: float
    sources: Dict[str, float]
    headline: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


class SentimentAgent(BaseAgent):
    """Agent responsible for sentiment analysis from news, social, and on-chain data."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(
            agent_id="sentiment_agent_001",
            name="Sentiment Agent"
        )
        self.capabilities = [
            "news_sentiment",
            "social_media_sentiment",
            "onchain_sentiment",
            "options_flow_analysis",
            "earnings_sentiment",
            "sentiment_aggregation"
        ]
        self.config = config or {
            'news_weight': 0.4,
            'social_weight': 0.3,
            'onchain_weight': 0.3,
            'threshold': 0.1
        }
        self.sentiment_cache: Dict[str, List[SentimentData]] = {}
        self.market_sentiment: Dict[str, float] = {}
        
        # Financial sentiment lexicon
        self.bullish_words = [
            'buy', 'bullish', 'gain', 'rise', 'surge', 'rally', 'growth', 'profit',
            'upgrade', 'beat', 'strong', 'breakout', 'momentum', 'optimistic',
            'opportunity', 'recovery', 'boom', 'success', 'positive', 'upgrade'
        ]
        
        self.bearish_words = [
            'sell', 'bearish', 'loss', 'fall', 'crash', 'decline', 'drop', 'warning',
            'downgrade', 'miss', 'weak', 'breakdown', 'risk', 'pessimistic',
            'concern', 'recession', 'failure', 'negative', 'trouble', 'crisis'
        ]
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the sentiment agent."""
        self.config.update(config)
        self.logger.info("Sentiment Agent initialized")
        return True
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sentiment analysis task."""
        task_type = task.get('type', 'analyze')
        
        if task_type == 'analyze':
            return self._analyze_sentiment(task)
        elif task_type == 'aggregate':
            return self._aggregate_sentiment(task)
        elif task_type == 'market_wide':
            return self._market_wide_sentiment(task)
        elif task_type == 'news':
            return self._analyze_news(task)
        elif task_type == 'social':
            return self._analyze_social(task)
        else:
            return {'status': 'error', 'message': f'Unknown task type: {task_type}'}
    
    def _analyze_sentiment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment for symbols."""
        symbols = task.get('symbols', [])
        sources = task.get('sources', ['news', 'social', 'onchain'])
        
        results = {}
        
        for symbol in symbols:
            sentiment_scores = {}
            
            if 'news' in sources:
                news_score = self._get_news_sentiment(symbol)
                sentiment_scores['news'] = news_score
            
            if 'social' in sources:
                social_score = self._get_social_sentiment(symbol)
                sentiment_scores['social'] = social_score
            
            if 'onchain' in sources:
                onchain_score = self._get_onchain_sentiment(symbol)
                sentiment_scores['onchain'] = onchain_score
            
            # Weighted average
            total_weight = 0
            weighted_sum = 0
            
            for source, score in sentiment_scores.items():
                weight = self.config.get(f'{source}_weight', 0.33)
                weighted_sum += score * weight
                total_weight += weight
            
            if total_weight > 0:
                final_score = weighted_sum / total_weight
            else:
                final_score = 0
            
            # Determine sentiment type
            threshold = self.config.get('threshold', 0.1)
            if final_score > threshold:
                sentiment_type = SentimentType.POSITIVE
            elif final_score < -threshold:
                sentiment_type = SentimentType.NEGATIVE
            else:
                sentiment_type = SentimentType.NEUTRAL
            
            confidence = np.mean(list(sentiment_scores.values())) if sentiment_scores else 0.5
            
            results[symbol] = {
                'sentiment_score': float(final_score),
                'sentiment_type': sentiment_type.value,
                'confidence': float(confidence),
                'breakdown': {k: float(v) for k, v in sentiment_scores.items()},
                'timestamp': datetime.now().isoformat()
            }
        
        return {
            'status': 'success',
            'sentiment': results,
            'symbols_analyzed': len(results)
        }
    
    def _get_news_sentiment(self, symbol: str) -> float:
        """Get news sentiment (simulated)."""
        # In real implementation, this would call news APIs
        # Simulating sentiment based on patterns
        np.random.seed(hash(symbol) % 2**32)
        
        base_sentiment = np.random.uniform(-0.3, 0.3)
        news_headlines = self._generate_simulated_headlines(symbol)
        
        headline_sentiments = []
        for headline in news_headlines:
            score = self._calculate_text_sentiment(headline)
            headline_sentiments.append(score)
        
        avg_headline = np.mean(headline_sentiments) if headline_sentiments else 0
        
        return (base_sentiment + avg_headline) / 2
    
    def _get_social_sentiment(self, symbol: str) -> float:
        """Get social media sentiment (simulated)."""
        # In real implementation, this would call Twitter/Reddit APIs
        np.random.seed(hash(symbol) % 2**32 + 1)
        
        # Simulate social sentiment
        base = np.random.uniform(-0.2, 0.2)
        
        # Volume-weighted (high volume = more extreme sentiment)
        volume = np.random.uniform(0.5, 2.0)
        sentiment = base * volume
        
        return np.clip(sentiment, -1, 1)
    
    def _get_onchain_sentiment(self, symbol: str) -> float:
        """Get on-chain sentiment (simulated for crypto)."""
        np.random.seed(hash(symbol) % 2**32 + 2)
        
        # Simulate on-chain metrics
        exchange_flow = np.random.uniform(-0.3, 0.3)
        whale_activity = np.random.uniform(-0.2, 0.2)
        network_value = np.random.uniform(-0.1, 0.1)
        
        # Combine metrics
        onchain_score = (exchange_flow * 0.5 + whale_activity * 0.3 + network_value * 0.2)
        
        return np.clip(onchain_score, -1, 1)
    
    def _generate_simulated_headlines(self, symbol: str) -> List[str]:
        """Generate simulated news headlines."""
        headlines = [
            f"{symbol} reports quarterly earnings above expectations",
            f"Analysts upgrade {symbol} price target",
            f"{symbol} announces new product launch",
            f"Regulatory concerns weigh on {symbol}",
            f"{symbol} CEO discusses growth strategy",
            f"Institutional investors increase {symbol} holdings",
            f"{symbol} faces competitive pressure",
            f"Market volatility affects {symbol} trading",
        ]
        
        return headlines[:4]
    
    def _calculate_text_sentiment(self, text: str) -> float:
        """Calculate sentiment from text."""
        text_lower = text.lower()
        
        bullish_count = sum(1 for word in self.bullish_words if word in text_lower)
        bearish_count = sum(1 for word in self.bearish_words if word in text_lower)
        
        total = bullish_count + bearish_count
        
        if total == 0:
            return 0
        
        return (bullish_count - bearish_count) / total
    
    def _aggregate_sentiment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate sentiment across multiple symbols."""
        symbols = task.get('symbols', [])
        timeframe = task.get('timeframe', '1d')
        
        aggregated = {}
        
        for symbol in symbols:
            history = self.sentiment_cache.get(symbol, [])
            
            # Filter by timeframe
            cutoff = datetime.now() - timedelta(days=1 if timeframe == '1d' else 7)
            filtered = [s for s in history if s.timestamp > cutoff]
            
            if filtered:
                avg_score = np.mean([s.sentiment_score for s in filtered])
                avg_confidence = np.mean([s.confidence for s in filtered])
                
                aggregated[symbol] = {
                    'average_sentiment': float(avg_score),
                    'average_confidence': float(avg_confidence),
                    'data_points': len(filtered),
                    'trend': self._calculate_sentiment_trend(filtered)
                }
            else:
                aggregated[symbol] = {
                    'average_sentiment': 0,
                    'average_confidence': 0,
                    'data_points': 0,
                    'trend': 'neutral'
                }
        
        # Market-wide sentiment
        if aggregated:
            market_sentiment = np.mean([v['average_sentiment'] for v in aggregated.values()])
        else:
            market_sentiment = 0
        
        return {
            'status': 'success',
            'aggregated_sentiment': aggregated,
            'market_sentiment': float(market_sentiment),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_sentiment_trend(self, sentiments: List[SentimentData]) -> str:
        """Calculate sentiment trend over time."""
        if len(sentiments) < 2:
            return 'neutral'
        
        scores = [s.sentiment_score for s in sentiments]
        
        if len(scores) >= 3:
            recent = np.mean(scores[-3:])
            older = np.mean(scores[:-3])
        else:
            recent = np.mean(scores)
            older = scores[0] if scores else 0
        
        diff = recent - older
        
        if diff > 0.1:
            return 'improving'
        elif diff < -0.1:
            return 'declining'
        else:
            return 'stable'
    
    def _market_wide_sentiment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get market-wide sentiment."""
        # Simulate market sentiment
        np.random.seed(42)
        
        market_sentiment = np.random.uniform(-0.2, 0.2)
        
        # Sector breakdown
        sectors = {
            'technology': market_sentiment + np.random.uniform(-0.1, 0.1),
            'finance': market_sentiment + np.random.uniform(-0.1, 0.1),
            'healthcare': market_sentiment + np.random.uniform(-0.1, 0.1),
            'energy': market_sentiment + np.random.uniform(-0.15, 0.15),
            'consumer': market_sentiment + np.random.uniform(-0.1, 0.1)
        }
        
        # Fear & Greed Index (simulated)
        fear_greed = 50 + market_sentiment * 25  # 0-100 scale
        
        if fear_greed > 75:
            fear_greed_label = 'Extreme Greed'
        elif fear_greed > 60:
            fear_greed_label = 'Greed'
        elif fear_greed > 40:
            fear_greed_label = 'Neutral'
        elif fear_greed > 25:
            fear_greed_label = 'Fear'
        else:
            fear_greed_label = 'Extreme Fear'
        
        return {
            'status': 'success',
            'market_sentiment': float(market_sentiment),
            'fear_greed_index': float(fear_greed),
            'fear_greed_label': fear_greed_label,
            'sector_sentiment': {k: float(v) for k, v in sectors.items()},
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_news(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze news sentiment."""
        headlines = task.get('headlines', [])
        
        sentiments = []
        
        for headline in headlines:
            score = self._calculate_text_sentiment(headline)
            sentiments.append({
                'headline': headline,
                'sentiment_score': float(score),
                'sentiment_type': SentimentType.POSITIVE if score > 0.1 else SentimentType.NEGATIVE if score < -0.1 else SentimentType.NEUTRAL
            })
        
        avg_score = np.mean([s['sentiment_score'] for s in sentiments]) if sentiments else 0
        
        return {
            'status': 'success',
            'headlines_sentiment': sentiments,
            'average_sentiment': float(avg_score),
            'positive_count': sum(1 for s in sentiments if s['sentiment_score'] > 0.1),
            'negative_count': sum(1 for s in sentiments if s['sentiment_score'] < -0.1),
            'neutral_count': sum(1 for s in sentiments if -0.1 <= s['sentiment_score'] <= 0.1)
        }
    
    def _analyze_social(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze social media sentiment."""
        posts = task.get('posts', [])
        
        sentiments = []
        
        for post in posts:
            score = self._calculate_text_sentiment(post)
            sentiments.append({
                'post': post[:100] + '...' if len(post) > 100 else post,
                'sentiment_score': float(score)
            })
        
        avg_score = np.mean([s['sentiment_score'] for s in sentiments]) if sentiments else 0
        
        # Calculate engagement-weighted sentiment
        weights = np.random.uniform(0.5, 1.5, len(sentiments))
        weighted_score = np.average([s['sentiment_score'] for s in sentiments], weights=weights) if sentiments else 0
        
        return {
            'status': 'success',
            'posts_sentiment': sentiments,
            'average_sentiment': float(avg_score),
            'engagement_weighted_sentiment': float(weighted_score),
            'total_posts': len(posts)
        }
    
    def add_sentiment_data(self, data: SentimentData) -> None:
        """Add sentiment data to cache."""
        if data.symbol not in self.sentiment_cache:
            self.sentiment_cache[data.symbol] = []
        
        self.sentiment_cache[data.symbol].append(data)
        
        # Keep only last 100 entries
        if len(self.sentiment_cache[data.symbol]) > 100:
            self.sentiment_cache[data.symbol] = self.sentiment_cache[data.symbol][-100:]
    
    def get_sentiment_history(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get sentiment history for a symbol."""
        history = self.sentiment_cache.get(symbol, [])[-limit:]
        
        return [
            {
                'sentiment_score': s.sentiment_score,
                'sentiment_type': s.sentiment_type.value,
                'confidence': s.confidence,
                'timestamp': s.timestamp.isoformat()
            }
            for s in history
        ]
    
    def _process_message(self, message: AgentMessage) -> None:
        """Process incoming message."""
        if message.msg_type == MessageType.ANALYSIS_REQUEST:
            task = message.payload
            result = self.execute(task)
            
            response = AgentMessage(
                msg_type=MessageType.ANALYSIS_RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                payload=result,
                priority=message.priority
            )
            self._deliver_message(response)
        
        elif message.msg_type == MessageType.HEARTBEAT:
            self.heartbeat()
            self.state = AgentState.RUNNING
