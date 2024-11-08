import queue
import logging
import threading
from typing import Callable, Tuple

class CommandProcessor:
    def __init__(self, root) -> None:
        """Initialize the CommandProcessor with a command queue and logger."""
        self.root = root
        self.logger = logging.getLogger(__name__)  # Initialize logger for the CommandProcessor module
        self.command_queue: queue.Queue[Tuple[Callable, Tuple]] = queue.Queue()
        self.processing = False
        self.lock = threading.Lock()
        self.worker_thread: threading.Thread = None

    def enqueue_command(self, command: Callable, *args) -> None:
        """Add a command to the queue for later execution."""
        self.logger.debug(f"Enqueueing command '{command.__name__}' with arguments: {args}")
        self.command_queue.put((command, args))

    def process_queue(self) -> None:
        """Start processing commands in the queue."""
        with self.lock:
            if not self.processing:
                self.processing = True
                self.worker_thread = threading.Thread(target=self._process_commands, daemon=True)
                self.worker_thread.start()
                self.logger.info("Started command processing.")

    def _process_commands(self) -> None:
        """Process commands from the queue in a loop."""
        while self.processing:
            try:
                command, args = self.command_queue.get(timeout=1)  # Timeout to allow periodic checking
                self.logger.debug(f"Scheduling command '{command.__name__}' with arguments: {args} to run in the main thread.")
                self.root.after(0, lambda cmd=command, cmd_args=args: self._execute_command(cmd, *cmd_args))
                self.command_queue.task_done()
            except queue.Empty:
                # No command to process; just continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing command '{command.__name__}': {e}")

    def _execute_command(self, command: Callable, *args) -> None:
        """Execute a command safely, catching any errors."""
        try:
            command(*args)
        except Exception as e:
            self.logger.error(f"Error executing command '{command.__name__}': {e}")

    def stop_processing(self) -> None:
        with self.lock:
            if self.processing:
                self.processing = False
                self.command_queue.join()  # Wait for the queue to be empty
                self.logger.info("Stopped command processing.")
