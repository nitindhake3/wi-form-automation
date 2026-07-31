import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import pytz

from logger import get_logger

logger = get_logger("config")

class ConfigValidationError(Exception):
    """Custom exception raised when configuration validation fails."""
    pass

class AppConfig:
    """Manages application configuration, validation, and dynamic variable expansion."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.form_url: str = ""
        self.submit_time: str = ""
        self.timezone_str: str = ""
        self.answers: Dict[str, Any] = {}
        self.load_and_validate()

    def load_and_validate(self) -> None:
        """Loads config.json and validates all required fields."""
        if not self.config_path.exists():
            raise ConfigValidationError(f"Configuration file not found at: {self.config_path.resolve()}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON format in {self.config_path}: {e}")

        # Check required keys
        required_keys = ["form_url", "submit_time", "timezone", "answers"]
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise ConfigValidationError(f"Missing required configuration keys: {', '.join(missing_keys)}")

        self.form_url = data["form_url"].strip()
        if not self.form_url or not self.form_url.startswith("http"):
            raise ConfigValidationError(f"Invalid 'form_url' in config: {self.form_url}")

        # Automatically ensure Google Form URL ends with /viewform instead of /formResponse
        if self.form_url.endswith("/formResponse"):
            self.form_url = self.form_url.rsplit("/formResponse", 1)[0] + "/viewform"

        self.submit_time = data["submit_time"].strip()
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", self.submit_time):
            raise ConfigValidationError(f"Invalid 'submit_time' format: '{self.submit_time}'. Expected HH:MM in 24-hour format.")

        self.days_of_week = data.get("days_of_week", "mon-fri").strip()

        self.timezone_str = data["timezone"].strip()
        try:
            pytz.timezone(self.timezone_str)
        except Exception:
            raise ConfigValidationError(f"Invalid 'timezone': '{self.timezone_str}'. Must be a valid IANA timezone string (e.g. 'Asia/Kolkata').")

        if not isinstance(data["answers"], dict):
            raise ConfigValidationError("'answers' field must be a JSON object (dictionary).")

        self.answers = data["answers"]
        logger.info(f"Loaded configuration from {self.config_path}. Schedule time: {self.submit_time} ({self.timezone_str}).")

    def get_resolved_answers(self) -> Dict[str, str]:
        """
        Returns a dictionary of answers with any dynamic placeholder tags expanded.
        Supported placeholders:
          - {{DATE}} or {{TODAY}} -> YYYY-MM-DD
          - {{TIME}} -> HH:MM (current time)
          - {{DATETIME}} -> YYYY-MM-DD HH:MM
        """
        tz = pytz.timezone(self.timezone_str)
        now = datetime.now(tz)

        resolved = {}
        for question, raw_val in self.answers.items():
            if isinstance(raw_val, str):
                val = raw_val
                val = val.replace("{{DATE}}", now.strftime("%Y-%m-%d"))
                val = val.replace("{{TODAY}}", now.strftime("%Y-%m-%d"))
                val = val.replace("{{TIME}}", now.strftime("%H:%M"))
                val = val.replace("{{DATETIME}}", now.strftime("%Y-%m-%d %H:%M"))
                resolved[question] = val
            else:
                resolved[question] = str(raw_val)

        return resolved
