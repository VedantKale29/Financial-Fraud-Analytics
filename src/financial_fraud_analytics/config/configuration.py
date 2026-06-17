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
    SparkConfig,
    KafkaConfig,
    StreamingConfig,
    BronzeConfig,
    SilverConfig,
    EnrichmentConfig,
    GoldConfig,
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

    def get_spark_config(self) -> SparkConfig:
        s = self.config['spark']
        return SparkConfig(
            app_name=s['app_name'],
            master=s['master'],
            shuffle_partitions=s['shuffle_partitions'],
            output_files_per_partition=s['output_files_per_partition'],
            jars_packages=s.get('jars_packages', ''),
        )

    def get_kafka_config(self) -> KafkaConfig:
        k = self.config['kafka']
        return KafkaConfig(
            bootstrap_servers=k['bootstrap_servers'],
            topic=k['topic'],
            client_id=k['client_id'],
            starting_offsets=k['starting_offsets'],
            throttle_ms=k['throttle_ms'],
        )

    def get_streaming_config(self) -> StreamingConfig:
        st = self.config['streaming']
        contract = self.schema['silver']['transactions']
        return StreamingConfig(
            output_path=Path(self.config['paths']['bronze_stream']),
            checkpoint_path=Path(st['checkpoint_path']),
            compression=self.config['bronze']['compression'],
            partition_cols=self.config['bronze']['partition_cols'],
            trigger_seconds=st['trigger_seconds'],
            max_offsets_per_trigger=st['max_offsets_per_trigger'],
            schema=contract['columns'],
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

    def get_enrichment_config(self) -> EnrichmentConfig:
        e = self.params['enrichment']
        return EnrichmentConfig(
            silver_path=Path(self.config['paths']['silver']),
            enriched_path=Path(self.config['paths']['enriched']),
            compression=self.config['silver']['compression'],
            partition_cols=self.config['silver']['partition_cols'],
            base_date=e['base_date'],
            num_customers=e['num_customers'],
            num_merchants=e['num_merchants'],
            categories=e['categories'],
            states=e['states'],
        )

    def get_gold_config(self) -> GoldConfig:
        g = self.params['gold']
        return GoldConfig(
            enriched_path=Path(self.config['paths']['enriched']),
            gold_path=Path(self.config['paths']['gold']),
            compression=self.config['gold']['compression'],
            top_n_merchants=g['top_n_merchants'],
            high_risk_min_fraud=g['high_risk_min_fraud'],
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