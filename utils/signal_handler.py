import signal
import logging

class SignalHandler:
    def __init__(self, application, logger: logging.Logger) -> None:
        """Initialize SignalHandler with the application instance and logger."""
        self.application = application
        self.logger = logger

    def register_signal_handler(self) -> None:
        """Register SIGINT signal handler for graceful shutdown."""
        signal.signal(signal.SIGINT, self.handle_sigint)
        self.logger.debug("Signal handler registered for SIGINT.")

    def handle_sigint(self, signum: int, frame) -> None:
        """Handle the SIGINT signal and trigger application shutdown."""
        self.logger.debug("SIGINT signal received. Initiating graceful shutdown.")
        self.application.shutdown_app()
