"""
Integrations Package — External Service Connectors
====================================================
Integration modules for connecting Quant-Nanggroe-AI with
external services and messaging platforms.

Integrations:
    WhatsAppBot  — WhatsApp bot for trade notifications and commands
"""

from quant_nanggroe_ai.integrations.whatsapp_bot import WhatsAppBot

__all__ = [
    "WhatsAppBot",
]
