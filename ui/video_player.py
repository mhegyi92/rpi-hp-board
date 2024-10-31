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
        self.timer_start_callback = None
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
        """Play the video from the specified folder and video number."""
        folder_path = os.path.join(self.video_base_path, folder_name)
        video_filename = f"video{video_number}.mp4"
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
        # self.player.audio_output_device_set(None, "alsa_output.platform-bcm2835_audio.stereo-fallback")
        self.player.audio_output_device_set(None, "hw:CARD=Headphones,DEV=0")

    def _start_playback(self) -> None:
        """Start video playback."""
        try:
            self.player.play()
            self.logger.debug("Video playback started.")
        except Exception as e:
            self.logger.error(f"Failed to play video: {e}")

    def _on_video_end(self, event: vlc.Event) -> None:
        """Handle video end event."""
        self.logger.debug("Video finished naturally, resetting media player.")
        self.stop_video()

    def stop_video(self) -> None:
        """Stop the video playback."""
        if self.player.is_playing():
            self.player.stop()

        # Clear canvas, reset the player, and recreate the canvas
        threading.Thread(target=self._reset_after_stop).start()

    def _reset_after_stop(self) -> None:
        """Reset player after stopping video playback."""
        self.logger.debug("Resetting media player after stop.")
        
        # Reset the player and recreate the canvas
        self._reset_player()
        self._recreate_canvas()

        # Clear the canvas after stopping
        self.canvas.after(100, self.clear_canvas)
        self.logger.debug("Video playback stopped and canvas reset.")

    def _reset_player(self) -> None:
        """Reset the player and reattach the canvas."""
        self.logger.debug("Resetting media player...")
        self.player.set_media(None)
        self.player.set_xwindow(0)  # Reset window ID to detach from canvas
        
        self._create_media_player()  # Recreate the media player after reset

    def _recreate_canvas(self) -> None:
        """Recreate the canvas to ensure fresh rendering for the next video."""
        self.logger.debug("Recreating the canvas...")

        # Destroy the old canvas
        self.canvas.destroy()

        # Create a new canvas, reattach it to the root window, and configure it
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

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
            return int(self.current_video_file.replace("video", "").replace(".mp4", ""))
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

    def set_timer_start_callback(self, callback: callable) -> None:
        """Set the callback to be triggered when the video ends."""
        self.timer_start_callback = callback

    def clear_canvas(self) -> None:
        """Clear the canvas after video playback."""
        self.canvas.delete("all")
        self.canvas.configure(bg="black")
        self.canvas.update_idletasks()
        self.canvas.update()
        self.logger.debug("Canvas cleared after video playback.")
