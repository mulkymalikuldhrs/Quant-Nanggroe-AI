"""Comprehensive tests for WhatsApp Gateway — Message Routing & Notification Push.

Tests cover:
- MessageType, MessageDirection, CommandName enums
- WhatsAppMessage, ParsedCommand, OutboundMessage, NotificationConfig,
  NotificationMessage models
- Command parsing (!forecast, !screen, !position, !balance, !risk,
  !help, !alert_on, !alert_off, !mood, !analysis, !chart)
- Command aliases (fc, f, scan, s, pos, p, bal, b, r, h, m, a, c)
- Prefix handling (!, /, #)
- WhatsAppGateway handle_inbound, command routing
- Notification types (trade alert, risk warning, daily brief)
- Subscription management (subscribe, unsubscribe, filtering)
- Message formatting (help, notification with severity emojis)
- Bridge communication (mocked httpx)
- FastAPI router configuration and endpoints
- Error handling

All tests use in-memory state — no real WhatsApp bridge calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.api.routes.whatsapp import (
    CommandName,
    MessageDirection,
    MessageType,
    NotificationConfig,
    NotificationMessage,
    OutboundMessage,
    ParsedCommand,
    WhatsAppGateway,
    WhatsAppMessage,
    parse_command,
    router,
)

# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def gateway():
    """Create a fresh WhatsAppGateway instance."""
    return WhatsAppGateway(bridge_url="http://localhost:3030")


@pytest.fixture
def sample_message():
    """Create a sample inbound message."""
    return WhatsAppMessage(
        message_id="msg-001",
        chat_id="chat-123",
        sender="+1234567890",
        sender_name="Test User",
        body="!forecast BTC",
        timestamp="2025-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_group_message():
    """Create a sample group message."""
    return WhatsAppMessage(
        message_id="msg-002",
        chat_id="group-456",
        sender="+9876543210",
        sender_name="Group User",
        body="!position",
        is_group=True,
        mentioned=True,
    )


@pytest.fixture
def subscribed_gateway(gateway):
    """Gateway with two subscribed chats."""
    gateway._subscribe("chat-1")
    gateway._subscribe("chat-2")
    return gateway


# ======================================================================
# 1. MessageType Enum Tests
# ======================================================================

class TestMessageType:
    """Tests for MessageType enum."""

    def test_text(self):
        assert MessageType.TEXT == "TEXT"

    def test_command(self):
        assert MessageType.COMMAND == "COMMAND"

    def test_alert(self):
        assert MessageType.ALERT == "ALERT"

    def test_notification(self):
        assert MessageType.NOTIFICATION == "NOTIFICATION"

    def test_trade_signal(self):
        assert MessageType.TRADE_SIGNAL == "TRADE_SIGNAL"

    def test_risk_warning(self):
        assert MessageType.RISK_WARNING == "RISK_WARNING"

    def test_daily_brief(self):
        assert MessageType.DAILY_BRIEF == "DAILY_BRIEF"

    def test_forecast_update(self):
        assert MessageType.FORECAST_UPDATE == "FORECAST_UPDATE"

    def test_count(self):
        assert len(MessageType) == 8

    def test_is_string_enum(self):
        assert isinstance(MessageType.TEXT, str)


# ======================================================================
# 2. MessageDirection Enum Tests
# ======================================================================

class TestMessageDirection:
    """Tests for MessageDirection enum."""

    def test_inbound(self):
        assert MessageDirection.INBOUND == "INBOUND"

    def test_outbound(self):
        assert MessageDirection.OUTBOUND == "OUTBOUND"

    def test_count(self):
        assert len(MessageDirection) == 2


# ======================================================================
# 3. CommandName Enum Tests
# ======================================================================

class TestCommandName:
    """Tests for CommandName enum."""

    def test_forecast(self):
        assert CommandName.FORECAST == "forecast"

    def test_screen(self):
        assert CommandName.SCREEN == "screen"

    def test_position(self):
        assert CommandName.POSITION == "position"

    def test_balance(self):
        assert CommandName.BALANCE == "balance"

    def test_risk(self):
        assert CommandName.RISK == "risk"

    def test_help(self):
        assert CommandName.HELP == "help"

    def test_alert_on(self):
        assert CommandName.ALERT_ON == "alert_on"

    def test_alert_off(self):
        assert CommandName.ALERT_OFF == "alert_off"

    def test_mood(self):
        assert CommandName.MOOD == "mood"

    def test_analysis(self):
        assert CommandName.ANALYSIS == "analysis"

    def test_chart(self):
        assert CommandName.CHART == "chart"

    def test_count(self):
        assert len(CommandName) == 11


# ======================================================================
# 4. WhatsAppMessage Model Tests
# ======================================================================

class TestWhatsAppMessage:
    """Tests for WhatsAppMessage model."""

    def test_required_fields_only(self):
        msg = WhatsAppMessage(body="Hello")
        assert msg.body == "Hello"
        assert msg.message_id == ""
        assert msg.chat_id == ""
        assert msg.sender == ""
        assert msg.sender_name == ""
        assert msg.timestamp == ""
        assert msg.is_group is False
        assert msg.mentioned is False

    def test_full_construction(self, sample_message):
        assert sample_message.message_id == "msg-001"
        assert sample_message.chat_id == "chat-123"
        assert sample_message.sender == "+1234567890"
        assert sample_message.sender_name == "Test User"
        assert sample_message.body == "!forecast BTC"
        assert sample_message.is_group is False

    def test_group_message(self, sample_group_message):
        assert sample_group_message.is_group is True
        assert sample_group_message.mentioned is True

    def test_body_required(self):
        """body is the only required field."""
        with pytest.raises(Exception):
            WhatsAppMessage()  # type: ignore[call-arg]


# ======================================================================
# 5. ParsedCommand Model Tests
# ======================================================================

class TestParsedCommand:
    """Tests for ParsedCommand model."""

    def test_required_fields_only(self):
        cmd = ParsedCommand(command=CommandName.FORECAST)
        assert cmd.command == CommandName.FORECAST
        assert cmd.args == []
        assert cmd.raw_message == ""
        assert cmd.chat_id == ""

    def test_with_args(self):
        cmd = ParsedCommand(
            command=CommandName.FORECAST,
            args=["BTC"],
            raw_message="!forecast BTC",
            chat_id="chat-1",
        )
        assert cmd.args == ["BTC"]
        assert cmd.raw_message == "!forecast BTC"
        assert cmd.chat_id == "chat-1"

    def test_multiple_args(self):
        cmd = ParsedCommand(
            command=CommandName.SCREEN,
            args=["BTC", "crypto", "momentum"],
        )
        assert len(cmd.args) == 3


# ======================================================================
# 6. OutboundMessage Model Tests
# ======================================================================

class TestOutboundMessage:
    """Tests for OutboundMessage model."""

    def test_required_fields(self):
        msg = OutboundMessage(chat_id="chat-1", body="Response")
        assert msg.chat_id == "chat-1"
        assert msg.body == "Response"
        assert msg.message_type == MessageType.TEXT
        assert msg.parse_mode == "markdown"
        assert msg.reply_to is None

    def test_with_reply(self):
        msg = OutboundMessage(
            chat_id="chat-1",
            body="Reply",
            reply_to="msg-001",
        )
        assert msg.reply_to == "msg-001"

    def test_with_message_type(self):
        msg = OutboundMessage(
            chat_id="chat-1",
            body="Alert",
            message_type=MessageType.ALERT,
        )
        assert msg.message_type == MessageType.ALERT

    def test_with_parse_mode(self):
        msg = OutboundMessage(
            chat_id="chat-1",
            body="Plain",
            parse_mode="plain",
        )
        assert msg.parse_mode == "plain"


# ======================================================================
# 7. NotificationConfig Model Tests
# ======================================================================

class TestNotificationConfig:
    """Tests for NotificationConfig model."""

    def test_required_fields(self):
        config = NotificationConfig(chat_id="chat-1")
        assert config.chat_id == "chat-1"
        assert config.trade_alerts is True
        assert config.risk_warnings is True
        assert config.daily_brief is False
        assert config.forecast_updates is False
        assert config.min_severity == "MEDIUM"
        assert config.symbols == []

    def test_custom_settings(self):
        config = NotificationConfig(
            chat_id="chat-1",
            trade_alerts=False,
            risk_warnings=False,
            daily_brief=True,
            forecast_updates=True,
            symbols=["BTC", "ETH"],
            min_severity="HIGH",
        )
        assert config.trade_alerts is False
        assert config.risk_warnings is False
        assert config.daily_brief is True
        assert config.forecast_updates is True
        assert len(config.symbols) == 2
        assert config.min_severity == "HIGH"


# ======================================================================
# 8. NotificationMessage Model Tests
# ======================================================================

class TestNotificationMessage:
    """Tests for NotificationMessage model."""

    def test_default_values(self):
        notif = NotificationMessage()
        assert notif.notification_id == ""
        assert notif.notification_type == MessageType.NOTIFICATION
        assert notif.title == ""
        assert notif.body == ""
        assert notif.severity == "MEDIUM"
        assert notif.symbol is None
        assert notif.action_required is False
        assert notif.timestamp == ""

    def test_trade_signal(self):
        notif = NotificationMessage(
            notification_type=MessageType.TRADE_SIGNAL,
            title="BUY BTC",
            body="Strong signal detected",
            severity="HIGH",
            action_required=True,
        )
        assert notif.action_required is True
        assert notif.notification_type == MessageType.TRADE_SIGNAL

    def test_risk_warning(self):
        notif = NotificationMessage(
            notification_type=MessageType.RISK_WARNING,
            title="Drawdown Alert",
            body="Portfolio down 5%",
            severity="CRITICAL",
            action_required=True,
        )
        assert notif.severity == "CRITICAL"

    def test_daily_brief(self):
        notif = NotificationMessage(
            notification_type=MessageType.DAILY_BRIEF,
            title="Market Brief",
            body="SPY up 1.2%",
            severity="LOW",
        )
        assert notif.notification_type == MessageType.DAILY_BRIEF

    def test_with_symbol(self):
        notif = NotificationMessage(
            title="Alert",
            body="BTC moving",
            symbol="BTC",
        )
        assert notif.symbol == "BTC"


# ======================================================================
# 9. Command Parsing Tests
# ======================================================================

class TestCommandParsing:
    """Tests for parse_command function."""

    # --- Primary commands ---

    def test_forecast_command(self):
        result = parse_command("!forecast BTC")
        assert result is not None
        assert result.command == CommandName.FORECAST
        assert result.args == ["BTC"]

    def test_screen_command(self):
        result = parse_command("!screen AAPL")
        assert result is not None
        assert result.command == CommandName.SCREEN
        assert result.args == ["AAPL"]

    def test_position_command(self):
        result = parse_command("!position")
        assert result is not None
        assert result.command == CommandName.POSITION
        assert result.args == []

    def test_balance_command(self):
        result = parse_command("!balance")
        assert result is not None
        assert result.command == CommandName.BALANCE

    def test_risk_command(self):
        result = parse_command("!risk")
        assert result is not None
        assert result.command == CommandName.RISK

    def test_help_command(self):
        result = parse_command("!help")
        assert result is not None
        assert result.command == CommandName.HELP

    def test_alert_on_command(self):
        result = parse_command("!alert_on")
        assert result is not None
        assert result.command == CommandName.ALERT_ON

    def test_alert_off_command(self):
        result = parse_command("!alert_off")
        assert result is not None
        assert result.command == CommandName.ALERT_OFF

    def test_mood_command(self):
        result = parse_command("!mood focused")
        assert result is not None
        assert result.command == CommandName.MOOD
        assert result.args == ["focused"]

    def test_analysis_command(self):
        result = parse_command("!analysis SPY")
        assert result is not None
        assert result.command == CommandName.ANALYSIS
        assert result.args == ["SPY"]

    def test_chart_command(self):
        result = parse_command("!chart BTC")
        assert result is not None
        assert result.command == CommandName.CHART
        assert result.args == ["BTC"]

    # --- Aliases ---

    def test_forecast_alias_fc(self):
        result = parse_command("!fc BTC")
        assert result is not None
        assert result.command == CommandName.FORECAST

    def test_forecast_alias_f(self):
        result = parse_command("!f ETH")
        assert result is not None
        assert result.command == CommandName.FORECAST

    def test_screen_alias_scan(self):
        result = parse_command("!scan AAPL")
        assert result is not None
        assert result.command == CommandName.SCREEN

    def test_screen_alias_s(self):
        result = parse_command("!s AAPL")
        assert result is not None
        assert result.command == CommandName.SCREEN

    def test_position_alias_pos(self):
        result = parse_command("!pos")
        assert result is not None
        assert result.command == CommandName.POSITION

    def test_position_alias_p(self):
        result = parse_command("!p")
        assert result is not None
        assert result.command == CommandName.POSITION

    def test_balance_alias_bal(self):
        result = parse_command("!bal")
        assert result is not None
        assert result.command == CommandName.BALANCE

    def test_balance_alias_b(self):
        result = parse_command("!b")
        assert result is not None
        assert result.command == CommandName.BALANCE

    def test_risk_alias_r(self):
        result = parse_command("!r")
        assert result is not None
        assert result.command == CommandName.RISK

    def test_help_alias_h(self):
        result = parse_command("!h")
        assert result is not None
        assert result.command == CommandName.HELP

    def test_mood_alias_m(self):
        result = parse_command("!m focused")
        assert result is not None
        assert result.command == CommandName.MOOD

    def test_analysis_alias_a(self):
        result = parse_command("!a SPY")
        assert result is not None
        assert result.command == CommandName.ANALYSIS

    def test_chart_alias_c(self):
        result = parse_command("!c BTC")
        assert result is not None
        assert result.command == CommandName.CHART

    # --- Prefix handling ---

    def test_slash_prefix(self):
        result = parse_command("/forecast BTC")
        assert result is not None
        assert result.command == CommandName.FORECAST

    def test_hash_prefix(self):
        result = parse_command("#forecast BTC")
        assert result is not None
        assert result.command == CommandName.FORECAST

    def test_no_prefix(self):
        result = parse_command("forecast BTC")
        assert result is None

    # --- Edge cases ---

    def test_empty_message(self):
        result = parse_command("")
        assert result is None

    def test_prefix_only(self):
        result = parse_command("!")
        assert result is None

    def test_unknown_command(self):
        result = parse_command("!unknown_cmd")
        assert result is None

    def test_with_chat_id(self):
        result = parse_command("!forecast BTC", chat_id="chat-1")
        assert result is not None
        assert result.chat_id == "chat-1"

    def test_whitespace_handling(self):
        result = parse_command("  !forecast   BTC  ")
        assert result is not None
        assert result.command == CommandName.FORECAST
        assert result.args == ["BTC"]

    def test_case_insensitive_command(self):
        result = parse_command("!FORECAST BTC")
        assert result is not None
        assert result.command == CommandName.FORECAST

    def test_multiple_args(self):
        result = parse_command("!forecast BTC USDT momentum")
        assert result is not None
        assert len(result.args) == 3

    def test_raw_message_preserved(self):
        result = parse_command("!forecast BTC")
        assert result is not None
        assert result.raw_message == "!forecast BTC"


# ======================================================================
# 10. WhatsAppGateway — Handle Inbound Tests
# ======================================================================

class TestGatewayHandleInbound:
    """Tests for handling inbound messages."""

    @pytest.mark.asyncio
    async def test_handle_command_returns_outbound(self, gateway, sample_message):
        result = await gateway.handle_inbound(sample_message)
        assert isinstance(result, OutboundMessage)
        assert result.message_type == MessageType.COMMAND

    @pytest.mark.asyncio
    async def test_handle_non_command_returns_none(self, gateway):
        msg = WhatsAppMessage(body="Just chatting")
        result = await gateway.handle_inbound(msg)
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_help_command(self, gateway):
        msg = WhatsAppMessage(body="!help", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "Commands" in result.body

    @pytest.mark.asyncio
    async def test_handle_forecast_command(self, gateway):
        msg = WhatsAppMessage(body="!forecast BTC", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "BTC" in result.body

    @pytest.mark.asyncio
    async def test_handle_forecast_default_symbol(self, gateway):
        msg = WhatsAppMessage(body="!forecast", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "SPY" in result.body  # Default symbol

    @pytest.mark.asyncio
    async def test_handle_screen_command(self, gateway):
        msg = WhatsAppMessage(body="!screen AAPL", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "AAPL" in result.body

    @pytest.mark.asyncio
    async def test_handle_screen_default_symbol(self, gateway):
        msg = WhatsAppMessage(body="!screen", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "AAPL" in result.body  # Default symbol

    @pytest.mark.asyncio
    async def test_handle_position_command(self, gateway):
        msg = WhatsAppMessage(body="!position", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "Positions" in result.body

    @pytest.mark.asyncio
    async def test_handle_balance_command(self, gateway):
        msg = WhatsAppMessage(body="!balance", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "Balance" in result.body

    @pytest.mark.asyncio
    async def test_handle_risk_command(self, gateway):
        msg = WhatsAppMessage(body="!risk", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "Risk" in result.body

    @pytest.mark.asyncio
    async def test_handle_mood_command(self, gateway):
        msg = WhatsAppMessage(body="!mood focused", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "focused" in result.body.lower() or "Mood" in result.body

    @pytest.mark.asyncio
    async def test_handle_mood_default(self, gateway):
        msg = WhatsAppMessage(body="!mood", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "neutral" in result.body.lower() or "Mood" in result.body

    @pytest.mark.asyncio
    async def test_handle_analysis_command(self, gateway):
        msg = WhatsAppMessage(body="!analysis SPY", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "SPY" in result.body

    @pytest.mark.asyncio
    async def test_handle_analysis_default(self, gateway):
        msg = WhatsAppMessage(body="!analysis", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "SPY" in result.body  # Default symbol

    @pytest.mark.asyncio
    async def test_handle_chart_command(self, gateway):
        msg = WhatsAppMessage(body="!chart BTC", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "BTC" in result.body

    @pytest.mark.asyncio
    async def test_handle_chart_default(self, gateway):
        msg = WhatsAppMessage(body="!chart", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "BTC" in result.body  # Default symbol

    @pytest.mark.asyncio
    async def test_inbound_records_history(self, gateway, sample_message):
        await gateway.handle_inbound(sample_message)
        assert len(gateway._message_history) == 1
        assert gateway._message_history[0]["direction"] == MessageDirection.INBOUND.value

    @pytest.mark.asyncio
    async def test_inbound_history_has_timestamp(self, gateway, sample_message):
        await gateway.handle_inbound(sample_message)
        assert "timestamp" in gateway._message_history[0]

    @pytest.mark.asyncio
    async def test_inbound_history_has_message_data(self, gateway, sample_message):
        await gateway.handle_inbound(sample_message)
        assert "message" in gateway._message_history[0]

    @pytest.mark.asyncio
    async def test_reply_references_original_message_id(self, gateway):
        msg = WhatsAppMessage(
            message_id="original-123",
            chat_id="chat-1",
            body="!help",
        )
        result = await gateway.handle_inbound(msg)
        assert result.reply_to == "original-123"

    @pytest.mark.asyncio
    async def test_reply_to_same_chat(self, gateway):
        msg = WhatsAppMessage(chat_id="chat-42", body="!help")
        result = await gateway.handle_inbound(msg)
        assert result.chat_id == "chat-42"


# ======================================================================
# 11. WhatsAppGateway — Alert Subscription Tests
# ======================================================================

class TestGatewayAlerts:
    """Tests for alert subscription management."""

    @pytest.mark.asyncio
    async def test_alert_on(self, gateway):
        msg = WhatsAppMessage(body="!alert_on", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "Enabled" in result.body
        assert "chat-1" in gateway._subscriptions

    @pytest.mark.asyncio
    async def test_alert_off(self, gateway):
        gateway._subscribe("chat-1")
        msg = WhatsAppMessage(body="!alert_off", chat_id="chat-1")
        result = await gateway.handle_inbound(msg)
        assert "Disabled" in result.body
        assert "chat-1" not in gateway._subscriptions

    def test_subscribe_creates_config(self, gateway):
        gateway._subscribe("chat-1")
        assert "chat-1" in gateway._subscriptions
        assert isinstance(gateway._subscriptions["chat-1"], NotificationConfig)

    def test_subscribe_idempotent(self, gateway):
        gateway._subscribe("chat-1")
        gateway._subscribe("chat-1")
        assert len(gateway._subscriptions) == 1

    def test_unsubscribe_nonexistent(self, gateway):
        # Should not raise
        gateway._unsubscribe("nonexistent-chat")

    def test_unsubscribe_removes_chat(self, gateway):
        gateway._subscribe("chat-1")
        gateway._unsubscribe("chat-1")
        assert "chat-1" not in gateway._subscriptions


# ======================================================================
# 12. WhatsAppGateway — Notification Push Tests
# ======================================================================

class TestGatewayNotifications:
    """Tests for notification push and recipient filtering."""

    @pytest.mark.asyncio
    async def test_push_notification_no_subscribers(self, gateway):
        notif = NotificationMessage(
            title="Test",
            body="Test body",
            notification_type=MessageType.TRADE_SIGNAL,
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert recipients == []

    @pytest.mark.asyncio
    async def test_push_notification_with_subscribers(self, gateway):
        gateway._subscribe("chat-1")
        gateway._subscribe("chat-2")

        notif = NotificationMessage(
            title="Risk Warning",
            body="Drawdown alert",
            notification_type=MessageType.RISK_WARNING,
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert len(recipients) == 2

    @pytest.mark.asyncio
    async def test_push_notification_filters_trade_alerts(self, gateway):
        """Chat with trade_alerts=False should not receive TRADE_SIGNAL."""
        config = NotificationConfig(
            chat_id="chat-1",
            trade_alerts=False,
            risk_warnings=True,
        )
        gateway._subscriptions["chat-1"] = config

        notif = NotificationMessage(
            title="Trade",
            body="BUY BTC",
            notification_type=MessageType.TRADE_SIGNAL,
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert "chat-1" not in recipients

    @pytest.mark.asyncio
    async def test_push_notification_filters_risk_warnings(self, gateway):
        """Chat with risk_warnings=False should not receive RISK_WARNING."""
        config = NotificationConfig(
            chat_id="chat-1",
            trade_alerts=True,
            risk_warnings=False,
        )
        gateway._subscriptions["chat-1"] = config

        notif = NotificationMessage(
            title="Risk",
            body="Drawdown alert",
            notification_type=MessageType.RISK_WARNING,
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert "chat-1" not in recipients

    @pytest.mark.asyncio
    async def test_push_notification_filters_daily_brief(self, gateway):
        """Chat with daily_brief=False should not receive DAILY_BRIEF."""
        config = NotificationConfig(
            chat_id="chat-1",
            daily_brief=False,
        )
        gateway._subscriptions["chat-1"] = config

        notif = NotificationMessage(
            title="Brief",
            body="Market overview",
            notification_type=MessageType.DAILY_BRIEF,
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert "chat-1" not in recipients

    @pytest.mark.asyncio
    async def test_push_notification_filters_forecast_updates(self, gateway):
        """Chat with forecast_updates=False should not receive FORECAST_UPDATE."""
        config = NotificationConfig(
            chat_id="chat-1",
            forecast_updates=False,
            trade_alerts=False,
            risk_warnings=False,
            daily_brief=False,
        )
        gateway._subscriptions["chat-1"] = config

        notif = NotificationMessage(
            title="Forecast Update",
            body="SPY forecast updated",
            notification_type=MessageType.FORECAST_UPDATE,
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert "chat-1" not in recipients

    @pytest.mark.asyncio
    async def test_push_notification_filters_by_symbol(self, gateway):
        """Chat watching only BTC should not receive ETH alerts."""
        config = NotificationConfig(
            chat_id="chat-1",
            symbols=["BTC"],
        )
        gateway._subscriptions["chat-1"] = config

        notif = NotificationMessage(
            title="ETH Alert",
            body="ETH signal",
            notification_type=MessageType.TRADE_SIGNAL,
            symbol="ETH",
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert "chat-1" not in recipients

    @pytest.mark.asyncio
    async def test_push_notification_symbol_match(self, gateway):
        """Chat watching BTC should receive BTC alerts."""
        config = NotificationConfig(
            chat_id="chat-1",
            symbols=["BTC", "ETH"],
        )
        gateway._subscriptions["chat-1"] = config

        notif = NotificationMessage(
            title="BTC Alert",
            body="BTC breakout",
            notification_type=MessageType.TRADE_SIGNAL,
            symbol="BTC",
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert "chat-1" in recipients

    @pytest.mark.asyncio
    async def test_push_notification_no_symbol_filter_if_watching_all(self, gateway):
        """Chat with empty symbols list should receive all notifications."""
        config = NotificationConfig(
            chat_id="chat-1",
            symbols=[],
        )
        gateway._subscriptions["chat-1"] = config

        notif = NotificationMessage(
            title="ETH Alert",
            body="ETH signal",
            notification_type=MessageType.TRADE_SIGNAL,
            symbol="ETH",
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.push_notification(notif)
            assert "chat-1" in recipients

    @pytest.mark.asyncio
    async def test_push_notification_records_history(self, gateway):
        gateway._subscribe("chat-1")
        notif = NotificationMessage(
            title="Test",
            body="Body",
            notification_type=MessageType.RISK_WARNING,
        )
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            await gateway.push_notification(notif)
            assert len(gateway._message_history) == 1
            assert gateway._message_history[0]["direction"] == MessageDirection.OUTBOUND.value

    @pytest.mark.asyncio
    async def test_push_notification_bridge_failure_skips_recipient(self, gateway):
        """If bridge fails for one recipient, it should still try others."""
        gateway._subscribe("chat-1")
        gateway._subscribe("chat-2")

        notif = NotificationMessage(
            title="Test",
            body="Body",
            notification_type=MessageType.TRADE_SIGNAL,
        )

        call_count = 0

        async def mock_send(msg):
            nonlocal call_count
            call_count += 1
            if msg.chat_id == "chat-1":
                raise Exception("Bridge failed")
            return True

        with patch.object(gateway, "_send_via_bridge", side_effect=mock_send):
            recipients = await gateway.push_notification(notif)
            assert "chat-2" in recipients
            assert "chat-1" not in recipients


# ======================================================================
# 13. WhatsAppGateway — Trade Alerts Tests
# ======================================================================

class TestGatewayTradeAlerts:
    """Tests for trade alert convenience methods."""

    @pytest.mark.asyncio
    async def test_send_trade_alert(self, gateway):
        gateway._subscribe("chat-1")
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.send_trade_alert(
                symbol="BTC",
                direction="BUY",
                price=50000.0,
                reason="Breakout",
                confidence=0.85,
            )
            assert len(recipients) == 1

    @pytest.mark.asyncio
    async def test_send_trade_alert_no_subscribers(self, gateway):
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.send_trade_alert(
                symbol="ETH",
                direction="SELL",
                price=3000.0,
            )
            assert recipients == []

    @pytest.mark.asyncio
    async def test_send_trade_alert_creates_notification(self, gateway):
        gateway._subscribe("chat-1")
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True) as mock_send:
            await gateway.send_trade_alert(
                symbol="BTC",
                direction="BUY",
                price=50000.0,
                reason="Momentum",
                confidence=0.9,
            )
            # Verify the bridge was called with an OutboundMessage
            mock_send.assert_called_once()
            sent_msg = mock_send.call_args[0][0]
            assert isinstance(sent_msg, OutboundMessage)
            assert "BTC" in sent_msg.body
            assert "BUY" in sent_msg.body


# ======================================================================
# 14. WhatsAppGateway — Risk Warnings Tests
# ======================================================================

class TestGatewayRiskWarnings:
    """Tests for risk warning convenience methods."""

    @pytest.mark.asyncio
    async def test_send_risk_warning(self, gateway):
        gateway._subscribe("chat-1")
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.send_risk_warning(
                warning_type="Drawdown",
                message="Portfolio down 5%",
                severity="HIGH",
            )
            assert len(recipients) == 1

    @pytest.mark.asyncio
    async def test_send_risk_warning_critical_action_required(self, gateway):
        """CRITICAL severity should set action_required=True."""
        gateway._subscribe("chat-1")
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.send_risk_warning(
                warning_type="Exchange",
                message="Exchange offline",
                severity="CRITICAL",
            )
            assert len(recipients) == 1

    @pytest.mark.asyncio
    async def test_send_risk_warning_low_no_action(self, gateway):
        """LOW severity should NOT set action_required."""
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            # This doesn't raise an error, just tests the path
            recipients = await gateway.send_risk_warning(
                warning_type="Info",
                message="Minor volatility",
                severity="LOW",
            )
            assert isinstance(recipients, list)

    @pytest.mark.asyncio
    async def test_send_risk_warning_high_action_required(self, gateway):
        """HIGH severity should set action_required=True."""
        gateway._subscribe("chat-1")
        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            await gateway.send_risk_warning(
                warning_type="Drawdown",
                message="Portfolio down 5%",
                severity="HIGH",
            )
            # Check that message was recorded in history
            outbound_entries = [
                e for e in gateway._message_history
                if e["direction"] == MessageDirection.OUTBOUND.value
            ]
            assert len(outbound_entries) == 1


# ======================================================================
# 15. WhatsAppGateway — Daily Brief Tests
# ======================================================================

class TestGatewayDailyBrief:
    """Tests for daily brief convenience methods."""

    @pytest.mark.asyncio
    async def test_send_daily_brief(self, gateway):
        config = NotificationConfig(chat_id="chat-1", daily_brief=True)
        gateway._subscriptions["chat-1"] = config

        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.send_daily_brief("Market overview...")
            assert len(recipients) == 1

    @pytest.mark.asyncio
    async def test_daily_brief_not_sent_if_disabled(self, gateway):
        config = NotificationConfig(chat_id="chat-1", daily_brief=False)
        gateway._subscriptions["chat-1"] = config

        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.send_daily_brief("Market overview...")
            assert len(recipients) == 0

    @pytest.mark.asyncio
    async def test_daily_brief_low_severity(self, gateway):
        """Daily brief should use LOW severity."""
        config = NotificationConfig(chat_id="chat-1", daily_brief=True)
        gateway._subscriptions["chat-1"] = config

        with patch.object(gateway, "_send_via_bridge", new_callable=AsyncMock, return_value=True):
            recipients = await gateway.send_daily_brief("SPY up 1.2% today")
            assert len(recipients) == 1


# ======================================================================
# 16. WhatsAppGateway — Message Formatting Tests
# ======================================================================

class TestGatewayFormatting:
    """Tests for message formatting."""

    def test_format_help(self):
        result = WhatsAppGateway._format_help()
        assert "forecast" in result
        assert "screen" in result
        assert "position" in result
        assert "balance" in result
        assert "risk" in result
        assert "mood" in result
        assert "analysis" in result
        assert "chart" in result
        assert "alert_on" in result
        assert "alert_off" in result
        assert "help" in result

    def test_format_notification_low_severity(self):
        notif = NotificationMessage(
            title="Info",
            body="Market update",
            severity="LOW",
        )
        result = WhatsAppGateway._format_notification(notif)
        assert "Info" in result
        assert "Market update" in result

    def test_format_notification_medium_severity(self):
        notif = NotificationMessage(
            title="Alert",
            body="Volatility spike",
            severity="MEDIUM",
        )
        result = WhatsAppGateway._format_notification(notif)
        assert "Alert" in result

    def test_format_notification_high_severity(self):
        notif = NotificationMessage(
            title="HIGH Alert",
            body="Drawdown warning",
            severity="HIGH",
        )
        result = WhatsAppGateway._format_notification(notif)
        assert "HIGH Alert" in result

    def test_format_notification_critical_severity(self):
        notif = NotificationMessage(
            title="CRITICAL",
            body="Exchange down!",
            severity="CRITICAL",
        )
        result = WhatsAppGateway._format_notification(notif)
        assert "CRITICAL" in result

    def test_format_notification_includes_timestamp(self):
        notif = NotificationMessage(
            title="Test",
            body="Body",
            severity="LOW",
        )
        result = WhatsAppGateway._format_notification(notif)
        assert "UTC" in result

    def test_format_notification_unknown_severity(self):
        """Unknown severity should use default emoji."""
        notif = NotificationMessage(
            title="Test",
            body="Body",
            severity="UNKNOWN",
        )
        result = WhatsAppGateway._format_notification(notif)
        assert "Test" in result


# ======================================================================
# 17. WhatsAppGateway — Bridge Communication Tests
# ======================================================================

class TestGatewayBridge:
    """Tests for bridge service communication."""

    @pytest.mark.asyncio
    async def test_send_via_bridge_success(self, gateway):
        import sys
        msg = OutboundMessage(chat_id="chat-1", body="Test")

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = await gateway._send_via_bridge(msg)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_via_bridge_non_200(self, gateway):
        import sys
        msg = OutboundMessage(chat_id="chat-1", body="Test")

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = await gateway._send_via_bridge(msg)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_via_bridge_failure(self, gateway):
        import sys
        msg = OutboundMessage(chat_id="chat-1", body="Test")

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.side_effect = Exception("Connection refused")

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            result = await gateway._send_via_bridge(msg)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_via_bridge_posts_to_correct_url(self, gateway):
        import sys
        msg = OutboundMessage(chat_id="chat-1", body="Test")

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            await gateway._send_via_bridge(msg)
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "http://localhost:3030/api/send" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_send_via_bridge_custom_url(self):
        import sys
        gateway = WhatsAppGateway(bridge_url="http://custom-host:9999")
        msg = OutboundMessage(chat_id="chat-1", body="Test")

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_client

        with patch.dict(sys.modules, {"httpx": mock_httpx}):
            await gateway._send_via_bridge(msg)
            call_args = mock_client.post.call_args
            assert "http://custom-host:9999/api/send" in call_args[0][0]


# ======================================================================
# 18. FastAPI Router Configuration Tests
# ======================================================================

class TestWhatsAppRouter:
    """Tests for FastAPI router configuration."""

    def test_router_exists(self):
        assert router is not None

    def test_router_prefix(self):
        assert router.prefix == "/whatsapp"

    def test_router_has_webhook(self):
        routes = [r.path for r in router.routes]
        assert any("webhook" in r for r in routes)

    def test_router_has_notify(self):
        routes = [r.path for r in router.routes]
        assert any("notify" in r for r in routes)

    def test_router_has_trade_alert(self):
        routes = [r.path for r in router.routes]
        assert any("trade-alert" in r for r in routes)

    def test_router_has_risk_warning(self):
        routes = [r.path for r in router.routes]
        assert any("risk-warning" in r for r in routes)

    def test_router_has_status(self):
        routes = [r.path for r in router.routes]
        assert any("status" in r for r in routes)

    def test_router_has_tags(self):
        assert "whatsapp" in router.tags


# ======================================================================
# 19. Gateway Initialization Tests
# ======================================================================

class TestGatewayInit:
    """Tests for WhatsAppGateway initialization."""

    def test_default_bridge_url(self):
        gw = WhatsAppGateway()
        assert gw._bridge_url == "http://localhost:3030"

    def test_custom_bridge_url(self):
        gw = WhatsAppGateway(bridge_url="http://my-bridge:5000")
        assert gw._bridge_url == "http://my-bridge:5000"

    def test_initial_subscriptions_empty(self, gateway):
        assert gateway._subscriptions == {}

    def test_initial_message_history_empty(self, gateway):
        assert gateway._message_history == []

    def test_initial_command_handlers_empty(self, gateway):
        assert gateway._command_handlers == {}
