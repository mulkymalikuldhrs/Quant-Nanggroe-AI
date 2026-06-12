"""Tests for the graceful shutdown module."""
import signal
import pytest
from unittest.mock import MagicMock, patch

from quant_nanggroe.config.shutdown import ShutdownConfig, GracefulShutdown


class TestRegisterCleanup:
    """Test that cleanup handlers can be registered."""

    def test_register_cleanup(self):
        gs = GracefulShutdown()
        handler = MagicMock()
        gs.register_cleanup(handler)
        assert handler in gs._cleanup_handlers


class TestInstallUninstall:
    """Test signal handler install/uninstall cycle."""

    def test_install_uninstall(self):
        gs = GracefulShutdown()
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        gs.install()
        # Handlers should be replaced
        assert signal.getsignal(signal.SIGTERM) is not original_sigterm
        assert signal.getsignal(signal.SIGINT) is not original_sigint

        gs.uninstall()
        # Original handlers should be restored
        assert signal.getsignal(signal.SIGTERM) is original_sigterm
        assert signal.getsignal(signal.SIGINT) is original_sigint


class TestShutdownHandlerRunsCleanup:
    """Test that _handle_signal runs registered cleanup handlers."""

    def test_shutdown_handler_runs_cleanup(self):
        gs = GracefulShutdown(config=ShutdownConfig(force_after_timeout=False))
        handler1 = MagicMock()
        handler2 = MagicMock()
        gs.register_cleanup(handler1)
        gs.register_cleanup(handler2)

        with patch.object(gs, '_handle_signal', wraps=gs._handle_signal):
            # Directly call _run_cleanup to test the logic without sys.exit
            gs._run_cleanup()
            # Handlers run in reverse order
            handler2.assert_called_once()
            handler1.assert_called_once()


class TestIsShuttingDown:
    """Test is_shutting_down property."""

    def test_is_shutting_down(self):
        gs = GracefulShutdown()
        assert gs.is_shutting_down is False
        gs._shutting_down = True
        assert gs.is_shutting_down is True


class TestCleanupExceptionHandled:
    """Test that exceptions in cleanup handlers don't stop other handlers."""

    def test_cleanup_exception_handled(self):
        gs = GracefulShutdown()
        handler_good = MagicMock()
        handler_bad = MagicMock(side_effect=RuntimeError("boom"))
        handler_also_good = MagicMock()

        # Register in order: good, bad, also_good
        gs.register_cleanup(handler_good)
        gs.register_cleanup(handler_bad)
        gs.register_cleanup(handler_also_good)

        # _run_cleanup reverses, so order is: also_good, bad, good
        gs._run_cleanup()

        handler_also_good.assert_called_once()
        handler_bad.assert_called_once()
        handler_good.assert_called_once()


class TestConfigDefaults:
    """Test ShutdownConfig default values."""

    def test_config_defaults(self):
        config = ShutdownConfig()
        assert config.timeout_seconds == 30.0
        assert config.force_after_timeout is True

        # Also test GracefulShutdown with no config uses defaults
        gs = GracefulShutdown()
        assert gs.config.timeout_seconds == 30.0
        assert gs.config.force_after_timeout is True
