from pathlib import Path

from financial_fraud_analytics.constants.constants import (
    CONFIG_FILE_PATH,
    SCHEMA_FILE_PATH,
)
from financial_fraud_analytics.utils.utils import (
    read_yaml,
    create_directories,
    get_database_uri,
)
from financial_fraud_analytics.entity.config_entity import (
    DataIngestionConfig,
    TransformationConfig,
    LoadingConfig,
)


class ConfigurationManager:

    def __init__(self):
        self.config = read_yaml(CONFIG_FILE_PATH)
        self.schema = read_yaml(SCHEMA_FILE_PATH)

        create_directories([
            self.config['paths']['raw'],
            self.config['paths']['bronze'],
            self.config['paths']['silver'],
            self.config['paths']['gold'],
            self.config['paths']['warehouse'],
        ])

    def get_data_ingestion_config(self) -> DataIngestionConfig:
        paths = self.config['paths']
        return DataIngestionConfig(
            source_file=Path(self.config['data_path']),
            raw_path=Path(paths['raw']),
        )

    def get_transformation_config(self) -> TransformationConfig:
        paths = self.config['paths']
        return TransformationConfig(
            raw_path=Path(paths['raw']),
            bronze_path=Path(paths['bronze']),
        )

    def get_loading_config(self) -> LoadingConfig:
        loading = self.config['loading']
        return LoadingConfig(
            bronze_path=Path(self.config['paths']['bronze']),
            db_uri=get_database_uri(self.config),
            table_name=loading['table'],
            if_exists=loading['if_exists'],
        )

    def get_config(self):
        return self.config