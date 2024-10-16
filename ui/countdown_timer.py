import tkinter as tk
import tkinter.font as tkFont
import logging
from typing import Optional

class CountdownTimer:
    def __init__(self, canvas: tk.Canvas, config: dict) -> None:
        """Initialize CountdownTimer with canvas and config."""
        self.canvas = canvas
        self.duration = config.get("duration", 60)
        self.font = tkFont.Font(family=config.get("font_path"), size=config.get("font_size"))
        self.font_color = config.get("font_color")
        self.bg_color = config.get("bg_color")
        self.time_left = self.duration
        self.timer_id = None
        self.text_id = None
        self.is_running = False
        self.is_paused = False
        self.is_hidden = False
        self.update_from_can = False
        self.logger = logging.getLogger(__name__)
        self.logger.info("CountdownTimer initialized.")

    def start(self) -> None:
        """Start the countdown."""
        if not self.is_running and not self.is_paused:
            self.logger.debug("Starting countdown.")
            self.canvas.config(bg=self.bg_color)
            self.is_running = True
            self._update_timer()

    def _update_timer(self) -> None:
        """Update the timer display and continue countdown."""
        if self.timer_id:
            self.canvas.after_cancel(self.timer_id)  # Cancel any previous callback

        if self.time_left > 0:
            if not self.is_paused and not self.update_from_can:
                self.time_left -= 1

            if not self.is_hidden:
                self._draw_timer()

            self.timer_id = self.canvas.after(1000, self._update_timer)
        else:
            self.logger.debug("Countdown finished.")
            self.stop()

    def _draw_timer(self) -> None:
        """Draw the current time on the canvas."""
        minutes, seconds = divmod(self.time_left, 60)
        time_str = f"{minutes:02}:{seconds:02}"

        if self.text_id:
            self.canvas.delete(self.text_id)

        self.text_id = self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            text=time_str,
            font=self.font,
            fill=self.font_color,
        )

    def update_time_from_can(self, total_seconds: int) -> None:
        """Update the displayed time based on data received from the CAN network."""
        self.logger.debug(f"Updating time from CAN network: {total_seconds} seconds.")
        self.time_left = total_seconds
        self.update_from_can = True  # Enable CAN update mode
        self._draw_timer()  # Immediately draw the updated time

    def stop_updating_from_can(self) -> None:
        """Stop updating the time from the CAN network and resume internal countdown."""
        self.update_from_can = False
        self.logger.debug("Stopped updating time from CAN network; resuming internal countdown.")


    def pause(self) -> None:
        """Pause the countdown."""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            if self.timer_id:
                self.canvas.after_cancel(self.timer_id)
                self.timer_id = None
            self.logger.debug("Countdown paused.")

    def resume(self) -> None:
        """Resume the countdown after being paused."""
        if self.is_paused:
            self.is_paused = False
            self.logger.debug("Countdown resumed.")
            self._update_timer()

    def stop(self) -> None:
        """Stop the countdown."""
        if self.timer_id:
            self.canvas.after_cancel(self.timer_id)
            self.timer_id = None
        self.is_running = False
        self.is_paused = False
        self.logger.debug("Countdown stopped.")

    def restart(self, new_duration: Optional[int] = None) -> None:
        """Restart the countdown with a specific or initial duration."""
        self.logger.debug(f"Restarting countdown with duration: {new_duration or self.duration} seconds.")
        self.stop()
        self.time_left = new_duration if new_duration else self.duration
        self.start()

    def hide_timer(self) -> None:
        """Hide the timer text without stopping the countdown."""
        if self.text_id:
            self.canvas.delete(self.text_id)
        self.is_hidden = True
        self.logger.debug("Countdown timer hidden.")

    def show_timer(self) -> None:
        """Show the timer text if hidden."""
        self.is_hidden = False
        if self.is_running and not self.is_paused:
            self._update_timer()
        else:
            self._draw_timer()
        self.logger.debug("Countdown timer shown.")

    def subtract_time(self, seconds: int) -> None:
        """Subtract time from the countdown and update the display if paused."""
        self.time_left -= seconds
        if self.time_left < 0:
            self.time_left = 0

        self.logger.debug(f"Subtracted {seconds} seconds. Time left: {self.time_left} seconds.")
        if self.is_paused or not self.is_running:
            self._draw_timer()

        if self.time_left == 0:
            self.stop()

    def add_time(self, seconds: int) -> None:
        """Add time to the countdown and update the display if paused."""
        self.time_left += seconds
        self.logger.debug(f"Added {seconds} seconds. Time left: {self.time_left} seconds.")
        if self.is_paused or not self.is_running:
            self._draw_timer()

        if self.time_left > 0 and not self.is_running and not self.is_paused:
            self.start()
