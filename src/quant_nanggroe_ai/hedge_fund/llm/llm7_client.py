#!/usr/bin/env python3
"""
AI HEDGE FUND v2.3.0 - LLM7 Client
===================================

Primary LLM Client for AI Hedge Fund using LLM7 API.
Agent Constitution v2.3.0 Compliant

Features:
- Chat completion for strategy reasoning
- Function calling for market data retrieval
- Streaming responses for real-time analysis
- Error handling with fallback to backup LLMs (OpenRouter, Groq, Gemini)

Configuration:
- Base URL: https://api.llm7.io/v1
- Primary Model: gpt-5-nano-2025-08-07
- Fallback Model: gpt-4.1-nano-2025-04-14
- Temperature: 0.1 (low variance for trading)
- Max Tokens: 2000

Usage:
    from src.llm.llm7_client import LLM7Client

    client = LLM7Client()

    # Chat completion
    response = client.chat("Analyze AAPL stock for buy signal")

    # Function calling
    result = client.call_function("get_stock_data", {"symbol": "AAPL"})

    # Streaming
    for chunk in client.chat_stream("Explain your reasoning step by step"):
        print(chunk, end="", flush=True)

Author: Mulky Malikul Dhaher
Version: 2.3.0
Date: 2026-01-19
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from datetime import datetime
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# ============ CONFIGURATION ============

LLM7_ENABLED = os.getenv("LLM7_ENABLED", "false").lower() == "true"
LLM7_BASE_URL = os.getenv("LLM7_BASE_URL", "https://api.llm7.io/v1")
LLM7_API_KEY = os.getenv("LLM7_API_KEY", "")
LLM7_MODEL = os.getenv("LLM7_MODEL", "gpt-5-nano-2025-08-07")
LLM7_FALLBACK_MODEL = os.getenv("LLM7_FALLBACK_MODEL", "gpt-4.1-nano-2025-04-14")
LLM7_TEMPERATURE = float(os.getenv("LLM7_TEMPERATURE", "0.1"))
LLM7_MAX_TOKENS = int(os.getenv("LLM7_MAX_TOKENS", "2000"))

# Backup LLM Providers (fallback)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    handlers=[logging.FileHandler("llm7_client.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============ DATA CLASSES ============


@dataclass
class LLM7Config:
    """LLM7 API configuration"""

    base_url: str = LLM7_BASE_URL
    api_key: str = LLM7_API_KEY
    primary_model: str = LLM7_MODEL
    fallback_model: str = LLM7_FALLBACK_MODEL
    temperature: float = LLM7_TEMPERATURE
    max_tokens: int = LLM7_MAX_TOKENS
    timeout: int = 30


@dataclass
class Message:
    """Chat message"""

    role: str = "user"
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FunctionCall:
    """Function call specification"""

    name: str
    parameters: Dict[str, Any]


@dataclass
class FunctionResponse:
    """Function call result"""

    name: str
    result: Dict[str, Any]


@dataclass
class ChatResponse:
    """Chat response"""

    message: str = ""
    finish_reason: str = "stop"
    delta: Optional[str] = None


@dataclass
class StreamChunk:
    """Streaming response chunk"""

    delta: Optional[str] = None
    role: str = "assistant"
    content: str = ""
    finish_reason: str = "stop"


# ============ LLM7 CLIENT ============


class LLM7Client:
    """LLM7 API Client for Hedge Fund"""

    def __init__(self, config: Optional[LLM7Config] = None):
        self.config = config or LLM7Config()
        self.session = None
        self.headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _make_request(self, endpoint: str, payload: Dict) -> Dict:
        """Make API request to LLM7"""
        try:
            import requests

            url = f"{self.config.base_url}/{endpoint}"
            logger.info(f"LLM7 Request: {endpoint}")

            response = requests.post(
                url, json=payload, headers=self.headers, timeout=self.config.timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"LLM7 Error {response.status_code}: {response.text[:200]}"
                )
                return {"error": str(response.status_code)}

        except Exception as e:
            logger.error(f"LLM7 Request failed: {e}")
            return {"error": str(e)}

    def chat(self, prompt: str, system_prompt: Optional[str] = None) -> ChatResponse:
        """
        Send chat completion request to LLM7.

        Args:
            prompt: User message or instruction
            system_prompt: Optional system prompt override

        Returns:
            ChatResponse with message and metadata
        """
        if not LLM7_ENABLED or not self.config.api_key:
            logger.warning("LLM7 not enabled or no API key")
            return ChatResponse(message="LLM7 not available")

        # System prompt for trading analysis
        default_system_prompt = """You are an expert hedge fund trading AI assistant with deep knowledge in:
