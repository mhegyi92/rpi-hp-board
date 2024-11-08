import signal
import os
import fcntl
import logging
import threading
from typing import Optional, Callable
import tkinter as tk
from can_system.command_processor import CommandProcessor

class SignalHandler:
    def __init__(self, application, command_processor: CommandProcessor, custom_shutdown_callback: Optional[Callable] = None) -> None:
        """Initialize SignalHandler with the application instance and optional custom shutdown logic."""
        self.application = application
        self.command_processor = command_processor
        self.logger = logging.getLogger(__name__)
        self.custom_shutdown_callback = custom_shutdown_callback

        # Create a pipe for handling signal wakeup
        self.read_fd, self.write_fd = os.pipe()

        # Set the write end of the pipe to non-blocking mode
        flags = fcntl.fcntl(self.write_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.write_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        signal.set_wakeup_fd(self.write_fd)

        # Register the file descriptor with Tkinter to read from it
        self.application.root.createfilehandler(self.read_fd, tk.READABLE, self._on_signal_received)

    def register_signal_handler(self) -> None:
        """Register signal handler for SIGINT and SIGTERM for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        self.logger.info("Signal handler registered for SIGINT and SIGTERM.")

    def _handle_signal(self, signum, frame):
        """Handle the signal and enqueue the shutdown command."""
        self.logger.info(f"Signal {signum} received. Enqueuing shutdown command.")
        self.command_processor.enqueue_command(self.application.shutdown_app)

    def _on_signal_received(self, fd, mask):
        """Callback when data is available on the signal pipe."""
        os.read(fd, 1)  # Clear the signal byte to prevent buffer overflow
        self.logger.debug("Signal processed by Tkinter event loop.")

    def unregister_signal_handler(self) -> None:
        """Unregister the signal handlers and restore default behavior."""
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        os.close(self.read_fd)
        os.close(self.write_fd)
        self.logger.info("Signal handlers unregistered and reset to default.")
