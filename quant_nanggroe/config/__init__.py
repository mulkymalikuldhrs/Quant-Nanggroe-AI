"""Configuration: settings, logging, and environment management.

WARNING: config/credentials.json is DEPRECATED. All secrets must come from .env.
The file is kept for reference but NEVER read by code at runtime.
"""
import logging
import os
from pathlib import Path

_logger = logging.getLogger(__name__)

_CRED_FILE = Path(__file__).resolve().parent / "credentials.json"
if _CRED_FILE.exists():
    _logger.warning(
        "config/credentials.json is DEPRECATED — secrets are loaded from .env via Pydantic Settings. "
        "Remove this file and use QNAI_* env vars instead."
    )

__all__ = [
    'logging_config',
    'settings',
]

from . import logging_config, settings
from .settings import Settings, get_settings
