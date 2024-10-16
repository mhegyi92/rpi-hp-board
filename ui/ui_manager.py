import tkinter as tk
import logging

class UIManager:
    def __init__(self, root: tk.Tk, logger: logging.Logger) -> None:
        """Initialize UIManager with the root window and logger."""
        self.root = root
        self.logger = logger
        self.logger.info("UIManager initialized.")

    def set_fullscreen(self, event=None) -> None:
        """Enable fullscreen mode for the root window."""
        self.root.attributes("-fullscreen", True)
        self.logger.debug("Fullscreen mode activated.")
