import signal
import logging
import threading
from typing import Optional, Callable

class SignalHandler:
    def __init__(self, application, custom_shutdown_callback: Optional[Callable] = None) -> None:
        """Initialize SignalHandler with the application instance and optional custom shutdown logic."""
        self.application = application
        self.logger = logging.getLogger(__name__)
        self.custom_shutdown_callback = custom_shutdown_callback
        self._lock = threading.Lock()

    def register_signal_handler(self) -> None:
        """Register signal handler for SIGINT and SIGTERM for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        self.logger.info("Signal handler registered for SIGINT and SIGTERM.")

    def handle_signal(self, signum, frame):
        """Handle received signals for graceful shutdown."""
        with self._lock:
            if signum == signal.SIGINT:
                self.logger.info("SIGINT received. Initiating graceful shutdown.")
            elif signum == signal.SIGTERM:
                self.logger.info("SIGTERM received. Initiating graceful shutdown.")

            if self.custom_shutdown_callback:
                self.logger.debug("Executing custom shutdown callback.")
                try:
                    self.custom_shutdown_callback()
                except Exception as e:
                    self.logger.error(f"Error executing custom shutdown callback: {e}")
            
            # Always ensure application shutdown logic is called
            self.application.shutdown_app()

    def unregister_signal_handler(self) -> None:
        """Unregister the signal handlers and restore default behavior."""
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self.logger.info("Signal handlers unregistered and reset to default.")
