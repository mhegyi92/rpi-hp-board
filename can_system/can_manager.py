import threading
import time
import logging
from .can_module import CANModule
from typing import Callable, Dict, List
from can import CanError

class CANManager:
    def __init__(self, can_module: CANModule, logger: logging.Logger, config: dict) -> None:
        """Initialize CANManager with a CAN module and logger."""
        self.can_module = can_module
        self.logger = logger

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
    
    def trigger_immediate_response(self) -> None:
        """Trigger an immediate response."""
        self.immediate_response_event.set()

    def start_can_listener(self, filters: List[dict], can_filter_to_handler: Dict[str, Callable]) -> None:
        """Start the CANListener thread to handle incoming CAN messages."""
        with self.lock:
            if self.can_listener_thread and self.can_listener_thread.is_alive():
                self.logger.debug("Stopping old CANListener thread before starting a new one.")
                self.stop_can_listener()

            self.logger.info("Starting CANListener thread.")
            self.can_listener_stop_event.clear()
            self.can_listener_thread = threading.Thread(target=self._can_message_handler, args=(filters, can_filter_to_handler), daemon=True, name="CANListener")
            self.can_listener_thread.start()

    def _can_message_handler(self, filters: List[dict], can_filter_to_handler: Dict[str, Callable]) -> None:
        """Continuously handle incoming CAN messages in the CANListener thread."""
        try:
            while not self.can_listener_stop_event.is_set():
                self.can_module.handle_can_message(filters, can_filter_to_handler)
                time.sleep(self.listener_poll_interval)
        except Exception as e:
            self.logger.error(f"CANListener thread crashed: {e}")

    def start_can_responder(self, get_video_status: Callable[[], tuple], get_correctness: Callable[[], int]) -> None:
        """Start the CANResponder thread to send periodic and immediate response messages."""
        self.can_responder_stop_event.clear()
        self.can_responder_thread = threading.Thread(
            target=self._send_periodic_responses, args=(get_video_status, get_correctness), daemon=True, name="CANResponder"
        )
        self.logger.info("Starting CANResponder thread.")
        self.can_responder_thread.start()

    def _send_periodic_responses(self, get_video_status: Callable[[], tuple], get_correctness: Callable[[], int]) -> None:
        """Send video playback and timer status responses periodically, restarting the interval for immediate responses."""
        next_send_time = time.time() + self.responder_initial_delay
        
        while not self.can_responder_stop_event.is_set():
            try:
                current_time = time.time()
                
                if self.immediate_response_event.is_set():
                    self.immediate_response_event.clear()
                    
                    playback_status, folder_selection, video_number = get_video_status()
                    correctness = get_correctness()
                    video_response_data = [0x03, folder_selection, video_number, correctness, 0x00, 0x00, 0x00, 0x00]
                    self.can_module.send_message(video_response_data)
                    # self.logger.debug(f"Sent immediate video playback status: {video_response_data}")
                                   
                    next_send_time = time.time() + self.responder_periodic_interval

                if current_time >= next_send_time:
                    playback_status, folder_selection, video_number = get_video_status()
                    correctness = get_correctness()
                    video_response_data = [0x03, folder_selection, video_number, correctness, 0x00, 0x00, 0x00, 0x00]
                    self.can_module.send_message(video_response_data)
                    # self.logger.debug(f"Sent periodic video playback status: {video_response_data}")
                             
                    next_send_time = time.time() + self.responder_periodic_interval

                time.sleep(self.responder_poll_interval)
            except Exception as e:
                self.logger.error(f"Error in CANResponder thread: {e}")

    def _send_can_message_with_retry(self, can_response_data: List[int], max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Attempt to send a CAN message with retries in case of failure."""
        attempt = 0
        while attempt < max_retries:
            try:
                # Send the CAN message using the CAN module
                self.can_module.send_message(can_response_data)
                self.logger.debug(f"Sent CAN message: {can_response_data}")
                return  # If successful, return early
            except CanError as e:
                self.logger.error(f"Failed to send CAN message (Attempt {attempt+1}/{max_retries}): {str(e)}")
                
                if "No buffer space available" in str(e):
                    self.logger.warning(f"CAN buffer full, retrying after {retry_delay} seconds.")
                    time.sleep(retry_delay)
                else:
                    # If it's another error, retry as well but with logging
                    time.sleep(retry_delay)
                
            attempt += 1
        
        # If all retries failed
        self.logger.error(f"Failed to send CAN message after {max_retries} attempts: {can_response_data}")

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
    
    def stop_can_responder(self) -> None:
        """Stop the CANResponder thread gracefully."""
        with self.lock:
            if self.can_responder_thread and self.can_responder_thread.is_alive():
                self.can_responder_stop_event.set()
            
                # Ensure we are not in the same thread
                if threading.current_thread() != self.can_listener_thread:
                    self.can_responder_thread.join(timeout=2)
                else:
                    self.logger.warning("Cannot join CANResponder thread from within itself. Skipping join.")
                self.logger.info("CANResponder thread stopped.")
