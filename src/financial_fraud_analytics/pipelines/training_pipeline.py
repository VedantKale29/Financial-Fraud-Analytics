from financial_fraud_analytics.config.configuration import ConfigurationManager

from financial_fraud_analytics.components.extraction import DataExtraction
from financial_fraud_analytics.components.transformation import DataTransformation
from financial_fraud_analytics.components.loading import DataLoading


class TrainingPipeline:

    def __init__(self):

        self.config_manager = ConfigurationManager()


    def run(self):

        ingestion_config = self.config_manager.get_data_ingestion_config()

        extractor = DataExtraction(ingestion_config)

        raw_file = extractor.extract()

        transformer = DataTransformation(ingestion_config)

        bronze_file = transformer.transform(raw_file)

        loader = DataLoading(self.config_manager.get_config())

        loader.load(bronze_file)