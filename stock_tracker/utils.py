import logging.config
from pathlib import Path
import yaml


def setup_logging(config_path: Path) -> None:
    with open(file=config_path, mode="r") as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
