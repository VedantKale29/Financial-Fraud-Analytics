from financial_fraud_analytics.config.configuration import ConfigurationManager
from financial_fraud_analytics.components.extraction import DataExtraction
from financial_fraud_analytics.components.transformation import DataTransformation
from financial_fraud_analytics.components.loading import DataLoading


class TrainingPipeline:

    def __init__(self):
        self.config_manager = ConfigurationManager()

    def run(self):

        # ---------- INGESTION ----------
        ingestion_config = self.config_manager.get_data_ingestion_config()
        raw_file = DataExtraction(ingestion_config).extract()

        # ---------- TRANSFORMATION ----------
        transformation_config = self.config_manager.get_transformation_config()
        bronze_file = DataTransformation(transformation_config).transform(raw_file)

        # ---------- LOADING ----------
        loading_config = self.config_manager.get_loading_config()
        DataLoading(loading_config).load(bronze_file)