import yaml
import os
from pathlib import Path


def read_yaml(file_path: Path):

    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def write_yaml(file_path: Path, data):

    with open(file_path, "w") as f:
        yaml.dump(data, f)


def create_dir(path: Path):

    os.makedirs(path, exist_ok=True)