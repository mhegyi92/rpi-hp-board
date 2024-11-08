import json
import os
import logging
from typing import Optional, List

class ConfigurationManager:
    def __init__(self, config_path: str, required_sections: Optional[List[str]] = None) -> None:
        """Initialize ConfigurationManager with config file path and required sections."""
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.required_sections = required_sections if required_sections else ["LOGGING", "UI", "CAN"]
        self.config_data = self._load_and_validate_config()

    def _load_and_validate_config(self) -> dict:
        """Load and validate the configuration file."""
        if not os.path.exists(self.config_path):
            self.logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: '{self.config_path}'.")

        with open(self.config_path, 'r') as file:
            try:
                config_data = json.load(file)
                config_data = self._expand_env_variables(config_data)  # Expand env variables in config
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON configuration file: {e}")
                raise ValueError(f"Failed to parse JSON configuration file: {e}")

        self._validate_config(config_data)
        return config_data

    def _validate_config(self, config_data: dict) -> None:
        """Ensure that all required sections and their keys are present in the configuration."""
        missing_sections = [section for section in self.required_sections if section not in config_data]
        if missing_sections:
            self.logger.error(f"Missing required configuration sections: {', '.join(missing_sections)}")
            raise ValueError(f"Missing required configuration sections: {', '.join(missing_sections)}")

        # Example: Check for required keys in each section, if necessary
        required_keys = {
            "LOGGING": ["file", "level"],
            "CAN": ["channel", "bitrate", "software_filters"]
            # Add more as needed
        }

        for section, keys in required_keys.items():
            if section in config_data:
                missing_keys = [key for key in keys if key not in config_data[section]]
                if missing_keys:
                    self.logger.error(f"Missing keys in '{section}': {', '.join(missing_keys)}")
                    raise ValueError(f"Missing keys in '{section}': {', '.join(missing_keys)}")

    def _expand_env_variables(self, config_data: dict) -> dict:
        """Expand environment variables within the configuration values."""
        def expand_value(value):
            if isinstance(value, str):
                return os.path.expandvars(value)
            if isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [expand_value(i) for i in value]
            return value

        return {key: expand_value(val) for key, val in config_data.items()}

    def get_config_section(self, section_name: str) -> dict:
        """Retrieve a configuration section by name."""
        return self.config_data.get(section_name, {})

    def get_can_filters(self) -> list:
        """Get the CAN filters from the configuration."""
        return self.get_config_section("CAN").get("software_filters", [])

    def reload_config(self) -> None:
        """Reload the configuration file."""
        self.logger.info("Reloading configuration file.")
        self.config_data = self._load_and_validate_config()
        self.logger.info("Configuration reloaded successfully.")
