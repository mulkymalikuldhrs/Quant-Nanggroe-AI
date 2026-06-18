"""Voice agent - from AgenticSeek STT/TTS pattern.

Specializes in speech-to-text, text-to-speech, voice commands,
and multi-language voice interactions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.agents.voice.prompts import (
    VOICE_SYSTEM_PROMPT,
    VOICE_CONVERSATION_PROMPT,
    VOICE_COMMAND_PROCESSING_PROMPT,
    VOICE_TRANSCRIPTION_PROMPT,
    VOICE_TTS_PROMPT,
    VOICE_MULTI_LANGUAGE_PROMPT,
)

logger = get_logger(__name__)


class VoiceAgent(BaseAgent):
    """Voice agent for STT/TTS integration.

    From AgenticSeek pattern. Handles speech-to-text transcription,
    text-to-speech synthesis, and voice-based interactions including
    command processing and multi-language support.

    State-specific behavior:
    - IDLE: Ready for voice input
    - RUNNING: Processing voice input or generating speech output
    - THINKING: Transcribing or analyzing audio
    - WAITING: Waiting for audio input or TTS completion
    - PAUSED: Voice processing paused
    - ERROR: Audio processing error, attempts recovery
    """

    # Track voice interactions
    _conversation_history: list[dict[str, Any]]
    _languages_supported: list[str]
    _current_language: str = "en"
    _is_listening: bool = False

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.VOICE,
                name="voice-agent",
                description="Voice input/output processing with STT/TTS",
                tools=["voice", "memory", "channel"],
                system_prompt=VOICE_SYSTEM_PROMPT,
                temperature=0.3,
                capabilities=AgentCapabilities(
                    voice_input=True,
                    voice_output=True,
                    memory_management=True,
                    mcp_protocol=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = VOICE_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["voice", "memory", "channel"]

        super().__init__(config=config, **kwargs)
        self._conversation_history = []
        self._languages_supported = ["en", "es", "fr", "de", "zh", "ja", "ko"]
        self._current_language = "en"
        self._is_listening = False

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names VoiceAgent requires.

        Returns:
            Tools needed for voice operations.
        """
        return ["voice", "memory", "channel"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Voice agent."""
        return self.config.system_prompt or VOICE_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "voice_agent_running",
            agent_id=self.agent_id,
            language=self._current_language,
            conversations=len(self._conversation_history),
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state."""
        logger.warning(
            "voice_agent_error",
            agent_id=self.agent_id,
            error_count=self.error_count,
        )

    def _on_enter_waiting(self) -> None:
        """Hook called when entering WAITING state."""
        self._is_listening = True
        logger.info("voice_agent_listening", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # Core voice methods
    # ------------------------------------------------------------------

    async def process_audio(self, audio_input: str, language: str = "en") -> str:
        """Process audio input and generate a response.

        Full pipeline: STT -> process -> TTS-ready output.

        Args:
            audio_input: Audio input (base64 or file path).
            language: Language code for processing.

        Returns:
            The voice agent's response formatted for TTS.
        """
        self._current_language = language

        # Step 1: Transcribe
        transcription = await self.transcribe(audio_input, language)

        # Step 2: Generate response
        conversation_prompt = VOICE_CONVERSATION_PROMPT.format(transcription=transcription)
        response = await self.run(conversation_prompt)

        # Record conversation
        self._conversation_history.append({
            "type": "conversation",
            "transcription": transcription[:200],
            "response": response[:200],
            "language": language,
        })

        return response

    async def transcribe(self, audio_input: str, language: str = "en") -> str:
        """Transcribe audio to text.

        Args:
            audio_input: Audio input (base64 or file path).
            language: Language code for transcription.

        Returns:
            Transcribed text.
        """
        prompt = VOICE_TRANSCRIPTION_PROMPT.format(
            language=language,
            audio_description=audio_input[:300],
        )
        result = await self.run(prompt)

        self._conversation_history.append({
            "type": "transcription",
            "language": language,
            "result_preview": result[:200],
        })

        return result

    async def speak(self, text: str, language: str = "en") -> str:
        """Convert text to speech-ready format.

        Args:
            text: Text to convert to speech.
            language: Language code for TTS.

        Returns:
            Speech-ready text with pronunciation hints.
        """
        prompt = VOICE_TTS_PROMPT.format(text=text, language=language)
        result = await self.run(prompt)

        self._conversation_history.append({
            "type": "tts",
            "text_preview": text[:100],
            "language": language,
        })

        return result

    async def process_command(self, transcription: str) -> str:
        """Process a voice command.

        Identifies the command type, extracts parameters,
        and executes the appropriate action.

        Args:
            transcription: The transcribed voice command.

        Returns:
            Command execution result formatted for TTS.
        """
        prompt = VOICE_COMMAND_PROCESSING_PROMPT.format(transcription=transcription)
        result = await self.run(prompt)

        self._conversation_history.append({
            "type": "command",
            "command": transcription[:100],
            "result_preview": result[:200],
        })

        return result

    async def handle_multi_language(
        self,
        user_input: str,
        detected_language: str,
        requested_language: Optional[str] = None,
    ) -> str:
        """Handle a multi-language voice interaction.

        Args:
            user_input: The user's input text.
            detected_language: The detected language of the input.
            requested_language: The language to respond in (if different).

        Returns:
            Response in the appropriate language.
        """
        prompt = VOICE_MULTI_LANGUAGE_PROMPT.format(
            detected_language=detected_language,
            user_input=user_input,
            requested_language=requested_language or detected_language,
        )
        result = await self.run(prompt)

        self._conversation_history.append({
            "type": "multi_language",
            "detected_language": detected_language,
            "requested_language": requested_language,
            "result_preview": result[:200],
        })

        return result

    # ------------------------------------------------------------------
    # Listening state management
    # ------------------------------------------------------------------

    def start_listening(self) -> None:
        """Mark the agent as actively listening for voice input."""
        self._is_listening = True
        logger.info("voice_listening_started", agent_id=self.agent_id)

    def stop_listening(self) -> None:
        """Mark the agent as no longer listening."""
        self._is_listening = False
        logger.info("voice_listening_stopped", agent_id=self.agent_id)

    @property
    def is_listening(self) -> bool:
        """Whether the agent is currently listening for input."""
        return self._is_listening

    @property
    def current_language(self) -> str:
        """The current language for voice processing."""
        return self._current_language

    def set_language(self, language: str) -> None:
        """Set the current language for voice processing.

        Args:
            language: Language code (e.g., 'en', 'es', 'fr').
        """
        if language in self._languages_supported:
            self._current_language = language
        else:
            logger.warning(
                "unsupported_language",
                agent_id=self.agent_id,
                language=language,
                supported=self._languages_supported,
            )
            self._current_language = language  # Allow it anyway

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Get the voice conversation history.

        Returns:
            List of conversation history entries.
        """
        return list(self._conversation_history)

    def clear_conversation_history(self) -> None:
        """Clear the voice conversation history."""
        self._conversation_history.clear()
