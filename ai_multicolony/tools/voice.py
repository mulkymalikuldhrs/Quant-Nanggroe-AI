"""VoiceTool – speech-to-text, text-to-speech, and language detection.

Autonomy level: **L1** (all operations are non-destructive).

This is a simulated voice interface.  Real STT/TTS backends
(e.g., Whisper, Azure Speech, Google TTS) would replace the
simulation internals.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .base import MCPTool

logger = logging.getLogger(__name__)


# Supported languages for simulation
_SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "ru": "Russian", "ar": "Arabic", "hi": "Hindi",
    "nl": "Dutch", "sv": "Swedish", "pl": "Polish", "tr": "Turkish",
}

_VOICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "alloy": {"gender": "neutral", "speed": 1.0},
    "echo": {"gender": "male", "speed": 1.0},
    "fable": {"gender": "neutral", "speed": 1.1},
    "onyx": {"gender": "male", "speed": 0.9},
    "nova": {"gender": "female", "speed": 1.0},
    "shimmer": {"gender": "female", "speed": 1.05},
}


class VoiceTool(MCPTool):
    """Voice I/O: speech-to-text, text-to-speech, and language detection.

    Actions
    -------
    transcribe      : convert audio data to text (STT)
    synthesize      : convert text to audio data (TTS)
    detect_language : detect language of audio or text
    list_voices     : list available TTS voices
    list_languages  : list supported languages
    """

    # ── MCPTool interface ────────────────────────────────────────

    def name(self) -> str:
        return "voice.io"

    def category(self) -> str:
        return "voice"

    def autonomy_level(self) -> int:
        return 1

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "transcribe", "synthesize", "detect_language",
                        "list_voices", "list_languages",
                    ],
                    "description": "Voice action to perform",
                },
                "audio_data": {
                    "type": "string",
                    "description": "Base64-encoded audio data (for STT)",
                },
                "text": {
                    "type": "string",
                    "description": "Text to synthesize (for TTS)",
                },
                "language": {
                    "type": "string",
                    "description": "Language code hint (e.g., 'en-US')",
                },
                "voice": {
                    "type": "string",
                    "default": "alloy",
                    "description": "Voice profile for TTS",
                },
                "speed": {
                    "type": "number",
                    "default": 1.0,
                    "minimum": 0.25,
                    "maximum": 4.0,
                    "description": "Speech speed multiplier",
                },
                "format": {
                    "type": "string",
                    "default": "mp3",
                    "enum": ["mp3", "wav", "ogg", "pcm"],
                    "description": "Output audio format",
                },
                "sample_rate": {
                    "type": "integer",
                    "default": 24000,
                    "description": "Audio sample rate in Hz",
                },
            },
        }

    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "action": {"type": "string"},
                "data": {"type": "object"},
            },
        }

    def error_codes(self) -> List[Dict[str, Any]]:
        return [
            {"code": 7001, "message": "No audio data provided"},
            {"code": 7002, "message": "Audio format not supported"},
            {"code": 7003, "message": "No text provided for synthesis"},
            {"code": 7004, "message": "Voice profile not found"},
            {"code": 7005, "message": "Language not supported"},
        ]

    # ── Execute ──────────────────────────────────────────────────

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action: str = params["action"]

        dispatch = {
            "transcribe": self._transcribe,
            "synthesize": self._synthesize,
            "detect_language": self._detect_language,
            "list_voices": self._list_voices,
            "list_languages": self._list_languages,
        }

        handler = dispatch.get(action)
        if handler is None:
            self.record_call(False)
            return {"success": False, "action": action, "data": {"error": f"Unknown action: {action}"}}

        start = time.monotonic()
        try:
            result = await handler(params)
            duration = (time.monotonic() - start) * 1000
            self.record_call(result.get("success", True), duration)
            result["action"] = action
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            self.record_call(False, duration)
            return {"success": False, "action": action, "data": {"error": str(exc)}}

    # ── STT ──────────────────────────────────────────────────────

    async def _transcribe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        audio_data = params.get("audio_data", "")
        language_hint = params.get("language", "en")

        if not audio_data:
            return {"success": False, "data": {"error": "No audio data provided"}}

        # Simulate transcription
        try:
            decoded_size = len(base64.b64decode(audio_data[:64], validate=True))
        except Exception:
            decoded_size = len(audio_data)

        # Generate a deterministic "transcription" based on audio hash
        audio_hash = hashlib.md5(audio_data.encode()[:256]).hexdigest()[:8]
        simulated_text = (
            f"Simulated transcription of {decoded_size} bytes of audio "
            f"(hash: {audio_hash}). The quick brown fox jumps over the lazy dog."
        )

        # Detect language (simulated)
        lang_code = language_hint.split("-")[0].lower()
        if lang_code not in _SUPPORTED_LANGUAGES:
            lang_code = "en"

        return {
            "success": True,
            "data": {
                "text": simulated_text,
                "language": f"{lang_code}-US",
                "confidence": 0.92,
                "duration_seconds": round(decoded_size / 16000, 2),
                "words": len(simulated_text.split()),
            },
        }

    # ── TTS ──────────────────────────────────────────────────────

    async def _synthesize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text", "")
        voice = params.get("voice", "alloy")
        speed = params.get("speed", 1.0)
        fmt = params.get("format", "mp3")
        sample_rate = params.get("sample_rate", 24000)

        if not text:
            return {"success": False, "data": {"error": "No text provided for synthesis"}}

        if voice not in _VOICE_PROFILES:
            return {"success": False, "data": {"error": f"Voice profile not found: {voice}"}}

        # Simulate audio generation
        # Approximate: ~150 words per minute, each character ~1 byte of PCM
        words = len(text.split())
        duration_seconds = (words / 150.0) / speed
        # Simulated audio size: sample_rate * channels (1) * bytes_per_sample (2) * duration
        raw_size = int(sample_rate * 2 * duration_seconds)
        # Compressed size estimate
        compression_ratio = {"mp3": 0.1, "ogg": 0.08, "wav": 1.0, "pcm": 1.0}
        estimated_size = int(raw_size * compression_ratio.get(fmt, 0.1))

        # Generate a fake base64 audio header
        fake_audio = base64.b64encode(
            f"SIMULATED_{fmt.upper()}_AUDIO".encode()
        ).decode()

        return {
            "success": True,
            "data": {
                "audio_data": fake_audio,
                "format": fmt,
                "sample_rate": sample_rate,
                "size_bytes": estimated_size,
                "duration_seconds": round(duration_seconds, 2),
                "voice": voice,
                "speed": speed,
                "words": words,
            },
        }

    # ── Language detection ───────────────────────────────────────

    async def _detect_language(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text", "")
        audio_data = params.get("audio_data", "")

        if not text and not audio_data:
            return {"success": False, "data": {"error": "No text or audio provided for language detection"}}

        # Simple heuristic for text-based detection
        if text:
            # Check for common scripts
            detected = "en"
            confidence = 0.85

            # CJK characters
            if any("\u4e00" <= c <= "\u9fff" for c in text):
                detected = "zh"
                confidence = 0.95
            elif any("\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" for c in text):
                detected = "ja"
                confidence = 0.95
            elif any("\uac00" <= c <= "\ud7af" for c in text):
                detected = "ko"
                confidence = 0.95
            elif any("\u0400" <= c <= "\u04ff" for c in text):
                detected = "ru"
                confidence = 0.90
            elif any("\u0600" <= c <= "\u06ff" for c in text):
                detected = "ar"
                confidence = 0.90
            elif any("\u0900" <= c <= "\u097f" for c in text):
                detected = "hi"
                confidence = 0.90
            else:
                # Check for common Romance language patterns
                text_lower = text.lower()
                if any(w in text_lower for w in ["el ", "la ", "los ", "las ", "en "]):
                    detected = "es"
                    confidence = 0.75
                elif any(w in text_lower for w in ["le ", "la ", "les ", "un ", "une "]):
                    detected = "fr"
                    confidence = 0.75
                elif any(w in text_lower for w in ["der ", "die ", "das ", "und "]):
                    detected = "de"
                    confidence = 0.75

            return {
                "success": True,
                "data": {
                    "language": f"{detected}-US" if detected == "en" else detected,
                    "language_name": _SUPPORTED_LANGUAGES.get(detected, "Unknown"),
                    "confidence": confidence,
                    "source": "text",
                },
            }

        # Audio-based: return simulated detection
        return {
            "success": True,
            "data": {
                "language": "en-US",
                "language_name": "English",
                "confidence": 0.78,
                "source": "audio",
            },
        }

    # ── List voices ──────────────────────────────────────────────

    async def _list_voices(self, params: Dict[str, Any]) -> Dict[str, Any]:
        voices = [
            {"id": k, **v} for k, v in _VOICE_PROFILES.items()
        ]
        return {"success": True, "data": {"voices": voices, "count": len(voices)}}

    # ── List languages ───────────────────────────────────────────

    async def _list_languages(self, params: Dict[str, Any]) -> Dict[str, Any]:
        languages = [
            {"code": k, "name": v} for k, v in _SUPPORTED_LANGUAGES.items()
        ]
        return {"success": True, "data": {"languages": languages, "count": len(languages)}}
