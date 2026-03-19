from pathlib import Path

from financial_fraud_analytics.constants.constants import (
    CONFIG_FILE_PATH,
    SCHEMA_FILE_PATH,
)

from financial_fraud_analytics.utils.utils import (
    read_yaml,
    create_directories,
)

from financial_fraud_analytics.entity.config_entity import (
    DataIngestionConfig,
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
            raw_path=Path(paths['raw']),
            bronze_path=Path(paths['bronze']),
            source_file=self.config['data_path'],
        )