import pytest
from ai_multicolony.channels.telegram import TelegramBot
from ai_multicolony.channels.whatsapp import WhatsAppGateway
from ai_multicolony.channels.discord import DiscordBot
from ai_multicolony.channels.slack import SlackIntegration

class TestChannels:
    def test_telegram(self): assert TelegramBot(token="t") is not None
    def test_whatsapp(self): assert WhatsAppGateway() is not None
    def test_discord(self): assert DiscordBot(token="t") is not None
    def test_slack(self): assert SlackIntegration(token="t") is not None