- Technical analysis (RSI, MACD, Bollinger Bands, Ichimoku, ATR)
- Risk management (VaR, CVaR, Sharpe ratio)
- Quantitative strategies (momentum, mean reversion, pairs trading)
- Portfolio optimization
- Market microstructure (liquidity, impact)
- Trading psychology
- Alpha generation and evaluation

Provide concise, actionable trading insights. Focus on:
- Signal generation (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
- Risk-reward analysis
- Stop loss and take profit levels
- Position sizing recommendations
- Market condition assessment (trending, ranging, volatile)
- Confidence levels (0-100%)

Be objective, data-driven, and acknowledge uncertainty."""

        payload = {
            "model": self.config.primary_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                    if not system_prompt
                    else system_prompt + "\n\n" + prompt,
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }

        logger.info(f"LLM7 Chat Request: {prompt[:100]}...")

        response_dict = self._make_request("chat/completions", payload)

        if "error" in response_dict:
            return ChatResponse(
                message=f"LLM7 Error: {response_dict['error']}", finish_reason="error"
            )

        response = response_dict.get("choices", [{}])
        if not response:
            return ChatResponse(message="No response from LLM7", finish_reason="stop")

        message_obj = response[0].get("message", {})
        return ChatResponse(
            message=message_obj.get("content", ""),
            finish_reason=response.get("finish_reason", "stop"),
        )

    def chat_stream(self, prompt: str) -> AsyncIterator[StreamChunk]:
        """
        Stream chat completion responses for real-time analysis.

        Args:
            prompt: User instruction or question

        Yields:
            StreamChunk objects with partial responses
        """
        if not LLM7_ENABLED:
            yield StreamChunk(content="LLM7 not enabled", role="assistant")
            return

        default_system_prompt = """You are a hedge fund AI assistant specializing in real-time market analysis. Provide streaming responses with:
- Step-by-step reasoning for your conclusions
- Technical indicator calculations as needed
- Real-time signal updates
- Confidence intervals

Be concise and actionable. Focus on immediate trading decisions."""

        payload = {
            "model": self.config.primary_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                    if not default_system_prompt
                    else default_system_prompt + "\n\n" + prompt,
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }

        logger.info(f"LLM7 Stream Request: {prompt[:100]}...")

        try:
            import requests

            url = f"{self.config.base_url}/chat/completions"
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                stream=True,
                timeout=self.config.timeout,
            )

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        chunk = StreamChunk(
                            content=data.get("delta", {}).get("content", ""),
                            role=data.get("role", "assistant"),
                            finish_reason=data.get("finish_reason", ""),
                        )
                        logger.debug(f"Stream chunk received: {chunk.content[:50]}")
                        yield chunk

                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in stream: {line[:50]}")
                        continue

        except Exception as e:
            logger.error(f"LLM7 Stream failed: {e}")

    def call_function(self, function_name: str, parameters: Dict) -> FunctionResponse:
        """
        Call a function (tool) for structured data retrieval.

        Args:
            function_name: Name of function to call
            parameters: Function parameters as dict

        Returns:
            FunctionResponse with result
        """
        if not LLM7_ENABLED:
            return FunctionResponse(
                name=function_name, result={"error": "LLM7 not enabled"}
            )

        # Define available functions
        functions = {
            "get_stock_data": {
                "description": "Get current and historical stock data",
                "parameters": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Historical period in days (default: 100)",
                    },
                },
            },
            "calculate_indicators": {
                "description": "Calculate technical indicators (RSI, MACD, Bollinger Bands)",
                "parameters": {
                    "symbol": {"type": "string", "description": "Stock symbol"},
                    "period": {
                        "type": "integer",
                        "description": "Calculation period (default: 100)",
                    },
                    "indicators": {
                        "type": "array",
                        "description": "Array of indicator names (rsi, macd, bb, atr, adx)",
                    },
                },
            },
            "analyze_portfolio_risk": {
                "description": "Calculate portfolio VaR and CVaR",
                "parameters": {
                    "positions": {
                        "type": "array",
                        "description": "Array of positions with symbol, entry_price, current_price, position_size",
                    },
                    "confidence_levels": {
                        "type": "array",
                        "description": "Confidence levels for VaR calculation (e.g., 0.90, 0.95, 0.99)",
                    },
                },
            },
        }

        payload = {
            "model": self.config.primary_model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Call function: {function_name} with parameters: {json.dumps(parameters)}",
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }

        logger.info(f"LLM7 Function Call: {function_name}")

        response_dict = self._make_request("functions/invoke", payload)

        if "error" in response_dict:
            return FunctionResponse(
                name=function_name, result={"error": response_dict["error"]}
            )

        result = response_dict.get("response", {})
        if not result:
            return FunctionResponse(name=function_name, result={"error": "No response"})

        # Extract function result
        if function_name == "get_stock_data":
            return FunctionResponse(
                name=function_name, result={"error": "Not implemented yet"}
            )

        return FunctionResponse(name=function_name, result=result)

    def get_supported_models(self) -> List[str]:
        """Get list of available models"""
        return [
            self.config.primary_model,
            self.config.fallback_model,
            "gpt-4-turbo",
            "gpt-4o-mini",
            "llama3-70b-8192",
            "gemini-1.5-flash",
            "deepseek-chat",
        ]

    def health_check(self) -> Dict[str, Any]:
        """Check LLM7 client health status"""
        try:
            import requests

            # Simple health check
            response = requests.get(
                f"{self.config.base_url}/models", headers=self.headers, timeout=10
            )

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "model": self.config.primary_model,
                    "available_models": response.json()
                    .get("data", {})
                    .get("models", []),
                }
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def estimate_cost(self, tokens: int) -> float:
        """Estimate API cost for tokens"""
        # Rough estimation: $0.002 per 1K tokens for gpt-5-nano
        return tokens * 0.002


# ============ FACTORY ============


def get_llm7_client() -> LLM7Client:
    """Factory function to get LLM7 client instance"""
    if not LLM7_ENABLED:
        logger.warning("LLM7 not enabled")
        return None

    config = LLM7Config(
        base_url=LLM7_BASE_URL,
        api_key=LLM7_API_KEY,
        primary_model=LLM7_MODEL,
        fallback_model=LLM7_FALLBACK_MODEL,
        temperature=LLM7_TEMPERATURE,
        max_tokens=LLM7_MAX_TOKENS,
    )

    logger.info(f"LLM7 Client initialized with model: {config.primary_model}")

    return LLM7Client(config=config)


# ============ TESTING ============


if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║   AI HEDGE FUND v2.2.2 - LLM7 CLIENT TEST                   ║")
    print("║                                                              ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    # Test client
    client = get_llm7_client()

    if client:
        print(f"{Fore.CYAN}LLM7 Client: {client.config.primary_model}{Style.RESET_ALL}")
        print(f"Base URL: {client.config.base_url}")
        print()

        # Health check
        health = client.health_check()
        print(
            f"{Fore.CYAN}Health Check: {health.get('status', 'unknown')}{Style.RESET_ALL}"
        )
        print()

        # Supported models
        models = client.get_supported_models()
        print(f"{Fore.CYAN}Supported Models:{Style.RESET_ALL}")
        for model in models:
            print(f"  • {model}")
        print()

        # Example chat
        print(f"\n{Fore.YELLOW}Testing Chat Completion...{Style.RESET_ALL}\n")
        test_prompt = (
            "What is the current market sentiment and should I buy AAPL stock?"
        )

        response = client.chat(test_prompt)
        print(f"{Fore.GREEN}Response:{Style.RESET_ALL}")
        print(f"Message: {response.message[:200]}")
        print(f"Finish Reason: {response.finish_reason}")
        print()

        # Estimate cost
        estimated_cost = client.estimate_cost(1000)
        print(
            f"\n{Fore.CYAN}Estimated Cost (1000 tokens): ${estimated_cost:.4f}{Style.RESET_ALL}\n"
        )

    else:
        print(f"{Fore.RED}LLM7 Client not available{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}Check LLM7_ENABLED and LLM7_API_KEY in .env{Style.RESET_ALL}"
        )
        print()
