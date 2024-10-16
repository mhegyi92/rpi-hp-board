import tkinter as tk
import tkinter.font as tkFont
import logging
from typing import Optional, Dict

class HintDisplay:
    def __init__(self, canvas: tk.Canvas, config: dict, countdown_timer) -> None:
        """Initialize HintDisplay with canvas, config, and countdown_timer."""
        self.canvas = canvas
        self.countdown_timer = countdown_timer
        self.font = tkFont.Font(family=config.get("font_path"), size=config.get("font_size"))
        self.font_color = config.get("font_color")
        self.bg_color = config.get("bg_color")
        self.typing_speed = config.get("typing_speed", 50)
        self.default_display_duration = config.get("default_display_duration", 3000)
        self.use_typewriter_effect = config.get("typewriter_effect", True)
        self.hints: Dict[str, str] = config.get("hints", {})
        self.text_id: Optional[int] = None
        self.hide_id = None
        self.is_hint_visible = False
        self.current_display_text = ""
        self.char_index = 0
        self.logger = logging.getLogger(__name__)
        self.logger.info("HintDisplay initialized.")

    def show_hint_message(self, message: str, duration: Optional[int] = None) -> None:
        """Display the hint message, with an optional typewriter effect if enabled."""

        self.is_hint_visible = True
        self.typing_speed = self.typing_speed
        duration = duration if duration is not None else self.default_display_duration

        self._clear_existing_hint()

        # Hide the countdown timer while showing the hint
        self.countdown_timer.hide_timer()

        # Calculate the wrapped text
        self.wrapped_message = self._wrap_text(message)
        self.current_display_text = ""
        self.char_index = 0

        if self.use_typewriter_effect:
            # Display the text character by character (typewriter effect)
            self._type_character(duration)
        else:
            # Display the entire message instantly
            self._draw_full_text()
            # Schedule hide after duration
            self.hide_id = self.canvas.after(duration, self.hide_hint)

    def _type_character(self, duration: int) -> None:
        """Display one character at a time with a delay to create a typing effect."""
        if self.char_index < len(self.wrapped_message):
            next_char = self.wrapped_message[self.char_index]
            self.current_display_text += next_char

            self.canvas.delete("text")
            self._draw_current_text()

            self.char_index += 1
            # Schedule the next character display
            self.canvas.after(self.typing_speed, lambda: self._type_character(duration))
        else:
            # Once the text is fully displayed, schedule the hide action
            self.hide_id = self.canvas.after(duration, self.hide_hint)

    def _draw_full_text(self) -> None:
        """Instantly draw the full hint message on the canvas, centered vertically."""
        total_text_height = self._calculate_text_height(self.wrapped_message)
        canvas_height = self.canvas.winfo_height()

        y_offset = (canvas_height - total_text_height) // 2
        self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            y_offset,
            text=self.wrapped_message,
            font=self.font,
            fill=self.font_color,
            anchor=tk.N,
            tag="text"
        )

    def _draw_current_text(self) -> None:
        """Draw the current text that has been typed so far, centered vertically."""
        total_text_height = self._calculate_text_height(self.current_display_text)
        canvas_height = self.canvas.winfo_height()

        y_offset = (canvas_height - total_text_height) // 2
        self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            y_offset,
            text=self.current_display_text,
            font=self.font,
            fill=self.font_color,
            anchor=tk.N,
            tag="text"
        )

    def _wrap_text(self, text: str) -> str:
        """Wrap text dynamically based on canvas width and font size."""
        canvas_width = self.canvas.winfo_width()
        words = text.split()  # Split text into words
        wrapped_lines = []
        current_line = ""

        for word in words:
            # Measure current line plus new word
            test_line = current_line + (word if not current_line else f" {word}")
            line_width = self.font.measure(test_line)

            # Check if adding the word exceeds canvas width
            if line_width <= canvas_width:
                current_line = test_line
            else:
                # Save the current line and start a new one
                wrapped_lines.append(current_line)
                current_line = word

        # Add the last line to wrapped lines
        if current_line:
            wrapped_lines.append(current_line)

        # Join wrapped lines back with newline characters to facilitate the typing effect
        return "\n".join(wrapped_lines)

    def _calculate_text_height(self, text: str) -> int:
        """Calculate the total height of the text block based on the number of lines."""
        lines = text.split("\n")
        line_height = self.font.metrics("linespace")
        total_height = len(lines) * line_height
        return total_height

    def hide_hint(self) -> None:
        """Hide the hint and show the countdown timer again."""
        if not self.is_hint_visible:
            return
        
        self.is_hint_visible = False
        self._clear_existing_hint()
        self.logger.debug("Hint hidden.")
        self.countdown_timer.show_timer()

    def _clear_existing_hint(self) -> None:
        """Clear any existing hint from the canvas."""
        self.canvas.delete("all")
        if self.hide_id:
            self.canvas.after_cancel(self.hide_id)
            self.hide_id = None

    def toggle_typewriter_effect(self, enabled: bool) -> None:
        """Enable or disable the typewriter effect."""
        self.use_typewriter_effect = enabled
        self.logger.debug(f"Typewriter effect set to: {enabled}")
