import asyncio
import httpx
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import LLM7_BASE_URL, LLM7_API_KEY

logger = logging.getLogger(__name__)

class AIAnalysisService:
    """
    AI Analysis Service for SolSniperX
    Integrates with LLM7 API and provides comprehensive token analysis
    """
    
    def __init__(self, socketio=None, data_fetcher_service=None):
        self.llm7_base_url = LLM7_BASE_URL
        self.llm7_api_key = LLM7_API_KEY
        self.socketio = socketio
        self.data_fetcher_service = data_fetcher_service
        self._http_client = None

    @property
    def http_client(self):
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client
    
    async def analyze_token_with_llm7(self, token_address: str) -> Dict:
        """
        Analyze token using LLM7 API
        """
        try:
            if self.data_fetcher_service:
                token_data = await self.data_fetcher_service.get_token_by_address(token_address)
            else:
                from services.data_fetcher import data_fetcher_service
                token_data = await data_fetcher_service.get_token_by_address(token_address)

            if not token_data:
                logger.warning(f"Token {token_address} not found for AI analysis.")
                return self._create_fallback_analysis({'address': token_address})

            # Prepare analysis prompt
            prompt = self._create_analysis_prompt(token_data)
            
            # LLM7 API request
            payload = {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are SolSniperX AI, an expert cryptocurrency analyst specializing in Solana memecoins. Provide detailed analysis with risk assessment, sentiment analysis, and trading recommendations. You MUST respond in pure JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3 # Lower temperature for more consistent JSON
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.llm7_api_key}"
            }

            response = await self.http_client.post(f"{self.llm7_base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            llm_response = response.json()
            
            if llm_response and llm_response.get('choices') and llm_response['choices'][0].get('message'):
                analysis_content = llm_response['choices'][0]['message']['content']
                logger.info(f"LLM7 analysis successful for {token_address}")
                return self._parse_llm_analysis(analysis_content)
            else:
                logger.error(f"Invalid response from LLM7 API: {llm_response}")
                return self._create_fallback_analysis(token_data)

        except httpx.RequestError as e:
            logger.error(f"HTTP error with LLM7 API for {token_address}: {e}")
            return self._create_fallback_analysis(token_data)
        except Exception as e:
            logger.error(f"Error during LLM7 analysis for {token_address}: {e}")
            return self._create_fallback_analysis(token_data)

    def _create_analysis_prompt(self, token_data: Dict) -> str:
        """
        Creates a detailed prompt for the LLM based on token data.
        """
        prompt = f"""Analyze the following Solana memecoin data and provide a comprehensive report in JSON format.
        Focus on identifying high-probability trading opportunities and potential rugpull risks. 

        Token Details:
        - Name: {token_data.get('name')}
        - Symbol: {token_data.get('symbol')}
        - Address: {token_data.get('address')}
        - Price (USD): {token_data.get('price', 0):.8f}
        - 24h Volume: {token_data.get('volume_24h', 0):.2f}
        - 24h Price Change (%): {token_data.get('price_change_24h', 0):.2f}
        - Liquidity (USD): {token_data.get('liquidity', 0):.2f}
        - Holder Count: {token_data.get('holder_count', 0)}
        - Age (hours): {token_data.get('age_hours', 0):.2f}
        - Transactions (24h): {token_data.get('transactions_24h', 0)}
        - Buy/Sell Ratio: {token_data.get('buy_sell_ratio', 0):.2f}
        - Top Holder Percentage: {token_data.get('top_holder_percentage', 0):.2f}%
        - Dev Wallet Active: {token_data.get('dev_wallet_active', False)}

        You MUST respond with a JSON object exactly like this:
        {{
            "summary": "A paragraph summarizing the token's current state, potential, and risks.",
            "sentiment": "Bullish|Neutral|Bearish",
            "probability_score": 0-100,
            "risk_assessment": "Low|Medium|High",
            "recommendation": "Buy|Sell|Hold|Avoid",
            "key_factors": ["factor 1", "factor 2", "factor 3"]
        }}
        """
        return prompt

    def _parse_llm_analysis(self, analysis_content: str) -> Dict:
        """
        Parses the LLM's analysis content from JSON, with regex-based fallback for robustness.
        """
        try:
            # 1. Attempt JSON parsing
            content = analysis_content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            content = content.strip()

            if not (content.startswith("{") and content.endswith("}")):
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    content = content[start:end+1]

            parsed_data = {}
            try:
                parsed_data = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("JSON parsing failed, falling back to regex for field extraction.")
                # 2. Regex-based fallback for field extraction with better patterns

                # Sentiment extraction
                sentiment_match = re.search(r'"sentiment":\s*["\']?(Bullish|Neutral|Bearish)["\']?', content, re.IGNORECASE)
                if sentiment_match:
                    parsed_data["sentiment"] = sentiment_match.group(1).capitalize()

                # Probability Score extraction (handles potential string quotes)
                prob_match = re.search(r'"probability_score":\s*["\']?(\d+)["\']?', content)
                if prob_match:
                    parsed_data["probability_score"] = int(prob_match.group(1))

                # Risk Assessment extraction
                risk_match = re.search(r'"risk_assessment":\s*["\']?(Low|Medium|High)["\']?', content, re.IGNORECASE)
                if risk_match:
                    parsed_data["risk_assessment"] = risk_match.group(1).capitalize()

                # Recommendation extraction
                rec_match = re.search(r'"recommendation":\s*["\']?(Buy|Sell|Hold|Avoid)["\']?', content, re.IGNORECASE)
                if rec_match:
                    parsed_data["recommendation"] = rec_match.group(1).capitalize()

                # Summary extraction (more robust quote handling)
                summary_match = re.search(r'"summary":\s*"(.*?)"', content, re.DOTALL)
                if summary_match:
                    parsed_data["summary"] = summary_match.group(1).strip()
                else:
                    # Fallback to taking a chunk if summary field not found specifically
                    parsed_data["summary"] = content[:500] + "..."

            sentiment = str(parsed_data.get("sentiment", "Neutral")).capitalize()
            if sentiment not in ["Bullish", "Neutral", "Bearish"]:
                sentiment = "Neutral"

            risk = str(parsed_data.get("risk_assessment", "Medium")).capitalize()
            if risk not in ["Low", "Medium", "High"]:
                risk = "Medium"

            recommendation = str(parsed_data.get("recommendation", "Hold")).capitalize()
            if recommendation not in ["Buy", "Sell", "Hold", "Avoid"]:
                recommendation = "Hold"

            try:
                prob = int(parsed_data.get("probability_score", 50))
                prob = max(0, min(100, prob))
            except (ValueError, TypeError):
                prob = 50

            return {
                "summary": str(parsed_data.get("summary", "No summary provided.")),
                "sentiment": sentiment,
                "probability_score": prob,
                "risk_assessment": risk,
                "recommendation": recommendation,
                "key_factors": list(parsed_data.get("key_factors", []))
            }
        except Exception as e:
            logger.error(f"Critical error parsing LLM analysis: {e}. Content: {analysis_content}")
            return self._create_fallback_analysis({})

    def _create_fallback_analysis(self, token_data: Dict) -> Dict:
        """
        Creates a fallback analysis in case LLM call fails.
        """
        return {
            "summary": f"Due to an issue, a full AI analysis could not be performed for {token_data.get('symbol', 'this token')}. Basic data is available.",
            "sentiment": "Neutral",
            "probability_score": 50,
            "risk_assessment": "Medium",
            "recommendation": "Hold",
            "key_factors": ["Data unavailable", "Manual review recommended"]
        }

    async def analyze_token(self, token_address: str) -> Dict:
        """
        Performs AI analysis for a given token.
        Compatibility layer for analyze_token_with_llm7.
        """
        return await self.analyze_token_with_llm7(token_address)

    async def get_trading_signals(self, token_address: str) -> Dict:
        """
        Generates trading signals based on AI analysis.
        """
        analysis = await self.analyze_token(token_address)
        
        signals = {
            "token_address": token_address,
            "recommendation": analysis['recommendation'],
            "sentiment": analysis['sentiment'],
            "probability_score": analysis['probability_score'],
            "risk_assessment": analysis['risk_assessment'],
            "signal_details": analysis['summary'],
            "timestamp": datetime.now().isoformat()
        }
        return signals

# Create a singleton instance
ai_analysis_service = AIAnalysisService()
