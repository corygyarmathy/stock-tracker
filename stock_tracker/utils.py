import logging.config
import yaml

from config import DEFAULT_LOGGING_CONFIG_PATH


def setup_logging(config_path: str = DEFAULT_LOGGING_CONFIG_PATH) -> None:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
