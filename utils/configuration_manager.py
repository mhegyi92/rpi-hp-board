import json
import os
import logging

class ConfigurationManager:
    REQUIRED_SECTIONS = ["LOGGING", "UI", "CAN"]

    def __init__(self, config_path: str) -> None:
        """Initialize ConfigurationManager with config file path."""
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.config_data = self._load_and_validate_config()

    def _load_and_validate_config(self) -> dict:
        """Load and validate the configuration file."""
        if not os.path.exists(self.config_path):
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: '{self.config_path}'.")

        with open(self.config_path, 'r') as file:
            try:
                config_data = json.load(file)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON configuration file: {e}")
                raise ValueError(f"Failed to parse JSON configuration file: {e}")

        self._validate_config(config_data)
        return config_data

    def _validate_config(self, config_data: dict) -> None:
        """Ensure that all required sections are present in the configuration."""
        missing_sections = [section for section in self.REQUIRED_SECTIONS if section not in config_data]
        if missing_sections:
            self.logger.error(f"Missing required configuration sections: {', '.join(missing_sections)}")
            raise ValueError(f"Missing required configuration sections: {', '.join(missing_sections)}")

    def get_config_section(self, section_name: str) -> dict:
        """Retrieve a configuration section by name."""
        return self.config_data.get(section_name, {})

    def get_can_filters(self) -> list:
        """Get the CAN filters from the configuration."""
        return self.get_config_section("CAN").get("software_filters", [])
