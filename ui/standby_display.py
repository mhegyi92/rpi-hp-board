from PIL import Image, ImageTk
import tkinter as tk
import logging
from typing import Optional

class StandbyDisplay:
    def __init__(self, canvas: tk.Canvas, config: dict) -> None:
        """Initialize StandbyDisplay with canvas and configuration."""
        self.canvas = canvas
        self.image_path = config.get("image_path")
        self.bg_color = config.get("bg_color")
        self.image_id: Optional[int] = None
        self.logger = logging.getLogger(__name__)
        self.logger.info("StandbyDisplay initialized.")

    def display_image(self) -> None:
        """Display the standby image on the canvas."""
        self.canvas.config(bg=self.bg_color)
        try:
            image = Image.open(self.image_path)
            self.photo_image = ImageTk.PhotoImage(image)
            self._draw_image()
        except Exception as e:
            self.logger.error(f"Failed to load image '{self.image_path}': {e}")

    def _draw_image(self) -> None:
        """Draw the image on the canvas."""
        x = self.canvas.winfo_width() // 2
        y = self.canvas.winfo_height() // 2
        if self.image_id:
            self.canvas.delete(self.image_id)

        self.image_id = self.canvas.create_image(x, y, anchor=tk.CENTER, image=self.photo_image)
        self.logger.debug(f"Image displayed at ({x}, {y}).")

    def display_background(self) -> None:
        """Display only the background color on the canvas without an image."""
        # Set the canvas background to the specified bg_color (default: black)
        self.canvas.config(bg=self.bg_color)
        if self.image_id:
            self.canvas.delete(self.image_id)  # Remove the image if it's displayed
            self.image_id = None
        self.logger.debug(f"Canvas set to background color '{self.bg_color}' without image.")
