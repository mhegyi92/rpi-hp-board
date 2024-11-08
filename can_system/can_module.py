import logging
import can
import time
import subprocess
from typing import List, Optional, Dict

class CANModule:
    def __init__(self, config: dict) -> None:
        """Initialize CANModule with the provided configuration."""
        self.config = config
        self.device_id = int(self.config["device_id"], 16)
        self.logger = logging.getLogger(__name__)
        self.bus = None
        self.hw_filters: Optional[List[Dict[str, int]]] = self.config.get("hardware_filters", None)
        self._initialize_can_module()

    def _initialize_can_module(self) -> None:
        """Initialize the CAN module, including setting up the interface and CAN bus."""
        self._check_and_setup_interface()
        self.bus = self._setup_can_interface()
        self._check_bus_status()

    def _check_and_setup_interface(self) -> None:
        """Check if the CAN interface is up, and bring it up if it is down."""
        try:
            command = f"ip link show {self.config['channel']} | grep 'state UP'"
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                # Check specific error details from `stderr`
                if "No such device" in result.stderr.decode():
                    self.logger.error(f"CAN interface '{self.config['channel']}' does not exist.")
                    raise RuntimeError(f"Interface '{self.config['channel']}' not found.")
                elif "Permission denied" in result.stderr.decode():
                    self.logger.error(f"Insufficient permissions to check CAN interface '{self.config['channel']}'.")
                    raise PermissionError("Permission denied while accessing the CAN interface status.")
                else:
                    self.logger.debug(f"CAN interface '{self.config['channel']}' is down, attempting to bring it up.")
                    self._bring_interface_up()
            else:
                self.logger.debug(f"CAN interface '{self.config['channel']}' is already up.")
        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to check or bring up CAN interface: {e}")
            raise

    def _check_bus_status(self) -> None:
        """Check if the CAN bus is experiencing transmission or reception errors and reset if necessary."""
        rx_errors_file = f"/sys/class/net/{self.config['channel']}/statistics/rx_errors"
        tx_errors_file = f"/sys/class/net/{self.config['channel']}/statistics/tx_errors"

        try:
            with open(rx_errors_file, "r") as rx_f, open(tx_errors_file, "r") as tx_f:
                rx_errors = int(rx_f.read().strip())
                tx_errors = int(tx_f.read().strip())

            if rx_errors > 0 or tx_errors > 0:
                self.logger.debug(f"CAN bus errors detected (rx_errors: {rx_errors}, tx_errors: {tx_errors}), resetting.")
                self._bring_interface_down()
                time.sleep(5)  # Cooldown period before bringing the interface back up
                self._bring_interface_up()
                time.sleep(5)  # Additional wait to allow interface to stabilize
            else:
                self.logger.debug("No CAN bus errors detected.")

        except FileNotFoundError as e:
            self.logger.error(f"Error file not found: {e}. This may indicate a misconfiguration or missing files for the interface '{self.config['channel']}'.")
        except PermissionError as e:
            self.logger.error(f"Permission denied when accessing error files for CAN interface '{self.config['channel']}': {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while checking or resetting CAN bus state: {e}")
            
    def _bring_interface_down(self) -> None:
        """Bring the CAN interface down."""
        try:
            command = f"sudo ip link set {self.config['channel']} down"
            subprocess.run(command, shell=True, check=True)
            self.logger.debug(f"CAN interface '{self.config['channel']}' brought down.")
        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to bring down CAN interface: {e}")

    def _bring_interface_up(self, retries=3) -> None:
        """Bring the CAN interface up with retries."""
        for attempt in range(retries):
            try:
                # Setting CAN bitrate and bringing it up
                command_bitrate = f"sudo ip link set {self.config['channel']} type can bitrate {self.config['bitrate']}"
                subprocess.run(command_bitrate, shell=True, check=True)

                command_up = f"sudo ip link set {self.config['channel']} up"
                subprocess.run(command_up, shell=True, check=True)

                self.logger.debug(f"CAN interface '{self.config['channel']}' brought up successfully.")
                return
            except subprocess.SubprocessError as e:
                self.logger.error(f"Attempt {attempt+1}/{retries}: Failed to bring up CAN interface: {e}")
                if attempt < retries - 1:
                    time.sleep(2)  # Wait before retrying
        raise RuntimeError(f"Failed to bring up CAN interface after {retries} attempts: {e}")

    def _setup_can_interface(self) -> can.Bus:
        """Set up the CAN interface with the provided configuration."""
        try:
            # Process hardware filters only once during setup if they are provided
            if self.hw_filters:
                for hw_filter in self.hw_filters:
                    hw_filter['can_id'] = int(hw_filter['can_id'], 16)
                    hw_filter['can_mask'] = int(hw_filter['can_mask'], 16)
                    
            bus = can.interface.Bus(
                channel=self.config['channel'],
                interface=self.config['interface'],
                bitrate=self.config['bitrate'],
                can_filters=self.hw_filters if self.hw_filters else None
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
            # Check if the arbitration ID falls within the specified range
            id_range = [int(x, 16) for x in filter["id_range"]]
            if not (id_range[0] <= message.arbitration_id <= id_range[1]):
                return False

            # Check payload conditions
            for index, expected_value in enumerate(filter["payload_conditions"]):
                if expected_value != "*" and expected_value is not None:
                    # Verify each condition matches the expected value in the payload
                    if message.data[index] != int(expected_value, 16):
                        return False

            # All conditions met, return True
            return True
        except ValueError as e:
            self.logger.error(f"Value error when processing filter conditions: {e}. Check payload_conditions format.")
            return False
        except IndexError as e:
            self.logger.error(f"Index error: payload length mismatch. Message data: {message.data}, filter: {filter}")
            return False

    def shutdown(self) -> None:
        """Shutdown the CAN interface."""
        try:
            if self.bus:
                self.logger.info("Shutting down CAN interface.")
                self.bus.shutdown()
                self.logger.info("CAN interface shut down successfully.")
            else:
                self.logger.warning("CAN bus is not active, skipping shutdown.")
        except Exception as e:
            self.logger.error(f"Error during CAN shutdown: {e}")

    def reinitialize_can(self) -> None:
        """Re-initialize CAN bus after shutdown."""
        self.logger.info("Re-initializing CAN interface.")
        try:
            self._initialize_can_module()  # Re-initialize the module
            self.logger.info("CAN interface re-initialized successfully.")
        except Exception as e:
            self.logger.error(f"Error reinitializing CAN interface: {e}")
            raise
