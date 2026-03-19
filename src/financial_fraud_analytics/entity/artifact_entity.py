from dataclasses import dataclass
from pathlib import Path


@dataclass
class IngestionArtifact:

    bronze_file: Path


@dataclass
class TransformationArtifact:

    silver_file: Path
    gold_file: Path


@dataclass
class LoadingArtifact:

    warehouse_db: Path