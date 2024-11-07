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
        self.current_image_name: Optional[str] = None  # Stores the name of the currently displayed image
        self.logger = logging.getLogger(__name__)
        self.logger.info("StandbyDisplay initialized.")

    def display_image(self, path: Optional[str] = None) -> None:
        """Display an image on the canvas. Uses path parameter if provided; otherwise, defaults to standby image."""
        self.canvas.config(bg=self.bg_color)
        image_path = path if path else self.image_path  # Use provided path or fallback to config image path

        try:
            image = Image.open(image_path)
            self.photo_image = ImageTk.PhotoImage(image)
            self._draw_image()
            self.current_image_name = image_path  # Update the currently displayed image name
            self.logger.info(f"Displayed image from path: {image_path}")
        except Exception as e:
            self.logger.error(f"Failed to load image '{image_path}': {e}")
            self.current_image_name = None  # Reset if loading fails

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
        self.canvas.config(bg=self.bg_color)
        if self.image_id:
            self.canvas.delete(self.image_id)  # Remove the image if it's displayed
            self.image_id = None
        self.current_image_name = None  # Reset the current image name since background is displayed
        self.logger.debug(f"Canvas set to background color '{self.bg_color}' without image.")

    def get_current_image_name(self) -> Optional[str]:
        """Return the path or name of the currently displayed image, if any."""
        return self.current_image_name

    def update_canvas(self, new_canvas: tk.Canvas) -> None:
        """Update the canvas reference to a new one."""
        self.canvas = new_canvas
        self.logger.debug("Canvas reference in StandbyDisplay updated.")