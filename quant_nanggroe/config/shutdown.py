"""Graceful shutdown handling for Quant-Nanggroe-AI."""
import signal
import sys
import structlog
from typing import Callable, Optional
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class ShutdownConfig(BaseModel):
    timeout_seconds: float = 30.0
    force_after_timeout: bool = True

class GracefulShutdown:
    """Handle graceful shutdown with cleanup on SIGTERM/SIGINT."""
    
    def __init__(self, config: Optional[ShutdownConfig] = None):
        self.config = config or ShutdownConfig()
        self._cleanup_handlers: list[Callable] = []
        self._shutting_down = False
        self._original_handlers = {}
    
    def register_cleanup(self, handler: Callable) -> None:
        """Register a cleanup function to run on shutdown."""
        self._cleanup_handlers.append(handler)
    
    def install(self) -> None:
        """Install signal handlers for graceful shutdown."""
        self._original_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, self._handle_signal)
        self._original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self._handle_signal)
        logger.info("graceful_shutdown_installed")
    
    def uninstall(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
        logger.info("graceful_shutdown_uninstalled")
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signal."""
        if self._shutting_down:
            logger.warning("shutdown_already_in_progress", signal=signum)
            return
        self._shutting_down = True
        sig_name = signal.Signals(signum).name
        logger.info("shutdown_signal_received", signal=sig_name)
        
        import threading
        timer = threading.Timer(self.config.timeout_seconds, self._force_exit)
        timer.daemon = True
        if self.config.force_after_timeout:
            timer.start()
        
        self._run_cleanup()
        timer.cancel()
        logger.info("shutdown_complete")
        sys.exit(0)
    
    def _run_cleanup(self):
        """Run all registered cleanup handlers."""
        for i, handler in enumerate(reversed(self._cleanup_handlers)):
            try:
                logger.info("running_cleanup", handler_index=i)
                handler()
            except Exception as e:
                logger.error("cleanup_handler_failed", handler_index=i, error=str(e))
    
    def _force_exit(self):
        """Force exit after timeout."""
        logger.warning("shutdown_timeout_exceeded", timeout=self.config.timeout_seconds)
        sys.exit(1)
    
    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down
