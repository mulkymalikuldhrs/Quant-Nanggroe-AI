"""
🎙️ Voice Agent - Speech Processing & Voice Command System
Handles speech-to-text, text-to-speech, voice commands, and audio processing

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import os
import json
import time
import hashlib
import struct
import wave
import io
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional

# Optional: aiohttp for remote API calls (Whisper API, TTS providers)
try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


class VoiceAgent:
    """
    Voice Processing Agent that:
    - Handles speech-to-text (STT) processing via OpenAI Whisper API or local fallback
    - Generates text-to-speech (TTS) audio output
    - Parses and routes voice commands to other agents
    - Processes audio files and streams (WAV, MP3, etc.)
    - Integrates with Web Speech API on the frontend
    - Supports configurable providers (OpenAI Whisper, local, etc.)
    """

    def __init__(self):
        self.agent_id = "voice_agent"
        self.name = "Voice Agent"
        self.status = "ready"
        self.capabilities = [
            "speech_to_text",
            "text_to_speech",
            "voice_commands",
            "audio_processing",
            "command_routing",
            "stream_processing",
        ]

        # Provider configuration
        self.stt_provider = os.getenv("VOICE_STT_PROVIDER", "openai")   # openai | local
        self.tts_provider = os.getenv("VOICE_TTS_PROVIDER", "openai")   # openai | local
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # Audio settings
        self.sample_rate = int(os.getenv("VOICE_SAMPLE_RATE", "16000"))
        self.default_voice = os.getenv("VOICE_DEFAULT_VOICE", "alloy")
        self.default_tts_model = os.getenv("VOICE_TTS_MODEL", "tts-1")
        self.default_stt_model = os.getenv("VOICE_STT_MODEL", "whisper-1")

        # Voice command routing map
        self.command_routes = self._load_command_routes()

        # Performance tracking
        self._stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "stt_operations": 0,
            "tts_operations": 0,
            "commands_parsed": 0,
            "avg_processing_time": 0.0,
        }

        # Audio processing cache (transcription cache keyed by audio hash)
        self._transcription_cache: Dict[str, str] = {}

        # Session for API calls (created lazily)
        self._session: Optional[Any] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_command_routes(self) -> Dict[str, Dict[str, Any]]:
        """Load default voice command routing rules."""
        return {
            "create": {"agent": "dev_engine", "action": "create_project"},
            "deploy": {"agent": "deploy_manager", "action": "deploy"},
            "build": {"agent": "fullstack_dev", "action": "build"},
            "design": {"agent": "ui_designer", "action": "design"},
            "run": {"agent": "cybershell", "action": "execute"},
            "execute": {"agent": "cybershell", "action": "execute"},
            "sync": {"agent": "data_sync", "action": "sync_all"},
            "status": {"agent": "prompt_master", "action": "get_system_status"},
            "commit": {"agent": "github_agent", "action": "list_commits"},
            "monitor": {"agent": "agent_watcher", "action": "health_check"},
            "help": {"agent": "prompt_master", "action": "help"},
        }

    async def _get_session(self) -> Any:
        """Return (or create) an aiohttp ClientSession for API calls."""
        if not _AIOHTTP_AVAILABLE:
            return None
        if self._session is None or self._session.closed:
            headers = {}
            if self.openai_api_key:
                headers["Authorization"] = f"Bearer {self.openai_api_key}"
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            )
        return self._session

    def _hash_audio(self, audio_data: bytes) -> str:
        """Compute a quick hash of audio bytes for caching."""
        return hashlib.sha256(audio_data).hexdigest()

    # ------------------------------------------------------------------
    # Public task dispatcher
    # ------------------------------------------------------------------

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a task dictionary to the appropriate handler."""
        try:
            action = task.get("action", "speech_to_text")

            handlers = {
                "speech_to_text": self._speech_to_text,
                "text_to_speech": self._text_to_speech,
                "parse_command": self._parse_command,
                "route_command": self._route_command,
                "process_audio": self._process_audio,
                "list_voices": self._list_voices,
                "configure": self._configure,
                "transcribe_file": self._transcribe_file,
            }

            handler = handlers.get(action)
            if handler is None:
                return self._create_error_response(f"Unknown action: {action}")

            return await handler(task)

        except Exception as exc:
            return self._create_error_response(str(exc))

    # ------------------------------------------------------------------
    # Speech-to-Text
    # ------------------------------------------------------------------

    async def _speech_to_text(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe audio data to text.

        Supports:
        - Base64-encoded audio in task["audio_base64"]
        - Raw bytes in task["audio_data"]
        - File path in task["audio_file"]
        """
        start = time.time()
        audio_bytes: Optional[bytes] = None
        audio_format = task.get("audio_format", "wav")
        language = task.get("language")

        # Resolve audio source
        if task.get("audio_base64"):
            try:
                audio_bytes = base64.b64decode(task["audio_base64"])
            except Exception:
                return self._create_error_response("Invalid base64 audio data")
        elif task.get("audio_data") and isinstance(task["audio_data"], bytes):
            audio_bytes = task["audio_data"]
        elif task.get("audio_file"):
            try:
                with open(task["audio_file"], "rb") as f:
                    audio_bytes = f.read()
                # Infer format from extension
                ext = os.path.splitext(task["audio_file"])[1].lstrip(".").lower()
                if ext in ("mp3", "wav", "m4a", "ogg", "flac", "webm"):
                    audio_format = ext
            except FileNotFoundError:
                return self._create_error_response(f"Audio file not found: {task['audio_file']}")
        else:
            return self._create_error_response("No audio data provided (use audio_base64, audio_data, or audio_file)")

        # Check cache
        cache_key = self._hash_audio(audio_bytes)
        if cache_key in self._transcription_cache:
            self._stats["stt_operations"] += 1
            self._stats["successful_tasks"] += 1
            return {
                "success": True,
                "text": self._transcription_cache[cache_key],
                "cached": True,
                "provider": "cache",
            }

        # Dispatch to provider
        if self.stt_provider == "openai" and self.openai_api_key:
            result = await self._stt_openai(audio_bytes, audio_format, language)
        else:
            result = await self._stt_local(audio_bytes, audio_format)

        if result.get("success"):
            self._transcription_cache[cache_key] = result["text"]
            # Keep cache bounded
            if len(self._transcription_cache) > 500:
                oldest = list(self._transcription_cache.keys())[:100]
                for k in oldest:
                    del self._transcription_cache[k]

        elapsed = time.time() - start
        self._stats["stt_operations"] += 1
        self._update_stats(result.get("success", False), elapsed)

        return result

    async def _stt_openai(
        self, audio_bytes: bytes, audio_format: str, language: Optional[str]
    ) -> Dict[str, Any]:
        """Call OpenAI Whisper API for transcription."""
        if not _AIOHTTP_AVAILABLE:
            return self._create_error_response("aiohttp not installed; cannot call Whisper API")

        session = await self._get_session()
        if session is None:
            return self._create_error_response("aiohttp session could not be created")

        # Build multipart form
        filename = f"audio.{audio_format}"
        data = aiohttp.FormData()
        data.add_field("file", audio_bytes, filename=filename, content_type=f"audio/{audio_format}")
        data.add_field("model", self.default_stt_model)
        if language:
            data.add_field("language", language)

        url = f"{self.openai_base_url}/audio/transcriptions"

        try:
            async with session.post(url, data=data) as resp:
                body = await resp.text()
                if resp.status != 200:
                    try:
                        err = json.loads(body).get("error", {}).get("message", body[:300])
                    except json.JSONDecodeError:
                        err = body[:300]
                    return {"success": False, "error": f"Whisper API error: {err}"}

                result = json.loads(body)
                return {
                    "success": True,
                    "text": result.get("text", ""),
                    "language": result.get("language"),
                    "duration": result.get("duration"),
                    "provider": "openai_whisper",
                }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Whisper API request timed out"}
        except Exception as exc:
            return {"success": False, "error": f"Whisper API error: {exc}"}

    async def _stt_local(self, audio_bytes: bytes, audio_format: str) -> Dict[str, Any]:
        """
        Local fallback STT.

        Attempts to use the `whisper` Python package if installed,
        otherwise returns a graceful degradation message.
        """
        try:
            import whisper  # type: ignore

            model_name = os.getenv("VOICE_LOCAL_WHISPER_MODEL", "base")
            model = whisper.load_model(model_name)

            # Write to a temp file for whisper
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            result = model.transcribe(tmp_path)
            os.unlink(tmp_path)

            return {
                "success": True,
                "text": result.get("text", ""),
                "language": result.get("language"),
                "segments": len(result.get("segments", [])),
                "provider": "local_whisper",
            }
        except ImportError:
            return {
                "success": False,
                "error": (
                    "No STT provider available. Set OPENAI_API_KEY for Whisper API "
                    "or install the 'whisper' package for local transcription."
                ),
            }
        except Exception as exc:
            return {"success": False, "error": f"Local STT error: {exc}"}

    # ------------------------------------------------------------------
    # Text-to-Speech
    # ------------------------------------------------------------------

    async def _text_to_speech(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate speech audio from text."""
        start = time.time()
        text = task.get("text", "")
        if not text:
            return self._create_error_response("No text provided for TTS")

        voice = task.get("voice", self.default_voice)
        model = task.get("model", self.default_tts_model)
        output_format = task.get("output_format", "mp3")  # mp3, opus, aac, flac, wav
        speed = task.get("speed", 1.0)

        if self.tts_provider == "openai" and self.openai_api_key:
            result = await self._tts_openai(text, voice, model, output_format, speed)
        else:
            result = await self._tts_local(text, voice, output_format)

        elapsed = time.time() - start
        self._stats["tts_operations"] += 1
        self._update_stats(result.get("success", False), elapsed)

        return result

    async def _tts_openai(
        self,
        text: str,
        voice: str,
        model: str,
        output_format: str,
        speed: float,
    ) -> Dict[str, Any]:
        """Call OpenAI TTS API."""
        if not _AIOHTTP_AVAILABLE:
            return self._create_error_response("aiohttp not installed; cannot call TTS API")

        session = await self._get_session()
        if session is None:
            return self._create_error_response("aiohttp session could not be created")

        payload: Dict[str, Any] = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": output_format,
        }
        if speed != 1.0:
            payload["speed"] = speed

        url = f"{self.openai_base_url}/audio/speech"

        try:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    try:
                        err = json.loads(body).get("error", {}).get("message", body[:300])
                    except json.JSONDecodeError:
                        err = body[:300]
                    return {"success": False, "error": f"TTS API error: {err}"}

                audio_data = await resp.read()
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                return {
                    "success": True,
                    "audio_base64": audio_b64,
                    "audio_size_bytes": len(audio_data),
                    "format": output_format,
                    "voice": voice,
                    "provider": "openai_tts",
                }
        except asyncio.TimeoutError:
            return {"success": False, "error": "TTS API request timed out"}
        except Exception as exc:
            return {"success": False, "error": f"TTS API error: {exc}"}

    async def _tts_local(
        self, text: str, voice: str, output_format: str
    ) -> Dict[str, Any]:
        """
        Local fallback TTS.

        Attempts to use the ` pyttsx3 ` or `gTTS` package if installed,
        otherwise returns a graceful degradation message.
        """
        # Try gTTS first (easier async-friendly approach)
        try:
            from gtts import gTTS  # type: ignore

            tts = gTTS(text=text, lang="en")
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            audio_data = buf.read()
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")

            return {
                "success": True,
                "audio_base64": audio_b64,
                "audio_size_bytes": len(audio_data),
                "format": "mp3",
                "voice": "gtts-default",
                "provider": "gtts",
            }
        except ImportError:
            pass

        # Try pyttsx3
        try:
            import pyttsx3  # type: ignore

            engine = pyttsx3.init()
            buf = io.BytesIO()
            # pyttsx3 doesn't support in-memory easily; create a temp file
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            engine.save_to_file(text, tmp_path)
            engine.runAndWait()

            with open(tmp_path, "rb") as f:
                audio_data = f.read()
            os.unlink(tmp_path)

            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            return {
                "success": True,
                "audio_base64": audio_b64,
                "audio_size_bytes": len(audio_data),
                "format": "wav",
                "voice": "pyttsx3-default",
                "provider": "pyttsx3",
            }
        except ImportError:
            pass

        return {
            "success": False,
            "error": (
                "No TTS provider available. Set OPENAI_API_KEY for OpenAI TTS "
                "or install 'gTTS' or 'pyttsx3' for local speech synthesis."
            ),
        }

    # ------------------------------------------------------------------
    # Voice Command Parsing & Routing
    # ------------------------------------------------------------------

    async def _parse_command(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a voice transcript into a structured command.

        Expects task["text"] to be the transcribed voice text.
        """
        text = task.get("text", "")
        if not text:
            return self._create_error_response("No text provided to parse as command")

        text_lower = text.lower().strip()

        # Simple keyword-based parsing
        parsed = self._extract_command(text_lower)
        self._stats["commands_parsed"] += 1

        return {
            "success": True,
            "original_text": text,
            "command": parsed["command"],
            "parameters": parsed["parameters"],
            "routed_agent": parsed.get("routed_agent"),
            "confidence": parsed.get("confidence", 0.0),
        }

    def _extract_command(self, text: str) -> Dict[str, Any]:
        """
        Extract command intent and parameters from lowercased text.

        Uses keyword matching against the command routing table.
        """
        words = text.split()
        best_command = None
        best_route = None
        best_position = len(words)  # earlier match = higher priority

        for keyword, route in self.command_routes.items():
            for i, word in enumerate(words):
                if keyword in word and i < best_position:
                    best_command = keyword
                    best_route = route
                    best_position = i
                    break

        if best_command is None:
            return {
                "command": "unknown",
                "parameters": {"raw_text": text},
                "routed_agent": None,
                "confidence": 0.0,
            }

        # Collect remaining words as parameters
        param_words = [w for i, w in enumerate(words) if i != best_position]
        params: Dict[str, Any] = {"raw_text": text, "args": param_words}

        # Extract quoted strings as a single argument
        import re

        quoted = re.findall(r'"([^"]*)"', text)
        if quoted:
            params["quoted_args"] = quoted

        confidence = 0.7 + 0.3 * (1.0 / (best_position + 1))

        return {
            "command": best_command,
            "parameters": params,
            "routed_agent": best_route.get("agent") if best_route else None,
            "routed_action": best_route.get("action") if best_route else None,
            "confidence": round(confidence, 2),
        }

    async def _route_command(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a voice command AND route it to the appropriate agent.

        This is a convenience action that combines parse_command with agent dispatch.
        """
        parse_result = await self._parse_command(task)
        if not parse_result.get("success"):
            return parse_result

        routed_agent = parse_result.get("routed_agent")
        routed_action = parse_result.get("routed_action")

        if not routed_agent:
            return {
                "success": False,
                "error": "Could not determine target agent for command",
                "parsed": parse_result,
            }

        # Attempt to import and dispatch to the target agent
        try:
            agent = self._get_agent_module(routed_agent)
            if agent is None:
                return {
                    "success": False,
                    "error": f"Agent '{routed_agent}' is not available",
                    "parsed": parse_result,
                }

            agent_task = {
                "action": routed_action,
                "prompt": task.get("text", ""),
                "parameters": parse_result.get("parameters", {}),
            }

            result = await agent.process_task(agent_task)
            return {
                "success": result.get("success", False),
                "routed_agent": routed_agent,
                "routed_action": routed_action,
                "parsed": parse_result,
                "result": result,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": f"Error routing to {routed_agent}: {exc}",
                "parsed": parse_result,
            }

    def _get_agent_module(self, agent_name: str) -> Any:
        """Lazily import an agent module by name."""
        try:
            if agent_name == "cybershell":
                from agents.cybershell import CyberShellAgent
                return CyberShellAgent()
            elif agent_name == "dev_engine":
                from agents.dev_engine import DevEngineAgent
                return DevEngineAgent()
            elif agent_name == "deploy_manager":
                from agents.deploy_manager import DeployManagerAgent
                return DeployManagerAgent()
            elif agent_name == "fullstack_dev":
                from agents.fullstack_dev import FullStackDevAgent
                return FullStackDevAgent()
            elif agent_name == "ui_designer":
                from agents.ui_designer import UIDesignerAgent
                return UIDesignerAgent()
            elif agent_name == "data_sync":
                from agents.data_sync import DataSyncAgent
                return DataSyncAgent()
            elif agent_name == "github_agent":
                from agents.github_agent import GitHubAgent
                return GitHubAgent()
            elif agent_name == "prompt_master":
                from core.prompt_master import PromptMasterAgent
                return PromptMasterAgent()
            elif agent_name == "agent_watcher":
                from agents.agent_watcher import AgentWatcherAgent
                return AgentWatcherAgent()
            else:
                return None
        except ImportError:
            return None

    # ------------------------------------------------------------------
    # Audio Processing
    # ------------------------------------------------------------------

    async def _process_audio(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an audio file/stream: extract metadata, validate format,
        convert sample rate, or strip silence.
        """
        audio_file = task.get("audio_file", "")
        operation = task.get("operation", "metadata")  # metadata | validate | convert

        if not audio_file:
            return self._create_error_response("No audio_file path provided")

        if not os.path.isfile(audio_file):
            return self._create_error_response(f"File not found: {audio_file}")

        try:
            if operation == "metadata":
                return self._audio_metadata(audio_file)
            elif operation == "validate":
                return self._audio_validate(audio_file)
            elif operation == "convert":
                return await self._audio_convert(task)
            else:
                return self._create_error_response(f"Unknown audio operation: {operation}")
        except Exception as exc:
            return self._create_error_response(f"Audio processing error: {exc}")

    def _audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from an audio file."""
        file_size = os.path.getsize(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        metadata: Dict[str, Any] = {
            "success": True,
            "file_path": file_path,
            "file_size": file_size,
            "extension": ext,
        }

        # WAV-specific metadata
        if ext == ".wav":
            try:
                with wave.open(file_path, "rb") as wf:
                    metadata.update(
                        {
                            "channels": wf.getnchannels(),
                            "sample_width": wf.getsampwidth(),
                            "frame_rate": wf.getframerate(),
                            "num_frames": wf.getnframes(),
                            "duration_seconds": wf.getnframes() / wf.getframerate(),
                            "compression_type": wf.getcomptype(),
                        }
                    )
            except Exception:
                metadata["wav_parse_error"] = "Could not parse WAV header"

        return metadata

    def _audio_validate(self, file_path: str) -> Dict[str, Any]:
        """Validate an audio file's integrity."""
        ext = os.path.splitext(file_path)[1].lower()
        valid = False
        details = ""

        if ext == ".wav":
            try:
                with wave.open(file_path, "rb") as wf:
                    wf.getnframes()  # attempt to read
                valid = True
                details = "WAV file is valid"
            except Exception as exc:
                details = f"Invalid WAV: {exc}"
        else:
            # Basic check: non-zero file size
            valid = os.path.getsize(file_path) > 0
            details = "Basic file-size validation only for non-WAV formats"

        return {"success": True, "valid": valid, "details": details, "file_path": file_path}

    async def _audio_convert(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert audio sample rate using basic WAV re-encoding.

        For production use, consider installing `pydub` + `ffmpeg`.
        """
        file_path = task.get("audio_file", "")
        target_rate = int(task.get("target_sample_rate", 16000))
        output_path = task.get("output_path", "")

        if not output_path:
            base, ext = os.path.splitext(file_path)
            output_path = f"{base}_{target_rate}hz{ext}"

        try:
            with wave.open(file_path, "rb") as wf:
                params = wf.getparams()
                frames = wf.readframes(wf.getnframes())

            # If already at target rate, just copy
            if params.framerate == target_rate:
                import shutil

                shutil.copy2(file_path, output_path)
                return {
                    "success": True,
                    "output_path": output_path,
                    "note": "File was already at target sample rate; copied as-is",
                }

            # Simple resampling via linear interpolation
            import array

            ratio = target_rate / params.framerate
            old_samples = array.array("h", frames)
            new_length = int(len(old_samples) * ratio)
            new_samples = array.array("h", (0,) * new_length)

            for i in range(new_length):
                src_idx = i / ratio
                low = int(src_idx)
                high = min(low + 1, len(old_samples) - 1)
                frac = src_idx - low
                new_samples[i] = int(old_samples[low] * (1 - frac) + old_samples[high] * frac)

            with wave.open(output_path, "wb") as wf_out:
                wf_out.setnchannels(params.nchannels)
                wf_out.setsampwidth(params.sampwidth)
                wf_out.setframerate(target_rate)
                wf_out.writeframes(new_samples.tobytes())

            return {
                "success": True,
                "output_path": output_path,
                "original_rate": params.framerate,
                "target_rate": target_rate,
                "output_size": os.path.getsize(output_path),
            }

        except Exception as exc:
            return {"success": False, "error": f"Audio conversion failed: {exc}"}

    async def _transcribe_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience: transcribe a file on disk (wraps speech_to_text)."""
        return await self._speech_to_text(task)

    async def _list_voices(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """List available TTS voices."""
        if self.tts_provider == "openai" and self.openai_api_key and _AIOHTTP_AVAILABLE:
            session = await self._get_session()
            if session:
                try:
                    url = f"{self.openai_base_url}/audio/speech"
                    # OpenAI doesn't have a /voices endpoint; we document known voices
                    pass
                except Exception:
                    pass

        # Return known voice catalog
        voices = [
            {"id": "alloy", "name": "Alloy", "provider": "openai", "description": "Balanced, neutral tone"},
            {"id": "echo", "name": "Echo", "provider": "openai", "description": "Warm, conversational"},
            {"id": "fable", "name": "Fable", "provider": "openai", "description": "Expressive storyteller"},
            {"id": "onyx", "name": "Onyx", "provider": "openai", "description": "Deep, authoritative"},
            {"id": "nova", "name": "Nova", "provider": "openai", "description": "Friendly, upbeat"},
            {"id": "shimmer", "name": "Shimmer", "provider": "openai", "description": "Clear, professional"},
        ]

        return {
            "success": True,
            "voices": voices,
            "default_voice": self.default_voice,
            "tts_provider": self.tts_provider,
        }

    async def _configure(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update voice agent configuration at runtime."""
        if task.get("stt_provider"):
            self.stt_provider = task["stt_provider"]
        if task.get("tts_provider"):
            self.tts_provider = task["tts_provider"]
        if task.get("default_voice"):
            self.default_voice = task["default_voice"]
        if task.get("default_tts_model"):
            self.default_tts_model = task["default_tts_model"]
        if task.get("default_stt_model"):
            self.default_stt_model = task["default_stt_model"]
        if task.get("sample_rate"):
            self.sample_rate = int(task["sample_rate"])

        # Rebuild session if API key changed
        if task.get("openai_api_key"):
            self.openai_api_key = task["openai_api_key"]
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None

        return {
            "success": True,
            "configuration": {
                "stt_provider": self.stt_provider,
                "tts_provider": self.tts_provider,
                "default_voice": self.default_voice,
                "default_tts_model": self.default_tts_model,
                "default_stt_model": self.default_stt_model,
                "sample_rate": self.sample_rate,
                "openai_configured": bool(self.openai_api_key),
            },
        }

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------

    def _update_stats(self, success: bool, elapsed: float):
        """Update running performance statistics."""
        self._stats["total_tasks"] += 1
        if success:
            self._stats["successful_tasks"] += 1
        else:
            self._stats["failed_tasks"] += 1
        total = self._stats["total_tasks"]
        current_avg = self._stats["avg_processing_time"]
        self._stats["avg_processing_time"] = (current_avg * (total - 1) + elapsed) / total

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        self._stats["failed_tasks"] += 1
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return agent performance metrics."""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "capabilities": self.capabilities,
            "stats": self._stats,
            "stt_provider": self.stt_provider,
            "tts_provider": self.tts_provider,
            "openai_configured": bool(self.openai_api_key),
            "cache_size": len(self._transcription_cache),
        }

    async def close(self):
        """Clean up the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global instance
voice_agent = VoiceAgent()
