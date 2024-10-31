import tkinter as tk
import logging
import threading
import sys
from typing import Callable
from utils.configuration_manager import ConfigurationManager
from utils.signal_handler import SignalHandler
from utils.logging_manager import LoggingManager
from ui.ui_manager import UIManager
from can_system.command_processor import CommandProcessor
from can_system.can_module import CANModule
from can_system.can_manager import CANManager
from ui.standby_display import StandbyDisplay
from ui.video_player import VideoPlayer
from ui.countdown_timer import CountdownTimer
from ui.hint_display import HintDisplay

class Application:
    def __init__(self) -> None:
        """Initialize the Application class, including thread locks for handling restart and shutdown."""
        self.restart_in_progress = False
        self.shutdown_in_progress = False
        self.lock = threading.Lock()  # Protects shutdown and restart states
        self.init_application()

    def init_application(self) -> None:
        """Initialize core application components including logging, UI, CAN, and signal handling."""
        self.config_manager = ConfigurationManager('config.json')
        self._setup_logging()
        self._setup_signal_handler()

        self.root = tk.Tk()
        self._setup_ui()

        self.ui_manager = UIManager(self.root, self.logger)
        self.command_processor = CommandProcessor(self.root, self.logger)

        can_module = CANModule(self.logger, self.config_manager.get_config_section("CAN"))
        self.can_manager = CANManager(can_module, self.logger, self.config_manager.get_config_section("CAN_MANAGER"))

        self._setup_displays()
        self.video_player.set_timer_start_callback(self.countdown_timer.start)

    def _setup_logging(self) -> None:
        """Setup the logging system based on configuration."""
        logging_manager = LoggingManager(self.config_manager.get_config_section("LOGGING"))
        logging_manager.setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Logging setup complete.")

    def _setup_signal_handler(self) -> None:
        """Setup signal handler for graceful shutdown."""
        self.signal_handler = SignalHandler(self, self.logger)
        self.signal_handler.register_signal_handler()
        self.logger.debug("Signal handler setup complete.")

    def _setup_ui(self) -> None:
        """Setup UI components such as root window and canvas."""
        ui_config = self.config_manager.get_config_section("UI")
        self.root.title(ui_config.get("title", "Delayed Full Screen Canvas"))
        self.root.config(cursor="none")
        self.canvas = tk.Canvas(self.root, bg=ui_config.get("bg_color"), highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind keys for keyboard controls
        self.root.bind("<q>", lambda event: self.shutdown_app())  # Q for quit
        self.root.bind("<r>", lambda event: self.restart_app())   # R for restart
        self.root.bind("<space>", lambda event: self.video_player.play_video("hun", 1))  # SPACE to start video
        self.root.bind("<Escape>", lambda event: self.video_player.stop_video())  # ESC to stop video

    def _setup_displays(self) -> None:
        """Setup display components for standby, video, timer, and hints."""
        ui_config = self.config_manager.get_config_section("UI")
        self.standby_display = StandbyDisplay(self.canvas, ui_config.get("standby", {}))
        self.video_player = VideoPlayer(self.root, self.canvas, ui_config.get("video", {}))
        self.countdown_timer = CountdownTimer(self.canvas, ui_config.get("timer", {}))
        self.hint_display = HintDisplay(self.canvas, ui_config.get("hint", {}), self.countdown_timer)

    def start(self) -> None:
        """Start the main application loop."""
        self.logger.info("Starting the application.")

        # Setup full-screen mode and display standby image
        self.root.after(100, self.ui_manager.set_fullscreen)
        self.root.after(500, self.standby_display.display_background)

        # Define CAN message filters and handlers
        can_filter_to_handler = self._setup_can_message_handlers()
        
        # Start CANListener and CANResponder threads
        can_filters = self.config_manager.get_config_section("CAN")["software_filters"]
        self.can_manager.start_can_listener(can_filters, can_filter_to_handler)
        self.can_manager.start_can_responder(self.video_player.get_video_status)

        self.command_processor.process_queue()

        # Start the tkinter main loop
        self.root.mainloop()
        self.logger.info("Application has stopped.")

    def handle_video_control(self, arbitration_id, data):
        playback_status = data[1]
        folder_selection = data[2]
        video_number = data[3]
        
        # Map folder selection to folder names
        folder_name = "hun" if folder_selection == 0x01 else "eng" if folder_selection == 0x02 else "Unknown"
        
        if playback_status == 0x00:
            self.video_player.stop_video()
            self.logger.debug("Received CAN message to stop video playback.")
        elif playback_status == 0x01 and folder_name is not None:
            self.logger.debug(f"Received CAN message to play video from folder '{folder_name}', video number '{video_number}'.")
            self.video_player.play_video(folder_name, video_number)
        
        self.can_manager.trigger_immediate_response()

    def handle_timer_control(self, arbitration_id, data):
        display_control = data[1]
        time_hi = data[2]
        time_lo = data[3]
        total_seconds = (time_hi << 8) | time_lo

        if display_control == 0x01:
            self.countdown_timer.show_timer()
            self.countdown_timer.update_time_from_can(total_seconds)  # Update time from CAN
        else:
            self.countdown_timer.hide_timer()

    def _setup_can_message_handlers(self) -> dict:
        """Define CAN message filters and handlers."""
        self.logger.debug("Setting up CAN message handlers.")
        return {
            "video_control": lambda id, data: self.command_processor.enqueue_command(self.handle_video_control, id, data),
            "timer_control": lambda id, data: self.command_processor.enqueue_command(self.handle_timer_control, id, data),
            "restart": lambda id, data: self.restart_app()
        }

    def restart_app(self) -> None:
        """Restart the application."""
        self.logger.info("Restarting the application.")
        self._perform_cleanup_and_action(self._restart_ui_cleanup)

    def shutdown_app(self) -> None:
        """Shutdown the application."""
        self.logger.info("Shutting down the application.")
        self._perform_cleanup_and_action(self._shutdown_ui_cleanup)

    def _perform_cleanup_and_action(self, cleanup_action: Callable[[], None]) -> None:
        """Perform cleanup actions before executing shutdown or restart."""
        with self.lock:
            if self.restart_in_progress or self.shutdown_in_progress:
                self.logger.debug("Action already in progress.")
                return
            self.restart_in_progress = cleanup_action == self._restart_ui_cleanup
            self.shutdown_in_progress = cleanup_action == self._shutdown_ui_cleanup

        threading.Thread(target=self._cleanup_and_execute_action, args=(cleanup_action,)).start()

    def _cleanup_and_execute_action(self, cleanup_action: Callable[[], None]) -> None:
        """Stop processes and perform cleanup actions."""
        try:
            self.logger.debug("Stopping application components.")
            self.command_processor.stop_processing()
            self.can_manager.stop_can_listener()
            self.can_manager.stop_can_responder()
            self.can_manager.can_module.shutdown()
            self.countdown_timer.stop()

            self.root.after(100, cleanup_action)
        except Exception as e:
            self.logger.error(f"Cleanup operation failed: {e}")
        finally:
            with self.lock:
                if cleanup_action == self._shutdown_ui_cleanup:
                    self.shutdown_in_progress = False
                    self.logger.info("Shutdown completed.")
                else:
                    self.restart_in_progress = False
                    self.logger.info("Restart completed.")

    def _restart_ui_cleanup(self) -> None:
        """Restart the application UI."""
        self.logger.debug("Restarting UI.")
        self._cleanup_ui()
        self.init_application()
        self.start()

    def _shutdown_ui_cleanup(self) -> None:
        """Shutdown the application UI."""
        self.logger.debug("Shutting down UI.")
        self._cleanup_ui()
        sys.exit(0)

    def _cleanup_ui(self) -> None:
        """Common UI cleanup logic."""
        self.logger.debug("Cleaning up UI.")
        self.root.quit()
        self.root.update()
        self.root.destroy()
