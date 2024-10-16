import queue
import logging
from typing import Callable, Tuple

class CommandProcessor:
    def __init__(self, root, logger: logging.Logger) -> None:
        """Initialize CommandProcessor with a command queue."""
        self.root = root
        self.logger = logger
        self.command_queue: queue.Queue[Tuple[Callable, Tuple]] = queue.Queue()
        self.processing = False
        self.logger.info("CommandProcessor initialized.")

    def enqueue_command(self, command: Callable, *args) -> None:
        """Add a command to the queue for later execution."""
        self.logger.debug(f"Enqueueing command '{command.__name__}' with arguments: {args}")
        self.command_queue.put((command, args))

    def process_queue(self) -> None:
        """Start processing commands in the queue."""
        self.processing = True
        self.logger.info("Command processing started.")
        self._process_commands()

    def _process_commands(self) -> None:
        """Process queued commands in a loop."""
        if self.processing:
            try:
                if not self.command_queue.empty():
                    command, args = self.command_queue.get()
                    self.logger.debug(f"Executing command '{command.__name__}' with arguments: {args}")
                    command(*args)
            except Exception as e:
                self.logger.error(f"Error processing command '{command.__name__}': {e}")
            finally:
                self.root.after(100, lambda: self._process_commands())

    def stop_processing(self) -> None:
        """Stop processing commands."""
        self.processing = False
        self.logger.info("Command processing stopped.")