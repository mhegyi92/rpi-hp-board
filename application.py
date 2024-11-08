import tkinter as tk
import logging
import os
import threading
import vlc
import time
from utils.configuration_manager import ConfigurationManager
from utils.logging_manager import LoggingManager
from utils.signal_handler import SignalHandler
from can_system.can_module import CANModule
from can_system.can_manager import CANManager
from can_system.command_processor import CommandProcessor

class Application:
    def __init__(self, root):
        # Initialize configuration, logging, and signal handling
        self.config_manager = ConfigurationManager('config.json')
        self._setup_logging()
        self._setup_signal_handler()

        self.root = root
        self.root.configure(bg='black')

        # Load video base path from config
        ui_config = self.config_manager.get_config_section("UI")
        self.video_base_path = ui_config["video"]["video_base_path"]

        # Default language
        self.language = 'hun'  # Default to Hungarian

        # Create a canvas for video rendering
        self.canvas = tk.Canvas(root, bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        # VLC media player instance
        self.instance = vlc.Instance("--aout=pulse")
        self.player = self.instance.media_player_new()

        # Initialize CAN components
        self.can_module = CANModule(self.config_manager.get_config_section("CAN"))
        self.can_manager = CANManager(self.can_module, self.config_manager.get_config_section("CAN_MANAGER"))
        self.command_processor = CommandProcessor(self.root)

        # Set fullscreen mode after 100 ms to ensure proper setup
        self.root.after(100, lambda: self.root.attributes('-fullscreen', True))

        # Handle key bindings for manual testing
        self.root.bind('<Key>', self.on_key_press)

        # Start processing commands
        self.command_processor.process_queue()

        # Start listening CAN messages
        self.can_manager.start_can_listener(
            self.config_manager.get_config_section("CAN")["software_filters"], 
            self._setup_can_message_handlers()
        )

        # Current video tracker
        self.current_video = None
        
        # Ensure shutdown on window close
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown_app) 

    def _setup_logging(self):
        """Setup the logging system based on configuration."""
        logging_manager = LoggingManager(self.config_manager.get_config_section("LOGGING"))
        logging_manager.setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Logging setup complete.")

    def _setup_signal_handler(self):
        """Setup signal handler for graceful shutdown."""
        self.signal_handler = SignalHandler(self)
        self.signal_handler.register_signal_handler()
        self.logger.debug("Signal handler setup complete.")

    def on_key_press(self, event):
        key = event.char.lower()
        video_path = self.get_video_path(key)
        if video_path:
            self.play_video(video_path)
        elif key == 'q':
            self.quit_app()

    def get_video_path(self, key):
        """Get the video path based on the key pressed and current language."""
        if key.isdigit():
            return os.path.join(self.video_base_path, self.language, f'video{key}.mkv')
        return None

    def play_video(self, video_path):
        if os.path.exists(video_path):
            # Stop any currently playing media
            if self.player.is_playing():
                self.player.stop()

            # Set the current video path
            self.current_video = video_path

            # Set the media to the player and play
            media = self.instance.media_new(video_path)
            self.player.set_media(media)
            self.player.audio_output_device_set(None, "hw:CARD=vc4hdmi0,DEV=0")

            # Embed video to the tkinter window
            self.player.set_xwindow(self.canvas.winfo_id())
            self.player.video_set_scale(0)
            self.player.video_set_aspect_ratio("16:9")
            
            self.player.play()
            self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self.on_video_end)

            self.logger.info(f"Playing video: {video_path}")

    def on_video_end(self, event):
        """Callback when video finishes playing."""
        self.logger.info("Video playback finished.")

        # Logic to play the next video after specific videos end
        next_video_map = {
            os.path.join(self.video_base_path, self.language, 'video2.mkv'): os.path.join(self.video_base_path, self.language, 'video3.mkv'),
            os.path.join(self.video_base_path, self.language, 'video4.mkv'): os.path.join(self.video_base_path, self.language, 'video5.mkv'),
            os.path.join(self.video_base_path, self.language, 'video6.mkv'): os.path.join(self.video_base_path, self.language, 'video7.mkv'),
            os.path.join(self.video_base_path, self.language, 'video7.mkv'): os.path.join(self.video_base_path, self.language, 'video8.mkv')
        }

        if self.current_video in next_video_map:
            next_video = next_video_map[self.current_video]
            self.logger.info(f"Scheduling next video: {next_video} in 3 seconds.")
            self.root.after(3000, lambda: self.play_video(next_video))

    def quit_app(self):
        """Quit the application."""
        if self.player.is_playing():
            self.player.stop()
        self.root.destroy()

    def can_message_handler(self, arbitration_id, data):
        """Handle incoming CAN messages."""
        try:
            # Set language based on byte 1 of CAN data
            if data[1] == 0x01:
                self.language = 'hun'
                self.logger.info("Language set to Hungarian.")
            elif data[1] == 0x02:
                self.language = 'eng'
                self.logger.info("Language set to English.")
            else:
                self.logger.warning(f"Unknown language code received: {data[1]}")

            # Play video based on byte 2 (assuming byte 2 is the video index)
            video_index = data[2]
            video_path = self.get_video_path(str(video_index))
            if video_path:
                self.logger.info(f"CAN message received to play video {video_index}.")
                self.logger.debug(f"Scheduling play_video() from thread: {threading.current_thread().name}")
                self.command_processor.enqueue_command(self.play_video, video_path)
            else:
                self.logger.warning(f"Invalid video index received: {video_index}")
        except Exception as e:
            self.logger.error(f"Error processing CAN message: {e}")

    def _setup_can_message_handlers(self):
        """Define CAN message handlers."""
        return {
            "control": lambda id, data: self.command_processor.enqueue_command(self.can_message_handler, id, data)
        }

    def shutdown_app(self):
        self.logger.info("Initiating application shutdown.")
        start_time = time.time()
        
        # Stop CAN listener and responder
        self.logger.info("Stopping CAN listener and responder.")
        self.can_manager.stop_can_listener()
        self.can_manager.stop_can_responder()
        self.logger.info(f"Stopped CAN threads in {time.time() - start_time:.2f} seconds.")
        
        # Shutdown CAN module
        self.logger.info("Shutting down CAN module.")
        self.can_module.shutdown()
        self.logger.info(f"CAN module shut down in {time.time() - start_time:.2f} seconds.")
        
        # Stop VLC player
        if self.player.is_playing():
            self.logger.info("Stopping VLC player.")
            self.player.stop()
            time.sleep(0.1)  # Ensure resources are released
        self.logger.info(f"VLC player stopped in {time.time() - start_time:.2f} seconds.")
        
        # Close the Tkinter window
        self.logger.info("Destroying Tkinter window.")
        self.root.destroy()
        self.logger.info(f"Application shutdown completed in {time.time() - start_time:.2f} seconds.")
