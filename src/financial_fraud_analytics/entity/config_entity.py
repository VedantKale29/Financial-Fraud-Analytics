from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict


@dataclass(frozen=True)
class DataIngestionConfig:
    source_file: Path
    raw_path: Path


@dataclass(frozen=True)
class TransformationConfig:
    raw_path: Path
    bronze_path: Path


@dataclass(frozen=True)
class SparkConfig:
    app_name: str
    master: str
    shuffle_partitions: int
    output_files_per_partition: int


@dataclass(frozen=True)
class BronzeConfig:
    bronze_path: Path
    file_format: str
    compression: str
    partition_cols: List[str]


@dataclass(frozen=True)
class SilverConfig:
    bronze_path: Path
    silver_path: Path
    compression: str
    partition_cols: List[str]
    schema: Dict[str, str]
    primary_key: str
    dedup_keys: List[str]
    not_null_columns: List[str]
    min_amount: float
    watermark_days: int


@dataclass(frozen=True)
class LoadingConfig:
    bronze_path: Path
    db_uri: str
    table_name: str
    if_exists: str