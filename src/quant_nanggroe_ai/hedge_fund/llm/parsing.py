import json
import re
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)

def extract_json_from_response(content: str) -> Optional[dict]:
    if content is None or not isinstance(content, str):
        return None
    content = content.strip()
    if not content:
        return None
    json_start = content.find('```json')
    if json_start != -1:
        json_text = content[json_start + 7:]
        json_end = json_text.find('```')
        if json_end != -1:
            json_text = json_text[:json_end].strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.debug(f'Failed to parse JSON: {e}')
    json_start = content.find('```')
    if json_start != -1:
        json_text = content[json_start + 3:]
        json_end = json_text.find('```')
        if json_end != -1:
            json_text = json_text[:json_end].strip()
            if json_text.startswith('{') or json_text.startswith('['):
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, content)
    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None

def extract_field_from_response(response: str, field: str) -> Any:
    if isinstance(response, str):
        parsed = extract_json_from_response(response)
        if parsed is None:
            return None
    else:
        parsed = response
    if not isinstance(parsed, dict):
        return None
    return parsed.get(field)

def parse_trading_signal(signal_text: str) -> Optional[str]:
    if signal_text is None:
        return None
    signal_text = str(signal_text).strip().upper()
    if signal_text in ['BUY', 'LONG']:
        return 'buy'
    elif signal_text in ['SELL', 'SHORT']:
        return 'sell'
    elif signal_text in ['HOLD', 'WAIT', 'NEUTRAL']:
        return 'hold'
    return None

def normalize_confidence(confidence: float) -> float:
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return 0.0
    if confidence > 1.0:
        confidence = confidence / 100.0
    return max(0.0, min(1.0, confidence))

def create_fallback_response(ticker: str = None) -> dict:
    response = {'signal': 'hold', 'confidence': 0.0, 'reasoning': 'Error in LLM analysis, using fallback'}
    if ticker:
        response['ticker'] = ticker
        response['symbol'] = ticker
    return response

def validate_signal_schema(signal: dict) -> bool:
    if not isinstance(signal, dict):
        return False
    required_fields = ['signal', 'confidence', 'reasoning']
    for field in required_fields:
        if field not in signal:
            return False
    valid_signals = ['buy', 'sell', 'hold']
    if signal['signal'] not in valid_signals:
        return False
    try:
        confidence = float(signal['confidence'])
        if confidence > 1.0:
            confidence = confidence / 100.0
        if not (0.0 <= confidence <= 1.0):
            return False
    except (TypeError, ValueError):
        return False
    if not isinstance(signal['reasoning'], str):
        return False
    return True
