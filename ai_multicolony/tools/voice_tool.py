"""Voice I/O tool for the AI MultiColony Ecosystem.

Provides speech-to-text (STT) and text-to-speech (TTS) capabilities
with local Whisper + API fallback for STT, and local + API fallback
for TTS, plus audio format conversion.
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
import struct
import tempfile
import wave
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


def _detect_wav_params(data: bytes) -> dict[str, Any]:
    """Detect WAV audio parameters from raw bytes.

    Args:
        data: Raw WAV bytes.

    Returns:
        Dict with sample_rate, channels, sample_width.
    """
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            return {
                "sample_rate": wf.getframerate(),
                "channels": wf.getnchannels(),
                "sample_width": wf.getsampwidth(),
                "frames": wf.getnframes(),
            }
    except Exception:
        return {"sample_rate": 16000, "channels": 1, "sample_width": 2, "frames": 0}


def _raw_pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """Convert raw PCM data to WAV format.

    Args:
        pcm_data: Raw PCM audio bytes.
        sample_rate: Sample rate in Hz.
        channels: Number of channels.
        sample_width: Sample width in bytes.

    Returns:
        WAV-formatted bytes.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _convert_audio_format(
    input_data: bytes,
    input_format: str = "wav",
    output_format: str = "wav",
) -> bytes:
    """Convert audio between formats (best-effort).

    Supports WAV <-> raw PCM conversions.  For MP3/OGG, falls back
    to pydub if available, otherwise returns the original data.

    Args:
        input_data: Input audio bytes.
        input_format: Input format (wav, mp3, ogg, pcm).
        output_format: Desired output format.

    Returns:
        Converted audio bytes.
    """
    if input_format == output_format:
        return input_data

    # WAV <-> PCM
    if input_format == "pcm" and output_format == "wav":
        return _raw_pcm_to_wav(input_data)

    if input_format == "wav" and output_format == "pcm":
        try:
            with wave.open(io.BytesIO(input_data), "rb") as wf:
                return wf.readframes(wf.getnframes())
        except Exception:
            return input_data

    # Try pydub for MP3/OGG conversions
    try:
        from pydub import AudioSegment
        segment = AudioSegment.from_file(io.BytesIO(input_data), format=input_format)
        out_buf = io.BytesIO()
        segment.export(out_buf, format=output_format)
        return out_buf.getvalue()
    except ImportError:
        logger.warning("pydub_not_available", msg="Install pydub for MP3/OGG conversion")
        return input_data
    except Exception as e:
        logger.warning("audio_conversion_error", error=str(e))
        return input_data


