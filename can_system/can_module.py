import os
import logging
import can
from typing import List, Optional, Dict

class CANModule:
    def __init__(self, logger: logging.Logger, config: dict) -> None:
        """Initialize CANModule with the provided configuration."""
        self.config = config
        self.device_id = int(self.config["device_id"], 16)
        self.logger = logger
        self.logger.info("Initializing CANModule.")
        self.hw_filters: Optional[List[Dict[str, int]]] = self.config.get("hardware_filters", None)
        self._initialize_can_module()

    def _initialize_can_module(self) -> None:
        """Initialize the CAN module, including setting up the interface and CAN bus."""
        self._check_and_setup_interface()
        self.bus = self._setup_can_interface()

    def _check_and_setup_interface(self) -> None:
        """Check if the CAN interface is up, and bring it up if it is down."""
        try:
            interface_status = os.system(f"ip link show {self.config['channel']} | grep 'state UP'")
            if interface_status != 0:
                self.logger.debug(f"CAN interface '{self.config['channel']}' is down, attempting to bring it up.")
                self._bring_interface_up()
            else:
                self.logger.debug(f"CAN interface '{self.config['channel']}' is already up.")
        except Exception as e:
            self.logger.error(f"Failed to check or bring up CAN interface: {e}")
            raise

    def _bring_interface_up(self) -> None:
        """Bring the CAN interface up."""
        try:
            os.system(f"sudo ip link set {self.config['channel']} type can bitrate {self.config['bitrate']}")
            os.system(f"sudo ip link set {self.config['channel']} up")
            self.logger.debug(f"CAN interface '{self.config['channel']}' brought up successfully.")
        except Exception as e:
            self.logger.error(f"Failed to bring up CAN interface: {e}")
            raise

    def _setup_can_interface(self) -> can.Bus:
        """Set up the CAN interface with the provided configuration."""
        try:
            if self.hw_filters:
                for hw_filter in self.hw_filters:
                    hw_filter['can_id'] = int(hw_filter['can_id'], 16)
                    hw_filter['can_mask'] = int(hw_filter['can_mask'], 16)
                    
            bus = can.interface.Bus(
                channel=self.config['channel'],
                interface=self.config['interface'],
                bitrate=self.config['bitrate'],
                can_filters=self.hw_filters
            )
            self.logger.info(f"CAN interface '{self.config['channel']}' initialized.")
            return bus
        except Exception as e:
            self.logger.error(f"Failed to initialize CAN interface: {e}")
            raise

    def send_message(self, data: List[int]) -> None:
        """Send a CAN message."""
        try:
            message = can.Message(arbitration_id=self.device_id, data=data, is_extended_id=False)
            self.bus.send(message)
            self.logger.debug(f"Sent CAN message with ID '{hex(self.device_id)}' and data '{data}'.")
        except can.CanError as e:
            self.logger.error(f"Failed to send CAN message: {e}")
            raise

    def handle_can_message(self, filters: List[dict], can_filter_to_handler: dict) -> None:
        """Receive and handle a CAN message based on the configured filters."""
        try:
            message = self.bus.recv(timeout=1.0)
            if message:
                self._process_message(message, filters, can_filter_to_handler)
        except can.CanError as e:
            self.logger.error(f"CAN bus error: {e}")

    def _process_message(self, message: can.Message, filters: List[dict], can_filter_to_handler: dict) -> None:
        """Process a received CAN message by finding the appropriate handler."""
        handler_name = self._match_filter_to_handler(message, filters)
        if handler_name:
            handler = can_filter_to_handler.get(handler_name)
            if handler:
                handler(message.arbitration_id, message.data)

    def _match_filter_to_handler(self, message: can.Message, filters: List[dict]) -> Optional[str]:
        """Find a matching filter for the received message."""
        for filter in filters:
            if self._is_message_matching_filter(message, filter):
                return filter['name']
        return None

    def _is_message_matching_filter(self, message: can.Message, filter: dict) -> bool:
        """Check if a message matches the given filter conditions."""
        try:
            if not self.hw_filters or len(self.hw_filters) > 1:
                id_range = [int(x, 16) for x in filter["id_range"]]
                if not (id_range[0] <= message.arbitration_id <= id_range[1]):
                    return False

            for index, expected_value in enumerate(filter["payload_conditions"]):
                if expected_value != "*" and expected_value is not None:
                    if message.data[index] != int(expected_value, 16):
                        return False

            return True
        except (ValueError, IndexError) as e:
            self.logger.error(f"Error checking payload condition: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the CAN interface."""
        try:
            self.bus.shutdown()
            self.logger.info("CAN interface shut down successfully.")
        except Exception as e:
            self.logger.error(f"Error during CAN shutdown: {e}")
