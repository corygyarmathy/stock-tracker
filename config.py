# config.py

import logging

# Default path to your SQLite database
DEFAULT_DB_PATH = "portfolio.db"

# Logging configuration
DEFAULT_LOGGING_CONFIG_PATH: str = "logging_config.yaml"
LOG_FILE_PATH = "app.log"

# Yahoo Finance rate limit (requests per X seconds)
YF_MAX_REQUESTS = 2
YF_REQUEST_INTERVAL_SECONDS = 5


DEFAULT_CSV_PATH: str = "import.csv"