class VoiceTool(BaseTool):
    """Voice STT/TTS tool with API fallback.

    Features:
    - Speech-to-Text (STT) transcription using local Whisper model
    - STT API fallback (OpenAI-compatible API)
    - Text-to-Speech (TTS) synthesis using local pyttsx3
    - TTS API fallback (OpenAI-compatible API)
    - Multi-language support
    - Audio format conversion (WAV, MP3, OGG, raw PCM)
    - Language detection
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._default_language = self._config.get("language", "en")
        self._whisper_model_size = self._config.get("whisper_model_size", "base")
        self._openai_api_key = self._config.get("openai_api_key", os.environ.get("OPENAI_API_KEY"))
        self._openai_base_url = self._config.get(
            "openai_base_url", "https://api.openai.com/v1"
        )
        self._tts_voice = self._config.get("tts_voice", "alloy")

        # Cache loaded models
        self._whisper_model: Any = None

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="voice",
            description="Speech-to-text and text-to-speech with API fallback and format conversion",
            tool_type=ToolType.VOICE,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Voice action: transcribe, synthesize, detect_language, convert_format",
                    required=True,
                    enum=["transcribe", "synthesize", "detect_language", "convert_format"],
                ),
                ToolParameter(
                    name="audio",
                    type="string",
                    description="Audio input (base64 encoded or file path) for transcription",
                    required=False,
                ),
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to synthesize to speech",
                    required=False,
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Language code (e.g., en, es, fr, de, zh, ja)",
                    required=False,
                    default=self._default_language,
                ),
                ToolParameter(
                    name="output_format",
                    type="string",
                    description="Output audio format",
                    required=False,
                    default="wav",
                    enum=["wav", "mp3", "ogg", "pcm"],
                ),
                ToolParameter(
                    name="voice",
                    type="string",
                    description="Voice name or ID for TTS",
                    required=False,
                ),
                ToolParameter(
                    name="input_format",
                    type="string",
                    description="Input audio format for conversion",
                    required=False,
                    default="wav",
                    enum=["wav", "mp3", "ogg", "pcm"],
                ),
                ToolParameter(
                    name="use_api",
                    type="boolean",
                    description="Use API instead of local model (for transcribe/synthesize)",
                    required=False,
                    default=False,
                ),
            ],
            tags=["voice", "stt", "tts", "audio"],
            requires_permission="voice.use",
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a voice action."""
        action = tool_call.arguments.get("action", "")

        dispatch = {
            "transcribe": self._transcribe,
            "synthesize": self._synthesize,
            "detect_language": self._detect_language,
            "convert_format": self._convert_format,
        }

        handler = dispatch.get(action)
        if handler is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=False, error=f"Unknown voice action: {action}",
            )
        return await handler(tool_call)

    # ------------------------------------------------------------------
    # STT
    # ------------------------------------------------------------------

    async def _transcribe(self, tool_call: ToolCall) -> ToolResult:
        """Transcribe audio to text.

        Tries local Whisper first, then falls back to API.
        """
        audio = tool_call.arguments.get("audio", "")
        language = tool_call.arguments.get("language", self._default_language)
        use_api = tool_call.arguments.get("use_api", False)

        if not audio:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=False, error="No audio input specified",
            )

        # Prepare audio file
        audio_path = await self._prepare_audio_file(audio)

        # Try API first if requested
        if use_api:
            result = await self._transcribe_api(audio_path, language)
            if result is not None:
                return result

        # Try local Whisper
        result = await self._transcribe_whisper(audio_path, language)
        if result is not None:
            return result

        # Fallback to API if local failed and API wasn't tried first
        if not use_api:
            result = await self._transcribe_api(audio_path, language)
            if result is not None:
                return result

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="voice",
            success=False,
            error="All transcription methods failed (local Whisper and API)",
        )

    async def _transcribe_whisper(self, audio_path: str, language: str) -> Optional[ToolResult]:
        """Transcribe using local Whisper model."""
        try:
            import whisper

            if self._whisper_model is None:
                self._whisper_model = whisper.load_model(self._whisper_model_size)

            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._whisper_model.transcribe(audio_path, language=language),
            )

            text = result.get("text", "")
            detected_lang = result.get("language", language)

            return ToolResult(
                tool_call_id="", tool_name="voice",
                success=True, output=text.strip(),
                metadata={
                    "engine": "whisper_local",
                    "language": detected_lang,
                    "model_size": self._whisper_model_size,
                },
            )
        except ImportError:
            logger.info("whisper_not_installed")
            return None
        except Exception as e:
            logger.warning("whisper_transcribe_error", error=str(e))
            return None

    async def _transcribe_api(self, audio_path: str, language: str) -> Optional[ToolResult]:
        """Transcribe using OpenAI-compatible API."""
        if not self._openai_api_key:
            logger.info("no_openai_api_key")
            return None

        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        f"{self._openai_base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self._openai_api_key}"},
                        files={"file": ("audio.wav", f, "audio/wav")},
                        data={"model": "whisper-1", "language": language},
                    )

                if response.status_code != 200:
                    logger.warning("api_transcribe_error", status=response.status_code)
                    return None

                data = response.json()
                text = data.get("text", "")

                return ToolResult(
                    tool_call_id="", tool_name="voice",
                    success=True, output=text.strip(),
                    metadata={
                        "engine": "api",
                        "language": data.get("language", language),
                    },
                )
        except ImportError:
            logger.info("httpx_not_installed")
            return None
        except Exception as e:
            logger.warning("api_transcribe_error", error=str(e))
            return None

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    async def _synthesize(self, tool_call: ToolCall) -> ToolResult:
        """Synthesize text to speech.

        Tries local pyttsx3 first, then falls back to API.
        """
        text = tool_call.arguments.get("text", "")
        language = tool_call.arguments.get("language", self._default_language)
        voice = tool_call.arguments.get("voice", self._tts_voice)
        output_format = tool_call.arguments.get("output_format", "wav")
        use_api = tool_call.arguments.get("use_api", False)

        if not text:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=False, error="No text specified for synthesis",
            )

        # Try API first if requested
        if use_api:
            result = await self._synthesize_api(text, voice, output_format)
            if result is not None:
                return result

        # Try local TTS
        result = await self._synthesize_local(text, voice, output_format)
        if result is not None:
            return result

        # Fallback to API if local failed
        if not use_api:
            result = await self._synthesize_api(text, voice, output_format)
            if result is not None:
                return result

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="voice",
            success=False,
            error="All TTS methods failed (local pyttsx3 and API)",
        )

    async def _synthesize_local(
        self, text: str, voice: str, output_format: str,
    ) -> Optional[ToolResult]:
        """Synthesize using local pyttsx3 engine."""
        try:
            import pyttsx3

            engine = pyttsx3.init()

            # Configure voice
            if voice and voice != "default":
                voices = engine.getProperty("voices")
                for v in voices:
                    if voice.lower() in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break

            output_path = tempfile.mktemp(suffix=f".{output_format}")
            engine.save_to_file(text, output_path)
            engine.runAndWait()

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                with open(output_path, "rb") as f:
                    audio_bytes = f.read()

                b64 = base64.b64encode(audio_bytes).decode("utf-8")

                return ToolResult(
                    tool_call_id="", tool_name="voice",
                    success=True,
                    output=f"Audio synthesized locally ({len(audio_bytes)} bytes, {output_format})",
                    metadata={
                        "engine": "pyttsx3_local",
                        "format": output_format,
                        "audio_b64": b64,
                        "size_bytes": len(audio_bytes),
                    },
                )
            return None
        except ImportError:
            logger.info("pyttsx3_not_installed")
            return None
        except Exception as e:
            logger.warning("local_tts_error", error=str(e))
            return None

    async def _synthesize_api(
        self, text: str, voice: str, output_format: str,
    ) -> Optional[ToolResult]:
        """Synthesize using OpenAI-compatible TTS API."""
        if not self._openai_api_key:
            logger.info("no_openai_api_key")
            return None

        try:
            import httpx

            # Map output format to API format
            api_format_map = {"wav": "wav", "mp3": "mp3", "ogg": "opus", "pcm": "pcm"}
            api_format = api_format_map.get(output_format, "wav")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self._openai_base_url}/audio/speech",
                    headers={"Authorization": f"Bearer {self._openai_api_key}"},
                    json={
                        "model": "tts-1",
                        "input": text,
                        "voice": voice,
                        "response_format": api_format,
                    },
                )

                if response.status_code != 200:
                    logger.warning("api_tts_error", status=response.status_code)
                    return None

                audio_bytes = response.content
                b64 = base64.b64encode(audio_bytes).decode("utf-8")

                return ToolResult(
                    tool_call_id="", tool_name="voice",
                    success=True,
                    output=f"Audio synthesized via API ({len(audio_bytes)} bytes, {output_format})",
                    metadata={
                        "engine": "api",
                        "format": output_format,
                        "audio_b64": b64,
                        "size_bytes": len(audio_bytes),
                    },
                )
        except ImportError:
            logger.info("httpx_not_installed")
            return None
        except Exception as e:
            logger.warning("api_tts_error", error=str(e))
            return None

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    async def _detect_language(self, tool_call: ToolCall) -> ToolResult:
        """Detect the language of audio input."""
        audio = tool_call.arguments.get("audio", "")
        if not audio:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=False, error="No audio input specified",
            )

        audio_path = await self._prepare_audio_file(audio)

        # Try Whisper for language detection
        try:
            import whisper

            if self._whisper_model is None:
                self._whisper_model = whisper.load_model(self._whisper_model_size)

            # Load audio and detect language
            audio_data = whisper.load_audio(audio_path)
            audio_padded = whisper.pad_or_trim(audio_data)
            mel = whisper.log_mel_spectrogram(audio_padded).to(self._whisper_model.device)
            _, probs = self._whisper_model.detect_language(mel)
            detected_lang = max(probs, key=probs.get)

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=True,
                output=f"Detected language: {detected_lang}",
                metadata={
                    "language": detected_lang,
                    "confidence": float(probs[detected_lang]),
                    "top_languages": dict(
                        sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
                    ),
                },
            )
        except ImportError:
            # Fallback: simple heuristic
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=True,
                output=f"Detected language: {self._default_language} (heuristic fallback)",
                metadata={"language": self._default_language, "confidence": 0.5, "method": "heuristic"},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=False, error=f"Language detection failed: {e}",
            )

    # ------------------------------------------------------------------
    # Format conversion
    # ------------------------------------------------------------------

    async def _convert_format(self, tool_call: ToolCall) -> ToolResult:
        """Convert audio between formats."""
        audio = tool_call.arguments.get("audio", "")
        input_format = tool_call.arguments.get("input_format", "wav")
        output_format = tool_call.arguments.get("output_format", "mp3")

        if not audio:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=False, error="No audio input specified",
            )

        # Decode audio data
        try:
            audio_data = await self._decode_audio(audio)
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="voice",
                success=False, error=f"Failed to decode audio: {e}",
            )

        # Convert
        converted = _convert_audio_format(audio_data, input_format, output_format)
        b64 = base64.b64encode(converted).decode("utf-8")

        return ToolResult(
            tool_call_id=tool_call.id, tool_name="voice",
            success=True,
            output=f"Converted audio from {input_format} to {output_format} ({len(converted)} bytes)",
            metadata={
                "input_format": input_format,
                "output_format": output_format,
                "input_size": len(audio_data),
                "output_size": len(converted),
                "audio_b64": b64,
            },
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    async def _prepare_audio_file(self, audio: str) -> str:
        """Prepare an audio file from base64 or file path.

        Args:
            audio: Base64 encoded audio data or file path.

        Returns:
            Path to the audio file.
        """
        # If it looks like a file path that exists, use it directly
        if os.path.isfile(audio):
            return audio

        # Otherwise treat as base64
        audio_data = audio
        if "," in audio and audio.startswith("data:"):
            audio_data = audio.split(",", 1)[1]

        raw_bytes = base64.b64decode(audio_data)

        # Write to temp file (ensure WAV format for Whisper compatibility)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Check if the raw bytes are already WAV
            if raw_bytes[:4] == b"RIFF":
                f.write(raw_bytes)
            else:
                # Assume raw PCM and convert to WAV
                wav_bytes = _raw_pcm_to_wav(raw_bytes)
                f.write(wav_bytes)
            return f.name

    async def _decode_audio(self, audio: str) -> bytes:
        """Decode audio from base64 or file path.

        Args:
            audio: Base64 encoded audio data or file path.

        Returns:
            Raw audio bytes.
        """
        if os.path.isfile(audio):
            with open(audio, "rb") as f:
                return f.read()

        audio_data = audio
        if "," in audio and audio.startswith("data:"):
            audio_data = audio.split(",", 1)[1]

        return base64.b64decode(audio_data)
