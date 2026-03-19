import sys
import pandas as pd

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class DataTransformation:

    def __init__(self, config):

        self.config = config


    def transform(self, input_file):

        try:

            logger.info("Starting transformation")

            df = pd.read_csv(input_file)

            df = df.dropna()

            bronze_file = self.config.bronze_path / "bronze.csv"

            df.to_csv(bronze_file, index=False)

            logger.info("Transformation done")

            return bronze_file

        except Exception as e:

            raise DataPlatformException(
                "Transformation failed",
                "TRANSFORMATION",
                sys
            )