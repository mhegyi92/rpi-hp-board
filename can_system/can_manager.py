import threading
import time
import logging
from .can_module import CANModule
from typing import Callable, Dict, List
from can import CanError

class CANManager:
    def __init__(self, can_module: CANModule, config: dict) -> None:
        """Initialize CANManager with a CAN module and configuration."""
        self.can_module = can_module
        self.logger = logging.getLogger(__name__)

        self.listener_poll_interval = config.get("listener_thread_poll_interval", 0.1)
        self.responder_poll_interval = config.get("responder_thread_poll_interval", 0.1)
        self.responder_initial_delay = config.get("responder_initial_delay", 2)
        self.responder_periodic_interval = config.get("responder_periodic_interval", 2)

        self.can_listener_thread: threading.Thread = None
        self.can_responder_thread: threading.Thread = None
        
        self.immediate_response_event = threading.Event()
        self.can_listener_stop_event = threading.Event()
        self.can_responder_stop_event = threading.Event()

        self.lock = threading.Lock()

        self.logger.debug("CANManager initialized.")

    def start_can_listener(self, filters: List[dict], can_filter_to_handler: Dict[str, Callable]) -> None:
        """Start the CANListener thread to handle incoming CAN messages."""
        with self.lock:
            # Ensure the old listener thread is stopped if running
            if self.can_listener_thread and self.can_listener_thread.is_alive():
                self.logger.debug("Stopping old CANListener thread before starting a new one.")
                self.stop_can_listener()

            # Start a new listener thread
            self.logger.info("Starting CANListener thread.")
            self.can_listener_stop_event.clear()
            self.can_listener_thread = threading.Thread(
                target=self._can_message_handler,
                args=(filters, can_filter_to_handler),
                daemon=True,
                name="CANListener"
            )
            self.can_listener_thread.start()

    def stop_can_listener(self) -> None:
        """Stop the CANListener thread gracefully."""
        with self.lock:
            if self.can_listener_thread and self.can_listener_thread.is_alive():
                self.can_listener_stop_event.set()

                # Ensure we are not in the same thread
                if threading.current_thread() != self.can_listener_thread:
                    self.can_listener_thread.join(timeout=2)
                else:
                    self.logger.warning("Cannot join CANListener thread from within itself. Skipping join.")

                self.logger.info("CANListener thread stopped.")
                self.can_listener_thread = None  # Reset the thread reference

    def start_can_responder(self, get_video_status: Callable[[], tuple], get_correctness: Callable[[], int]) -> None:
        """Start the CANResponder thread to send periodic and immediate response messages."""
        with self.lock:
            # Ensure the old responder thread is stopped if running
            if self.can_responder_thread and self.can_responder_thread.is_alive():
                self.logger.debug("Stopping old CANResponder thread before starting a new one.")
                self.stop_can_responder()

            # Start a new responder thread
            self.logger.info("Starting CANResponder thread.")
            self.can_responder_stop_event.clear()
            self.can_responder_thread = threading.Thread(
                target=self._send_periodic_responses,
                args=(get_video_status, get_correctness),
                daemon=True,
                name="CANResponder"
            )
            self.can_responder_thread.start()

    def stop_can_responder(self) -> None:
        """Stop the CANResponder thread gracefully."""
        with self.lock:
            if self.can_responder_thread and self.can_responder_thread.is_alive():
                self.can_responder_stop_event.set()
            
                # Ensure we are not in the same thread
                if threading.current_thread() != self.can_responder_thread:
                    self.can_responder_thread.join(timeout=2)
                else:
                    self.logger.warning("Cannot join CANResponder thread from within itself. Skipping join.")
                
                self.logger.info("CANResponder thread stopped.")
                self.can_responder_thread = None  # Reset the thread reference

    def trigger_immediate_response(self) -> None:
        """Trigger an immediate response."""
        self.immediate_response_event.set()
        self.logger.debug("Immediate response triggered.")

    def _can_message_handler(self, filters: List[dict], can_filter_to_handler: Dict[str, Callable]) -> None:
        """Continuously handle incoming CAN messages in the CANListener thread with error handling and retries."""
        retry_count = 0
        max_retries = 5
        try:
            while not self.can_listener_stop_event.is_set():
                try:
                    self.can_module.handle_can_message(filters, can_filter_to_handler)
                    retry_count = 0  # Reset retry count on success
                except Exception as e:
                    retry_count += 1
                    self.logger.error(f"CANListener encountered an error: {e} (retry {retry_count}/{max_retries})")
                    if retry_count >= max_retries:
                        self.logger.critical("CANListener thread stopping due to repeated errors.")
                        break  # Exit loop if too many consecutive errors
                time.sleep(self.listener_poll_interval)
        except Exception as e:
            self.logger.critical(f"CANListener thread crashed with unhandled exception: {e}")

    def _send_periodic_responses(self, get_video_status: Callable[[], tuple], get_correctness: Callable[[], int]) -> None:
        """Send video playback and timer status responses periodically with error handling and retries."""
        next_send_time = time.time() + self.responder_initial_delay
        retry_count = 0
        max_retries = 5

        try:
            while not self.can_responder_stop_event.is_set():
                try:
                    current_time = time.time()
                    
                    if self.immediate_response_event.is_set():
                        self.immediate_response_event.clear()
                        playback_status, folder_selection, video_number = get_video_status()
                        correctness = get_correctness()
                        video_response_data = [0x03, folder_selection, video_number, correctness, 0x00, 0x00, 0x00, 0x00]
                        self.can_module.send_message(video_response_data)
                        retry_count = 0  # Reset retry count on success

                        next_send_time = time.time() + self.responder_periodic_interval

                    if current_time >= next_send_time:
                        playback_status, folder_selection, video_number = get_video_status()
                        correctness = get_correctness()
                        video_response_data = [0x03, folder_selection, video_number, correctness, 0x00, 0x00, 0x00, 0x00]
                        self.can_module.send_message(video_response_data)
                        retry_count = 0  # Reset retry count on success

                        next_send_time = time.time() + self.responder_periodic_interval

                except Exception as e:
                    retry_count += 1
                    self.logger.error(f"CANResponder encountered an error: {e} (retry {retry_count}/{max_retries})")
                    if retry_count >= max_retries:
                        self.logger.critical("CANResponder thread stopping due to repeated errors.")
                        break  # Exit loop if too many consecutive errors

                time.sleep(self.responder_poll_interval)
        except Exception as e:
            self.logger.critical(f"CANResponder thread crashed with unhandled exception: {e}")

    def _send_can_message_with_retry(self, can_response_data: List[int], max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Attempt to send a CAN message with retries in case of failure."""
        attempt = 0
        while attempt < max_retries:
            try:
                # Attempt to send the CAN message using the CAN module
                self.can_module.send_message(can_response_data)
                if attempt > 0:
                    self.logger.info(f"CAN message successfully sent after {attempt} retries: {can_response_data}")
                else:
                    self.logger.debug(f"CAN message sent on first attempt: {can_response_data}")
                return  # Exit early if successful
            except CanError as e:
                # Log the first failure and the final attempt if retries are needed
                if attempt == 0:
                    self.logger.warning(f"Initial attempt to send CAN message failed: {e}")
                elif attempt == max_retries - 1:
                    self.logger.error(f"Failed to send CAN message after {max_retries} attempts: {can_response_data} - {e}")
                
                # Increment attempt and wait before retrying
                attempt += 1
                time.sleep(retry_delay)
        
        # Log consolidated failure if all retries failed
        self.logger.critical(f"Unable to send CAN message after {max_retries} attempts due to persistent issues: {can_response_data}")
