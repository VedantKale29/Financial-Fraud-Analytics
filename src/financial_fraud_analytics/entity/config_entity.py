from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataIngestionConfig:
    source_file: Path
    raw_path: Path


@dataclass(frozen=True)
class TransformationConfig:
    raw_path: Path
    bronze_path: Path


@dataclass(frozen=True)
class LoadingConfig:
    bronze_path: Path
    db_uri: str
    table_name: str
    if_exists: str