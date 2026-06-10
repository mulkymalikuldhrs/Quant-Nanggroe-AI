#!/usr/bin/env python3
"""
Chart Vision Agent (L1 - Data Layer)
Chart image analysis via vision LLM
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("HermesQuantOS.ChartVision")


class ChartVisionTool:
    """L1 Agent: Chart Vision - Analyze chart images via LLM"""

    def __init__(self):
        self.vision_provider = os.getenv("VISION_PROVIDER", "openai")
        self.api_key = os.getenv("OPENAI_VISION_KEY", "")

    def analyze_chart(self, image_path: str, question: str = "Analyze this chart for trading opportunities using SMC principles") -> str:
        """
        Analyze a chart image using vision LLM.

        Args:
            image_path: Path to chart image file
            question: What to analyze about the chart
        """
        if not os.path.exists(image_path):
            return json.dumps({
                "error": f"Image not found: {image_path}",
                "suggestion": "Provide a valid path to a chart screenshot"
            })

        # Try to use vision API
        try:
            import base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Try OpenAI vision
            if self.api_key:
                import urllib.request
                import urllib.error

                url = "https://api.openai.com/v1/chat/completions"
                data = {
                    "model": "gpt-4o-mini",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }}
                        ]
                    }],
                    "max_tokens": 1000
                }

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode('utf-8'),
                    headers=headers,
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    analysis = result["choices"][0]["message"]["content"]

                    return json.dumps({
                        "image": image_path,
                        "analysis": analysis,
                        "provider": "openai_vision",
                        "timestamp": datetime.now().isoformat()
                    }, indent=2)

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Vision API failed: {e}")

        # Fallback: Return instruction for manual analysis
        return json.dumps({
            "image": image_path,
            "analysis": "Vision API not available. Manual analysis required.",
            "checklist": [
                "1. Identify current trend (HH/HL = bullish, LH/LL = bearish)",
                "2. Find nearest Order Block (last opposing candle before impulse)",
                "3. Identify Fair Value Gaps (3-candle imbalance)",
                "4. Check for BOS or CHoCH at key levels",
                "5. Mark liquidity pools (equal highs/lows, swing points)",
                "6. Determine confluence score (min 3/5 required)"
            ],
            "timestamp": datetime.now().isoformat()
        }, indent=2)
