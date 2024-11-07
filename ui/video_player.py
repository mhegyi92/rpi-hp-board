import tkinter as tk
import vlc
import logging
import os
import threading
import time

class VideoPlayer:
    def __init__(self, root: tk.Tk, canvas: tk.Canvas, config: dict) -> None:
        """Initialize VideoPlayer with root window, canvas, and configuration."""
        self.root = root
        self.canvas = canvas
        self.video_base_path = config.get("video_base_path")
        self.instance = vlc.Instance("--aout=pulse")
        self._create_media_player()
        self.on_video_end_callback = None
        self.current_folder = None
        self.current_video_file = None

        self.logger = logging.getLogger(__name__)
        self.logger.info("VideoPlayer initialized.")

    def _create_media_player(self) -> None:
        """Create a new VLC media player instance."""
        self.player = self.instance.media_player_new()
        self.player_events = self.player.event_manager()
        self.player_events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_video_end)

    def play_video(self, folder_name: str, video_number: int) -> None:
        """Recreate the canvas and play the video from the specified folder and video number."""
        self.stop_video()
        self._recreate_canvas()

        folder_path = os.path.join(self.video_base_path, folder_name)
        video_filename = f"video{video_number}.mkv"
        video_path = os.path.join(folder_path, video_filename)

        if not os.path.isfile(video_path):
            self.logger.error(f"Video file '{video_path}' not found. Cannot play video.")
            return

        self.current_folder = folder_name
        self.current_video_file = video_filename
        self.logger.debug(f"Starting video playback from folder '{folder_name}', file '{video_filename}'")

        self._initialize_media(video_path)
        self._start_playback()
        # Polling loop to check if the video is playing
        start_time = time.time()
        timeout = 5  # Timeout after 5 seconds
        while time.time() - start_time < timeout:
            if self.player.is_playing():
                self.logger.debug("Video is now playing.")
                break
            time.sleep(0.1)  # Sleep for 100ms and check again

        if not self.player.is_playing():
            self.logger.error("Failed to start video playback within timeout period.")

    def _initialize_media(self, video_path: str) -> None:
        """Initialize the media player with the video."""
        media = self.instance.media_new(video_path)
        self.player.set_media(media)

        # Get the canvas window handle and attach it to the media player
        handle = self.canvas.winfo_id()
        self.logger.debug(f"Attaching canvas window handle to media player: {handle}")
        self.player.set_xwindow(handle)
        self.player.audio_output_device_set(None, "hw:CARD=Headphones,DEV=0")

    def _start_playback(self) -> None:
        """Start video playback."""
        try:
            self.player.play()
            self.logger.debug("Video playback started.")
        except Exception as e:
            self.logger.error(f"Failed to play video: {e}")

    def _on_video_end(self, event: vlc.Event) -> None:
        """Handle video end event and display an image immediately."""
        self.logger.debug("Video finished naturally, stopping playback.")
        self.stop_video()

        # Display an image immediately after stopping the video
        if self.on_video_end_callback:
            self.logger.debug("Calling the on_video_end_callback to display the image.")
            self.on_video_end_callback()

    def stop_video(self) -> None:
        """Stop the video playback and release resources."""
        if self.player.is_playing():
            self.logger.debug("Stopping video playback.")
            self.player.stop()
            self.player.release()  # Release and clean up the media player
        self._create_media_player()  # Reinitialize the media player

    def _recreate_canvas(self) -> None:
        """Recreate the canvas before playing each video."""
        self.logger.debug("Recreating the canvas...")

        # Destroy the old canvas
        self.canvas.destroy()

        # Create a new canvas, reattach it to the root window, and configure it
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Update StandbyDisplay's reference if necessary
        if hasattr(self.root, 'standby_display'):
            self.root.standby_display.update_canvas(self.canvas)
        
        # Update the application's canvas reference
        if hasattr(self.root, 'application'):
            self.root.application.update_canvas(self.canvas)

        # Force the canvas to refresh
        self.canvas.update_idletasks()
        self.logger.debug("New canvas created and packed.")

    def get_current_status(self) -> int:
        """Return the current playback status (0x00 for stopped, 0x01 for playing)."""
        return 0x01 if self.player.is_playing() else 0x00

    def get_current_folder_selection(self) -> int:
        """Return the folder selection (01 for Hungarian, 02 for English)."""
        if self.current_folder == "hun":
            return 0x01
        elif self.current_folder == "eng":
            return 0x02
        return 0x00

    def get_current_video_number(self) -> int:
        """Return the current video number being played."""
        if self.current_video_file:
            return int(self.current_video_file.replace("video", "").replace(".mkv", ""))
        return 0

    def get_video_status(self) -> tuple:
        """
        Get the current video playback status for CAN responses.
        
        Returns:
            tuple: (playback_status, folder_selection, video_number)
        """
        playback_status = self.get_current_status()
        folder_selection = self.get_current_folder_selection()
        video_number = self.get_current_video_number() if self.player.is_playing() else 0
        return playback_status, folder_selection, video_number

    def set_on_video_end_callback(self, callback: callable) -> None:
        """Set the callback to be triggered when the video ends."""
        self.on_video_end_callback = callback

