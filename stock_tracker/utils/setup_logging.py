from logging import Logger
import logging.config
from pathlib import Path
import sys

import yaml


def setup_logging(config_path: Path, log_level: str) -> None:
    try:
        # Load default logging configuration from supplied Path to YAML file
        with open(file=config_path, mode="r") as f:
            config = yaml.safe_load(f)

        # Apply default config
        logging.config.dictConfig(config)

        # Override default log_level from AppConfig
        override_level_str: str = log_level.upper()

        # Convert string level to integer level. logging module constants are integers.
        level_map: dict[str, int] = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "NOTSET": logging.NOTSET,
        }
        override_level: int | None = level_map.get(override_level_str)

        if override_level is None:
            logging.warning(
                f"Invalid log level '{log_level}' from AppConfig. Using default levels from YAML."
            )
            return

        package_logger: Logger = logging.getLogger("stock_tracker")
        if package_logger:  # Check if the logger exists (it should if in YAML)
            package_logger.setLevel(override_level)
            logging.info(
                f"Package logger 'stock_tracker' level overridden to {override_level_str}"
            )  # Log via root/existing logger

    except FileNotFoundError:
        print(f"Error: Logging config file not found at {config_path}", file=sys.stderr)
        # Fallback: Configure a basic console logger so subsequent errors are seen
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Failed to load logging config from {config_path}")
    except RuntimeError as e:
        print(f"Error: AppConfig not initialised when setting up logging: {e}", file=sys.stderr)
        # Fallback: Configure a basic console logger so subsequent errors are seen
        logging.basicConfig(level=logging.INFO)
        logging.error(
            "Failed to setup logging due to AppConfig not being initialised. Setup default logging."
        )
    except Exception as e:
        print(f"An unexpected error occurred during logging setup: {e}", file=sys.stderr)
        # Fallback: Configure a basic console logger so subsequent errors are seen
        logging.basicConfig(level=logging.INFO)
        logging.error(f"An unexpected error occurred during logging setup: {e}")
