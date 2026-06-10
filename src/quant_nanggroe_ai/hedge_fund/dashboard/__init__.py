"""Dashboard module for AI Hedge Fund v2.2

Features:
- Streamlit Web Dashboard
- Enhanced CLI Terminal
- Telegram Bot Integration
"""

from src.dashboard.streamlit_app import (
    get_dashboard_state,
    DashboardState,
    main as run_dashboard,
)

from src.dashboard.telegram_bot import (
    get_notification_manager,
    NotificationManager,
    TelegramConfig,
    TelegramBot,
    MockTelegramBot,
    SignalMessage,
)

from src.dashboard.cli_terminal import (
    CLITerminal,
)

__all__ = [
    "get_dashboard_state",
    "DashboardState",
    "run_dashboard",
    "get_notification_manager",
    "NotificationManager",
    "TelegramConfig",
    "TelegramBot",
    "MockTelegramBot",
    "SignalMessage",
    "CLITerminal",
]
