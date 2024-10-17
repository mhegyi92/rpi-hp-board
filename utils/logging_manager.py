import logging
from logging.handlers import RotatingFileHandler

class LoggingManager:
    def __init__(self, logging_config: dict) -> None:
        """Initialize the LoggingManager with the provided logging configuration."""
        self.logging_config = logging_config

    def setup_logging(self) -> None:
        """Set up logging configuration based on the provided config."""
        log_file = self.logging_config.get("file", "app.log")
        log_level = self.logging_config.get("level", "DEBUG").upper()
        log_format = self.logging_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Log rotation settings
        max_bytes = self.logging_config.get("max_bytes", 10 * 1024 * 1024)  # Default 10MB
        backup_count = self.logging_config.get("backup_count", 5)  # Default 5 backup files

        # Set up the rotating file handler
        rotating_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        rotating_handler.setLevel(getattr(logging, log_level, logging.DEBUG))
        rotating_handler.setFormatter(logging.Formatter(log_format))

        # Set up the stream handler for console output
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(getattr(logging, log_level, logging.DEBUG))
        stream_handler.setFormatter(logging.Formatter(log_format))

        # Apply handlers to the root logger
        logging.basicConfig(level=getattr(logging, log_level, logging.DEBUG), handlers=[rotating_handler, stream_handler])

        # Set the log level for third-party libraries
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('can.interfaces.socketcan.socketcan').setLevel(logging.INFO)  # Change to INFO or higher

        logging.getLogger('other_library').setLevel(logging.WARNING)

        logger = logging.getLogger(__name__)
        logger.debug("Logging configuration with log rotation completed.")
