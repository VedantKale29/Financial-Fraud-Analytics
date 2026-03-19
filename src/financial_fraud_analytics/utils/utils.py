import os
import sys
import yaml
from pathlib import Path
from typing import Any

from ensure import ensure_annotations

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


def read_yaml(file_path: Path):

    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)

    except Exception as e:
        raise DataPlatformException(
            f"Failed to read yaml {file_path}",
            "UTILS",
            sys
        )


def write_yaml(file_path: Path, data):

    try:
        with open(file_path, "w") as f:
            yaml.dump(data, f)

    except Exception as e:
        raise DataPlatformException(
            "Failed to write yaml",
            "UTILS",
            sys
        )


@ensure_annotations
def create_directories(path_to_directories: list, verbose=True):

    for path in path_to_directories:

        os.makedirs(path, exist_ok=True)

        if verbose:
            logger.info(f"Created directory at: {path}")


def get_size(path: Path) -> str:

    size_in_kb = round(os.path.getsize(path) / 1024)

    return f"~ {size_in_kb} KB"


def get_database_uri(config: dict) -> str:

    try:

        db = config['database']

        return (
            f"postgresql://{db['user']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['db']}"
        )

    except KeyError as e:

        raise DataPlatformException(
            f"Missing DB config key: {str(e)}",
            "UTILS",
            sys
        )