from pathlib import Path

from financial_fraud_analytics.constants.constants import (
    CONFIG_FILE_PATH,
    SCHEMA_FILE_PATH,
    PARAMS_FILE_PATH,
)
from financial_fraud_analytics.utils.utils import (
    read_yaml,
    create_directories,
    get_database_uri,
)
from financial_fraud_analytics.entity.config_entity import (
    DataIngestionConfig,
    TransformationConfig,
    BronzeConfig,
    SilverConfig,
    LoadingConfig,
)


class ConfigurationManager:

    def __init__(self):
        self.config = read_yaml(CONFIG_FILE_PATH)
        self.schema = read_yaml(SCHEMA_FILE_PATH)
        self.params = read_yaml(PARAMS_FILE_PATH)

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

    def get_bronze_config(self) -> BronzeConfig:
        bronze = self.config['bronze']
        return BronzeConfig(
            bronze_path=Path(self.config['paths']['bronze']),
            file_format=bronze['format'],
            compression=bronze['compression'],
            partition_cols=bronze['partition_cols'],
        )

    def get_silver_config(self) -> SilverConfig:
        silver = self.config['silver']
        p = self.params['silver']
        contract = self.schema['silver']['transactions']
        return SilverConfig(
            bronze_path=Path(self.config['paths']['bronze']),
            silver_path=Path(self.config['paths']['silver']),
            compression=silver['compression'],
            partition_cols=silver['partition_cols'],
            schema=contract['columns'],
            primary_key=contract['primary_key'],
            dedup_keys=p['dedup_keys'],
            not_null_columns=p['not_null_columns'],
            min_amount=p['min_amount'],
            watermark_days=p['watermark_days'],
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