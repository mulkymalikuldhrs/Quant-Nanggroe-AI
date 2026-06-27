"""
Agentic AI System - Connectors Module
External service integrations and API gateways

Made with love by Mulky Malikul Dhaher in Indonesia
"""

from .llm_gateway import LLMGateway

# Optional connectors - require additional dependencies
# These are lightweight stubs that gracefully degrade when dependencies are missing

try:
    from .audio_stream import AudioStreamProcessor
except ImportError:
    class AudioStreamProcessor:
        """Audio stream processor - requires pyaudio and speech_recognition"""
        def __init__(self):
            raise ImportError(
                "AudioStreamProcessor requires additional dependencies. "
                "Install with: pip install pyaudio SpeechRecognition"
            )

try:
    from .google_integration import GoogleIntegration
except ImportError:
    class GoogleIntegration:
        """Google services integration - requires google-api-python-client"""
        def __init__(self):
            raise ImportError(
                "GoogleIntegration requires additional dependencies. "
                "Install with: pip install google-api-python-client google-auth-oauthlib"
            )

try:
    from .github_integration import GitHubIntegration
except ImportError:
    class GitHubIntegration:
        """GitHub API integration - uses aiohttp for async operations"""
        def __init__(self, token: str = None):
            self.token = token or None
            self.connected = False
        
        def is_available(self) -> bool:
            return self.token is not None

try:
    from .simulated import SimulatedBroker
except ImportError:
    class SimulatedBroker:
        """Simulated broker for paper trading"""
        def __init__(self):
            raise ImportError("SimulatedBroker unavailable")

try:
    from .web3_plugin import Web3Plugin
except ImportError:
    class Web3Plugin:
        """Web3 blockchain integration - requires web3.py"""
        def __init__(self):
            raise ImportError(
                "Web3Plugin requires additional dependencies. "
                "Install with: pip install web3"
            )

__all__ = [
    'LLMGateway',
    'AudioStreamProcessor',
    'GoogleIntegration',
    'GitHubIntegration',
    'Web3Plugin',
    'SimulatedBroker',
]
