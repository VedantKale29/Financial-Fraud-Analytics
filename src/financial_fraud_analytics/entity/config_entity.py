from dataclasses import dataclass
from pathlib import Path


@dataclass
class IngestionConfig:

    raw_data_path: Path
    bronze_path: Path


@dataclass
class TransformationConfig:

    silver_path: Path
    gold_path: Path


@dataclass
class LoadingConfig:

    warehouse_path: Path