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
    jars_packages: str = ""


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


@dataclass(frozen=True)
class KafkaConfig:
    bootstrap_servers: str
    topic: str
    client_id: str
    starting_offsets: str
    throttle_ms: int


@dataclass(frozen=True)
class StreamingConfig:
    output_path: Path
    checkpoint_path: Path
    compression: str
    partition_cols: List[str]
    trigger_seconds: int
    max_offsets_per_trigger: int
    schema: Dict[str, str]


@dataclass(frozen=True)
class EnrichmentConfig:
    silver_path: Path
    enriched_path: Path
    compression: str
    partition_cols: List[str]
    base_date: str
    num_customers: int
    num_merchants: int
    categories: List[str]
    states: List[str]


@dataclass(frozen=True)
class GoldConfig:
    enriched_path: Path
    gold_path: Path
    compression: str
    top_n_merchants: int
    high_risk_min_fraud: int