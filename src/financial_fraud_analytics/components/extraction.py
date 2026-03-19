import sys
import pandas as pd

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class DataExtraction:

    def __init__(self, config):

        self.config = config


    def extract(self):

        try:

            logger.info("Starting extraction")

            df = pd.read_csv(self.config.source_file)

            output = self.config.raw_path / "transactions.csv"

            df.to_csv(output, index=False)

            logger.info("Extraction completed")

            return output

        except Exception as e:

            raise DataPlatformException(
                "Extraction failed",
                "EXTRACTION",
                sys
            )