import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

class LoggingManager:
    def __init__(self, config: dict) -> None:
        """Initialize the LoggingManager with the provided logging configuration."""
        self.config = config

    def setup_logging(self) -> None:
        """Set up the root logger with rotating file and stream handlers."""
        try:
            log_file = self.config.get("file", "app.log")
            log_level = self._get_log_level(self.config.get("level", "DEBUG"))
            log_format = self.config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

            # Log rotation settings
            max_bytes = self.config.get("max_bytes", 10 * 1024 * 1024)  # Default 10MB
            backup_count = self.config.get("backup_count", 5)  # Default 5 backup files

            # Ensure no duplicate handlers
            root_logger = logging.getLogger()
            if not any(isinstance(handler, RotatingFileHandler) for handler in root_logger.handlers):
                rotating_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
                rotating_handler.setLevel(log_level)
                rotating_handler.setFormatter(logging.Formatter(log_format))
                root_logger.addHandler(rotating_handler)

            if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
                stream_handler = logging.StreamHandler()
                stream_handler.setLevel(log_level)
                stream_handler.setFormatter(logging.Formatter(log_format))
                root_logger.addHandler(stream_handler)

            # Set the root logger level
            root_logger.setLevel(log_level)

            # Set log levels for external libraries if specified
            external_log_levels = self.config.get("external_log_levels", {})
            for library, level in external_log_levels.items():
                logging.getLogger(library).setLevel(self._get_log_level(level))

            root_logger.debug("Logging configuration completed successfully.")

        except Exception as e:
            logging.error(f"Error setting up logging: {e}")

    def _get_log_level(self, level: str) -> int:
        """Convert a log level string to a logging level constant, with a default fallback."""
        try:
            return getattr(logging, level.upper())
        except AttributeError:
            logging.warning(f"Invalid log level '{level}', defaulting to 'DEBUG'.")
            return logging.DEBUG
