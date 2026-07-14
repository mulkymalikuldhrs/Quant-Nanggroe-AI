"""Voice agent – speech-to-text, text-to-speech, and voice commands.

Provides transcription (STT), synthesis (TTS), language detection, and
voice command interpretation for multi-modal agent interactions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from ..types import AgentSpec, AgentType, Task, TaskResult

logger = logging.getLogger(__name__)


class VoiceSession:
    """Tracks a single voice interaction session."""

    def __init__(self, session_id: str = "", language: str = "en-US"):
        self.session_id = session_id or f"vs-{uuid.uuid4().hex[:8]}"
        self.language = language
        self.transcriptions: List[Dict[str, Any]] = []
        self.syntheses: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "language": self.language,
            "transcription_count": len(self.transcriptions),
            "synthesis_count": len(self.syntheses),
            "created_at": self.created_at.isoformat(),
        }


# ── Voice command patterns ──

VOICE_COMMAND_PATTERNS: Dict[str, List[str]] = {
    "navigate": ["go to", "open", "visit", "navigate to"],
    "search": ["search for", "find", "look up", "query"],
    "execute": ["run", "execute", "start", "launch"],
    "stop": ["stop", "cancel", "abort", "terminate"],
    "status": ["status", "state", "what is", "how is"],
    "help": ["help", "what can you", "commands"],
}


class VoiceAgent(BaseAgent):
    """Voice I/O agent for speech recognition and synthesis.

    Features
    --------
    * **Speech-to-text transcription** – convert audio input to text.
    * **Text-to-speech synthesis** – generate audio from text.
    * **Language detection** – identify spoken language.
    * **Voice command interpretation** – parse natural-language commands
      into structured intents.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.VOICE, autonomy_level=1)
        if spec.agent_type != AgentType.VOICE:
            spec.agent_type = AgentType.VOICE
        super().__init__(spec=spec, **kwargs)
        self._language = "en-US"
        self._stt_enabled = True
        self._tts_enabled = True
        self._sessions: Dict[str, VoiceSession] = {}
        self._supported_languages = [
            "en-US", "en-GB", "es-ES", "fr-FR", "de-DE",
            "it-IT", "pt-BR", "ja-JP", "ko-KR", "zh-CN",
        ]
        self._voice = "default"
        self._speed = 1.0

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Execute voice task based on ``payload.action``."""
        action = task.payload.get("action", "transcribe")
        if action == "transcribe":
            return await self._transcribe(task)
        elif action == "synthesize":
            return await self._synthesize(task)
        elif action == "detect_language":
            return await self._detect_language(task)
        elif action == "interpret_command":
            return await self._interpret_command(task)
        elif action == "create_session":
            return self._create_session(task)
        elif action == "list_languages":
            return self._list_languages()
        else:
            return {"action": action, "result": f"Unknown voice action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle A2A messages for voice operations."""
        msg_type = message.get("message_type", "")
        if msg_type == "transcribe_request":
            return {"text": "Transcribed from message", "language": self._language}
        elif msg_type == "synthesize_request":
            text = message.get("payload", {}).get("text", "")
            return {"audio_size_bytes": len(text) * 100, "language": self._language}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare voice capabilities."""
        return [
            "speech_to_text", "text_to_speech", "language_detection",
            "voice_commands", "transcription", "synthesis",
        ]

    # ── Speech-to-text ──

    async def _transcribe(self, task: Task) -> Dict[str, Any]:
        """Transcribe audio data to text.

        Payload fields:
        * ``audio_data`` – raw audio bytes (simulated).
        * ``language`` – BCP-47 language hint (default from config).
        * ``session_id`` – optional session for multi-turn tracking.
        """
        if not self._stt_enabled:
            return {"action": "transcribe", "error": "STT disabled"}

        audio_data = task.payload.get("audio_data", b"")
        language = task.payload.get("language", self._language)
        session_id = task.payload.get("session_id")

        # Simulate transcription
        text = "Transcribed text"
        confidence = 0.95

        # Detect if audio data contains enough signal
        if isinstance(audio_data, (bytes, bytearray)) and len(audio_data) > 0:
            confidence = min(1.0, 0.8 + len(audio_data) / 100000)

        result = {
            "action": "transcribe",
            "text": text,
            "language": language,
            "confidence": confidence,
            "word_count": len(text.split()),
        }

        # Track in session
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.transcriptions.append(result)

        return result

    # ── Text-to-speech ──

    async def _synthesize(self, task: Task) -> Dict[str, Any]:
        """Synthesize speech from text.

        Payload fields:
        * ``text`` – text to synthesize.
        * ``language`` – BCP-47 language code.
        * ``voice`` – voice identifier.
        * ``speed`` – speech rate multiplier.
        """
        if not self._tts_enabled:
            return {"action": "synthesize", "error": "TTS disabled"}

        text = task.payload.get("text", "")
        language = task.payload.get("language", self._language)
        voice = task.payload.get("voice", self._voice)
        speed = task.payload.get("speed", self._speed)
        session_id = task.payload.get("session_id")

        # Simulate synthesis – audio size proportional to text length
        audio_size_bytes = int(len(text) * 100 * speed)

        result = {
            "action": "synthesize",
            "audio_size_bytes": audio_size_bytes,
            "language": language,
            "voice": voice,
            "speed": speed,
            "duration_seconds": len(text.split()) * 0.3 / speed,
        }

        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.syntheses.append(result)

        return result

    # ── Language detection ──

    async def _detect_language(self, task: Task) -> Dict[str, Any]:
        """Detect the language of audio or text input.

        Payload fields:
        * ``audio_data`` – audio sample (optional).
        * ``text`` – text sample (optional).
        """
        text = task.payload.get("text", "")
        audio_data = task.payload.get("audio_data")

        # Simple heuristic: check for common words
        detected_language = self._language
        confidence = 0.98

        text_lower = text.lower() if text else ""
        lang_markers = {
            "en-US": ["the", "is", "and", "hello"],
            "es-ES": ["el", "la", "es", "hola"],
            "fr-FR": ["le", "la", "est", "bonjour"],
            "de-DE": ["der", "die", "ist", "hallo"],
            "ja-JP": ["は", "の", "に", "こんにちは"],
        }
        best_score = 0
        for lang, markers in lang_markers.items():
            score = sum(1 for m in markers if m in text_lower)
            if score > best_score:
                best_score = score
                detected_language = lang

        if best_score > 0:
            confidence = min(1.0, 0.7 + best_score * 0.05)

        return {
            "action": "detect_language",
            "language": detected_language,
            "confidence": confidence,
            "supported": detected_language in self._supported_languages,
        }

    # ── Voice command interpretation ──

    async def _interpret_command(self, task: Task) -> Dict[str, Any]:
        """Interpret a voice command from text into a structured intent.

        Parses the text against known command patterns and returns a
        structured intent with extracted parameters.
        """
        text = task.payload.get("text", "").lower()
        language = task.payload.get("language", self._language)

        intent = "unknown"
        parameters: Dict[str, Any] = {}
        confidence = 0.5

        for cmd_intent, patterns in VOICE_COMMAND_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    intent = cmd_intent
                    # Extract parameter: everything after the pattern
                    remainder = text.split(pattern, 1)[-1].strip()
                    if remainder:
                        parameters["target"] = remainder
                    confidence = 0.85
                    break
            if intent != "unknown":
                break

        return {
            "action": "interpret_command",
            "text": task.payload.get("text", ""),
            "intent": intent,
            "parameters": parameters,
            "confidence": confidence,
            "language": language,
        }

    # ── Session management ──

    def _create_session(self, task: Task) -> Dict[str, Any]:
        """Create a new voice session."""
        language = task.payload.get("language", self._language)
        session = VoiceSession(language=language)
        self._sessions[session.session_id] = session
        return {"session_id": session.session_id, "language": language}

    def _list_languages(self) -> Dict[str, Any]:
        """List supported languages."""
        return {
            "languages": self._supported_languages,
            "current": self._language,
            "total": len(self._supported_languages),
        }

    # ── Configuration ──

    @property
    def language(self) -> str:
        """Current BCP-47 language code."""
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        if value in self._supported_languages:
            self._language = value

    @property
    def stt_enabled(self) -> bool:
        """Whether speech-to-text is enabled."""
        return self._stt_enabled

    @stt_enabled.setter
    def stt_enabled(self, value: bool) -> None:
        self._stt_enabled = value

    @property
    def tts_enabled(self) -> bool:
        """Whether text-to-speech is enabled."""
        return self._tts_enabled

    @tts_enabled.setter
    def tts_enabled(self, value: bool) -> None:
        self._tts_enabled = value
