import logging.config
import yaml


def setup_logging(config_path: str = "logging_config.yaml") -> None:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
