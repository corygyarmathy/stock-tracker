# config.py

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env or specific test override
env_file: str = ".env.test" if os.getenv("PYTEST_CURRENT_TEST") else ".env"
_ = load_dotenv(dotenv_path=env_file)


# Define project root directory dynamically
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
# CONFIG_FOLDER = "config/"

ENV: str = os.getenv("ENV", "development").lower()

DEFAULT_DB_PATH: str = os.getenv("DB_PATH", "dev.db")
DEFAULT_CSV_PATH: str = os.getenv("CSV_PATH", "import.csv")

# Logging configuration
DEFAULT_LOGGING_CONFIG_PATH = os.path.join(
    PROJECT_ROOT, os.getenv("LOGGING_CONFIG_PATH", "config/logging_config.yaml")
)
# DEFAULT_LOGGING_CONFIG_PATH: str = (
#     f"{PROJECT_ROOT}/{os.getenv('LOGGING_CONFIG_PATH', 'config/logging_config.yaml')}"
# )
DEFAULT_LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", "app.log")
DEFAULT_LOG_LEVEL: str = os.getenv("LOG_LEVEL", "logging.DEBUG")

# Yahoo Finance rate limit (requests per X seconds)
DEFAULT_YF_MAX_REQUESTS: str = os.getenv("YF_MAX_REQUESTS", "2")
DEFAULT_YF_REQUEST_INTERVAL_SECONDS: str = os.getenv("YF_REQUEST_INTERVAL_SECONDS", "5")
