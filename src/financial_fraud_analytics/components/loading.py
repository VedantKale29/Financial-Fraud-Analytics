import sys
import pandas as pd
from sqlalchemy import create_engine

from financial_fraud_analytics.logger.logging import get_logger
from financial_fraud_analytics.exception.exception import DataPlatformException

logger = get_logger()


class DataLoading:

    def __init__(self, config):
        self.config = config

    def load(self, file_path):
        try:
            logger.info("Loading to warehouse")

            engine = create_engine(self.config.db_uri)
            df = pd.read_csv(file_path)

            df.to_sql(
                self.config.table_name,
                engine,
                if_exists=self.config.if_exists,
                index=False,
            )

            logger.info("Loading done")

        except Exception:
            raise DataPlatformException("Loading failed", "LOADING", sys)